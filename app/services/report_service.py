"""
app/services/report_service.py
------------------------------
Generates business summary PDF reports using ReportLab and formatted
CSV exports for customer analysis cohorts with synthetic data disclosures.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = PROJECT_ROOT / "reports" / "metrics.json"

SYNTHETIC_DATA_DISCLOSURE = (
    "Synthetic data: demonstration only, not validated on real customers."
)


def load_metrics() -> dict[str, Any]:
    """Read performance metrics from reports/metrics.json at runtime."""
    if METRICS_PATH.exists():
        with open(METRICS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_pdf_report(
    metrics: dict[str, Any],
    stats: dict[str, Any],
    top_at_risk: list[dict[str, Any]],
) -> bytes:
    """
    Generate an executive PDF summary with KPI cards, model metrics,
    top at-risk users, and ethical / synthetic data disclosures.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError("ReportLab is not installed or available.") from exc

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=6,
        textColor=colors.HexColor("#4F46E5"),
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=14,
        spaceAfter=4,
        textColor=colors.HexColor("#1E1B4B"),
    )
    body_style = styles["BodyText"]
    warning_style = ParagraphStyle(
        "Warning",
        parent=styles["BodyText"],
        backColor=colors.HexColor("#FEF3C7"),
        borderColor=colors.HexColor("#F59E0B"),
        borderWidth=1,
        borderPadding=8,
        textColor=colors.HexColor("#92400E"),
        spaceAfter=10,
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("RetentionIQ — Executive Retention Report", title_style))
    story.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | Model: XGBoost Retention Classifier",
            body_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4F46E5")))
    story.append(Spacer(1, 0.3 * cm))

    # Mandatory synthetic data disclaimer
    story.append(
        Paragraph(
            "<b>NOTICE:</b> This report is generated from demonstration software trained "
            "exclusively on <b>SYNTHETIC data</b>. It has not been validated on real customer "
            "cohorts and must not be used as the sole basis for business decisions.",
            warning_style,
        )
    )

    # Risk KPI Summary
    story.append(Paragraph("Customer Retention & Churn Risk Overview", h2_style))
    avg_p = stats.get("avg_retention_probability")
    avg_p_str = f"{avg_p:.1%}" if avg_p is not None else "N/A"

    kpi_data = [
        ["Metric", "Value"],
        ["Total Customers Scored", str(stats.get("total_customers", 0))],
        ["High Risk (Retention < 40%)", str(stats.get("high_risk", 0))],
        ["Medium Risk (40% - 70%)", str(stats.get("medium_risk", 0))],
        ["Low Risk (Retention ≥ 70%)", str(stats.get("low_risk", 0))],
        ["Average Retention Probability", avg_p_str],
    ]
    kpi_table = Table(kpi_data, colWidths=[10 * cm, 6 * cm])
    kpi_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3FF")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E7FF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(kpi_table)
    story.append(Spacer(1, 0.3 * cm))

    # Model Performance Validation (from reports/metrics.json)
    story.append(Paragraph("Model Evaluation Metrics (Test Set, N=600)", h2_style))
    if metrics:
        metrics_data = [
            ["Metric", "Score / Specification"],
            ["Test Accuracy", f"{metrics.get('xgboost_accuracy', 0):.1%}"],
            ["Test Precision", f"{metrics.get('xgboost_precision', 0):.1%}"],
            ["Test Recall", f"{metrics.get('xgboost_recall', 0):.1%}"],
            ["Test F1 Score", f"{metrics.get('xgboost_f1_score', 0):.1%}"],
            ["Dataset Rows", str(metrics.get("dataset_rows", "3,000"))],
            ["Dataset Provenance", metrics.get("dataset_type", "Synthetic demonstration")],
        ]
        cfg = metrics.get("selected_configuration", {})
        if cfg:
            metrics_data.append(["Hyperparameters", f"n_estimators={cfg.get('n_estimators')}, max_depth={cfg.get('max_depth')}, lr={cfg.get('learning_rate')}"])

        m_table = Table(metrics_data, colWidths=[10 * cm, 6 * cm])
        m_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7C3AED")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3FF")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E7FF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(m_table)
    story.append(Spacer(1, 0.3 * cm))

    # Top At-Risk Cohort Table
    if top_at_risk:
        story.append(Paragraph("Priority At-Risk Customers (Immediate Attention)", h2_style))
        risk_rows = [["ID", "Customer ID", "Probability", "Risk Tier", "Crashes", "Sessions/wk"]]
        for c in top_at_risk[:10]:
            f = c.get("features", {})
            risk_rows.append([
                str(c.get("id", "")),
                str(c.get("customer_id") or "—"),
                f"{c.get('probability', 0):.1%}",
                c.get("risk_level", ""),
                str(int(f.get("crashes", 0))),
                str(int(f.get("session_frequency", 0))),
            ])
        r_table = Table(risk_rows, colWidths=[2 * cm, 4 * cm, 3 * cm, 3 * cm, 2.5 * cm, 2.5 * cm])
        r_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DC2626")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FEF2F2")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(r_table)
        story.append(Spacer(1, 0.3 * cm))

    # Limitations & Academic Fairness Section
    story.append(Paragraph("System Limitations & Ethical Caveats", h2_style))
    limitations = [
        "<b>Synthetic Data Provenance:</b> Generated via random probabilistic simulation. Behavioural signals do not represent real-world customer usage.",
        "<b>Model Error Rate:</b> Test accuracy of 69.7% entails an approximate 30% error margin. Predictions must be verified by customer success staff.",
        "<b>Fairness & Demographic Variables:</b> The 'age' variable is included for academic demonstration. Demographic attributes require strict bias auditing prior to commercial use.",
        "<b>Single-Snapshot Limitation:</b> The model classifies static metrics; it does not model longitudinal retention survival curves or user lifetime value (LTV).",
        "<b>Single-User Database:</b> Local SQLite database is designed for demonstration and developer testing; it is not multi-tenant production storage.",
    ]
    for lim in limitations:
        story.append(Paragraph(f"• {lim}", body_style))
        story.append(Spacer(1, 0.15 * cm))

    doc.build(story)
    return buf.getvalue()


def generate_customers_csv(customers: list[dict[str, Any]]) -> str:
    """Format customer list as CSV with synthetic data notice header."""
    output = io.StringIO()
    output.write(f"# {SYNTHETIC_DATA_DISCLOSURE}\n")
    writer = csv.writer(output)
    writer.writerow([
        "id", "created_at", "customer_id",
        "age", "session_frequency", "avg_session_minutes",
        "days_since_install", "notifications_clicked", "crashes", "purchases",
        "prediction", "probability", "risk_level", "source", "batch_id",
    ])
    for item in customers:
        feats = item.get("features", {})
        writer.writerow([
            item.get("id"),
            item.get("created_at"),
            item.get("customer_id", ""),
            feats.get("age", ""),
            feats.get("session_frequency", ""),
            feats.get("avg_session_minutes", ""),
            feats.get("days_since_install", ""),
            feats.get("notifications_clicked", ""),
            feats.get("crashes", ""),
            feats.get("purchases", ""),
            item.get("prediction"),
            round(item.get("probability", 0.0), 4),
            item.get("risk_level"),
            item.get("source"),
            item.get("batch_id", ""),
        ])
    return output.getvalue()
