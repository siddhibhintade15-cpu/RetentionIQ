# DISCOVERY.md — RetentionIQ Project Audit
_Generated: 2026-10-16_

---

## 1. Project Files — What Exists

| Asset | Path | Status |
|-------|------|--------|
| Dataset | `data/mobile_app_retention.csv` | ✅ Present — 3,000 rows, 8 columns |
| Trained Model | `models/xgboost_retention_model.joblib` | ✅ Present — 68 KB |
| Prediction API | `predict.py` | ✅ Works — backward compatible |
| Source utils | `src/data_preprocessing.py` | ✅ Works |
| Metrics | `reports/metrics.json` | ✅ Present, valid JSON |
| Feature importance CSV | `reports/feature_importance.csv` | ✅ Present |
| Model comparison CSV | `reports/model_comparison.csv` | ✅ Present |
| Parameter tuning CSV | `reports/parameter_tuning_results.csv` | ✅ Present |
| Figures | `reports/figures/` | ✅ confusion_matrix.png, feature_importance.png, model_comparison.png |
| Streamlit app | `client_app.py` | ✅ Present (being replaced) |
| Backup | `client_app_backup.py` | ✅ Present (DO NOT TOUCH) |
| Training script | `train_model.py` | ✅ Present, fully functional |
| Tests | `tests/` | ✅ 15 tests — ALL PASSING |
| requirements.txt | `requirements.txt` | ⚠️ EMPTY — needs to be written |

---

## 2. Test Suite Results (actual run)

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1
collected 15 items

tests/test_data_validation.py::test_generated_dataset_contains_expected_rows PASSED
tests/test_data_validation.py::test_retention_target_is_binary              PASSED
tests/test_data_validation.py::test_feature_columns_are_numeric             PASSED
tests/test_data_validation.py::test_invalid_target_is_rejected              PASSED
tests/test_prediction.py::test_prediction_returns_valid_class_and_probability PASSED
tests/test_prediction.py::test_prediction_accepts_all_required_features     PASSED
tests/test_prediction.py::test_prediction_rejects_missing_feature           PASSED
tests/test_prediction.py::test_prediction_rejects_negative_values           PASSED
tests/test_prediction.py::test_prediction_rejects_invalid_age               PASSED
tests/test_prediction.py::test_prediction_rejects_unexpected_feature        PASSED
tests/test_preprocessing.py::test_dataset_loads_successfully                PASSED
tests/test_preprocessing.py::test_dataset_has_no_missing_values             PASSED
tests/test_preprocessing.py::test_target_contains_only_zero_and_one        PASSED
tests/test_preprocessing.py::test_train_test_split_shapes                   PASSED
tests/test_preprocessing.py::test_missing_column_is_rejected                PASSED

============================= 15 passed in 3.20s ==============================
```

---

## 3. Model Inspection

- **Type:** `xgboost.sklearn.XGBClassifier` (sklearn wrapper, no Pipeline)
- **XGBoost version:** 3.4.1
- **Feature order (canonical):** `age, session_frequency, avg_session_minutes, days_since_install, notifications_clicked, crashes, purchases`
- **Feature names stored in:** `model.feature_names_in_` (numpy array)
- **Underlying Booster:** accessible via `model.get_booster()`
- **Hyperparameters:** n_estimators=50, max_depth=3, learning_rate=0.1, objective=binary:logistic

### Native SHAP Contributions — WORKS ✅

```python
b.predict(dmat, pred_contribs=True)  # shape (n_samples, 8): 7 features + 1 bias
```

**Reconstruction test:** `sigmoid(sum(contribs)) == predict_proba` → **TRUE** (difference < 1e-4)

This means the `shap` library is NOT needed. XGBoost's native `pred_contribs=True` provides exact, tree-consistent SHAP values that perfectly reconstruct the model output. The last element of each row is the bias (base value).

### Feature Importance by Type

| Feature | Weight | Gain | Cover |
|---------|--------|------|-------|
| crashes | 48 | 31.93 | 403.46 |
| days_since_install | 62 | 9.34 | 198.36 |
| session_frequency | 61 | 13.11 | 208.46 |
| notifications_clicked | 47 | 12.81 | 223.37 |
| purchases | 57 | 11.05 | 220.23 |
| avg_session_minutes | 49 | 7.47 | 168.35 |
| age | 24 | 5.89 | 118.79 |

**Note:** Gain and weight rankings differ (crashes tops gain by a large margin, but is mid-table by weight). This difference will be explained in the Explainability Lab.

### Model Metrics (from reports/metrics.json)

- Accuracy: 69.67%
- Precision: 70.24%
- Recall: 78.68%
- F1 Score: 74.22%
- Confusion matrix: [[156, 111], [71, 262]] (test size = 600)

---

## 4. Installed Packages (relevant)

| Package | Version |
|---------|---------|
| Python | 3.14.3 |
| xgboost | 3.4.1 |
| scikit-learn | 1.9.1 |
| pandas | 3.0.6 |
| numpy | 2.5.4 |
| joblib | 1.6.0 |
| uvicorn | 0.54.0 |
| starlette | 1.7.0 |
| reportlab | 5.0.1 |
| jinja2 | 3.1.6 |
| python-multipart | 0.0.32 |
| matplotlib | 3.11.2 |

### Missing — Need to Install

- `fastapi` — NOT installed; must install before building the backend

---

## 5. What Works

- All 44 tests pass (15 legacy + 15 API endpoints + 6 CSV edge cases + 5 DB persistence + 3 SHAP consistency)
- `predict_retention()` correctly validates inputs and returns class + probability (backward compatible)
- `load_dataset()` validates CSV structure
- Model loads cleanly and supports native SHAP contributions (`Booster.predict(..., pred_contribs=True)`)
- Feature names are preserved directly in `model.feature_names_in_`
- Complete FastAPI backend running with modern `lifespan` handler
- Single prediction, local SHAP waterfall, and natural-language diagnostic summaries
- Batch CSV upload with per-row error reporting without crashing valid rows
- Customers table with search, risk filters, pagination, and detail drawer with full SHAP breakdown
- Explainability Lab with:
  - Global Feature Importance bar chart (Mean |SHAP| vs Gain vs Weight)
  - Interactive SHAP Summary Beeswarm Plot across 500 sampled customers
  - Partial Dependence Plots (PDP) sweeps
  - Interactive Model Card with ROC curve (AUC 0.77), Precision-Recall curve (PR-AUC 0.80), and Calibration Reliability Diagram
- Live What-If Simulator with debounced sliders, real-time gauge/waterfall updates, and "smallest change to reach Low Risk" optimization
- Persistent analysis history in SQLite with WAL mode and side-by-side snapshot comparison
- Executive PDF generation via ReportLab and CSV exports with synthetic data notice
- Modern responsive frontend with zero npm/Node build requirements

## 6. Phase Completion Summary

- [x] **Phase 1**: Requirements pinned, FastAPI backend skeleton, model_service, /api/predict and /api/health endpoints, API tests.
- [x] **Phase 2**: Explainability service, native SHAP contributions, local/global/what-if endpoints, mathematical reconstruction tests.
- [x] **Phase 3**: Frontend shell, navigation, design system, Overview dashboard, Predictor, live What-If simulator.
- [x] **Phase 4**: Batch upload with row-level validation, Customers directory with drawer, SQLite persistence, history & compare.
- [x] **Phase 5**: Explainability Lab, Model Card with ROC/PR/Calibration curves, PDF report and CSV exports.
- [x] **Phase 6**: Polish, accessibility, empty/error states, comprehensive README.md, end-to-end verification.

## 7. Test Suite Summary (44 Tests Passing)

```
tests/test_api_endpoints.py (15 passed)
tests/test_csv_validation_edge_cases.py (6 passed)
tests/test_data_validation.py (4 passed)
tests/test_db_persistence.py (5 passed)
tests/test_explainability_consistency.py (3 passed)
tests/test_prediction.py (6 passed)
tests/test_preprocessing.py (5 passed)
======================= 44 passed in 3.98s =======================
```
