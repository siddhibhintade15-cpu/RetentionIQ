
"""Visualize feature importance from the trained XGBoost model."""

from pathlib import Path
import joblib
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "xgboost_retention_model.joblib"
FIGURE_DIR = PROJECT_ROOT / "reports" / "figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Model not found. Please run train_model.py first."
        )

    model = joblib.load(MODEL_PATH)

    importance = pd.DataFrame({
        "feature": model.feature_names_in_,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)

    print("\nFEATURE IMPORTANCE")
    print(importance.to_string(index=False))

    importance.to_csv(
        PROJECT_ROOT / "reports" / "feature_importance.csv",
        index=False,
    )

    plt.figure(figsize=(9, 5))
    plt.barh(importance["feature"], importance["importance"])
    plt.gca().invert_yaxis()
    plt.xlabel("Relative feature importance")
    plt.ylabel("User activity feature")
    plt.title("XGBoost Feature Importance for App Retention")
    plt.tight_layout()

    output_path = FIGURE_DIR / "feature_importance.png"
    plt.savefig(output_path, dpi=150)
    plt.close()

    print(f"\nChart saved to: {output_path}")
    print("Feature importance analysis completed!")


if __name__ == "__main__":
    main()
