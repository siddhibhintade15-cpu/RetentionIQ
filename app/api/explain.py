"""
app/api/explain.py
------------------
Explainability endpoints: local SHAP, global importance, what-if, PDP.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import (
    GlobalExplanationResponse,
    LocalExplanationResponse,
    UserFeatures,
    WhatIfResponse,
)
from app.services.explain_service import (
    plain_english_summary,
    recommended_actions,
    suggest_low_risk,
)
from app.services.model_service import model_service

router = APIRouter(prefix="/api/explain", tags=["Explainability"])


@router.post(
    "/local",
    response_model=LocalExplanationResponse,
    summary="Local SHAP explanation for a single prediction",
)
def local_explanation(body: UserFeatures) -> LocalExplanationResponse:
    """
    Compute per-feature SHAP contributions for a single user using
    XGBoost's native `pred_contribs=True`.

    The contributions plus the bias reconstruct the model's exact
    log-odds output: `sigmoid(sum(contribs) + bias) == probability`.

    Returns a waterfall-ready payload with plain-English summary and
    recommended retention actions.
    """
    features = body.to_feature_dict()
    contribs_result = model_service.contributions(features)

    summary = plain_english_summary(
        contribs_result["contribs"],
        features,
        contribs_result["probability"],
    )
    actions = recommended_actions(contribs_result["contribs"])

    return LocalExplanationResponse(
        contribs=contribs_result["contribs"],
        bias=contribs_result["bias"],
        raw_margin=contribs_result["raw_margin"],
        probability=contribs_result["probability"],
        plain_english=summary,
        actions=actions,
    )


@router.get(
    "/global",
    response_model=GlobalExplanationResponse,
    summary="Global feature importance and mean |SHAP|",
)
def global_explanation() -> GlobalExplanationResponse:
    """
    Return global feature importance (gain, weight, cover) and mean |SHAP|
    over a 500-row sample of the dataset.

    Results are cached on startup for fast responses.

    **Why gain and weight can differ:**
    Gain measures average accuracy improvement per split; weight counts how
    often a feature is used. A feature used rarely but at critical splits
    will score high on gain but low on weight. Mean |SHAP| reflects the
    actual average impact on individual predictions.
    """
    data = model_service.global_contributions()
    return GlobalExplanationResponse(**data)


@router.post(
    "/whatif",
    response_model=WhatIfResponse,
    summary="What-if: smallest change to reach Low Risk",
)
def what_if(body: UserFeatures) -> WhatIfResponse:
    """
    Find the smallest realistic single-feature change that moves a user
    from their current risk level to Low Risk (retention probability ≥ 70%).

    Useful for the live simulator slider suggestions.
    """
    features = body.to_feature_dict()
    result = suggest_low_risk(features)
    return WhatIfResponse(**result)


@router.get(
    "/pdp/{feature}",
    summary="Partial dependence plot data for one feature",
)
def partial_dependence(
    feature: str,
    n_points: int = Query(default=40, ge=10, le=100),
) -> dict:
    """
    Sweep `feature` across its 5th–95th percentile range while holding
    all other features at their median. Returns x/y pairs for a PDP chart.
    """
    from app.services.model_service import FEATURES
    if feature not in FEATURES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown feature: {feature}. Valid: {FEATURES}")
    result = model_service.partial_dependence(feature, n_points=n_points)
    result["synthetic_data_notice"] = (
        "Synthetic data: demonstration only, not validated on real customers."
    )
    return result
