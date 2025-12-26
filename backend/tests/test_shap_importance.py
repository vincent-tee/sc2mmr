import pytest
import numpy as np
from unittest.mock import MagicMock
from backend.app.services.shap_feature_importance import SHAPFeatureImportance


def test_shap_feature_importance_init():
    model = MagicMock()
    feature_names = ["f1", "f2"]
    shap_analyzer = SHAPFeatureImportance(model, feature_names)
    assert shap_analyzer.model == model
    assert shap_analyzer.feature_names == feature_names


def test_shap_feature_importance_get_importance():
    model = MagicMock()
    feature_names = ["f1", "f2"]
    shap_analyzer = SHAPFeatureImportance(model, feature_names)
    shap_analyzer.explainer = MagicMock()

    # Mock SHAP values: 2 samples, 2 features
    shap_values = np.array([[0.5, -0.2], [0.3, 0.4]])

    importance_df = shap_analyzer.get_feature_importance(shap_values)

    # f1 importance: (|0.5| + |0.3|) / 2 = 0.4
    # f2 importance: (|-0.2| + |0.4|) / 2 = 0.3

    assert importance_df.iloc[0]["feature"] == "f1"
    assert importance_df.iloc[0]["importance"] == pytest.approx(0.4)
    assert importance_df.iloc[1]["feature"] == "f2"
    assert importance_df.iloc[1]["importance"] == pytest.approx(0.3)


def test_get_top_features():
    model = MagicMock()
    feature_names = ["f1", "f2", "f3"]
    shap_analyzer = SHAPFeatureImportance(model, feature_names)
    shap_analyzer.explainer = MagicMock()

    shap_values = np.array([[1.0, 0.1, 0.5]])

    top_features = shap_analyzer.get_top_features(shap_values, n=2)

    assert len(top_features) == 2
    assert top_features[0]["feature"] == "f1"
    assert top_features[1]["feature"] == "f3"
