"""
app/services/explain_service.py
--------------------------------
Provides high-level explainability helpers on top of model_service:
  - Plain-English summary of a local prediction
  - Recommended retention actions based on top risk factors
  - What-if optimisation: smallest feature change to reach Low Risk
  - Global explanation caching (warm-up on startup)
"""

from __future__ import annotations

import math
from typing import Any

from app.services.model_service import FEATURES, RISK_MEDIUM_THRESHOLD, model_service


# ---------------------------------------------------------------------------
# Plain-English sentence templates
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, dict[str, str]] = {
    "crashes": {
        "high_risk":   "{value:.0f} crash(es) is the primary driver pushing this user toward churn.",
        "medium_risk": "{value:.0f} crash(es) is increasing churn risk.",
        "protective":  "Low crash count ({value:.0f}) is helping retain this user.",
    },
    "session_frequency": {
        "high_risk":   "Very low session frequency ({value:.0f}/week) signals disengagement.",
        "medium_risk": "Below-average session frequency ({value:.0f}/week) is a concern.",
        "protective":  "High session frequency ({value:.0f}/week) is a strong retention signal.",
    },
    "avg_session_minutes": {
        "high_risk":   "Short average sessions ({value:.1f} min) indicate low engagement.",
        "medium_risk": "Moderate session length ({value:.1f} min) could be improved.",
        "protective":  "Long average sessions ({value:.1f} min) show strong engagement.",
    },
    "notifications_clicked": {
        "high_risk":   "Very few notifications clicked ({value:.0f}) — low re-engagement.",
        "medium_risk": "Moderate notification engagement ({value:.0f} clicks).",
        "protective":  "Strong notification engagement ({value:.0f} clicks).",
    },
    "purchases": {
        "high_risk":   "No purchases ({value:.0f}) means no monetisation anchor.",
        "medium_risk": "{value:.0f} purchase(s) show some commitment.",
        "protective":  "{value:.0f} purchase(s) indicate strong commitment.",
    },
    "days_since_install": {
        "high_risk":   "Very early user ({value:.0f} days) — still in the critical drop-off window.",
        "medium_risk": "User is {value:.0f} days post-install — still building habits.",
        "protective":  "User has been active for {value:.0f} days — habit formed.",
    },
    "age": {
        "high_risk":   "Age {value:.0f} is associated with slightly lower retention in this dataset.",
        "medium_risk": "Age {value:.0f} is a minor factor in this prediction.",
        "protective":  "Age {value:.0f} is a minor positive factor.",
    },
}

_ACTIONS: dict[str, list[str]] = {
    "crashes": [
        "Prioritise crash fixes in the next release — even 1–2 crashes significantly increase churn.",
        "Add in-app feedback after a crash to show you care about the user experience.",
    ],
    "session_frequency": [
        "Send a personalised re-engagement push notification with a value hook.",
        "Surface a 'Continue where you left off' prompt on next open.",
        "Consider a streak or habit-building mechanic to drive daily opens.",
    ],
    "avg_session_minutes": [
        "Recommend a 'quick win' feature that delivers value in under 2 minutes.",
        "Add a progress indicator or micro-achievement to encourage longer sessions.",
    ],
    "notifications_clicked": [
        "Review your notification copy — are CTAs clear and personalised?",
        "A/B test notification timing and message types for this user segment.",
    ],
    "purchases": [
        "Offer a low-friction first purchase (e.g., trial, starter pack, free credit).",
        "Show a value-comparison screen highlighting what paid users get.",
    ],
    "days_since_install": [
        "Trigger an onboarding re-engagement flow for users who haven't formed a habit yet.",
        "Send a Day-7 or Day-14 check-in email with tips and success stories.",
    ],
    "age": [],  # No specific age-based action (sensitive feature)
}


# ---------------------------------------------------------------------------
# Local explanation helpers
# ---------------------------------------------------------------------------

def plain_english_summary(
    contribs: dict[str, float],
    features: dict[str, float],
    probability: float,
) -> str:
    """
    Produce a 1–3 sentence plain-English explanation of WHY the model
    predicted what it did for a specific user.
    """
    # Sort features by |contribution|, descending
    sorted_feats = sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)
    top = sorted_feats[:3]

    risk_tier = "High" if probability < 0.40 else ("Medium" if probability < 0.70 else "Low")

    parts: list[str] = []
    for feat, contrib in top:
        value = features[feat]
        if contrib < -0.05:    # pushing toward churn
            key = "high_risk"
        elif contrib < 0.05:   # neutral
            key = "medium_risk"
        else:                  # pushing toward retention
            key = "protective"

        template = _TEMPLATES.get(feat, {}).get(key, f"{feat}={value:.2f}.")
        parts.append(template.format(value=value))

    # Introductory sentence
    if risk_tier == "Low":
        intro = f"This user has a {probability:.0%} retention probability (Low Risk). "
    elif risk_tier == "Medium":
        intro = f"This user has a {probability:.0%} retention probability (Medium Risk). "
    else:
        intro = f"This user is at High Risk of churn (retention probability {probability:.0%}). "

    return intro + " ".join(parts)


def recommended_actions(
    contribs: dict[str, float], n: int = 3
) -> list[dict[str, str]]:
    """
    Return the top-N recommended retention actions based on which
    features are most negatively impacting the prediction.
    """
    # Find features with negative (churn-driving) contributions
    negative = [(f, c) for f, c in contribs.items() if c < 0]
    negative.sort(key=lambda x: x[1])  # most negative first

    actions: list[dict[str, str]] = []
    for feat, contrib in negative[:n]:
        for action_text in _ACTIONS.get(feat, [])[:1]:
            actions.append({"feature": feat, "action": action_text, "impact": f"{contrib:+.3f}"})

    return actions


# ---------------------------------------------------------------------------
# What-if optimisation
# ---------------------------------------------------------------------------

def suggest_low_risk(
    features: dict[str, float],
    max_steps: int = 12,
) -> dict[str, Any]:
    """
    Find the smallest realistic single-feature change that moves the user
    from their current probability to Low Risk (>= 0.70).

    Strategy: try increasing each non-negative feature by realistic steps
    (session_frequency, avg_session_minutes, notifications_clicked,
    purchases) and decreasing crashes. Return the suggestion with
    the smallest absolute change that achieves Low Risk.

    Returns a dict with:
      feasible      : bool
      suggestions   : list of {feature, original, proposed, delta, new_prob}
      best          : the single best suggestion (or None)
    """
    current_result = model_service.predict(features)
    current_prob = current_result["probability"]

    if current_prob >= RISK_MEDIUM_THRESHOLD:
        return {
            "feasible": True,
            "already_low_risk": True,
            "current_probability": current_prob,
            "suggestions": [],
            "best": None,
        }

    # Define which features can be realistically nudged and by how much
    feature_steps = {
        "session_frequency": (1, 40),          # increase up to 40
        "avg_session_minutes": (5.0, 120.0),   # increase up to 120 min
        "notifications_clicked": (1, 50),       # increase up to 50
        "purchases": (1, 10),                   # increase up to 10
        "crashes": (-1, None),                  # decrease (negative step)
        "days_since_install": (7, 365),         # increase — more tenure
    }

    suggestions: list[dict[str, Any]] = []

    for feat, (step, max_val) in feature_steps.items():
        if feat not in features:
            continue
        original = features[feat]
        candidate = dict(features)

        if step < 0:
            # Decrease feature (crashes)
            for reduction in range(1, int(original) + 1):
                candidate[feat] = max(0, original - reduction)
                try:
                    result = model_service.predict(candidate)
                    if result["probability"] >= RISK_MEDIUM_THRESHOLD:
                        suggestions.append({
                            "feature": feat,
                            "original": original,
                            "proposed": candidate[feat],
                            "delta": candidate[feat] - original,
                            "new_prob": result["probability"],
                        })
                        break
                except ValueError:
                    pass
        else:
            # Increase feature
            trial_val = original + step
            while (max_val is None or trial_val <= max_val):
                candidate[feat] = trial_val
                try:
                    result = model_service.predict(candidate)
                    if result["probability"] >= RISK_MEDIUM_THRESHOLD:
                        suggestions.append({
                            "feature": feat,
                            "original": original,
                            "proposed": trial_val,
                            "delta": trial_val - original,
                            "new_prob": result["probability"],
                        })
                        break
                except ValueError:
                    pass
                trial_val += step

    if not suggestions:
        return {
            "feasible": False,
            "already_low_risk": False,
            "current_probability": current_prob,
            "suggestions": [],
            "best": None,
            "message": (
                "No single realistic feature change is sufficient. "
                "Multiple improvements are likely needed."
            ),
        }

    # Best = smallest absolute delta
    best = min(suggestions, key=lambda s: abs(s["delta"]))
    return {
        "feasible": True,
        "already_low_risk": False,
        "current_probability": current_prob,
        "suggestions": suggestions,
        "best": best,
    }
