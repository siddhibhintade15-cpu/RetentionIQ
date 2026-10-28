
"""Generate a reproducible sample mobile app retention dataset."""

from pathlib import Path

import numpy as np
import pandas as pd


def generate_sample_data(n_samples=3000, random_state=42):
    """Create sample user activity and retention records."""
    rng = np.random.default_rng(random_state)

    age = rng.integers(18, 61, n_samples)
    session_frequency = rng.integers(0, 15, n_samples)
    avg_session_minutes = rng.uniform(1, 45, n_samples).round(2)
    days_since_install = rng.integers(1, 91, n_samples)
    notifications_clicked = rng.integers(0, 20, n_samples)
    crashes = rng.integers(0, 6, n_samples)
    purchases = rng.integers(0, 8, n_samples)

    # Illustrative probability: more engagement generally means
    # a greater chance of retention; crashes reduce that chance.
    score = (
        -1.0
        + 0.15 * session_frequency
        + 0.025 * avg_session_minutes
        + 0.08 * notifications_clicked
        + 0.20 * purchases
        - 0.50 * crashes
        - 0.012 * days_since_install
    )

    probability = 1 / (1 + np.exp(-np.clip(score, -20, 20)))
    retained = rng.binomial(1, probability)

    return pd.DataFrame({
        "age": age,
        "session_frequency": session_frequency,
        "avg_session_minutes": avg_session_minutes,
        "days_since_install": days_since_install,
        "notifications_clicked": notifications_clicked,
        "crashes": crashes,
        "purchases": purchases,
        "retained": retained,
    })


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    df = generate_sample_data()
    output_path = data_dir / "mobile_app_retention.csv"
    df.to_csv(output_path, index=False)

    print(f"Dataset saved to: {output_path}")
    print(f"Dataset shape: {df.shape}")
    print("\nFirst five rows:")
    print(df.head())
    print("\nRetention distribution:")
    print(df["retained"].value_counts())

