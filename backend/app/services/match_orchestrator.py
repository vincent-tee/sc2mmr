"""
MatchOrchestrator - Single Source of Truth for the match lifecycle.

This service orchestrates the entire pipeline for processing a match:
Duplicate Detection -> Unified Parsing -> DB Creation -> Rating Pipeline -> ML Extraction.

SPEC-ARCH-001 Implementation.

Type Issues:
- sc2reader and trueskill libraries lack type stubs.
- SQLAlchemy model attributes (e.g., build_order_json) require # type: ignore for assignment.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, cast

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models import Match, MatchPlayer, Player, PerformanceFeatures  # type: ignore
from app.impact_service import ImpactService  # type: ignore
from app.services.unified_parser import UnifiedParser  # type: ignore
from app.types.results import ProcessedMatchResult  # type: ignore

logger = logging.getLogger(__name__)

# Load player aliases from config
_PLAYER_ALIASES: Dict[str, str] = {}


def _load_player_aliases() -> Dict[str, str]:
    """Load player aliases from config file."""
    global _PLAYER_ALIASES
    if _PLAYER_ALIASES:
        return _PLAYER_ALIASES

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "player_aliases.json",
    )
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                _PLAYER_ALIASES = config.get("aliases", {})
                if _PLAYER_ALIASES:
                    logger.info(f"Loaded {len(_PLAYER_ALIASES)} player aliases")
    except Exception as e:
        logger.warning(f"Could not load player aliases: {e}")

    return _PLAYER_ALIASES


def resolve_player_name(name: str) -> str:
    """Resolve a player name through aliases to canonical name."""
    aliases = _load_player_aliases()
    canonical = aliases.get(name, name)
    if canonical != name:
        logger.info(f"Player alias resolved: '{name}' -> '{canonical}'")
    return canonical


@dataclass
class OrchestrationStats:
    """Statistics about the orchestration stages."""

    parse_time_ms: float
    validation_time_ms: float
    duplicate_check_time_ms: float
    rating_update_time_ms: float
    total_time_ms: float


@dataclass
class MatchOrchestrationResult:
    """Result of successful match orchestration."""

    match: Match
    num_players: int
    stats: OrchestrationStats
    message: str
    created: bool = True


from app.services.commandcenter_parser import (  # type: ignore
    get_commandcenter_parser,
    parse_replay_isolated,
)


class MatchOrchestrator:
    """
    Orchestrates the lifecycle of a match from replay to database.
    """

    def __init__(self, db: Session):
        self.db = db
        self.parser = UnifiedParser()
        self.cc_parser = get_commandcenter_parser()

    def orchestrate_match(
        self,
        file_path: str,
        filename: str,
        manual_winner_team: Optional[int] = None,
        use_advanced_parser: bool = True,
        use_cc_parser: bool = False,
        persist_replay: bool = False,
    ) -> MatchOrchestrationResult:
        """Execute the full match processing pipeline."""
        start_time = time.time()

        # 1. Unified Parsing (sc2reader based)
        parse_start = time.time()
        result = self.parser.parse(file_path, manual_winner_team=manual_winner_team)

        # 1b. Augmented Parsing (CommandCenter based)
        # Runs in an isolated child process with a hard timeout — the SC2
        # engine can hang indefinitely on connection failure instead of
        # returning, which would otherwise freeze this thread forever
        # (this pipeline runs on the replay-folder watcher's background
        # thread; a hang here stops all future replay ingestion).
        if use_cc_parser and self.cc_parser:
            try:
                num_players = len(result.players)
                cc_metrics = parse_replay_isolated(file_path, num_players=num_players)
                if cc_metrics:
                    self._augment_with_cc_metrics(result, cc_metrics)
                else:
                    logger.warning(
                        f"CommandCenter parsing produced no metrics for {file_path}; "
                        "falling back to sc2reader-based metrics"
                    )
            except Exception as e:
                logger.error(f"CommandCenter parsing failed: {e}")

        parse_time_ms = (time.time() - parse_start) * 1000

        from app.replay_parser import ReplayData, PlayerData
        from app.services.ingestion import ingest_match

        legacy_data = ReplayData(
            played_at=result.played_at, game_mode=result.game_mode,
            map_name=result.map_name, duration_seconds=result.duration_seconds,
            replay_hash=result.replay_hash, game_fingerprint=result.game_fingerprint or "",
            players=[PlayerData(name=resolve_player_name(p.name), race=p.race,
                                team=p.team, won=p.won) for p in result.players],
        )
        if persist_replay:
            from app.services import replay_storage

            with open(file_path, "rb") as replay_file:
                result.replay_file_path = replay_storage.save_replay(
                    replay_file.read(), result.replay_hash
                )
        rating_start = time.time()
        match, created = ingest_match(
            self.db, legacy_data, result.replay_file_path,
            save_metrics=lambda work, recorded: self.save_metrics_only(recorded, result, db=work),
            require_experience=False,
        )
        rating_update_time_ms = (time.time() - rating_start) * 1000
        duplicate_check_time_ms = 0.0
        if created:
            self._trigger_post_processing(match, result)

        total_time_ms = (time.time() - start_time) * 1000

        return MatchOrchestrationResult(
            match=match,
            num_players=len(result.players),
            stats=OrchestrationStats(
                parse_time_ms=round(parse_time_ms, 2),
                validation_time_ms=0.0,
                duplicate_check_time_ms=round(duplicate_check_time_ms, 2),
                rating_update_time_ms=round(rating_update_time_ms, 2),
                total_time_ms=round(total_time_ms, 2),
            ),
            message=f"Match {match.id} orchestrated successfully",
            created=created,
        )

    def _augment_with_cc_metrics(
        self, result: ProcessedMatchResult, cc_metrics: Dict[int, Any]
    ):
        """
        Update sc2reader results with high-fidelity CommandCenter metrics.

        CommandCenter uses player IDs 1-N where N is the number of players.
        sc2reader player order should match CommandCenter player order.
        """
        for idx, pr in enumerate(result.players):
            # CommandCenter uses 1-indexed player IDs matching the order in the replay
            cc_pid = idx + 1

            if cc_pid not in cc_metrics:
                logger.warning(f"No CC metrics for player {pr.name} (pid={cc_pid})")
                continue

            stats = cc_metrics[cc_pid]
            logger.info(f"Augmenting player {pr.name} (pid={cc_pid}) with CC metrics")

            # Economic metrics
            pr.minerals_collected = int(
                stats.get("collected_minerals", pr.minerals_collected)
            )
            pr.vespene_collected = int(
                stats.get("collected_vespene", pr.vespene_collected)
            )
            pr.total_resources_collected = pr.minerals_collected + pr.vespene_collected
            pr.resources_spent = int(
                stats.get("spent_minerals", 0) + stats.get("spent_vespene", 0)
            )

            # Spending efficiency
            if pr.total_resources_collected > 0:
                pr.spending_efficiency = (
                    pr.resources_spent / pr.total_resources_collected
                )

            # Damage metrics (actual HP damage, not cost-based)
            dealt = stats.get("total_damage_dealt_life", 0) + stats.get(
                "total_damage_dealt_shields", 0
            )
            taken = stats.get("total_damage_taken_life", 0) + stats.get(
                "total_damage_taken_shields", 0
            )

            if dealt > 0:
                pr.damage_dealt = int(dealt)
            if taken > 0:
                pr.damage_taken = int(taken)

            # Calculate damage ratio
            if pr.damage_taken > 0:
                pr.damage_ratio = pr.damage_dealt / pr.damage_taken
            elif pr.damage_dealt > 0:
                pr.damage_ratio = float(pr.damage_dealt)  # Infinite ratio, cap it

            # Army value killed (from CC stats)
            killed_army_minerals = stats.get("killed_minerals_army", 0)
            killed_army_vespene = stats.get("killed_vespene_army", 0)
            killed_eco_minerals = stats.get("killed_minerals_economy", 0)
            killed_eco_vespene = stats.get("killed_vespene_economy", 0)

            pr.army_value_killed = int(
                killed_army_minerals
                + killed_army_vespene
                + killed_eco_minerals
                + killed_eco_vespene
            )

            # Current army value
            pr.army_value_built = int(
                stats.get("total_value_units", 0)
                + stats.get("total_value_structures", 0)
            )

    def save_metrics_only(self, match: Match, result: ProcessedMatchResult, *, db: Optional[Session] = None):
        """Save metrics and features without updating ratings."""
        db = db if db is not None else self.db
        for pr in result.players:
            # Use canonical name from alias resolution
            from app.services.player_service import PlayerService
            canonical_name = PlayerService.resolve_canonical_name(
                db, resolve_player_name(pr.name), result.game_mode, len(result.players)
            )
            player = db.query(Player).filter(Player.name == canonical_name).first()
            if not player:
                continue

            mp = (
                db.query(MatchPlayer)
                .filter(
                    MatchPlayer.match_id == match.id, MatchPlayer.player_id == player.id
                )
                .first()
            )
            if not mp:
                continue

            # Impact Metrics
            ImpactService.save_match_metrics(db, mp.id, cast(Any, pr))
            ImpactService.update_player_averages(db, player.id)

            # Performance Features (ML features)
            # Check if pf already exists (might have been created by RatingSystem/PICalculator)
            pf = (
                db.query(PerformanceFeatures)
                .filter(PerformanceFeatures.match_player_id == mp.id)
                .first()
            )
            if not pf:
                pf = PerformanceFeatures(match_player_id=mp.id)
                db.add(pf)

            pf.build_order_json = pr.build_order  # type: ignore
            pf.build_order_hash = pr.build_order_hash
            pf.upgrades_json = pr.upgrades  # type: ignore
            pf.abilities_json = pr.ability_usage  # type: ignore
            pf.supply_block_seconds = pr.supply_block_seconds
            pf.early_worker_losses = pr.early_worker_losses
            pf.harassment_response_score = pr.harassment_response_score
            pf.detected_build_type = pr.detected_build_type

        ImpactService.save_kill_events(db, int(match.id), result.kill_events)
        db.commit()

    def _trigger_post_processing(self, match: Match, result: ProcessedMatchResult):
        from app.services.ingestion import post_process_match

        post_process_match(self.db, int(match.id), True, result.replay_file_path)

