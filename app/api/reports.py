"""
app/api/reports.py
-------------------
PDF and CSV report generation endpoints delegating to report_service.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.db import list_customers, overview_stats
from app.services.report_service import generate_pdf_report, load_metrics

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/pdf", summary="Download PDF business summary report")
def download_pdf() -> StreamingResponse:
    """
    Generate and download an executive PDF summary report including:
    - Current KPI statistics from the database
    - Model metrics loaded dynamically from reports/metrics.json
    - Top at-risk customers
    - Mandatory limitations disclaimer and synthetic data notice
    """
    try:
        metrics = load_metrics()
        stats = overview_stats()
        top_at_risk = list_customers(limit=10, risk_filter="High", sort_by="probability", sort_dir="ASC")
        pdf_bytes = generate_pdf_report(metrics, stats, top_at_risk)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"PDF generation error: {exc}",
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=retentioniq_report_{timestamp}.pdf"},
    )


@router.get("/metrics", summary="Return raw metrics JSON")
def get_metrics() -> dict:
    """Return model metrics from reports/metrics.json with synthetic data disclosure."""
    metrics = load_metrics()
    if not metrics:
        return {"error": "Metrics file not found."}
    metrics["synthetic_data_notice"] = (
        "Synthetic data: demonstration only, not validated on real customers."
    )
    return metrics
