"""
app/api/meta.py
----------------
Model metadata and health check endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.schemas import HealthResponse, MetaResponse
from app.services.model_service import model_service

router = APIRouter(tags=["Meta"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = PROJECT_ROOT / "reports" / "metrics.json"


@router.get("/api/health", response_model=HealthResponse, summary="Health check")
def health() -> HealthResponse:
    """Returns 200 if the app and model are running correctly."""
    try:
        _ = model_service.model  # Will raise if not loaded
        loaded = True
    except RuntimeError:
        loaded = False
    return HealthResponse(model_loaded=loaded)


@router.get("/api/meta", response_model=MetaResponse, summary="Model metadata and metrics")
def meta() -> MetaResponse:
    """
    Return model type, hyperparameters, feature list, and test-set metrics
    loaded from reports/metrics.json.
    """
    metrics: dict = {}
    if METRICS_PATH.exists():
        with open(METRICS_PATH, encoding="utf-8") as f:
            metrics = json.load(f)

    return MetaResponse(
        model_info=model_service.model_info(),
        metrics=metrics,
    )


@router.get("/api/meta/curves", summary="Model evaluation curves (ROC, PR, Calibration)")
def model_curves() -> dict:
    """
    Compute and return ROC curve, Precision-Recall curve, and Calibration
    curve (reliability diagram) on the test split (600 rows).
    """
    import pandas as pd
    from sklearn.calibration import calibration_curve
    from sklearn.metrics import auc, average_precision_score, precision_recall_curve, roc_curve

    from src.data_preprocessing import load_dataset, prepare_data

    # Load dataset & prepare standard stratified 80/20 test split (seed 42)
    df = load_dataset()
    _, X_test, _, y_test = prepare_data(df)

    probs = model_service.model.predict_proba(X_test)[:, 1]

    # 1. ROC Curve
    fpr, tpr, _ = roc_curve(y_test, probs)
    roc_auc = float(auc(fpr, tpr))

    # Downsample points for efficient Chart.js rendering (~30 points)
    step = max(1, len(fpr) // 30)
    fpr_sampled = fpr[::step].tolist() + [float(fpr[-1])]
    tpr_sampled = tpr[::step].tolist() + [float(tpr[-1])]

    # 2. Precision-Recall Curve
    precision, recall, _ = precision_recall_curve(y_test, probs)
    pr_auc = float(average_precision_score(y_test, probs))
    pr_step = max(1, len(precision) // 30)
    prec_sampled = precision[::pr_step].tolist() + [float(precision[-1])]
    rec_sampled = recall[::pr_step].tolist() + [float(recall[-1])]

    # 3. Calibration Curve (10 bins)
    prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=10)

    return {
        "roc": {
            "fpr": [round(x, 4) for x in fpr_sampled],
            "tpr": [round(y, 4) for y in tpr_sampled],
            "auc": round(roc_auc, 3),
        },
        "pr": {
            "recall": [round(r, 4) for r in rec_sampled],
            "precision": [round(p, 4) for p in prec_sampled],
            "auc": round(pr_auc, 3),
            "baseline": round(float(y_test.mean()), 3),
        },
        "calibration": {
            "prob_pred": [round(float(p), 4) for p in prob_pred],
            "prob_true": [round(float(t), 4) for t in prob_true],
        },
        "synthetic_data_notice": "Synthetic data: demonstration only, not validated on real customers.",
    }

