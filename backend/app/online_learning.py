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
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text

from .models import Match, MatchPlayer, PlayerMatchMetrics, Base, Player
from .adaptive_model import PerformanceWeights, AdaptiveModelTuner
from .config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Session Tracking Model
# ============================================================================

class PlayerSession(Base):
    """
    Tracks player gaming sessions for session-aware learning.

    A session is defined as a continuous period of play with no gaps
    longer than SESSION_GAP_HOURS between matches.
    """
    __tablename__ = "player_sessions"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    session_start = Column(DateTime, nullable=False)
    session_end = Column(DateTime, nullable=False)
    match_count = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    # Session statistics
    avg_performance = Column(Float, nullable=True)
    session_mmr_change = Column(Float, default=0.0)

    # Learning metadata
    learning_triggered = Column(Boolean, default=False)
    learning_triggered_at = Column(DateTime, nullable=True)


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
    """
    Configuration for online learning system.

    Values are loaded from centralized settings for consistency.
    Optimized for infrequent play patterns (8-10 games per session,
    weeks between sessions).
    """
    # Retraining frequency - optimized for session-based play
    retrain_every_n_matches: int = field(default_factory=lambda: settings.retrain_threshold)
    min_matches_for_training: int = field(default_factory=lambda: settings.min_matches_for_training)
    training_window: int = field(default_factory=lambda: settings.training_window)

    # Session-aware learning
    session_gap_hours: float = field(default_factory=lambda: settings.session_gap_hours)
    session_weight_multiplier: float = field(default_factory=lambda: settings.session_weight_multiplier)

    # Bayesian online updating
    bayesian_online_enabled: bool = field(default_factory=lambda: settings.bayesian_online_enabled)
    upset_learning_boost: float = field(default_factory=lambda: settings.upset_learning_boost)
    feature_importance_ema_alpha: float = field(default_factory=lambda: settings.feature_importance_ema_alpha)

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
        2. Perform Bayesian online update (incremental learning)
        3. Update session tracking
        4. Check if session ended (triggers session-based learning)
        5. Update feature importance with EMA
        6. Check if retraining is needed
        7. Suggest new features if patterns found
        """
        # Get the match for session tracking
        match = self.db.query(Match).filter(Match.id == match_id).first()

        # Update prediction logs with actual outcome
        pred_logs = self.db.query(PredictionLog).filter(
            PredictionLog.match_id == match_id,
            PredictionLog.actual_team1_won.is_(None)
        ).all()

        prediction_error = 0.0
        was_upset = False

        for pred_log in pred_logs:
            pred_log.actual_team1_won = team1_won

            # Calculate prediction error
            predicted_prob = pred_log.predicted_team1_win_prob if team1_won else pred_log.predicted_team2_win_prob
            pred_log.prediction_error = abs(1.0 - predicted_prob)
            prediction_error = pred_log.prediction_error

            # Mark upsets (underdog with <40% win probability wins)
            underdog_won = (team1_won and pred_log.predicted_team1_win_prob < 0.4) or \
                          (not team1_won and pred_log.predicted_team2_win_prob < 0.4)
            pred_log.was_upset = underdog_won
            was_upset = underdog_won

        self.db.commit()

        # Bayesian online update after EVERY match (incremental learning)
        if self.config.bayesian_online_enabled and pred_logs:
            self._bayesian_online_update(pred_logs[0], was_upset)

        # Update session tracking for all players in the match
        if match:
            self._update_player_sessions(match)

        # Trigger learning pipeline (may trigger session-end learning)
        self._check_and_trigger_learning(match)

    def _check_and_trigger_learning(self, current_match: Optional[Match] = None) -> None:
        """
        Check if it's time to retrain and trigger learning if needed.

        Supports two modes:
        1. Session-based: Trigger at end of gaming session
        2. Match-count based: Trigger after N matches (fallback)

        Args:
            current_match: The current match for session boundary detection
        """
        total_matches = self.db.query(Match).count()

        # Get last model version
        latest_model = self.db.query(ModelVersion).order_by(
            ModelVersion.created_at.desc()
        ).first()

        if latest_model:
            matches_since_training = total_matches - latest_model.total_predictions
        else:
            matches_since_training = total_matches

        # Check if session ended (triggers learning at session boundary)
        session_ended = self._detect_session_end(current_match) if current_match else False

        # Should we retrain?
        # Option 1: Session ended with enough matches
        # Option 2: Match count threshold reached
        should_retrain = (
            (session_ended and matches_since_training >= 3) or  # At least 3 matches in session
            (matches_since_training >= self.config.retrain_every_n_matches)
        ) and total_matches >= self.config.min_matches_for_training

        if should_retrain:
            trigger_reason = "session end" if session_ended else f"{matches_since_training} new matches"
            logger.info(f"Triggering retraining: {trigger_reason}")
            self._retrain_model()

            if self.config.feature_discovery_enabled:
                self._discover_new_features()

    def _detect_session_end(self, current_match: Match) -> bool:
        """
        Detect if a gaming session has ended.

        A session is considered ended if the gap between this match
        and the next match (if any) exceeds SESSION_GAP_HOURS.

        Since we process matches in order, we detect session end by
        checking the gap since the previous match.

        Args:
            current_match: The current match being processed

        Returns:
            True if this match ends a session
        """
        if not current_match or not current_match.played_at:
            return False

        # Find the previous match
        previous_match = self.db.query(Match).filter(
            Match.played_at < current_match.played_at
        ).order_by(Match.played_at.desc()).first()

        if not previous_match:
            # First match ever - no session end
            return False

        # Calculate time gap
        time_gap = current_match.played_at - previous_match.played_at
        gap_hours = time_gap.total_seconds() / 3600

        # If gap is larger than session threshold, the PREVIOUS session ended
        is_new_session = gap_hours >= self.config.session_gap_hours

        if is_new_session:
            logger.info(
                f"Session boundary detected: {gap_hours:.1f}h gap "
                f"(threshold: {self.config.session_gap_hours}h)"
            )

        return is_new_session

    def _update_player_sessions(self, match: Match) -> None:
        """
        Update session tracking for all players in a match.

        Creates or updates PlayerSession records to track gaming sessions.

        Args:
            match: The match to process
        """
        if not match.played_at:
            return

        # Get all players in this match
        match_players = self.db.query(MatchPlayer).filter(
            MatchPlayer.match_id == match.id
        ).all()

        session_gap = timedelta(hours=self.config.session_gap_hours)

        for mp in match_players:
            # Find the player's current active session
            current_session = self.db.query(PlayerSession).filter(
                PlayerSession.player_id == mp.player_id,
                PlayerSession.session_end >= match.played_at - session_gap
            ).order_by(PlayerSession.session_end.desc()).first()

            if current_session:
                # Extend the existing session
                current_session.session_end = match.played_at
                current_session.match_count += 1
                if mp.won:
                    current_session.wins += 1
                else:
                    current_session.losses += 1

                logger.debug(
                    f"Extended session for player {mp.player_id}: "
                    f"{current_session.match_count} matches"
                )
            else:
                # Start a new session
                new_session = PlayerSession(
                    player_id=mp.player_id,
                    session_start=match.played_at,
                    session_end=match.played_at,
                    match_count=1,
                    wins=1 if mp.won else 0,
                    losses=0 if mp.won else 1
                )
                self.db.add(new_session)

                logger.debug(f"Started new session for player {mp.player_id}")

        self.db.commit()

    def _bayesian_online_update(
        self,
        pred_log: PredictionLog,
        was_upset: bool
    ) -> None:
        """
        Perform Bayesian online update after a single match.

        This provides incremental learning without full retraining:
        1. Update model beliefs based on prediction error
        2. Weight learning by prediction surprise (upsets teach more)
        3. Use EMA for feature importance updates

        Args:
            pred_log: The prediction log with outcome
            was_upset: Whether this was an upset (unexpected outcome)
        """
        if not pred_log or pred_log.prediction_error is None:
            return

        # Calculate learning rate based on surprise
        # Higher error = more surprise = more learning
        base_learning_rate = 0.05
        surprise_factor = pred_log.prediction_error  # 0.0 to 1.0

        # Boost learning for upsets (they're informative)
        if was_upset:
            surprise_factor *= self.config.upset_learning_boost

        learning_rate = base_learning_rate * (1 + surprise_factor)
        learning_rate = min(learning_rate, 0.15)  # Cap at 15%

        logger.info(
            f"Bayesian update: error={pred_log.prediction_error:.3f}, "
            f"upset={was_upset}, learning_rate={learning_rate:.3f}"
        )

        # Update feature importance using EMA
        if pred_log.features_json:
            self._update_feature_importance_ema(
                pred_log.features_json,
                pred_log.prediction_error,
                learning_rate
            )

        # Update model version statistics
        model = self.db.query(ModelVersion).filter(
            ModelVersion.version_name == pred_log.model_version
        ).first()

        if model:
            model.total_predictions += 1

            # Track prediction accuracy
            if pred_log.prediction_error < 0.5:  # Correct prediction
                model.correct_predictions += 1

            # Update average prediction error using EMA
            alpha = self.config.feature_importance_ema_alpha
            if model.avg_prediction_error == 0:
                model.avg_prediction_error = pred_log.prediction_error
            else:
                model.avg_prediction_error = (
                    alpha * pred_log.prediction_error +
                    (1 - alpha) * model.avg_prediction_error
                )

            self.db.commit()

    def _update_feature_importance_ema(
        self,
        features: Dict[str, Any],
        prediction_error: float,
        learning_rate: float
    ) -> None:
        """
        Update feature importance using Exponential Moving Average.

        Features that correlate with prediction errors are less important.
        Features that help predict correctly are more important.

        Args:
            features: Dictionary of feature values used in prediction
            prediction_error: Error of this prediction (0-1)
            learning_rate: How much to weight this update
        """
        # Get active model
        active_model = self.db.query(ModelVersion).filter(
            ModelVersion.is_active == True
        ).first()

        if not active_model:
            return

        model_version = active_model.version_name

        for feature_name, feature_value in features.items():
            if feature_value is None:
                continue

            # Get or create feature importance record
            importance = self.db.query(FeatureImportance).filter(
                FeatureImportance.feature_name == feature_name,
                FeatureImportance.model_version == model_version
            ).first()

            if not importance:
                importance = FeatureImportance(
                    feature_name=feature_name,
                    model_version=model_version,
                    correlation_with_outcome=0.5,  # Start neutral
                    sample_size=0,
                    feature_type="existing"
                )
                self.db.add(importance)

            # Update correlation using EMA
            # Lower error = higher correlation with correct outcome
            outcome_correlation = 1.0 - prediction_error
            alpha = self.config.feature_importance_ema_alpha

            importance.correlation_with_outcome = (
                alpha * outcome_correlation +
                (1 - alpha) * importance.correlation_with_outcome
            )
            importance.sample_size += 1
            importance.calculated_at = datetime.utcnow()

        self.db.commit()

    def get_session_weighted_training_data(
        self,
        limit: int = None
    ) -> List[Tuple[Any, bool, float]]:
        """
        Get training data with session-based weighting.

        Recent session matches are weighted higher (2x by default) for
        faster adaptation to current skill level.

        Args:
            limit: Maximum number of matches to retrieve

        Returns:
            List of (metrics, won, weight) tuples
        """
        limit = limit or self.config.training_window

        # Get recent matches
        recent_matches = self.db.query(Match).order_by(
            Match.played_at.desc()
        ).limit(limit).all()

        # Identify current session boundary
        current_time = datetime.utcnow()
        session_cutoff = current_time - timedelta(hours=self.config.session_gap_hours)

        training_data = []
        for match in recent_matches:
            # Determine weight based on session
            is_current_session = (
                match.played_at and match.played_at >= session_cutoff
            )
            weight = self.config.session_weight_multiplier if is_current_session else 1.0

            for match_player in match.players:
                if match_player.metrics:
                    won = match_player.won == 1
                    training_data.append((match_player.metrics, won, weight))

        logger.info(
            f"Prepared {len(training_data)} training samples, "
            f"{sum(1 for d in training_data if d[2] > 1.0)} from current session"
        )

        return training_data

    def _retrain_model(self) -> ModelVersion:
        """
        Retrain the model on recent data with session-aware weighting.

        Uses session-weighted training data where recent session matches
        count more heavily (2x by default) for faster adaptation.

        Returns:
            New model version or None if not enough data
        """
        logger.info("Starting model retraining with session-weighted data...")

        # Get session-weighted training data
        weighted_training_data = self.get_session_weighted_training_data(
            limit=self.config.training_window
        )

        # Convert to unweighted format for backward compatibility
        # and prepare weighted samples for optimization
        training_data = [(metrics, won) for metrics, won, _ in weighted_training_data]
        sample_weights = [weight for _, _, weight in weighted_training_data]

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

        # Optimize weights using AdaptiveModelTuner with sample weights
        tuner = AdaptiveModelTuner()
        from scipy.optimize import minimize

        def objective(weights_array):
            weights = PerformanceWeights.from_array(weights_array)
            # Use weighted evaluation if available
            return tuner.evaluate_weights_weighted(
                weights, training_data, sample_weights
            ) if hasattr(tuner, 'evaluate_weights_weighted') else tuner.evaluate_weights(
                weights, training_data
            )

        # Optimize with increased iterations for better convergence
        result = minimize(
            objective,
            current_weights.to_array(),
            method='Nelder-Mead',
            options={'maxiter': 150}  # Increased from 100
        )

        new_weights = PerformanceWeights.from_array(result.x)

        # Calculate session statistics for notes
        current_session_samples = sum(1 for w in sample_weights if w > 1.0)
        total_weight = sum(sample_weights)

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
            notes=(
                f"Trained on {len(training_data)} samples "
                f"({current_session_samples} from current session, "
                f"effective weight: {total_weight:.1f})"
            )
        )

        self.db.add(new_model)
        self.db.commit()

        logger.info(f"Created new model version: {version_name}")
        logger.info(f"New weights: {new_weights}")
        logger.info(
            f"Training used {len(training_data)} samples "
            f"({current_session_samples} session-weighted at {self.config.session_weight_multiplier}x)"
        )

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
