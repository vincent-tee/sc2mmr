"""
XGBoost Match Predictor - Enhanced ML Model for SC2 Match Prediction

Uses gradient boosting (XGBoost) to predict match outcomes based on:
- Player metrics (MMR, impact scores, efficiency)
- Team composition features
- Historical performance data
- Momentum and form indicators

Designed to be compared against TrueSkill predictions for accuracy benchmarking.

SPEC-ML-001 Implementation - Phase 2: Advanced ML Models
"""

import logging
import pickle
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Match, MatchPlayer, Player, PlayerMatchMetrics

logger = logging.getLogger(__name__)


# ============================================================================
# Feature Engineering
# ============================================================================


@dataclass
class TeamFeatures:
    """Aggregated features for a team."""

    avg_mmr: float = 0.0
    avg_recency_mmr: float = 0.0
    avg_hybrid_mmr: float = 0.0
    avg_combat_score: float = 0.0
    avg_economic_score: float = 0.0
    avg_efficiency_score: float = 0.0
    avg_overall_impact: float = 0.0
    total_games: int = 0
    avg_win_rate: float = 0.5
    avg_recent_win_rate: float = 0.5
    max_mmr: float = 0.0
    min_mmr: float = 0.0
    mmr_std: float = 0.0
    team_size: int = 0
    avg_win_streak: float = 0.0


class FeatureExtractor:
    """Extracts ML features from player/team data."""

    @staticmethod
    def get_player_win_streak(db: Session, player_id: int, max_games: int = 10) -> int:
        """Get current win streak for a player."""
        recent_matches = (
            db.query(MatchPlayer)
            .filter(MatchPlayer.player_id == player_id)
            .join(Match)
            .order_by(Match.played_at.desc())
            .limit(max_games)
            .all()
        )

        streak = 0
        for mp in recent_matches:
            if mp.won:
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def get_recent_win_rate(db: Session, player_id: int, days: int = 30) -> float:
        """Get win rate over recent period."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_matches = (
            db.query(MatchPlayer)
            .filter(MatchPlayer.player_id == player_id)
            .join(Match)
            .filter(Match.played_at >= cutoff)
            .all()
        )

        if not recent_matches:
            return 0.5

        wins = sum(1 for mp in recent_matches if mp.won)
        return wins / len(recent_matches)

    @staticmethod
    def extract_team_features(db: Session, player_ids: List[int]) -> TeamFeatures:
        """Extract aggregated features for a team."""
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()

        if not players:
            return TeamFeatures()

        features = TeamFeatures()
        features.team_size = len(players)

        mmrs = []
        win_streaks = []

        for player in players:
            mmr = player.mmr or 1000
            mmrs.append(mmr)

            features.avg_mmr += mmr
            features.avg_recency_mmr += player.recency_weighted_mmr or mmr
            features.avg_hybrid_mmr += player.hybrid_mmr or mmr
            features.avg_combat_score += player.avg_combat_score or 50
            features.avg_economic_score += player.avg_economic_score or 50
            features.avg_efficiency_score += player.avg_efficiency_score or 50
            features.avg_overall_impact += player.avg_overall_impact or 50
            features.total_games += player.total_games or 0
            features.avg_win_rate += player.win_rate if player.win_rate else 0.5
            features.avg_recent_win_rate += FeatureExtractor.get_recent_win_rate(
                db, player.id
            )

            win_streak = FeatureExtractor.get_player_win_streak(db, player.id)
            win_streaks.append(win_streak)

        n = len(players)
        if n > 0:
            features.avg_mmr /= n
            features.avg_recency_mmr /= n
            features.avg_hybrid_mmr /= n
            features.avg_combat_score /= n
            features.avg_economic_score /= n
            features.avg_efficiency_score /= n
            features.avg_overall_impact /= n
            features.avg_win_rate /= n
            features.avg_recent_win_rate /= n
            features.avg_win_streak = sum(win_streaks) / n if win_streaks else 0

        features.max_mmr = max(mmrs) if mmrs else 0
        features.min_mmr = min(mmrs) if mmrs else 0
        features.mmr_std = float(np.std(mmrs)) if len(mmrs) > 1 else 0

        return features

    @staticmethod
    def create_match_features(team1: TeamFeatures, team2: TeamFeatures) -> np.ndarray:
        """Create feature vector from two team features (difference-based)."""
        return np.array(
            [
                # MMR differences (normalized)
                (team1.avg_mmr - team2.avg_mmr) / 200,
                (team1.avg_recency_mmr - team2.avg_recency_mmr) / 200,
                (team1.avg_hybrid_mmr - team2.avg_hybrid_mmr) / 200,
                # Performance score differences
                (team1.avg_combat_score - team2.avg_combat_score) / 20,
                (team1.avg_economic_score - team2.avg_economic_score) / 20,
                (team1.avg_efficiency_score - team2.avg_efficiency_score) / 20,
                (team1.avg_overall_impact - team2.avg_overall_impact) / 20,
                # Win rate differences
                team1.avg_win_rate - team2.avg_win_rate,
                team1.avg_recent_win_rate - team2.avg_recent_win_rate,
                # Momentum
                team1.avg_win_streak - team2.avg_win_streak,
                # Team composition
                (team1.max_mmr - team2.max_mmr) / 200,
                (team1.min_mmr - team2.min_mmr) / 200,
                (team1.mmr_std - team2.mmr_std) / 100,
                # Experience
                (team1.total_games - team2.total_games) / 100,
            ]
        )


# ============================================================================
# XGBoost Model Wrapper
# ============================================================================


class XGBoostPredictor:
    """
    XGBoost-based match predictor with training and prediction capabilities.
    """

    MODEL_PATH = Path("data/xgboost_model.pkl")

    def __init__(self):
        self.model: Any = None
        self.is_xgboost = False
        self.is_trained = False
        self.training_accuracy = 0.0
        self.feature_importance: Dict[str, float] = {}
        self.shap_importance: Dict[str, float] = {}

    def _get_model(self):
        """Get XGBoost or fallback model."""
        try:
            from xgboost import XGBClassifier  # type: ignore

            self.is_xgboost = True
            return XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric="logloss",
            )
        except ImportError:
            logger.warning("XGBoost not available, using LogisticRegression")
            from sklearn.linear_model import LogisticRegression  # type: ignore

            self.is_xgboost = False
            return LogisticRegression(max_iter=1000, random_state=42)

    def train(self, db: Session, min_matches: int = 50) -> Dict[str, Any]:
        """
        Train the model on historical match data.
        """
        # Get completed matches
        matches = (
            db.query(Match)
            .filter(Match.played_at.isnot(None))
            .order_by(Match.played_at.desc())
            .limit(500)
            .all()
        )

        if len(matches) < min_matches:
            return {
                "status": "insufficient_data",
                "matches": len(matches),
                "required": min_matches,
            }

        X = []
        y = []

        for match in matches:
            match_players = (
                db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
            )

            team1_ids = [mp.player_id for mp in match_players if mp.team_number == 1]
            team2_ids = [mp.player_id for mp in match_players if mp.team_number == 2]

            if not team1_ids or not team2_ids:
                continue

            # Get features
            team1_features = FeatureExtractor.extract_team_features(db, team1_ids)
            team2_features = FeatureExtractor.extract_team_features(db, team2_ids)

            feature_vector = FeatureExtractor.create_match_features(
                team1_features, team2_features
            )
            X.append(feature_vector)

            # Label: 1 if team 1 won
            team1_won = any(mp.won and mp.team_number == 1 for mp in match_players)
            y.append(1 if team1_won else 0)

        if len(X) < min_matches:
            return {
                "status": "insufficient_valid_data",
                "valid_matches": len(X),
                "required": min_matches,
            }

        X_arr = np.array(X)
        y_arr = np.array(y)

        # Train/test split
        from sklearn.model_selection import train_test_split  # type: ignore

        X_train, X_test, y_train, y_test = train_test_split(
            X_arr, y_arr, test_size=0.2, random_state=42
        )

        # Train model
        self.model = self._get_model()
        self.model.fit(X_train, y_train)

        # Evaluate
        train_accuracy = self.model.score(X_train, y_train)
        test_accuracy = self.model.score(X_test, y_test)
        self.training_accuracy = float(test_accuracy)
        self.is_trained = True

        # Feature importance
        feature_names = [
            "mmr_diff",
            "recency_mmr_diff",
            "hybrid_mmr_diff",
            "combat_diff",
            "economic_diff",
            "efficiency_diff",
            "impact_diff",
            "win_rate_diff",
            "recent_wr_diff",
            "win_streak_diff",
            "max_mmr_diff",
            "min_mmr_diff",
            "mmr_std_diff",
            "games_diff",
        ]

        if self.is_xgboost and hasattr(self.model, "feature_importances_"):
            self.feature_importance = dict(
                zip(feature_names, self.model.feature_importances_.tolist())
            )
        elif hasattr(self.model, "coef_"):
            # Use coefficients for linear model importance
            self.feature_importance = dict(
                zip(feature_names, np.abs(self.model.coef_[0]).tolist())
            )

        # Advanced Feature Importance (SHAP)
        try:
            from .shap_feature_importance import SHAPFeatureImportance

            shap_analyzer = SHAPFeatureImportance(self.model, feature_names)
            shap_analyzer.fit(X_train)
            shap_values = shap_analyzer.explain(X_test, output_format="array")
            importance_df = shap_analyzer.get_feature_importance(shap_values)

            # Store SHAP importance
            self.shap_importance = {
                str(row["feature"]): float(row["importance"])
                for _, row in importance_df.iterrows()
            }
            logger.info("Global SHAP importance calculated successfully")
        except Exception as e:
            logger.warning(f"Could not calculate global SHAP importance: {e}")
            self.shap_importance = {}

        # Save model
        self._save_model()

        return {
            "status": "success",
            "model_type": "XGBoost" if self.is_xgboost else "LogisticRegression",
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_accuracy": round(float(train_accuracy) * 100, 1),
            "test_accuracy": round(float(test_accuracy) * 100, 1),
            "feature_importance": {
                k: round(v, 4)
                for k, v in sorted(
                    (
                        self.shap_importance
                        if self.shap_importance
                        else self.feature_importance
                    ).items(),
                    key=lambda x: -x[1],
                )[:5]
            },
        }

    def explain_prediction(self, feature_vector: np.ndarray) -> List[Dict[str, Any]]:
        """
        Explain a single prediction using SHAP values.
        """
        if not self.is_trained or self.model is None:
            return []

        try:
            from .shap_feature_importance import SHAPFeatureImportance

            feature_names = [
                "mmr_diff",
                "recency_mmr_diff",
                "hybrid_mmr_diff",
                "combat_diff",
                "economic_diff",
                "efficiency_diff",
                "impact_diff",
                "win_rate_diff",
                "recent_wr_diff",
                "win_streak_diff",
                "max_mmr_diff",
                "min_mmr_diff",
                "mmr_std_diff",
                "games_diff",
            ]

            explainer = SHAPFeatureImportance(self.model, feature_names)

            # Initialize explainer based on model type
            import shap  # type: ignore

            if self.is_xgboost:
                explainer.explainer = shap.TreeExplainer(self.model)
            else:
                explainer.explainer = shap.Explainer(self.model, feature_vector)

            shap_values = explainer.explain(feature_vector, output_format="array")

            # Handle different SHAP output formats
            if len(shap_values.shape) == 3:  # Explicit classes
                impacts_arr = shap_values[0, :, 1]
            elif len(shap_values.shape) == 2:
                impacts_arr = shap_values[0]
            else:
                impacts_arr = shap_values

            # Combine with names
            results = []
            for name, val in zip(feature_names, impacts_arr):
                results.append(
                    {
                        "feature": name,
                        "impact": float(val),
                        "magnitude": abs(float(val)),
                    }
                )

            # Sort by magnitude
            results.sort(key=lambda x: x["magnitude"], reverse=True)
            return results

        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return []

    def predict(
        self, db: Session, team1_ids: List[int], team2_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Predict match outcome.
        """
        if not self.is_trained:
            self._load_model()

        if self.model is None:
            return {
                "error": "Model not trained",
                "team_1_win_probability": 50.0,
                "team_2_win_probability": 50.0,
            }

        # Extract features
        team1_features = FeatureExtractor.extract_team_features(db, team1_ids)
        team2_features = FeatureExtractor.extract_team_features(db, team2_ids)

        feature_vector = FeatureExtractor.create_match_features(
            team1_features, team2_features
        ).reshape(1, -1)

        # Predict
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(feature_vector)[0]
            team1_prob = float(proba[1]) * 100
        else:
            prediction = self.model.predict(feature_vector)[0]
            team1_prob = 100.0 if prediction == 1 else 0.0

        confidence = abs(team1_prob - 50) / 50  # 0-1 scale

        # Add SHAP explanations
        shap_explanations = self.explain_prediction(feature_vector)

        # Format key factors from SHAP
        key_factors = []
        for exp in shap_explanations[:3]:
            if exp["magnitude"] > 0.01:
                team = "Team 1" if exp["impact"] > 0 else "Team 2"
                factor = exp["feature"].replace("_diff", "").replace("_", " ").title()
                key_factors.append(f"{team} has advantage in {factor}")

        return {
            "predicted_winner": 1 if team1_prob >= 50 else 2,
            "team_1_win_probability": round(team1_prob, 1),
            "team_2_win_probability": round(100 - team1_prob, 1),
            "confidence": "High"
            if confidence > 0.4
            else "Medium"
            if confidence > 0.2
            else "Low",
            "model": f"{'XGBoost' if self.is_xgboost else 'LogisticRegression'} ({self.training_accuracy * 100:.1f}% accuracy)",
            "model_accuracy": round(self.training_accuracy * 100, 1),
            "key_factors": key_factors if key_factors else ["Evenly matched"],
            "shap_impacts": shap_explanations[:5],
        }

    def _save_model(self) -> None:
        """Save trained model to disk."""
        try:
            self.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.MODEL_PATH, "wb") as f:
                pickle.dump(
                    {
                        "model": self.model,
                        "is_xgboost": self.is_xgboost,
                        "training_accuracy": self.training_accuracy,
                        "feature_importance": self.feature_importance,
                        "shap_importance": self.shap_importance,
                    },
                    f,
                )
            logger.info(f"Model saved to {self.MODEL_PATH}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def _load_model(self) -> bool:
        """Load model from disk."""
        try:
            if self.MODEL_PATH.exists():
                with open(self.MODEL_PATH, "rb") as f:
                    data = pickle.load(f)
                    self.model = data["model"]
                    self.is_xgboost = data["is_xgboost"]
                    self.training_accuracy = data["training_accuracy"]
                    self.feature_importance = data.get("feature_importance", {})
                    self.shap_importance = data.get("shap_importance", {})
                    self.is_trained = True
                logger.info(f"Model loaded from {self.MODEL_PATH}")
                return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
        return False


_predictor_instance: Optional[XGBoostPredictor] = None


def get_xgboost_predictor() -> XGBoostPredictor:
    """Get or create XGBoost predictor instance."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = XGBoostPredictor()
    return _predictor_instance


def train_xgboost_model(db: Session) -> Dict[str, Any]:
    """Train the XGBoost prediction model."""
    predictor = get_xgboost_predictor()
    return predictor.train(db)


def predict_with_xgboost(
    db: Session, team1_ids: List[int], team2_ids: List[int]
) -> Dict[str, Any]:
    """Predict match outcome using XGBoost model."""
    predictor = get_xgboost_predictor()
    return predictor.predict(db, team1_ids, team2_ids)
