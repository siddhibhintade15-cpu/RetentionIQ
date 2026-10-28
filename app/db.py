"""
app/db.py
----------
SQLite-based persistence for analysis history and scored customers.
Uses the standard library `sqlite3` — no ORM needed.

IMPORTANT: SQLite is not a secure multi-user production database.
It is used here for local, single-user demonstration only.
Do not use this setup in a multi-user or internet-facing deployment.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

DB_PATH = Path(__file__).resolve().parent.parent / "retentioniq.db"


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Open a database connection with WAL mode and row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation — called on startup
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables if they do not already exist."""
    with get_db() as conn:
        conn.executescript("""
            -- Individual customer predictions scored by the user
            CREATE TABLE IF NOT EXISTS customers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                -- Optional customer identifier supplied by the user
                customer_id  TEXT,
                -- Input features (stored as JSON for flexibility)
                features     TEXT    NOT NULL,
                -- Model outputs
                prediction   INTEGER NOT NULL,
                probability  REAL    NOT NULL,
                risk_level   TEXT    NOT NULL,
                -- Source: 'single' or 'batch'
                source       TEXT    DEFAULT 'single',
                -- Batch upload identifier (null for single predictions)
                batch_id     INTEGER REFERENCES batches(id)
            );

            -- Batch upload sessions
            CREATE TABLE IF NOT EXISTS batches (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                filename     TEXT    NOT NULL,
                total_rows   INTEGER NOT NULL,
                valid_rows   INTEGER NOT NULL,
                error_rows   INTEGER NOT NULL,
                -- Summary statistics stored as JSON
                summary      TEXT
            );

            -- Named analysis snapshots (for the History & Compare page)
            CREATE TABLE IF NOT EXISTS analyses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                name         TEXT    NOT NULL,
                -- Snapshot of KPIs at the time of saving
                summary_json TEXT    NOT NULL
            );
        """)


# ---------------------------------------------------------------------------
# Customer CRUD
# ---------------------------------------------------------------------------

def insert_customer(
    features: dict[str, float],
    prediction: int,
    probability: float,
    risk_lv: str,
    source: str = "single",
    customer_id: str | None = None,
    batch_id: int | None = None,
) -> int:
    """Insert a scored customer and return the new row id."""
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO customers
                (customer_id, features, prediction, probability, risk_level, source, batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                json.dumps(features),
                prediction,
                probability,
                risk_lv,
                source,
                batch_id,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def insert_customers_bulk(
    records: list[tuple[str | None, str, int, float, str, str, int | None]]
) -> None:
    """Bulk insert scored customers in a single database transaction."""
    with get_db() as conn:
        conn.executemany(
            """
            INSERT INTO customers
                (customer_id, features, prediction, probability, risk_level, source, batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )


def get_batch(batch_id: int) -> dict[str, Any] | None:
    """Fetch a single batch record by id."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    return dict(row) if row else None


def list_customers(
    limit: int = 100,
    offset: int = 0,
    risk_filter: str | None = None,
    search: str | None = None,
    batch_id: int | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "DESC",
) -> list[dict[str, Any]]:
    """Return a paginated, filtered, sorted list of scored customers."""
    valid_sort = {"created_at", "probability", "risk_level", "customer_id"}
    valid_dir = {"ASC", "DESC"}
    sort_by = sort_by if sort_by in valid_sort else "created_at"
    sort_dir = sort_dir.upper() if sort_dir.upper() in valid_dir else "DESC"

    where_clauses: list[str] = []
    params: list[Any] = []

    if risk_filter:
        where_clauses.append("risk_level = ?")
        params.append(risk_filter)
    if search:
        where_clauses.append("customer_id LIKE ?")
        params.append(f"%{search}%")
    if batch_id is not None:
        where_clauses.append("batch_id = ?")
        params.append(batch_id)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    sql = f"""
        SELECT id, created_at, customer_id, features, prediction,
               probability, risk_level, source, batch_id
        FROM customers
        {where_sql}
        ORDER BY {sort_by} {sort_dir}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_customer_row_to_dict(r) for r in rows]


def count_customers(
    risk_filter: str | None = None,
    search: str | None = None,
    batch_id: int | None = None,
) -> int:
    """Return total count of customers matching the filter."""
    where_clauses: list[str] = []
    params: list[Any] = []
    if risk_filter:
        where_clauses.append("risk_level = ?")
        params.append(risk_filter)
    if search:
        where_clauses.append("customer_id LIKE ?")
        params.append(f"%{search}%")
    if batch_id is not None:
        where_clauses.append("batch_id = ?")
        params.append(batch_id)
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) FROM customers {where_sql}", params
        ).fetchone()
    return row[0]


def get_customer(customer_db_id: int) -> dict[str, Any] | None:
    """Fetch a single customer by database id."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_db_id,)
        ).fetchone()
    if row is None:
        return None
    return _customer_row_to_dict(row)


def overview_stats() -> dict[str, Any]:
    """Compute KPI stats for the Overview page from the customers table."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        if total == 0:
            return {
                "total_customers": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0,
                "avg_retention_probability": None,
                "latest_batch_id": None,
                "histogram": {
                    "labels": ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%", "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"],
                    "counts": [0] * 10,
                },
                "latest_batch": None,
                "latest_analysis": None,
            }
        counts = conn.execute(
            """
            SELECT risk_level, COUNT(*) as n
            FROM customers
            GROUP BY risk_level
            """
        ).fetchall()
        risk_counts = {r["risk_level"]: r["n"] for r in counts}
        avg_prob = conn.execute(
            "SELECT AVG(probability) FROM customers"
        ).fetchone()[0]
        
        # Calculate retention probability histogram (10 bins: 0.0-0.1, ..., 0.9-1.0)
        prob_rows = conn.execute("SELECT probability FROM customers").fetchall()
        hist_counts = [0] * 10
        for r in prob_rows:
            p = float(r[0])
            bin_idx = min(int(p * 10), 9)
            hist_counts[bin_idx] += 1
        
        latest_batch_row = conn.execute(
            "SELECT id, filename, total_rows, valid_rows, created_at FROM batches ORDER BY id DESC LIMIT 1"
        ).fetchone()
        latest_batch = dict(latest_batch_row) if latest_batch_row else None

        latest_analysis_row = conn.execute(
            "SELECT id, name, created_at, summary_json FROM analyses ORDER BY id DESC LIMIT 1"
        ).fetchone()
        latest_analysis = None
        if latest_analysis_row:
            latest_analysis = dict(latest_analysis_row)
            latest_analysis["summary"] = json.loads(latest_analysis.pop("summary_json", "{}"))

    return {
        "total_customers": total,
        "high_risk": risk_counts.get("High", 0),
        "medium_risk": risk_counts.get("Medium", 0),
        "low_risk": risk_counts.get("Low", 0),
        "avg_retention_probability": round(float(avg_prob), 4) if avg_prob else None,
        "latest_batch_id": latest_batch["id"] if latest_batch else None,
        "histogram": {
            "labels": ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%", "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"],
            "counts": hist_counts,
        },
        "latest_batch": latest_batch,
        "latest_analysis": latest_analysis,
    }


# ---------------------------------------------------------------------------
# Batch CRUD
# ---------------------------------------------------------------------------

def insert_batch(
    filename: str,
    total_rows: int,
    valid_rows: int,
    error_rows: int,
    summary: dict[str, Any] | None = None,
) -> int:
    """Create a batch record and return its id."""
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO batches (filename, total_rows, valid_rows, error_rows, summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            (filename, total_rows, valid_rows, error_rows, json.dumps(summary or {})),
        )
        return cur.lastrowid  # type: ignore[return-value]


def list_batches(limit: int = 20) -> list[dict[str, Any]]:
    """Return most recent batches."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM batches ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Analysis history CRUD
# ---------------------------------------------------------------------------

def save_analysis(name: str, summary: dict[str, Any]) -> int:
    """Persist a named analysis snapshot and return its id."""
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO analyses (name, summary_json) VALUES (?, ?)",
            (name, json.dumps(summary)),
        )
        return cur.lastrowid  # type: ignore[return-value]


def list_analyses(limit: int = 50) -> list[dict[str, Any]]:
    """Return analyses ordered by most recent first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["summary"] = json.loads(d.pop("summary_json", "{}"))
        result.append(d)
    return result


def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    """Fetch a single analysis by id."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["summary"] = json.loads(d.pop("summary_json", "{}"))
    return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _customer_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["features"] = json.loads(d.get("features", "{}"))
    return d
