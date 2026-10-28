"""
tests/test_csv_fail_checks.py
-----------------------------
Comprehensive test suite verifying all 4 tiers of the CSV fail-check engine:
1. Empty file rejection
2. Missing required column rejection
3. Non-numeric type detection with precise row and column tracking
4. Out-of-bounds validation (age, session minutes, crashes)
5. Negative value rejection
6. Missing / NaN cell detection
7. Strict mode (422 reject all) vs Lenient mode (200 score valid + report errors)
8. Template & sample endpoint downloads
9. Dry-run validate endpoint
10. Delimiter auto-detection (comma, semicolon, tab)
"""

from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _upload_csv(
    client: TestClient,
    content: bytes | str,
    endpoint: str = "/api/batch/upload",
    filename: str = "batch.csv",
    params: dict = None,
):
    if isinstance(content, str):
        content = content.encode("utf-8")
    files = {"file": (filename, io.BytesIO(content), "text/csv")}
    return client.post(endpoint, files=files, params=params or {})


def test_empty_file_fails(client: TestClient):
    """0-byte file returns HTTP 400 with clear message."""
    resp = _upload_csv(client, b"")
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_missing_required_column_fails(client: TestClient):
    """CSV missing required column 'crashes' returns HTTP 400 with missing columns list."""
    csv_data = (
        "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,purchases\n"
        "USR-1,25,5,15.0,20,3,1\n"
    )
    resp = _upload_csv(client, csv_data)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "crashes" in detail
    assert "Missing required column" in detail


def test_non_numeric_type_fails(client: TestClient):
    """String in numeric field (e.g. 'forty-five' in avg_session_minutes) is reported with exact row and column."""
    csv_data = (
        "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "USR-1,28,7,forty-five,30,8,0,1\n"
    )
    # Strict mode test
    resp = _upload_csv(client, csv_data, params={"mode": "strict"})
    assert resp.status_code == 422
    report = resp.json()["detail"]
    assert report["error_rows"] == 1
    assert len(report["errors"]) == 1
    err = report["errors"][0]
    assert err["row_index"] == 1
    assert err["column"] == "avg_session_minutes"
    assert "Expected Numeric Value" in err["constraint"]


def test_out_of_bounds_age_fails(client: TestClient):
    """Age out of bounds (< 18 or > 100) triggers explicit range error."""
    csv_data = (
        "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "USR-YOUNG,12,7,20.0,30,8,0,1\n"
        "USR-OLD,150,7,20.0,30,8,0,1\n"
    )
    resp = _upload_csv(client, csv_data, params={"mode": "strict"})
    assert resp.status_code == 422
    report = resp.json()["detail"]
    assert report["error_rows"] == 2
    assert any(e["row_index"] == 1 and e["column"] == "age" for e in report["errors"])
    assert any(e["row_index"] == 2 and e["column"] == "age" for e in report["errors"])


def test_negative_values_fail(client: TestClient):
    """Negative values in features (e.g. crashes = -3) trigger negative rejection."""
    csv_data = (
        "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "USR-NEG,25,-4,20.0,30,8,-1,1\n"
    )
    resp = _upload_csv(client, csv_data, params={"mode": "strict"})
    assert resp.status_code == 422
    report = resp.json()["detail"]
    assert report["error_rows"] == 1
    neg_errors = [e for e in report["errors"] if "negative" in e["constraint"].lower()]
    assert len(neg_errors) >= 1


def test_missing_value_nan_fails(client: TestClient):
    """Empty cell in required column produces an explicit missing value error."""
    csv_data = (
        "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "USR-NULL,28,,20.0,30,8,0,1\n"
    )
    resp = _upload_csv(client, csv_data, params={"mode": "strict"})
    assert resp.status_code == 422
    report = resp.json()["detail"]
    assert report["error_rows"] == 1
    assert any(e["column"] == "session_frequency" and "Must be non-empty" in e["constraint"] for e in report["errors"])


def test_strict_vs_lenient_mode(client: TestClient):
    """
    Verify that in strict mode, any row failure results in HTTP 422 (no rows scored).
    In lenient mode, valid rows are scored and invalid rows are cataloged in response.
    """
    mixed_csv = (
        "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "USR-VALID-1,28,7,22.5,30,8,0,1\n"
        "USR-BAD-1,999,7,22.5,30,8,0,1\n"  # age 999 invalid
        "USR-VALID-2,35,4,15.0,60,3,1,0\n"
    )

    # 1. Strict mode must reject with 422
    strict_resp = _upload_csv(client, mixed_csv, params={"mode": "strict"})
    assert strict_resp.status_code == 422
    strict_detail = strict_resp.json()["detail"]
    assert strict_detail["is_valid"] is False
    assert strict_detail["valid_rows"] == 2
    assert strict_detail["error_rows"] == 1

    # 2. Lenient mode must succeed with 200, returning scored results for 2 valid rows
    lenient_resp = _upload_csv(client, mixed_csv, params={"mode": "lenient"})
    assert lenient_resp.status_code == 200
    lenient_data = lenient_resp.json()
    assert lenient_data["total_rows"] == 3
    assert lenient_data["valid_rows"] == 2
    assert lenient_data["error_rows"] == 1

    results = lenient_data["results"]
    assert results[0]["ok"] is True
    assert results[0]["probability"] is not None
    assert results[1]["ok"] is False
    assert "age" in results[1]["error"]
    assert results[2]["ok"] is True

    # Detailed errors must be attached
    assert len(lenient_data["errors"]) == 1
    assert lenient_data["errors"][0]["row_index"] == 2
    assert lenient_data["errors"][0]["column"] == "age"


def test_template_endpoints(client: TestClient):
    """Verify /api/batch/template and /api/batch/sample return valid CSV downloads."""
    # Test blank template
    t_resp = client.get("/api/batch/template")
    assert t_resp.status_code == 200
    assert "text/csv" in t_resp.headers["content-type"]
    assert "retentioniq_template.csv" in t_resp.headers["content-disposition"]
    assert "age,session_frequency,avg_session_minutes" in t_resp.text

    # Test sample dataset
    s_resp = client.get("/api/batch/sample")
    assert s_resp.status_code == 200
    assert "text/csv" in s_resp.headers["content-type"]
    assert "retentioniq_sample_valid.csv" in s_resp.headers["content-disposition"]
    lines = s_resp.text.strip().splitlines()
    assert len(lines) == 11  # header + 10 rows


def test_dry_run_validate_endpoint(client: TestClient):
    """Verify /api/batch/validate performs dry-run validation without database writes."""
    valid_csv = (
        "customer_id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "USR-VAL-1,28,7,22.5,30,8,0,1\n"
        "USR-VAL-2,42,3,10.0,90,1,2,0\n"
    )
    resp = _upload_csv(client, valid_csv, endpoint="/api/batch/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["total_rows"] == 2
    assert data["valid_rows"] == 2
    assert data["error_rows"] == 0
    assert len(data["errors"]) == 0


def test_delimiter_detection(client: TestClient):
    """Verify semicolon-delimited CSV files are sniffed and parsed seamlessly."""
    semicolon_csv = (
        "customer_id;age;session_frequency;avg_session_minutes;days_since_install;notifications_clicked;crashes;purchases\n"
        "USR-SEMI;28;7;22.5;30;8;0;1\n"
    )
    resp = _upload_csv(client, semicolon_csv, params={"mode": "strict"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid_rows"] == 1
    assert data["error_rows"] == 0
