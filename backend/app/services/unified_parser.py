"""
Unified SC2 Replay Parser - Phase 2 Core Infrastructure

Consolidates basic metadata extraction, advanced performance metrics,
and ML-ready feature sequences into a single, high-performance engine.

Performs one single sc2reader load (Level 4) and extracts:
- Game Metadata (Map, Mode, Duration)
- Player Performance (Econ, Combat, APM)
- Tactical Sequences (Build Orders, Upgrades)
- Micro Insights (Ability Usage, Timelines)

SPEC-ARCH-001 Implementation.
"""

import hashlib
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import sc2reader  # type: ignore
from sc2reader.events import TrackerEvent  # type: ignore

# Absolute imports based on project pattern
from app.models import GameMode, Race  # type: ignore
from app.types.results import PlayerMatchResult, ProcessedMatchResult  # type: ignore
from app.replay_parser import (  # type: ignore
    calculate_replay_hash,
    determine_game_mode,
    normalize_race_name,
    SUPPLY_ADVANTAGE_THRESHOLD,
    RESOURCES_ADVANTAGE_THRESHOLD,
    WinnerDeterminationError,
    ReplayParseError,
)
from app.exceptions import ValidationError  # type: ignore
from app.damage_timeline import DamageTimelineExtractor, DamageTimeline  # type: ignore

# Dynamic ability discovery integration
try:
    from app.services.ability_discovery import get_discovery_engine  # type: ignore

    DYNAMIC_DISCOVERY_AVAILABLE = True
except ImportError:
    DYNAMIC_DISCOVERY_AVAILABLE = False
    get_discovery_engine = None  # type: ignore

logger = logging.getLogger(__name__)

# Recursive type resolution for JSON fields
JSONValue = Union[str, int, float, bool, None, List[Any], Dict[str, Any]]
JSONDict = Dict[str, JSONValue]


class UnifiedParser:
    """
    The authoritative parser for SC2 MMR Tracker.
    Merging logic from basic, advanced, and enhanced parsers.
    """

    # Unit cost database
    UNIT_COSTS = {
        "Marine": 50,
        "Marauder": 100,
        "Reaper": 50,
        "Ghost": 200,
        "Hellion": 100,
        "Hellbat": 100,
        "WidowMine": 75,
        "SiegeTank": 150,
        "Thor": 300,
        "Viking": 150,
        "Medivac": 100,
        "Liberator": 150,
        "Raven": 100,
        "Banshee": 150,
        "Battlecruiser": 400,
        "SCV": 50,
        "Probe": 50,
        "Zealot": 100,
        "Stalker": 125,
        "Sentry": 50,
        "Adept": 100,
        "HighTemplar": 50,
        "DarkTemplar": 125,
        "Immortal": 275,
        "Colossus": 300,
        "Disruptor": 150,
        "Observer": 25,
        "WarpPrism": 200,
        "Phoenix": 150,
        "VoidRay": 250,
        "Oracle": 150,
        "Tempest": 300,
        "Carrier": 350,
        "Mothership": 400,
        "Archon": 0,
        "Drone": 50,
        "Zergling": 25,
        "Baneling": 25,
        "Roach": 75,
        "Ravager": 100,
        "Hydralisk": 100,
        "Lurker": 150,
        "Infestor": 100,
        "SwarmHost": 100,
        "Ultralisk": 300,
        "Queen": 150,
        "Overlord": 100,
        "Overseer": 50,
        "Mutalisk": 100,
        "Corruptor": 150,
        "BroodLord": 150,
        "Viper": 100,
        "CommandCenter": 400,
        "Nexus": 400,
        "Hatchery": 300,
    }

    def __init__(self):
        self.use_dynamic_discovery = (
            os.getenv("USE_DYNAMIC_DISCOVERY", "true").lower() == "true"
        )
        self.ability_discovery: Any = None
        if self.use_dynamic_discovery and DYNAMIC_DISCOVERY_AVAILABLE:
            try:
                engine_func = cast(Any, get_discovery_engine)
                self.ability_discovery = engine_func()
            except Exception as e:
                logger.warning(f"Failed to init dynamic discovery: {e}")

    def parse(
        self, file_path: str, manual_winner_team: Optional[int] = None
    ) -> ProcessedMatchResult:
        """Execute unified parsing with single Level 4 load."""
        try:
            replay = sc2reader.load_replay(file_path, load_level=4)  # type: ignore
            # Try multiple date attributes in order of preference
            played_at = getattr(replay, "utc_date", None)
            if played_at is None:
                played_at = getattr(replay, "date", None)
            if played_at is None:
                played_at = getattr(replay, "start_time", None)
            if played_at is None:
                played_at = datetime.utcnow()
            map_name = getattr(replay, "map_name", "Unknown Map")
            duration_seconds = getattr(
                getattr(replay, "game_length", None), "seconds", 0
            )
            human_players = [
                p
                for p in getattr(replay, "players", [])
                if getattr(p, "is_human", False)
            ]

            # Reject 1v1 games - only team games (3+ players) are supported
            if len(human_players) < 3:
                raise ValidationError(
                    f"Only team games (2v2+) are supported. Found {len(human_players)} players (1v1 game)."
                )

            winner_team = self._determine_winner(
                replay, human_players, manual_winner_team
            )

            player_results: Dict[int, PlayerMatchResult] = {}
            for p in human_players:
                pid = getattr(p, "pid", 0)
                player_results[pid] = PlayerMatchResult(
                    name=self._clean_name(p),
                    race=normalize_race_name(str(p.play_race)),
                    team=int(getattr(p, "team_id", 0)),
                    won=(int(getattr(p, "team_id", 0)) == winner_team)
                    if winner_team is not None
                    else (str(getattr(p, "result", "") or "").lower() == "win"),
                    apm=float(getattr(p, "avg_apm", 0.0)),
                )
                self._extract_basic_stats(p, player_results[pid])

            if hasattr(replay, "tracker_events"):
                self._process_tracker_events(replay.tracker_events, player_results)

            if hasattr(replay, "game_events"):
                self._process_game_events(replay, player_results)

            # Damage timeline extraction
            for pid, result in player_results.items():
                timeline = DamageTimelineExtractor.extract_from_replay(replay, pid)
                result.damage_timeline = timeline.damage_events
                if (first_dmg := timeline.get_first_damage_second()) is not None:
                    result.first_damage_timing = first_dmg

            results_list = list(player_results.values())

            # Team fight detection and metrics
            engagements = self._detect_team_engagements(results_list)
            for r in results_list:
                self._calculate_team_fight_metrics(r, engagements)

            # Final derived metrics and impact scores
            self._calculate_derived_metrics(results_list)

            return ProcessedMatchResult(
                played_at=played_at,
                game_mode=determine_game_mode(len(human_players)) or GameMode.TWO_V_TWO,
                map_name=str(map_name),
                duration_seconds=int(duration_seconds),
                replay_hash=calculate_replay_hash(file_path),
                players=results_list,
                replay_file_path=file_path,
            )

        except Exception as e:
            if isinstance(e, WinnerDeterminationError):
                raise
            logger.error(f"Unified parsing error: {e}")
            raise ReplayParseError(str(e))

    def _extract_basic_stats(self, player: Any, result: PlayerMatchResult):
        """Extract stats from sc2reader's player.stats attribute."""
        if not hasattr(player, "stats") or not player.stats:
            return

        stats = player.stats
        if (
            hasattr(stats, "minerals_collection_rate")
            and stats.minerals_collection_rate
        ):
            result.minerals_collected = int(stats.minerals_collection_rate[-1])
        if hasattr(stats, "vespene_collection_rate") and stats.vespene_collection_rate:
            result.vespene_collected = int(stats.vespene_collection_rate[-1])

        result.total_resources_collected = (
            result.minerals_collected + result.vespene_collected
        )

    def _determine_winner(
        self, replay: Any, players: List[Any], manual_override: Optional[int]
    ) -> Optional[int]:
        if manual_override is not None:
            return manual_override
        for p in players:
            res = getattr(p, "result", "")
            if res and str(res).lower() == "win":
                return int(getattr(p, "team_id", 0))

        team_stats: Dict[int, Dict[str, float]] = {}
        for p in players:
            tid = int(getattr(p, "team_id", 0))
            if tid not in team_stats:
                team_stats[tid] = {"s": 0.0, "r": 0.0}
            if hasattr(p, "stats") and p.stats:
                team_stats[tid]["s"] += float(getattr(p.stats, "supply_produced", 0))
                team_stats[tid]["r"] += float(getattr(p.stats, "minerals_collected", 0))

        if len(team_stats) == 2:
            t1, t2 = list(team_stats.keys())
            s1, s2 = team_stats[t1]["s"], team_stats[t2]["s"]
            r1, r2 = team_stats[t1]["r"], team_stats[t2]["r"]
            if (
                s1 > s2 * SUPPLY_ADVANTAGE_THRESHOLD
                or r1 > r2 * RESOURCES_ADVANTAGE_THRESHOLD
            ):
                return t1
            if (
                s2 > s1 * SUPPLY_ADVANTAGE_THRESHOLD
                or r2 > r1 * RESOURCES_ADVANTAGE_THRESHOLD
            ):
                return t2
        return None

    def _process_tracker_events(
        self, events: List[Any], player_results: Dict[int, PlayerMatchResult]
    ):
        unit_compositions: Dict[int, Dict[str, int]] = {}

        for event in events:
            if event.name == "UnitBornEvent":
                pid = getattr(event, "control_pid", None)
                if pid in player_results:
                    utype = getattr(event, "unit_type_name", "Unknown")
                    cost = self.UNIT_COSTS.get(utype, 100)
                    player_results[pid].army_value_built += cost

                    if pid not in unit_compositions:
                        unit_compositions[pid] = {}
                    unit_compositions[pid][utype] = (
                        unit_compositions[pid].get(utype, 0) + 1
                    )

                    if utype in {"SCV", "Probe", "Drone"}:
                        player_results[pid].workers_created += 1
                    else:
                        # Count non-worker units as units_trained
                        player_results[pid].units_trained += 1

                    # Note: Bases are tracked in UnitInitEvent (when building starts)
                    # UnitBornEvent fires when buildings complete, so we don't double-count here

                    if self._should_track_build_event(utype):
                        player_results[pid].build_order.append(
                            {
                                "second": event.second,
                                "unit_type": utype,
                                "is_building": False,
                                "is_worker": utype in {"SCV", "Probe", "Drone"},
                                "supply": 0,
                            }
                        )

            elif event.name == "UnitInitEvent":
                pid = getattr(event, "control_pid", None)
                if pid in player_results:
                    utype = getattr(event, "unit_type_name", "Unknown")
                    cost = self.UNIT_COSTS.get(utype, 100)
                    player_results[pid].army_value_built += cost

                    # Track bases from UnitInitEvent (buildings start here)
                    if utype in {"CommandCenter", "Nexus", "Hatchery"}:
                        player_results[pid].bases_created += 1
                        # First expansion is the 2nd base (index 2 since we start at 1)
                        if (
                            player_results[pid].bases_created == 2
                            and player_results[pid].first_expansion_timing is None
                        ):
                            player_results[pid].first_expansion_timing = event.second

                    player_results[pid].build_order.append(
                        {
                            "second": event.second,
                            "unit_type": utype,
                            "is_building": True,
                            "is_worker": False,
                            "supply": 0,
                        }
                    )

            elif event.name == "UnitDiedEvent":
                # Get unit type from the unit object, not unit_type_name (which doesn't exist on UnitDiedEvent)
                utype = "Unknown"
                if hasattr(event, "unit") and event.unit:
                    utype = getattr(event.unit, "name", "Unknown")
                    # Also try _type_class.name as fallback
                    if (
                        utype == "Unknown"
                        and hasattr(event.unit, "_type_class")
                        and event.unit._type_class
                    ):
                        utype = getattr(event.unit._type_class, "name", "Unknown")

                # NOTE: We only count units_killed/lost here, not army_value.
                # army_value_killed/lost comes from PlayerStatsEvent which is more accurate.

                # Resilient killer detection
                kpid = getattr(event, "killer_pid", None)
                if kpid is None and hasattr(event, "killer") and event.killer:
                    killer = event.killer
                    if hasattr(killer, "pid"):
                        kpid = killer.pid

                if kpid and kpid in player_results:
                    player_results[kpid].units_killed += 1

                # Resilient victim detection
                vpid = getattr(event, "unit_pid", None)
                if vpid is None and hasattr(event, "unit") and event.unit:
                    unit = event.unit
                    if hasattr(unit, "owner") and unit.owner:
                        vpid = unit.owner.pid

                if vpid and vpid in player_results:
                    player_results[vpid].units_lost += 1
                    if utype in {"SCV", "Probe", "Drone"} and event.second < 300:
                        player_results[vpid].early_worker_losses += 1

            elif event.name == "UpgradeCompleteEvent":
                pid = getattr(event, "pid", None)
                if pid in player_results:
                    uname = getattr(event, "upgrade_type_name", "Unknown")
                    player_results[pid].upgrades.append(
                        {
                            "second": event.second,
                            "upgrade_name": uname,
                            "category": self._categorize_upgrade(uname),
                        }
                    )

            # PlayerStatsEvent - contains resource collection, army values, workers
            elif event.name == "PlayerStatsEvent":
                pid = getattr(event, "pid", None)
                if pid in player_results:
                    r = player_results[pid]
                    # Cumulative resources: Used + Current
                    # minerals_used_current is total spent on buildings/units still alive
                    # minerals_lost is total spent on things that died
                    # minerals_current is unspent
                    # Total collected = used + lost + current
                    m_used = getattr(event, "minerals_used_current", 0)
                    m_lost = getattr(event, "minerals_lost", 0)
                    m_curr = getattr(event, "minerals_current", 0)

                    v_used = getattr(event, "vespene_used_current", 0)
                    v_lost = getattr(event, "vespene_lost", 0)
                    v_curr = getattr(event, "vespene_current", 0)

                    # Use direct assignment - the last PlayerStatsEvent has the final values
                    # Previous logic used max() which could pick inflated mid-game values
                    r.minerals_collected = m_used + m_lost + m_curr
                    r.vespene_collected = v_used + v_lost + v_curr

                    r.total_resources_collected = (
                        r.minerals_collected + r.vespene_collected
                    )

                    # Army value lost (more accurate than UnitDiedEvent tracking)
                    minerals_lost_army = getattr(event, "minerals_lost_army", 0)
                    vespene_lost_army = getattr(event, "vespene_lost_army", 0)
                    r.army_value_lost = minerals_lost_army + vespene_lost_army

                    # Army value killed
                    minerals_killed = getattr(event, "minerals_killed_army", 0)
                    vespene_killed = getattr(event, "vespene_killed_army", 0)
                    r.army_value_killed = minerals_killed + vespene_killed

                    # FALLBACK: If damage_dealt is still 0, use army_value_killed as a proxy
                    if r.damage_dealt == 0 and r.army_value_killed > 0:
                        r.damage_dealt = r.army_value_killed

                    # Workers active
                    workers = getattr(event, "workers_active_count", 0)
                    if workers > r.workers_created:
                        r.workers_created = workers

                    # Supply block detection - PlayerStatsEvent fires every 10 seconds
                    food_used = getattr(event, "food_used", 0)
                    food_cap = getattr(event, "food_made", 0)
                    # Supply blocked = at cap and can't produce
                    if food_used >= food_cap and food_cap < 200:
                        # Each event represents ~10 game seconds of being supply blocked
                        r.supply_block_seconds += 10

        for pid, composition in unit_compositions.items():
            if pid in player_results:
                sorted_units = sorted(
                    composition.items(), key=lambda x: x[1], reverse=True
                )[:5]
                player_results[pid].unit_composition = dict(sorted_units)

    def _process_game_events(
        self, replay: Any, player_results: Dict[int, PlayerMatchResult]
    ):
        if self.use_dynamic_discovery and self.ability_discovery:
            self.ability_discovery.discover_from_replay(replay)

        for event in replay.game_events:
            # Track abilities from various event types
            if event.name in {
                "CmdEvent",
                "BasicCommandEvent",
                "TargetPointCommandEvent",
                "TargetUnitCommandEvent",
            }:
                p = getattr(event, "player", None)
                pid = getattr(p, "pid", None) if p else None
                if pid in player_results:
                    # Try multiple ways to get ability name
                    aname = None
                    if hasattr(event, "ability") and event.ability:
                        aname = getattr(event.ability, "name", None)
                    if not aname:
                        aname = getattr(event, "ability_name", None)

                    if aname and aname != "Unknown" and aname != "None":
                        should_track = True
                        if self.use_dynamic_discovery and self.ability_discovery:
                            should_track = self.ability_discovery.should_track_ability(
                                aname
                            )

                        if should_track:
                            player_results[pid].ability_usage[aname] = (
                                player_results[pid].ability_usage.get(aname, 0) + 1
                            )

    def _calculate_derived_metrics(self, results: List[PlayerMatchResult]):
        for r in results:
            # Build order hash
            major = [e["unit_type"] for e in r.build_order if not e.get("is_worker")][
                :10
            ]
            r.build_order_hash = hashlib.md5(",".join(major).encode()).hexdigest()[:16]

            # Build order classification
            try:
                from app.services.build_order_classifier import get_classifier  # type: ignore

                classifier = get_classifier()
                archetype, _ = classifier.classify(r.build_order, r.race.value)
                r.detected_build_type = archetype
            except Exception as e:
                logger.warning(f"Build classification failed: {e}")

            # Damage stats - Fallback to army_value_killed if damage_dealt is 0
            if (r.damage_dealt or 0) == 0:
                r.damage_dealt = r.army_value_killed
            if (r.damage_taken or 0) == 0:
                r.damage_taken = r.army_value_lost

            # Economy stats - Fallback to army_value_built if total_resources_collected is 0
            if (r.total_resources_collected or 0) < 100:
                # Use army_value_built + workers as a proxy for economy
                # Each worker is ~50 minerals, plus their production value
                # This is a rough estimate but better than 0
                estimated_eco = r.army_value_built + (r.workers_created * 100)
                r.total_resources_collected = estimated_eco
                r.minerals_collected = int(estimated_eco * 0.7)
                r.vespene_collected = int(estimated_eco * 0.3)

            # Calculate damage ratio with edge case handling
            if r.damage_taken > 0:
                r.damage_ratio = r.damage_dealt / r.damage_taken
            elif r.damage_dealt > 0:
                r.damage_ratio = 10.0  # Cap when no losses
            else:
                r.damage_ratio = 1.0

            r.harassment_response_score = max(0, 100 - (r.early_worker_losses * 10))
            if r.total_resources_collected > 0:
                estimated_spending = r.army_value_killed + r.army_value_lost
                r.resources_spent = estimated_spending
                r.spending_efficiency = min(
                    1.0, estimated_spending / r.total_resources_collected
                )
            self._calculate_impact_scores(r)

    def _calculate_impact_scores(self, r: PlayerMatchResult):
        """
        Calculate impact scores using DISTINCT raw metrics to avoid double-counting.
        Matches the formula in advanced_parser.py.
        """
        # ECONOMIC SCORE (0-100)
        resource_score = min(100, r.total_resources_collected / 1000)
        worker_score = min(100, r.workers_created / 0.8)
        spending_score = r.spending_efficiency * 100
        r.economic_score = (resource_score + worker_score + spending_score) / 3

        # COMBAT SCORE (0-100) - uses army_value_killed and damage_ratio
        capped_ratio = min(r.damage_ratio, 10.0)
        kill_value_score = min(100, r.army_value_killed / 500)
        ratio_score = min(100, capped_ratio * 10)
        r.combat_score = (kill_value_score + ratio_score) / 2

        # EFFICIENCY SCORE (0-100) - Resource conversion efficiency
        # Spending efficiency + APM
        spending_score = min(100, r.spending_efficiency * 100)
        apm_score = min(100, (r.apm / 150) * 100) if r.apm > 0 else 50
        r.efficiency_score = (spending_score + apm_score) / 2

        # TEAM CONTRIBUTION SCORE (0-100)
        participation_score = min(100, r.team_fight_participation * 100)
        effectiveness_score = min(100, r.team_fight_damage_ratio * 100)
        team_contribution_score = (participation_score + effectiveness_score) / 2

        # OVERALL IMPACT - Weighted for team games
        r.overall_impact = (
            r.combat_score * 0.35
            + team_contribution_score * 0.35
            + r.economic_score * 0.20
            + r.efficiency_score * 0.10
        )

    def _detect_team_engagements(
        self, results: List[PlayerMatchResult], threshold: int = 1000, window: int = 10
    ) -> List[Dict[str, Any]]:
        """Detect multi-player engagements based on damage timelines."""
        all_seconds: set[int] = set()
        for r in results:
            all_seconds.update(r.damage_timeline.keys())

        sorted_seconds = sorted(all_seconds)
        engagements = []
        current_window: List[int] = []
        for second in sorted_seconds:
            if not current_window or second - current_window[-1] <= window:
                current_window.append(second)
            else:
                if len(current_window) >= 3:
                    engagement = self._process_window(
                        current_window, results, threshold
                    )
                    if engagement:
                        engagements.append(engagement)
                current_window = [second]
        if len(current_window) >= 3:
            engagement = self._process_window(current_window, results, threshold)
            if engagement:
                engagements.append(engagement)
        return engagements

    def _process_window(
        self, seconds: List[int], results: List[PlayerMatchResult], threshold: int
    ) -> Optional[Dict[str, Any]]:
        start, end = seconds[0], seconds[-1]
        players_active = []
        total_damage = 0
        for r in results:
            dmg = sum(v for k, v in r.damage_timeline.items() if start <= k <= end)
            if dmg > 0:
                players_active.append(r.name)
                total_damage += dmg
        if len(players_active) >= 3 and total_damage >= threshold:
            return {
                "start": start,
                "end": end,
                "players": players_active,
                "total_damage": total_damage,
            }
        return None

    def _calculate_team_fight_metrics(
        self, r: PlayerMatchResult, engagements: List[Dict[str, Any]]
    ):
        if not engagements:
            return
        fights_participated = 0
        total_tf_damage = 0
        for e in engagements:
            dmg = sum(
                v for k, v in r.damage_timeline.items() if e["start"] <= k <= e["end"]
            )
            if dmg > 0:
                fights_participated += 1
                total_tf_damage += dmg
        r.team_fight_participation = fights_participated / len(engagements)
        r.team_fight_damage = total_tf_damage
        r.team_fight_damage_ratio = total_tf_damage / max(1, r.damage_dealt)

    def _clean_name(self, player: Any) -> str:
        name = getattr(player, "name", "Unknown")
        if hasattr(player, "clan_tag") and player.clan_tag:
            name = name.replace(f"[{player.clan_tag}]", "").strip()
        return name

    def _should_track_build_event(self, utype: str) -> bool:
        skip = {"Larva", "Egg", "Cocoon", "MULE", "Interceptor", "AdeptPhaseShift"}
        return utype not in skip and not utype.startswith(
            ("Beacon", "Reward", "Spray", "Destructible")
        )

    def _categorize_upgrade(self, name: str) -> str:
        n = name.lower()
        if any(x in n for x in ["attack", "weapons"]):
            return "attack"
        if any(x in n for x in ["armor", "plating", "carapace"]):
            return "armor"
        if "shield" in n:
            return "shield"
        if any(x in n for x in ["speed", "boost", "thermal"]):
            return "speed"
        return "tech"
