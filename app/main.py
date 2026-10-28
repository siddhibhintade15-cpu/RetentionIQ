"""
app/main.py
-----------
FastAPI application entry point for RetentionIQ.

Run with:
    python -m uvicorn app.main:app --reload

API docs available at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import batch, customers, explain, history, meta, predict, reports
from app.db import init_db
from app.services.model_service import model_service

# ---------------------------------------------------------------------------
# Lifespan: load model, warm SHAP cache, initialise DB
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup:
    1. Initialise the SQLite database (create tables if missing).
    2. Load the XGBoost model into memory.
    3. Pre-compute and cache global SHAP explanations.
    """
    init_db()
    model_service.load()
    # Warm up global explanation cache (runs once, takes ~1s)
    model_service.global_contributions()
    print("RetentionIQ started. Model loaded. SHAP cache warm.")
    print("Synthetic data notice: demonstration only, not validated on real customers.")
    yield


# ---------------------------------------------------------------------------
# App definition
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RetentionIQ",
    description=(
        "XGBoost-powered mobile app user retention analytics. "
        "**IMPORTANT:** Trained on synthetic data only — not validated on real customers."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS (permissive for local dev — restrict in production)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------

app.include_router(meta.router)
app.include_router(predict.router)
app.include_router(explain.router)
app.include_router(batch.router)
app.include_router(customers.router)
app.include_router(history.router)
app.include_router(reports.router)


# ---------------------------------------------------------------------------
# Frontend: serve the SPA shell for all non-API routes
# ---------------------------------------------------------------------------

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR_PATH = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_spa(full_path: str = "") -> HTMLResponse:
    """Serve the single-page application shell for all frontend routes."""
    # Don't intercept /static, /docs, /redoc, /api routes
    if full_path.startswith(("static/", "docs", "redoc", "api/", "openapi")):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    index_path = TEMPLATE_DIR / "index.html"
    if index_path.exists():
        # Cache-busting: version string = mtime of app.js so browsers always
        # pick up the latest JavaScript after a hot-reload edit.
        js_mtime  = int((STATIC_DIR_PATH / "js"  / "app.js"   ).stat().st_mtime)
        css_mtime = int((STATIC_DIR_PATH / "css" / "style.css").stat().st_mtime)
        html = (index_path).read_text(encoding="utf-8")
        html = html.replace(
            'href="/static/css/style.css"',
            f'href="/static/css/style.css?v={css_mtime}"',
        ).replace(
            'src="/static/js/app.js"',
            f'src="/static/js/app.js?v={js_mtime}"',
        )
        return HTMLResponse(
            content=html,
            headers={"Cache-Control": "no-store"},
        )
    return HTMLResponse(content="<h1>RetentionIQ loading...</h1>", status_code=200)
