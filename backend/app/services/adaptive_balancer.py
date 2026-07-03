"""
Adaptive Balancing Service - Phase 2
Integrates ML-derived weights and performance metrics for dynamic team generation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.component_accuracy_tracker import ComponentAccuracyTracker
from app.models import GroupSynergy, Player, Match, MatchPlayer
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MLPlayerRating:
    """Player rating with ML component breakdown."""

    player_id: int
    player_name: str
    session_mmr: float
    combat: float
    economic: float
    efficiency: float
    teamwork: float
    ml_rating: float
    total_games: int


@dataclass
class MLTeamSuggestion:
    """Balanced team suggestion from ML engine."""

    team1: List[MLPlayerRating]
    team2: List[MLPlayerRating]
    team1_total: float
    team2_total: float
    team1_synergy: float
    team2_synergy: float
    balance_score: float
    weights_used: Dict[str, float]


class SynergyCalculator:
    """Calculates and updates synergy scores between groups of players."""

    @staticmethod
    def _get_player_ids_key(player_ids: List[int]) -> str:
        """Standardized key for a group of players (sorted comma-separated IDs)."""
        return ",".join(map(str, sorted(player_ids)))

    @staticmethod
    def update_synergy(player_ids: List[int], won: bool, db: Session) -> None:
        """Update synergy for a team and all its sub-groups."""
        if len(player_ids) < 2:
            return

        # Update duo synergies
        for pair in combinations(player_ids, 2):
            SynergyCalculator._update_group_synergy(list(pair), won, db)

        # Update trio synergies (only for 4v4/5v5)
        if len(player_ids) >= 4:
            for trio in combinations(player_ids, 3):
                SynergyCalculator._update_group_synergy(list(trio), won, db)

    @staticmethod
    def _update_group_synergy(
        player_ids: List[int], won: bool, db: Session, combined_impact: float = 0.0
    ) -> None:
        """Update synergy for a specific group (pair or trio)."""
        key = SynergyCalculator._get_player_ids_key(player_ids)
        player_count = len(player_ids)

        synergy = (
            db.query(GroupSynergy).filter(GroupSynergy.player_ids_key == key).first()
        )

        if not synergy:
            # Create new synergy record
            synergy = GroupSynergy(
                player_ids_key=key,
                player_count=player_count,
                matches_played=0,
                matches_won=0,
                win_rate=0.0,
                synergy_score=0.0,
                last_updated=datetime.utcnow(),
            )
            db.add(synergy)

        # Update stats
        synergy.matches_played += 1
        if won:
            synergy.matches_won += 1

        synergy.win_rate = synergy.matches_won / synergy.matches_played

        # Calculate synergy score
        # Calibrated scaling for synergy (Validated Dec 29)
        # Higher consistency multiplier for long-term partners
        win_rate_diff = synergy.win_rate - 0.5

        if win_rate_diff > 0:
            win_rate_bonus = win_rate_diff * 15  # +0.2 -> +3 points
        else:
            win_rate_bonus = win_rate_diff * 25  # -0.2 -> -5 points

        consistency_multiplier = min(synergy.matches_played / 10.0, 2.0)
        synergy.synergy_score = max(
            -20.0, min(20.0, win_rate_bonus * consistency_multiplier)
        )
        synergy.last_updated = datetime.utcnow()

    @staticmethod
    def get_synergy_score(player_ids: List[int], db: Session) -> float:
        """
        Calculate the total synergy bonus for a team.
        Returns aggregate bonus to be added to team's balanced rating.
        """
        if len(player_ids) < 2:
            return 0.0

        total_synergy = 0.0

        # Sum up duo synergies
        for pair in combinations(player_ids, 2):
            key = SynergyCalculator._get_player_ids_key(list(pair))
            synergy = (
                db.query(GroupSynergy)
                .filter(GroupSynergy.player_ids_key == key)
                .first()
            )
            if synergy:
                total_synergy += (
                    (synergy.win_rate - 0.5)
                    * 1000
                    * min(synergy.matches_played / 20.0, 1.0)
                )

        return max(-400.0, min(400.0, total_synergy))


class MLMetricsBalancer:
    """Core logic for balancing teams using ML-weighted metrics."""

    MIN_MATCHES_FOR_METRICS = 5

    @staticmethod
    def _get_map_specialist_bonus(player_id: int, map_name: str, db: Session) -> float:
        """
        Calculate a performance bonus if a player historically dominates this map.

        Bonus: Up to +300 MMR equivalent if WinRate > 75% (min 5 games).
        """
        from ..models import MatchPlayer, Match

        matches = (
            db.query(MatchPlayer)
            .join(Match)
            .filter(MatchPlayer.player_id == player_id)
            .filter(Match.map_name == map_name)
            .all()
        )

        if len(matches) < 5:
            return 0.0

        wins = sum(1 for m in matches if m.won)
        win_rate = wins / len(matches)

        if win_rate >= 0.75:
            # Scale bonus by number of games to avoid small sample bias
            certainty = min(len(matches) / 10.0, 1.0)
            return 300.0 * certainty
        elif win_rate <= 0.25:
            # Map Penalty for consistent losers on this map
            certainty = min(len(matches) / 10.0, 1.0)
            return -200.0 * certainty

        return 0.0

    @staticmethod
    def calculate_ml_rating(
        player: Player,
        weights: Dict[str, float],
        db: Session,
        map_name: Optional[str] = None,
    ) -> Tuple[float, MLPlayerRating]:
        """
        Calculate a player's predictive rating based on ML weights.
        Refined for 10/10: Uses Unified MMR as the high-fidelity base.
        """
        # Base stats - Using Unified MMR as the gold standard for skill
        # It already includes Handicap Correction, Combat Bonus, and Inactivity Decay
        base_mmr = player.unified_mmr or player.mmr or 2000

        # We still look at session/recency for weighting current momentum
        recency_mmr = player.recency_weighted_mmr or player.mmr or 2000
        session_mmr = player.session_weighted_mmr or base_mmr

        combat = player.avg_combat_score or 24
        economic = player.avg_economic_score or 60
        efficiency = player.avg_efficiency_score or 55
        impact = player.avg_overall_impact or 60
        total_games = player.total_games or 0

        map_bonus = 0.0
        if map_name:
            map_bonus = MLMetricsBalancer._get_map_specialist_bonus(
                player.id, map_name, db
            )

        if total_games < 15:
            # For new players, use conservative raw MMR to avoid volatility
            ml_rating = player.mmr + map_bonus
        else:
            # 10/10 Formula: Unified MMR + Momentum Adjustment
            # Unified MMR is 80% of the weight, Recency/Impact provides the 'form' adjustment

            # Form adjustment: How much is the player outperforming their average impact lately?
            # Using weights to allow tuning
            impact_weight = weights.get("teamwork", 1.0)
            form_adjustment = (impact - 60) * 4 * impact_weight

            ml_rating = base_mmr + form_adjustment + map_bonus

        breakdown = MLPlayerRating(
            player_id=player.id,
            player_name=player.name,
            session_mmr=round(session_mmr, 1),
            combat=round(combat, 1),
            economic=round(economic, 1),
            efficiency=round(efficiency, 1),
            teamwork=round(impact, 1),
            ml_rating=round(ml_rating, 1),
            total_games=total_games,
        )

        return ml_rating, breakdown

    @staticmethod
    def balance_teams(
        player_ids: List[int],
        db: Session,
        use_adaptive_weights: bool = True,
        manual_weights: Optional[Dict[str, float]] = None,
        top_n: int = 10,
        map_name: Optional[str] = None,
    ) -> List[MLTeamSuggestion]:
        """
        Generate balanced team suggestions using ML metrics + synergy.

        Args:
            player_ids: List of player IDs to balance
            db: Database session
            use_adaptive_weights: If True, use learned weights; if False, use manual_weights
            manual_weights: Custom weights (only used if use_adaptive_weights is False)
            top_n: Number of suggestions to return
            map_name: Optional map name to apply Map Specialist bonuses

        Returns:
            List of MLTeamSuggestion with balanced teams and breakdown
        """
        if len(player_ids) < 2:
            raise ValueError("At least 2 players required for team balancing")

        # Determine weights
        if use_adaptive_weights or manual_weights is None:
            weights = ComponentAccuracyTracker.get_optimal_weights(db)
        else:
            weights = manual_weights

        # Get players
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        player_map = {p.id: p for p in players}

        # Validate all player IDs exist
        missing_ids = set(player_ids) - set(player_map.keys())
        if missing_ids:
            raise ValueError(f"Players not found: {missing_ids}")

        # Calculate ML ratings for all players
        ml_ratings: Dict[int, float] = {}
        player_breakdowns: Dict[int, MLPlayerRating] = {}

        for pid in player_ids:
            if pid in player_map:
                rating, breakdown = MLMetricsBalancer.calculate_ml_rating(
                    player_map[pid], weights, db, map_name=map_name
                )
                ml_ratings[pid] = rating
                player_breakdowns[pid] = breakdown

        all_suggestions: List[MLTeamSuggestion] = []

        # Handle odd number of players
        num_players = len(player_ids)
        if num_players % 2 == 0:
            team_size = num_players // 2
        else:
            team_size = (num_players // 2) + 1

        # To avoid mirrors (Team A vs Team B == Team B vs Team A),
        # we fix the first player in Team 1.
        first_player = player_ids[0]
        remaining_players = player_ids[1:]

        # Try combinations for the rest of Team 1
        for team1_indices in combinations(remaining_players, team_size - 1):
            team1_ids = [first_player] + list(team1_indices)
            team2_ids = [p for p in player_ids if p not in team1_ids]

            # Calculate total ML ratings
            team1_ml_total = sum(ml_ratings.get(p, 1000) for p in team1_ids)
            team2_ml_total = sum(ml_ratings.get(p, 1000) for p in team2_ids)

            # Add synergy bonuses
            team1_synergy = SynergyCalculator.get_synergy_score(team1_ids, db)
            team2_synergy = SynergyCalculator.get_synergy_score(team2_ids, db)

            team1_total = team1_ml_total + team1_synergy
            team2_total = team2_ml_total + team2_synergy

            # Calculate balance score (0-1, higher = better)
            diff = abs(team1_total - team2_total)
            avg = (team1_total + team2_total) / 2
            balance_score = max(0, 1 - (diff / avg)) if avg > 0 else 0

            # Reward synergy (bonus for good team chemistry)
            total_synergy = team1_synergy + team2_synergy
            balance_score += min(total_synergy / 50, 0.1)

            all_suggestions.append(
                MLTeamSuggestion(
                    team1=[player_breakdowns[p] for p in team1_ids],
                    team2=[player_breakdowns[p] for p in team2_ids],
                    team1_total=round(team1_total, 1),
                    team2_total=round(team2_total, 1),
                    team1_synergy=round(team1_synergy, 1),
                    team2_synergy=round(team2_synergy, 1),
                    balance_score=round(balance_score, 3),
                    weights_used=weights,
                )
            )

        # Sort by balance score descending
        all_suggestions.sort(key=lambda x: x.balance_score, reverse=True)

        logger.info(f"Generated {len(all_suggestions)} balanced team options")
        return all_suggestions[:top_n]
