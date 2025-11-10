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
import sc2reader
from sc2reader.events import TrackerEvent

from .replay_parser import parse_replay, ReplayData, ReplayParseError
from .damage_timeline import DamageTimelineExtractor, DamageTimeline


@dataclass
class PlayerMetrics:
    """Detailed player performance metrics."""
    player_name: str
    race: str
    team: int
    won: bool

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

    # Timing metrics (in game seconds)
    first_expansion_timing: Optional[int] = None
    first_army_timing: Optional[int] = None  # When 8+ army supply
    bases_created: int = 0

    # Mechanics
    apm: float = 0.0

    # Unit composition (top 5 units by count)
    unit_composition: Dict[str, int] = None

    # Impact scores (calculated)
    economic_score: float = 0.0
    combat_score: float = 0.0
    efficiency_score: float = 0.0
    overall_impact: float = 0.0

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
    'Marine': 50, 'Marauder': 100, 'Reaper': 50, 'Ghost': 200,
    'Hellion': 100, 'Hellbat': 100, 'WidowMine': 75, 'SiegeTank': 150,
    'Thor': 300, 'Viking': 150, 'Medivac': 100, 'Liberator': 150,
    'Raven': 100, 'Banshee': 150, 'Battlecruiser': 400,
    'SCV': 50,

    # Protoss
    'Probe': 50, 'Zealot': 100, 'Stalker': 125, 'Sentry': 50,
    'Adept': 100, 'HighTemplar': 50, 'DarkTemplar': 125,
    'Immortal': 275, 'Colossus': 300, 'Disruptor': 150,
    'Observer': 25, 'WarpPrism': 200, 'Phoenix': 150,
    'VoidRay': 250, 'Oracle': 150, 'Tempest': 300,
    'Carrier': 350, 'Mothership': 400, 'Archon': 0,  # Created from merging

    # Zerg
    'Drone': 50, 'Zergling': 25, 'Baneling': 25, 'Roach': 75,
    'Ravager': 100, 'Hydralisk': 100, 'Lurker': 150, 'Infestor': 100,
    'SwarmHost': 100, 'Ultralisk': 300, 'Queen': 150,
    'Overlord': 100, 'Overseer': 50, 'Mutalisk': 100,
    'Corruptor': 150, 'BroodLord': 150, 'Viper': 100,

    # Buildings (for damage tracking)
    'CommandCenter': 400, 'Nexus': 400, 'Hatchery': 300,
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


def parse_replay_advanced(file_path: str) -> AdvancedReplayData:
    """
    Parse replay and extract advanced player metrics.

    Args:
        file_path: Path to .SC2Replay file

    Returns:
        AdvancedReplayData with detailed metrics

    Raises:
        ReplayParseError: If parsing fails
    """
    try:
        # Get basic replay data
        basic_data = parse_replay(file_path)

        # Load replay with full detail level
        replay = sc2reader.load_replay(file_path, load_level=4)

        # Initialize metrics for each player
        player_metrics_dict = {}

        for player in replay.players:
            if not player.is_human:
                continue

            metrics = PlayerMetrics(
                player_name=player.name.replace(f"[{player.clan_tag}]", "").strip() if hasattr(player, 'clan_tag') and player.clan_tag else player.name,
                race=player.play_race,
                team=player.team_id,
                won=player.result == "Win"
            )

            # Extract statistics if available
            if hasattr(player, 'stats'):
                stats = player.stats

                # Economic stats
                if hasattr(stats, 'minerals_collection_rate'):
                    metrics.minerals_collected = int(stats.minerals_collection_rate[-1]) if stats.minerals_collection_rate else 0
                if hasattr(stats, 'vespene_collection_rate'):
                    metrics.vespene_collected = int(stats.vespene_collection_rate[-1]) if stats.vespene_collection_rate else 0

                metrics.total_resources_collected = metrics.minerals_collected + metrics.vespene_collected

                # Army stats
                if hasattr(stats, 'units_trained'):
                    metrics.units_trained = len(stats.units_trained) if stats.units_trained else 0
                if hasattr(stats, 'killed_unit_count'):
                    metrics.units_killed = stats.killed_unit_count

                # Workers
                if hasattr(stats, 'workers_active_count'):
                    metrics.workers_created = max(stats.workers_active_count) if stats.workers_active_count else 0

            # APM
            if hasattr(player, 'avg_apm'):
                metrics.apm = player.avg_apm

            player_metrics_dict[player.pid] = metrics

        # Process tracker events for detailed metrics
        if hasattr(replay, 'tracker_events'):
            _process_tracker_events(replay.tracker_events, player_metrics_dict, replay.game_length.seconds)

        # Extract damage timelines for each player
        for player_id, metrics in player_metrics_dict.items():
            damage_timeline = DamageTimelineExtractor.extract_from_replay(replay, player_id)
            metrics.damage_timeline = damage_timeline

            # Update timing metrics from timeline
            first_damage = damage_timeline.get_first_damage_second()
            if first_damage is not None:
                metrics.first_damage_timing = first_damage

        # Calculate impact scores
        for metrics in player_metrics_dict.values():
            _calculate_impact_scores(metrics)

        # Convert to list
        player_metrics = list(player_metrics_dict.values())

        # Calculate team aggregates
        team_1_damage = sum(m.damage_dealt for m in player_metrics if m.team == 1)
        team_2_damage = sum(m.damage_dealt for m in player_metrics if m.team == 2)
        team_1_resources = sum(m.total_resources_collected for m in player_metrics if m.team == 1)
        team_2_resources = sum(m.total_resources_collected for m in player_metrics if m.team == 2)

        return AdvancedReplayData(
            basic_data=basic_data,
            player_metrics=player_metrics,
            game_duration_seconds=replay.game_length.seconds,
            team_1_total_damage=team_1_damage,
            team_2_total_damage=team_2_damage,
            team_1_total_resources=team_1_resources,
            team_2_total_resources=team_2_resources
        )

    except ReplayParseError:
        raise
    except Exception as e:
        raise ReplayParseError(f"Failed to parse advanced replay data: {str(e)}") from e


def _process_tracker_events(events: List, player_metrics: Dict, game_duration: int):
    """
    Process tracker events to extract detailed metrics.

    Args:
        events: List of tracker events
        player_metrics: Dictionary of player metrics to update
        game_duration: Game duration in seconds
    """
    unit_born_count = {}
    unit_died_count = {}
    unit_compositions = {}
    base_timings = {}

    for event in events:
        # Unit born events
        if event.name == 'UnitBornEvent':
            pid = event.control_pid
            if pid in player_metrics:
                unit_name = event.unit_type_name

                # Track unit composition
                if pid not in unit_compositions:
                    unit_compositions[pid] = {}
                unit_compositions[pid][unit_name] = unit_compositions[pid].get(unit_name, 0) + 1

                # Track workers
                if unit_name in ['SCV', 'Probe', 'Drone']:
                    player_metrics[pid].workers_created += 1

                # Track bases for expansion timing
                if unit_name in ['CommandCenter', 'Nexus', 'Hatchery']:
                    player_metrics[pid].bases_created += 1
                    if player_metrics[pid].first_expansion_timing is None and player_metrics[pid].bases_created == 2:
                        player_metrics[pid].first_expansion_timing = event.second

        # Unit died events
        elif event.name == 'UnitDiedEvent':
            if hasattr(event, 'killer_pid') and event.killer_pid in player_metrics:
                killer_pid = event.killer_pid
                unit_name = event.unit_type_name
                unit_cost = get_unit_cost(unit_name)

                # Killer gains credit
                player_metrics[killer_pid].army_value_killed += unit_cost
                player_metrics[killer_pid].units_killed += 1

            # Unit owner loses value
            if hasattr(event, 'unit_pid') and event.unit_pid in player_metrics:
                owner_pid = event.unit_pid
                unit_name = event.unit_type_name
                unit_cost = get_unit_cost(unit_name)

                player_metrics[owner_pid].army_value_lost += unit_cost
                player_metrics[owner_pid].units_lost += 1

        # Upgrade complete events could be tracked here
        # elif event.name == 'UpgradeCompleteEvent':
        #     pass

    # Set unit compositions (top 5 units)
    for pid, composition in unit_compositions.items():
        if pid in player_metrics:
            # Sort by count and take top 5
            sorted_units = sorted(composition.items(), key=lambda x: x[1], reverse=True)[:5]
            player_metrics[pid].unit_composition = dict(sorted_units)

    # Calculate derived metrics
    for metrics in player_metrics.values():
        # Damage approximations (since true damage not always available)
        # Use army value killed as proxy for damage dealt
        metrics.damage_dealt = metrics.army_value_killed
        metrics.damage_taken = metrics.army_value_lost

        if metrics.damage_taken > 0:
            metrics.damage_ratio = metrics.damage_dealt / metrics.damage_taken

        # Spending efficiency (how much of collected resources were spent)
        # Approximate as: units built * avg cost
        if metrics.total_resources_collected > 0:
            estimated_spending = metrics.army_value_killed + metrics.army_value_lost
            metrics.resources_spent = estimated_spending
            metrics.spending_efficiency = min(1.0, estimated_spending / metrics.total_resources_collected)


def _calculate_impact_scores(metrics: PlayerMetrics):
    """
    Calculate impact scores for a player.

    Impact is measured across multiple dimensions:
    - Economic: resource collection, workers, spending
    - Combat: damage dealt, efficiency, kills
    - Efficiency: ratios and per-minute metrics

    Args:
        metrics: PlayerMetrics to calculate scores for
    """
    # Economic score (0-100)
    # Based on resources collected, workers, and spending
    resource_score = min(100, metrics.total_resources_collected / 1000)  # Cap at 100k resources
    worker_score = min(100, metrics.workers_created / 0.8)  # Cap at 80 workers
    spending_score = metrics.spending_efficiency * 100

    metrics.economic_score = (resource_score + worker_score + spending_score) / 3

    # Combat score (0-100)
    # Based on damage dealt, kills, and army value
    damage_score = min(100, metrics.damage_dealt / 500)  # Cap at 50k damage
    kill_score = min(100, metrics.army_value_killed / 500)  # Cap at 50k value
    ratio_score = min(100, metrics.damage_ratio * 50)  # 2:1 ratio = 100 points

    metrics.combat_score = (damage_score + kill_score + ratio_score) / 3

    # Efficiency score (0-100)
    # Based on ratios and performance per resource
    efficiency_components = [
        metrics.spending_efficiency * 100,
        metrics.damage_ratio * 50,  # Normalized to 100
        min(100, (metrics.units_killed / max(1, metrics.units_lost)) * 50)  # Kill/death ratio
    ]

    metrics.efficiency_score = sum(efficiency_components) / len(efficiency_components)

    # Overall impact (weighted average)
    # Combat is most important for team contribution
    metrics.overall_impact = (
        metrics.economic_score * 0.3 +
        metrics.combat_score * 0.5 +
        metrics.efficiency_score * 0.2
    )


def calculate_player_synergy(
    player1_metrics: List[PlayerMetrics],
    player2_metrics: List[PlayerMetrics]
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
    if not player1_metrics or not player2_metrics or len(player1_metrics) != len(player2_metrics):
        return 50.0  # Neutral synergy

    # Win rate together
    wins = sum(1 for m in player1_metrics if m.won)
    win_rate = wins / len(player1_metrics)
    win_rate_score = win_rate * 100

    # Role complementarity
    # Check if players have different strengths (economic vs combat)
    avg_econ_diff = abs(
        sum(m.economic_score for m in player1_metrics) / len(player1_metrics) -
        sum(m.economic_score for m in player2_metrics) / len(player2_metrics)
    )
    avg_combat_diff = abs(
        sum(m.combat_score for m in player1_metrics) / len(player1_metrics) -
        sum(m.combat_score for m in player2_metrics) / len(player2_metrics)
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
    variance = sum((x - avg_combined) ** 2 for x in combined_impacts) / len(combined_impacts)
    consistency_score = max(0, 100 - variance / 10)

    # Overall synergy (weighted)
    synergy = (
        win_rate_score * 0.6 +  # Win rate is most important
        role_score * 0.2 +
        consistency_score * 0.2
    )

    return synergy
