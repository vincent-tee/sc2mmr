"""
Component Accuracy Tracker

Tracks prediction accuracy for each component using Exponential Moving Average (EMA).
- Components: trueskill_mmr, session_mmr, combat, economic, efficiency
- EMA with alpha=0.1 (recent predictions matter more)
- All match history tracked from match #1
- Provides optimal weights based on accuracy
"""

from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import numpy as np
import json
import logging

from ..models import Player, ComponentAccuracy, MLConfig

logger = logging.getLogger(__name__)


class ComponentAccuracyTracker:
    """Track prediction accuracy with Exponential Moving Average."""

    COMPONENTS = ["trueskill_mmr", "session_mmr", "combat", "economic", "efficiency"]
    MIN_PREDICTIONS = 10  # Minimum before trusting accuracy
    EMA_ALPHA = 0.1  # Recent predictions matter more

    # Default weights (before enough data)
    DEFAULT_WEIGHTS = {
        "session_mmr": 0.40,
        "combat": 0.25,
        "economic": 0.20,
        "efficiency": 0.15,
    }

    @staticmethod
    def record_prediction(
        team1_ids: List[int],
        team2_ids: List[int],
        winner: int,  # 1 or 2
        db: Session,
    ) -> None:
        """
        Record which component correctly predicted winner using EMA.
        Called after EVERY match.

        Args:
            team1_ids: List of player IDs on team 1
            team2_ids: List of player IDs on team 2
            winner: Winning team number (1 or 2)
            db: Database session
        """
        try:
            t1_values = ComponentAccuracyTracker._get_team_components(team1_ids, db)
            t2_values = ComponentAccuracyTracker._get_team_components(team2_ids, db)

            for component in ComponentAccuracyTracker.COMPONENTS:
                diff = t1_values.get(component, 0) - t2_values.get(component, 0)
                predicted_winner = 1 if diff > 0 else 2
                was_correct = predicted_winner == winner

                ComponentAccuracyTracker._update_accuracy_ema(
                    component, was_correct, db
                )

            logger.debug(
                f"Recorded prediction accuracy for {len(ComponentAccuracyTracker.COMPONENTS)} components"
            )
        except Exception as e:
            logger.error(f"Error recording prediction: {e}")
            raise

    @staticmethod
    def _get_team_components(player_ids: List[int], db: Session) -> Dict[str, float]:
        """
        Get average component values for a team.

        Args:
            player_ids: List of player IDs
            db: Database session

        Returns:
            Dictionary of component name to average value
        """
        if not player_ids:
            return {c: 0.0 for c in ComponentAccuracyTracker.COMPONENTS}

        players = db.query(Player).filter(Player.id.in_(player_ids)).all()

        if not players:
            return {c: 0.0 for c in ComponentAccuracyTracker.COMPONENTS}

        return {
            "trueskill_mmr": float(np.mean([p.mmr or 1000 for p in players])),
            "session_mmr": float(
                np.mean([p.session_weighted_mmr or p.mmr or 1000 for p in players])
            ),
            "combat": float(np.mean([p.avg_combat_score or 50 for p in players])),
            "economic": float(np.mean([p.avg_economic_score or 50 for p in players])),
            "efficiency": float(
                np.mean([p.avg_efficiency_score or 50 for p in players])
            ),
        }

    @staticmethod
    def _update_accuracy_ema(component: str, was_correct: bool, db: Session) -> None:
        """
        Update accuracy using Exponential Moving Average.

        Formula: new_accuracy = alpha * current_result + (1 - alpha) * old_accuracy

        Args:
            component: Component name
            was_correct: Whether the prediction was correct
            db: Database session
        """
        try:
            accuracy = (
                db.query(ComponentAccuracy)
                .filter(ComponentAccuracy.component_name == component)
                .first()
            )

            if not accuracy:
                # Create new entry
                accuracy = ComponentAccuracy(
                    component_name=component,
                    predictions_correct=1 if was_correct else 0,
                    predictions_total=1,
                    accuracy=1.0 if was_correct else 0.0,
                    last_updated=datetime.utcnow(),
                )
                db.add(accuracy)
                db.commit()
                return

            # Update counts
            accuracy.predictions_total += 1
            if was_correct:
                accuracy.predictions_correct += 1

            # Apply EMA: new_accuracy = alpha * current_result + (1-alpha) * old_accuracy
            current_result = 1.0 if was_correct else 0.0
            accuracy.accuracy = (
                ComponentAccuracyTracker.EMA_ALPHA * current_result
                + (1 - ComponentAccuracyTracker.EMA_ALPHA) * accuracy.accuracy
            )

            accuracy.last_updated = datetime.utcnow()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating accuracy for {component}: {e}")
            raise

    @staticmethod
    def get_all_accuracies(db: Session) -> Dict[str, float]:
        """
        Get current EMA accuracy for all components.

        Args:
            db: Database session

        Returns:
            Dictionary of component name to accuracy (0.0 to 1.0)
        """
        accuracies = db.query(ComponentAccuracy).all()
        result = {a.component_name: a.accuracy for a in accuracies}

        # Fill in defaults for missing components
        for comp in ComponentAccuracyTracker.COMPONENTS:
            if comp not in result:
                result[comp] = 0.5  # Default 50% accuracy

        return result

    @staticmethod
    def get_accuracy_stats(db: Session) -> Dict[str, Dict]:
        """
        Get detailed accuracy stats for all components.

        Args:
            db: Database session

        Returns:
            Dictionary of component name to stats dict containing:
            - accuracy: Current EMA accuracy
            - predictions_total: Total predictions made
            - predictions_correct: Total correct predictions
            - last_updated: ISO timestamp of last update
        """
        accuracies = db.query(ComponentAccuracy).all()
        result = {}

        for a in accuracies:
            result[a.component_name] = {
                "accuracy": a.accuracy,
                "predictions_total": a.predictions_total,
                "predictions_correct": a.predictions_correct,
                "last_updated": a.last_updated.isoformat() if a.last_updated else None,
            }

        # Fill in defaults for missing components
        for comp in ComponentAccuracyTracker.COMPONENTS:
            if comp not in result:
                result[comp] = {
                    "accuracy": 0.5,
                    "predictions_total": 0,
                    "predictions_correct": 0,
                    "last_updated": None,
                }

        return result

    @staticmethod
    def get_optimal_weights(db: Session) -> Dict[str, float]:
        """
        Calculate weights based on component accuracies.
        Higher accuracy = higher weight.

        Args:
            db: Database session

        Returns:
            Dictionary of component weights, e.g.:
            {'session_mmr': 0.40, 'combat': 0.25, 'economic': 0.20, 'efficiency': 0.15}
        """
        accuracies = ComponentAccuracyTracker.get_all_accuracies(db)

        # Check if we have enough data
        components_with_data = (
            db.query(ComponentAccuracy)
            .filter(
                ComponentAccuracy.predictions_total
                >= ComponentAccuracyTracker.MIN_PREDICTIONS
            )
            .count()
        )

        # Require at least n-1 components to have enough data
        has_enough_data = (
            components_with_data >= len(ComponentAccuracyTracker.COMPONENTS) - 1
        )

        if not has_enough_data:
            # Check for saved recommended weights from backfill
            saved = ComponentAccuracyTracker._get_saved_weights(db)
            if saved:
                return saved
            return ComponentAccuracyTracker.DEFAULT_WEIGHTS.copy()

        # Filter to only ML-relevant components (exclude trueskill_mmr for balancing)
        ml_components = ["session_mmr", "combat", "economic", "efficiency"]
        valid_accuracies = {k: v for k, v in accuracies.items() if k in ml_components}

        # Normalize to sum to 1.0
        total = sum(valid_accuracies.values())
        if total == 0:
            return ComponentAccuracyTracker.DEFAULT_WEIGHTS.copy()

        weights = {k: v / total for k, v in valid_accuracies.items()}

        # Apply minimum weight (10%)
        min_weight = 0.10
        for k in weights:
            if weights[k] < min_weight:
                weights[k] = min_weight

        # Renormalize after applying minimum
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        return weights

    @staticmethod
    def save_recommended_weights(weights: Dict[str, float], db: Session) -> None:
        """
        Save recommended weights to MLConfig table.

        Args:
            weights: Dictionary of component weights
            db: Database session
        """
        try:
            config = (
                db.query(MLConfig)
                .filter(MLConfig.config_key == "recommended_weights")
                .first()
            )

            if config:
                config.config_value = json.dumps(weights)
                config.last_updated = datetime.utcnow()
            else:
                config = MLConfig(
                    config_key="recommended_weights",
                    config_value=json.dumps(weights),
                    last_updated=datetime.utcnow(),
                )
                db.add(config)

            db.commit()
            logger.info(f"Saved recommended weights: {weights}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving recommended weights: {e}")
            raise

    @staticmethod
    def _get_saved_weights(db: Session) -> Optional[Dict[str, float]]:
        """
        Get saved recommended weights from MLConfig.

        Args:
            db: Database session

        Returns:
            Dictionary of weights if found, None otherwise
        """
        config = (
            db.query(MLConfig)
            .filter(MLConfig.config_key == "recommended_weights")
            .first()
        )

        if config:
            try:
                return json.loads(config.config_value)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse saved weights: {e}")
                return None

        return None

    @staticmethod
    def reset_component_accuracy(component: str, db: Session) -> bool:
        """
        Reset accuracy tracking for a specific component.

        Args:
            component: Component name to reset
            db: Database session

        Returns:
            True if reset successful, False if component not found
        """
        if component not in ComponentAccuracyTracker.COMPONENTS:
            logger.warning(f"Unknown component: {component}")
            return False

        try:
            accuracy = (
                db.query(ComponentAccuracy)
                .filter(ComponentAccuracy.component_name == component)
                .first()
            )

            if accuracy:
                accuracy.predictions_correct = 0
                accuracy.predictions_total = 0
                accuracy.accuracy = 0.5
                accuracy.last_updated = datetime.utcnow()
                db.commit()
                logger.info(f"Reset accuracy for component: {component}")
                return True

            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error resetting component accuracy: {e}")
            raise

    @staticmethod
    def reset_all_accuracies(db: Session) -> int:
        """
        Reset accuracy tracking for all components.

        Args:
            db: Database session

        Returns:
            Number of components reset
        """
        try:
            count = db.query(ComponentAccuracy).delete()
            db.commit()
            logger.info(f"Reset accuracy for {count} components")
            return count
        except Exception as e:
            db.rollback()
            logger.error(f"Error resetting all accuracies: {e}")
            raise
