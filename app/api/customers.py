"""
app/api/customers.py
---------------------
Customer history list, detail, and export endpoints.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import io
import csv

from app.db import (
    count_customers,
    get_customer,
    list_customers,
    overview_stats,
)
from app.schemas import CustomerListResponse, CustomerRecord
from app.services.explain_service import (
    plain_english_summary,
    recommended_actions,
)
from app.services.model_service import model_service

router = APIRouter(prefix="/api/customers", tags=["Customers"])


@router.get(
    "/",
    response_model=CustomerListResponse,
    summary="List all scored customers",
)
def list_customers_endpoint(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    risk: Optional[str] = Query(default=None, description="Filter by risk level: High, Medium, Low"),
    search: Optional[str] = Query(default=None, description="Search by customer_id substring"),
    batch_id: Optional[int] = Query(default=None, description="Filter by batch upload id"),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="DESC"),
) -> CustomerListResponse:
    """
    Return a paginated, filterable, sortable list of customers that have
    been scored (individually or via batch upload).
    """
    items = list_customers(
        limit=limit,
        offset=offset,
        risk_filter=risk,
        search=search,
        batch_id=batch_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    total = count_customers(risk_filter=risk, search=search, batch_id=batch_id)
    return CustomerListResponse(
        items=[CustomerRecord(**c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/overview",
    summary="KPI overview statistics",
)
def overview() -> dict:
    """Return KPI counts, risk breakdown, retention histogram, and recent analyses."""
    return overview_stats()


@router.get(
    "/export",
    summary="Export all customers as CSV",
)
def export_customers(
    risk: Optional[str] = None,
    search: Optional[str] = None,
    batch_id: Optional[int] = None,
) -> StreamingResponse:
    """
    Download matching scored customers as a CSV file.
    Includes the mandatory synthetic data notice as a comment header.
    """
    from app.services.report_service import generate_customers_csv
    items = list_customers(limit=10000, offset=0, risk_filter=risk, search=search, batch_id=batch_id)
    csv_text = generate_customers_csv(items)

    return StreamingResponse(
        io.BytesIO(csv_text.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=retentioniq_customers.csv"},
    )


@router.get(
    "/{customer_id}",
    summary="Get a single customer record with SHAP explanation",
)
def get_customer_detail(customer_id: int) -> dict:
    """
    Fetch a customer record by its database id, including SHAP
    waterfall data and recommended retention actions.
    """
    record = get_customer(customer_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Customer not found.")

    # Compute local SHAP explanation
    features = record["features"]
    contribs_result = model_service.contributions(features)
    summary = plain_english_summary(
        contribs_result["contribs"],
        features,
        contribs_result["probability"],
    )
    actions = recommended_actions(contribs_result["contribs"])

    return {
        **record,
        "explanation": {
            "contribs": contribs_result["contribs"],
            "bias": contribs_result["bias"],
            "probability": contribs_result["probability"],
            "plain_english": summary,
            "actions": actions,
        },
        "synthetic_data_notice": (
            "Synthetic data: demonstration only, not validated on real customers."
        ),
    }
