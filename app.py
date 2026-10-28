import joblib
"""RetentionIQ client-focused mobile app retention analytics."""
import json
from datetime import datetime
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "xgboost_retention_model.joblib"
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

FEATURES = [
    "age", "session_frequency", "avg_session_minutes",
    "days_since_install", "notifications_clicked", "crashes", "purchases",
]
INTEGER_FEATURES = {
    "age", "session_frequency", "days_since_install",
    "notifications_clicked", "crashes", "purchases",
}

st.set_page_config(
    page_title="RetentionIQ | Retention Analytics",
    page_icon="ðŸ“±",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp {background:linear-gradient(135deg,#f7f8fc,#eef2ff);}
.block-container {max-width:1500px;padding-top:1.4rem;padding-bottom:3rem;}
[data-testid="stSidebar"] {background:#f0f3f9;}
.hero {padding:1.7rem 2rem;border-radius:20px;color:white;
background:linear-gradient(115deg,#172554,#4338ca,#6366f1);margin-bottom:1rem;}
.hero h1 {color:white;font-size:2.35rem;margin-bottom:.4rem;}
.hero p {color:#e0e7ff;font-size:1.05rem;margin-bottom:0;}
div[data-testid="stMetric"] {background:white;border:1px solid #e2e8f0;
padding:.9rem;border-radius:14px;box-shadow:0 3px 12px rgba(15,23,42,.035);}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_model(model_path, modified_time):
    return joblib.load(model_path)


def get_model():
    if not MODEL_PATH.exists():
        return None, f"Model file not found: {MODEL_PATH.relative_to(BASE_DIR)}"
    try:
        return load_model(str(MODEL_PATH), MODEL_PATH.stat().st_mtime), None
    except Exception as exc:
        return None, f"Could not load model: {exc}"


def validate_dataframe(raw):
    if raw.empty:
        return None, ["The uploaded CSV contains no rows."]
    df = raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        return None, [
            "Missing required columns: " + ", ".join(missing),
            "Required columns: " + ", ".join(FEATURES),
        ]
    data = df[FEATURES].copy()
    for feature in FEATURES:
        data[feature] = pd.to_numeric(data[feature], errors="coerce")
    bad_missing = data.isna().any(axis=1)
    messages = []
    if bad_missing.any():
        messages.append(f"{int(bad_missing.sum())} row(s) with missing/non-numeric values were excluded.")
        data = data.loc[~bad_missing].copy()
    if data.empty:
        return None, messages + ["No valid rows remain."]
    invalid = (data[FEATURES] < 0).any(axis=1)
    invalid |= (data["age"] < 13) | (data["age"] > 100)
    if invalid.any():
        messages.append(f"{int(invalid.sum())} row(s) with negative values or age outside 13â€“100 were excluded.")
        data = data.loc[~invalid].copy()
    if data.empty:
        return None, messages + ["No valid rows remain after range checks."]
    for feature in INTEGER_FEATURES:
        fractional = data[feature] % 1 != 0
        if fractional.any():
            messages.append(f"Fractional values in {feature} were rounded to whole numbers.")
            data.loc[:, feature] = data[feature].round()
    return data.reset_index(drop=True), messages


def predict_batch(model, data):
    X = data[FEATURES].copy()
    expected = getattr(model, "feature_names_in_", None)
    if expected is not None:
        expected = list(expected)
        missing = [name for name in expected if name not in X.columns]
        if missing:
            raise ValueError("Saved model expects different features: " + ", ".join(missing))
        X = X[expected]
    pred = model.predict(X)
    result = pd.DataFrame({"prediction_class": pred})
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        classes = list(getattr(model, "classes_", []))
        if 1 in classes:
            result["retention_probability"] = proba[:, classes.index(1)]
        elif True in classes:
            result["retention_probability"] = proba[:, classes.index(True)]
        elif proba.ndim == 2 and proba.shape[1] == 2:
            result["retention_probability"] = proba[:, 1]
        else:
            result["retention_probability"] = float("nan")
    else:
        result["retention_probability"] = float("nan")

    def status(value):
        value = str(value).strip().lower()
        if value in {"1", "true", "retained", "yes"}:
            return "Likely retained"
        if value in {"0", "false", "not retained", "no"}:
            return "At risk"
        return f"Predicted class: {value}"

    result["retention_status"] = result["prediction_class"].map(status)
    prob = pd.to_numeric(result["retention_probability"], errors="coerce")
    result["risk_level"] = "Not available"
    result.loc[prob < 0.40, "risk_level"] = "High"
    result.loc[(prob >= 0.40) & (prob < 0.70), "risk_level"] = "Medium"
    result.loc[prob >= 0.70, "risk_level"] = "Low"

    actions = []
    for _, row in data.iterrows():
        advice = []
        if row["crashes"] >= 2:
            advice.append("Investigate app crashes and stability")
        if row["session_frequency"] < 3:
            advice.append("Test a helpful re-engagement message")
        if row["notifications_clicked"] == 0:
            advice.append("Review notification relevance and opt-in preferences")
        if row["purchases"] == 0:
            advice.append("Review onboarding and value proposition")
        if row["days_since_install"] <= 7:
            advice.append("Improve first-week onboarding")
        if not advice:
            advice.append("Monitor engagement and test changes before scaling")
        actions.append("; ".join(advice[:3]))
    result["suggested_actions"] = actions
    return result.reset_index(drop=True)


def load_metrics():
    path = REPORTS_DIR / "metrics.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def pct(value):
    try:
        return "â€”" if pd.isna(value) else f"{float(value) * 100:.1f}%"
    except (ValueError, TypeError):
        return "â€”"


with st.sidebar:
    st.title("ðŸ“± RetentionIQ")
    st.caption("Mobile App Retention Analytics")
    st.divider()
    page = st.radio("WORKSPACE", [
        "Business Overview", "Upload & Analyze", "User Risk Explorer",
        "Single User Prediction", "Reports & Model", "Project & Limitations",
    ])
    st.divider()
    st.caption("Model: XGBoost")
    st.caption("Data source: CSV upload")

st.markdown("""
<div class="hero">
<h1>RetentionIQ</h1>
<p>Turn mobile app engagement data into retention insights and prioritized actions.</p>
</div>
""", unsafe_allow_html=True)
st.warning(
    "Prototype limitation: this model was trained on synthetic data. Predictions and "
    "risk bands are exploratory, not validated predictions for real customers. Validate "
    "on representative, appropriately collected real data before business use."
)

model, model_error = get_model()
if model_error:
    st.error(model_error)

if "analysis_df" not in st.session_state:
    st.session_state["analysis_df"] = None
if "source_name" not in st.session_state:
    st.session_state["source_name"] = None


if page == "Business Overview":
    st.subheader("Business Overview")
    st.write("Upload a compatible CSV to calculate business KPIs and prioritize records.")
    df = st.session_state["analysis_df"]
    if df is None or df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Users analyzed", "â€”")
        c2.metric("Predicted at risk", "â€”")
        c3.metric("Likely retained", "â€”")
        c4.metric("High-risk share", "â€”")
        st.info("No analysis yet. Open Upload & Analyze and upload a CSV.")
    else:
        n = len(df)
        at_risk = int((df["retention_status"] == "At risk").sum())
        retained = int((df["retention_status"] == "Likely retained").sum())
        high = int((df["risk_level"] == "High").sum())
        probs = pd.to_numeric(df["retention_probability"], errors="coerce")
        a, b, c, d = st.columns(4)
        a.metric("Users analyzed", f"{n:,}")
        b.metric("Predicted at risk", f"{at_risk:,}", f"{at_risk/n:.1%} of analyzed")
        c.metric("Likely retained", f"{retained:,}", f"{retained/n:.1%} of analyzed")
        d.metric("High-risk share", f"{high/n:.1%}")
        e, f = st.columns(2)
        e.metric("Average retention probability", pct(probs.mean()))
        f.metric("Source file", st.session_state.get("source_name") or "CSV")
        st.divider()
        st.subheader("Risk distribution")
        counts = df["risk_level"].value_counts().reindex(
            ["High", "Medium", "Low", "Not available"], fill_value=0
        )
        st.bar_chart(counts)
        st.subheader("Priority list: lowest predicted retention first")
        sorted_df = df.assign(_p=probs).sort_values("_p", ascending=True, na_position="last")
        st.dataframe(sorted_df.drop(columns="_p").head(15), use_container_width=True, hide_index=True)
        st.caption("Prototype thresholds: High <40%, Medium 40â€“69.9%, Low â‰¥70% retention probability. Validate thresholds before use.")

    st.divider()
    x, y, z = st.columns(3)
    x.markdown("#### 1. Detect")
    x.write("Score compatible user-activity records in one batch.")
    y.markdown("#### 2. Prioritize")
    y.write("Investigate low predicted retention probabilities and engagement signals.")
    z.markdown("#### 3. Learn")
    z.write("Measure actual outcomes after interventions; do not assume a recommendation works.")

elif page == "Upload & Analyze":
    st.subheader("Upload & Analyze")
    st.write("Upload a CSV with one row per user and the seven required model features.")
    with st.expander("Required CSV format", expanded=True):
        st.code(",".join(FEATURES), language="text")
        template = pd.DataFrame([{
            "age": 22, "session_frequency": 10, "avg_session_minutes": 25,
            "days_since_install": 14, "notifications_clicked": 8, "crashes": 0, "purchases": 2,
        }])
        st.dataframe(template, use_container_width=True, hide_index=True)
        st.download_button("Download CSV template", csv_bytes(template), "retentioniq_template.csv", "text/csv")
        st.caption("Extra columns are ignored. Column names are case-insensitive.")
    uploaded = st.file_uploader("Choose CSV file", type=["csv"])
    if uploaded:
        try:
            raw = pd.read_csv(uploaded)
            st.write(f"File: **{uploaded.name}** Â· {len(raw):,} row(s)")
            cleaned, messages = validate_dataframe(raw)
            for message in messages:
                st.warning(message)
            if cleaned is not None:
                st.success(f"{len(cleaned):,} valid row(s) ready.")
                st.dataframe(cleaned.head(10), use_container_width=True, hide_index=True)
                if st.button("Analyze users with XGBoost", type="primary", use_container_width=True):
                    if model is None:
                        st.error("Model not loaded. Check models/xgboost_retention_model.joblib.")
                    else:
                        try:
                            pred = predict_batch(model, cleaned)
                            combined = pd.concat([cleaned.reset_index(drop=True), pred], axis=1)
                            st.session_state["analysis_df"] = combined
                            st.session_state["source_name"] = uploaded.name
                            st.success("Analysis complete. Visit Business Overview or User Risk Explorer.")
                            st.dataframe(combined.head(20), use_container_width=True, hide_index=True)
                            st.download_button(
                                "Download prediction results",
                                csv_bytes(combined),
                                f"retentioniq_predictions_{datetime.now():%Y%m%d_%H%M%S}.csv",
                                "text/csv",
                            )
                        except Exception as exc:
                            st.error("Batch prediction failed. Check compatibility of model and feature columns.")
                            st.exception(exc)
            else:
                st.error("This CSV cannot be analyzed until the validation issues are corrected.")
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")
    current = st.session_state["analysis_df"]
    if current is not None and not current.empty:
        st.divider()
        st.subheader("Latest analysis")
        st.download_button("Download latest analysis", csv_bytes(current), "retentioniq_latest_analysis.csv", "text/csv", key="download_latest")

elif page == "User Risk Explorer":
    st.subheader("User Risk Explorer")
    df = st.session_state["analysis_df"]
    if df is None or df.empty:
        st.info("Upload and analyze a CSV first.")
    else:
        f1, f2 = st.columns(2)
        risks = f1.multiselect("Risk levels", ["High", "Medium", "Low", "Not available"], default=["High", "Medium"])
        query = f2.text_input("Filter by prediction status", placeholder="e.g. At risk")
        filtered = df[df["risk_level"].isin(risks)].copy()
        if query.strip():
            filtered = filtered[filtered["retention_status"].astype(str).str.contains(query.strip(), case=False, na=False)]
        probs = pd.to_numeric(filtered["retention_probability"], errors="coerce")
        filtered = filtered.assign(_p=probs).sort_values("_p", ascending=True, na_position="last").drop(columns="_p")
        st.write(f"Showing **{len(filtered):,}** record(s).")
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        st.download_button("Export filtered users", csv_bytes(filtered), "retentioniq_filtered_users.csv", "text/csv")
        st.caption("The input template has no user identifiers. Prefer pseudonymous IDs and avoid unnecessary personal data.")

elif page == "Single User Prediction":
    st.subheader("Single User Prediction")
    with st.form("single_user_form"):
        left, right = st.columns(2)
        with left:
            age = st.number_input("Age", 13, 100, 22)
            session_frequency = st.number_input("Sessions per week", 0, 200, 10)
            avg_session_minutes = st.number_input("Average session duration (minutes)", 0.0, 600.0, 25.0)
            days_since_install = st.number_input("Days since installation", 0, 5000, 14)
        with right:
            notifications_clicked = st.number_input("Notifications clicked", 0, 1000, 8)
            crashes = st.number_input("App crashes", 0, 1000, 0)
            purchases = st.number_input("Purchases", 0, 1000, 2)
        submit = st.form_submit_button("Predict retention", use_container_width=True)
    if submit:
        if model is None:
            st.error("Model could not be loaded.")
        else:
            one = pd.DataFrame([{
                "age": age, "session_frequency": session_frequency,
                "avg_session_minutes": avg_session_minutes, "days_since_install": days_since_install,
                "notifications_clicked": notifications_clicked, "crashes": crashes, "purchases": purchases,
            }])
            try:
                result = predict_batch(model, one)
                status = result.loc[0, "retention_status"]
                if status == "Likely retained":
                    st.success("Predicted class: Likely retained")
                elif status == "At risk":
                    st.warning("Predicted class: At risk")
                else:
                    st.info(status)
                a, b = st.columns(2)
                a.metric("Retention probability", pct(result.loc[0, "retention_probability"]))
                b.metric("Prototype risk band", result.loc[0, "risk_level"])
                st.markdown("### Suggested actions to consider")
                st.write(result.loc[0, "suggested_actions"])
                st.caption("Suggestions are rule-based prompts, not causal explanations or guarantees.")
                with st.expander("Technical details"):
                    st.dataframe(pd.concat([one, result], axis=1), use_container_width=True, hide_index=True)
            except Exception as exc:
                st.error("Prediction failed. Check saved-model compatibility.")
                st.exception(exc)

elif page == "Reports & Model":
    st.subheader("Reports & Model")
    metrics = load_metrics()
    if metrics:
        st.markdown("### Saved evaluation metrics")
        st.json(metrics)
    else:
        st.info("reports/metrics.json not found or unreadable.")
    st.markdown("### Previously recorded project results")
    st.dataframe(pd.DataFrame({
        "Metric": ["Accuracy", "Precision", "Recall", "F1 Score"],
        "Recorded score": ["69.67%", "70.24%", "78.68%", "74.22%"],
    }), use_container_width=True, hide_index=True)
    st.caption("Confirm recorded scores against the current evaluation report before external use.")
    chart = FIGURES_DIR / "feature_importance.png"
    if chart.exists():
        st.image(str(chart), caption="Feature importance from the saved project report", use_container_width=True)
    else:
        st.info("Feature-importance chart not found in reports/figures.")
    df = st.session_state["analysis_df"]
    if df is not None and not df.empty:
        st.download_button("Download prediction report", csv_bytes(df), "retentioniq_report.csv", "text/csv")

elif page == "Project & Limitations":
    st.subheader("Project, Methodology & Limitations")
    st.markdown("### Aim")
    st.write("Demonstrate how an XGBoost classifier can estimate mobile app retention from activity features.")
    st.markdown("### Required input features")
    st.code(", ".join(FEATURES), language="text")
    st.markdown("### Workflow")
    st.write("CSV upload â†’ validation â†’ feature preparation â†’ saved model â†’ batch predictions â†’ risk prioritization â†’ downloadable report.")
    st.markdown("### Interpretation")
    st.write(
        "- A predicted class is an estimate, not certainty about future behavior.\n"
        "- Probability is shown only when the saved model supports predict_proba.\n"
        "- Risk bands are prototype thresholds and may not be calibrated.\n"
        "- Suggested actions are simple rules and must be tested.\n"
        "- Feature importance does not prove causation."
    )
    st.warning(
        "The current model was trained on synthetic data. Patterns may not represent actual users. "
        "Before business use, validate on representative and appropriately collected data, verify labels "
        "and prediction horizon, evaluate calibration and subgroup performance, choose thresholds with "
        "stakeholders, protect personal data, and monitor model drift."
    )
    st.markdown("### Future improvements")
    st.write(
        "- Validate and calibrate with real-world outcomes.\n"
        "- Compare XGBoost with baseline models.\n"
        "- Monitor model drift.\n"
        "- Track intervention outcomes.\n"
        "- Add secure authentication and role-based access before multi-user deployment."
    )

st.divider()
st.caption("RetentionIQ Â· Mobile App Retention Analytics Â· Academic prototype")
