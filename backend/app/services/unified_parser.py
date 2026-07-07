"""
Unified SC2 Replay Parser - Phase 2 Core Infrastructure
"""

import hashlib
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import sc2reader
from sc2reader.events import TrackerEvent

from app.models import GameMode, Race
from app.types.results import PlayerMatchResult, ProcessedMatchResult
from app.replay_parser import (
    calculate_replay_hash,
    calculate_game_fingerprint,
    determine_game_mode,
    normalize_race_name,
    SUPPLY_ADVANTAGE_THRESHOLD,
    RESOURCES_ADVANTAGE_THRESHOLD,
    WinnerDeterminationError,
    ReplayParseError,
)
from app.exceptions import ValidationError
from app.damage_timeline import DamageTimelineExtractor, DamageTimeline

logger = logging.getLogger(__name__)


class UnifiedParser:
    """
    The authoritative parser for SC2 MMR Tracker.
    """

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
        pass

    def parse(
        self, file_path: str, manual_winner_team: Optional[int] = None
    ) -> ProcessedMatchResult:
        """Execute unified parsing."""
        try:
            replay = sc2reader.load_replay(file_path, load_level=4)
            played_at = getattr(replay, "utc_date", None) or getattr(
                replay, "date", datetime.utcnow()
            )
            # `or` catches both "attribute missing" and "attribute is None"
            # (sc2reader can set map_name=None on partial/corrupt replays);
            # getattr's default alone only covers the former and previously
            # crashed calculate_game_fingerprint's map_name.lower().
            map_name = getattr(replay, "map_name", None) or "Unknown Map"
            duration_seconds = getattr(
                getattr(replay, "game_length", None), "seconds", 0
            )
            human_players = [
                p
                for p in getattr(replay, "players", [])
                if getattr(p, "is_human", False)
            ]

            if len(human_players) < 3:
                raise ValidationError(
                    f"Only team games (2v2+) are supported. Found {len(human_players)} players."
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

            for pid, result in player_results.items():
                timeline = DamageTimelineExtractor.extract_from_replay(replay, pid)
                # Normalize damage
                timeline_total = sum(timeline.damage_events.values())
                if result.army_value_killed > 0 and timeline_total > 0:
                    scale = result.army_value_killed / timeline_total
                    if scale > 1.1:
                        for sec in timeline.damage_events:
                            timeline.damage_events[sec] = int(
                                timeline.damage_events[sec] * scale
                            )
                result.damage_timeline = timeline.damage_events
                if (first_dmg := timeline.get_first_damage_second()) is not None:
                    result.first_damage_timing = first_dmg

            results_list = list(player_results.values())
            engagements = self._detect_team_engagements(results_list)
            for r in results_list:
                self._calculate_team_fight_metrics(r, engagements)

            self._calculate_derived_metrics(results_list)

            # Calculate game fingerprint for same-game detection
            player_names = [p.name for p in results_list]
            game_fp = calculate_game_fingerprint(map_name, played_at, player_names)

            return ProcessedMatchResult(
                played_at=played_at,
                game_mode=determine_game_mode(human_players) or GameMode.TWO_V_TWO,
                map_name=str(map_name),
                duration_seconds=int(duration_seconds),
                replay_hash=calculate_replay_hash(file_path),
                players=results_list,
                replay_file_path=file_path,
                game_fingerprint=game_fp,
            )
        except Exception as e:
            logger.error(f"Unified parsing error: {e}")
            raise ReplayParseError(str(e))

    def _extract_basic_stats(self, player: Any, result: PlayerMatchResult):
        if not hasattr(player, "stats") or not player.stats:
            return
        s = player.stats
        if hasattr(s, "minerals_collection_rate") and s.minerals_collection_rate:
            result.minerals_collected = int(s.minerals_collection_rate[-1])
        if hasattr(s, "vespene_collection_rate") and s.vespene_collection_rate:
            result.vespene_collected = int(s.vespene_collection_rate[-1])
        result.total_resources_collected = (
            result.minerals_collected + result.vespene_collected
        )

    def _determine_winner(self, replay, players, manual_override):
        if manual_override is not None:
            return manual_override
        for p in players:
            if str(getattr(p, "result", "")).lower() == "win":
                return int(getattr(p, "team_id", 0))
        # Heuristics if None
        team_stats = {}
        for p in players:
            tid = int(getattr(p, "team_id", 0))
            if tid not in team_stats:
                team_stats[tid] = {"s": 0.0, "r": 0.0}
            if hasattr(p, "stats") and p.stats:
                team_stats[tid]["s"] += float(getattr(p.stats, "supply_produced", 0))
                team_stats[tid]["r"] += float(getattr(p.stats, "minerals_collected", 0))
        if len(team_stats) == 2:
            t1, t2 = list(team_stats.keys())
            if team_stats[t1]["s"] > team_stats[t2]["s"] * 1.5:
                return t1
            if team_stats[t2]["s"] > team_stats[t1]["s"] * 1.5:
                return t2
        return None

    def _process_tracker_events(self, events, player_results):
        for event in events:
            if event.name == "UnitBornEvent":
                pid = getattr(event, "control_pid", None)
                if pid in player_results:
                    utype = getattr(event, "unit_type_name", "Unknown")
                    player_results[pid].army_value_built += self.UNIT_COSTS.get(
                        utype, 100
                    )
                    if utype in {"SCV", "Probe", "Drone"}:
                        player_results[pid].workers_created += 1
                    else:
                        player_results[pid].units_trained += 1
            elif event.name == "UnitDiedEvent":
                kpid = getattr(event, "killer_pid", None)
                if kpid in player_results:
                    player_results[kpid].units_killed += 1
                vpid = getattr(event, "unit_pid", None)
                if (
                    vpid is None
                    and hasattr(event, "unit")
                    and event.unit
                    and hasattr(event.unit, "owner")
                    and event.unit.owner
                ):
                    vpid = event.unit.owner.pid
                if vpid in player_results:
                    player_results[vpid].units_lost += 1
                    utype = (
                        getattr(event.unit, "name", "Unknown")
                        if hasattr(event, "unit")
                        else "Unknown"
                    )
                    if utype in {"SCV", "Probe", "Drone"}:
                        if event.second < 300:
                            player_results[vpid].early_worker_losses += 1
            elif event.name == "PlayerStatsEvent":
                pid = getattr(event, "pid", None)
                if pid in player_results:
                    r = player_results[pid]
                    r.minerals_collected = (
                        getattr(event, "minerals_used_current", 0)
                        + getattr(event, "minerals_lost", 0)
                        + getattr(event, "minerals_current", 0)
                    )
                    r.vespene_collected = (
                        getattr(event, "vespene_used_current", 0)
                        + getattr(event, "vespene_lost", 0)
                        + getattr(event, "vespene_current", 0)
                    )
                    r.total_resources_collected = (
                        r.minerals_collected + r.vespene_collected
                    )
                    r.army_value_lost = getattr(event, "resources_lost", 0)
                    r.army_value_killed = getattr(event, "resources_killed", 0)
                    if (
                        getattr(event, "food_used", 0) >= getattr(event, "food_made", 0)
                        and getattr(event, "food_made", 0) < 200
                    ):
                        r.supply_block_seconds += 10

    def _process_game_events(self, replay, player_results):
        for event in replay.game_events:
            if event.name in {
                "CmdEvent",
                "BasicCommandEvent",
                "TargetPointCommandEvent",
                "TargetUnitCommandEvent",
            }:
                p = getattr(event, "player", None)
                if p and p.pid in player_results:
                    aname = getattr(event, "ability_name", "Unknown")
                    player_results[p.pid].ability_usage[aname] = (
                        player_results[p.pid].ability_usage.get(aname, 0) + 1
                    )

    def _calculate_derived_metrics(self, results):
        for r in results:
            r.damage_dealt = r.army_value_killed
            r.damage_taken = r.army_value_lost
            r.damage_ratio = r.damage_dealt / max(1, r.damage_taken)
            if r.total_resources_collected > 0:
                r.spending_efficiency = min(
                    1.0,
                    (r.army_value_killed + r.army_value_lost)
                    / r.total_resources_collected,
                )
            self._calculate_impact_scores(r)

    def _calculate_impact_scores(self, r):
        res_score = min(100, r.total_resources_collected / 1000)
        worker_score = min(100, r.workers_created / 0.8)
        spending_score = r.spending_efficiency * 100
        r.economic_score = (res_score + worker_score + spending_score) / 3

        kill_score = min(100, r.army_value_killed / 500)
        ratio_score = min(100, r.damage_ratio * 10)
        ability_count = sum(r.ability_usage.values()) if r.ability_usage else 0
        r.combat_score = (kill_score + ratio_score + min(50, ability_count / 2)) / 3

        r.efficiency_score = max(
            0,
            (min(100, r.spending_efficiency * 100) + min(100, r.apm / 1.5)) / 2
            - (r.supply_block_seconds / 10),
        )

        team_score = (
            min(100, r.team_fight_participation * 100)
            + min(100, r.team_fight_damage_ratio * 100)
        ) / 2

        r.overall_impact = min(
            100,
            (
                r.combat_score * 0.30
                + team_score * 0.35
                + r.economic_score * 0.15
                + r.efficiency_score * 0.20
                + min(10, r.damage_ratio * 2)
            ),
        )

        if (
            r.early_worker_losses < 2
            and r.army_value_killed > 5000
            and r.overall_impact > 60
        ):
            r.player_archetype = "The Reaper (Aggressor)"
        elif r.overall_impact > 65:
            r.player_archetype = "The Assassin (Micro)"
        elif r.workers_created > 60:
            r.player_archetype = "The Titan (Macro)"
        elif r.team_fight_participation > 0.8:
            r.player_archetype = "The Vanguard (Teamwork)"
        else:
            r.player_archetype = "Tactical Balanced"

    def _detect_team_engagements(self, results):
        all_seconds = set()
        for r in results:
            all_seconds.update(r.damage_timeline.keys())
        sorted_seconds = sorted(all_seconds)
        engagements = []
        current = []
        for s in sorted_seconds:
            if not current or s - current[-1] <= 10:
                current.append(s)
            else:
                if len(current) >= 3:
                    active = []
                    for r in results:
                        if (
                            sum(
                                v
                                for k, v in r.damage_timeline.items()
                                if current[0] <= k <= current[-1]
                            )
                            > 0
                        ):
                            active.append(r.name)
                    if len(active) >= 3:
                        engagements.append({"start": current[0], "end": current[-1]})
                current = [s]
        return engagements

    def _calculate_team_fight_metrics(self, r, engagements):
        if not engagements:
            return
        participated = 0
        for e in engagements:
            if (
                sum(
                    v
                    for k, v in r.damage_timeline.items()
                    if e["start"] <= k <= e["end"]
                )
                > 0
            ):
                participated += 1
        r.team_fight_participation = participated / len(engagements)
        r.team_fight_damage_ratio = sum(
            v
            for k, v in r.damage_timeline.items()
            if any(e["start"] <= k <= e["end"] for e in engagements)
        ) / max(1, r.damage_dealt)

    def _clean_name(self, player):
        name = getattr(player, "name", None) or "Unknown"
        if hasattr(player, "clan_tag") and player.clan_tag:
            name = name.replace(f"[{player.clan_tag}]", "").strip()
        return name
