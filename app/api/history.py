"""
app/api/history.py
-------------------
Named analysis history and side-by-side comparison endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.db import get_analysis, list_analyses, overview_stats, save_analysis

router = APIRouter(prefix="/api/history", tags=["History"])


class SaveAnalysisRequest(BaseModel):
    name: str
    snapshot: dict[str, Any] | None = None  # optional additional metadata


@router.post("/", summary="Save a named analysis snapshot")
def save_snapshot(body: SaveAnalysisRequest) -> dict:
    """
    Persist current KPI stats as a named analysis snapshot for later
    comparison. Automatically captures the current DB overview stats.
    """
    snapshot = overview_stats()
    if body.snapshot:
        snapshot.update(body.snapshot)
    analysis_id = save_analysis(body.name, snapshot)
    return {"id": analysis_id, "name": body.name, "summary": snapshot}


@router.get("/", summary="List all saved analyses")
def list_history() -> list[dict]:
    """Return all saved analyses, newest first."""
    return list_analyses()


@router.get("/{analysis_id}", summary="Get a single analysis snapshot")
def get_history(analysis_id: int) -> dict:
    """Fetch a specific analysis snapshot by id."""
    record = get_analysis(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return record


@router.get("/compare/{id_a}/{id_b}", summary="Compare two analysis snapshots")
def compare_analyses(id_a: int, id_b: int) -> dict:
    """
    Side-by-side comparison of two saved analyses.
    Reports the shift in risk mix and average probability between them.
    """
    a = get_analysis(id_a)
    b = get_analysis(id_b)
    if a is None:
        raise HTTPException(status_code=404, detail=f"Analysis {id_a} not found.")
    if b is None:
        raise HTTPException(status_code=404, detail=f"Analysis {id_b} not found.")

    def _risk_pct(s: dict, level: str) -> float | None:
        total = s.get("total_customers", 0)
        if not total:
            return None
        return round(s.get(level, 0) / total * 100, 1)

    summary_a = a["summary"]
    summary_b = b["summary"]

    prob_a = summary_a.get("avg_retention_probability")
    prob_b = summary_b.get("avg_retention_probability")
    prob_delta = (
        round(prob_b - prob_a, 4)
        if prob_a is not None and prob_b is not None
        else None
    )

    return {
        "analysis_a": a,
        "analysis_b": b,
        "comparison": {
            "total_customers_a": summary_a.get("total_customers"),
            "total_customers_b": summary_b.get("total_customers"),
            "high_risk_pct_a": _risk_pct(summary_a, "high_risk"),
            "high_risk_pct_b": _risk_pct(summary_b, "high_risk"),
            "high_risk_pct_delta": (
                round(_risk_pct(summary_b, "high_risk") - _risk_pct(summary_a, "high_risk"), 1)
                if _risk_pct(summary_a, "high_risk") is not None
                and _risk_pct(summary_b, "high_risk") is not None
                else None
            ),
            "avg_prob_a": prob_a,
            "avg_prob_b": prob_b,
            "avg_prob_delta": prob_delta,
        },
    }
