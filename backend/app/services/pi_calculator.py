"""
Performance Impact Calculator for Hybrid MMR System.

Calculates Performance Impact Modifier (PIM) based on in-game metrics.
PIM adjusts MMR gain/loss: actual_change = base_change × (1 + PIM)

Design Philosophy:
- Phase 1: Rule-based weighted formula (this implementation)
- Phase 2+: ML model can replace calculate_pim() method while keeping same interface

SPEC-ML-001 Implementation.
"""
import math
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models import MatchPlayer, PlayerMatchMetrics, Match, PerformanceFeatures
from app.config import settings


@dataclass
class MatchAverages:
    """
    Average metrics across all players in a match.

    Used for z-score normalization. Each metric has:
    - Mean value (for centering)
    - Standard deviation (for scaling)
    """
    # Combat metrics
    damage_ratio: float = 1.0
    damage_ratio_std: float = 0.5
    army_value_ratio: float = 1.0
    army_value_ratio_std: float = 0.5
    combat_score: float = 50.0
    combat_score_std: float = 20.0

    # Economic metrics
    spending_efficiency: float = 0.7
    spending_efficiency_std: float = 0.15
    economic_score: float = 50.0
    economic_score_std: float = 20.0
    resource_advantage: float = 0.0
    resource_advantage_std: float = 10000.0

    # Team metrics
    team_fight_participation: float = 0.5
    team_fight_participation_std: float = 0.2
    team_fight_damage_ratio: float = 1.0
    team_fight_damage_ratio_std: float = 0.5
    overall_impact: float = 50.0
    overall_impact_std: float = 20.0

    # Efficiency metrics
    efficiency_score: float = 50.0
    efficiency_score_std: float = 20.0


@dataclass
class PIMBreakdown:
    """
    Breakdown of PIM by category.

    Provides transparency into how PIM was calculated,
    useful for debugging and user explanation.
    """
    combat: float = 0.0      # Combat performance contribution
    economic: float = 0.0    # Economic performance contribution
    team: float = 0.0        # Team contribution
    efficiency: float = 0.0  # Efficiency contribution
    total: float = 0.0       # Final bounded PIM value

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for API responses."""
        return {
            "combat": round(self.combat, 4),
            "economic": round(self.economic, 4),
            "team": round(self.team, 4),
            "efficiency": round(self.efficiency, 4),
            "total": round(self.total, 4),
        }


class PICalculator:
    """
    Performance Impact Calculator.

    Calculates PIM (Performance Impact Modifier) for each player in a match.
    Uses z-score normalization relative to match averages.

    PIM Range: [-0.5, +0.5] (configurable)
    - Positive: Above-average performance
    - Negative: Below-average performance
    - Zero: Average performance
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize calculator with optional custom weights.

        Args:
            weights: Custom weight dictionary. If None, uses config settings.
        """
        if weights:
            self.weights = weights
        else:
            # Load weights from centralized config
            self.weights = {
                # Combat (40%)
                "damage_ratio": settings.pim_weight_damage_ratio,
                "army_value_ratio": settings.pim_weight_army_value_ratio,
                "combat_score": settings.pim_weight_combat_score,
                # Economic (25%)
                "spending_efficiency": settings.pim_weight_spending_efficiency,
                "economic_score": settings.pim_weight_economic_score,
                "resource_advantage": settings.pim_weight_resource_advantage,
                # Team (25%)
                "team_fight_participation": settings.pim_weight_team_fight_participation,
                "team_fight_damage_ratio": settings.pim_weight_team_fight_damage_ratio,
                "overall_impact": settings.pim_weight_overall_impact,
                # Efficiency (10%)
                "efficiency_score": settings.pim_weight_efficiency_score,
            }

        self.pim_min = settings.pim_min
        self.pim_max = settings.pim_max
        self.pim_version = settings.pim_version

    def calculate_match_averages(self, db: Session, match_id: int) -> MatchAverages:
        """
        Calculate average metrics for all players in a match.

        Args:
            db: Database session
            match_id: Match ID

        Returns:
            MatchAverages with mean and std for each metric
        """
        # Get all match players with their metrics
        match_players = db.query(MatchPlayer).filter(
            MatchPlayer.match_id == match_id
        ).all()

        if not match_players:
            return MatchAverages()

        # Collect metrics from all players
        metrics_list: List[PlayerMatchMetrics] = []
        for mp in match_players:
            # Get associated metrics using the relationship
            metrics = db.query(PlayerMatchMetrics).filter(
                PlayerMatchMetrics.match_player_id == mp.id
            ).first()
            if metrics:
                metrics_list.append(metrics)

        if not metrics_list:
            return MatchAverages()

        def calc_avg_and_std(values: List[float]) -> Tuple[float, float]:
            """Calculate mean and standard deviation."""
            if not values:
                return 0.0, 1.0
            n = len(values)
            mean = sum(values) / n
            if n < 2:
                return mean, 1.0
            variance = sum((v - mean) ** 2 for v in values) / n
            std = math.sqrt(variance) if variance > 0 else 1.0
            return mean, max(std, 0.001)  # Prevent division by zero

        averages = MatchAverages()

        # Calculate for each metric
        for metric_name in self.weights.keys():
            values = []
            for m in metrics_list:
                val = getattr(m, metric_name, None)
                if val is not None:
                    values.append(float(val))
                else:
                    values.append(0.0)

            mean, std = calc_avg_and_std(values)
            setattr(averages, metric_name, mean)
            setattr(averages, f"{metric_name}_std", std)

        return averages

    def calculate_z_score(self, value: float, mean: float, std: float) -> float:
        """
        Calculate z-score (standard score).

        Args:
            value: The metric value
            mean: Population mean
            std: Population standard deviation

        Returns:
            Z-score indicating how many std devs from mean
        """
        if std <= 0:
            return 0.0
        return (value - mean) / std

    def calculate_pim(
        self,
        metrics: Optional[PlayerMatchMetrics],
        match_averages: MatchAverages
    ) -> Tuple[float, PIMBreakdown]:
        """
        Calculate Performance Impact Modifier.

        Args:
            metrics: Player's match metrics (can be None for missing data)
            match_averages: Average metrics for the match

        Returns:
            Tuple of (pim, breakdown)
            - pim: Float in range [pim_min, pim_max]
            - breakdown: PIMBreakdown with category scores
        """
        breakdown = PIMBreakdown()

        if not metrics:
            return 0.0, breakdown

        z_scores: Dict[str, float] = {}

        # Calculate z-scores for each metric
        for metric_name, weight in self.weights.items():
            value = getattr(metrics, metric_name, None)
            if value is None:
                value = 0.0
            else:
                value = float(value)

            mean = getattr(match_averages, metric_name, 0.0)
            std = getattr(match_averages, f"{metric_name}_std", 1.0)

            z_scores[metric_name] = self.calculate_z_score(value, mean, std)

        # Calculate category breakdowns (weighted z-scores)
        breakdown.combat = (
            z_scores.get("damage_ratio", 0) * self.weights.get("damage_ratio", 0) +
            z_scores.get("army_value_ratio", 0) * self.weights.get("army_value_ratio", 0) +
            z_scores.get("combat_score", 0) * self.weights.get("combat_score", 0)
        )

        breakdown.economic = (
            z_scores.get("spending_efficiency", 0) * self.weights.get("spending_efficiency", 0) +
            z_scores.get("economic_score", 0) * self.weights.get("economic_score", 0) +
            z_scores.get("resource_advantage", 0) * self.weights.get("resource_advantage", 0)
        )

        breakdown.team = (
            z_scores.get("team_fight_participation", 0) * self.weights.get("team_fight_participation", 0) +
            z_scores.get("team_fight_damage_ratio", 0) * self.weights.get("team_fight_damage_ratio", 0) +
            z_scores.get("overall_impact", 0) * self.weights.get("overall_impact", 0)
        )

        breakdown.efficiency = (
            z_scores.get("efficiency_score", 0) * self.weights.get("efficiency_score", 0)
        )

        # Raw PIM (sum of weighted z-scores)
        raw_pim = breakdown.combat + breakdown.economic + breakdown.team + breakdown.efficiency

        # Bound using tanh to [pim_min, pim_max]
        # tanh output is [-1, 1], scale to [pim_min, pim_max]
        bounded_pim = self.pim_max * math.tanh(raw_pim)

        breakdown.total = bounded_pim

        return bounded_pim, breakdown

    def apply_pim_to_mmr_change(self, base_change: float, pim: float) -> float:
        """
        Apply PIM to modify MMR change.

        For wins: good performance amplifies gain, bad performance reduces gain
        For losses: good performance reduces loss, bad performance amplifies loss

        Args:
            base_change: Raw MMR change from TrueSkill (positive for win, negative for loss)
            pim: Performance Impact Modifier [-0.5, +0.5]

        Returns:
            Modified MMR change

        Examples:
            Win (+50) with great performance (PIM=+0.3): 50 * 1.3 = +65
            Win (+50) with poor performance (PIM=-0.3): 50 * 0.7 = +35
            Loss (-50) with great performance (PIM=+0.3): -50 * 0.7 = -35
            Loss (-50) with poor performance (PIM=-0.3): -50 * 1.3 = -65
        """
        modifier = 1.0 + pim  # Range: [0.5, 1.5] for pim in [-0.5, +0.5]

        if base_change >= 0:
            # Won: good performance = more gain
            return base_change * modifier
        else:
            # Lost: good performance = less loss
            # Invert the modifier for losses
            return base_change * (2.0 - modifier)

    def calculate_and_store_features(
        self,
        db: Session,
        match_player: MatchPlayer,
        raw_mmr_change: float,
        match_averages: Optional[MatchAverages] = None
    ) -> PerformanceFeatures:
        """
        Calculate PIM and store all features in the database.

        This is the main entry point for processing a player's match performance.

        Args:
            db: Database session
            match_player: MatchPlayer record
            raw_mmr_change: Raw MMR change from TrueSkill
            match_averages: Pre-calculated match averages (optional, will calculate if None)

        Returns:
            PerformanceFeatures record (already added to session)
        """
        # Get match averages if not provided
        if match_averages is None:
            match_averages = self.calculate_match_averages(db, match_player.match_id)

        # Get player's metrics
        metrics = db.query(PlayerMatchMetrics).filter(
            PlayerMatchMetrics.match_player_id == match_player.id
        ).first()

        # Calculate PIM
        pim, breakdown = self.calculate_pim(metrics, match_averages)

        # Calculate hybrid MMR change
        hybrid_mmr_change = self.apply_pim_to_mmr_change(raw_mmr_change, pim)

        # Calculate z-scores for storage
        z_scores: Dict[str, float] = {}
        if metrics:
            for metric_name in self.weights.keys():
                value = getattr(metrics, metric_name, 0) or 0
                mean = getattr(match_averages, metric_name, 0)
                std = getattr(match_averages, f"{metric_name}_std", 1)
                z_scores[metric_name] = self.calculate_z_score(value, mean, std)

        # Create PerformanceFeatures record
        features = PerformanceFeatures(
            match_player_id=match_player.id,

            # Z-score normalized features
            damage_ratio_z=z_scores.get("damage_ratio", 0.0),
            army_value_ratio_z=z_scores.get("army_value_ratio", 0.0),
            combat_score_z=z_scores.get("combat_score", 0.0),
            spending_efficiency_z=z_scores.get("spending_efficiency", 0.0),
            economic_score_z=z_scores.get("economic_score", 0.0),
            resource_advantage_z=z_scores.get("resource_advantage", 0.0),
            team_fight_participation_z=z_scores.get("team_fight_participation", 0.0),
            team_fight_damage_ratio_z=z_scores.get("team_fight_damage_ratio", 0.0),
            overall_impact_z=z_scores.get("overall_impact", 0.0),
            efficiency_score_z=z_scores.get("efficiency_score", 0.0),

            # PIM values
            pim=pim,
            pim_combat=breakdown.combat,
            pim_economic=breakdown.economic,
            pim_team=breakdown.team,
            pim_efficiency=breakdown.efficiency,
            pim_version=self.pim_version,

            # MMR changes
            raw_mmr_change=raw_mmr_change,
            hybrid_mmr_change=hybrid_mmr_change,
        )

        db.add(features)
        return features

    def get_weights(self) -> Dict[str, float]:
        """
        Get current weight configuration.

        Returns:
            Dictionary of metric name to weight
        """
        return self.weights.copy()

    def validate_weights(self) -> bool:
        """
        Validate that weights sum to approximately 1.0.

        Returns:
            True if weights are valid
        """
        total = sum(self.weights.values())
        return 0.99 <= total <= 1.01
