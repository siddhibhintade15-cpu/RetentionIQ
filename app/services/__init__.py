"""
app/services/__init__.py
------------------------
Service layer modules: model_service, explain_service, risk_service, report_service.
"""

from app.services.explain_service import (
    plain_english_summary,
    recommended_actions,
    suggest_low_risk,
)
from app.services.model_service import FEATURES, model_service, risk_level
from app.services.report_service import (
    generate_customers_csv,
    generate_pdf_report,
    load_metrics,
)
from app.services.risk_service import (
    calculate_risk_mix_shift,
    get_retention_recommendations,
    get_risk_distribution,
    get_risk_level,
    get_risk_metadata,
)

__all__ = [
    "model_service",
    "FEATURES",
    "risk_level",
    "plain_english_summary",
    "recommended_actions",
    "suggest_low_risk",
    "get_risk_level",
    "get_risk_metadata",
    "get_risk_distribution",
    "get_retention_recommendations",
    "calculate_risk_mix_shift",
    "generate_pdf_report",
    "generate_customers_csv",
    "load_metrics",
]
