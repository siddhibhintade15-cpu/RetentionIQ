"""
app/api/batch.py
----------------
Resilient, forgiving CSV ingestion, smart column mapping, and automated health profiling.

Endpoints:
- POST /api/batch/profile: Upload any CSV -> instant data health report + smart mapping
- POST /api/batch/remap: Live update mappings and preview recomputed health
- POST /api/batch/dynamic-process: Execute dynamic ingestion, scoring, SHAP, and persistence
- GET  /api/batch/{batch_id}/export: Export enriched cohort CSV with original + model columns
- POST /api/batch/upload: Legacy endpoint kept for strict/lenient backward compatibility
- POST /api/batch/validate: Legacy dry-run endpoint
- GET  /api/batch/template: Blank template download
- GET  /api/batch/sample: Valid demonstration cohort download
"""

from __future__ import annotations

import io
import json
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile

from app.db import get_batch, get_db, insert_batch, insert_customer, insert_customers_bulk
from app.schemas import (
    BatchResponse,
    BatchRowResult,
    BatchValidationReport,
    DatasetHealthReport,
    DynamicProcessRequest,
    DynamicProcessResponse,
    RemapRequest,
)
from app.services.feature_spec import FEATURE_SPECS, MODEL_FEATURES
from app.services.ingestion_service import IngestionEngine
from app.services.mapping_service import MIN_MAPPED_FEATURES, MappingEngine
from app.services.model_service import model_service, risk_level
from app.services.profiling_service import ProfilingService
from app.services.validation_service import CSVValidationEngine

router = APIRouter(prefix="/api/batch", tags=["Batch Analysis"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_DIR = PROJECT_ROOT / "data" / "staged_uploads"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

MAX_SHAP_ROWS = 5000
STAGING_TTL_SECONDS = 1800  # 30 minutes


def _cleanup_expired_staging() -> None:
    """Removes staged files older than 30 minutes."""
    now = time.time()
    try:
        for p in STAGING_DIR.glob("*"):
            if p.is_file() and (now - p.stat().st_mtime) > STAGING_TTL_SECONDS:
                p.unlink(missing_ok=True)
    except Exception:
        pass


def _save_staged_dataset(upload_id: str, df: pd.DataFrame, meta: dict[str, Any]) -> None:
    """Persists staged dataframe as parquet and metadata as json."""
    df_path = STAGING_DIR / f"{upload_id}.parquet"
    meta_path = STAGING_DIR / f"{upload_id}_meta.json"
    df.to_parquet(df_path, index=False)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)


def _load_staged_dataset(upload_id: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Loads staged dataset from disk or raises 404."""
    df_path = STAGING_DIR / f"{upload_id}.parquet"
    meta_path = STAGING_DIR / f"{upload_id}_meta.json"

    if not df_path.exists() or not meta_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "STAGED_SESSION_EXPIRED",
                "message": "Upload staging session expired or not found.",
                "hint": "Please upload your CSV file again to start a new analysis."
            },
        )

    df = pd.read_parquet(df_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    return df, meta


# ---------------------------------------------------------------------------
# Dynamic Stage-then-Process Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/profile",
    response_model=DatasetHealthReport,
    summary="Upload and profile any customer CSV without rigid schema constraints",
)
async def profile_dataset(file: UploadFile = File(...)) -> DatasetHealthReport:
    """
    Accepts arbitrary customer CSV files, detects delimiters/encodings, auto-maps
    columns via fuzzy matching, and generates a visual Data Health Report (<200ms).
    Stages data server-side for review and one-click scoring.
    """
    _cleanup_expired_staging()
    content = await file.read()
    filename = file.filename or "upload.csv"

    # Stage 1 & 2: Safe decode
    text, encoding = IngestionEngine.read_and_decode(content, filename)

    # Stage 3: Delimiter sniffing
    delimiter = IngestionEngine.detect_delimiter(text)

    # Stage 4: Parse into raw dataframe
    df, original_headers = IngestionEngine.parse_raw_dataframe(text, delimiter)

    # Stage 5: Profile & Map
    upload_id = uuid.uuid4().hex
    profile = ProfilingService.profile_dataset(
        upload_id=upload_id,
        filename=filename,
        df=df,
        encoding=encoding,
        delimiter=delimiter,
    )

    # Stage 6: Persist staged session
    meta = {
        "upload_id": upload_id,
        "filename": filename,
        "encoding": encoding,
        "delimiter": delimiter,
        "original_headers": original_headers,
        "created_at": time.time(),
    }
    _save_staged_dataset(upload_id, df, meta)

    return DatasetHealthReport(**profile)


@router.post(
    "/remap",
    response_model=DatasetHealthReport,
    summary="Update column mappings without re-uploading file",
)
def remap_dataset(req: RemapRequest) -> DatasetHealthReport:
    """
    Recomputes feature mappings and dataset health diagnostics based on
    user-adjusted column assignments without requiring a new upload.
    """
    df, meta = _load_staged_dataset(req.upload_id)

    profile = ProfilingService.profile_dataset(
        upload_id=req.upload_id,
        filename=meta["filename"],
        df=df,
        encoding=meta["encoding"],
        delimiter=meta["delimiter"],
        user_overrides=req.overrides,
    )

    return DatasetHealthReport(**profile)


@router.post(
    "/dynamic-process",
    response_model=DynamicProcessResponse,
    summary="Execute dynamic ingestion, scoring, SHAP analysis, and persistence",
)
def dynamic_process(req: DynamicProcessRequest) -> DynamicProcessResponse:
    """
    Cleans dirty values, imputes missing features with training medians,
    scores retention probabilities, runs tree SHAP, and persists records to SQLite.
    """
    df, meta = _load_staged_dataset(req.upload_id)
    filename = meta["filename"]

    # 1. Resolve final column mappings
    numeric_dict = {}
    for col in df.columns:
        num_s, _ = IngestionEngine.parse_locale_numeric(df[col])
        numeric_dict[col] = num_s

    mapping_res = MappingEngine.resolve_mappings(
        user_columns=list(df.columns),
        numeric_dict=numeric_dict,
        user_overrides=req.overrides,
    )

    mapped_feats = mapping_res["mapped_features"]
    id_col = mapping_res["id_column"]

    # Reject if fewer than MIN_MAPPED_FEATURES can be identified
    if len(mapped_feats) < MIN_MAPPED_FEATURES:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INSUFFICIENT_FEATURES",
                "message": f"Only {len(mapped_feats)} of 7 model features could be identified.",
                "hint": f"At least {MIN_MAPPED_FEATURES} features must be mapped. Review column mapping options."
            },
        )

    # 2. Assign batch record
    total_rows = len(df)
    batch_id = insert_batch(
        filename=filename,
        total_rows=total_rows,
        valid_rows=total_rows,
        error_rows=0,
        summary=None,
    )

    # 3. Special transformations (DOB -> Age, email hashing, ID generation)
    df_transformed, customer_ids, transform_notices = MappingEngine.transform_special_columns(
        df=df,
        mapped_features=mapped_feats,
        id_column=id_col,
        batch_id=batch_id,
    )

    # 4. Prepare, clip, and impute feature matrix
    clean_features_df, row_imputed_flags, data_quality_flags = ProfilingService.prepare_and_clean_data(
        df=df_transformed,
        mapped_features=mapped_feats,
        batch_id=batch_id,
    )

    # 5. Model scoring
    probabilities = model_service.model.predict_proba(clean_features_df)[:, 1]
    predictions = (probabilities >= 0.50).astype(int)
    risk_tiers = [risk_level(float(p)) for p in probabilities]

    # 6. Vectorized SHAP contributions
    shap_sample_len = min(len(clean_features_df), MAX_SHAP_ROWS)
    dmat = xgb.DMatrix(clean_features_df.iloc[:shap_sample_len], feature_names=MODEL_FEATURES)
    contribs = model_service.booster.predict(dmat, pred_contribs=True)

    # Extract top 3 signed drivers per row
    top_drivers_list: list[str] = []
    for r_idx in range(len(clean_features_df)):
        if r_idx < shap_sample_len:
            row_c = contribs[r_idx, :-1]  # exclude bias
            top_indices = np.argsort(np.abs(row_c))[::-1][:3]
            drivers = [
                f"{MODEL_FEATURES[i]}: {'+' if row_c[i] >= 0 else ''}{row_c[i]:.2f}"
                for i in top_indices
            ]
            top_drivers_list.append("; ".join(drivers))
        else:
            top_drivers_list.append("Heuristic / Fast Mode")

    # 7. Bulk persistence in single transaction
    db_records: list[tuple[str | None, str, int, float, str, str, int | None]] = []
    results_summary: list[dict[str, Any]] = []

    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0

    for idx in range(total_rows):
        cid = customer_ids[idx]
        p_prob = round(float(probabilities[idx]), 4)
        p_pred = int(predictions[idx])
        r_tier = risk_tiers[idx]
        feat_dict = clean_features_df.iloc[idx].to_dict()

        if r_tier == "High":
            high_risk_count += 1
        elif r_tier == "Medium":
            medium_risk_count += 1
        else:
            low_risk_count += 1

        db_records.append((
            cid,
            json.dumps(feat_dict),
            p_pred,
            p_prob,
            r_tier,
            "dynamic_batch",
            batch_id,
        ))

        if idx < 100:
            results_summary.append({
                "row_index": idx + 1,
                "customer_id": cid,
                "prediction": p_pred,
                "probability": p_prob,
                "risk_level": r_tier,
                "top_drivers": top_drivers_list[idx],
                "data_quality_flag": data_quality_flags[idx],
                "imputed_features": row_imputed_flags[idx],
            })

    insert_customers_bulk(db_records)

    # 8. Compute quality metrics & confidence
    imputed_features_list = [f for f in MODEL_FEATURES if f not in mapped_feats]
    completeness = 1.0 - (len(imputed_features_list) / 7.0)

    if len(imputed_features_list) <= 1:
        scoring_confidence = "High"
        quality_score = 92
        quality_label = "Excellent"
    elif len(imputed_features_list) <= 3:
        scoring_confidence = "Medium"
        quality_score = 78
        quality_label = "Good"
    else:
        scoring_confidence = "Low"
        quality_score = 55
        quality_label = "Fair"

    # Update batch summary record
    batch_summary = {
        "quality_score": quality_score,
        "quality_label": quality_label,
        "scoring_confidence": scoring_confidence,
        "mapped_features": mapped_feats,
        "imputed_features": imputed_features_list,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,
        "avg_retention_probability": round(float(np.mean(probabilities)), 4),
    }

    with get_db() as conn:
        conn.execute(
            "UPDATE batches SET summary=? WHERE id=?",
            (json.dumps(batch_summary), batch_id),
        )

    # 9. Save enriched export CSV (Original Columns + Model Predictions)
    df_export = df.copy()
    df_export["customer_id"] = customer_ids
    df_export["predicted_retention"] = predictions
    df_export["retention_probability"] = probabilities
    df_export["risk_tier"] = risk_tiers
    df_export["top_drivers"] = top_drivers_list
    df_export["imputed_features"] = [",".join(f) if f else "none" for f in row_imputed_flags]
    df_export["data_quality_flag"] = data_quality_flags

    export_path = STAGING_DIR / f"{batch_id}_export.csv"
    df_export.to_csv(export_path, index=False)

    return DynamicProcessResponse(
        batch_id=batch_id,
        filename=filename,
        total_rows=total_rows,
        quality_score=quality_score,
        quality_label=quality_label,
        scoring_confidence=scoring_confidence,
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        low_risk_count=low_risk_count,
        avg_retention_probability=round(float(np.mean(probabilities)), 4),
        results=results_summary,
        export_url=f"/api/batch/{batch_id}/export",
    )


@router.get(
    "/{batch_id}/export",
    summary="Download enriched CSV with original columns and model predictions",
    response_class=Response,
)
def export_batch_csv(batch_id: int) -> Response:
    """Download the full enriched cohort CSV joined positionally with original columns."""
    export_path = STAGING_DIR / f"{batch_id}_export.csv"

    if export_path.exists():
        content = export_path.read_text(encoding="utf-8")
    else:
        # Fallback from SQLite customers
        with get_db() as conn:
            rows = conn.execute(
                "SELECT customer_id, features, prediction, probability, risk_level FROM customers WHERE batch_id = ?",
                (batch_id,)
            ).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="Batch export not found.")

        out_rows = []
        for r in rows:
            feats = json.loads(r["features"])
            feats["customer_id"] = r["customer_id"]
            feats["prediction"] = r["prediction"]
            feats["probability"] = r["probability"]
            feats["risk_level"] = r["risk_level"]
            out_rows.append(feats)

        df_out = pd.DataFrame(out_rows)
        content = df_out.to_csv(index=False)

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="retentioniq_batch_{batch_id}_export.csv"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


# ---------------------------------------------------------------------------
# Legacy Endpoints (Preserved for 100% backward compatibility)
# ---------------------------------------------------------------------------

BLANK_TEMPLATE_CSV = (
    "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
    "USR-001,28,7,22.5,30,8,0,1\n"
)

SAMPLE_VALID_CSV = (
    "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
    "USR-101,28,7,22.5,30,8,0,1\n"
    "USR-102,45,3,12.0,90,2,1,0\n"
    "USR-103,19,14,45.0,15,20,0,3\n"
    "USR-104,36,5,18.5,120,4,2,0\n"
    "USR-105,52,2,8.0,240,1,3,0\n"
    "USR-106,24,10,32.0,45,12,0,2\n"
    "USR-107,31,8,25.0,60,6,1,1\n"
    "USR-108,60,1,5.5,300,0,4,0\n"
    "USR-109,22,12,40.0,10,15,0,5\n"
    "USR-110,40,6,20.0,180,5,1,2\n"
)


@router.get("/template", summary="Download blank CSV template", response_class=Response)
def download_template() -> Response:
    return Response(
        content=BLANK_TEMPLATE_CSV,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="retentioniq_template.csv"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get("/sample", summary="Download valid sample dataset", response_class=Response)
def download_sample() -> Response:
    return Response(
        content=SAMPLE_VALID_CSV,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="retentioniq_sample_valid.csv"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.post("/validate", response_model=BatchValidationReport, summary="Dry-run validation")
async def validate_batch(
    file: UploadFile = File(...),
    customer_id_column: Optional[str] = None,
) -> BatchValidationReport:
    content = await file.read()
    filename = file.filename or "upload.csv"
    text = CSVValidationEngine.validate_file_transport(content=content, filename=filename)
    _, report = CSVValidationEngine.parse_and_validate(text=text, filename=filename, customer_id_col=customer_id_column)
    return report


@router.post("/upload", response_model=BatchResponse, summary="Strict/Lenient batch upload")
async def batch_upload(
    file: UploadFile = File(...),
    customer_id_column: Optional[str] = None,
    mode: str = Query("strict", pattern="^(strict|lenient)$"),
) -> BatchResponse:
    content = await file.read()
    filename = file.filename or "upload.csv"

    text = CSVValidationEngine.validate_file_transport(content=content, filename=filename)
    parsed_rows, report = CSVValidationEngine.parse_and_validate(
        text=text,
        filename=filename,
        customer_id_col=customer_id_column,
    )

    if mode == "strict" and report.error_rows > 0:
        raise HTTPException(status_code=422, detail=report.model_dump())

    results: list[BatchRowResult] = []
    valid_count = 0
    error_count = 0

    batch_id = insert_batch(
        filename=filename,
        total_rows=report.total_rows,
        valid_rows=0,
        error_rows=0,
        summary=None,
    )

    for row_item in parsed_rows:
        row_num = row_item["row_index"]
        cust_id = row_item["customer_id"]

        if not row_item["ok"]:
            results.append(BatchRowResult(row_index=row_num, customer_id=cust_id, ok=False, error=row_item["error"]))
            error_count += 1
            continue

        feat_dict = row_item["features"]
        try:
            pred_result = model_service.predict(feat_dict)
            insert_customer(
                features=feat_dict,
                prediction=pred_result["prediction"],
                probability=pred_result["probability"],
                risk_lv=pred_result["risk_level"],
                source="batch",
                customer_id=cust_id,
                batch_id=batch_id,
            )
            results.append(BatchRowResult(
                row_index=row_num,
                customer_id=cust_id,
                ok=True,
                prediction=pred_result["prediction"],
                probability=pred_result["probability"],
                risk_level=pred_result["risk_level"],
            ))
            valid_count += 1
        except Exception as exc:
            results.append(BatchRowResult(row_index=row_num, customer_id=cust_id, ok=False, error=f"Prediction failed: {exc}"))
            error_count += 1

    with get_db() as conn:
        conn.execute("UPDATE batches SET valid_rows=?, error_rows=? WHERE id=?", (valid_count, error_count, batch_id))

    return BatchResponse(
        batch_id=batch_id,
        filename=filename,
        total_rows=report.total_rows,
        valid_rows=valid_count,
        error_rows=error_count,
        results=results,
        errors=report.errors,
    )
