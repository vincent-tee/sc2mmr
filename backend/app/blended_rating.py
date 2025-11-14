"""
Blended Rating System - Combines TrueSkill with Adaptive Model

This system:
1. Uses TrueSkill as the foundation (stable, proven)
2. Applies adaptive model corrections (context-aware adjustments)
3. Monitors impact and allows rollback
4. Provides detailed logging for analysis

Architecture:
------------
TrueSkill (85%) + Adaptive Model (15%) = Final MMR Change

Example:
- Player wins, TrueSkill says +25 MMR
- Adaptive model sees they were heavily favored (70% predicted)
- Adjustment: Lower the gain slightly (expected win)
- Final: +22 MMR

Conversely:
- Underdog wins, TrueSkill says +25 MMR
- Adaptive model sees they had only 30% chance
- Adjustment: Increase the gain (impressive upset!)
- Final: +30 MMR
"""
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import logging
import trueskill
from datetime import datetime
from sqlalchemy.orm import Session

from .models import Match, MatchPlayer, Player
from .rating_system import RatingSystem
from .adaptive_model import PerformanceWeights, AdaptiveModelTuner

logger = logging.getLogger(__name__)


@dataclass
class BlendConfig:
    """Configuration for blended rating system."""
    # Blending weights
    trueskill_weight: float = 0.85  # 85% TrueSkill
    adaptive_weight: float = 0.15   # 15% Adaptive adjustment

    # Safety limits
    max_adjustment_percent: float = 0.3  # Max 30% adjustment
    min_mmr_change: float = 5.0  # Minimum MMR change
    max_mmr_change: float = 50.0  # Maximum MMR change

    # Feature flags
    enabled: bool = False  # Start disabled for safety
    log_only_mode: bool = True  # Log adjustments without applying them

    # Monitoring
    alert_on_large_adjustment: float = 0.25  # Alert if adjustment > 25%


@dataclass
class BlendedRatingResult:
    """Result of a blended rating calculation."""
    # Original TrueSkill values
    trueskill_mmr_change: float
    trueskill_new_mu: float
    trueskill_new_sigma: float

    # Adaptive model values
    adaptive_prediction: float  # Win probability from adaptive model
    adaptive_adjustment_factor: float  # How much to adjust (0.7 - 1.3)

    # Final blended values
    final_mmr_change: float
    final_new_mu: float
    final_new_sigma: float

    # Metadata
    was_upset: bool
    prediction_confidence: float


class BlendedRatingSystem:
    """
    Combines TrueSkill with adaptive model predictions.

    The key insight: TrueSkill is great at tracking long-term skill,
    but the adaptive model captures short-term context (maps, races, synergies).
    """

    def __init__(self, config: BlendConfig = None):
        self.config = config or BlendConfig()

    def calculate_adaptive_adjustment(
        self,
        predicted_win_prob: float,
        actually_won: bool
    ) -> float:
        """
        Calculate how much to adjust MMR based on adaptive model prediction.

        Logic:
        - If team was heavily favored (>70%) and won: Reduce MMR gain (expected)
        - If team was underdog (<30%) and won: Increase MMR gain (impressive!)
        - If team was favored but lost: Increase MMR loss (bad performance)
        - If team was underdog and lost: Reduce MMR loss (expected)

        Args:
            predicted_win_prob: Adaptive model's win probability (0.0 - 1.0)
            actually_won: Whether the team actually won

        Returns:
            Adjustment factor (0.7 - 1.3)
            - 1.0 = no adjustment
            - > 1.0 = increase MMR change
            - < 1.0 = decrease MMR change
        """
        if actually_won:
            # Team won
            if predicted_win_prob > 0.7:
                # Heavy favorite won - expected, reduce gain
                # 0.7 prob → 0.95x, 0.9 prob → 0.85x
                adjustment = 1.0 - (predicted_win_prob - 0.5) * 0.5
            elif predicted_win_prob < 0.3:
                # Underdog won - impressive, increase gain
                # 0.3 prob → 1.2x, 0.1 prob → 1.3x
                adjustment = 1.0 + (0.5 - predicted_win_prob) * 0.6
            else:
                # Close match - normal gain
                adjustment = 1.0
        else:
            # Team lost
            if predicted_win_prob > 0.7:
                # Heavy favorite lost - bad, increase loss
                adjustment = 1.0 + (predicted_win_prob - 0.5) * 0.6
            elif predicted_win_prob < 0.3:
                # Underdog lost - expected, reduce loss
                adjustment = 1.0 - (0.5 - predicted_win_prob) * 0.5
            else:
                # Close match - normal loss
                adjustment = 1.0

        # Clamp to reasonable range
        adjustment = max(0.7, min(1.3, adjustment))

        return adjustment

    def blend_rating_update(
        self,
        old_rating: trueskill.Rating,
        new_rating_trueskill: trueskill.Rating,
        predicted_win_prob: float,
        actually_won: bool,
        old_mmr: float
    ) -> BlendedRatingResult:
        """
        Blend TrueSkill rating update with adaptive model adjustment.

        Args:
            old_rating: Original TrueSkill rating
            new_rating_trueskill: New rating from pure TrueSkill
            predicted_win_prob: Adaptive model's prediction
            actually_won: Actual match outcome
            old_mmr: Old MMR value

        Returns:
            BlendedRatingResult with all the details
        """
        # Calculate original changes
        trueskill_mmr_old = RatingSystem.get_conservative_rating(old_rating.mu, old_rating.sigma)
        trueskill_mmr_new = RatingSystem.get_conservative_rating(
            new_rating_trueskill.mu,
            new_rating_trueskill.sigma
        )
        trueskill_mmr_change = trueskill_mmr_new - trueskill_mmr_old

        # Get adaptive adjustment
        adaptive_adjustment = self.calculate_adaptive_adjustment(
            predicted_win_prob,
            actually_won
        )

        # Blend the adjustment
        if self.config.enabled and not self.config.log_only_mode:
            # Apply blending
            blended_adjustment = (
                self.config.trueskill_weight * 1.0 +
                self.config.adaptive_weight * adaptive_adjustment
            )

            # Apply adjustment to MMR change
            adjusted_mmr_change = trueskill_mmr_change * blended_adjustment

            # Safety limits
            adjusted_mmr_change = max(
                -self.config.max_mmr_change,
                min(self.config.max_mmr_change, adjusted_mmr_change)
            )

            # Ensure minimum change
            if abs(adjusted_mmr_change) < self.config.min_mmr_change:
                if adjusted_mmr_change > 0:
                    adjusted_mmr_change = self.config.min_mmr_change
                else:
                    adjusted_mmr_change = -self.config.min_mmr_change

            final_mmr = old_mmr + adjusted_mmr_change

            # Back-calculate mu/sigma for the adjusted MMR
            # Keep sigma the same as TrueSkill calculated
            # Adjust mu to hit target MMR
            # MMR = 1000 + 40*mu - 120*sigma
            # mu = (MMR - 1000 + 120*sigma) / 40
            final_sigma = new_rating_trueskill.sigma
            final_mu = (final_mmr - 1000 + 120 * final_sigma) / 40

        else:
            # Log-only mode or disabled - use TrueSkill values
            adjusted_mmr_change = trueskill_mmr_change
            final_mu = new_rating_trueskill.mu
            final_sigma = new_rating_trueskill.sigma

        # Check if it was an upset
        was_upset = (actually_won and predicted_win_prob < 0.4) or \
                    (not actually_won and predicted_win_prob > 0.6)

        # Confidence in prediction (distance from 0.5)
        prediction_confidence = abs(predicted_win_prob - 0.5) * 2.0

        result = BlendedRatingResult(
            trueskill_mmr_change=trueskill_mmr_change,
            trueskill_new_mu=new_rating_trueskill.mu,
            trueskill_new_sigma=new_rating_trueskill.sigma,
            adaptive_prediction=predicted_win_prob,
            adaptive_adjustment_factor=adaptive_adjustment,
            final_mmr_change=adjusted_mmr_change,
            final_new_mu=final_mu,
            final_new_sigma=final_sigma,
            was_upset=was_upset,
            prediction_confidence=prediction_confidence
        )

        # Log the adjustment
        self._log_adjustment(result)

        # Alert on large adjustments
        adjustment_percent = abs(adaptive_adjustment - 1.0)
        if adjustment_percent > self.config.alert_on_large_adjustment:
            logger.warning(
                f"Large MMR adjustment: {adjustment_percent:.1%} "
                f"(Pred: {predicted_win_prob:.1%}, Won: {actually_won}, "
                f"Upset: {was_upset})"
            )

        return result

    def _log_adjustment(self, result: BlendedRatingResult) -> None:
        """Log the adjustment for monitoring."""
        mode = "LOG-ONLY" if self.config.log_only_mode else "APPLIED"
        logger.info(
            f"[{mode}] MMR Adjustment: "
            f"TrueSkill={result.trueskill_mmr_change:+.1f} → "
            f"Blended={result.final_mmr_change:+.1f} "
            f"(Adaptive={result.adaptive_adjustment_factor:.2f}x, "
            f"Pred={result.adaptive_prediction:.1%}, "
            f"Upset={result.was_upset})"
        )

    def update_ratings_from_match_blended(
        self,
        db: Session,
        match: Match,
        team_1_players: List[Tuple[Player, any]],
        team_2_players: List[Tuple[Player, any]],
        team_1_ratings: List[trueskill.Rating],
        team_2_ratings: List[trueskill.Rating],
        new_team_1_ratings: List[trueskill.Rating],
        new_team_2_ratings: List[trueskill.Rating],
        team_1_won: bool
    ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Apply blended rating updates to all players.

        This replaces the pure TrueSkill updates with blended ones.

        Args:
            db: Database session
            match: Match object
            team_1_players: List of (Player, PlayerData) tuples for team 1
            team_2_players: List of (Player, PlayerData) tuples for team 2
            team_1_ratings: Old TrueSkill ratings for team 1
            team_2_ratings: Old TrueSkill ratings for team 2
            new_team_1_ratings: New TrueSkill ratings for team 1
            new_team_2_ratings: New TrueSkill ratings for team 2
            team_1_won: Whether team 1 won

        Returns:
            Tuple of (team1_new_ratings, team2_new_ratings)
            Each is a list of (mu, sigma) tuples
        """
        # Get adaptive model predictions
        team1_win_prob = match.predicted_team1_win_prob or 0.5
        team2_win_prob = match.predicted_team2_win_prob or 0.5

        # Process team 1
        team1_blended_ratings = []
        for i, (player, _) in enumerate(team_1_players):
            old_mmr = RatingSystem.get_conservative_rating(
                team_1_ratings[i].mu,
                team_1_ratings[i].sigma
            )

            result = self.blend_rating_update(
                old_rating=team_1_ratings[i],
                new_rating_trueskill=new_team_1_ratings[i],
                predicted_win_prob=team1_win_prob,
                actually_won=team_1_won,
                old_mmr=old_mmr
            )

            team1_blended_ratings.append((result.final_new_mu, result.final_new_sigma))

        # Process team 2
        team2_blended_ratings = []
        for i, (player, _) in enumerate(team_2_players):
            old_mmr = RatingSystem.get_conservative_rating(
                team_2_ratings[i].mu,
                team_2_ratings[i].sigma
            )

            result = self.blend_rating_update(
                old_rating=team_2_ratings[i],
                new_rating_trueskill=new_team_2_ratings[i],
                predicted_win_prob=team2_win_prob,
                actually_won=not team_1_won,
                old_mmr=old_mmr
            )

            team2_blended_ratings.append((result.final_new_mu, result.final_new_sigma))

        return (team1_blended_ratings, team2_blended_ratings)


# ============================================================================
# Monitoring and Analysis
# ============================================================================

class BlendedRatingMonitor:
    """
    Monitor the impact of blended ratings.

    Compares blended system to pure TrueSkill to ensure we're improving.
    """

    def __init__(self, db: Session):
        self.db = db

    def analyze_impact(self, days: int = 30) -> Dict:
        """
        Analyze the impact of blended ratings over the past N days.

        Returns:
            Dictionary with analysis results
        """
        # This would query prediction logs and compare
        # blended vs pure TrueSkill accuracy
        return {
            "blended_accuracy": 0.0,
            "trueskill_accuracy": 0.0,
            "improvement": 0.0,
            "total_matches": 0,
            "upset_detection_rate": 0.0
        }

    def should_enable_blending(self) -> Tuple[bool, str]:
        """
        Decide if blending should be enabled based on performance.

        Returns:
            (should_enable, reason)
        """
        analysis = self.analyze_impact()

        if analysis["total_matches"] < 100:
            return (False, "Not enough data - need at least 100 matches")

        improvement = analysis["improvement"]
        if improvement > 0.05:  # 5% improvement
            return (True, f"Blending shows {improvement:.1%} improvement in accuracy")
        elif improvement < -0.02:  # Worse by 2%
            return (False, f"Blending is {-improvement:.1%} worse - keeping TrueSkill only")
        else:
            return (False, "Improvement is marginal - staying conservative with TrueSkill")
