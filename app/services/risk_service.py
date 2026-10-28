"""
app/services/risk_service.py
----------------------------
Risk scoring, tier classification, cohort risk distribution analysis,
and actionable retention recommendations based on SHAP feature impacts.
"""

from __future__ import annotations

from typing import Any

# Standard retention risk tier thresholds (retention probability)
# < 0.40: High Churn Risk (retention unlikely without intervention)
# 0.40 - 0.70: Medium Churn Risk (borderline engagement)
# >= 0.70: Low Churn Risk (loyal / habituated user)
RISK_HIGH_THRESHOLD = 0.40
RISK_MEDIUM_THRESHOLD = 0.70

# Semantic styling and metadata for each risk tier
RISK_METADATA = {
    "High": {
        "color": "#DC2626",
        "bg_color": "#FEF2F2",
        "border_color": "#FECACA",
        "badge_class": "high",
        "urgency": "Immediate intervention required",
    },
    "Medium": {
        "color": "#D97706",
        "bg_color": "#FFFBEB",
        "border_color": "#FDE68A",
        "badge_class": "medium",
        "urgency": "Nurture and proactive monitoring",
    },
    "Low": {
        "color": "#059669",
        "bg_color": "#ECFDF5",
        "border_color": "#A7F3D0",
        "badge_class": "low",
        "urgency": "Maintain engagement and delight",
    },
}

# Feature-specific retention playbooks
RECOMMENDED_ACTIONS_PLAYBOOK: dict[str, list[str]] = {
    "crashes": [
        "Prioritise crash fixes in the next sprint — even 1-2 crashes spike churn by up to 40%.",
        "Trigger an in-app apology modal offering bonus credits or customer support contact.",
    ],
    "session_frequency": [
        "Send a personalised re-engagement push notification with a tailored value hook.",
        "Surface a 'Continue where you left off' reminder on next launch.",
        "Introduce a streak or weekly habit challenge to encourage frequent app opens.",
    ],
    "avg_session_minutes": [
        "Recommend quick-win core workflows that provide value in under 2 minutes.",
        "Add micro-achievements and interactive progress indicators to lengthen active sessions.",
    ],
    "notifications_clicked": [
        "Audit notification copy, deliverability, and send-time optimisation (STO).",
        "A/B test richer media (images, action buttons) and personalized notification triggers.",
    ],
    "purchases": [
        "Offer an introductory promotional discount, trial tier, or bonus in-app pack.",
        "Display a frictionless value comparison highlighting benefits of premium membership.",
    ],
    "days_since_install": [
        "Activate a guided onboarding checklist for users in their first critical 14 days.",
        "Send a Day-7 celebration email highlighting user milestones and tips.",
    ],
    "age": [],  # Protected/sensitive demographic attribute: do not generate automated intervention rules
}


def get_risk_level(probability: float) -> str:
    """
    Classify a customer into High, Medium, or Low risk based on retention probability.
    """
    if probability < RISK_HIGH_THRESHOLD:
        return "High"
    if probability < RISK_MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def get_risk_metadata(risk_level: str) -> dict[str, str]:
    """Return presentation metadata for a given risk level."""
    return RISK_METADATA.get(risk_level, RISK_METADATA["Low"])


def get_risk_distribution(probabilities: list[float]) -> dict[str, int]:
    """Compute risk breakdown counts for an array of customer probabilities."""
    counts = {"High": 0, "Medium": 0, "Low": 0}
    for p in probabilities:
        level = get_risk_level(p)
        counts[level] += 1
    return counts


def get_retention_recommendations(
    contribs: dict[str, float], n: int = 3
) -> list[dict[str, str]]:
    """
    Generate the top-N recommended retention actions based on which features
    are exerting the strongest negative pull (pushing toward churn).
    """
    negative_contribs = [(f, c) for f, c in contribs.items() if c < 0]
    negative_contribs.sort(key=lambda x: x[1])  # Most negative impact first

    actions: list[dict[str, str]] = []
    for feat, contrib in negative_contribs[:n]:
        playbook = RECOMMENDED_ACTIONS_PLAYBOOK.get(feat, [])
        for action_text in playbook[:1]:
            actions.append({
                "feature": feat,
                "action": action_text,
                "impact": f"{contrib:+.3f}",
            })
    return actions


def calculate_risk_mix_shift(
    summary_a: dict[str, Any], summary_b: dict[str, Any]
) -> dict[str, Any]:
    """
    Calculate the risk distribution shift and average probability change
    between two analysis snapshots for comparison.
    """
    total_a = summary_a.get("total_customers", 0)
    total_b = summary_b.get("total_customers", 0)

    def _pct(val: int | None, total: int) -> float | None:
        if not total or val is None:
            return None
        return round(val / total * 100, 1)

    high_a = summary_a.get("high_risk", 0)
    high_b = summary_b.get("high_risk", 0)
    pct_high_a = _pct(high_a, total_a)
    pct_high_b = _pct(high_b, total_b)

    prob_a = summary_a.get("avg_retention_probability")
    prob_b = summary_b.get("avg_retention_probability")

    return {
        "total_customers_a": total_a,
        "total_customers_b": total_b,
        "high_risk_pct_a": pct_high_a,
        "high_risk_pct_b": pct_high_b,
        "high_risk_pct_delta": (
            round(pct_high_b - pct_high_a, 1)
            if pct_high_a is not None and pct_high_b is not None
            else None
        ),
        "avg_prob_a": prob_a,
        "avg_prob_b": prob_b,
        "avg_prob_delta": (
            round(prob_b - prob_a, 4)
            if prob_a is not None and prob_b is not None
            else None
        ),
    }
