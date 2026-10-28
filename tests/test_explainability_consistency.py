"""
tests/test_explainability_consistency.py
----------------------------------------
Strict mathematical verification tests ensuring that XGBoost native
SHAP contributions plus the base value reconstruct the model's raw
log-odds output and predicted probability.

Core formula:
    raw_margin = sum(contribs.values()) + bias
    probability = 1.0 / (1.0 + exp(-raw_margin))
    assert abs(probability - model.predict_proba(x)[1]) < 1e-4
"""

from __future__ import annotations

import math
import pandas as pd
import pytest

from app.services.model_service import FEATURES, model_service
from src.data_preprocessing import load_dataset


@pytest.fixture(scope="module", autouse=True)
def setup_model():
    model_service.load()


def test_shap_reconstruction_single_user():
    user = {
        "age": 28.0,
        "session_frequency": 7.0,
        "avg_session_minutes": 22.5,
        "days_since_install": 30.0,
        "notifications_clicked": 12.0,
        "crashes": 0.0,
        "purchases": 1.0,
    }

    # 1. Prediction via sklearn model wrapper
    pred_result = model_service.predict(user)
    model_prob = pred_result["probability"]

    # 2. Native SHAP contributions via booster
    contrib_result = model_service.contributions(user)
    contribs = contrib_result["contribs"]
    bias = contrib_result["bias"]
    raw_margin = contrib_result["raw_margin"]
    shap_prob = contrib_result["probability"]

    # Check sum of contributions + bias equals raw_margin
    expected_margin = sum(contribs.values()) + bias
    assert abs(raw_margin - expected_margin) < 1e-5

    # Check sigmoid of raw_margin matches probability
    expected_prob = 1.0 / (1.0 + math.exp(-raw_margin))
    assert abs(shap_prob - expected_prob) < 1e-5

    # Check that SHAP probability matches sklearn predict_proba
    assert abs(shap_prob - model_prob) < 1e-4, (
        f"Reconstruction failed: SHAP prob {shap_prob} vs model prob {model_prob}"
    )


def test_shap_reconstruction_across_dataset_sample():
    df = load_dataset()
    sample = df[FEATURES].sample(n=50, random_state=42)

    for idx, row in sample.iterrows():
        feat_dict = {col: float(row[col]) for col in FEATURES}

        # Model output
        model_prob = model_service.predict(feat_dict)["probability"]

        # Native SHAP output
        c_res = model_service.contributions(feat_dict)
        raw_margin = sum(c_res["contribs"].values()) + c_res["bias"]
        shap_prob = 1.0 / (1.0 + math.exp(-raw_margin))

        # Reconstructed probability must match sklearn within 1e-4
        assert abs(shap_prob - model_prob) < 1e-4, (
            f"Row {idx} failed SHAP reconstruction: diff = {abs(shap_prob - model_prob)}"
        )


def test_shap_directional_consistency():
    base_user = {
        "age": 30.0,
        "session_frequency": 5.0,
        "avg_session_minutes": 15.0,
        "days_since_install": 20.0,
        "notifications_clicked": 5.0,
        "crashes": 0.0,
        "purchases": 0.0,
    }

    # User with 5 crashes should have a negative crash contribution
    crashed_user = dict(base_user)
    crashed_user["crashes"] = 5.0

    contribs_crashed = model_service.contributions(crashed_user)["contribs"]
    assert contribs_crashed["crashes"] < 0, (
        f"Expected negative SHAP contribution for 5 crashes, got {contribs_crashed['crashes']}"
    )

    # User with high session frequency should have a positive contribution
    frequent_user = dict(base_user)
    frequent_user["session_frequency"] = 25.0

    contribs_frequent = model_service.contributions(frequent_user)["contribs"]
    assert contribs_frequent["session_frequency"] > 0, (
        f"Expected positive SHAP contribution for 25 sessions/wk, got {contribs_frequent['session_frequency']}"
    )
