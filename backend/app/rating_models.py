"""
Multi-Model Rating System

Provides different approaches to rating players and balancing teams:
1. TrueSkill (pure win/loss)
2. Impact (pure performance metrics)
3. Hybrid (configurable weights)
4. Ensemble (combines multiple signals)

Allows experimentation to find the best model for your group.
"""

from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session

from .models import Player


class RatingModel(str, Enum):
    """Available rating models."""

    TRUESKILL = "trueskill"  # Pure TrueSkill MMR (win/loss only)
    SESSION = "session"  # Session-weighted MMR (recent matches heavy)
    IMPACT = "impact"  # Pure performance metrics
    HYBRID_BALANCED = "hybrid_balanced"  # 50/50 TrueSkill and Impact
    HYBRID_SKILL_HEAVY = "hybrid_skill_heavy"  # 70% TrueSkill, 30% Impact
    HYBRID_IMPACT_HEAVY = "hybrid_impact_heavy"  # 30% TrueSkill, 70% Impact
    IMPACT_ECONOMIC = "impact_economic"  # 100% economic score
    IMPACT_COMBAT = "impact_combat"  # 100% combat score
    ENSEMBLE = "ensemble"  # Weighted ensemble of all signals


@dataclass
class PlayerRating:
    """Player rating with breakdown by component."""

    player_id: int
    player_name: str

    # Component ratings
    trueskill_mmr: float
    session_mmr: float
    economic_score: float
    combat_score: float
    efficiency_score: float
    overall_impact: float

    # Computed ratings by model
    trueskill_rating: float = 0.0
    session_rating: float = 0.0
    impact_rating: float = 0.0
    hybrid_balanced: float = 0.0
    hybrid_skill_heavy: float = 0.0
    hybrid_impact_heavy: float = 0.0
    combat_only: float = 0.0
    economic_only: float = 0.0
    ensemble_rating: float = 0.0

    def __post_init__(self):
        """Calculate all model ratings."""
        # TrueSkill (pure MMR)
        self.trueskill_rating = self.trueskill_mmr

        # Session-weighted rating
        self.session_rating = self.session_mmr

        # Impact (pure performance)
        # Normalize to similar scale as MMR (starting at 3500, range ±1000)
        # impact_rating = 3500 + (overall_impact - 50) * 20
        self.impact_rating = 3500.0 + (self.overall_impact - 50.0) * 20.0

        # Hybrid models
        self.hybrid_balanced = self.trueskill_mmr * 0.5 + self.impact_rating * 0.5

        self.hybrid_skill_heavy = self.trueskill_mmr * 0.7 + self.impact_rating * 0.3

        self.hybrid_impact_heavy = self.trueskill_mmr * 0.3 + self.impact_rating * 0.7

        # Component-specific models
        self.combat_only = 3500.0 + (self.combat_score - 50.0) * 20.0
        self.economic_only = 3500.0 + (self.economic_score - 50.0) * 20.0

        # Ensemble (combines multiple signals with learned weights)
        # Adjusted for 100x scale
        self.ensemble_rating = (
            self.trueskill_mmr * 0.4
            + (3500 + (self.combat_score - 50) * 20) * 0.25
            + (3500 + (self.economic_score - 50) * 20) * 0.2
            + (3500 + (self.efficiency_score - 50) * 20) * 0.15
        )

    def get_rating(self, model: RatingModel) -> float:
        """Get rating for specified model."""
        model_map = {
            RatingModel.TRUESKILL: self.trueskill_rating,
            RatingModel.SESSION: self.session_rating,
            RatingModel.IMPACT: self.impact_rating,
            RatingModel.HYBRID_BALANCED: self.hybrid_balanced,
            RatingModel.HYBRID_SKILL_HEAVY: self.hybrid_skill_heavy,
            RatingModel.HYBRID_IMPACT_HEAVY: self.hybrid_impact_heavy,
            RatingModel.IMPACT_ECONOMIC: self.economic_only,
            RatingModel.IMPACT_COMBAT: self.combat_only,
            RatingModel.ENSEMBLE: self.ensemble_rating,
        }
        return model_map.get(model, self.trueskill_rating)


class RatingModelService:
    """Service for calculating ratings using different models."""

    @staticmethod
    def get_player_rating(
        player: Player, model: RatingModel = RatingModel.TRUESKILL
    ) -> PlayerRating:
        """
        Get player rating with all model variants.

        Args:
            player: Player object
            model: Which model to use (optional, calculates all)

        Returns:
            PlayerRating with all model scores
        """
        rating = PlayerRating(
            player_id=player.id,
            player_name=player.name,
            trueskill_mmr=player.mmr,
            session_mmr=player.session_weighted_mmr or player.mmr,
            economic_score=player.avg_economic_score,
            combat_score=player.avg_combat_score,
            efficiency_score=player.avg_efficiency_score,
            overall_impact=player.avg_overall_impact,
        )

        return rating

    @staticmethod
    def get_all_player_ratings(
        db: Session, player_ids: Optional[List[int]] = None
    ) -> List[PlayerRating]:
        """
        Get ratings for all players (or subset).

        Args:
            db: Database session
            player_ids: Optional list of player IDs to filter

        Returns:
            List of PlayerRating objects
        """
        query = db.query(Player)
        if player_ids:
            query = query.filter(Player.id.in_(player_ids))

        players = query.all()
        return [RatingModelService.get_player_rating(p) for p in players]

    @staticmethod
    def calculate_team_rating(
        player_ratings: List[PlayerRating], model: RatingModel
    ) -> float:
        """
        Calculate total team rating for a model.

        Args:
            player_ratings: List of player ratings
            model: Which model to use

        Returns:
            Total team rating
        """
        return sum(pr.get_rating(model) for pr in player_ratings)

    @staticmethod
    def predict_match_winner(
        team1_ratings: List[PlayerRating],
        team2_ratings: List[PlayerRating],
        model: RatingModel,
    ) -> Tuple[int, float]:
        """
        Predict which team will win using specified model.

        Args:
            team1_ratings: Team 1 player ratings
            team2_ratings: Team 2 player ratings
            model: Which model to use for prediction

        Returns:
            Tuple of (predicted_winner_team, confidence)
            predicted_winner_team: 1 or 2
            confidence: 0.5-1.0 (0.5 = even, 1.0 = guaranteed)
        """
        team1_rating = RatingModelService.calculate_team_rating(team1_ratings, model)
        team2_rating = RatingModelService.calculate_team_rating(team2_ratings, model)

        # Calculate win probability using rating difference
        rating_diff = abs(team1_rating - team2_rating)
        avg_rating = (team1_rating + team2_rating) / 2

        # Confidence based on rating difference
        # 0 diff = 50% confidence, large diff = 100% confidence
        if avg_rating > 0:
            confidence = 0.5 + (rating_diff / (2 * avg_rating))
        else:
            confidence = 0.5

        confidence = min(1.0, max(0.5, confidence))

        predicted_winner = 1 if team1_rating > team2_rating else 2

        return predicted_winner, confidence

    @staticmethod
    def calculate_match_quality(
        team1_ratings: List[PlayerRating],
        team2_ratings: List[PlayerRating],
        model: RatingModel,
    ) -> float:
        """
        Calculate match quality (balance) for specified model.

        Args:
            team1_ratings: Team 1 player ratings
            team2_ratings: Team 2 player ratings
            model: Which model to use

        Returns:
            Match quality score 0-1 (1 = perfectly balanced)
        """
        team1_rating = RatingModelService.calculate_team_rating(team1_ratings, model)
        team2_rating = RatingModelService.calculate_team_rating(team2_ratings, model)

        # Quality based on rating difference
        rating_diff = abs(team1_rating - team2_rating)
        avg_rating = max(abs(team1_rating + team2_rating) / 2, 1.0)

        # Normalize: 0 diff = 1.0 quality, large diff = 0.0 quality
        quality = max(0.0, 1.0 - (rating_diff / avg_rating))

        return quality


class ModelComparison:
    """Compare different models on historical data."""

    @dataclass
    class ModelMetrics:
        """Metrics for a single model."""

        model_name: str
        correct_predictions: int
        total_predictions: int
        accuracy: float
        avg_confidence: float
        avg_match_quality: float

    @staticmethod
    def compare_models_on_matches(
        db: Session, match_data: List[Dict], models: Optional[List[RatingModel]] = None
    ) -> Dict[str, ModelMetrics]:
        """
        Compare multiple models on historical matches.

        Args:
            db: Database session
            match_data: List of dicts with 'team1_ids', 'team2_ids', 'winner'
            models: Which models to compare (default: all)

        Returns:
            Dict mapping model name to metrics
        """
        if models is None:
            models = list(RatingModel)

        results = {}

        for model in models:
            correct = 0
            total = 0
            confidences = []
            qualities = []

            for match in match_data:
                # Get player ratings
                team1_players = (
                    db.query(Player).filter(Player.id.in_(match["team1_ids"])).all()
                )
                team2_players = (
                    db.query(Player).filter(Player.id.in_(match["team2_ids"])).all()
                )

                team1_ratings = [
                    RatingModelService.get_player_rating(p) for p in team1_players
                ]
                team2_ratings = [
                    RatingModelService.get_player_rating(p) for p in team2_players
                ]

                # Make prediction
                predicted_winner, confidence = RatingModelService.predict_match_winner(
                    team1_ratings, team2_ratings, model
                )

                # Check if correct
                if predicted_winner == match["winner"]:
                    correct += 1

                total += 1
                confidences.append(confidence)

                # Calculate match quality
                quality = RatingModelService.calculate_match_quality(
                    team1_ratings, team2_ratings, model
                )
                qualities.append(quality)

            # Calculate metrics
            accuracy = correct / total if total > 0 else 0.0
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            avg_quality = sum(qualities) / len(qualities) if qualities else 0.0

            results[model.value] = ModelComparison.ModelMetrics(
                model_name=model.value,
                correct_predictions=correct,
                total_predictions=total,
                accuracy=accuracy,
                avg_confidence=avg_confidence,
                avg_match_quality=avg_quality,
            )

        return results

    @staticmethod
    def recommend_best_model(
        comparison_results: Dict[str, ModelMetrics],
        min_improvement: float = 0.03,  # 3% improvement threshold
    ) -> Tuple[str, str]:
        """
        Recommend best model based on comparison results.

        Args:
            comparison_results: Results from compare_models_on_matches
            min_improvement: Minimum accuracy improvement to recommend complex model

        Returns:
            Tuple of (recommended_model, reason)
        """
        # Get TrueSkill baseline
        trueskill_metrics = comparison_results.get("trueskill")
        if not trueskill_metrics:
            return ("trueskill", "No baseline data")

        trueskill_accuracy = trueskill_metrics.accuracy

        # Find best model
        best_model = max(comparison_results.items(), key=lambda x: x[1].accuracy)

        best_model_name, best_metrics = best_model

        # Check if improvement is significant
        improvement = best_metrics.accuracy - trueskill_accuracy

        if improvement < min_improvement:
            return (
                "trueskill",
                f"Simple TrueSkill works well ({trueskill_accuracy:.1%} accuracy). "
                f"Best model only {improvement:.1%} better - not worth complexity.",
            )

        if best_model_name == "impact":
            return (
                "impact",
                f"Pure impact rating is {improvement:.1%} better than TrueSkill! "
                f"Individual performance matters more than team results for your group.",
            )

        if "impact_heavy" in best_model_name:
            return (
                "hybrid_impact_heavy",
                f"Impact-heavy hybrid is {improvement:.1%} better than TrueSkill. "
                f"Performance metrics are more predictive than win/loss.",
            )

        if "ensemble" in best_model_name:
            return (
                "ensemble",
                f"Ensemble model is {improvement:.1%} better than TrueSkill. "
                f"Multiple signals combine for best predictions.",
            )

        return (
            best_model_name,
            f"{best_model_name} is {improvement:.1%} better than baseline "
            f"({best_metrics.accuracy:.1%} vs {trueskill_accuracy:.1%})",
        )


def get_model_description(model: RatingModel) -> str:
    """Get human-readable description of a model."""
    descriptions = {
        RatingModel.TRUESKILL: "Pure TrueSkill - Win/loss only, no performance metrics",
        RatingModel.SESSION: "Session-Weighted - Recent matches count 3x more",
        RatingModel.IMPACT: "Pure Impact - 100% performance-based, ignores wins/losses",
        RatingModel.HYBRID_BALANCED: "Balanced Hybrid - 50% TrueSkill, 50% Impact",
        RatingModel.HYBRID_SKILL_HEAVY: "Skill-Heavy Hybrid - 70% TrueSkill, 30% Impact",
        RatingModel.HYBRID_IMPACT_HEAVY: "Impact-Heavy Hybrid - 30% TrueSkill, 70% Impact",
        RatingModel.IMPACT_ECONOMIC: "Economic Only - Rewards resource collection",
        RatingModel.IMPACT_COMBAT: "Combat Only - Rewards damage dealing",
        RatingModel.ENSEMBLE: "Ensemble - Combines all signals with optimized weights",
    }
    return descriptions.get(model, "Unknown model")
