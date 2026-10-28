"""
app/services/profiling_service.py
---------------------------------
Automated dataset health audit, vectorized statistical profiling, and quality scoring.
Computes dataset completeness, outlier ratios, duplicate rates, and scoring confidence.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.services.feature_spec import (
    FEATURE_SPECS,
    MODEL_FEATURES,
    TARGET_ALIASES,
    TRAINING_DEFAULTS,
)
from app.services.ingestion_service import IngestionEngine
from app.services.mapping_service import MappingEngine, normalize_col_name

SAMPLE_THRESHOLD = 10_000


class ProfilingService:
    """Profiles arbitrary CSV datasets, generates health diagnostics, and cleans data for scoring."""

    @classmethod
    def profile_dataset(
        cls,
        upload_id: str,
        filename: str,
        df: pd.DataFrame,
        encoding: str,
        delimiter: str,
        user_overrides: Optional[dict[str, Optional[str]]] = None,
    ) -> dict[str, Any]:
        """
        Fast (<200ms) statistical health profile of uploaded dataset.
        """
        total_rows = len(df)
        total_columns = len(df.columns)
        profiled_on_sample = False

        # Work on sample if dataset is massive for sub-200ms speed
        if total_rows > SAMPLE_THRESHOLD:
            prof_df = df.sample(n=SAMPLE_THRESHOLD, random_state=42)
            profiled_on_sample = True
        else:
            prof_df = df

        # Parse numeric series for each column
        numeric_dict: dict[str, pd.Series] = {}
        is_numeric_dict: dict[str, bool] = {}

        for col in prof_df.columns:
            num_s, is_num = IngestionEngine.parse_locale_numeric(prof_df[col])
            numeric_dict[col] = num_s
            is_numeric_dict[col] = is_num

        # Smart Mapping
        mapping_result = MappingEngine.resolve_mappings(
            user_columns=list(df.columns),
            numeric_dict=numeric_dict,
            user_overrides=user_overrides,
        )

        mappings = mapping_result["mappings"]
        unmapped_cols = mapping_result["unmapped_columns"]
        mapped_feats = mapping_result["mapped_features"]
        id_col = mapping_result["id_column"]
        target_col = mapping_result["target_column"]
        warnings = list(mapping_result["warnings"])
        notices: list[dict[str, Any]] = []

        # Target column polarity & historical retention
        historical_retention_rate: Optional[float] = None
        if target_col and target_col in df.columns:
            hist_rate = cls._parse_historical_target(df[target_col], target_col)
            if hist_rate is not None:
                historical_retention_rate = round(hist_rate, 4)
                warnings.append(f"Historical outcome detected in '{target_col}' ({round(hist_rate*100, 1)}% retention rate). This column will be used for audit comparisons only and excluded from model scoring.")

        # Column health statistics
        col_health_list: list[dict[str, Any]] = []
        outlier_counts = 0
        total_non_null_mapped = 0
        total_possible_mapped = 0

        for col in prof_df.columns:
            raw_s = prof_df[col]
            num_s = numeric_dict[col]
            is_num = is_numeric_dict[col]

            detected_type = IngestionEngine.detect_column_type(raw_s, num_s, is_num)
            null_count = int(num_s.isna().sum()) if is_num else int((raw_s == "").sum() + (raw_s.isna().sum()))
            null_pct = round(null_count / len(prof_df), 4)

            # Check if mapped to a feature
            mapped_feat = None
            conf = None
            for m in mappings:
                if m["user_column"] == col:
                    mapped_feat = m["model_feature"]
                    conf = m["confidence"]
                    break

            clipped_count = 0
            stats: dict[str, Any] = {"min": None, "max": None, "median": None, "mean": None, "std": None}

            if is_num and num_s.notna().sum() > 0:
                valid_num = num_s.dropna()
                stats["min"] = round(float(valid_num.min()), 2)
                stats["max"] = round(float(valid_num.max()), 2)
                stats["median"] = round(float(valid_num.median()), 2)
                stats["mean"] = round(float(valid_num.mean()), 2)
                stats["std"] = round(float(valid_num.std()), 2) if len(valid_num) > 1 else 0.0

                # Outlier detection (values beyond 3 IQRs)
                q25, q75 = valid_num.quantile(0.25), valid_num.quantile(0.75)
                iqr = q75 - q25
                if iqr > 0:
                    outliers = valid_num[(valid_num < q25 - 3 * iqr) | (valid_num > q75 + 3 * iqr)]
                    outlier_counts += len(outliers)

                # Check bounds if mapped
                if mapped_feat:
                    spec = FEATURE_SPECS[mapped_feat]
                    out_of_bounds = (valid_num < spec.min_clip) | (valid_num > spec.max_clip)
                    clipped_count = int(out_of_bounds.sum())

            # Track completeness for mapped features
            if mapped_feat:
                non_null_in_col = len(prof_df) - null_count
                total_non_null_mapped += non_null_in_col
                total_possible_mapped += len(prof_df)

            # Health status classification
            if mapped_feat and clipped_count > 0:
                health_status = "Imputed/Clipped"
            elif null_pct >= 0.30:
                health_status = "High Nulls"
            elif null_pct >= 0.05:
                health_status = "Moderate Nulls"
            else:
                health_status = "Clean"

            col_health_list.append({
                "column_name": col,
                "mapped_to": mapped_feat,
                "mapping_confidence": conf,
                "detected_type": detected_type,
                "total_count": len(prof_df),
                "null_count": null_count,
                "null_pct": null_pct,
                "unique_count": int(raw_s.nunique()),
                "min": stats["min"],
                "max": stats["max"],
                "median": stats["median"],
                "mean": stats["mean"],
                "std": stats["std"],
                "clipped_count": clipped_count,
                "health_status": health_status,
            })

        # Imputed features list (features in model that were NOT mapped)
        mapped_feature_names = set(mapped_feats.keys())
        imputed_features = [f for f in MODEL_FEATURES if f not in mapped_feature_names]

        for missing_feat in imputed_features:
            spec = FEATURE_SPECS[missing_feat]
            val = spec.fallback_default
            notices.append({
                "feature": missing_feat,
                "reason": "column_missing",
                "count": total_rows,
                "value_used": val,
                "message": f"Feature '{spec.label}' was missing from the upload and will be imputed with default {val} {spec.unit}."
            })

        # Duplicate ratios
        duplicate_rows = int(prof_df.duplicated().sum())
        duplicate_ratio = duplicate_rows / len(prof_df) if len(prof_df) > 0 else 0.0

        # Completeness ratio
        overall_completeness = (
            total_non_null_mapped / total_possible_mapped
            if total_possible_mapped > 0
            else 0.0
        )

        outlier_ratio = min(1.0, outlier_counts / (len(prof_df) * max(1, len(mapped_feats))))

        # Weighted mapping coverage: sum(confidence * weight)
        weighted_coverage = sum(
            FEATURE_SPECS[m["model_feature"]].weight * m["confidence"]
            for m in mappings
        )

        # Deterministic Quality Score Formula
        quality_score = int(round(100 * (
            0.35 * overall_completeness
            + 0.30 * min(1.0, weighted_coverage)
            + 0.20 * (1.0 - outlier_ratio)
            + 0.15 * (1.0 - duplicate_ratio)
        )))
        quality_score = max(0, min(100, quality_score))

        # Quality Label
        if quality_score >= 90:
            quality_label = "Excellent"
        elif quality_score >= 75:
            quality_label = "Good"
        elif quality_score >= 50:
            quality_label = "Fair"
        else:
            quality_label = "Poor"

        # Scoring Confidence
        if len(imputed_features) <= 1 and overall_completeness >= 0.95:
            scoring_confidence = "High"
        elif len(imputed_features) <= 3:
            scoring_confidence = "Medium"
        else:
            scoring_confidence = "Low"

        # Unit Sanity Check (e.g. seconds vs minutes)
        if "avg_session_minutes" in mapped_feats:
            col_name = mapped_feats["avg_session_minutes"]
            s = numeric_dict.get(col_name)
            if s is not None and s.dropna().median() > 300:
                warnings.append(
                    f"Unit anomaly detected in '{col_name}': median value is {s.dropna().median():.1f}, "
                    "which appears to be in seconds rather than minutes. We recommend converting to minutes."
                )

        # 10-row preview for user inspection
        preview_rows = df.head(10).replace({np.nan: None}).to_dict(orient="records")

        return {
            "upload_id": upload_id,
            "filename": filename,
            "encoding": encoding,
            "delimiter": delimiter,
            "total_rows": total_rows,
            "total_columns": total_columns,
            "quality_score": quality_score,
            "quality_label": quality_label,
            "scoring_confidence": scoring_confidence,
            "overall_completeness": round(overall_completeness, 4),
            "mapped_features_count": len(mapped_feats),
            "model_features_total": len(MODEL_FEATURES),
            "imputed_features": imputed_features,
            "mappings": mappings,
            "unmapped_columns": unmapped_cols,
            "notices": notices,
            "warnings": warnings,
            "columns": col_health_list,
            "target_column": target_col,
            "historical_retention_rate": historical_retention_rate,
            "profiled_on_sample": profiled_on_sample,
            "data_preview": preview_rows,
        }

    @classmethod
    def _parse_historical_target(cls, s: pd.Series, col_name: str) -> Optional[float]:
        """Infers binary retention probability from target column."""
        clean = s.dropna().astype(str).str.strip().str.lower()
        if len(clean) == 0:
            return None

        is_churn_col = any(normalize_col_name(col_name) == normalize_col_name(a) for a in TARGET_ALIASES["churn"])

        ones = clean.isin(["1", "true", "yes", "y", "retained", "active"]).sum()
        zeros = clean.isin(["0", "false", "no", "n", "churn", "churned", "canceled", "cancelled"]).sum()

        total = ones + zeros
        if total == 0:
            return None

        rate = ones / total
        return (1.0 - rate) if is_churn_col else rate

    @classmethod
    def prepare_and_clean_data(
        cls,
        df: pd.DataFrame,
        mapped_features: dict[str, str],
        batch_id: int,
    ) -> tuple[pd.DataFrame, list[str], list[list[str]], list[str]]:
        """
        Stage 4b: Clean, clip, impute, and prepare feature matrix for model scoring.
        Returns:
            - features_df: DataFrame with exact 7 model features
            - customer_ids: list of customer IDs
            - row_imputed_flags: list of list[str] (which features were imputed per row)
            - data_quality_flags: list of str ("ok", "partial", "heavy_imputation")
        """
        n_rows = len(df)
        clean_features: dict[str, np.ndarray] = {}
        row_imputations = [[] for _ in range(n_rows)]

        for feat in MODEL_FEATURES:
            spec = FEATURE_SPECS[feat]
            user_col = mapped_features.get(feat)

            if user_col and user_col in df.columns:
                num_s, _ = IngestionEngine.parse_locale_numeric(df[user_col])
                arr = num_s.to_numpy(dtype=float, copy=True)

                # Clip out of bounds
                arr_clipped = np.clip(arr, spec.min_clip, spec.max_clip)

                # Find missing indices and impute with dataset median or training fallback
                valid_mask = ~np.isnan(arr_clipped)
                if np.any(valid_mask):
                    col_impute_val = float(np.nanmedian(arr_clipped))
                else:
                    col_impute_val = spec.fallback_default

                nan_indices = np.where(~valid_mask)[0]
                for idx in nan_indices:
                    row_imputations[idx].append(feat)

                arr_clipped[nan_indices] = col_impute_val
                if spec.is_integer:
                    arr_clipped = np.round(arr_clipped)

                clean_features[feat] = arr_clipped
            else:
                # Column completely missing: fill with training default
                default_val = spec.fallback_default
                clean_features[feat] = np.full(n_rows, default_val, dtype=float)
                for idx in range(n_rows):
                    row_imputations[idx].append(feat)

        features_df = pd.DataFrame(clean_features, columns=MODEL_FEATURES)

        # Row quality flags
        data_quality_flags = []
        for imp_list in row_imputations:
            if len(imp_list) == 0:
                data_quality_flags.append("ok")
            elif len(imp_list) <= 3:
                data_quality_flags.append("partial")
            else:
                data_quality_flags.append("heavy_imputation")

        return features_df, row_imputations, data_quality_flags
