
"""RetentionIQ - Mobile App User Retention Prediction."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from predict import predict_retention


# ==================== PATHS ====================
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"


# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="RetentionIQ | User Analytics",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==================== CUSTOM CSS ====================
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fb, #eef2ff);
    }
    .block-container {
        max-width: 1450px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
    [data-testid="stSidebar"] {
        background: #f0f3f9;
    }
    .hero {
        padding: 2rem;
        border-radius: 20px;
        color: white;
        background: linear-gradient(120deg, #172554, #4338ca, #6366f1);
        margin-bottom: 1.2rem;
    }
    .hero h1 {
        color: white;
        font-size: 2.35rem;
        font-weight: 800;
    }
    .hero p {
        color: #e0e7ff;
        font-size: 1.05rem;
    }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        padding: 1rem;
        border-radius: 14px;
    }
    div.stButton > button,
    div.stFormSubmitButton > button {
        border-radius: 10px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================== HELPER FUNCTIONS ====================
def load_metrics():
    """Load saved evaluation metrics."""
    file_path = REPORTS_DIR / "metrics.json"

    if not file_path.exists():
        return {}

    try:
        with file_path.open("r", encoding="utf-8") as file:
            result = json.load(file)
        return result if isinstance(result, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def show_image(path, caption):
    """Display a chart if it exists."""
    if path.exists():
        st.image(
            str(path),
            caption=caption,
            use_container_width=True,
        )
    else:
        st.info(
            f"{path.name} is not available. "
            "Check your reports/figures folder."
        )


def show_metric_table():
    """Show recorded model evaluation results."""
    data = pd.DataFrame(
        {
            "Metric": ["Accuracy", "Precision", "Recall", "F1 Score"],
            "Score (%)": [69.67, 70.24, 78.68, 74.22],
        }
    )
    st.dataframe(data, use_container_width=True, hide_index=True)


def navigate_to(destination):
    """Change pages through a button callback."""
    st.session_state["navigation"] = destination


def show_prediction_result(result):
    """Display the result returned by predict_retention()."""
    if not isinstance(result, dict):
        st.write(result)
        return

    label = result.get(
        "prediction",
        result.get("label", result.get("retained", result.get("result"))),
    )
    probability = result.get(
        "probability",
        result.get("retention_probability"),
    )

    if label is not None:
        label_text = str(label).strip().lower()

        if label_text in {
            "1", "true", "retained", "likely to be retained"
        }:
            st.success("✅ Likely to be retained")
        elif label_text in {
            "0", "false", "not retained", "unlikely to be retained"
        }:
            st.warning("⚠️ May not be retained")
        else:
            st.write(f"**Prediction:** {label}")

    if probability is not None:
        try:
            probability = float(probability)

            # Fractions such as 0.856 are converted to 85.6%.
            if 0 <= probability <= 1:
                probability *= 100

            probability = max(0.0, min(100.0, probability))

            st.metric(
                "Retention Probability",
                f"{probability:.1f}%",
            )
            st.progress(probability / 100)

        except (TypeError, ValueError):
            st.write(f"**Probability:** {probability}")

    with st.expander("View prediction details"):
        st.json(result)


# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("📱 RetentionIQ")
    st.caption("Machine Learning Analytics")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "Predict Retention",
            "Model Insights",
            "About Project",
        ],
        key="navigation",
    )

    st.divider()
    st.caption("Model: XGBoost")
    st.caption("Project: ML Mini Project")
    st.caption("Mobile App User Retention Prediction")


# ==================== MAIN HEADER ====================
st.markdown(
    """
    <div class="hero">
        <h1>Mobile App User Retention</h1>
        <p>
            Understand user engagement, estimate retention,
            and explore data-driven improvement opportunities.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Academic prototype: this model uses synthetically generated data. "
    "Its predictions and evaluation metrics have not been validated "
    "on real mobile app users."
)


# ==========================================================
# PAGE 1: DASHBOARD
# ==========================================================
if page == "Dashboard":

    st.subheader("📊 Project Dashboard")
    st.write(
        "Explore the project objective, model performance, "
        "and mobile app retention analysis."
    )

    # Summary cards
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Algorithm", "XGBoost")
    col2.metric("Test Samples", "600")
    col3.metric("Accuracy", "69.67%")
    col4.metric("F1 Score", "74.22%")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("### 🎯 Project Objective")
        st.write(
            "Predict whether a mobile app user is likely to remain "
            "active using activity and engagement information."
        )

        st.markdown("### 📌 Input Features")
        st.write(
            "- Age\n"
            "- Session frequency\n"
            "- Average session duration\n"
            "- Days since installation\n"
            "- Notifications clicked\n"
            "- App crashes\n"
            "- Number of purchases"
        )

    with right:
        st.markdown("### ⚙️ Project Workflow")
        st.write(
            "1. Prepare the dataset.\n"
            "2. Train the XGBoost model.\n"
            "3. Evaluate its performance.\n"
            "4. Enter user details.\n"
            "5. Display the retention prediction."
        )

        st.markdown("### 💡 Practical Importance")
        st.write(
            "Retention analysis can help product teams investigate "
            "engagement patterns and plan experiments to improve "
            "the user experience."
        )

    st.divider()
    st.subheader("📈 Model Performance")
    show_metric_table()

    st.caption(
        "Recorded test results from this project, not verified "
        "performance on real-world mobile app users."
    )

    st.divider()
    st.subheader("🔍 Feature Importance")
    st.write(
        "Feature importance describes how the trained model uses "
        "different features. It does not prove causation."
    )

    show_image(
        FIGURES_DIR / "feature_importance.png",
        "Feature importance from the trained XGBoost model",
    )

    st.divider()
    st.subheader("🚀 Explore the Project")

    card1, card2, card3 = st.columns(3)

    with card1:
        st.markdown("#### 🔮 Predict Retention")
        st.write("Enter a user's activity details.")
        st.button(
            "Open Prediction",
            key="open_prediction",
            on_click=navigate_to,
            args=("Predict Retention",),
            use_container_width=True,
        )

    with card2:
        st.markdown("#### 📊 Model Insights")
        st.write("Review metrics and feature importance.")
        st.button(
            "View Insights",
            key="open_insights",
            on_click=navigate_to,
            args=("Model Insights",),
            use_container_width=True,
        )

    with card3:
        st.markdown("#### ℹ️ About Project")
        st.write("Learn about the workflow and technologies.")
        st.button(
            "About Project",
            key="open_about",
            on_click=navigate_to,
            args=("About Project",),
            use_container_width=True,
        )


# ==========================================================
# PAGE 2: PREDICT RETENTION
# ==========================================================
elif page == "Predict Retention":

    st.subheader("🔮 Predict Mobile App User Retention")
    st.write(
        "Enter the user's activity information and submit "
        "the form to generate a model prediction."
    )

    with st.form("retention_prediction_form"):

        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input(
                "User Age",
                min_value=13,
                max_value=100,
                value=22,
                step=1,
            )

            session_frequency = st.number_input(
                "Sessions per Week",
                min_value=0,
                max_value=200,
                value=10,
                step=1,
            )

            avg_session_minutes = st.number_input(
                "Average Session Duration (minutes)",
                min_value=0.0,
                max_value=600.0,
                value=25.0,
                step=1.0,
            )

            days_since_install = st.number_input(
                "Days Since Installation",
                min_value=0,
                max_value=5000,
                value=14,
                step=1,
            )

        with col2:
            notifications_clicked = st.number_input(
                "Notifications Clicked",
                min_value=0,
                max_value=1000,
                value=8,
                step=1,
            )

            crashes = st.number_input(
                "Number of App Crashes",
                min_value=0,
                max_value=1000,
                value=0,
                step=1,
            )

            purchases = st.number_input(
                "Number of Purchases",
                min_value=0,
                max_value=1000,
                value=2,
                step=1,
            )

        submitted = st.form_submit_button(
            "✨ Predict Retention",
            use_container_width=True,
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
            result = predict_retention(user_data)

            st.divider()
            st.subheader("Prediction Result")
            show_prediction_result(result)

            st.caption(
                "This is a model estimate, not a guarantee "
                "of future user behavior."
            )

        except Exception as exc:
            st.error(
                "Prediction failed. Check predict.py and the trained "
                "model file. The prediction function must accept a "
                "dictionary containing the seven input features."
            )

            with st.expander("Technical error details"):
                st.exception(exc)


# ==========================================================
# PAGE 3: MODEL INSIGHTS
# ==========================================================
elif page == "Model Insights":

    st.subheader("📈 Model Insights")
    st.write(
        "Review evaluation metrics and inspect the model's "
        "feature-importance chart."
    )

    st.markdown("### Evaluation Metrics")

    metrics = load_metrics()

    if metrics:
        st.json(metrics)
    else:
        st.info(
            "reports/metrics.json was not found or could not be read. "
            "The recorded test results are shown below."
        )
        show_metric_table()

    st.divider()
    st.markdown("### Understanding the Metrics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Accuracy")
        st.write(
            "The percentage of test examples classified correctly."
        )

        st.markdown("#### Precision")
        st.write(
            "Among users predicted as retained, the proportion "
            "actually retained in the test labels."
        )

    with col2:
        st.markdown("#### Recall")
        st.write(
            "Among users actually retained in the test labels, "
            "the proportion correctly identified by the model."
        )

        st.markdown("#### F1 Score")
        st.write(
            "The harmonic mean of precision and recall."
        )

    st.divider()
    st.markdown("### Feature Importance")

    show_image(
        FIGURES_DIR / "feature_importance.png",
        "Relative feature importance from the trained model",
    )

    st.caption(
        "Feature importance shows model usage; it does not prove "
        "that a feature causes retention or churn."
    )

    st.divider()
    st.markdown("### Recorded Test Results")
    show_metric_table()

    st.warning(
        "The dataset is synthetic. These results are not validated "
        "real-world performance."
    )


# ==========================================================
# PAGE 4: ABOUT PROJECT
# ==========================================================
elif page == "About Project":

    st.subheader("📱 About RetentionIQ")
    st.write(
        "RetentionIQ is an academic machine learning mini-project "
        "that demonstrates how an XGBoost classifier can estimate "
        "mobile app user retention."
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎯 Project Aim")
        st.write(
            "Build a machine learning prototype that predicts a "
            "mobile app user's retention class from activity features."
        )

        st.markdown("### 🧰 Technology Stack")
        st.write(
            "- Python\n"
            "- Pandas\n"
            "- Streamlit\n"
            "- XGBoost\n"
            "- Scikit-learn\n"
            "- Matplotlib"
        )

    with col2:
        st.markdown("### 🔄 Project Workflow")
        st.write(
            "1. Dataset preparation\n"
            "2. Data validation and preprocessing\n"
            "3. Train/test split\n"
            "4. XGBoost model training\n"
            "5. Model evaluation\n"
            "6. Retention prediction\n"
            "7. Dashboard visualization"
        )

        st.markdown("### 📂 Project Files")
        st.code(
            "app.py              # Streamlit dashboard\n"
            "predict.py          # Prediction logic\n"
            "models/             # Trained model files\n"
            "reports/            # Evaluation outputs\n"
            "reports/figures/    # Generated charts",
            language="text",
        )

    st.divider()
    st.markdown("### ⚠️ Project Limitations")

    st.warning(
        "This prototype uses synthetically generated data. The data "
        "may not represent actual mobile app users. Real-world "
        "deployment would require suitable real data, independent "
        "validation, monitoring, and privacy safeguards."
    )

    st.markdown("### 🌟 Potential Future Improvements")
    st.write(
        "- Evaluate on real, appropriately consented user data.\n"
        "- Compare additional classification algorithms.\n"
        "- Add model monitoring and drift detection.\n"
        "- Improve explanations of individual predictions.\n"
        "- Study which retention interventions are effective."
    )


# ==================== FOOTER ====================
st.divider()
st.caption(
    "RetentionIQ | Mobile App User Retention Prediction | "
    "Academic Machine Learning Prototype"
)
