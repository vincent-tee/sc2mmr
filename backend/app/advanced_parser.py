"""
Advanced SC2 Replay Parser - Extract detailed player metrics

This module uses sc2reader to extract deep statistics:
- Economic performance (resources, workers, spending)
- Army composition and value
- Damage dealt and taken
- Build order timings
- Player impact metrics
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import timedelta
import sc2reader  # type: ignore
from sc2reader.events import TrackerEvent  # type: ignore
from sc2reader.engine.plugins import APMTracker  # type: ignore
import logging

from .replay_parser import (
    parse_replay,
    ReplayData,
    ReplayParseError,
    WinnerDeterminationError,
)
from .damage_timeline import DamageTimelineExtractor, DamageTimeline

logger = logging.getLogger(__name__)

# Register APMTracker plugin for APM calculation
sc2reader.engine.register_plugin(APMTracker())  # type: ignore


@dataclass
class PlayerMetrics:
    """Detailed player performance metrics."""

    player_name: str
    race: str
    team: int
    won: bool
    is_ai: bool = False
    difficulty: Optional[str] = None

    # Economic metrics
    minerals_collected: int = 0
    vespene_collected: int = 0
    total_resources_collected: int = 0
    resources_spent: int = 0
    spending_efficiency: float = 0.0  # Spent / Collected
    workers_created: int = 0

    # Army metrics
    units_trained: int = 0
    units_lost: int = 0
    units_killed: int = 0
    army_value_built: int = 0  # Resource value
    army_value_killed: int = 0
    army_value_lost: int = 0

    # Combat metrics
    damage_dealt: int = 0
    damage_taken: int = 0
    damage_dealt_to_structures: int = 0
    damage_ratio: float = 0.0  # Dealt / Taken
    kill_death_ratio: float = 1.0  # Units killed / units lost

    # Timing metrics (in game seconds)
    first_expansion_timing: Optional[int] = None
    first_army_timing: Optional[int] = None  # When 8+ army supply
    first_damage_timing: Optional[int] = None  # When first damage was dealt
    bases_created: int = 0

    # Mechanics
    apm: float = 0.0

    # Unit composition (top 5 units by count)
    unit_composition: Optional[Dict[str, int]] = None

    # Impact scores (calculated)
    economic_score: float = 0.0
    combat_score: float = 0.0
    efficiency_score: float = 0.0
    overall_impact: float = 0.0

    # Team game metrics
    team_fight_participation: float = 0.0  # % of team fights participated in (0-1)
    team_fight_damage: int = 0  # Damage dealt in multi-player engagements
    team_fight_damage_ratio: float = 0.0  # Team fight damage / total damage

    # Game phase damage (for timeline analysis)
    early_game_damage: int = 0  # Damage in first 5 minutes
    mid_game_damage: int = 0  # Damage 5-15 minutes
    late_game_damage: int = 0  # Damage 15+ minutes

    # Player style metrics
    aggression_score: float = 0.0  # How aggressive the player is (0-100)
    player_archetype: Optional[str] = None  # e.g., 'Rusher', 'Macro', 'Harasser'

    # Damage timeline (second-by-second)
    damage_timeline: Optional[DamageTimeline] = None

    def __post_init__(self):
        if self.unit_composition is None:
            self.unit_composition = {}


@dataclass
class AdvancedReplayData:
    """Replay data with advanced metrics."""

    basic_data: ReplayData
    player_metrics: List[PlayerMetrics]
    game_duration_seconds: int

    # Team aggregates
    team_1_total_damage: int = 0
    team_2_total_damage: int = 0
    team_1_total_resources: int = 0
    team_2_total_resources: int = 0


# Unit cost database (simplified - can be expanded)
UNIT_COSTS = {
    # Terran
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
    # Protoss
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
    "Archon": 0,  # Created from merging
    # Zerg
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
    # Buildings (for damage tracking)
    "CommandCenter": 400,
    "Nexus": 400,
    "Hatchery": 300,
}


def get_unit_cost(unit_name: str) -> int:
    """
    Get resource cost for a unit (minerals + vespene).

    Args:
        unit_name: Name of the unit

    Returns:
        Total resource cost
    """
    return UNIT_COSTS.get(unit_name, 100)  # Default 100 for unknown units


# Single source of truth for K/D — also used by the backfill script and tests.
KD_RATIO_CAP = 10.0


def compute_kill_death_ratio(units_killed: int, units_lost: int) -> float:
    """
    Kill/death ratio from unit counts, capped at KD_RATIO_CAP for every value —
    not just the zero-loss case — so a 50-kill/1-loss game can't overtake a
    flawless one. Returns 1.0 (neutral) when no combat was recorded.
    """
    killed = units_killed or 0
    lost = units_lost or 0
    if lost > 0:
        return min(killed / lost, KD_RATIO_CAP)
    if killed > 0:
        return KD_RATIO_CAP
    return 1.0


def parse_replay_advanced(
    file_path: str, manual_winner_team: Optional[int] = None
) -> AdvancedReplayData:
    """
    Parse replay and extract advanced player metrics.

    Args:
        file_path: Path to .SC2Replay file
        manual_winner_team: Optional manual winner determination (1 or 2).
                           If provided, skips automatic winner determination.

    Returns:
        AdvancedReplayData with detailed metrics

    Raises:
        ReplayParseError: If parsing fails
        WinnerDeterminationError: If winner cannot be determined automatically
    """
    try:
        # Get basic replay data
        basic_data = parse_replay(file_path, manual_winner_team=manual_winner_team)

        # Load replay with full detail level
        replay = sc2reader.load_replay(file_path, load_level=4)  # type: ignore

        # Initialize metrics for each player
        player_metrics_dict = {}

        for player in replay.players:
            is_ai = not getattr(player, "is_human", False)
            difficulty = getattr(player, "difficulty", None) if is_ai else None

            p_name = (
                player.name.replace(f"[{player.clan_tag}]", "").strip()
                if hasattr(player, "clan_tag") and player.clan_tag
                else player.name
            )
            if is_ai and difficulty:
                p_name = f"Computer ({difficulty})"

            metrics = PlayerMetrics(
                player_name=p_name,
                race=player.play_race,
                team=player.team_id,
                won=player.result == "Win",
                is_ai=is_ai,
                difficulty=difficulty,
            )

            # Extract statistics if available
            if hasattr(player, "stats"):
                stats = player.stats

                # Economic stats
                if hasattr(stats, "minerals_collection_rate"):
                    metrics.minerals_collected = (
                        int(stats.minerals_collection_rate[-1])
                        if stats.minerals_collection_rate
                        else 0
                    )
                if hasattr(stats, "vespene_collection_rate"):
                    metrics.vespene_collected = (
                        int(stats.vespene_collection_rate[-1])
                        if stats.vespene_collection_rate
                        else 0
                    )

                metrics.total_resources_collected = (
                    metrics.minerals_collected + metrics.vespene_collected
                )

                # Army stats
                if hasattr(stats, "units_trained"):
                    metrics.units_trained = (
                        len(stats.units_trained) if stats.units_trained else 0
                    )
                if hasattr(stats, "killed_unit_count"):
                    metrics.units_killed = stats.killed_unit_count

                # Workers
                if hasattr(stats, "workers_active_count"):
                    metrics.workers_created = (
                        max(stats.workers_active_count)
                        if stats.workers_active_count
                        else 0
                    )

            # APM
            if hasattr(player, "avg_apm"):
                metrics.apm = player.avg_apm

            player_metrics_dict[player.pid] = metrics

        # Process tracker events for detailed metrics
        if hasattr(replay, "tracker_events"):
            _process_tracker_events(
                replay.tracker_events, player_metrics_dict, replay.game_length.seconds
            )

        # Extract damage timelines for each player
        for player_id, metrics in player_metrics_dict.items():
            damage_timeline = DamageTimelineExtractor.extract_from_replay(
                replay, player_id
            )
            metrics.damage_timeline = damage_timeline

            # Update timing metrics from timeline
            first_damage = damage_timeline.get_first_damage_second()
            if first_damage is not None:
                metrics.first_damage_timing = first_damage

            # Calculate game phase damage
            metrics.early_game_damage = damage_timeline.get_window_damage(
                0, 300
            )  # 0-5 minutes
            metrics.mid_game_damage = damage_timeline.get_window_damage(
                300, 900
            )  # 5-15 minutes
            metrics.late_game_damage = damage_timeline.get_window_damage(
                900, 99999
            )  # 15+ minutes

            # Calculate aggression score based on early damage
            total_damage = metrics.damage_dealt
            if total_damage > 0:
                early_damage_ratio = metrics.early_game_damage / total_damage
                metrics.aggression_score = min(
                    100, early_damage_ratio * 200
                )  # Scale to 0-100

        # Detect team engagements (where 3+ players are fighting)
        player_metrics_list = list(player_metrics_dict.values())
        team_engagements = _detect_team_engagements(player_metrics_list)

        # Calculate team fight metrics for each player
        for metrics in player_metrics_list:
            _calculate_team_fight_metrics(metrics, team_engagements)

        # Calculate impact scores
        for metrics in player_metrics_dict.values():
            _calculate_impact_scores(metrics)

        # Convert to list
        player_metrics = list(player_metrics_dict.values())

        # Calculate team aggregates
        team_1_damage = sum(m.damage_dealt for m in player_metrics if m.team == 1)
        team_2_damage = sum(m.damage_dealt for m in player_metrics if m.team == 2)
        team_1_resources = sum(
            m.total_resources_collected for m in player_metrics if m.team == 1
        )
        team_2_resources = sum(
            m.total_resources_collected for m in player_metrics if m.team == 2
        )

        return AdvancedReplayData(
            basic_data=basic_data,
            player_metrics=player_metrics,
            game_duration_seconds=replay.game_length.seconds,
            team_1_total_damage=team_1_damage,
            team_2_total_damage=team_2_damage,
            team_1_total_resources=team_1_resources,
            team_2_total_resources=team_2_resources,
        )

    except (ReplayParseError, WinnerDeterminationError):
        # Re-raise these exceptions without wrapping
        raise
    except Exception as e:
        # Wrap all other exceptions as ReplayParseError
        # Log the full traceback to see where the error actually occurred
        import traceback

        logger.error(f"❌ Exception during advanced replay parsing: {str(e)}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise ReplayParseError(f"Failed to parse advanced replay data: {str(e)}") from e


def _process_tracker_events(events: List, player_metrics: Dict, game_duration: int):
    """
    Process tracker events to extract detailed metrics.

    Args:
        events: List of tracker events
        player_metrics: Dictionary of player metrics to update
        game_duration: Game duration in seconds
    """
    # Log sc2reader version and event overview for debugging
    logger.info(
        f"🔍 Processing {len(events)} tracker events. sc2reader version: {sc2reader.__version__ if hasattr(sc2reader, '__version__') else 'unknown'}"
    )

    # Count event types for diagnostic purposes
    event_types = {}
    for event in events:
        event_types[event.name] = event_types.get(event.name, 0) + 1
    logger.info(f"🔍 Event type distribution: {event_types}")

    unit_born_count = {}
    unit_died_count = {}
    unit_compositions = {}
    base_timings = {}

    for event in events:
        # Unit born events
        if event.name == "UnitBornEvent":
            pid = event.control_pid
            if pid in player_metrics:
                # Try to get unit type name from various possible attributes
                try:
                    unit_name = (
                        getattr(event, "unit_type_name", None)
                        or getattr(event, "unit_type", None)
                        or getattr(getattr(event, "unit", None), "name", None)
                        or "Unknown"
                    )
                except AttributeError as e:
                    logger.warning(
                        f"⚠️ AttributeError getting unit type from UnitBornEvent: {e}"
                    )
                    unit_name = "Unknown"

                if unit_name == "Unknown":
                    # Debug logging: show what attributes are actually available
                    logger.info(
                        f"🔍 UnitBornEvent with unknown unit type. Available attributes: {dir(event)}"
                    )
                    logger.info(
                        f"  event.__dict__: {event.__dict__ if hasattr(event, '__dict__') else 'N/A'}"
                    )
                    if hasattr(event, "unit"):
                        logger.info(f"  event.unit type: {type(event.unit)}")
                        logger.info(
                            f"  event.unit.__dict__: {event.unit.__dict__ if hasattr(event.unit, '__dict__') else 'N/A'}"
                        )
                    # Skip if we can't determine the unit type
                    continue

                # Track unit composition
                if pid not in unit_compositions:
                    unit_compositions[pid] = {}
                unit_compositions[pid][unit_name] = (
                    unit_compositions[pid].get(unit_name, 0) + 1
                )

                # Track workers
                if unit_name in ["SCV", "Probe", "Drone"]:
                    player_metrics[pid].workers_created += 1

                # Track bases for expansion timing
                if unit_name in ["CommandCenter", "Nexus", "Hatchery"]:
                    player_metrics[pid].bases_created += 1
                    if (
                        player_metrics[pid].first_expansion_timing is None
                        and player_metrics[pid].bases_created == 2
                    ):
                        player_metrics[pid].first_expansion_timing = event.second

        # Unit died events
        elif event.name == "UnitDiedEvent":
            # Try to get unit type name from various possible attributes
            try:
                unit_name = (
                    getattr(event, "unit_type_name", None)
                    or getattr(event, "unit_type", None)
                    or getattr(getattr(event, "unit", None), "name", None)
                    or "Unknown"
                )
            except AttributeError as e:
                logger.warning(
                    f"⚠️ AttributeError getting unit type from UnitDiedEvent: {e}"
                )
                unit_name = "Unknown"

            if unit_name == "Unknown":
                # Debug logging: show what attributes are actually available
                logger.info(
                    f"🔍 UnitDiedEvent with unknown unit type. Available attributes: {dir(event)}"
                )
                logger.info(
                    f"  event.__dict__: {event.__dict__ if hasattr(event, '__dict__') else 'N/A'}"
                )
                if hasattr(event, "unit"):
                    logger.info(f"  event.unit type: {type(event.unit)}")
                    logger.info(
                        f"  event.unit.__dict__: {event.unit.__dict__ if hasattr(event.unit, '__dict__') else 'N/A'}"
                    )
                # Skip if we can't determine the unit type
                continue

            unit_cost = get_unit_cost(unit_name)

            if hasattr(event, "killer_pid") and event.killer_pid in player_metrics:
                killer_pid = event.killer_pid
                # Killer gains credit
                player_metrics[killer_pid].army_value_killed += unit_cost
                player_metrics[killer_pid].units_killed += 1

            # DAMAGE TAKEN (owner tracking)
            # Note: UnitDiedEvent doesn't have unit_pid, we need to access event.unit.owner
            if event.unit and hasattr(event.unit, "owner"):
                owner = event.unit.owner
                if hasattr(owner, "pid") and owner.pid in player_metrics:
                    owner_pid = owner.pid
                    player_metrics[owner_pid].army_value_lost += unit_cost
                    player_metrics[owner_pid].units_lost += 1

        # Upgrade complete events could be tracked here
        # elif event.name == 'UpgradeCompleteEvent':
        #     pass

        # PlayerStatsEvent - contains resource collection, army values, workers
        elif event.name == "PlayerStatsEvent":
            pid = event.pid
            if pid in player_metrics:
                # These events are cumulative; keep updating to get the final values
                # Resource collection
                player_metrics[pid].minerals_collected = getattr(
                    event, "minerals_collection_rate", 0
                )
                player_metrics[pid].vespene_collected = getattr(
                    event, "vespene_collection_rate", 0
                )
                player_metrics[pid].total_resources_collected = (
                    player_metrics[pid].minerals_collected
                    + player_metrics[pid].vespene_collected
                )

                # Army value lost (from PlayerStatsEvent is more accurate than UnitDiedEvent)
                minerals_lost = getattr(event, "minerals_lost_army", 0)
                vespene_lost = getattr(event, "vespene_lost_army", 0)
                player_metrics[pid].army_value_lost = minerals_lost + vespene_lost

                # Army value killed
                minerals_killed = getattr(event, "minerals_killed_army", 0)
                vespene_killed = getattr(event, "vespene_killed_army", 0)
                player_metrics[pid].army_value_killed = minerals_killed + vespene_killed

                # Units lost count from resources (divide by avg unit cost ~100)
                if player_metrics[pid].units_lost == 0 and minerals_lost > 0:
                    player_metrics[pid].units_lost = max(1, minerals_lost // 100)

                # Workers active
                workers = getattr(event, "workers_active_count", 0)
                if workers > player_metrics[pid].workers_created:
                    player_metrics[pid].workers_created = workers

    # Set unit compositions (top 5 units)
    for pid, composition in unit_compositions.items():
        if pid in player_metrics:
            # Sort by count and take top 5
            sorted_units = sorted(
                composition.items(), key=lambda x: x[1], reverse=True
            )[:5]
            player_metrics[pid].unit_composition = dict(sorted_units)

    # Calculate derived metrics
    for metrics in player_metrics.values():
        # Damage approximations (since true damage not always available)
        # Use army value killed as proxy for damage dealt
        metrics.damage_dealt = metrics.army_value_killed
        metrics.damage_taken = metrics.army_value_lost

        # Calculate damage ratio - handle edge cases
        if metrics.damage_taken > 0:
            metrics.damage_ratio = metrics.damage_dealt / metrics.damage_taken
        elif metrics.damage_dealt > 0:
            # Dealt damage but took none - cap at 10 to prevent score inflation
            metrics.damage_ratio = 10.0
        else:
            # No damage dealt or taken - neutral ratio
            metrics.damage_ratio = 1.0

        # Kill/Death ratio - unit counts killed vs lost, capped uniformly.
        metrics.kill_death_ratio = compute_kill_death_ratio(
            metrics.units_killed, metrics.units_lost
        )

        # Spending efficiency (how much of collected resources were spent)
        # Approximate as: units built * avg cost
        if metrics.total_resources_collected > 0:
            estimated_spending = metrics.army_value_killed + metrics.army_value_lost
            metrics.resources_spent = estimated_spending
            metrics.spending_efficiency = min(
                1.0, estimated_spending / metrics.total_resources_collected
            )


@dataclass
class TeamEngagement:
    """Represents a team fight where multiple players are active."""

    start_second: int
    end_second: int
    players_involved: List[str]  # Player names
    total_damage: int


def _detect_team_engagements(
    all_player_metrics: List[PlayerMetrics],
    damage_threshold: int = 1000,  # Min damage to count as engagement
    time_window: int = 10,  # Seconds for grouping damage
) -> List[TeamEngagement]:
    """
    Detect team engagements where multiple players (3+) are dealing damage.

    Args:
        all_player_metrics: All players' metrics with damage timelines
        damage_threshold: Minimum total damage to consider an engagement
        time_window: Window in seconds for grouping damage events

    Returns:
        List of detected team engagements
    """
    engagements = []

    # Get all damage timelines
    timelines = {
        m.player_name: m.damage_timeline
        for m in all_player_metrics
        if m.damage_timeline
    }

    if len(timelines) < 3:
        return []  # Need at least 3 players for team fights

    # Find all seconds where damage occurred
    all_seconds = set()
    for timeline in timelines.values():
        all_seconds.update(timeline.damage_events.keys())

    # Group consecutive seconds into engagement windows
    sorted_seconds = sorted(all_seconds)
    current_engagement = []

    for i, second in enumerate(sorted_seconds):
        if not current_engagement or second - current_engagement[-1] <= time_window:
            current_engagement.append(second)
        else:
            # Process current engagement
            if len(current_engagement) >= 3:  # At least 3 seconds of fighting
                _process_engagement_window(
                    current_engagement, timelines, engagements, damage_threshold
                )
            current_engagement = [second]

    # Process final engagement
    if len(current_engagement) >= 3:
        _process_engagement_window(
            current_engagement, timelines, engagements, damage_threshold
        )

    return engagements


def _process_engagement_window(
    seconds: List[int],
    timelines: Dict[str, "DamageTimeline"],
    engagements: List[TeamEngagement],
    damage_threshold: int,
):
    """Process a window of seconds to detect team engagement."""
    start_second = seconds[0]
    end_second = seconds[-1]

    # Count players who dealt damage in this window
    players_active = []
    total_damage = 0

    for player_name, timeline in timelines.items():
        player_damage = timeline.get_window_damage(start_second, end_second + 1)
        if player_damage > 0:
            players_active.append(player_name)
            total_damage += player_damage

    # Team fight requires 3+ players and minimum damage
    if len(players_active) >= 3 and total_damage >= damage_threshold:
        engagements.append(
            TeamEngagement(
                start_second=start_second,
                end_second=end_second,
                players_involved=players_active,
                total_damage=total_damage,
            )
        )


def _calculate_team_fight_metrics(
    metrics: PlayerMetrics, engagements: List[TeamEngagement]
):
    """
    Calculate team fight participation metrics for a player.

    Args:
        metrics: PlayerMetrics to update
        engagements: List of detected team engagements
    """
    if not engagements or not metrics.damage_timeline:
        metrics.team_fight_participation = 0.0
        metrics.team_fight_damage = 0
        metrics.team_fight_damage_ratio = 0.0
        return

    # Calculate participation
    fights_participated = 0
    total_team_fight_damage = 0

    for engagement in engagements:
        player_damage = metrics.damage_timeline.get_window_damage(
            engagement.start_second, engagement.end_second + 1
        )

        if player_damage > 0:
            fights_participated += 1
            total_team_fight_damage += player_damage

    # Update metrics
    metrics.team_fight_participation = (
        fights_participated / len(engagements) if engagements else 0.0
    )
    metrics.team_fight_damage = total_team_fight_damage
    metrics.team_fight_damage_ratio = (
        total_team_fight_damage / metrics.damage_dealt
        if metrics.damage_dealt > 0
        else 0.0
    )


def _calculate_impact_scores(metrics: PlayerMetrics):
    """
    Calculate impact scores for a player.

    Impact is measured across multiple dimensions:
    - Economic: resource collection, workers, spending efficiency
    - Combat: army value killed, damage ratio (how efficiently you trade)
    - Efficiency: unit kill/death ratio (micro/army control)
    - Team contribution: engagement participation, team fight effectiveness

    Each intermediate score uses DISTINCT raw metrics to avoid double-counting.
    Overall impact weights these scores for team game context.

    Args:
        metrics: PlayerMetrics to calculate scores for
    """
    # ==========================================================================
    # ECONOMIC SCORE (0-100) - Resource management
    # Metrics: total_resources_collected, workers_created, spending_efficiency
    # ==========================================================================
    resource_score = min(100, metrics.total_resources_collected / 1000)  # Cap at 100k
    worker_score = min(100, metrics.workers_created / 0.8)  # Cap at 80 workers
    spending_score = metrics.spending_efficiency * 100  # 0-100 from 0-1.0

    metrics.economic_score = (resource_score + worker_score + spending_score) / 3

    # ==========================================================================
    # COMBAT SCORE (0-100) - Combat effectiveness
    # Metrics: army_value_killed, damage_ratio
    # Note: damage_dealt == army_value_killed, so we use only army_value_killed
    # ==========================================================================
    capped_ratio = min(metrics.damage_ratio, 10.0)  # Cap to prevent outliers
    kill_value_score = min(100, metrics.army_value_killed / 500)  # Cap at 50k value
    ratio_score = min(100, capped_ratio * 10)  # 10:1 ratio = 100 points

    metrics.combat_score = (kill_value_score + ratio_score) / 2

    # ==========================================================================
    # EFFICIENCY SCORE (0-100) - Resource conversion efficiency
    # Metrics: spending_efficiency (how much of collected resources were used)
    # This is DISTINCT from combat which measures killing, and economic which measures collection
    # ==========================================================================
    # Spending efficiency: what % of resources collected were converted to army/units
    spending_score = min(100, metrics.spending_efficiency * 100)

    # APM efficiency: higher APM generally means more efficient play (capped at 150 APM = 100 pts)
    apm_score = min(100, (metrics.apm / 150) * 100) if metrics.apm > 0 else 50

    metrics.efficiency_score = (spending_score + apm_score) / 2

    # ==========================================================================
    # TEAM CONTRIBUTION SCORE (0-100) - Teamwork in team fights
    # Metrics: team_fight_participation, team_fight_damage_ratio
    # ==========================================================================
    participation_score = min(100, metrics.team_fight_participation * 100)
    # Cap effectiveness at 100 (ratio > 1 means data mismatch between sources)
    team_fight_effectiveness_score = min(100, metrics.team_fight_damage_ratio * 100)
    team_contribution_score = (participation_score + team_fight_effectiveness_score) / 2

    # ==========================================================================
    # OVERALL IMPACT - Weighted combination optimized for team games
    # Weights: Combat 35%, Team 35%, Economic 20%, Efficiency 10%
    # ==========================================================================
    metrics.overall_impact = (
        metrics.combat_score * 0.35  # Combat effectiveness
        + team_contribution_score * 0.35  # Team fight participation critical
        + metrics.economic_score * 0.20  # Economy matters but less in team games
        + metrics.efficiency_score * 0.10  # Unit trading efficiency
    )


def calculate_player_synergy(
    player1_metrics: List[PlayerMetrics], player2_metrics: List[PlayerMetrics]
) -> float:
    """
    Calculate synergy score between two players based on their performance together.

    Synergy is measured by:
    - Win rate when playing together
    - Complementary roles (one economic, one combat)
    - Consistent performance

    Args:
        player1_metrics: List of metrics for player 1 (games together)
        player2_metrics: List of metrics for player 2 (games together)

    Returns:
        Synergy score (0-100)
    """
    if (
        not player1_metrics
        or not player2_metrics
        or len(player1_metrics) != len(player2_metrics)
    ):
        return 50.0  # Neutral synergy

    # Win rate together
    wins = sum(1 for m in player1_metrics if m.won)
    win_rate = wins / len(player1_metrics)
    win_rate_score = win_rate * 100

    # Role complementarity
    # Check if players have different strengths (economic vs combat)
    avg_econ_diff = abs(
        sum(m.economic_score for m in player1_metrics) / len(player1_metrics)
        - sum(m.economic_score for m in player2_metrics) / len(player2_metrics)
    )
    avg_combat_diff = abs(
        sum(m.combat_score for m in player1_metrics) / len(player1_metrics)
        - sum(m.combat_score for m in player2_metrics) / len(player2_metrics)
    )

    # Higher difference in roles = better synergy (specialization)
    role_complementarity = (avg_econ_diff + avg_combat_diff) / 2
    role_score = min(100, role_complementarity)

    # Performance consistency
    # Lower variance in combined impact = better synergy
    combined_impacts = [
        m1.overall_impact + m2.overall_impact
        for m1, m2 in zip(player1_metrics, player2_metrics)
    ]
    avg_combined = sum(combined_impacts) / len(combined_impacts)
    variance = sum((x - avg_combined) ** 2 for x in combined_impacts) / len(
        combined_impacts
    )
    consistency_score = max(0, 100 - variance / 10)

    # Overall synergy (weighted)
    synergy = (
        win_rate_score * 0.6  # Win rate is most important
        + role_score * 0.2
        + consistency_score * 0.2
    )

    return synergy
