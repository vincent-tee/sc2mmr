import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from backend.app.services.xgboost_predictor import XGBoostPredictor


@patch("backend.app.services.xgboost_predictor.XGBoostPredictor._load_model")
@patch("backend.app.services.xgboost_predictor.FeatureExtractor.extract_team_features")
@patch("backend.app.services.xgboost_predictor.FeatureExtractor.create_match_features")
@patch("shap.TreeExplainer")
def test_xgboost_predict_with_shap(
    mock_tree_explainer, mock_create_features, mock_extract_features, mock_load_model
):
    # Setup
    predictor = XGBoostPredictor()
    predictor.model = MagicMock()
    predictor.is_trained = True
    predictor.is_xgboost = True

    db = MagicMock()
    team1_ids = [1, 2]
    team2_ids = [3, 4]

    # Mock features
    mock_create_features.return_value = np.zeros(14)

    # Mock model prediction
    predictor.model.predict_proba.return_value = np.array([[0.4, 0.6]])

    # Mock SHAP
    mock_explainer_inst = MagicMock()
    mock_tree_explainer.return_value = mock_explainer_inst

    # SHAP values for 1 sample, 14 features
    # Let's say feature 0 (mmr_diff) has high impact
    shap_vals = np.zeros((1, 14))
    shap_vals[0, 0] = 0.5
    mock_explainer_inst.shap_values.return_value = shap_vals

    # Run
    result = predictor.predict(db, team1_ids, team2_ids)

    # Verify
    assert "team_1_win_probability" in result
    assert result["team_1_win_probability"] == 60.0
    assert "key_factors" in result
    assert len(result["key_factors"]) > 0
    assert "Team 1 has advantage in Mmr" in result["key_factors"][0]
    assert "shap_impacts" in result
    assert result["shap_impacts"][0]["feature"] == "mmr_diff"
    assert result["shap_impacts"][0]["impact"] == 0.5
