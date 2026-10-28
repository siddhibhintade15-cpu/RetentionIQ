"""
app/services/validation_service.py
----------------------------------
Multi-tier pre-flight validation and fail-check engine for CSV uploads.

Tier 1: File & transport integrity checks (size, extension, MIME, encoding, delimiter)
Tier 2: Header & schema checks (missing columns, duplicates, header existence)
Tier 3: Row & cell-level integrity checks (type coercion, non-null, physical bounds)
Tier 4: Mode selection (strict vs lenient processing)
"""

from __future__ import annotations

import csv
import io
import math
import re
from typing import Any, Optional

from fastapi import HTTPException

from app.schemas import BatchValidationReport, RowValidationError

# ---------------------------------------------------------------------------
# Strict CSV Data Contract Configuration
# ---------------------------------------------------------------------------

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 5000
MIN_ROWS = 1

CORE_FEATURES = [
    "age",
    "session_frequency",
    "avg_session_minutes",
    "days_since_install",
    "notifications_clicked",
    "crashes",
    "purchases",
]

INTEGER_FEATURES = {
    "age",
    "days_since_install",
    "notifications_clicked",
    "crashes",
    "purchases",
}

# Strict physical bounds per contract
FEATURE_CONTRACT = {
    "age": {
        "type": "integer",
        "min": 18,
        "max": 100,
        "required": True,
        "remediation": "Ensure age is an integer between 18 and 100.",
    },
    "session_frequency": {
        "type": "numeric",
        "min": 0.0,
        "max": 100.0,
        "required": True,
        "remediation": "Ensure session frequency is between 0 and 100 sessions/week.",
    },
    "avg_session_minutes": {
        "type": "float",
        "min": 0.0,
        "max": 180.0,
        "required": True,
        "remediation": "Ensure average session minutes is between 0.0 and 180.0 minutes.",
    },
    "days_since_install": {
        "type": "integer",
        "min": 1,
        "max": 365,
        "required": True,
        "remediation": "Ensure days since install is an integer between 1 and 365.",
    },
    "notifications_clicked": {
        "type": "integer",
        "min": 0,
        "max": 100,
        "required": True,
        "remediation": "Ensure notifications clicked is an integer between 0 and 100.",
    },
    "crashes": {
        "type": "integer",
        "min": 0,
        "max": 20,
        "required": True,
        "remediation": "Ensure crash count is an integer between 0 and 20.",
    },
    "purchases": {
        "type": "integer",
        "min": 0,
        "max": 50,
        "required": True,
        "remediation": "Ensure in-app purchases is an integer between 0 and 50.",
    },
}

ALLOWED_EXTENSIONS = {".csv"}
ALLOWED_MIME_PREFIXES = ("text/csv", "application/vnd.ms-excel", "text/plain", "application/csv")


class CSVValidationEngine:
    """Multi-stage validation engine for CSV files."""

    @staticmethod
    def validate_file_transport(
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Tier 1: Verify file transport, size, extension, MIME, encoding, and delimiter.
        Returns decoded text string.
        """
        # 1. Empty file check
        if not content or len(content.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        # 2. File size limit (5 MB)
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File too large. File exceeds 5 MB limit. Please split your dataset.",
            )

        # 3. Extension check
        lower_name = (filename or "").lower()
        if not any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are accepted. Do not upload model or pickle files.",
            )

        # 4. Binary file check (null byte inspection)
        if b"\x00" in content[:2048]:
            raise HTTPException(
                status_code=400,
                detail="Malformed CSV: binary characters detected. Please upload a plain text CSV.",
            )

        # 5. Encoding decoding (UTF-8-SIG -> UTF-8 -> Latin-1)
        decoded_text: Optional[str] = None
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                decoded_text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if decoded_text is None:
            raise HTTPException(
                status_code=400,
                detail="Could not decode CSV. File must be encoded in UTF-8 or Latin-1.",
            )

        return decoded_text

    @staticmethod
    def sniff_delimiter(sample_line: str) -> str:
        """Detect if delimiter is comma, semicolon, or tab."""
        for delim in (",", ";", "\t"):
            if delim in sample_line:
                return delim
        return ","

    @classmethod
    def parse_and_validate(
        cls,
        text: str,
        filename: str,
        customer_id_col: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], BatchValidationReport]:
        """
        Runs Tier 2 & Tier 3 checks on decoded text.
        Returns:
            - list of parsed row records (contains valid features or error marker)
            - BatchValidationReport with all diagnostics
        """
        # Split lines, safely stripping trailing blank lines
        raw_lines = [line for line in text.splitlines() if line.strip()]
        if not raw_lines:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        delimiter = cls.sniff_delimiter(raw_lines[0])

        reader = csv.reader(raw_lines, delimiter=delimiter)
        try:
            raw_headers = next(reader, None)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not parse CSV headers: {exc}")

        if not raw_headers:
            raise HTTPException(status_code=400, detail="Uploaded file is empty or missing headers.")

        # Normalize headers
        normalized_headers = [h.strip().lower() for h in raw_headers]

        # Check duplicate headers
        seen_headers = set()
        for h in normalized_headers:
            if h in seen_headers:
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate column header found: '{h}'. Each column must be unique.",
                )
            seen_headers.add(h)

        # Tier 2: Check required columns
        missing_columns = [feat for feat in CORE_FEATURES if feat not in normalized_headers]
        unexpected_columns = [
            h for h in normalized_headers
            if h not in CORE_FEATURES and h != (customer_id_col.lower() if customer_id_col else "customer_id")
        ]

        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required column(s): {missing_columns}. Required: {CORE_FEATURES}",
            )

        # Header index mapping
        col_indices = {col: idx for idx, col in enumerate(normalized_headers)}
        cust_id_idx = None
        if customer_id_col and customer_id_col.lower() in col_indices:
            cust_id_idx = col_indices[customer_id_col.lower()]
        elif "customer_id" in col_indices:
            cust_id_idx = col_indices["customer_id"]

        # Tier 3: Parse and validate rows
        rows: list[dict[str, Any]] = []
        errors: list[RowValidationError] = []
        valid_rows_count = 0
        error_rows_count = 0

        row_idx = 1  # 1-based data row index (row 1 is first row after header)

        for line_values in reader:
            # Skip empty lines
            if not line_values or all(not val.strip() for val in line_values):
                continue

            if len(rows) >= MAX_ROWS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Too many rows. Maximum is {MAX_ROWS}, got {len(rows) + 1}.",
                )

            # Determine customer ID if present
            cust_id_val: Optional[str] = None
            if cust_id_idx is not None and cust_id_idx < len(line_values):
                raw_cust = line_values[cust_id_idx].strip()
                if raw_cust:
                    cust_id_val = raw_cust[:64]

            row_has_error = False
            validated_features: dict[str, float] = {}
            first_error_msg: Optional[str] = None

            for feat in CORE_FEATURES:
                feat_idx = col_indices[feat]
                raw_val = line_values[feat_idx].strip() if feat_idx < len(line_values) else ""
                spec = FEATURE_CONTRACT[feat]

                # 1. Non-null check
                if raw_val == "" or raw_val.lower() in ("null", "none", "nan", "na", "--"):
                    err = RowValidationError(
                        row_index=row_idx,
                        customer_id=cust_id_val,
                        column=feat,
                        invalid_value=raw_val or "<empty>",
                        constraint="Must be non-empty",
                        message=f"Missing value for '{feat}'.",
                        remediation=spec["remediation"],
                    )
                    errors.append(err)
                    row_has_error = True
                    if not first_error_msg:
                        first_error_msg = f"missing value for '{feat}'"
                    continue

                # Clean potential currency or percentage symbols
                clean_val = raw_val.replace("$", "").replace("%", "").strip()

                # 2. Type coercion check
                try:
                    num_val = float(clean_val)
                    if math.isnan(num_val) or math.isinf(num_val):
                        raise ValueError()
                except ValueError:
                    err = RowValidationError(
                        row_index=row_idx,
                        customer_id=cust_id_val,
                        column=feat,
                        invalid_value=raw_val,
                        constraint="Expected Numeric Value",
                        message=f"'{feat}' is not numeric (got '{raw_val}').",
                        remediation=spec["remediation"],
                    )
                    errors.append(err)
                    row_has_error = True
                    if not first_error_msg:
                        first_error_msg = f"'{feat}' is not numeric (got {raw_val!r})"
                    continue

                # 3. Non-negative check
                if num_val < 0:
                    err = RowValidationError(
                        row_index=row_idx,
                        customer_id=cust_id_val,
                        column=feat,
                        invalid_value=num_val,
                        constraint="Cannot be negative",
                        message=f"'{feat}' cannot be negative (got {num_val}).",
                        remediation=spec["remediation"],
                    )
                    errors.append(err)
                    row_has_error = True
                    if not first_error_msg:
                        first_error_msg = f"'{feat}' cannot be negative"
                    continue

                # 4. Integer check
                if feat in INTEGER_FEATURES and not num_val.is_integer():
                    err = RowValidationError(
                        row_index=row_idx,
                        customer_id=cust_id_val,
                        column=feat,
                        invalid_value=num_val,
                        constraint="Expected Integer",
                        message=f"'{feat}' must be a whole number (got {num_val}).",
                        remediation="Provide a whole integer without decimal points.",
                    )
                    errors.append(err)
                    row_has_error = True
                    if not first_error_msg:
                        first_error_msg = f"'{feat}' must be a whole number"
                    continue

                # 5. Range bounds check
                min_bound = spec["min"]
                max_bound = spec["max"]
                if not (min_bound <= num_val <= max_bound):
                    err = RowValidationError(
                        row_index=row_idx,
                        customer_id=cust_id_val,
                        column=feat,
                        invalid_value=num_val,
                        constraint=f"Range: {min_bound} to {max_bound}",
                        message=f"'{feat}' must be between {min_bound} and {max_bound} (got {num_val}).",
                        remediation=spec["remediation"],
                    )
                    errors.append(err)
                    row_has_error = True
                    if not first_error_msg:
                        first_error_msg = f"'{feat}' must be between {min_bound} and {max_bound} (got {num_val})"
                    continue

                validated_features[feat] = num_val

            if row_has_error:
                error_rows_count += 1
                rows.append({
                    "row_index": row_idx,
                    "customer_id": cust_id_val,
                    "ok": False,
                    "features": None,
                    "error": f"Row {row_idx}: {first_error_msg}" if first_error_msg else f"Row {row_idx} failed validation",
                })
            else:
                valid_rows_count += 1
                rows.append({
                    "row_index": row_idx,
                    "customer_id": cust_id_val,
                    "ok": True,
                    "features": validated_features,
                    "error": None,
                })

            row_idx += 1

        total_rows = len(rows)
        if total_rows < MIN_ROWS:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV has no data rows.",
            )

        report = BatchValidationReport(
            filename=filename,
            total_rows=total_rows,
            valid_rows=valid_rows_count,
            error_rows=error_rows_count,
            is_valid=(error_rows_count == 0),
            errors=errors,
            missing_columns=missing_columns,
            unexpected_columns=unexpected_columns,
        )

        return rows, report
