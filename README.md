# RetentionIQ — Mobile App User Retention Analytics

> **Enterprise-Grade Retention & Churn Analytics Powered by XGBoost, Native SHAP Explainability, and FastAPI.**

[![Tests: 54 Passing](https://img.shields.io/badge/tests-54%20passing-brightgreen.svg)]()
[![FastAPI](https://img.shields.io/badge/backend-FastAPI%200.115-009688.svg)]()
[![XGBoost](https://img.shields.io/badge/ML-XGBoost%203.4.1-EB5424.svg)]()
[![License: Academic / Demo](https://img.shields.io/badge/data-Synthetic%20Demo-orange.svg)]()

---

> [!WARNING]
> **Synthetic Data Disclosure**: RetentionIQ is an academic machine learning application trained exclusively on a synthetic dataset (`3,000` rows). While the underlying XGBoost model, native SHAP contributions, and mathematical evaluations are authentic, the dataset is synthetic and has not been validated on real customer populations. Do not use this model for real-world business retention interventions without independent validation.

---

## 1. Executive Summary

**RetentionIQ** bridges the gap between machine learning model development and operational product analytics. Originally developed as an academic exploration of tree-based retention classifiers, it has been transformed into a full-featured, client-ready retention analytics platform.

### What Is Real vs. What Is Synthetic?

| Component | Status | Technical Details |
| :--- | :--- | :--- |
| **Training Dataset** | **SYNTHETIC** | 3,000 rows generated via probabilistic simulation in `data/mobile_app_retention.csv`. |
| **XGBoost Model** | **REAL** | `XGBClassifier` trained and serialized in `models/xgboost_retention_model.joblib`. |
| **Model Metrics** | **REAL** | Computed on hold-out test set ($N=600$); test accuracy: 69.7%, F1 score: 74.2%. |
| **SHAP Contributions** | **REAL** | Tree SHAP calculated natively using `Booster.predict(..., pred_contribs=True)`. |
| **Predicted Probabilities** | **REAL** | Exact logistic sigmoid outputs from the model weights. |
| **Retention Playbooks** | **ILLUSTRATIVE** | Best-practice recommendations derived from feature impact patterns. |

---

## 2. Technical Architecture

RetentionIQ uses a zero-build, dependency-lean architecture that runs out-of-the-box on Windows 11 with Python standard tooling:

```
mobile_app_retention_xgboost/
├── app/
│   ├── main.py                  # FastAPI application entry point & lifespan manager
│   ├── db.py                    # SQLite persistence layer (WAL mode, transactions)
│   ├── schemas.py               # Pydantic v2 schemas with field documentation
│   ├── api/                     # REST API routers
│   │   ├── meta.py              # Health, metadata, & ROC/PR/Calibration curve endpoints
│   │   ├── predict.py           # Single-user prediction with persistence
│   │   ├── explain.py           # Local SHAP, global metrics, what-if, and PDP sweeps
│   │   ├── batch.py             # CSV batch upload with per-row error handling
│   │   ├── customers.py         # Scored customers listing, search, drawer, & CSV export
│   │   ├── history.py           # Snapshot persistence & side-by-side comparison
│   │   └── reports.py           # Executive PDF generation & metrics JSON
│   ├── services/                # Business & model service layer
│   │   ├── model_service.py     # Thread-safe model loader & native SHAP engine
│   │   ├── explain_service.py   # Plain-English summaries & what-if optimizer
│   │   ├── risk_service.py      # Risk tiers, distributions, & retention playbooks
│   │   └── report_service.py    # ReportLab PDF building & CSV cohort exporter
│   ├── static/
│   │   ├── css/style.css        # Custom design system (white theme, mesh aurora, WCAG AA)
│   │   ├── js/app.js            # Vanilla JS SPA, router, interactive canvas & charts
│   │   └── vendor/chart.umd.min.js # Vendored Chart.js 4.4.1 (100% offline support)
│   └── templates/
│       └── index.html           # SPA shell with accessible semantics
├── data/                        # Dataset storage (mobile_app_retention.csv)
├── models/                      # Serialized models (xgboost_retention_model.joblib)
├── reports/                     # Academic metrics.json & evaluation charts
├── tests/                       # 44 automated pytest tests
├── requirements.txt             # Pinned Python dependencies
└── README.md                    # Project documentation
```

---

## 3. Quickstart & Installation (Windows 11 / PowerShell)

All commands are tested and optimized for Windows PowerShell.

### Step 1: Open PowerShell in the Project Directory
```powershell
cd "C:\Users\SIDDHI BHINTADE\Desktop\mobile_app_retention_xgboost"
```

### Step 2: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first).*

### Step 3: Install Pinned Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Complete Test Suite
```powershell
python -m pytest -v
```
*Expected: 54 passed tests covering API endpoints, mathematical SHAP reconstruction, multi-tier CSV fail checks, and SQLite persistence.*

### Step 5: Start the Application
```powershell
python -m uvicorn app.main:app --reload
```

Open your browser to:
- **Application Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 4. Key Pages & Features

### 1. Overview Dashboard
- **KPI Cards**: Live customer counts by risk tier with animated count-up effects.
- **Risk Distribution**: Interactive doughnut chart breaking down High, Medium, and Low risk cohorts.
- **Retention Probability Histogram**: 10-bin distribution of scored user probabilities with risk-colored segments.
- **Priority At-Risk Table**: Clickable list of customers requiring immediate retention interventions.
- **Analysis Recap**: Summaries of recent batch scoring runs and saved snapshots.

### 2. Single-Customer Predictor
- Validated inputs for all 7 features:
  - `age`: User age in years (18–100)
  - `session_frequency`: Sessions opened per week (0–100)
  - `avg_session_minutes`: Average duration per session (0–180 min)
  - `days_since_install`: App tenure in days (1–365)
  - `notifications_clicked`: Push re-engagement interactions (0–100)
  - `crashes`: App crashes experienced (0–20)
  - `purchases`: In-app monetization transactions (0–50)
- **Animated Probability Gauge**: Color-coded arc reflecting exact probability of retention.
- **Local SHAP Waterfall**: Center-aligned waterfall showing exact positive and negative feature contributions relative to model bias.
- **Plain-English Explanations**: Automated generation of natural-language diagnostic summaries.
- **Retention Playbooks**: Actionable, feature-specific customer success tactics.

### 3. Batch Analysis & Ingestion Engine
- **Prominent Data Contract**: In-UI visual guide detailing exact column names, required vs optional pills, permitted value ranges, and null policies.
- **Template & Sample Downloads**: One-click downloads for verified blank template (`retentioniq_template.csv`) and 10-row demonstration cohort (`retentioniq_sample_valid.csv`).
- **4-Tier Fail-Check Engine**:
  - *Tier 1 (File/Transport)*: 5 MB limit enforcement, UTF-8 / Latin-1 decoding, comma/semicolon delimiter auto-detection.
  - *Tier 2 (Schema)*: Checks header existence, flags duplicate columns, and reports missing features.
  - *Tier 3 (Cell/Row)*: Coerces numeric types, verifies whole integers, enforces physical bounds, and safely skips trailing blank rows.
  - *Tier 4 (Mode)*: Dual-mode support (`strict` halts with HTTP 422 diagnostic audit; `lenient` scores valid rows and catalogs errors).
- **Interactive Actionable Error Table**: Reports `Row #`, `Customer ID`, `Column`, highlighted offending value, constraint violated, and remediation tip.
- **Direct CSV Export**: Export scored batch results with prediction, probability, and risk classifications.

### 4. Customer Directory
- Search by customer identifier or database index.
- Filter by risk level (High, Medium, Low) and sort by probability or creation date.
- **Slide-Out Detail Drawer**: Deep dive into individual customer profiles to inspect their unique SHAP waterfall and tailored action plan.
- **Batch-Filtered CSV Export**: Export filtered cohorts directly to disk.

### 5. Explainability Lab
- **Global Importance Comparison**: Mean |SHAP|, Gain, and Weight ranked side-by-side with an explanation of why tree-split frequency differs from sample impact magnitude.
- **SHAP Summary Plot (Beeswarm)**: High-DPI canvas visualization plotting 500 sampled customers with individual points color-coded by feature value (cool blue = low, hot pink = high).
- **Partial Dependence Plots (PDP)**: Interactive sweeps showing marginal retention probability response across the 5th–95th percentile of each feature.
- **Interactive Model Card**:
  - Full model hyperparameters and training configuration.
  - Test-set confusion matrix ($N=600$).
  - Interactive **ROC Curve** ($\text{AUC} = 0.77$).
  - Interactive **Precision-Recall Curve** ($\text{PR-AUC} = 0.80$).
  - Interactive **Calibration Reliability Diagram** (10 probability bins vs. observed retention rate).
  - Ethical fairness notes regarding demographic variables.

### 6. Live What-If Simulator
- Interactive sliders for all 7 features with debounced live updates.
- Real-time gauge and waterfall recalculation.
- **Smallest Change Optimizer**: Algorithmic recommender that calculates the minimum realistic feature adjustment necessary to graduate a user from High/Medium Risk to Low Risk ($\ge 70\%$).

### 7. History & Cohort Comparison
- Persistent analysis snapshots stored in SQLite.
- Side-by-side comparative analysis quantifying risk mix shift ($\% \text{ High Risk Shift}$) and average retention probability delta ($\Delta P$).

### 8. Executive Reports
- **ReportLab PDF Generator**: Automated downloadable executive summaries containing KPI tables, model validation metrics, priority at-risk rosters, and limitation disclosures.
- **CSV Data Dumps**: Formatted customer data exports containing compliance disclaimers.

---

## 5. Mathematical Explainability & Native SHAP

RetentionIQ fulfills its academic explainability requirement without external dependencies like the heavy `shap` library by leveraging XGBoost's native tree contribution algorithm:

```python
raw_contributions = booster.predict(dmatrix, pred_contribs=True)
# raw_contributions shape: (n_samples, n_features + 1)
```

### Exact Output Reconstruction
Tree SHAP contributions mathematically sum to the log-odds margin, guaranteed to reconstruct the predicted probability within $10^{-4}$ tolerance:

$$\text{margin} = \sum_{i=1}^{M} \phi_i + \phi_0$$

$$P(\text{retained} = 1) = \sigma(\text{margin}) = \frac{1}{1 + e^{-\text{margin}}}$$

Where:
- $\phi_i$ is the SHAP contribution for feature $i$
- $\phi_0$ is the model bias (base value)
- $\sigma(z)$ is the standard logistic sigmoid function

This mathematical property is verified on every test run in `tests/test_explainability_consistency.py`.

---

## 6. Testing & Quality Assurance

RetentionIQ includes 44 unit and integration tests executed with `pytest`:

```powershell
python -m pytest -v
```

### Test Coverage Highlights:
- **`tests/test_api_endpoints.py`**: Full FastAPI TestClient coverage across all endpoints (`/api/health`, `/api/meta`, `/api/meta/curves`, `/api/predict/`, `/api/explain/*`, `/api/customers/*`, `/api/history/*`, `/api/reports/*`).
- **`tests/test_explainability_consistency.py`**: Mathematical verification that native SHAP contributions plus base value reconstruct the sklearn prediction probability across individual users and random dataset samples.
- **`tests/test_csv_validation_edge_cases.py`**: Validates file security (5 MB limit, `.csv` extension verification), per-row error handling for non-numeric, negative, out-of-bounds, or NaN inputs, and customer ID mapping.
- **`tests/test_db_persistence.py`**: Validates SQLite schema generation, transaction rollback, WAL mode, filter queries, and data persistence across simulated application restarts.
- **`tests/test_data_validation.py` & `test_preprocessing.py`**: Legacy validation ensuring training data integrity and stratified split behavior.

---

## 7. Limitations & Ethical Considerations

1. **Synthetic Data**: The model reflects artificial rules generated for demonstration. Patterns (e.g. crash sensitivity) should not be assumed to reflect real user behavior.
2. **Model Accuracy**: An overall accuracy of 69.7% implies that approximately 3 out of 10 users will be misclassified. High-stakes interventions should involve human review.
3. **Protected Demographic Attributes**: The `age` feature is included for academic completeness. Demographic segmentation in commercial churn interventions requires algorithmic fairness auditing (disparate impact, demographic parity).
4. **Static Snapshot Modeling**: The model analyzes static aggregated counts rather than longitudinal time-series or survival hazard rates.
5. **Local SQLite Storage**: SQLite is suitable for single-user local analysis. Production multi-tenant deployments should migrate to PostgreSQL.

---

## 8. License & Provenance

Academic Project — Developed for mobile app user retention modeling with XGBoost. Built for demonstration and research purposes only.
#   R e t e n t i o n I Q  
 