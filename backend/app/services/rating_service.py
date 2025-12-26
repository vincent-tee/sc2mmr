"""
Rating Service for SC2 MMR Tracker.

This service handles all rating-related business logic including:
- Full rating recalculation from match history
- TrueSkill algorithm application
- Performance-based adjustments
- Recency bias calculations

Extracted from players.py as part of SPEC-REFACTOR-001.

Design Principles:
- No method exceeds 50 lines
- Uses custom exceptions from app.exceptions
- Uses centralized settings from app.config
- Integrates with existing RatingSystem class
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import trueskill
from sqlalchemy.orm import Session

from ..config import settings
from ..exceptions import RatingCalculationError, PlayerNotFoundError
from ..models import Match, MatchPlayer, Player, PlayerMatchMetrics
from ..performance_rating import PerformanceRatingAdjuster
from ..rating_system import RatingSystem


@dataclass
class RecalculationStats:
    """
    Statistics from a full rating recalculation.

    Provides detailed metrics about the recalculation process,
    useful for monitoring and debugging.
    """

    total_players: int = 0
    total_matches: int = 0
    processing_time_ms: float = 0.0
    players_updated: int = 0
    matches_processed: int = 0
    matches_with_performance_adjustments: int = 0
    matches_without_metrics: int = 0
    avg_performance_multiplier: float = 1.0
    min_performance_multiplier: float = 1.0
    max_performance_multiplier: float = 1.0
    total_adjustments_applied: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "total_players": self.total_players,
            "total_matches": self.total_matches,
            "processing_time_ms": round(self.processing_time_ms, 2),
            "players_updated": self.players_updated,
            "matches_processed": self.matches_processed,
            "matches_with_performance_adjustments": self.matches_with_performance_adjustments,
            "matches_without_metrics": self.matches_without_metrics,
            "avg_performance_multiplier": round(self.avg_performance_multiplier, 3),
            "min_performance_multiplier": round(self.min_performance_multiplier, 3),
            "max_performance_multiplier": round(self.max_performance_multiplier, 3),
            "total_adjustments_applied": self.total_adjustments_applied,
        }


@dataclass
class MatchProcessingContext:
    """Context object for processing a single match during recalculation."""

    match: Match
    match_index: int
    total_matches: int
    player_ratings: Dict[int, trueskill.Rating]
    all_multipliers: List[float] = field(default_factory=list)
    adjustments_applied: int = 0


class RatingService:
    """
    Service for managing player ratings and recalculations.

    Handles the complete rating lifecycle:
    - Resetting ratings to defaults
    - Processing matches chronologically
    - Applying TrueSkill updates
    - Integrating performance adjustments
    - Managing recency bias

    Example:
        service = RatingService(db)
        stats = service.recalculate_all_ratings()
    """

    # Default TrueSkill values from settings
    DEFAULT_MU = settings.trueskill_mu
    DEFAULT_SIGMA = settings.trueskill_sigma

    def __init__(self, db: Session):
        """
        Initialize the rating service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def recalculate_all_ratings(self) -> RecalculationStats:
        """
        Recalculate all player ratings from scratch.

        This method:
        1. Resets all player ratings to default values
        2. Processes each match chronologically
        3. Applies TrueSkill + performance adjustments
        4. Updates player statistics

        Returns:
            RecalculationStats with processing information

        Raises:
            RatingCalculationError: If calculation fails critically
        """
        start_time = time.time()

        try:
            # Get all players and matches
            all_players = self.db.query(Player).all()
            all_matches = self.db.query(Match).order_by(Match.played_at.asc()).all()

            # Reset all players to defaults
            player_ratings = self._reset_all_players(all_players)
            self.db.commit()

            # Process all matches
            stats = self._process_all_matches(
                all_matches, player_ratings, all_players
            )

            # Calculate processing time
            stats.processing_time_ms = (time.time() - start_time) * 1000
            stats.total_players = len(all_players)
            stats.total_matches = len(all_matches)

            return stats

        except Exception as e:
            self.db.rollback()
            raise RatingCalculationError(
                message="Failed to recalculate ratings",
                detail=str(e)
            )

    def _reset_all_players(
        self, players: List[Player]
    ) -> Dict[int, trueskill.Rating]:
        """
        Reset all players to default rating values.

        Args:
            players: List of Player objects to reset

        Returns:
            Dictionary mapping player_id to TrueSkill Rating
        """
        player_ratings = {}

        for player in players:
            player.mu = self.DEFAULT_MU
            player.sigma = self.DEFAULT_SIGMA
            player.wins = 0
            player.losses = 0
            player.total_games = 0
            player.last_played = None
            player.terran_games = 0
            player.protoss_games = 0
            player.zerg_games = 0
            player.random_games = 0

            player_ratings[player.id] = trueskill.Rating(
                mu=self.DEFAULT_MU, sigma=self.DEFAULT_SIGMA
            )

        return player_ratings

    def _process_all_matches(
        self,
        matches: List[Match],
        player_ratings: Dict[int, trueskill.Rating],
        all_players: List[Player]
    ) -> RecalculationStats:
        """
        Process all matches chronologically to update ratings.

        Args:
            matches: List of matches ordered by played_at
            player_ratings: Current player ratings dictionary
            all_players: List of all Player objects

        Returns:
            RecalculationStats with processing statistics
        """
        stats = RecalculationStats()
        players_updated: Set[int] = set()
        all_multipliers: List[float] = []
        total_matches = len(matches)

        for match_index, match in enumerate(matches):
            result = self._process_single_match(
                match, match_index, total_matches, player_ratings
            )
            if result is not None:
                self._aggregate_match_result(
                    result, stats, players_updated, all_multipliers
                )

            if stats.matches_processed % 50 == 0:
                self.db.commit()

        self.db.commit()
        self._update_final_player_ratings(all_players, player_ratings)
        self.db.commit()

        self._calculate_final_statistics(stats, players_updated, all_multipliers)
        return stats

    def _aggregate_match_result(
        self,
        result: Dict,
        stats: RecalculationStats,
        players_updated: Set[int],
        all_multipliers: List[float]
    ) -> None:
        """
        Aggregate a single match result into overall statistics.

        Args:
            result: Match processing result
            stats: RecalculationStats to update
            players_updated: Set of updated player IDs
            all_multipliers: List of all multipliers
        """
        players_updated.update(result["players_updated"])
        all_multipliers.extend(result["multipliers"])
        stats.total_adjustments_applied += result["adjustments_applied"]
        stats.matches_processed += 1

        if result["has_metrics"]:
            stats.matches_with_performance_adjustments += 1
        else:
            stats.matches_without_metrics += 1

    def _calculate_final_statistics(
        self,
        stats: RecalculationStats,
        players_updated: Set[int],
        all_multipliers: List[float]
    ) -> None:
        """
        Calculate final aggregate statistics.

        Args:
            stats: RecalculationStats to finalize
            players_updated: Set of updated player IDs
            all_multipliers: List of all multipliers
        """
        stats.players_updated = len(players_updated)
        if all_multipliers:
            stats.avg_performance_multiplier = sum(all_multipliers) / len(all_multipliers)
            stats.min_performance_multiplier = min(all_multipliers)
            stats.max_performance_multiplier = max(all_multipliers)
        else:
            stats.avg_performance_multiplier = 1.0
            stats.min_performance_multiplier = 1.0
            stats.max_performance_multiplier = 1.0

    def _process_single_match(
        self,
        match: Match,
        match_index: int,
        total_matches: int,
        player_ratings: Dict[int, trueskill.Rating]
    ) -> Optional[Dict]:
        """Process a single match and update ratings."""
        match_players = self._get_match_players(match.id)
        if not match_players:
            return None

        teams = self._group_by_team(match_players)
        if not teams:
            return None

        team_1_mps, team_2_mps = teams
        new_ratings = self._calculate_trueskill_update(
            team_1_mps, team_2_mps, player_ratings
        )

        players_updated = self._update_match_player_ratings(
            team_1_mps, team_2_mps,
            new_ratings["team_1"], new_ratings["team_2"],
            player_ratings
        )

        perf_result = self._apply_performance_adjustments(
            match, match_index, total_matches, match_players, player_ratings
        )
        self._update_player_statistics(match, match_players)

        return {
            "players_updated": players_updated,
            "multipliers": perf_result["multipliers"],
            "adjustments_applied": perf_result["adjustments_applied"],
            "has_metrics": perf_result["has_metrics"]
        }

    def _get_match_players(self, match_id: int) -> List[MatchPlayer]:
        """Get all MatchPlayer records for a match."""
        return self.db.query(MatchPlayer).filter(
            MatchPlayer.match_id == match_id
        ).all()

    def _group_by_team(
        self, match_players: List[MatchPlayer]
    ) -> Optional[Tuple[List[MatchPlayer], List[MatchPlayer]]]:
        """Group match players by team. Returns None if invalid."""
        team_1 = [mp for mp in match_players if mp.team_number == 1]
        team_2 = [mp for mp in match_players if mp.team_number == 2]
        if not team_1 or not team_2:
            return None
        return (team_1, team_2)

    def _calculate_trueskill_update(
        self,
        team_1_mps: List[MatchPlayer],
        team_2_mps: List[MatchPlayer],
        player_ratings: Dict[int, trueskill.Rating]
    ) -> Dict[str, List[trueskill.Rating]]:
        """
        Calculate new TrueSkill ratings for a match.

        Args:
            team_1_mps: Team 1 MatchPlayer records
            team_2_mps: Team 2 MatchPlayer records
            player_ratings: Current ratings dictionary

        Returns:
            Dictionary with new ratings for each team
        """
        team_1_ratings = [player_ratings[mp.player_id] for mp in team_1_mps]
        team_2_ratings = [player_ratings[mp.player_id] for mp in team_2_mps]

        # Determine winner
        team_1_won = team_1_mps[0].won == 1

        if team_1_won:
            new_team_1, new_team_2 = trueskill.rate(
                [team_1_ratings, team_2_ratings],
                ranks=[0, 1]
            )
        else:
            new_team_1, new_team_2 = trueskill.rate(
                [team_1_ratings, team_2_ratings],
                ranks=[1, 0]
            )

        return {"team_1": new_team_1, "team_2": new_team_2}

    def _update_match_player_ratings(
        self,
        team_1_mps: List[MatchPlayer],
        team_2_mps: List[MatchPlayer],
        new_team_1_ratings: List[trueskill.Rating],
        new_team_2_ratings: List[trueskill.Rating],
        player_ratings: Dict[int, trueskill.Rating]
    ) -> Set[int]:
        """
        Update MatchPlayer records with before/after ratings.

        Args:
            team_1_mps: Team 1 MatchPlayer records
            team_2_mps: Team 2 MatchPlayer records
            new_team_1_ratings: New ratings for team 1
            new_team_2_ratings: New ratings for team 2
            player_ratings: Current ratings dictionary

        Returns:
            Set of player IDs that were updated
        """
        players_updated = set()

        for i, mp in enumerate(team_1_mps):
            old_rating = player_ratings[mp.player_id]
            new_rating = new_team_1_ratings[i]

            mp.mu_before = old_rating.mu
            mp.sigma_before = old_rating.sigma
            mp.mu_after = new_rating.mu
            mp.sigma_after = new_rating.sigma

            players_updated.add(mp.player_id)

        for i, mp in enumerate(team_2_mps):
            old_rating = player_ratings[mp.player_id]
            new_rating = new_team_2_ratings[i]

            mp.mu_before = old_rating.mu
            mp.sigma_before = old_rating.sigma
            mp.mu_after = new_rating.mu
            mp.sigma_after = new_rating.sigma

            players_updated.add(mp.player_id)

        return players_updated

    def _apply_performance_adjustments(
        self,
        match: Match,
        match_index: int,
        total_matches: int,
        match_players: List[MatchPlayer],
        player_ratings: Dict[int, trueskill.Rating]
    ) -> Dict:
        """Apply performance-based adjustments with recency bias."""
        result = {"multipliers": [], "adjustments_applied": 0, "has_metrics": False}
        player_metrics_map = self._fetch_match_metrics(match_players)
        result["has_metrics"] = len(player_metrics_map) > 0

        team_metrics = self._build_team_metrics(match_players, player_metrics_map)

        for mp in match_players:
            adjustment = self._apply_single_player_adjustment(
                mp, match.id, match_index, total_matches,
                player_metrics_map, team_metrics, player_ratings
            )
            if adjustment is not None:
                result["multipliers"].append(adjustment)
                result["adjustments_applied"] += 1
            else:
                player_ratings[mp.player_id] = trueskill.Rating(
                    mu=mp.mu_after, sigma=mp.sigma_after
                )
        return result

    def _fetch_match_metrics(
        self, match_players: List[MatchPlayer]
    ) -> Dict[int, PlayerMatchMetrics]:
        """Fetch all metrics for match players in one query."""
        match_player_ids = [mp.id for mp in match_players]
        metrics_list = self.db.query(PlayerMatchMetrics).filter(
            PlayerMatchMetrics.match_player_id.in_(match_player_ids)
        ).all()
        return {m.match_player_id: m for m in metrics_list}

    def _build_team_metrics(
        self,
        match_players: List[MatchPlayer],
        metrics_map: Dict[int, PlayerMatchMetrics]
    ) -> Dict[int, List[PlayerMatchMetrics]]:
        """Build team metrics mapping for performance calculations."""
        team_1_mps = [mp for mp in match_players if mp.team_number == 1]
        team_2_mps = [mp for mp in match_players if mp.team_number == 2]
        team_1_metrics = [metrics_map[mp.id] for mp in team_1_mps if mp.id in metrics_map]
        team_2_metrics = [metrics_map[mp.id] for mp in team_2_mps if mp.id in metrics_map]
        return {1: team_1_metrics, 2: team_2_metrics}

    def _apply_single_player_adjustment(
        self,
        mp: MatchPlayer,
        match_id: int,
        match_index: int,
        total_matches: int,
        player_metrics_map: Dict[int, PlayerMatchMetrics],
        team_metrics: Dict[int, List[PlayerMatchMetrics]],
        player_ratings: Dict[int, trueskill.Rating]
    ) -> Optional[float]:
        """Apply performance adjustment for a single player."""
        if mp.id not in player_metrics_map:
            return None

        metrics = player_metrics_map[mp.id]
        my_team = team_metrics[mp.team_number]
        opponent_team = team_metrics[3 - mp.team_number]  # 1->2 or 2->1

        base_multiplier = PerformanceRatingAdjuster.calculate_performance_multiplier(
            metrics, my_team, opponent_team, bool(mp.won)
        )

        recency_weight = self._calculate_recency_weight(match_index, total_matches)
        multiplier = 1.0 + (base_multiplier - 1.0) * recency_weight

        self._validate_multiplier(multiplier, mp.player_id, match_id)

        base_mu_change = mp.mu_after - mp.mu_before
        adjusted_mu_after = mp.mu_before + (base_mu_change * multiplier)

        self._validate_rating_change(base_mu_change, mp.player_id, match_id)

        mp.mu_after = adjusted_mu_after
        player_ratings[mp.player_id] = trueskill.Rating(
            mu=adjusted_mu_after, sigma=mp.sigma_after
        )

        return multiplier

    def _calculate_recency_weight(
        self, match_index: int, total_matches: int
    ) -> float:
        """
        Calculate recency weight for performance adjustments.

        Recent matches have stronger performance impact.
        Weight ranges from 0.3 (oldest) to 1.0 (newest).

        Args:
            match_index: Current match index
            total_matches: Total number of matches

        Returns:
            Recency weight between 0.3 and 1.0
        """
        if total_matches <= 1:
            return 1.0
        return 0.3 + 0.7 * (match_index / (total_matches - 1))

    def _validate_multiplier(
        self, multiplier: float, player_id: int, match_id: int
    ) -> None:
        """
        Validate that multiplier is within expected bounds.

        Args:
            multiplier: The calculated multiplier
            player_id: Player ID for logging
            match_id: Match ID for logging
        """
        if multiplier < 0.5 or multiplier > 1.5:
            print(
                f"WARNING: Multiplier {multiplier} outside expected bounds "
                f"for player {player_id} in match {match_id}"
            )

    def _validate_rating_change(
        self, base_mu_change: float, player_id: int, match_id: int
    ) -> None:
        """
        Validate that rating change is reasonable.

        Args:
            base_mu_change: The TrueSkill mu change
            player_id: Player ID for logging
            match_id: Match ID for logging
        """
        if abs(base_mu_change) > 10:
            print(
                f"INFO: Large TrueSkill change {base_mu_change:.2f} "
                f"for player {player_id} in match {match_id}"
            )

    def _update_player_statistics(
        self, match: Match, match_players: List[MatchPlayer]
    ) -> None:
        """
        Update player statistics after processing a match.

        Args:
            match: The processed match
            match_players: All MatchPlayer records for this match
        """
        for mp in match_players:
            player = self.db.query(Player).filter(
                Player.id == mp.player_id
            ).first()

            if not player:
                continue

            player.total_games += 1
            if mp.won:
                player.wins += 1
            else:
                player.losses += 1
            player.last_played = match.played_at

            # Update race statistics
            self._update_race_stats(player, mp.race.value)

    def _update_race_stats(self, player: Player, race: str) -> None:
        """
        Update player's race statistics.

        Args:
            player: Player to update
            race: Race played in the match
        """
        race_attr_map = {
            "Terran": "terran_games",
            "Protoss": "protoss_games",
            "Zerg": "zerg_games",
            "Random": "random_games"
        }

        attr_name = race_attr_map.get(race)
        if attr_name:
            current = getattr(player, attr_name, 0)
            setattr(player, attr_name, current + 1)

    def _update_final_player_ratings(
        self,
        players: List[Player],
        player_ratings: Dict[int, trueskill.Rating]
    ) -> None:
        """
        Update all player objects with their final ratings.

        Args:
            players: List of Player objects
            player_ratings: Final ratings dictionary
        """
        for player in players:
            if player.id in player_ratings:
                final_rating = player_ratings[player.id]
                player.mu = final_rating.mu
                player.sigma = final_rating.sigma

    def calculate_win_probability(
        self,
        team1_player_ids: List[int],
        team2_player_ids: List[int]
    ) -> Tuple[float, float]:
        """
        Calculate win probability for two teams.

        Args:
            team1_player_ids: List of player IDs on team 1
            team2_player_ids: List of player IDs on team 2

        Returns:
            Tuple of (team1_win_prob, team2_win_prob)

        Raises:
            PlayerNotFoundError: If any player is not found
        """
        team1_ratings = []
        team2_ratings = []

        for player_id in team1_player_ids:
            player = self.db.query(Player).filter(
                Player.id == player_id
            ).first()
            if not player:
                raise PlayerNotFoundError(player_id=player_id)
            team1_ratings.append(
                trueskill.Rating(mu=player.mu, sigma=player.sigma)
            )

        for player_id in team2_player_ids:
            player = self.db.query(Player).filter(
                Player.id == player_id
            ).first()
            if not player:
                raise PlayerNotFoundError(player_id=player_id)
            team2_ratings.append(
                trueskill.Rating(mu=player.mu, sigma=player.sigma)
            )

        return RatingSystem.calculate_win_probability(
            team1_ratings, team2_ratings
        )

    def apply_decay(self, player_id: int, days_inactive: int) -> Player:
        """
        Apply skill decay to an inactive player.

        Args:
            player_id: Player ID to apply decay to
            days_inactive: Number of days since last game

        Returns:
            Updated Player object

        Raises:
            PlayerNotFoundError: If player not found
        """
        player = self.db.query(Player).filter(
            Player.id == player_id
        ).first()

        if not player:
            raise PlayerNotFoundError(player_id=player_id)

        RatingSystem.apply_skill_decay(player, days_inactive)
        self.db.commit()

        return player

    def calculate_player_rating(
        self, player_id: int
    ) -> Tuple[float, float, float]:
        """
        Get current rating for a single player.

        Args:
            player_id: Player ID to look up

        Returns:
            Tuple of (mu, sigma, display_mmr)

        Raises:
            PlayerNotFoundError: If player not found
        """
        player = self.db.query(Player).filter(
            Player.id == player_id
        ).first()

        if not player:
            raise PlayerNotFoundError(player_id=player_id)

        return (player.mu, player.sigma, player.mmr)

    def apply_trueskill_update(
        self,
        team1_ratings: List[trueskill.Rating],
        team2_ratings: List[trueskill.Rating],
        team1_won: bool
    ) -> Tuple[List[trueskill.Rating], List[trueskill.Rating]]:
        """
        Apply TrueSkill algorithm to calculate new ratings.

        This is a pure function wrapper around trueskill.rate().

        Args:
            team1_ratings: Current ratings for team 1
            team2_ratings: Current ratings for team 2
            team1_won: True if team 1 won the match

        Returns:
            Tuple of (new_team1_ratings, new_team2_ratings)
        """
        ranks = [0, 1] if team1_won else [1, 0]

        new_team_1, new_team_2 = trueskill.rate(
            [team1_ratings, team2_ratings],
            ranks=ranks
        )

        return new_team_1, new_team_2

    def get_player_ratings_by_ids(
        self, player_ids: List[int]
    ) -> Dict[int, trueskill.Rating]:
        """
        Get TrueSkill ratings for multiple players.

        Args:
            player_ids: List of player IDs

        Returns:
            Dictionary mapping player_id to TrueSkill Rating

        Raises:
            PlayerNotFoundError: If any player not found
        """
        ratings = {}

        for player_id in player_ids:
            player = self.db.query(Player).filter(
                Player.id == player_id
            ).first()

            if not player:
                raise PlayerNotFoundError(player_id=player_id)

            ratings[player_id] = trueskill.Rating(
                mu=player.mu, sigma=player.sigma
            )

        return ratings

    def update_recency_weighted_mmr(self, player_id: int) -> float:
        """
        Update recency-weighted MMR for a player.

        Args:
            player_id: Player ID to update

        Returns:
            New recency-weighted MMR value

        Raises:
            PlayerNotFoundError: If player not found
        """
        player = self.db.query(Player).filter(
            Player.id == player_id
        ).first()

        if not player:
            raise PlayerNotFoundError(player_id=player_id)

        RatingSystem.update_recency_weighted_rating(self.db, player)

        return player.recency_weighted_mmr or player.mmr
