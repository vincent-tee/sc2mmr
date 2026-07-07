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
from typing import Any, Dict, List, Optional, Tuple, cast

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.auto_adaptive import trigger_auto_optimization  # type: ignore
from app.exceptions import (  # type: ignore
    DuplicateReplayError,
    DuplicateGameError,
    ReplayParseError,
    ValidationError,
    WinnerDeterminationError,
)
from app.models import Match, MatchPlayer, Player, PerformanceFeatures, Race  # type: ignore
from app.impact_service import ImpactService  # type: ignore
from app.performance_rating import PerformanceRatingAdjuster  # type: ignore
from app.rating_system import RatingSystem  # type: ignore
from app.services.unified_parser import UnifiedParser  # type: ignore
from app.types.results import ProcessedMatchResult, PlayerMatchResult  # type: ignore
from app.services.ml_features_service import MLFeaturesService  # type: ignore

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

        # 2. Duplicate Detection (by hash and fingerprint)
        duplicate_start = time.time()

        # 2a. Check for exact file duplicate (same replay file)
        existing = (
            self.db.query(Match).filter(Match.replay_hash == result.replay_hash).first()
        )
        if existing:
            raise DuplicateReplayError(result.replay_hash, existing.id)

        # 2b. Check for same game from different observer (fingerprint match)
        if result.game_fingerprint:
            fingerprint_match = (
                self.db.query(Match)
                .filter(Match.game_fingerprint == result.game_fingerprint)
                .first()
            )
            if fingerprint_match:
                # Same game found - compare durations
                if fingerprint_match.duration_seconds >= result.duration_seconds:
                    # Existing has more or equal data - reject new upload
                    raise DuplicateGameError(
                        game_fingerprint=result.game_fingerprint,
                        existing_match_id=fingerprint_match.id,
                        existing_duration=fingerprint_match.duration_seconds,
                        new_duration=result.duration_seconds,
                    )
                else:
                    # New replay has more data - delete old match and proceed
                    logger.info(
                        f"Replacing match {fingerprint_match.id} with longer replay "
                        f"({fingerprint_match.duration_seconds}s -> {result.duration_seconds}s)"
                    )
                    self._delete_match_and_recalculate(fingerprint_match.id)

        duplicate_check_time_ms = (time.time() - duplicate_start) * 1000

        # 3. DB Record Creation (Match & MatchPlayers)
        match = self._create_match_records(result)

        # 4. Rating & Metrics Pipeline
        rating_start = time.time()
        self._process_match_data(match, result)
        rating_update_time_ms = (time.time() - rating_start) * 1000

        # 5. Optimization Triggers
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

    def _create_match_records(self, result: ProcessedMatchResult) -> Match:
        """Create Match and MatchPlayer records."""
        match = Match(
            played_at=result.played_at,
            game_mode=result.game_mode,
            map_name=result.map_name,
            duration_seconds=result.duration_seconds,
            replay_file_path=result.replay_file_path,
            replay_hash=result.replay_hash,
            game_fingerprint=result.game_fingerprint,
        )
        self.db.add(match)
        self.db.flush()

        for pr in result.players:
            canonical_name = resolve_player_name(pr.name)
            player = self.db.query(Player).filter(Player.name == canonical_name).first()
            if not player:
                player = Player(name=canonical_name)
                self.db.add(player)
                self.db.flush()

            mp = MatchPlayer(
                match_id=match.id,
                player_id=player.id,
                team_number=pr.team,
                race=Race(pr.race),
                won=1 if pr.won else 0,
                mu_before=player.mu,
                sigma_before=player.sigma,
                mu_after=player.mu,
                sigma_after=player.sigma,
            )
            self.db.add(mp)

        self.db.flush()
        return match

    def _process_match_data(self, match: Match, result: ProcessedMatchResult):
        """Update ratings, save metrics, and extract ML features."""
        # A. Save Performance Metrics & Features FIRST
        # This ensures RatingSystem/PICalculator can use them for PIM
        self.save_metrics_only(match, result)

        # B. Update TrueSkill Ratings
        from app.replay_parser import ReplayData, PlayerData  # type: ignore

        legacy_data = ReplayData(
            played_at=result.played_at,
            game_mode=result.game_mode,
            map_name=result.map_name,
            duration_seconds=result.duration_seconds,
            replay_hash=result.replay_hash,
            game_fingerprint=result.game_fingerprint or "",
            players=[
                PlayerData(
                    name=resolve_player_name(p.name),  # Use canonical name
                    race=p.race,
                    team=p.team,
                    won=p.won,
                )
                for p in result.players
            ],
        )
        RatingSystem.update_ratings_from_match(self.db, legacy_data, match)

        # C. Performance Adjustments (PIM)
        PerformanceRatingAdjuster.adjust_ratings_for_match(self.db, int(match.id))
        ImpactService.update_synergies(self.db, int(match.id))

        # D. Achievements - checked against the totals/metrics/synergies just
        # written above. Non-blocking: an achievement bug must never break
        # ingestion for the batch/observer pipeline.
        try:
            from app.services import AchievementService  # type: ignore

            for pr in result.players:
                canonical_name = resolve_player_name(pr.name)
                player = (
                    self.db.query(Player)
                    .filter(Player.name == canonical_name)
                    .first()
                )
                if player:
                    AchievementService.check_and_award_all(
                        self.db, int(player.id), int(match.id)
                    )
        except Exception as e:
            logger.warning(f"Achievement check failed for match {match.id}: {e}")

        # E. Head-to-head/rivalry stats (player_rivalries table, backing the
        # /h2h page) - same non-blocking rationale as Achievements above.
        # This mirrors the equivalent call added to the HTTP upload path
        # (app/api/replays.py); both pipelines must stay in sync or rivalry
        # data silently goes stale for matches ingested via this path
        # (batch scripts / replay observer).
        try:
            from app.services.rivalry_service import RivalryService  # type: ignore

            RivalryService.calculate_all_rivalries(self.db)
        except Exception as e:
            logger.warning(f"Rivalry recalculation failed for match {match.id}: {e}")

    def save_metrics_only(self, match: Match, result: ProcessedMatchResult):
        """Save metrics and features without updating ratings."""
        for pr in result.players:
            # Use canonical name from alias resolution
            canonical_name = resolve_player_name(pr.name)
            player = self.db.query(Player).filter(Player.name == canonical_name).first()
            if not player:
                continue

            mp = (
                self.db.query(MatchPlayer)
                .filter(
                    MatchPlayer.match_id == match.id, MatchPlayer.player_id == player.id
                )
                .first()
            )
            if not mp:
                continue

            # Impact Metrics
            ImpactService.save_match_metrics(self.db, mp.id, cast(Any, pr))
            ImpactService.update_player_averages(self.db, player.id)

            # Performance Features (ML features)
            # Check if pf already exists (might have been created by RatingSystem/PICalculator)
            pf = (
                self.db.query(PerformanceFeatures)
                .filter(PerformanceFeatures.match_player_id == mp.id)
                .first()
            )
            if not pf:
                pf = PerformanceFeatures(match_player_id=mp.id)
                self.db.add(pf)

            pf.build_order_json = pr.build_order  # type: ignore
            pf.build_order_hash = pr.build_order_hash
            pf.upgrades_json = pr.upgrades  # type: ignore
            pf.abilities_json = pr.ability_usage  # type: ignore
            pf.supply_block_seconds = pr.supply_block_seconds
            pf.early_worker_losses = pr.early_worker_losses
            pf.harassment_response_score = pr.harassment_response_score
            pf.detected_build_type = pr.detected_build_type

        self.db.commit()

    def _trigger_post_processing(self, match: Match, result: ProcessedMatchResult):
        """Trigger background tasks and optimizations."""
        # A. ML Feature Extraction (Essential for SHAP and Win Prob)
        try:
            MLFeaturesService.extract_and_save_ml_features(
                self.db, str(match.replay_file_path), int(match.id)
            )
        except Exception as e:
            logger.warning(f"ML Feature extraction failed: {e}")

        # B. Online Learning
        try:
            from app.online_learning import OnlineLearningEngine  # type: ignore

            team1_won = any(p.won for p in result.players if p.team == 1)
            engine = OnlineLearningEngine(self.db)
            engine.record_outcome(int(match.id), team1_won)
        except Exception as e:
            logger.warning(f"Online learning failed: {e}")

        # C. Auto Optimization (Weights)
        try:
            trigger_auto_optimization(self.db)
        except Exception as e:
            logger.warning(f"Auto-optimization failed: {e}")

        # D. Automated ML Retraining (Every 15 matches)
        try:
            match_count = self.db.query(Match).count()
            if match_count % 15 == 0:
                from .ml_predictor import train_ml_model

                logger.info(
                    f"Triggering automated ML retraining (Match #{match_count})"
                )
                train_ml_model(self.db)
        except Exception as e:
            logger.warning(f"Automated ML retraining failed: {e}")

        # E. Live Forecast Feed
        try:
            from app.services.tactical_forecast import TacticalForecastService
            from app.models import LiveMatchFeed

            pids = [p.player_id for p in match.participants]
            forecast = TacticalForecastService.get_forecast(
                pids, match.map_name, self.db
            )

            # Deactivate old feeds
            self.db.execute(text("UPDATE live_match_feed SET is_active = 0"))

            new_feed = LiveMatchFeed(
                match_id=match.id,
                map_name=match.map_name,
                forecast_json=forecast,
                is_active=True,
            )
            self.db.add(new_feed)
            self.db.commit()
            logger.info(f"Live forecast generated for Match #{match.id}")
        except Exception as e:
            logger.warning(f"Live forecast generation failed: {e}")

    def _delete_match_and_recalculate(self, match_id: int) -> None:
        """
        Delete a match that will be replaced by a longer replay of the same game.

        This is used when a fingerprint duplicate is found but the new replay
        has more data (longer duration). We delete the old match so the new
        one can be inserted properly.
        """
        match = self.db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return

        # Delete related match_players first (CASCADE should handle this, but being explicit)
        self.db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).delete()

        # Delete performance features
        self.db.query(PerformanceFeatures).filter(
            PerformanceFeatures.match_player_id.in_(
                self.db.query(MatchPlayer.id).filter(MatchPlayer.match_id == match_id)
            )
        ).delete(synchronize_session=False)

        # Delete the match
        self.db.delete(match)
        self.db.flush()

        logger.info(f"Deleted match {match_id} to be replaced by longer replay")
