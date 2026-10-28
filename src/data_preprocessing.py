
"""Load, validate, and split the mobile app retention dataset."""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

TARGET = "retained"

FEATURES = [
    "age",
    "session_frequency",
    "avg_session_minutes",
    "days_since_install",
    "notifications_clicked",
    "crashes",
    "purchases",
]


def load_dataset(path=None):
    """Load the CSV and validate its structure."""
    if path is None:
        project_root = Path(__file__).resolve().parents[1]
        path = project_root / "data" / "mobile_app_retention.csv"

    df = pd.read_csv(path)

    required_columns = FEATURES + [TARGET]
    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")

    if df[required_columns].isnull().any().any():
        raise ValueError("Dataset contains missing values.")

    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError("Target must contain only 0 and 1.")

    return df


def prepare_data(df, test_size=0.2, random_state=42):
    """Separate features and target, then create stratified splits."""
    X = df[FEATURES].copy()
    y = df[TARGET].astype(int).copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    return X_train, X_test, y_train, y_test


if __name__ == "__main__":
    df = load_dataset()
    X_train, X_test, y_train, y_test = prepare_data(df)

    print("Dataset loaded and validated successfully!")
    print(f"Full dataset: {df.shape}")
    print(f"Training features: {X_train.shape}")
    print(f"Testing features: {X_test.shape}")
    print(f"Training labels: {y_train.shape}")
    print(f"Testing labels: {y_test.shape}")
    print("\nMissing values:")
    print(df.isnull().sum())
    print("\nTarget distribution:")
    print(df[TARGET].value_counts())
