"""
app/services/ingestion_service.py
---------------------------------
Robust, forgiving ingestion pipeline for arbitrary customer CSV files:
1. Safe byte reading with file size and row limits
2. Dynamic encoding detection (UTF-8, UTF-8-BOM, UTF-16, Windows-1252, Latin-1)
3. Delimiter auto-sniffing (, ; \\t |)
4. Header cleaning and de-duplication
5. Locale-aware numeric parsing (currency, thousand commas vs decimal commas)
6. Column data type classification
7. Unit sanity checks (seconds vs minutes)
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import HTTPException

MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_ROWS = 100_000

# Null token representations
NULL_TOKENS = {
    "", "n/a", "na", "null", "none", "-", "--", "?", "nan", "nil", "<na>",
    "undefined", "unknown", "#n/a", "#na"
}

# Currency and decorative characters to strip
CURRENCY_REGEX = re.compile(r"[\$€£₹¥₽₩\s\u00a0]")


class IngestionEngine:
    """Safe, forgiving CSV parser that repairs messy input rather than rejecting it."""

    @classmethod
    def read_and_decode(cls, content: bytes, filename: str) -> tuple[str, str]:
        """
        Stage 1 & 2: Enforce size limits, detect binary data, decode encoding.
        Returns (decoded_text, detected_encoding).
        """
        if not content or len(content.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail={"error_code": "EMPTY_FILE", "message": "Uploaded file is empty.", "hint": "Select a CSV with data rows."},
            )

        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "error_code": "FILE_TOO_LARGE",
                    "message": f"File exceeds {MAX_UPLOAD_MB} MB limit.",
                    "hint": "Please upload a smaller dataset or slice your cohort."
                },
            )

        # Binary check (null bytes in first 2048 bytes)
        if b"\x00" in content[:2048] and not (content.startswith(b"\xff\xfe") or content.startswith(b"\xfe\xff")):
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "BINARY_FILE",
                    "message": "Binary or non-text file detected.",
                    "hint": "Ensure your file is a valid plain text CSV."
                },
            )

        # Try-chain for encoding
        encodings = ["utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"]
        decoded_text: Optional[str] = None
        used_encoding = "utf-8"

        for enc in encodings:
            try:
                decoded_text = content.decode(enc)
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue

        if decoded_text is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "ENCODING_ERROR",
                    "message": "Could not decode text with standard encodings.",
                    "hint": "Save your spreadsheet as UTF-8 CSV before uploading."
                },
            )

        return decoded_text, used_encoding

    @classmethod
    def detect_delimiter(cls, sample_text: str) -> str:
        """
        Stage 3: Sniff delimiter with fallback over comma, semicolon, tab, pipe.
        """
        lines = [ln for ln in sample_text.splitlines() if ln.strip()][:10]
        if not lines:
            return ","

        sample_chunk = "\n".join(lines)
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample_chunk, delimiters=[",", ";", "\t", "|"])
            if dialect.delimiter in (",", ";", "\t", "|"):
                return dialect.delimiter
        except Exception:
            pass

        # Fallback: count candidate delimiters in first line
        first_line = lines[0]
        counts = {d: first_line.count(d) for d in (",", ";", "\t", "|")}
        best = max(counts, key=counts.get)  # type: ignore[arg-type]
        return best if counts[best] > 0 else ","

    @classmethod
    def parse_raw_dataframe(
        cls,
        text: str,
        delimiter: str,
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Stage 4: Read CSV into pandas, clean headers, preserve original headers.
        """
        try:
            df = pd.read_csv(
                io.StringIO(text),
                sep=delimiter,
                dtype=str,
                keep_default_na=False,
                on_bad_lines="skip",
                nrows=MAX_ROWS,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "CSV_PARSE_ERROR",
                    "message": f"Could not parse CSV: {exc}",
                    "hint": "Check for unclosed quotation marks or corrupted rows."
                },
            )

        if df.empty or len(df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "NO_DATA_ROWS",
                    "message": "The CSV contains no data rows.",
                    "hint": "Ensure your file contains at least one header and one row of values."
                },
            )

        original_headers = list(df.columns)

        # De-duplicate and sanitize column headers
        cleaned_headers: list[str] = []
        seen: dict[str, int] = {}

        for idx, col in enumerate(original_headers):
            c_str = str(col).strip()
            if not c_str or c_str.lower().startswith("unnamed:"):
                c_str = f"unnamed_{idx + 1}"

            norm = c_str
            if norm in seen:
                seen[norm] += 1
                cleaned_headers.append(f"{norm}_{seen[norm]}")
            else:
                seen[norm] = 1
                cleaned_headers.append(norm)

        df.columns = cleaned_headers
        return df, original_headers

    @classmethod
    def parse_locale_numeric(cls, s: pd.Series) -> tuple[pd.Series, bool]:
        """
        Stage 5: Locale-aware numeric conversion.
        Handles US ($1,200.50), EU (1.200,50), percentage (45%), and negatives.
        Returns (parsed_numeric_series, was_numeric_detected).
        """
        # Convert null representations to np.nan
        s_clean = s.astype(str).str.strip()
        s_lower = s_clean.str.lower()
        is_null = s_lower.isin(NULL_TOKENS) | (s_clean == "")

        # Extract values that are not null
        valid_vals = s_clean[~is_null]
        if len(valid_vals) == 0:
            return pd.Series(np.nan, index=s.index, dtype=float), False

        # Clean currency symbols, percentage signs, spaces
        cleaned = valid_vals.str.replace(CURRENCY_REGEX, "", regex=True)

        # Sample non-empty values to inspect decimal style
        sample = cleaned.head(50)
        has_comma = sample.str.contains(",", regex=False).any()
        has_dot = sample.str.contains(r"\.", regex=True).any()

        def convert_val(v: str) -> float:
            if not v or v.lower() in NULL_TOKENS:
                return np.nan
            # Strip remaining symbols
            v = CURRENCY_REGEX.sub("", v).replace("%", "")
            # Check EU style: 1.200,50 -> 1200.50
            if "," in v and "." in v:
                comma_idx = v.rfind(",")
                dot_idx = v.rfind(".")
                if comma_idx > dot_idx:
                    # EU: dots are thousands, comma is decimal
                    v = v.replace(".", "").replace(",", ".")
                else:
                    # US: commas are thousands, dot is decimal
                    v = v.replace(",", "")
            elif "," in v and not "." in v:
                # Could be decimal comma (e.g. 12,5) or integer thousand (1,200)
                parts = v.split(",")
                if len(parts) == 2 and len(parts[1]) != 3:
                    # Likely decimal comma e.g. 12,5
                    v = v.replace(",", ".")
                else:
                    # Likely thousand separator e.g. 1,000
                    v = v.replace(",", "")

            try:
                val = float(v)
                return val if not (np.isnan(val) or np.isinf(val)) else np.nan
            except ValueError:
                return np.nan

        parsed = pd.Series(np.nan, index=s.index, dtype=float)
        numeric_converted = valid_vals.map(convert_val)
        parsed.loc[numeric_converted.index] = numeric_converted

        # If at least 60% of non-null values converted successfully to numeric
        valid_count = len(valid_vals)
        success_count = parsed.notna().sum()
        is_numeric = (success_count / valid_count >= 0.60) if valid_count > 0 else False

        return parsed, is_numeric

    @classmethod
    def detect_column_type(cls, raw_series: pd.Series, numeric_series: pd.Series, is_numeric: bool) -> str:
        """
        Stage 6: Classify into Numeric, Categorical, Datetime, Identifier, Boolean.
        """
        clean = raw_series.dropna().astype(str).str.strip()
        clean = clean[~clean.str.lower().isin(NULL_TOKENS)]
        if len(clean) == 0:
            return "Categorical"

        sample = clean.head(100)

        # Check Boolean
        bool_tokens = {"true", "false", "yes", "no", "1", "0", "y", "n", "t", "f"}
        if set(sample.str.lower().unique()).issubset(bool_tokens) and len(sample.unique()) <= 2:
            return "Boolean"

        # Check Datetime (look for year-like patterns or date slashes/dashes)
        date_pattern = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}|^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}")
        date_matches = sample.str.match(date_pattern).sum()
        if date_matches / len(sample) >= 0.60:
            return "Datetime"

        # Check Numeric
        if is_numeric:
            return "Numeric"

        # Check Identifier (high cardinality, alphanumeric strings)
        unique_ratio = len(sample.unique()) / len(sample)
        if unique_ratio >= 0.90 and len(clean) > 5:
            return "Identifier"

        return "Categorical"
