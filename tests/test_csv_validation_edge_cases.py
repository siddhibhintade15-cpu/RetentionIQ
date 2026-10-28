"""
tests/test_csv_validation_edge_cases.py
---------------------------------------
Comprehensive testing of CSV upload validation, bounds checking,
per-row error reporting without batch failure, and file-level security limits.
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


def _upload_csv_bytes(client: TestClient, csv_content: bytes, filename: str = "test.csv", params: dict = None):
    files = {"file": (filename, io.BytesIO(csv_content), "text/csv")}
    return client.post("/api/batch/upload", files=files, params=params or {})


def test_missing_required_column(client: TestClient):
    # CSV missing 'purchases'
    csv_data = b"age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes\n25,5,15.0,20,3,1\n"
    resp = _upload_csv_bytes(client, csv_data)
    assert resp.status_code == 400
    assert "Missing required column" in resp.json()["detail"]


def test_empty_csv_file(client: TestClient):
    resp = _upload_csv_bytes(client, b"")
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_invalid_file_extension(client: TestClient):
    resp = _upload_csv_bytes(client, b"dummy data", filename="model.joblib")
    assert resp.status_code == 400
    assert "Only CSV files are accepted" in resp.json()["detail"]


def test_oversized_file_rejected(client: TestClient):
    # Create 5.5 MB dummy content
    large_content = b"a" * (5 * 1024 * 1024 + 1024)
    resp = _upload_csv_bytes(client, large_content, filename="large.csv")
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"].lower()


def test_per_row_error_reporting_with_invalid_types(client: TestClient):
    # Row 1: valid
    # Row 2: non-numeric age "thirty"
    # Row 3: negative crashes "-2"
    # Row 4: float for integer field "2.5" crashes
    # Row 5: NaN in avg_session_minutes
    csv_data = (
        b"age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        b"25,5,15.0,20,3,1,0\n"
        b"thirty,5,15.0,20,3,1,0\n"
        b"25,5,15.0,20,3,-2,0\n"
        b"25,5,15.0,20,3,2.5,0\n"
        b"25,5,,20,3,1,0\n"
        b"32,10,30.0,45,8,0,2\n"
    )
    resp = _upload_csv_bytes(client, csv_data, params={"mode": "lenient"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_rows"] == 6
    assert data["valid_rows"] == 2
    assert data["error_rows"] == 4

    results = data["results"]
    assert len(results) == 6

    # Check valid row 1
    assert results[0]["ok"] is True
    assert results[0]["prediction"] in (0, 1)

    # Check non-numeric row 2
    assert results[1]["ok"] is False
    assert "not numeric" in results[1]["error"]

    # Check negative crashes row 3
    assert results[2]["ok"] is False
    assert "cannot be negative" in results[2]["error"]

    # Check float crashes row 4
    assert results[3]["ok"] is False
    assert "whole number" in results[3]["error"]

    # Check missing NaN row 5
    assert results[4]["ok"] is False
    assert "missing" in results[4]["error"]

    # Check valid row 6
    assert results[5]["ok"] is True


def test_batch_upload_with_customer_id_column(client: TestClient):
    csv_data = (
        b"user_token,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        b"USR-101,29,7,20.0,35,10,0,1\n"
        b"USR-102,40,2,8.0,10,1,3,0\n"
    )
    resp = _upload_csv_bytes(client, csv_data, params={"customer_id_column": "user_token"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid_rows"] == 2
    assert data["results"][0]["customer_id"] == "USR-101"
    assert data["results"][1]["customer_id"] == "USR-102"
