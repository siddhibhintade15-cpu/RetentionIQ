"""
tests/test_api_endpoints.py
---------------------------
Pytest suite using FastAPI TestClient to test all REST API endpoints:
meta, health, predict, explain, customers, batch, history, reports.
"""

from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.model_service import FEATURES, model_service


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_features():
    return {
        "age": 28,
        "session_frequency": 7,
        "avg_session_minutes": 22.5,
        "days_since_install": 30,
        "notifications_clicked": 12,
        "crashes": 0,
        "purchases": 1,
    }


def test_health_endpoint(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert "version" in data


def test_meta_endpoint(client: TestClient):
    resp = client.get("/api/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_info" in data
    assert "metrics" in data
    assert "synthetic_data_notice" in data
    assert data["model_info"]["library"] == "xgboost"
    assert data["model_info"]["features"] == FEATURES


def test_meta_curves_endpoint(client: TestClient):
    resp = client.get("/api/meta/curves")
    assert resp.status_code == 200
    data = resp.json()
    assert "roc" in data
    assert "pr" in data
    assert "calibration" in data
    assert "auc" in data["roc"]
    assert 0.5 <= data["roc"]["auc"] <= 1.0
    assert "auc" in data["pr"]
    assert len(data["calibration"]["prob_true"]) > 0


def test_predict_single_endpoint(client: TestClient, sample_features):
    resp = client.post("/api/predict/", json=sample_features)
    assert resp.status_code == 200
    data = resp.json()
    assert data["prediction"] in (0, 1)
    assert 0.0 <= data["probability"] <= 1.0
    assert data["risk_level"] in ("High", "Medium", "Low")
    assert data["customer_db_id"] is not None
    assert "Synthetic data" in data["synthetic_data_notice"]


def test_predict_invalid_feature(client: TestClient, sample_features):
    invalid_data = dict(sample_features)
    invalid_data["age"] = 15  # < 18
    resp = client.post("/api/predict/", json=invalid_data)
    assert resp.status_code == 422  # Pydantic validation error


def test_explain_local_endpoint(client: TestClient, sample_features):
    resp = client.post("/api/explain/local", json=sample_features)
    assert resp.status_code == 200
    data = resp.json()
    assert "contribs" in data
    assert "bias" in data
    assert "plain_english" in data
    assert "actions" in data
    assert len(data["contribs"]) == len(FEATURES)


def test_explain_global_endpoint(client: TestClient):
    resp = client.get("/api/explain/global")
    assert resp.status_code == 200
    data = resp.json()
    assert "mean_abs_shap" in data
    assert "gain" in data
    assert "weight" in data
    assert "all_shap_values" in data
    assert "all_feature_values" in data
    assert data["n_samples"] > 0


def test_explain_whatif_endpoint(client: TestClient, sample_features):
    # High risk input: many crashes, low sessions
    high_risk_input = dict(sample_features)
    high_risk_input["crashes"] = 5
    high_risk_input["session_frequency"] = 1
    resp = client.post("/api/explain/whatif", json=high_risk_input)
    assert resp.status_code == 200
    data = resp.json()
    assert "feasible" in data
    assert "current_probability" in data
    assert "suggestions" in data


def test_explain_pdp_endpoint(client: TestClient):
    resp = client.get("/api/explain/pdp/crashes?n_points=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature"] == "crashes"
    assert len(data["x"]) == 20
    assert len(data["y"]) == 20


def test_explain_pdp_invalid_feature(client: TestClient):
    resp = client.get("/api/explain/pdp/non_existent_feature")
    assert resp.status_code == 400


def test_customers_list_and_overview(client: TestClient):
    resp = client.get("/api/customers/overview")
    assert resp.status_code == 200
    stats = resp.json()
    assert "total_customers" in stats
    assert "histogram" in stats

    list_resp = client.get("/api/customers/?limit=10&offset=0")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "items" in data
    assert "total" in data


def test_customer_detail_endpoint(client: TestClient, sample_features):
    # Create customer
    pred_resp = client.post("/api/predict/", json=sample_features)
    cid = pred_resp.json()["customer_db_id"]

    detail_resp = client.get(f"/api/customers/{cid}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == cid
    assert "explanation" in detail
    assert "plain_english" in detail["explanation"]


def test_customers_export_csv(client: TestClient):
    resp = client.get("/api/customers/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.text
    assert "Synthetic data" in text
    assert "prediction,probability,risk_level" in text


def test_history_and_compare(client: TestClient):
    # Save snapshot A
    res_a = client.post("/api/history/", json={"name": "Snapshot A"})
    assert res_a.status_code == 200
    id_a = res_a.json()["id"]

    # Save snapshot B
    res_b = client.post("/api/history/", json={"name": "Snapshot B"})
    assert res_b.status_code == 200
    id_b = res_b.json()["id"]

    # Compare A and B
    comp_resp = client.get(f"/api/history/compare/{id_a}/{id_b}")
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert "comparison" in comp_data
    assert "analysis_a" in comp_data
    assert "analysis_b" in comp_data


def test_pdf_report_endpoint(client: TestClient):
    resp = client.get("/api/reports/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 1000  # Non-trivial PDF binary
    assert resp.content.startswith(b"%PDF")
