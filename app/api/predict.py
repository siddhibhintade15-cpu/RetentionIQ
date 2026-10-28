"""
app/api/predict.py
------------------
Single-user prediction endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.db import insert_customer
from app.schemas import PredictionResponse, UserFeatures
from app.services.model_service import model_service

router = APIRouter(prefix="/api/predict", tags=["Prediction"])


@router.post("/", response_model=PredictionResponse, summary="Predict retention for a single user")
def predict_single(body: UserFeatures, save: bool = True) -> PredictionResponse:
    """
    Run the XGBoost retention model on a single user's feature vector.

    - `save=true` (default): persists the result to the customer history DB.
    - Returns prediction class (0/1), probability, and risk level.

    **Synthetic data notice:** This model was trained on synthetic data and is
    not validated on real customer populations.
    """
    features = body.to_feature_dict()
    result = model_service.predict(features)

    customer_db_id: int | None = None
    if save:
        customer_db_id = insert_customer(
            features=features,
            prediction=result["prediction"],
            probability=result["probability"],
            risk_lv=result["risk_level"],
            source="single",
        )

    return PredictionResponse(
        prediction=result["prediction"],
        probability=result["probability"],
        risk_level=result["risk_level"],
        customer_db_id=customer_db_id,
    )
