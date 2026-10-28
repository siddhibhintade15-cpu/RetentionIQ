
import pandas as pd
import pytest

from src.data_preprocessing import load_dataset, prepare_data, FEATURES, TARGET


def test_dataset_loads_successfully():
    df = load_dataset()
    assert not df.empty
    assert set(FEATURES + [TARGET]).issubset(df.columns)


def test_dataset_has_no_missing_values():
    df = load_dataset()
    assert not df[FEATURES + [TARGET]].isnull().any().any()


def test_target_contains_only_zero_and_one():
    df = load_dataset()
    assert set(df[TARGET].unique()).issubset({0, 1})


def test_train_test_split_shapes():
    df = load_dataset()
    X_train, X_test, y_train, y_test = prepare_data(df)

    assert len(X_train) == 2400
    assert len(X_test) == 600
    assert X_train.shape[1] == 7
    assert len(y_train) == len(X_train)
    assert len(y_test) == len(X_test)


def test_missing_column_is_rejected(tmp_path):
    bad_df = pd.DataFrame({"age": [22], "retained": [1]})
    file_path = tmp_path / "bad_data.csv"
    bad_df.to_csv(file_path, index=False)

    with pytest.raises(ValueError, match="Missing columns"):
        load_dataset(file_path)
