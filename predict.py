
"""Validated predictions for the mobile app retention project."""

from pathlib import Path
from numbers import Real

import joblib
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "xgboost_retention_model.joblib"

FEATURES = [
    "age",
    "session_frequency",
    "avg_session_minutes",
    "days_since_install",
    "notifications_clicked",
    "crashes",
    "purchases",
]

INTEGER_FEATURES = [
    "age",
    "session_frequency",
    "days_since_install",
    "notifications_clicked",
    "crashes",
    "purchases",
]

# Load once per Streamlit process and reuse the model.
@st.cache_resource
def load_model():
    """Load the trained model from disk."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_PATH}. "
            "Run train_model.py first."
        )
    return joblib.load(MODEL_PATH)


def predict_retention(user_data):
    """Return predicted class and probability of retention."""
    if not isinstance(user_data, dict):
        raise ValueError("Input must be a dictionary of user features.")

    missing = [feature for feature in FEATURES if feature not in user_data]
    extra = [feature for feature in user_data if feature not in FEATURES]

    if missing:
        raise ValueError(
            "Missing required feature(s): " + ", ".join(missing)
        )

    if extra:
        raise ValueError(
            "Unexpected feature(s): " + ", ".join(extra)
        )

    validated = {}

    for feature in FEATURES:
        value = user_data[feature]

        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{feature} must be a numeric value.")

        if pd.isna(value):
            raise ValueError(f"{feature} cannot be missing.")

        if value < 0:
            raise ValueError(f"{feature} cannot be negative.")

        if feature in INTEGER_FEATURES and not float(value).is_integer():
            raise ValueError(f"{feature} must be a whole number.")

        validated[feature] = value

    if not 18 <= validated["age"] <= 100:
        raise ValueError("Age must be between 18 and 100.")

    if not 1 <= validated["days_since_install"] <= 3650:
        raise ValueError("Days since installation must be between 1 and 3650.")

    if validated["session_frequency"] > 100:
        raise ValueError("Session frequency cannot exceed 100.")

    if validated["avg_session_minutes"] > 1440:
        raise ValueError("Average session duration cannot exceed 1440 minutes.")

    if validated["notifications_clicked"] > 1000:
        raise ValueError("Notifications clicked cannot exceed 1000.")

    if validated["crashes"] > 1000:
        raise ValueError("App crashes cannot exceed 1000.")

    if validated["purchases"] > 1000:
        raise ValueError("Purchases cannot exceed 1000.")

    input_df = pd.DataFrame(
        [[validated[feature] for feature in FEATURES]],
        columns=FEATURES,
    )

    model = load_model()
    prediction = int(model.predict(input_df)[0])
    probability = float(model.predict_proba(input_df)[0][1])

    return prediction, probability


if __name__ == "__main__":
    sample_user = {
        "age": 22,
        "session_frequency": 10,
        "avg_session_minutes": 25.0,
        "days_since_install": 14,
        "notifications_clicked": 8,
        "crashes": 0,
        "purchases": 2,
    }

    prediction, probability = predict_retention(sample_user)

    print("\nMOBILE APP RETENTION PREDICTION")
    print("-" * 35)
    print(f"Predicted class: {prediction}")
    print(
        "Result:",
        "Likely to be retained"
        if prediction == 1
        else "At risk of not being retained",
    )
    print(f"Predicted retention probability: {probability:.2%}")
    print("\nNote: This is a demonstration using synthetic data.")
