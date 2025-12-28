"""
Match Service for SC2 MMR Tracker.

This service handles all match-related business logic including:
- Match CRUD operations (get, delete)
- Manual winner determination for failed uploads
- Match history queries with filtering
- Match statistics and analysis

Extracted from replays.py as part of SPEC-REFACTOR-001.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

# Absolute imports based on project pattern
from app.exceptions import (  # type: ignore
    DuplicateReplayError,
    MatchNotFoundError,
    ValidationError,
)
from app.models import (  # type: ignore
    FailedUpload,
    Match,
    MatchPlayer,
    Player,
    PlayerMatchMetrics,
)
from app.rating_system import RatingSystem  # type: ignore
from app.services.match_orchestrator import MatchOrchestrator  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class MatchPlayerData:
    """Data class for match player information."""

    player_id: int
    player_name: str
    team_number: int
    race: str
    won: bool
    mmr_before: float
    mmr_after: float
    mmr_change: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team_number": self.team_number,
            "race": self.race,
            "won": self.won,
            "mmr_before": round(self.mmr_before, 1),
            "mmr_after": round(self.mmr_after, 1),
            "mmr_change": round(self.mmr_change, 1),
        }


@dataclass
class MatchDetails:
    """Detailed match information including players."""

    match_id: int
    played_at: str
    game_mode: str
    map_name: str
    duration_seconds: int
    replay_hash: str
    predicted_team1_win_prob: Optional[float]
    predicted_team2_win_prob: Optional[float]
    players: List[MatchPlayerData]

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "match_id": self.match_id,
            "played_at": self.played_at,
            "game_mode": self.game_mode,
            "map_name": self.map_name,
            "duration_seconds": self.duration_seconds,
            "replay_hash": self.replay_hash,
            "predicted_team1_win_prob": self.predicted_team1_win_prob,
            "predicted_team2_win_prob": self.predicted_team2_win_prob,
            "players": [p.to_dict() for p in self.players],
        }


@dataclass
class MatchStatistics:
    """Statistical analysis of a match."""

    match_id: int
    team1_total_damage: int
    team2_total_damage: int
    team1_total_resources: int
    team2_total_resources: int
    team1_avg_impact: float
    team2_avg_impact: float
    mvp_player_id: Optional[int]
    mvp_player_name: Optional[str]
    mvp_impact_score: float
    balance_score: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "match_id": self.match_id,
            "team1_total_damage": self.team1_total_damage,
            "team2_total_damage": self.team2_total_damage,
            "team1_total_resources": self.team1_total_resources,
            "team2_total_resources": self.team2_total_resources,
            "team1_avg_impact": round(self.team1_avg_impact, 2),
            "team2_avg_impact": round(self.team2_avg_impact, 2),
            "mvp_player_id": self.mvp_player_id,
            "mvp_player_name": self.mvp_player_name,
            "mvp_impact_score": round(self.mvp_impact_score, 2),
            "balance_score": round(self.balance_score, 1),
        }


@dataclass
class ManualWinnerResult:
    """Result of manual winner determination."""

    match_id: int
    map_name: str
    game_mode: str
    played_at: str
    duration_seconds: int
    num_players: int
    message: str
    parse_time_ms: float
    validation_time_ms: float
    duplicate_check_time_ms: float
    rating_update_time_ms: float
    total_time_ms: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "match_id": self.match_id,
            "map_name": self.map_name,
            "game_mode": self.game_mode,
            "played_at": self.played_at,
            "duration_seconds": self.duration_seconds,
            "num_players": self.num_players,
            "message": self.message,
            "processing_stats": {
                "parse_time_ms": round(self.parse_time_ms, 2),
                "validation_time_ms": round(self.validation_time_ms, 2),
                "duplicate_check_time_ms": round(self.duplicate_check_time_ms, 2),
                "rating_update_time_ms": round(self.rating_update_time_ms, 2),
                "total_time_ms": round(self.total_time_ms, 2),
            },
        }


class MatchService:
    """
    Service for managing match operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_match_details(self, match_id: int) -> MatchDetails:
        """Get detailed information about a specific match."""
        match = self._get_match_or_raise(match_id)
        players = self._get_match_players_with_details(match_id)

        return MatchDetails(
            match_id=match.id,
            played_at=match.played_at.isoformat(),
            game_mode=match.game_mode.value,
            map_name=match.map_name,
            duration_seconds=match.duration_seconds,
            replay_hash=match.replay_hash or "",
            predicted_team1_win_prob=match.predicted_team1_win_prob,
            predicted_team2_win_prob=match.predicted_team2_win_prob,
            players=players,
        )

    def get_match_history(
        self,
        limit: int = 50,
        offset: int = 0,
        player_id: Optional[int] = None,
    ) -> Tuple[List[Dict], int]:
        """Query match history with pagination and optional filtering."""
        query = self.db.query(Match)

        if player_id is not None:
            query = self._filter_by_player(query, player_id)

        total_count = query.count()
        matches = (
            query.order_by(Match.played_at.desc()).limit(limit).offset(offset).all()
        )

        match_list = [self._format_match_summary(m) for m in matches]
        return match_list, total_count

    def _filter_by_player(self, query, player_id: int):
        """Filter matches by player participation."""
        match_ids = (
            select(MatchPlayer.match_id)
            .where(MatchPlayer.player_id == player_id)
            .scalar_subquery()
        )
        return query.filter(Match.id.in_(match_ids))

    def _format_match_summary(self, match: Match) -> Dict:
        """Format match for list response."""
        return {
            "id": match.id,
            "played_at": match.played_at.isoformat(),
            "game_mode": match.game_mode.value,
            "map_name": match.map_name,
            "duration_seconds": match.duration_seconds,
            "replay_hash": match.replay_hash or "",
        }

    def delete_match(self, match_id: int, recalculate: bool = True) -> Dict:
        """Delete a match and optionally recalculate ratings."""
        match = self._get_match_or_raise(match_id)
        player_ids = self._delete_match_records(match)

        if recalculate:
            self._trigger_rating_recalculation()

        return {
            "deleted_match_id": match_id,
            "affected_player_ids": player_ids,
            "recalculation_triggered": recalculate,
        }

    def _delete_match_records(self, match: Match) -> List[int]:
        """Delete match and related records, return affected player IDs."""
        match_players = (
            self.db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )
        player_ids = [mp.player_id for mp in match_players]

        # Delete metrics first (cascades should handle this, but being explicit)
        for mp in match_players:
            self.db.query(PlayerMatchMetrics).filter(
                PlayerMatchMetrics.match_player_id == mp.id
            ).delete()

        # Delete match players
        self.db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).delete()

        # Delete match
        self.db.delete(match)
        self.db.commit()

        return player_ids

    def _trigger_rating_recalculation(self) -> None:
        """Trigger full rating recalculation via RatingService."""
        from app.services.rating_service import RatingService  # type: ignore

        rating_service = RatingService(self.db)
        rating_service.recalculate_all_ratings()

    def get_match_statistics(self, match_id: int) -> MatchStatistics:
        """Get statistical analysis of a match."""
        self._get_match_or_raise(match_id)
        team_stats = self._calculate_team_statistics(match_id)
        mvp_info = self._find_mvp(match_id)
        balance = self._calculate_balance_score(team_stats)

        return MatchStatistics(
            match_id=match_id,
            team1_total_damage=team_stats["team1"]["damage"],
            team2_total_damage=team_stats["team2"]["damage"],
            team1_total_resources=team_stats["team1"]["resources"],
            team2_total_resources=team_stats["team2"]["resources"],
            team1_avg_impact=team_stats["team1"]["avg_impact"],
            team2_avg_impact=team_stats["team2"]["avg_impact"],
            mvp_player_id=mvp_info["player_id"],
            mvp_player_name=mvp_info["player_name"],
            mvp_impact_score=mvp_info["impact_score"],
            balance_score=balance,
        )

    def _calculate_team_statistics(self, match_id: int) -> Dict:
        """Calculate aggregate statistics for each team."""
        match_players = (
            self.db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
        )

        team1 = {"damage": 0, "resources": 0, "impacts": []}
        team2 = {"damage": 0, "resources": 0, "impacts": []}

        for mp in match_players:
            metrics = (
                self.db.query(PlayerMatchMetrics)
                .filter(PlayerMatchMetrics.match_player_id == mp.id)
                .first()
            )

            target = team1 if mp.team_number == 1 else team2

            if metrics:
                target["damage"] += metrics.damage_dealt or 0
                target["resources"] += metrics.total_resources_collected or 0
                target["impacts"].append(metrics.overall_impact or 0)

        return {
            "team1": {
                "damage": team1["damage"],
                "resources": team1["resources"],
                "avg_impact": self._safe_average(team1["impacts"]),
            },
            "team2": {
                "damage": team2["damage"],
                "resources": team2["resources"],
                "avg_impact": self._safe_average(team2["impacts"]),
            },
        }

    def _safe_average(self, values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def _find_mvp(self, match_id: int) -> Dict:
        """Find the MVP (highest overall impact) of the match."""
        match_players = (
            self.db.query(MatchPlayer, PlayerMatchMetrics)
            .outerjoin(
                PlayerMatchMetrics, MatchPlayer.id == PlayerMatchMetrics.match_player_id
            )
            .filter(MatchPlayer.match_id == match_id)
            .all()
        )

        mvp_info: Dict[str, Any] = {
            "player_id": None,
            "player_name": None,
            "impact_score": 0.0,
        }

        for mp, metrics in match_players:
            if metrics and (metrics.overall_impact or 0) > mvp_info["impact_score"]:
                player = self.db.query(Player).filter(Player.id == mp.player_id).first()
                mvp_info = {
                    "player_id": mp.player_id,
                    "player_name": player.name if player else "Unknown",
                    "impact_score": metrics.overall_impact or 0,
                }

        return mvp_info

    def _calculate_balance_score(self, team_stats: Dict) -> float:
        damage_diff = abs(team_stats["team1"]["damage"] - team_stats["team2"]["damage"])
        total_damage = team_stats["team1"]["damage"] + team_stats["team2"]["damage"]

        if total_damage == 0:
            damage_balance = 100.0
        else:
            damage_balance = 100 * (1 - damage_diff / total_damage)

        impact_diff = abs(
            team_stats["team1"]["avg_impact"] - team_stats["team2"]["avg_impact"]
        )
        impact_balance = max(0, 100 - impact_diff)

        return 0.6 * damage_balance + 0.4 * impact_balance

    def set_manual_winner(
        self,
        upload_id: int,
        winner_team: int,
        reason: Optional[str] = None,
    ) -> ManualWinnerResult:
        """
        Manually specify winner for a failed replay and reprocess it.
        Delegates core logic to MatchOrchestrator.
        """
        self._validate_winner_team(winner_team)
        failed_upload = self._get_failed_upload_or_raise(upload_id)
        self._validate_replay_file_exists(failed_upload)

        path = failed_upload.replay_file_path
        if not path:
            raise ValidationError("Replay file path is missing")

        orchestrator = MatchOrchestrator(self.db)
        start_time = time.time()

        try:
            result = orchestrator.orchestrate_match(
                file_path=path,
                filename=failed_upload.filename,
                manual_winner_team=winner_team,
            )
            message = "Replay processed with manual winner determination"
        except DuplicateReplayError as e:
            if e.match_id is None:
                raise ValidationError("Duplicate replay detected but match ID missing")
            existing = self._get_match_or_raise(cast(int, e.match_id))
            players = (
                self.db.query(MatchPlayer)
                .filter(MatchPlayer.match_id == existing.id)
                .all()
            )
            self.db.delete(failed_upload)
            self.db.commit()

            return ManualWinnerResult(
                match_id=existing.id,
                map_name=existing.map_name,
                game_mode=existing.game_mode.value,
                played_at=existing.played_at.isoformat(),
                duration_seconds=existing.duration_seconds,
                num_players=len(players),
                message=f"Replay already processed as Match #{existing.id}",
                parse_time_ms=0,
                validation_time_ms=0,
                duplicate_check_time_ms=0,
                rating_update_time_ms=0,
                total_time_ms=(time.time() - start_time) * 1000,
            )

        self.db.delete(failed_upload)
        self.db.commit()

        return ManualWinnerResult(
            match_id=result.match.id,
            map_name=result.match.map_name,
            game_mode=result.match.game_mode.value,
            played_at=result.match.played_at.isoformat(),
            duration_seconds=result.match.duration_seconds,
            num_players=result.num_players,
            message=message,
            parse_time_ms=result.stats.parse_time_ms,
            validation_time_ms=result.stats.validation_time_ms,
            duplicate_check_time_ms=result.stats.duplicate_check_time_ms,
            rating_update_time_ms=result.stats.rating_update_time_ms,
            total_time_ms=result.stats.total_time_ms,
        )

    def _validate_winner_team(self, winner_team: int) -> None:
        if winner_team not in [1, 2]:
            raise ValidationError(
                message="Invalid winner team", detail="winner_team must be 1 or 2"
            )

    def _get_failed_upload_or_raise(self, upload_id: int) -> FailedUpload:
        failed_upload = (
            self.db.query(FailedUpload).filter(FailedUpload.id == upload_id).first()
        )
        if not failed_upload:
            raise MatchNotFoundError(upload_id)
        return failed_upload

    def _validate_replay_file_exists(self, failed_upload: FailedUpload) -> None:
        path = failed_upload.replay_file_path
        if not path:
            raise ValidationError(message="Replay file not found")
        if not os.path.exists(path):
            raise ValidationError(
                message="Replay file not found", detail=f"File missing at: {path}"
            )

    def _get_match_or_raise(self, match_id: int) -> Match:
        match = self.db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise MatchNotFoundError(match_id)
        return match

    def _get_match_players_with_details(self, match_id: int) -> List[MatchPlayerData]:
        match_players_with_player = (
            self.db.query(MatchPlayer, Player)
            .join(Player, MatchPlayer.player_id == Player.id)
            .filter(MatchPlayer.match_id == match_id)
            .all()
        )
        result = []
        for mp, player in match_players_with_player:
            mmr_before = RatingSystem.calculate_display_mmr(mp.mu_before)
            mmr_after = RatingSystem.calculate_display_mmr(mp.mu_after)
            result.append(
                MatchPlayerData(
                    player_id=player.id,
                    player_name=player.name,
                    team_number=mp.team_number,
                    race=mp.race.value,
                    won=bool(mp.won),
                    mmr_before=mmr_before,
                    mmr_after=mmr_after,
                    mmr_change=mmr_after - mmr_before,
                )
            )
        return result
