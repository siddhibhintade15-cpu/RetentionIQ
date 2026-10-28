"""
app/schemas.py
--------------
Pydantic v2 schemas for request validation and response serialisation.
All schemas include field-level documentation visible in /docs.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Feature bounds — kept in sync with predict.py validation logic
# ---------------------------------------------------------------------------

class UserFeatures(BaseModel):
    """Single user's feature vector for the retention model."""

    age: int = Field(
        ..., ge=18, le=100,
        description="User age in years (18–100).",
        examples=[28]
    )
    session_frequency: int = Field(
        ..., ge=0, le=100,
        description="Sessions per week (0–100).",
        examples=[7]
    )
    avg_session_minutes: float = Field(
        ..., ge=0.0, le=1440.0,
        description="Average session duration in minutes (0–1440).",
        examples=[22.5]
    )
    days_since_install: int = Field(
        ..., ge=1, le=3650,
        description="Days since the app was installed (1–3650).",
        examples=[30]
    )
    notifications_clicked: int = Field(
        ..., ge=0, le=1000,
        description="Total notifications clicked (0–1000).",
        examples=[12]
    )
    crashes: int = Field(
        ..., ge=0, le=1000,
        description="Number of app crashes experienced (0–1000).",
        examples=[0]
    )
    purchases: int = Field(
        ..., ge=0, le=1000,
        description="In-app purchases made (0–1000).",
        examples=[1]
    )

    def to_feature_dict(self) -> dict[str, float]:
        """Return a plain dict suitable for model_service.predict()."""
        return {
            "age": float(self.age),
            "session_frequency": float(self.session_frequency),
            "avg_session_minutes": float(self.avg_session_minutes),
            "days_since_install": float(self.days_since_install),
            "notifications_clicked": float(self.notifications_clicked),
            "crashes": float(self.crashes),
            "purchases": float(self.purchases),
        }


# ---------------------------------------------------------------------------
# Prediction response
# ---------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    """Response for a single user prediction."""
    prediction: int = Field(..., description="0 = not retained, 1 = retained.")
    probability: float = Field(..., description="Probability of being retained (0–1).")
    risk_level: str = Field(..., description="High / Medium / Low risk tier.")
    customer_db_id: Optional[int] = Field(None, description="DB row id if saved to history.")
    synthetic_data_notice: str = Field(
        default="Synthetic data: demonstration only, not validated on real customers.",
        description="Mandatory disclosure."
    )


# ---------------------------------------------------------------------------
# Explanation response
# ---------------------------------------------------------------------------

class LocalExplanationResponse(BaseModel):
    """SHAP waterfall data for a single prediction."""
    contribs: dict[str, float] = Field(..., description="Per-feature SHAP contributions.")
    bias: float = Field(..., description="Base value (model intercept in log-odds space).")
    raw_margin: float = Field(..., description="Sum of contributions + bias.")
    probability: float = Field(..., description="Retention probability (sigmoid of raw_margin).")
    plain_english: str = Field(..., description="Plain-language explanation of the prediction.")
    actions: list[dict[str, str]] = Field(default_factory=list, description="Recommended actions.")
    synthetic_data_notice: str = Field(
        default="Synthetic data: demonstration only, not validated on real customers."
    )


class GlobalExplanationResponse(BaseModel):
    """Global feature importance and SHAP summary."""
    mean_abs_shap: dict[str, float]
    weight: dict[str, float]
    gain: dict[str, float]
    cover: dict[str, float]
    all_shap_values: dict[str, list[float]]
    all_feature_values: dict[str, list[float]]
    n_samples: int
    note: str = Field(
        default=(
            "Gain measures the average improvement in accuracy per feature split. "
            "Weight counts how often a feature is used in splits. "
            "Mean |SHAP| measures the average magnitude of a feature's contribution "
            "to individual predictions. These can differ because gain/weight are "
            "tree-structure metrics while SHAP reflects actual prediction impact."
        )
    )
    synthetic_data_notice: str = Field(
        default="Synthetic data: demonstration only, not validated on real customers."
    )


class WhatIfResponse(BaseModel):
    """Response for the what-if optimisation endpoint."""
    feasible: bool
    already_low_risk: bool = False
    current_probability: float
    suggestions: list[dict[str, Any]]
    best: Optional[dict[str, Any]] = None
    message: Optional[str] = None
    synthetic_data_notice: str = Field(
        default="Synthetic data: demonstration only, not validated on real customers."
    )


# ---------------------------------------------------------------------------
# Batch analysis & Fail-Check Validation
# ---------------------------------------------------------------------------

class RowValidationError(BaseModel):
    """Detailed error for a single row or cell during batch CSV validation."""
    row_index: int = Field(..., description="1-based row number in the CSV.")
    customer_id: Optional[str] = Field(None, description="Customer identifier if provided.")
    column: str = Field(..., description="Name of the offending column.")
    invalid_value: Any = Field(..., description="The value that failed validation.")
    constraint: str = Field(..., description="The constraint or rule that was violated.")
    message: str = Field(..., description="Human-readable error description.")
    remediation: Optional[str] = Field(None, description="Actionable tip to fix the error.")


class BatchValidationReport(BaseModel):
    """Pre-flight diagnostic report for CSV validation."""
    filename: str
    total_rows: int
    valid_rows: int
    error_rows: int
    is_valid: bool
    errors: list[RowValidationError] = Field(default_factory=list)
    missing_columns: list[str] = Field(default_factory=list)
    unexpected_columns: list[str] = Field(default_factory=list)


class BatchRowResult(BaseModel):
    """Result for one row of a batch prediction."""
    row_index: int
    customer_id: Optional[str] = None
    ok: bool
    prediction: Optional[int] = None
    probability: Optional[float] = None
    risk_level: Optional[str] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    """Response for a completed batch prediction run."""
    batch_id: int
    filename: str
    total_rows: int
    valid_rows: int
    error_rows: int
    results: list[BatchRowResult]
    errors: list[RowValidationError] = Field(default_factory=list)
    synthetic_data_notice: str = Field(
        default="Synthetic data: demonstration only, not validated on real customers."
    )


# ---------------------------------------------------------------------------
# Dynamic Resilient Ingestion & Profiling Schemas
# ---------------------------------------------------------------------------

class MappingSuggestion(BaseModel):
    """Mapping recommendation between an uploaded column and a model feature."""
    user_column: str
    model_feature: str
    confidence: float
    method: Literal["exact", "alias", "fuzzy", "value_based", "user_override"]
    status: Literal["auto", "suggested", "overridden"]


class ColumnHealth(BaseModel):
    """Detailed column profile and health metrics."""
    column_name: str
    mapped_to: Optional[str] = None
    mapping_confidence: Optional[float] = None
    detected_type: Literal["Numeric", "Categorical", "Datetime", "Identifier", "Boolean"]
    total_count: int
    null_count: int
    null_pct: float
    unique_count: int
    min: Optional[float] = None
    max: Optional[float] = None
    median: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    clipped_count: int = 0
    health_status: str


class ImputationNotice(BaseModel):
    """Diagnostic disclosure of any column or cell-level imputation."""
    feature: str
    reason: Literal["column_missing", "cells_missing", "clipped", "unit_converted"]
    count: int
    value_used: Optional[float] = None
    message: str


class DatasetHealthReport(BaseModel):
    """Comprehensive dataset health and column mapping report."""
    upload_id: str
    filename: str
    encoding: str
    delimiter: str
    total_rows: int
    total_columns: int
    quality_score: int
    quality_label: str
    scoring_confidence: Literal["High", "Medium", "Low"]
    overall_completeness: float
    mapped_features_count: int
    model_features_total: int = 7
    imputed_features: list[str] = Field(default_factory=list)
    mappings: list[MappingSuggestion] = Field(default_factory=list)
    unmapped_columns: list[str] = Field(default_factory=list)
    notices: list[ImputationNotice] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    columns: list[ColumnHealth] = Field(default_factory=list)
    target_column: Optional[str] = None
    historical_retention_rate: Optional[float] = None
    profiled_on_sample: bool = False
    data_preview: list[dict[str, Any]] = Field(default_factory=list)


class RemapRequest(BaseModel):
    """Request to update column mappings without re-uploading file."""
    upload_id: str
    overrides: dict[str, Optional[str]]


class DynamicProcessRequest(BaseModel):
    """Request to execute dynamic scoring on staged dataset."""
    upload_id: str
    overrides: Optional[dict[str, Optional[str]]] = None
    options: Optional[dict[str, Any]] = None


class DynamicProcessResponse(BaseModel):
    """Result summary of dynamic batch scoring."""
    batch_id: int
    filename: str
    total_rows: int
    quality_score: int
    quality_label: str
    scoring_confidence: str
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    avg_retention_probability: float
    results: list[dict[str, Any]]
    export_url: str
    synthetic_data_notice: str = Field(
        default="Synthetic data: demonstration only, not validated on real customers."
    )


# ---------------------------------------------------------------------------
# Customer list / detail
# ---------------------------------------------------------------------------

class CustomerRecord(BaseModel):
    """A customer record from the history database."""
    id: int
    created_at: str
    customer_id: Optional[str] = None
    features: dict[str, float]
    prediction: int
    probability: float
    risk_level: str
    source: str
    batch_id: Optional[int] = None


class CustomerListResponse(BaseModel):
    """Paginated list of customer records."""
    items: list[CustomerRecord]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Analysis history
# ---------------------------------------------------------------------------

class AnalysisRecord(BaseModel):
    """Saved analysis snapshot."""
    id: int
    created_at: str
    name: str
    summary: dict[str, Any]


# ---------------------------------------------------------------------------
# Meta / health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    model_loaded: bool
    version: str = "1.0.0"


class MetaResponse(BaseModel):
    """Model metadata response."""
    model_info: dict[str, Any]
    metrics: dict[str, Any]
    synthetic_data_notice: str = Field(
        default="Synthetic data: demonstration only, not validated on real customers."
    )
