"""
app/services/feature_spec.py
----------------------------
Single source of truth for RetentionIQ feature contracts, aliases, bounds,
units, quality score weights, and imputation defaults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_FILE = PROJECT_ROOT / "models" / "feature_defaults.json"

# Core model features in exact order
MODEL_FEATURES: list[str] = [
    "age",
    "session_frequency",
    "avg_session_minutes",
    "days_since_install",
    "notifications_clicked",
    "crashes",
    "purchases",
]

IDENTIFIER_ALIASES = [
    "customer_id", "id", "user_id", "userid", "client_id", "uuid",
    "account_id", "email", "handle", "user", "username", "customer"
]

TARGET_ALIASES = {
    "retained": ["retained", "is_retained", "retention", "stayed", "active"],
    "churn": ["churn", "churned", "is_churned", "churn_risk", "uninstalled", "canceled", "cancelled"],
    "generic": ["target", "label", "outcome", "y"]
}


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    label: str
    aliases: tuple[str, ...]
    min_clip: float
    max_clip: float
    dtype: type
    is_integer: bool
    unit: str
    weight: float
    fallback_default: float
    description: str


# Hardcoded fallbacks if models/feature_defaults.json is absent
HARDCODED_FALLBACKS: dict[str, float] = {
    "age": 30.0,
    "session_frequency": 5.0,
    "avg_session_minutes": 15.0,
    "days_since_install": 45.0,
    "notifications_clicked": 3.0,
    "crashes": 0.0,
    "purchases": 0.0,
}


def load_training_defaults() -> dict[str, float]:
    """Load training-set medians from file, falling back to config defaults."""
    if DEFAULTS_FILE.exists():
        try:
            with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {k: float(v) for k, v in data.items() if k in MODEL_FEATURES}
        except Exception:
            pass
    return dict(HARDCODED_FALLBACKS)


TRAINING_DEFAULTS = load_training_defaults()

FEATURE_SPECS: dict[str, FeatureDefinition] = {
    "age": FeatureDefinition(
        name="age",
        label="User Age",
        aliases=(
            "age", "user_age", "customer_age", "demographic_age", "years", "dob", "birth_year"
        ),
        min_clip=18.0,
        max_clip=100.0,
        dtype=int,
        is_integer=True,
        unit="years",
        weight=0.10,
        fallback_default=TRAINING_DEFAULTS.get("age", 30.0),
        description="Customer age in whole years (18–100).",
    ),
    "session_frequency": FeatureDefinition(
        name="session_frequency",
        label="Session Frequency",
        aliases=(
            "session_frequency", "sessions", "frequency", "weekly_sessions", "sessions_per_week",
            "visits", "logins", "weekly_logins", "weekly_visits", "session_count", "logins_per_week"
        ),
        min_clip=0.0,
        max_clip=100.0,
        dtype=float,
        is_integer=False,
        unit="sessions/wk",
        weight=0.20,
        fallback_default=TRAINING_DEFAULTS.get("session_frequency", 5.0),
        description="Average application opens per week (0–100).",
    ),
    "avg_session_minutes": FeatureDefinition(
        name="avg_session_minutes",
        label="Avg Session Minutes",
        aliases=(
            "avg_session_minutes", "session_duration", "avg_duration", "minutes", "time_spent",
            "session_length", "duration", "avg_session_duration", "session_time", "avg_time_spent"
        ),
        min_clip=0.0,
        max_clip=180.0,
        dtype=float,
        is_integer=False,
        unit="minutes",
        weight=0.20,
        fallback_default=TRAINING_DEFAULTS.get("avg_session_minutes", 15.0),
        description="Average active duration per session in minutes (0–180).",
    ),
    "days_since_install": FeatureDefinition(
        name="days_since_install",
        label="Days Since Install",
        aliases=(
            "days_since_install", "tenure", "tenure_days", "days_active", "days_since_signup",
            "account_age_days", "installed_days_ago", "user_tenure", "days_installed", "account_age"
        ),
        min_clip=1.0,
        max_clip=365.0,
        dtype=int,
        is_integer=True,
        unit="days",
        weight=0.15,
        fallback_default=TRAINING_DEFAULTS.get("days_since_install", 45.0),
        description="Account tenure in days since initial installation (1–365).",
    ),
    "notifications_clicked": FeatureDefinition(
        name="notifications_clicked",
        label="Notifications Clicked",
        aliases=(
            "notifications_clicked", "notif_clicks", "push_clicks", "notifications_opened",
            "pushes_clicked", "push_opens", "alerts_clicked", "notif_opened", "push_interactions"
        ),
        min_clip=0.0,
        max_clip=100.0,
        dtype=int,
        is_integer=True,
        unit="clicks",
        weight=0.15,
        fallback_default=TRAINING_DEFAULTS.get("notifications_clicked", 3.0),
        description="Push notifications interacted with in the past 30 days (0–100).",
    ),
    "crashes": FeatureDefinition(
        name="crashes",
        label="App Crashes",
        aliases=(
            "crashes", "crash_count", "app_crashes", "errors", "fatal_errors", "exceptions",
            "bug_reports", "app_errors", "crash_events"
        ),
        min_clip=0.0,
        max_clip=20.0,
        dtype=int,
        is_integer=True,
        unit="crashes",
        weight=0.10,
        fallback_default=0.0,  # Explicitly 0.0 as requested
        description="Fatal app crash events experienced (0–20). Defaults to 0 if omitted.",
    ),
    "purchases": FeatureDefinition(
        name="purchases",
        label="In-App Purchases",
        aliases=(
            "purchases", "in_app_purchases", "orders", "transactions", "buy_count",
            "monetization_events", "checkouts", "iap_count", "payments", "total_purchases"
        ),
        min_clip=0.0,
        max_clip=50.0,
        dtype=int,
        is_integer=True,
        unit="purchases",
        weight=0.10,
        fallback_default=0.0,  # Explicitly 0.0 as requested
        description="Total lifetime in-app purchases (0–50). Defaults to 0 if omitted.",
    ),
}
