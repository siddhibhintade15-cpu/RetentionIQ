"""
app/services/mapping_service.py
-------------------------------
Smart fuzzy column mapping engine:
- Token normalization and alias matching
- String fuzzy matching via difflib.SequenceMatcher
- Value-based statistical evidence for tiebreaking
- Global 1-to-1 conflict resolution
- DOB to age conversion and PII email hashing
"""

from __future__ import annotations

import difflib
import hashlib
import re
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import HTTPException

from app.services.feature_spec import (
    FEATURE_SPECS,
    IDENTIFIER_ALIASES,
    MODEL_FEATURES,
    TARGET_ALIASES,
)

MIN_MAPPED_FEATURES = 3
PII_SALT = "retentioniq_pii_salt_2026"
AMBIGUOUS_ALIASES = {"minutes", "years", "duration", "errors", "time", "count"}


def normalize_col_name(name: str) -> str:
    """Normalize column name: lowercase, strip non-alphanumerics, singularize."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(name).strip().lower()).strip("_")
    # Simple singularization
    if s.endswith("ies"):
        s = s[:-3] + "y"
    elif s.endswith("es") and not s.endswith("crashes"):
        s = s[:-2]
    elif s.endswith("s") and not (s.endswith("crashes") or s.endswith("purchases")):
        s = s[:-1]
    return s


class MappingEngine:
    """Intelligently matches user columns to model features and handles special transforms."""

    @classmethod
    def score_column_for_feature(
        cls,
        user_col: str,
        feat_name: str,
        numeric_series: pd.Series,
    ) -> tuple[float, str]:
        """
        Calculates a match confidence score between 0.0 and 1.0.
        Returns (confidence, method).
        """
        spec = FEATURE_SPECS[feat_name]
        norm_user = normalize_col_name(user_col)

        # 1. Exact alias match
        for alias in spec.aliases:
            norm_alias = normalize_col_name(alias)
            if norm_user == norm_alias:
                # Check if ambiguous
                if alias in AMBIGUOUS_ALIASES:
                    val_bonus = cls._eval_value_evidence(feat_name, numeric_series)
                    if val_bonus >= 0.10:
                        return 0.95, "value_based"
                    return 0.80, "alias"
                return 1.0, "exact"

        # 2. Token overlap & substring match
        best_token_score = 0.0
        for alias in spec.aliases:
            norm_alias = normalize_col_name(alias)
            # Substring match (e.g. "user_session_frequency" contains "session_frequency")
            if norm_alias in norm_user or norm_user in norm_alias:
                ratio = len(norm_alias) / max(len(norm_user), 1)
                best_token_score = max(best_token_score, min(0.90, 0.70 + 0.20 * ratio))

            # difflib fuzzy ratio
            ratio = difflib.SequenceMatcher(None, norm_user, norm_alias).ratio()
            best_token_score = max(best_token_score, ratio * 0.90)

        # 3. Value-based evidence
        val_evidence = cls._eval_value_evidence(feat_name, numeric_series)
        total_score = min(1.0, best_token_score + val_evidence)

        method = "fuzzy" if best_token_score > 0.50 else "value_based"
        return total_score, method

    @classmethod
    def _eval_value_evidence(cls, feat_name: str, s: pd.Series) -> float:
        """Heuristics based on observed numeric distribution."""
        valid = s.dropna()
        if len(valid) == 0:
            return 0.0

        median = valid.median()
        v_min = valid.min()
        v_max = valid.max()
        zero_ratio = (valid == 0).sum() / len(valid)

        if feat_name == "age":
            if 15 <= median <= 75 and 10 <= v_min and v_max <= 110:
                return 0.15
        elif feat_name == "crashes":
            if 0 <= v_min and v_max <= 25 and zero_ratio >= 0.40:
                return 0.18
        elif feat_name == "purchases":
            if 0 <= v_min and v_max <= 100 and zero_ratio >= 0.30:
                return 0.15
        elif feat_name == "session_frequency":
            if 0 <= v_min and median <= 35 and v_max <= 150:
                return 0.12
        elif feat_name == "avg_session_minutes":
            if 0 <= v_min and 2.0 <= median <= 90.0 and v_max <= 300:
                return 0.12
        elif feat_name == "days_since_install":
            if 1 <= v_min and 5 <= median <= 365 and v_max <= 1000:
                return 0.12
        elif feat_name == "notifications_clicked":
            if 0 <= v_min and median <= 40 and v_max <= 150:
                return 0.12

        return 0.0

    @classmethod
    def resolve_mappings(
        cls,
        user_columns: list[str],
        numeric_dict: dict[str, pd.Series],
        user_overrides: Optional[dict[str, Optional[str]]] = None,
    ) -> dict[str, Any]:
        """
        Global best-assignment mapping for all features and identifiers.
        Returns:
            - mappings: list of mapping dicts
            - unmapped_columns: list of user column names
            - mapped_features: dict {feat_name: user_col}
            - id_column: str | None
            - target_column: str | None
            - warnings: list of str
        """
        overrides = user_overrides or {}
        assigned_user_cols: set[str] = set()
        assigned_features: set[str] = set()
        results: list[dict[str, Any]] = []
        warnings: list[str] = []

        # 1. Apply explicit user overrides first
        for u_col, target in overrides.items():
            if u_col not in user_columns:
                continue
            assigned_user_cols.add(u_col)
            if target is None:
                # Explicitly ignored column
                continue
            if target in MODEL_FEATURES:
                assigned_features.add(target)
                results.append({
                    "user_column": u_col,
                    "model_feature": target,
                    "confidence": 1.0,
                    "method": "user_override",
                    "status": "overridden",
                })

        # 2. Score remaining (user_col, model_feature) pairs
        candidates: list[tuple[float, str, str, str]] = []
        for u_col in user_columns:
            if u_col in assigned_user_cols:
                continue
            num_s = numeric_dict.get(u_col, pd.Series(dtype=float))
            for feat in MODEL_FEATURES:
                if feat in assigned_features:
                    continue
                score, method = cls.score_column_for_feature(u_col, feat, num_s)
                if score >= 0.60:
                    candidates.append((score, u_col, feat, method))

        # Sort candidates descending by score for greedy global resolution
        candidates.sort(key=lambda x: x[0], reverse=True)

        for score, u_col, feat, method in candidates:
            if u_col in assigned_user_cols or feat in assigned_features:
                continue
            assigned_user_cols.add(u_col)
            assigned_features.add(feat)

            status = "auto" if score >= 0.85 else "suggested"
            results.append({
                "user_column": u_col,
                "model_feature": feat,
                "confidence": round(score, 2),
                "method": method,
                "status": status,
            })

        # 3. Identify customer_id column
        id_column: Optional[str] = None
        for u_col in user_columns:
            if u_col in assigned_user_cols:
                continue
            norm = normalize_col_name(u_col)
            for id_alias in IDENTIFIER_ALIASES:
                if norm == normalize_col_name(id_alias) or norm.endswith(f"_{id_alias}"):
                    id_column = u_col
                    break
            if id_column:
                break

        # 4. Identify Target column (retained / churn)
        target_column: Optional[str] = None
        for u_col in user_columns:
            if u_col in assigned_user_cols or u_col == id_column:
                continue
            norm = normalize_col_name(u_col)
            for t_type, aliases in TARGET_ALIASES.items():
                if any(norm == normalize_col_name(a) for a in aliases):
                    target_column = u_col
                    break
            if target_column:
                break

        # Check for unmapped columns
        mapped_user_cols = {m["user_column"] for m in results}
        unmapped = [c for c in user_columns if c not in mapped_user_cols and c != id_column and c != target_column]

        mapped_feature_names = {m["model_feature"]: m["user_column"] for m in results}

        return {
            "mappings": results,
            "unmapped_columns": unmapped,
            "mapped_features": mapped_feature_names,
            "id_column": id_column,
            "target_column": target_column,
            "warnings": warnings,
        }

    @classmethod
    def transform_special_columns(
        cls,
        df: pd.DataFrame,
        mapped_features: dict[str, str],
        id_column: Optional[str],
        batch_id: int,
    ) -> tuple[pd.DataFrame, list[str], list[str]]:
        """
        Stage 3b:
        - Convert DOB column to age in years (if age column looks like a date).
        - Hash email identifier if used as customer_id.
        - Generate namespaced IDs if no customer_id exists.
        Returns (transformed_df, customer_ids, notices).
        """
        notices: list[str] = []
        df_out = df.copy()

        # 1. DOB to Age conversion
        age_col = mapped_features.get("age")
        if age_col and age_col in df_out.columns:
            sample_val = str(df_out[age_col].dropna().iloc[0]) if not df_out[age_col].dropna().empty else ""
            if any(char in sample_val for char in ["-", "/", "."]) and len(sample_val) >= 6:
                try:
                    dob_series = pd.to_datetime(df_out[age_col], errors="coerce")
                    now = datetime.now()
                    ages = (now - dob_series).dt.days // 365.25
                    df_out[age_col] = ages
                    notices.append(f"Column '{age_col}' parsed as Date-of-Birth and converted to age in years as of today.")
                except Exception:
                    pass

        # 2. Customer ID handling & PII hashing
        customer_ids: list[str] = []
        if id_column and id_column in df_out.columns:
            for idx, raw_val in enumerate(df_out[id_column]):
                val_str = str(raw_val).strip()
                if "@" in val_str:  # PII email detection
                    hashed = hashlib.sha256(f"{val_str}_{PII_SALT}".encode()).hexdigest()[:12]
                    customer_ids.append(f"PII_{hashed}")
                else:
                    customer_ids.append(val_str if val_str and val_str.lower() != "nan" else f"B{batch_id}-{idx + 1:06d}")

            if any("@" in str(v) for v in df_out[id_column].head(50)):
                notices.append(f"PII Warning: Email detected in '{id_column}'. Hashed with SHA-256 for privacy compliance.")
        else:
            # Generate namespaced IDs
            for idx in range(len(df_out)):
                customer_ids.append(f"B{batch_id}-{idx + 1:06d}")
            notices.append(f"No ID column mapped. Generated batch-namespaced IDs: B{batch_id}-000001 to B{batch_id}-{len(df_out):06d}.")

        return df_out, customer_ids, notices
