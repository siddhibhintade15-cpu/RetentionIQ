
"""Train and evaluate an XGBoost mobile retention classifier."""

import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from joblib import dump
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from src.data_preprocessing import load_dataset, prepare_data


ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
FIGURE_DIR = REPORT_DIR / "figures"

MODEL_PATH = MODEL_DIR / "xgboost_retention_model.joblib"


def evaluate_model(name, model, X_test, y_test):
    """Generate predictions and calculate evaluation metrics."""
    start = time.perf_counter()
    predictions = model.predict(X_test)
    prediction_time = time.perf_counter() - start

    return {
        "model": name,
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(
            y_test, predictions, zero_division=0
        ),
        "recall": recall_score(
            y_test, predictions, zero_division=0
        ),
        "f1_score": f1_score(
            y_test, predictions, zero_division=0
        ),
        "prediction_time_seconds": prediction_time,
        "predictions": predictions,
    }


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load and split the dataset.
    df = load_dataset()
    X_train, X_test, y_train, y_test = prepare_data(df)

    # 2. Make a validation set from training data for tuning.
    X_fit, X_val, y_fit, y_val = train_test_split(
        X_train,
        y_train,
        test_size=0.2,
        random_state=42,
        stratify=y_train,
    )

    # 3. Compare three XGBoost configurations using validation F1.
    configurations = [
        {"n_estimators": 50, "max_depth": 3, "learning_rate": 0.10},
        {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.10},
        {"n_estimators": 100, "max_depth": 5, "learning_rate": 0.05},
    ]

    tuning_results = []
    best_model = None
    best_config = None
    best_f1 = -1

    print("\nPARAMETER TUNING")
    for config in configurations:
        model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            n_jobs=2,
            random_state=42,
            **config,
        )

        start = time.perf_counter()
        model.fit(X_fit, y_fit)
        training_time = time.perf_counter() - start

        val_predictions = model.predict(X_val)
        val_f1 = f1_score(
            y_val, val_predictions, zero_division=0
        )

        tuning_results.append({
            **config,
            "validation_f1": val_f1,
            "training_time_seconds": training_time,
        })

        print(
            f"{config} | Validation F1: {val_f1:.4f} "
            f"| Training time: {training_time:.2f}s"
        )

        if val_f1 > best_f1:
            best_f1 = val_f1
            best_config = config

    # 4. Train the selected model on the complete training split.
    best_model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_jobs=2,
        random_state=42,
        **best_config,
    )

    start = time.perf_counter()
    best_model.fit(X_train, y_train)
    training_time = time.perf_counter() - start

    dump(best_model, MODEL_PATH)

    # 5. Compare XGBoost with a Decision Tree baseline.
    baseline = DecisionTreeClassifier(
        max_depth=3,
        random_state=42,
    )

    start = time.perf_counter()
    baseline.fit(X_train, y_train)
    baseline_training_time = time.perf_counter() - start

    xgb_result = evaluate_model(
        "XGBoost", best_model, X_test, y_test
    )
    baseline_result = evaluate_model(
        "Decision Tree", baseline, X_test, y_test
    )

    # 6. Save actual metrics and model-comparison results.
    comparison_rows = []

    for result, train_time in [
        (xgb_result, training_time),
        (baseline_result, baseline_training_time),
    ]:
        comparison_rows.append({
            "model": result["model"],
            "accuracy": result["accuracy"],
            "precision": result["precision"],
            "recall": result["recall"],
            "f1_score": result["f1_score"],
            "training_time_seconds": train_time,
            "prediction_time_seconds": result[
                "prediction_time_seconds"
            ],
        })

    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(
        REPORT_DIR / "model_comparison.csv", index=False
    )
    pd.DataFrame(tuning_results).to_csv(
        REPORT_DIR / "parameter_tuning_results.csv",
        index=False,
    )

    xgb_predictions = xgb_result["predictions"]
    cm = confusion_matrix(
        y_test, xgb_predictions, labels=[0, 1]
    )

    # 7. Save the confusion matrix plot.
    plt.figure(figsize=(6, 5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Not retained", "Retained"],
        yticklabels=["Not retained", "Retained"],
    )
    plt.title("XGBoost Confusion Matrix")
    plt.xlabel("Predicted label")
    plt.ylabel("Actual label")
    plt.tight_layout()
    plt.savefig(
        FIGURE_DIR / "confusion_matrix.png", dpi=150
    )
    plt.close()

    # 8. Save the comparison chart.
    comparison.set_index("model")[
        ["accuracy", "precision", "recall", "f1_score"]
    ].plot(kind="bar", figsize=(9, 5))
    plt.title("XGBoost vs Decision Tree")
    plt.ylabel("Score")
    plt.ylim(0, 1)
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(
        FIGURE_DIR / "model_comparison.png", dpi=150
    )
    plt.close()

    # 9. Calculate manual accuracy and save the results.
    correct = int((y_test.to_numpy() == xgb_predictions).sum())
    total = len(y_test)
    manual_accuracy = correct / total * 100

    metrics = {
        "dataset_type": "Synthetic demonstration data",
        "dataset_rows": len(df),
        "selected_configuration": best_config,
        "xgboost_accuracy": float(xgb_result["accuracy"]),
        "xgboost_precision": float(xgb_result["precision"]),
        "xgboost_recall": float(xgb_result["recall"]),
        "xgboost_f1_score": float(xgb_result["f1_score"]),
        "manual_accuracy_correct_predictions": correct,
        "manual_accuracy_total_predictions": total,
        "manual_accuracy_percent": manual_accuracy,
        "confusion_matrix": cm.tolist(),
        "classification_report": classification_report(
            y_test,
            xgb_predictions,
            target_names=["Not retained", "Retained"],
            output_dict=True,
            zero_division=0,
        ),
    }

    with open(
        REPORT_DIR / "metrics.json", "w", encoding="utf-8"
    ) as file:
        json.dump(metrics, file, indent=2)

    # 10. Display the real output from this execution.
    print("\nMODEL COMPARISON")
    print(comparison.to_string(index=False))

    print("\nXGBOOST CLASSIFICATION REPORT")
    print(classification_report(
        y_test,
        xgb_predictions,
        target_names=["Not retained", "Retained"],
        zero_division=0,
    ))

    print("\nMANUAL ACCURACY CALCULATION")
    print(f"Correct predictions: {correct}")
    print(f"Total predictions: {total}")
    print(f"Accuracy = ({correct}/{total}) x 100")
    print(f"Manual accuracy = {manual_accuracy:.2f}%")

    print("\nPROJECT FILES SAVED")
    print(f"Model: {MODEL_PATH}")
    print(f"Metrics: {REPORT_DIR / 'metrics.json'}")
    print(f"Comparison: {REPORT_DIR / 'model_comparison.csv'}")
    print(f"Tuning: {REPORT_DIR / 'parameter_tuning_results.csv'}")
    print(f"Figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()