"""
tests/test_db_persistence.py
-----------------------------
Verifies database persistence, transaction integrity, schema initialization,
and cross-restart survival for customers, batches, and analysis snapshots.
"""

from __future__ import annotations

import json
import sqlite3
import pytest

from app.db import (
    DB_PATH,
    count_customers,
    get_analysis,
    get_batch,
    get_customer,
    get_db,
    init_db,
    insert_batch,
    insert_customer,
    list_analyses,
    list_customers,
    overview_stats,
    save_analysis,
)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


def test_customer_insert_and_retrieve():
    features = {
        "age": 31.0,
        "session_frequency": 6.0,
        "avg_session_minutes": 25.0,
        "days_since_install": 40.0,
        "notifications_clicked": 9.0,
        "crashes": 0.0,
        "purchases": 2.0,
    }
    cust_id = insert_customer(
        features=features,
        prediction=1,
        probability=0.825,
        risk_lv="Low",
        source="single",
        customer_id="TEST-USER-1",
    )
    assert cust_id > 0

    retrieved = get_customer(cust_id)
    assert retrieved is not None
    assert retrieved["customer_id"] == "TEST-USER-1"
    assert retrieved["prediction"] == 1
    assert abs(retrieved["probability"] - 0.825) < 1e-4
    assert retrieved["risk_level"] == "Low"
    assert retrieved["features"]["age"] == 31.0


def test_batch_insert_and_retrieve():
    batch_id = insert_batch(
        filename="cohort_june.csv",
        total_rows=100,
        valid_rows=95,
        error_rows=5,
        summary={"notes": "Q2 cohort"},
    )
    assert batch_id > 0

    b = get_batch(batch_id)
    assert b is not None
    assert b["filename"] == "cohort_june.csv"
    assert b["total_rows"] == 100
    assert b["valid_rows"] == 95


def test_analysis_snapshot_persistence():
    summary_data = {
        "total_customers": 50,
        "high_risk": 12,
        "medium_risk": 18,
        "low_risk": 20,
        "avg_retention_probability": 0.612,
    }
    analysis_id = save_analysis("Weekly Cohort Snapshot", summary_data)
    assert analysis_id > 0

    record = get_analysis(analysis_id)
    assert record is not None
    assert record["name"] == "Weekly Cohort Snapshot"
    assert record["summary"]["high_risk"] == 12
    assert abs(record["summary"]["avg_retention_probability"] - 0.612) < 1e-4


def test_persistence_across_simulated_restart():
    """
    Simulate app restart by establishing a brand new raw sqlite3 connection
    independent of any connection cache, and verifying data is persisted.
    """
    unique_customer_id = "PERSIST-RESTART-TEST-999"
    cust_id = insert_customer(
        features={"age": 45.0, "crashes": 0.0, "session_frequency": 12.0, "avg_session_minutes": 15.0, "days_since_install": 60.0, "notifications_clicked": 4.0, "purchases": 0.0},
        prediction=1,
        probability=0.75,
        risk_lv="Low",
        customer_id=unique_customer_id,
    )

    # Open fresh direct connection mimicking completely separate process launch
    raw_conn = sqlite3.connect(str(DB_PATH))
    raw_conn.row_factory = sqlite3.Row
    row = raw_conn.execute("SELECT * FROM customers WHERE id = ?", (cust_id,)).fetchone()
    raw_conn.close()

    assert row is not None
    assert row["customer_id"] == unique_customer_id
    assert row["prediction"] == 1
    assert row["risk_level"] == "Low"


def test_list_and_count_filters():
    total_before = count_customers()
    high_before = count_customers(risk_filter="High")

    # Insert a guaranteed high risk user
    insert_customer(
        features={"age": 22.0, "crashes": 8.0, "session_frequency": 1.0, "avg_session_minutes": 2.0, "days_since_install": 5.0, "notifications_clicked": 0.0, "purchases": 0.0},
        prediction=0,
        probability=0.15,
        risk_lv="High",
        customer_id="FILTER-TEST-HIGH",
    )

    total_after = count_customers()
    high_after = count_customers(risk_filter="High")

    assert total_after == total_before + 1
    assert high_after == high_before + 1

    # Verify search filter
    search_results = list_customers(search="FILTER-TEST-HIGH")
    assert len(search_results) >= 1
    assert search_results[0]["customer_id"] == "FILTER-TEST-HIGH"
