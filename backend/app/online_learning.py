"""
Online Learning System - Self-Improving Adaptive Model

This system creates a "living model" that:
1. Continuously learns from new match outcomes
2. Discovers important features automatically
3. Improves not just weights, but what it extracts from replays
4. Versions models for safe experimentation
5. Provides A/B testing for new features

Architecture:
-----------
┌─────────────────┐
│  Match Happens  │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│ Feature Extraction      │  ← Parser plugins extract features
│ - Current features      │
│ - Experimental features │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│ Prediction & Storage    │
│ - Model A predicts      │
│ - Model B predicts      │
│ - Store predictions     │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│ Outcome Observation     │
│ - Actual result known   │
│ - Calculate errors      │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│ Learning Pipeline       │
│ - Update model weights  │
│ - Analyze feature       │
│   importance            │
│ - Detect correlations   │
│ - Suggest new features  │
└─────────────────────────┘
"""
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text

from .models import Match, MatchPlayer, PlayerMatchMetrics, Base
from .adaptive_model import PerformanceWeights, AdaptiveModelTuner

logger = logging.getLogger(__name__)


# ============================================================================
# Database Models for Online Learning
# ============================================================================

class ModelVersion(Base):
    """Tracks different model versions for A/B testing."""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    version_name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    weights_json = Column(JSON)  # PerformanceWeights as JSON
    features_used = Column(JSON)  # List of feature names
    is_active = Column(Boolean, default=False)
    is_experimental = Column(Boolean, default=False)

    # Performance tracking
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    avg_prediction_error = Column(Float, default=0.0)

    # Metadata
    notes = Column(Text, nullable=True)
    parent_version = Column(String, nullable=True)


class PredictionLog(Base):
    """Logs predictions for later evaluation."""
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Predictions
    predicted_team1_win_prob = Column(Float)
    predicted_team2_win_prob = Column(Float)

    # Actual outcome (filled in after match)
    actual_team1_won = Column(Boolean, nullable=True)

    # Feature values used for this prediction
    features_json = Column(JSON)

    # Prediction quality
    prediction_error = Column(Float, nullable=True)
    was_upset = Column(Boolean, nullable=True)


class FeatureImportance(Base):
    """Tracks importance of different features over time."""
    __tablename__ = "feature_importance"

    id = Column(Integer, primary_key=True, index=True)
    feature_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Importance metrics
    correlation_with_outcome = Column(Float)
    information_gain = Column(Float, nullable=True)
    sample_size = Column(Integer)

    # Feature metadata
    feature_type = Column(String)  # "existing", "experimental", "suggested"
    extraction_method = Column(String, nullable=True)


class FeatureSuggestion(Base):
    """AI-suggested new features to extract from replays."""
    __tablename__ = "feature_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    feature_name = Column(String, nullable=False)
    feature_description = Column(Text)
    extraction_logic = Column(Text)  # Pseudocode or actual code

    # Why suggested
    reasoning = Column(Text)
    correlation_hypothesis = Column(Float, nullable=True)

    # Status
    status = Column(String, default="pending")  # pending, implemented, rejected, testing
    tested_at = Column(DateTime, nullable=True)
    test_results = Column(JSON, nullable=True)


# ============================================================================
# Online Learning Engine
# ============================================================================

@dataclass
class LearningConfig:
    """Configuration for online learning system."""
    # Retraining frequency
    retrain_every_n_matches: int = 50
    min_matches_for_training: int = 100

    # Feature discovery
    feature_discovery_enabled: bool = True
    min_correlation_threshold: float = 0.15

    # Model versioning
    max_active_models: int = 2  # For A/B testing
    experimental_traffic_percent: float = 0.2  # 20% to experimental model

    # Safety
    max_weight_change_per_update: float = 0.1
    rollback_if_accuracy_drops: bool = True
    min_accuracy_threshold: float = 0.55


class OnlineLearningEngine:
    """
    Manages continuous learning and improvement of the model.

    This is the "brain" that makes the system self-improving.
    """

    def __init__(self, db: Session, config: LearningConfig = None):
        self.db = db
        self.config = config or LearningConfig()

    def log_prediction(
        self,
        match_id: int,
        model_version: str,
        team1_win_prob: float,
        team2_win_prob: float,
        features: Dict[str, Any]
    ) -> PredictionLog:
        """
        Log a prediction for later evaluation.

        This is called when a match's outcome is predicted.
        """
        pred_log = PredictionLog(
            match_id=match_id,
            model_version=model_version,
            predicted_team1_win_prob=team1_win_prob,
            predicted_team2_win_prob=team2_win_prob,
            features_json=features
        )
        self.db.add(pred_log)
        self.db.commit()

        logger.info(f"Logged prediction for match {match_id} using model {model_version}")
        return pred_log

    def record_outcome(
        self,
        match_id: int,
        team1_won: bool
    ) -> None:
        """
        Record the actual outcome of a match.

        This triggers the learning process:
        1. Calculate prediction errors
        2. Update feature importance
        3. Check if retraining is needed
        4. Suggest new features if patterns found
        """
        # Update prediction logs with actual outcome
        pred_logs = self.db.query(PredictionLog).filter(
            PredictionLog.match_id == match_id,
            PredictionLog.actual_team1_won.is_(None)
        ).all()

        for pred_log in pred_logs:
            pred_log.actual_team1_won = team1_won

            # Calculate prediction error
            predicted_prob = pred_log.predicted_team1_win_prob if team1_won else pred_log.predicted_team2_win_prob
            pred_log.prediction_error = abs(1.0 - predicted_prob)

            # Mark upsets
            underdog_won = (team1_won and pred_log.predicted_team1_win_prob < 0.4) or \
                          (not team1_won and pred_log.predicted_team2_win_prob < 0.4)
            pred_log.was_upset = underdog_won

        self.db.commit()

        # Trigger learning pipeline
        self._check_and_trigger_learning()

    def _check_and_trigger_learning(self) -> None:
        """
        Check if it's time to retrain and trigger learning if needed.
        """
        # Count matches since last training
        total_matches = self.db.query(Match).count()

        # Get last model version
        latest_model = self.db.query(ModelVersion).order_by(
            ModelVersion.created_at.desc()
        ).first()

        if latest_model:
            matches_since_training = total_matches - latest_model.total_predictions
        else:
            matches_since_training = total_matches

        # Should we retrain?
        should_retrain = (
            matches_since_training >= self.config.retrain_every_n_matches and
            total_matches >= self.config.min_matches_for_training
        )

        if should_retrain:
            logger.info(f"Triggering retraining: {matches_since_training} new matches")
            self._retrain_model()

            if self.config.feature_discovery_enabled:
                self._discover_new_features()

    def _retrain_model(self) -> ModelVersion:
        """
        Retrain the model on recent data.

        Returns:
            New model version
        """
        logger.info("Starting model retraining...")

        # Get recent matches for training
        recent_matches = self.db.query(Match).order_by(
            Match.played_at.desc()
        ).limit(500).all()

        # Prepare training data
        training_data = []
        for match in recent_matches:
            for match_player in match.players:
                if match_player.metrics:
                    won = match_player.won == 1
                    training_data.append((match_player.metrics, won))

        if len(training_data) < self.config.min_matches_for_training:
            logger.warning(f"Not enough data for training: {len(training_data)} samples")
            return None

        # Get current weights
        current_model = self.db.query(ModelVersion).filter(
            ModelVersion.is_active == True
        ).first()

        if current_model:
            current_weights = PerformanceWeights(**json.loads(current_model.weights_json))
        else:
            current_weights = PerformanceWeights()

        # Optimize weights using AdaptiveModelTuner
        tuner = AdaptiveModelTuner()
        from scipy.optimize import minimize

        def objective(weights_array):
            weights = PerformanceWeights.from_array(weights_array)
            return tuner.evaluate_weights(weights, training_data)

        # Optimize
        result = minimize(
            objective,
            current_weights.to_array(),
            method='Nelder-Mead',
            options={'maxiter': 100}
        )

        new_weights = PerformanceWeights.from_array(result.x)

        # Create new model version
        version_name = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_model = ModelVersion(
            version_name=version_name,
            weights_json=json.dumps({
                'combat_weight': new_weights.combat_weight,
                'economic_weight': new_weights.economic_weight,
                'team_contribution_weight': new_weights.team_contribution_weight,
                'efficiency_weight': new_weights.efficiency_weight
            }),
            features_used=['combat_score', 'economic_score', 'team_contribution', 'efficiency_score'],
            is_experimental=True,  # Start as experimental
            parent_version=current_model.version_name if current_model else None,
            notes=f"Trained on {len(training_data)} samples"
        )

        self.db.add(new_model)
        self.db.commit()

        logger.info(f"Created new model version: {version_name}")
        logger.info(f"New weights: {new_weights}")

        return new_model

    def _discover_new_features(self) -> List[FeatureSuggestion]:
        """
        Analyze prediction errors to suggest new features.

        This is where the magic happens - the system figures out
        what new things it should extract from replays.

        Strategy:
        1. Find matches with high prediction errors
        2. Look for patterns in those matches
        3. Suggest features that correlate with errors
        4. Generate extraction logic suggestions
        """
        logger.info("Starting feature discovery...")

        # Get recent predictions with high errors
        high_error_predictions = self.db.query(PredictionLog).filter(
            PredictionLog.prediction_error > 0.3,
            PredictionLog.prediction_error.isnot(None)
        ).order_by(
            PredictionLog.created_at.desc()
        ).limit(100).all()

        if len(high_error_predictions) < 20:
            logger.info("Not enough error data for feature discovery")
            return []

        suggestions = []

        # Analyze patterns in high-error matches
        # Pattern 1: Upsets (underdog wins)
        upset_count = sum(1 for p in high_error_predictions if p.was_upset)
        if upset_count > len(high_error_predictions) * 0.3:
            # Many upsets - suggests we're missing a feature
            suggestions.append(FeatureSuggestion(
                feature_name="early_game_aggression",
                feature_description="Measure of early game pressure (units created in first 5 minutes)",
                extraction_logic="""
                # Pseudocode
                early_units = count_units_created(replay, time_range=(0, 300))
                early_attacks = count_attack_events(replay, time_range=(0, 300))
                aggression_score = (early_units * 0.3 + early_attacks * 0.7) / game_duration
                """,
                reasoning="High upset rate suggests early game dynamics not captured. "
                         "Underdogs may win through early aggression not reflected in mid/late metrics.",
                correlation_hypothesis=0.25,
                status="pending"
            ))

        # Pattern 2: Check if errors correlate with specific maps
        # (This would require more sophisticated analysis)
        suggestions.append(FeatureSuggestion(
            feature_name="map_control_percentage",
            feature_description="Percentage of map controlled (based on vision/creep/buildings)",
            extraction_logic="""
            # Pseudocode
            control_events = extract_map_control_timeline(replay)
            avg_control = mean(control_events.team_control_percentage)
            """,
            reasoning="Map control often determines long-term outcome but isn't captured by combat/economy alone.",
            correlation_hypothesis=0.20,
            status="pending"
        ))

        # Pattern 3: Team synergy features
        suggestions.append(FeatureSuggestion(
            feature_name="composition_synergy",
            feature_description="How well team races complement each other (e.g., Terran bio + Protoss storm)",
            extraction_logic="""
            # Define synergy matrix
            synergy_matrix = {
                ('Terran', 'Protoss'): 1.2,
                ('Zerg', 'Terran'): 1.1,
                # etc...
            }
            races = [p.race for p in team]
            synergy_score = calculate_team_synergy(races, synergy_matrix)
            """,
            reasoning="Some race combinations naturally work better together. This meta-game knowledge isn't captured.",
            correlation_hypothesis=0.15,
            status="pending"
        ))

        # Save suggestions
        for suggestion in suggestions:
            # Check if already suggested
            existing = self.db.query(FeatureSuggestion).filter(
                FeatureSuggestion.feature_name == suggestion.feature_name
            ).first()

            if not existing:
                self.db.add(suggestion)

        self.db.commit()

        logger.info(f"Generated {len(suggestions)} feature suggestions")
        return suggestions

    def get_active_model(self) -> Optional[ModelVersion]:
        """Get currently active model version."""
        return self.db.query(ModelVersion).filter(
            ModelVersion.is_active == True
        ).first()

    def promote_experimental_model(self, version_name: str) -> None:
        """
        Promote an experimental model to active.

        This happens after A/B testing shows the new model is better.
        """
        # Deactivate current active model
        current_active = self.get_active_model()
        if current_active:
            current_active.is_active = False

        # Activate new model
        new_model = self.db.query(ModelVersion).filter(
            ModelVersion.version_name == version_name
        ).first()

        if new_model:
            new_model.is_active = True
            new_model.is_experimental = False
            self.db.commit()

            logger.info(f"Promoted {version_name} to active model")


# ============================================================================
# Feature Discovery Helpers
# ============================================================================

class FeatureExtractor:
    """
    Plugin-based feature extractor.

    Allows adding new feature extraction methods without changing core code.
    """

    def __init__(self):
        self.extractors = {}

    def register_extractor(self, feature_name: str, extractor_func):
        """Register a new feature extraction function."""
        self.extractors[feature_name] = extractor_func
        logger.info(f"Registered feature extractor: {feature_name}")

    def extract_all(self, replay_data, match_data) -> Dict[str, Any]:
        """Extract all registered features from a replay."""
        features = {}
        for name, extractor in self.extractors.items():
            try:
                features[name] = extractor(replay_data, match_data)
            except Exception as e:
                logger.error(f"Failed to extract feature {name}: {e}")
                features[name] = None
        return features


# Example feature extractors
def extract_early_aggression(replay_data, match_data) -> float:
    """
    Example: Extract early game aggression metric.
    This would need actual replay parsing implementation.
    """
    # Placeholder - would need sc2reader integration
    return 0.5


def extract_map_control(replay_data, match_data) -> float:
    """
    Example: Extract map control percentage.
    """
    # Placeholder
    return 0.5
