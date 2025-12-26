"""
Adaptive Model Tuning System

Self-improving model that optimizes performance metric weights based on actual match outcomes.

The system:
1. Tracks prediction accuracy (do high-performing players win more?)
2. Uses gradient descent to optimize weights
3. Validates changes to prevent overfitting
4. Suggests weight updates when confidence is high
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import PlayerMatchMetrics, MatchPlayer, Match


@dataclass
class PerformanceWeights:
    """Weights for calculating overall_impact."""

    combat_weight: float = 0.40
    economic_weight: float = 0.20
    team_contribution_weight: float = 0.30
    efficiency_weight: float = 0.10

    def to_array(self) -> np.ndarray:
        """Convert to numpy array for optimization."""
        return np.array(
            [
                self.combat_weight,
                self.economic_weight,
                self.team_contribution_weight,
                self.efficiency_weight,
            ]
        )

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "PerformanceWeights":
        """Create from numpy array."""
        # Ensure weights sum to 1.0
        arr = arr / np.sum(arr)
        return cls(
            combat_weight=float(arr[0]),
            economic_weight=float(arr[1]),
            team_contribution_weight=float(arr[2]),
            efficiency_weight=float(arr[3]),
        )

    def validate(self) -> bool:
        """Ensure weights are valid."""
        total = sum(
            [
                self.combat_weight,
                self.economic_weight,
                self.team_contribution_weight,
                self.efficiency_weight,
            ]
        )
        return abs(total - 1.0) < 0.001 and all(
            w >= 0
            for w in [
                self.combat_weight,
                self.economic_weight,
                self.team_contribution_weight,
                self.efficiency_weight,
            ]
        )


@dataclass
class ModelPerformance:
    """Performance metrics for the model."""

    win_prediction_accuracy: float  # How well high performance predicts wins
    correlation_strength: float  # Correlation between performance and winning
    sample_size: int
    confidence_score: float  # 0-1, how confident we are in the model


class AdaptiveModelTuner:
    """
    Tunes performance metric weights based on match outcomes.

    Uses gradient-free optimization (Nelder-Mead) to find weights that maximize
    the correlation between calculated performance and actual wins.
    """

    MIN_SAMPLES_FOR_TUNING = 50  # Need at least 50 matches to tune
    VALIDATION_SPLIT = 0.2  # Use 20% of data for validation
    CONFIDENCE_THRESHOLD = 0.75  # Only suggest changes above this confidence

    @staticmethod
    def calculate_overall_impact_custom(
        metrics: PlayerMatchMetrics, weights: PerformanceWeights
    ) -> float:
        """
        Calculate overall_impact with custom weights.

        Args:
            metrics: Player metrics
            weights: Custom weights to use

        Returns:
            Calculated overall impact score
        """
        # Team contribution score
        participation_score = metrics.team_fight_participation * 100
        team_fight_effectiveness = metrics.team_fight_damage_ratio * 100
        team_contribution_score = (participation_score + team_fight_effectiveness) / 2

        return (
            metrics.combat_score * weights.combat_weight
            + metrics.economic_score * weights.economic_weight
            + team_contribution_score * weights.team_contribution_weight
            + metrics.efficiency_score * weights.efficiency_weight
        )

    @staticmethod
    def evaluate_weights(
        weights: PerformanceWeights, data: List[Tuple[PlayerMatchMetrics, bool]]
    ) -> float:
        """
        Evaluate how well weights predict wins.

        Args:
            weights: Weights to evaluate
            data: List of (metrics, won) tuples

        Returns:
            Score (higher is better) - negative for minimization
        """
        if not data or not weights.validate():
            return -999999.0

        impacts = []
        outcomes = []

        for metrics, won in data:
            impact = AdaptiveModelTuner.calculate_overall_impact_custom(
                metrics, weights
            )
            impacts.append(impact)
            outcomes.append(1.0 if won else 0.0)

        impacts_arr = np.array(impacts)
        outcomes_arr = np.array(outcomes)

        # Calculate correlation between impact and winning
        correlation = np.corrcoef(impacts_arr, outcomes_arr)[0, 1]

        # We want to maximize correlation, so return negative for minimization
        return -abs(correlation)

    @staticmethod
    def fetch_training_data(
        db: Session, limit: int = 1000
    ) -> List[Tuple[PlayerMatchMetrics, bool]]:
        """
        Fetch recent match data for training.

        Args:
            db: Database session
            limit: Max matches to fetch

        Returns:
            List of (metrics, won) tuples
        """
        # Get recent matches with metrics
        results = (
            db.query(PlayerMatchMetrics, MatchPlayer.won)
            .join(MatchPlayer, PlayerMatchMetrics.match_player_id == MatchPlayer.id)
            .join(Match, MatchPlayer.match_id == Match.id)
            .order_by(Match.played_at.desc())
            .limit(limit)
            .all()
        )

        return [(metrics, bool(won)) for metrics, won in results]

    @staticmethod
    def calculate_match_prediction_accuracy(
        db: Session, weights: PerformanceWeights, limit: int = 1000
    ) -> Tuple[float, int, int]:
        """
        Calculate how accurately team performance predicts match winners.

        For each match:
        1. Calculate total performance for each team
        2. Predict team with higher performance wins
        3. Compare to actual winner

        Args:
            db: Database session
            weights: Weights to use for performance calculation
            limit: Max matches to evaluate

        Returns:
            Tuple of (accuracy, correct_predictions, total_matches)
        """
        # Get recent matches with metrics
        matches = db.query(Match).order_by(Match.played_at.desc()).limit(limit).all()

        if not matches:
            return 0.0, 0, 0

        correct_predictions = 0
        total_matches = 0

        for match in matches:
            # Get all players in this match
            match_players = (
                db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
            )

            if len(match_players) < 2:
                continue

            # Get metrics for all players
            player_metrics = {}
            for mp in match_players:
                metrics = (
                    db.query(PlayerMatchMetrics)
                    .filter(PlayerMatchMetrics.match_player_id == mp.id)
                    .first()
                )

                if metrics:
                    player_metrics[mp.id] = (
                        AdaptiveModelTuner.calculate_overall_impact_custom(
                            metrics, weights
                        ),
                        mp.team_number,
                        mp.won,
                    )

            if not player_metrics:
                continue

            # Calculate team performance scores
            team_scores = {}
            team_won = {}
            for mp_id, (impact, team_num, won) in player_metrics.items():
                if team_num not in team_scores:
                    team_scores[team_num] = []
                    team_won[team_num] = won
                team_scores[team_num].append(impact)

            # Need at least 2 teams
            if len(team_scores) < 2:
                continue

            # Calculate average team performance
            team_avg_scores = {
                team: sum(scores) / len(scores) for team, scores in team_scores.items()
            }

            # Predict winner: team with highest average performance
            predicted_winner = max(team_avg_scores, key=lambda k: team_avg_scores[k])

            # Get actual winner
            actual_winner = None
            for team, won in team_won.items():
                if won:
                    actual_winner = team
                    break

            if actual_winner is not None:
                total_matches += 1
                if predicted_winner == actual_winner:
                    correct_predictions += 1

        accuracy = correct_predictions / total_matches if total_matches > 0 else 0.0
        return accuracy, correct_predictions, total_matches

    @staticmethod
    def optimize_weights(
        db: Session, current_weights: Optional[PerformanceWeights] = None
    ) -> Tuple[PerformanceWeights, ModelPerformance]:
        """
        Optimize weights using recent match data.

        Args:
            db: Database session
            current_weights: Starting weights (optional)

        Returns:
            Tuple of (optimized_weights, performance_metrics)
        """
        from scipy.optimize import minimize

        # Fetch training data
        all_data = AdaptiveModelTuner.fetch_training_data(db)

        if len(all_data) < AdaptiveModelTuner.MIN_SAMPLES_FOR_TUNING:
            # Not enough data to optimize, but still calculate accuracy with current weights
            if current_weights is None:
                current_weights = PerformanceWeights()

            # Calculate accuracy even with limited data
            match_accuracy, correct, total = (
                AdaptiveModelTuner.calculate_match_prediction_accuracy(
                    db, current_weights, limit=1000
                )
            )

            return (
                current_weights,
                ModelPerformance(
                    win_prediction_accuracy=match_accuracy,
                    correlation_strength=0.0,
                    sample_size=len(all_data),
                    confidence_score=0.0,
                ),
            )

        # Split into training and validation
        # Set random seed for reproducibility
        import random

        random.seed(42)
        random.shuffle(all_data)

        split_idx = int(len(all_data) * (1 - AdaptiveModelTuner.VALIDATION_SPLIT))
        training_data = all_data[:split_idx]
        validation_data = all_data[split_idx:]

        # Starting weights
        if current_weights is None:
            current_weights = PerformanceWeights()

        x0 = current_weights.to_array()

        # Constraint: weights must sum to 1
        def constraint(x):
            return np.sum(x) - 1.0

        # Bounds: each weight must be between 0 and 1
        bounds = [(0.0, 1.0) for _ in range(4)]

        constraints = {"type": "eq", "fun": constraint}

        # Optimize
        result = minimize(
            lambda x: AdaptiveModelTuner.evaluate_weights(
                PerformanceWeights.from_array(x), training_data
            ),
            x0=x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 100},
        )

        # Get optimized weights
        optimized_weights = PerformanceWeights.from_array(result.x)

        # Evaluate on validation set (correlation)
        validation_score = -AdaptiveModelTuner.evaluate_weights(
            optimized_weights, validation_data
        )

        # Calculate REAL match prediction accuracy
        match_accuracy, correct, total = (
            AdaptiveModelTuner.calculate_match_prediction_accuracy(
                db, optimized_weights, limit=1000
            )
        )

        # Calculate confidence (based on sample size and correlation)
        confidence = min(1.0, (len(all_data) / 200) * validation_score)

        performance = ModelPerformance(
            win_prediction_accuracy=match_accuracy,  # Real accuracy: % of correct match predictions
            correlation_strength=validation_score,  # Correlation: player performance vs wins
            sample_size=len(all_data),
            confidence_score=confidence,
        )

        return optimized_weights, performance

    @staticmethod
    def suggest_weight_update(db: Session) -> Optional[Dict]:
        """
        Analyze recent matches and suggest weight updates if confident.

        Args:
            db: Database session

        Returns:
            Dict with suggested weights and reasoning, or None if no changes needed
        """
        current_weights = PerformanceWeights()  # Get current from config
        optimized_weights, performance = AdaptiveModelTuner.optimize_weights(
            db, current_weights
        )

        # Only suggest if we're confident
        if performance.confidence_score < AdaptiveModelTuner.CONFIDENCE_THRESHOLD:
            return {
                "suggestion": "insufficient_data",
                "reason": f"Need more matches (have {performance.sample_size}, need {AdaptiveModelTuner.MIN_SAMPLES_FOR_TUNING}+)",
                "confidence": performance.confidence_score,
                "current_weights": current_weights,
                "sample_size": performance.sample_size,
            }

        # Calculate weight changes
        changes = {
            "combat": optimized_weights.combat_weight - current_weights.combat_weight,
            "economic": optimized_weights.economic_weight
            - current_weights.economic_weight,
            "team_contribution": optimized_weights.team_contribution_weight
            - current_weights.team_contribution_weight,
            "efficiency": optimized_weights.efficiency_weight
            - current_weights.efficiency_weight,
        }

        # Check if changes are significant
        max_change = max(abs(v) for v in changes.values())
        if max_change < 0.05:
            return {
                "suggestion": "no_change_needed",
                "reason": "Current weights are already optimal",
                "confidence": performance.confidence_score,
                "current_weights": current_weights,
                "sample_size": performance.sample_size,
            }

        return {
            "suggestion": "update_recommended",
            "reason": f"Found {performance.correlation_strength:.1%} correlation improvement",
            "confidence": performance.confidence_score,
            "current_weights": current_weights,
            "suggested_weights": optimized_weights,
            "changes": changes,
            "sample_size": performance.sample_size,
            "performance": performance,
        }
