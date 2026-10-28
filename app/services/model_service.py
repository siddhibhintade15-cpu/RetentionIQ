"""
app/services/model_service.py
-----------------------------
Loads the trained XGBoost model once at startup and exposes
prediction + native-SHAP contribution methods.

NOTE: This module intentionally does NOT import predict.py
      (which depends on Streamlit). It re-implements the same
      loading and validation logic in a Streamlit-free way so
      that predict.py remains backward-compatible with the old
      Streamlit app.
"""

from __future__ import annotations

import math
import threading
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

# ---------------------------------------------------------------------------
# Constants — must match predict.py exactly so both files stay in sync
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "xgboost_retention_model.joblib"

FEATURES: list[str] = [
    "age",
    "session_frequency",
    "avg_session_minutes",
    "days_since_install",
    "notifications_clicked",
    "crashes",
    "purchases",
]

# Risk tier thresholds (probability of retention)
RISK_HIGH_THRESHOLD = 0.40    # prob < 0.40 → High risk
RISK_MEDIUM_THRESHOLD = 0.70  # prob < 0.70 → Medium risk
# prob >= 0.70 → Low risk


def risk_level(prob: float) -> str:
    """Convert retention probability to a human-readable risk tier."""
    if prob < RISK_HIGH_THRESHOLD:
        return "High"
    if prob < RISK_MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# Singleton model wrapper
# ---------------------------------------------------------------------------

class ModelService:
    """Thread-safe singleton that holds the loaded model and booster."""

    _instance: "ModelService | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "ModelService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._model = None       # type: ignore[attr-defined]
                    instance._booster = None     # type: ignore[attr-defined]
                    cls._instance = instance
        return cls._instance

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load the model from disk. Called once on FastAPI startup."""
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run train_model.py first."
            )
        self._model = joblib.load(MODEL_PATH)
        self._booster = self._model.get_booster()

    @property
    def model(self):
        """Return the sklearn XGBClassifier, raising if not loaded."""
        if self._model is None:
            raise RuntimeError("ModelService.load() has not been called.")
        return self._model

    @property
    def booster(self) -> xgb.Booster:
        """Return the underlying XGBoost Booster."""
        if self._booster is None:
            raise RuntimeError("ModelService.load() has not been called.")
        return self._booster

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, features: dict[str, float]) -> dict[str, Any]:
        """
        Run a single prediction and return class, probability, risk level.

        Parameters
        ----------
        features : dict mapping feature name → numeric value.
                   Must contain exactly FEATURES keys.

        Returns
        -------
        dict with keys: prediction, probability, risk_level
        """
        df = self._to_dataframe(features)
        prediction = int(self.model.predict(df)[0])
        probability = float(self.model.predict_proba(df)[0][1])
        return {
            "prediction": prediction,
            "probability": probability,
            "risk_level": risk_level(probability),
        }

    # ------------------------------------------------------------------
    # Native SHAP contributions
    # ------------------------------------------------------------------

    def contributions(self, features: dict[str, float]) -> dict[str, Any]:
        """
        Compute per-feature SHAP contributions using XGBoost's native
        pred_contribs=True. The last element is the bias (base value).

        Reconstruction check: sigmoid(sum(contribs)) ≈ predict_proba
        This is guaranteed by tree SHAP and verified in tests.

        Returns
        -------
        dict with keys:
          contribs      : {feature → float}  (7 features)
          bias          : float  (base value / intercept)
          raw_margin    : float  (sum of contribs + bias, i.e. log-odds)
          probability   : float  (sigmoid of raw_margin)
        """
        df = self._to_dataframe(features)
        dmat = xgb.DMatrix(df)
        # Shape: (1, n_features + 1) — last column is the bias
        raw = self.booster.predict(dmat, pred_contribs=True)[0]

        contrib_dict = {feat: float(raw[i]) for i, feat in enumerate(FEATURES)}
        bias = float(raw[-1])
        raw_margin = float(raw.sum())
        probability = 1.0 / (1.0 + math.exp(-raw_margin))

        return {
            "contribs": contrib_dict,
            "bias": bias,
            "raw_margin": raw_margin,
            "probability": probability,
        }

    def global_contributions(self, n_samples: int = 500) -> dict[str, Any]:
        """
        Compute mean |SHAP| over a random sample of the training dataset.
        Also returns feature importance by weight, gain, and cover.

        Results are computed once and cached in this instance.
        """
        # Return cached result if available
        if hasattr(self, "_global_cache") and self._global_cache is not None:
            return self._global_cache

        # Load dataset for SHAP summary
        data_path = PROJECT_ROOT / "data" / "mobile_app_retention.csv"
        df = pd.read_csv(data_path)
        sample_df = df[FEATURES].sample(
            n=min(n_samples, len(df)), random_state=42
        )

        dmat = xgb.DMatrix(sample_df)
        raw_contribs = self.booster.predict(dmat, pred_contribs=True)
        # raw_contribs shape: (n_samples, n_features + 1)
        feature_contribs = raw_contribs[:, :-1]  # drop bias column

        mean_abs_shap = {
            feat: float(np.abs(feature_contribs[:, i]).mean())
            for i, feat in enumerate(FEATURES)
        }

        # Feature importance: weight, gain, cover
        def _importance(imp_type: str) -> dict[str, float]:
            scores = self.booster.get_score(importance_type=imp_type)
            # Normalize so values sum to 1
            total = sum(scores.values()) or 1.0
            return {k: v / total for k, v in scores.items()}

        # All SHAP values per sample (for beeswarm-style summary)
        all_shap_values = {
            feat: feature_contribs[:, i].tolist()
            for i, feat in enumerate(FEATURES)
        }
        all_feature_values = {
            feat: sample_df[feat].tolist()
            for feat in FEATURES
        }

        self._global_cache = {
            "mean_abs_shap": mean_abs_shap,
            "weight": _importance("weight"),
            "gain": _importance("gain"),
            "cover": _importance("cover"),
            "all_shap_values": all_shap_values,
            "all_feature_values": all_feature_values,
            "n_samples": len(sample_df),
        }
        return self._global_cache

    def partial_dependence(
        self, feature: str, n_points: int = 40
    ) -> dict[str, Any]:
        """
        Compute marginal (partial dependence) effect of one feature
        by sweeping it across its range while holding others at median.
        """
        data_path = PROJECT_ROOT / "data" / "mobile_app_retention.csv"
        df = pd.read_csv(data_path)
        medians = df[FEATURES].median()

        feat_min = float(df[feature].quantile(0.05))
        feat_max = float(df[feature].quantile(0.95))
        sweep_values = np.linspace(feat_min, feat_max, n_points)

        rows = []
        for v in sweep_values:
            row = medians.copy()
            row[feature] = v
            rows.append(row)

        sweep_df = pd.DataFrame(rows, columns=FEATURES)
        probs = self.model.predict_proba(sweep_df)[:, 1]

        return {
            "feature": feature,
            "x": sweep_values.tolist(),
            "y": probs.tolist(),
        }

    def feature_importance_raw(self) -> dict[str, Any]:
        """Return raw (un-normalised) importance scores for all types."""
        result = {}
        for imp_type in ("weight", "gain", "cover"):
            scores = self.booster.get_score(importance_type=imp_type)
            # Ensure all features present (features with 0 split won't appear)
            result[imp_type] = {
                feat: float(scores.get(feat, 0.0)) for feat in FEATURES
            }
        return result

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _to_dataframe(self, features: dict[str, float]) -> pd.DataFrame:
        """Build an ordered single-row DataFrame from a feature dict."""
        missing = [f for f in FEATURES if f not in features]
        if missing:
            raise ValueError(f"Missing features: {missing}")
        return pd.DataFrame(
            [[features[f] for f in FEATURES]], columns=FEATURES
        )

    def model_info(self) -> dict[str, Any]:
        """Return a summary of the model for the /api/meta endpoint."""
        params = self.model.get_params()
        return {
            "model_type": type(self.model).__name__,
            "library": "xgboost",
            "library_version": xgb.__version__,
            "features": FEATURES,
            "n_features": len(FEATURES),
            "objective": params.get("objective", "binary:logistic"),
            "n_estimators": params.get("n_estimators"),
            "max_depth": params.get("max_depth"),
            "learning_rate": params.get("learning_rate"),
            "model_path": str(MODEL_PATH),
            "shap_method": "native XGBoost pred_contribs=True",
        }


# ---------------------------------------------------------------------------
# Module-level singleton for convenient import
# ---------------------------------------------------------------------------

model_service = ModelService()
