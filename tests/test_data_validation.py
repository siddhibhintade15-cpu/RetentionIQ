
import pandas as pd
import pytest

from src.data_preprocessing import load_dataset, FEATURES, TARGET


def test_generated_dataset_contains_expected_rows():
    df = load_dataset()
    assert len(df) == 3000


def test_retention_target_is_binary():
    df = load_dataset()
    assert set(df[TARGET].unique()) == {0, 1}


def test_feature_columns_are_numeric():
    df = load_dataset()
    assert all(
        pd.api.types.is_numeric_dtype(df[column])
        for column in FEATURES
    )


def test_invalid_target_is_rejected(tmp_path):
    df = load_dataset()
    df.loc[0, TARGET] = 2

    file_path = tmp_path / "invalid_target.csv"
    df.to_csv(file_path, index=False)

    with pytest.raises(
        ValueError,
        match="Target must contain only 0 and 1",
    ):
        load_dataset(file_path)
