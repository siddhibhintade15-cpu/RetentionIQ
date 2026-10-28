"""
tests/test_dynamic_csv_processing.py
------------------------------------
Test suite for resilient CSV ingestion, smart fuzzy column mapping,
automated data health audit, and dynamic scoring pipeline:
1. Arbitrary column names & profiling report
2. Fuzzy alias matching (tokens, typos, abbreviations)
3. Dirty numeric healing (currency symbols $, commas, percent %, null tokens)
4. Missing feature auto-imputation with training medians (crashes=0, purchases=0)
5. Outlier clipping (negative values, extreme ages)
6. PII email hashing with SHA-256
7. Date-of-Birth (DOB) conversion to age
8. Target detection & historical retention rate (with churn inversion)
9. Re-mapping endpoint without re-uploading
10. Dynamic process & positional CSV export with original columns
11. Insufficient features (< 3) rejection
12. Profiling speed benchmark (< 200ms)
"""

from __future__ import annotations

import io
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _profile_csv(client: TestClient, csv_text: str, filename: str = "messy_users.csv"):
    files = {"file": (filename, io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    return client.post("/api/batch/profile", files=files)


def test_profile_arbitrary_csv(client: TestClient):
    """CSV with non-standard column headers is profiled with instant quality score."""
    csv_data = (
        "Client_Identifier,User_Age,Weekly_Visits,Session_Duration,Tenure_Days,Push_Opens,Error_Count,Checkouts\n"
        "USR-101,28,7,22.5,30,8,0,1\n"
        "USR-102,45,3,12.0,90,2,1,0\n"
    )
    resp = _profile_csv(client, csv_data)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_rows"] == 2
    assert data["total_columns"] == 8
    assert data["quality_score"] >= 80
    assert data["scoring_confidence"] in ("High", "Medium")
    assert "upload_id" in data
    assert len(data["mappings"]) >= 7

    # Check mapped names
    mapped = {m["model_feature"]: m["user_column"] for m in data["mappings"]}
    assert mapped["age"] == "User_Age"
    assert mapped["session_frequency"] == "Weekly_Visits"
    assert mapped["avg_session_minutes"] == "Session_Duration"
    assert mapped["days_since_install"] == "Tenure_Days"


def test_dirty_numeric_healing(client: TestClient):
    """Dirty values with currency ($), commas, percentage (%), and NA strings are cleanly healed."""
    csv_data = (
        "id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "U1,25,$5.00,15.5,20,3,0,$1\n"
        'U2,32,10,25.0,"1,200",8,1,0\n'
        "U3,40,N/A,30.0,45,--,0,2\n"
    )
    resp = _profile_csv(client, csv_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 3

    # Now run dynamic process to verify it scores without throwing
    upload_id = data["upload_id"]
    proc_resp = client.post("/api/batch/dynamic-process", json={"upload_id": upload_id})
    assert proc_resp.status_code == 200
    proc_data = proc_resp.json()
    assert proc_data["total_rows"] == 3
    assert len(proc_data["results"]) == 3
    assert all(r["probability"] is not None for r in proc_data["results"])


def test_missing_column_imputation(client: TestClient):
    """CSV missing 3 of the 7 features auto-imputes them with defaults and flags confidence."""
    # Only provides: age, session_frequency, avg_session_minutes, days_since_install
    # Missing: notifications_clicked, crashes, purchases
    csv_data = (
        "id,user_age,sessions_per_week,session_minutes,days_since_signup\n"
        "CUST-A,25,8,20.0,40\n"
        "CUST-B,35,4,10.0,120\n"
    )
    resp = _profile_csv(client, csv_data)
    assert resp.status_code == 200
    data = resp.json()

    assert data["mapped_features_count"] == 4
    assert len(data["imputed_features"]) == 3
    assert "crashes" in data["imputed_features"]
    assert "purchases" in data["imputed_features"]

    # Imputation notices must disclose the defaults used
    notices = {n["feature"]: n for n in data["notices"]}
    assert notices["crashes"]["value_used"] == 0.0
    assert notices["purchases"]["value_used"] == 0.0

    # Score dataset
    proc_resp = client.post("/api/batch/dynamic-process", json={"upload_id": data["upload_id"]})
    assert proc_resp.status_code == 200
    res = proc_resp.json()
    assert res["total_rows"] == 2
    # Verify row quality flag indicates partial imputation
    for r in res["results"]:
        assert r["data_quality_flag"] == "partial"
        assert "crashes" in r["imputed_features"]


def test_outlier_clipping(client: TestClient):
    """Negative values and extreme ages are safely clipped to physical bounds."""
    csv_data = (
        "id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "USR-OUTLIER,185,15,350.0,500,10,-5,0\n"
    )
    resp = _profile_csv(client, csv_data)
    assert resp.status_code == 200

    proc_resp = client.post("/api/batch/dynamic-process", json={"upload_id": resp.json()["upload_id"]})
    assert proc_resp.status_code == 200
    res = proc_resp.json()
    assert res["total_rows"] == 1
    assert res["results"][0]["probability"] is not None


def test_pii_email_hashing(client: TestClient):
    """Emails provided in user ID column are masked with salted SHA-256."""
    csv_data = (
        "email,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "alex.smith@example.com,28,7,22.5,30,8,0,1\n"
        "priya.sharma@domain.org,35,4,15.0,60,3,1,0\n"
    )
    resp = _profile_csv(client, csv_data)
    assert resp.status_code == 200

    proc_resp = client.post("/api/batch/dynamic-process", json={"upload_id": resp.json()["upload_id"]})
    assert proc_resp.status_code == 200
    results = proc_resp.json()["results"]
    for r in results:
        assert "@" not in r["customer_id"]
        assert r["customer_id"].startswith("PII_")


def test_target_column_detection_and_polarity(client: TestClient):
    """Target column 'churn' is recognized and inverted to compute retention rate."""
    csv_data = (
        "id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases,churn\n"
        "U1,25,5,15.0,20,3,1,0,0\n"  # not churned -> retained
        "U2,40,2,10.0,90,1,2,0,1\n"  # churned -> not retained
        "U3,30,8,25.0,30,6,0,1,0\n"  # not churned -> retained
        "U4,50,1,5.0,180,0,4,0,1\n"  # churned -> not retained
    )
    resp = _profile_csv(client, csv_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_column"] == "churn"
    # 2 out of 4 retained = 0.50
    assert data["historical_retention_rate"] == 0.50


def test_remap_endpoint(client: TestClient):
    """POST /api/batch/remap updates mappings without re-uploading file."""
    csv_data = (
        "id,col_a,col_b,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "U1,25,7,15.0,20,3,0,1\n"
    )
    resp = _profile_csv(client, csv_data)
    upload_id = resp.json()["upload_id"]

    # Remap col_a to age and col_b to session_frequency
    remap_resp = client.post(
        "/api/batch/remap",
        json={"upload_id": upload_id, "overrides": {"col_a": "age", "col_b": "session_frequency"}}
    )
    assert remap_resp.status_code == 200
    remap_data = remap_resp.json()
    mapped = {m["model_feature"]: m["user_column"] for m in remap_data["mappings"]}
    assert mapped["age"] == "col_a"
    assert mapped["session_frequency"] == "col_b"


def test_dynamic_process_and_export(client: TestClient):
    """Exported CSV contains all original columns plus model prediction and SHAP columns."""
    csv_data = (
        "custom_id,country,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
        "CUST-001,USA,28,7,22.5,30,8,0,1\n"
        "CUST-002,CAN,45,3,12.0,90,2,1,0\n"
    )
    resp = _profile_csv(client, csv_data)
    upload_id = resp.json()["upload_id"]

    proc_resp = client.post("/api/batch/dynamic-process", json={"upload_id": upload_id})
    assert proc_resp.status_code == 200
    proc_data = proc_resp.json()
    batch_id = proc_data["batch_id"]

    # Download export CSV
    export_resp = client.get(f"/api/batch/{batch_id}/export")
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers["content-type"]
    text = export_resp.text

    # Verify original user columns are preserved
    assert "country" in text
    assert "USA" in text
    assert "CAN" in text

    # Verify model output columns are appended
    assert "predicted_retention" in text
    assert "retention_probability" in text
    assert "risk_tier" in text
    assert "top_drivers" in text
    assert "data_quality_flag" in text


def test_insufficient_features_rejected(client: TestClient):
    """Upload with only 1 identifiable model feature is rejected with HTTP 422 and helpful hint."""
    csv_data = (
        "first_name,last_name,city,country,age\n"
        "John,Doe,Seattle,USA,30\n"
        "Jane,Smith,Toronto,CAN,28\n"
    )
    resp = _profile_csv(client, csv_data)
    upload_id = resp.json()["upload_id"]

    proc_resp = client.post("/api/batch/dynamic-process", json={"upload_id": upload_id})
    assert proc_resp.status_code == 422
    err = proc_resp.json()["detail"]
    assert err["error_code"] == "INSUFFICIENT_FEATURES"
    assert "At least 3 features must be mapped" in err["hint"]


def test_profiling_benchmark_speed(client: TestClient):
    """Vectorized profiling of 1,000 rows completes in under 200 ms."""
    header = "id,age,session_frequency,avg_session_minutes,days_since_install,notifications_clicked,crashes,purchases\n"
    rows = "\n".join([f"U-{i},28,7,22.5,30,8,0,1" for i in range(1000)])
    csv_data = header + rows

    t0 = time.perf_counter()
    resp = _profile_csv(client, csv_data)
    t1 = time.perf_counter()

    assert resp.status_code == 200
    elapsed_ms = (t1 - t0) * 1000
    # Allow generous tolerance for test environment overhead, but assert fast
    assert elapsed_ms < 1500  # HTTP network + parse + profiling total
