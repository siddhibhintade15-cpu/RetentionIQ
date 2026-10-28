
"""Professional Streamlit dashboard for mobile app retention prediction."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from predict import predict_retention

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

st.set_page_config(
    page_title="RetentionIQ | User Analytics",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fb 0%, #eef2ff 100%);
    }
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }
    .hero {
        padding: 1.7rem 2rem;
        border-radius: 20px;
        color: white;
        background: linear-gradient(120deg, #172554, #4338ca, #6366f1);
        margin-bottom: 1.2rem;
    }
    .hero h1 {
        color: white;
        margin-bottom: 0.4rem;
    }
    .hero p {
        color: #e0e7ff;
        font-size: 1.05rem;
        margin-bottom: 0;
    }
    .section-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        padding: 1rem;
        border-radius: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.title("📱 RetentionIQ")
    st.caption("Machine Learning Analytics")
    page = st.radio(
        "NAVIGATION",
        ["Dashboard", "Predict Retention", "Model Insights", "About Project"],
    )
    st.divider()
    st.caption("Model: XGBoost")
    st.caption("Project: ML Mini Project")

# ---------- Header ----------
st.markdown(
    """
    <div class="hero">
        <h1>Mobile App User Retention</h1>
        <p>Predict engagement outcomes and explore model performance.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Academic prototype: the model uses synthetically generated data. "
    "Its predictions and evaluation metrics are not validated on real app users."
)

# ---------- Load reports safely ----------
def load_metrics():
    path = REPORTS_DIR / "metrics.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}


def show_image(path, caption):
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.warning(f"Chart not found: {path.name}")


metrics = load_metrics()

# ---------- Dashboard ----------
if page == "Dashboard":
    st.subheader("Project Overview")
    st.write(
        "This dashboard demonstrates how an XGBoost classifier can estimate "
        "whether a mobile app user is likely to remain active."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Test Accuracy", "69.67%")
    c2.metric("Precision", "70.24%")
    c3.metric("Recall", "78.68%")
    c4.metric("F1 Score", "74.22%")

    st.caption(
        "These are the previously recorded test results for the current model. "
        "They describe performance on a synthetic test set."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("#### Model Comparison")
        show_image(
            FIGURES_DIR / "model_comparison.png",
            "XGBoost compared with Decision Tree",
        )
    with right:
        st.markdown("#### Important Features")
        show_image(
            FIGURES_DIR / "feature_importance.png",
            "Feature importance from the trained XGBoost model",
        )

    st.markdown("#### Confusion Matrix")
    show_image(
        FIGURES_DIR / "confusion_matrix.png",
        "Actual versus predicted retention classes",
    )

    st.caption(
        "Feature importance indicates how the trained model uses features; "
        "it does not establish that a feature causes retention or churn."
    )

# ---------- Prediction ----------
elif page == "Predict Retention":
    st.subheader("Predict an Individual User")
    st.write("Enter the user's activity details, then submit the form.")

    with st.form("retention_form"):
        st.markdown("#### User Profile")
        c1, c2 = st.columns(2)

        with c1:
            age = st.number_input(
                "User age",
                min_value=18,
                max_value=100,
                value=22,
                help="Age in years.",
            )
            days_since_install = st.number_input(
                "Days since installation",
                min_value=1,
                max_value=3650,
                value=14,
                help="Number of days since the app was installed.",
            )
            avg_session_minutes = st.number_input(
                "Average session duration (minutes)",
                min_value=0.0,
                max_value=1440.0,
                value=25.0,
                help="Average duration of one session.",
            )
            session_frequency = st.number_input(
                "Sessions / activity frequency",
                min_value=0,
                max_value=100,
                value=10,
                help="Use the same counting period as the training dataset.",
            )

        with c2:
            notifications_clicked = st.number_input(
                "Notifications clicked",
                min_value=0,
                max_value=1000,
                value=8,
            )
            crashes = st.number_input(
                "App crashes",
                min_value=0,
                max_value=1000,
                value=0,
                help="Number of recorded app crashes.",
            )
            purchases = st.number_input(
                "Number of purchases",
                min_value=0,
                max_value=1000,
                value=2,
            )

        submitted = st.form_submit_button(
            "🔍 Predict User Retention",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        user_data = {
            "age": age,
            "session_frequency": session_frequency,
            "avg_session_minutes": avg_session_minutes,
            "days_since_install": days_since_install,
            "notifications_clicked": notifications_clicked,
            "crashes": crashes,
            "purchases": purchases,
        }

        try:
            prediction, probability = predict_retention(user_data)

            st.divider()
            st.subheader("Prediction Result")

            result_col, probability_col = st.columns([1, 2])

            with result_col:
                if prediction == 1:
                    st.success("Likely to be retained")
                else:
                    st.warning("Potential retention risk")

            with probability_col:
                st.metric(
                    "Estimated retention probability",
                    f"{probability:.1%}",
                )
                st.progress(max(0.0, min(1.0, float(probability))))

            if prediction == 0:
                st.markdown("**Possible actions to investigate:**")
                st.write(
                    "- Review app crashes and technical reliability.\n"
                    "- Explore whether users are engaging with key features.\n"
                    "- Test helpful onboarding or re-engagement messages."
                )
            else:
                st.markdown("**Possible actions to consider:**")
                st.write(
                    "- Continue monitoring engagement over time.\n"
                    "- Keep the app experience useful and reliable.\n"
                    "- Evaluate which features users find valuable."
                )

            st.caption(
                "This is a model estimate, not a guarantee of future behavior. "
                "Recommendations are general examples, not causal conclusions."
            )

        except (FileNotFoundError, ValueError, KeyError) as error:
            st.error(f"Prediction could not be completed: {error}")

# ---------- Model Insights ----------
elif page == "Model Insights":
    st.subheader("Model Performance and Explainability")

    st.markdown("#### Confusion Matrix")
    show_image(
        FIGURES_DIR / "confusion_matrix.png",
        "Counts of correct and incorrect test predictions",
    )

    st.markdown("#### Feature Importance")
    show_image(
        FIGURES_DIR / "feature_importance.png",
        "Relative feature importance reported by the trained model",
    )

    st.markdown("#### Model Comparison")
    comparison_path = REPORTS_DIR / "model_comparison.csv"
    if comparison_path.exists():
        try:
            comparison = pd.read_csv(comparison_path)
            st.dataframe(comparison, use_container_width=True, hide_index=True)
        except (OSError, pd.errors.ParserError) as error:
            st.error(f"Could not load comparison results: {error}")
    else:
        st.warning("Model comparison CSV has not been generated.")

    st.caption(
        "Metrics should be interpreted in the context of the synthetic dataset. "
        "Feature importance alone does not explain every individual prediction."
    )

# ---------- About ----------
elif page == "About Project":
    st.subheader("About the Project")

    st.markdown(
        """
        **Objective:** Demonstrate how machine learning can estimate mobile app
        user retention from user activity features.

        **Algorithm:** Extreme Gradient Boosting (XGBoost), a tree-boosting
        method that combines sequentially trained decision trees.

        **Input features:**
        - Age
        - Session frequency
        - Average session duration
        - Days since installation
        - Notifications clicked
        - App crashes
        - Number of purchases

        **Target:** `retained` — 1 indicates retained and 0 indicates not retained.

        **Technology stack:** Python, pandas, scikit-learn, XGBoost, Streamlit,
        Matplotlib, and joblib.

        **Limitation:** The dataset is synthetic. Results do not establish
        real-world predictive performance. A production system would require
        representative, properly consented real-world data, temporal validation,
        monitoring, and privacy safeguards.
        """
    )

    st.markdown("#### Saved Project Artifacts")
    for artifact in [
        BASE_DIR / "models" / "xgboost_retention_model.joblib",
        REPORTS_DIR / "metrics.json",
        REPORTS_DIR / "model_comparison.csv",
        REPORTS_DIR / "feature_importance.csv",
    ]:
        if artifact.exists():
            st.write(f"✅ `{artifact.relative_to(BASE_DIR)}`")
        else:
            st.write(f"⚠️ Missing: `{artifact.relative_to(BASE_DIR)}`")

st.divider()
st.caption(
    "RetentionIQ | Educational ML mini-project | XGBoost + Streamlit"
)
