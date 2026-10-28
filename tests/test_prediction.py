
import pytest

from predict import predict_retention


def valid_user():
    return {
        "age": 22,
        "session_frequency": 10,
        "avg_session_minutes": 25.0,
        "days_since_install": 14,
        "notifications_clicked": 8,
        "crashes": 0,
        "purchases": 2,
    }


def test_prediction_returns_valid_class_and_probability():
    prediction, probability = predict_retention(valid_user())

    assert prediction in (0, 1)
    assert 0.0 <= probability <= 1.0


def test_prediction_accepts_all_required_features():
    user = valid_user()
    user["age"] = 30
    user["session_frequency"] = 5
    user["avg_session_minutes"] = 15.0
    user["days_since_install"] = 7
    user["notifications_clicked"] = 3
    user["crashes"] = 1
    user["purchases"] = 0

    prediction, probability = predict_retention(user)

    assert isinstance(prediction, int)
    assert isinstance(probability, float)


def test_prediction_rejects_missing_feature():
    user = valid_user()
    del user["age"]

    with pytest.raises(ValueError, match="Missing required feature"):
        predict_retention(user)


def test_prediction_rejects_negative_values():
    user = valid_user()
    user["crashes"] = -1

    with pytest.raises(ValueError, match="cannot be negative"):
        predict_retention(user)


def test_prediction_rejects_invalid_age():
    user = valid_user()
    user["age"] = 17

    with pytest.raises(ValueError, match="Age must be between"):
        predict_retention(user)


def test_prediction_rejects_unexpected_feature():
    user = valid_user()
    user["country"] = "India"

    with pytest.raises(ValueError, match="Unexpected feature"):
        predict_retention(user)
