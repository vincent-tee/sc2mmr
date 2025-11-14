"""
Second-by-Second Damage Timeline Analysis

Extracts and analyzes exact damage timings from replays to identify:
- Timing attacks (when attacks happen)
- Damage spikes (big fights, all-ins)
- Attack patterns (early rush, mid-game timing, late-game)
- Player coordination (do teammates attack together?)
"""
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import json
import sc2reader


@dataclass
class DamageEvent:
    """Single damage event."""
    second: int
    damage: int
    unit_killed: str
    killer_player_id: int
    victim_player_id: int


@dataclass
class TimingAttack:
    """Detected timing attack."""
    start_second: int
    end_second: int
    peak_second: int
    total_damage: int
    peak_damage: int
    duration_seconds: int

    @property
    def start_time_display(self) -> str:
        """Display time as MM:SS."""
        minutes = self.start_second // 60
        seconds = self.start_second % 60
        return f"{minutes}:{seconds:02d}"

    @property
    def peak_time_display(self) -> str:
        """Display peak time as MM:SS."""
        minutes = self.peak_second // 60
        seconds = self.peak_second % 60
        return f"{minutes}:{seconds:02d}"


@dataclass
class DamageSpike:
    """Single-second damage spike."""
    second: int
    damage: int

    @property
    def time_display(self) -> str:
        """Display time as MM:SS."""
        minutes = self.second // 60
        seconds = self.second % 60
        return f"{minutes}:{seconds:02d}"


class DamageTimeline:
    """
    Sparse damage timeline with analysis methods.

    Stores only seconds where damage occurred for efficiency.
    """

    def __init__(self, damage_events: Optional[Dict[int, int]] = None):
        """
        Initialize timeline.

        Args:
            damage_events: Dict of {second: damage_amount}
        """
        self.damage_events = damage_events or {}

    @classmethod
    def from_json(cls, json_str: str) -> 'DamageTimeline':
        """Create timeline from JSON string."""
        if not json_str:
            return cls({})
        data = json.loads(json_str)
        # Convert string keys to integers
        events = {int(k): v for k, v in data.items()}
        return cls(events)

    def to_json(self) -> str:
        """Convert timeline to JSON string."""
        return json.dumps(self.damage_events)

    def get_damage_at(self, second: int) -> int:
        """Get damage at specific second."""
        return self.damage_events.get(second, 0)

    def get_window_damage(self, start: int, end: int) -> int:
        """Get total damage in time window [start, end)."""
        return sum(
            dmg for sec, dmg in self.damage_events.items()
            if start <= sec < end
        )

    def get_total_damage(self) -> int:
        """Get total damage across all time."""
        return sum(self.damage_events.values())

    def get_first_damage_second(self) -> Optional[int]:
        """Get second when first damage occurred."""
        if not self.damage_events:
            return None
        return min(self.damage_events.keys())

    def get_peak_damage_second(self) -> Optional[Tuple[int, int]]:
        """
        Get second with highest damage.

        Returns:
            Tuple of (second, damage) or None
        """
        if not self.damage_events:
            return None
        second = max(self.damage_events.keys(), key=lambda k: self.damage_events[k])
        return (second, self.damage_events[second])

    def get_damage_spikes(self, threshold: Optional[int] = None) -> List[DamageSpike]:
        """
        Find damage spikes (seconds with unusually high damage).

        Args:
            threshold: Damage threshold. If None, uses 3x average.

        Returns:
            List of DamageSpike objects, sorted by damage descending
        """
        if not self.damage_events:
            return []

        if threshold is None:
            avg_damage = self.get_average_damage_per_active_second()
            threshold = avg_damage * 3

        spikes = [
            DamageSpike(second=sec, damage=dmg)
            for sec, dmg in self.damage_events.items()
            if dmg >= threshold
        ]

        return sorted(spikes, key=lambda s: s.damage, reverse=True)

    def get_average_damage_per_active_second(self) -> float:
        """Get average damage per second (only counting seconds with damage)."""
        if not self.damage_events:
            return 0.0
        return sum(self.damage_events.values()) / len(self.damage_events)

    def detect_timing_attacks(
        self,
        spike_threshold: Optional[int] = None,
        min_duration: int = 3,
        max_gap: int = 5
    ) -> List[TimingAttack]:
        """
        Detect timing attacks (sustained damage periods).

        Args:
            spike_threshold: Minimum damage to consider (default: 2x average)
            min_duration: Minimum duration in seconds
            max_gap: Maximum gap between damage events in same attack

        Returns:
            List of TimingAttack objects
        """
        if not self.damage_events:
            return []

        if spike_threshold is None:
            avg_damage = self.get_average_damage_per_active_second()
            spike_threshold = avg_damage * 2

        # Sort damage events by time
        sorted_events = sorted(self.damage_events.items())

        attacks = []
        current_attack = None

        for second, damage in sorted_events:
            if damage >= spike_threshold:
                if current_attack is None:
                    # Start new attack
                    current_attack = {
                        'start': second,
                        'end': second,
                        'peak_second': second,
                        'peak_damage': damage,
                        'total_damage': damage,
                        'last_second': second
                    }
                elif second - current_attack['last_second'] <= max_gap:
                    # Continue current attack
                    current_attack['end'] = second
                    current_attack['total_damage'] += damage
                    current_attack['last_second'] = second

                    if damage > current_attack['peak_damage']:
                        current_attack['peak_second'] = second
                        current_attack['peak_damage'] = damage
                else:
                    # Gap too large, finish current attack and start new one
                    duration = current_attack['end'] - current_attack['start'] + 1
                    if duration >= min_duration:
                        attacks.append(TimingAttack(
                            start_second=current_attack['start'],
                            end_second=current_attack['end'],
                            peak_second=current_attack['peak_second'],
                            total_damage=current_attack['total_damage'],
                            peak_damage=current_attack['peak_damage'],
                            duration_seconds=duration
                        ))

                    # Start new attack
                    current_attack = {
                        'start': second,
                        'end': second,
                        'peak_second': second,
                        'peak_damage': damage,
                        'total_damage': damage,
                        'last_second': second
                    }

        # Finish last attack if exists
        if current_attack:
            duration = current_attack['end'] - current_attack['start'] + 1
            if duration >= min_duration:
                attacks.append(TimingAttack(
                    start_second=current_attack['start'],
                    end_second=current_attack['end'],
                    peak_second=current_attack['peak_second'],
                    total_damage=current_attack['total_damage'],
                    peak_damage=current_attack['peak_damage'],
                    duration_seconds=duration
                ))

        return sorted(attacks, key=lambda a: a.total_damage, reverse=True)

    def get_damage_distribution(self) -> Dict[str, int]:
        """
        Get damage distribution across game phases.

        Returns:
            Dict with 'early', 'mid', 'late' damage totals
        """
        return {
            'early': self.get_window_damage(0, 300),      # 0-5 min
            'mid': self.get_window_damage(300, 600),      # 5-10 min
            'late': self.get_window_damage(600, 9999)     # 10+ min
        }

    def get_activity_periods(self, min_damage: int = 100, max_gap: int = 30) -> List[Tuple[int, int]]:
        """
        Find periods of sustained activity.

        Args:
            min_damage: Minimum damage to consider active
            max_gap: Maximum gap between events in same period

        Returns:
            List of (start_second, end_second) tuples
        """
        if not self.damage_events:
            return []

        sorted_events = sorted(
            [(sec, dmg) for sec, dmg in self.damage_events.items() if dmg >= min_damage]
        )

        if not sorted_events:
            return []

        periods = []
        period_start = sorted_events[0][0]
        period_end = sorted_events[0][0]

        for second, damage in sorted_events[1:]:
            if second - period_end <= max_gap:
                period_end = second
            else:
                periods.append((period_start, period_end))
                period_start = second
                period_end = second

        periods.append((period_start, period_end))
        return periods

    def calculate_consistency_score(self) -> float:
        """
        Calculate how consistent damage output is.

        Returns:
            Score 0-100 (100 = perfectly consistent)
        """
        if len(self.damage_events) < 5:
            return 50.0  # Not enough data

        damages = list(self.damage_events.values())
        avg_damage = sum(damages) / len(damages)

        if avg_damage == 0:
            return 50.0

        # Calculate coefficient of variation
        variance = sum((d - avg_damage) ** 2 for d in damages) / len(damages)
        std_dev = variance ** 0.5
        cv = std_dev / avg_damage

        # Convert to 0-100 score (lower CV = higher consistency)
        # CV of 0 = 100, CV of 2 = 0
        consistency = max(0, 100 - (cv * 50))
        return consistency


class DamageTimelineExtractor:
    """Extracts second-by-second damage timelines from replays."""

    @staticmethod
    def extract_from_replay(
        replay: Any,  # sc2reader.Replay object
        player_id: int
    ) -> DamageTimeline:
        """
        Extract damage timeline for a specific player.

        Args:
            replay: Loaded sc2reader Replay object (load_level >= 2)
            player_id: Player ID to extract timeline for

        Returns:
            DamageTimeline object
        """
        damage_by_second = defaultdict(int)

        if not hasattr(replay, 'tracker_events'):
            return DamageTimeline({})

        for event in replay.tracker_events:
            # Unit died events indicate damage
            if event.name == 'UnitDiedEvent':
                if hasattr(event, 'killer_pid') and event.killer_pid == player_id:
                    # Try to get unit type name from various possible attributes
                    try:
                        unit_name = getattr(event, 'unit_type_name', None) or \
                                   getattr(event, 'unit_type', None) or \
                                   getattr(getattr(event, 'unit', None), 'name', None) or \
                                   'Unknown'
                    except AttributeError:
                        unit_name = 'Unknown'

                    if unit_name == 'Unknown':
                        # Skip if we can't determine the unit type
                        continue

                    second = event.second
                    unit_cost = _get_unit_cost(unit_name)
                    damage_by_second[second] += unit_cost

        # Convert defaultdict to regular dict
        return DamageTimeline(dict(damage_by_second))

    @staticmethod
    def calculate_coordination_score(
        timeline1: DamageTimeline,
        timeline2: DamageTimeline,
        window_seconds: int = 10
    ) -> float:
        """
        Calculate how well two players coordinate attacks.

        Args:
            timeline1: First player's timeline
            timeline2: Second player's timeline
            window_seconds: Time window for coordination (default 10s)

        Returns:
            Coordination score 0-100 (100 = perfect coordination)
        """
        if not timeline1.damage_events or not timeline2.damage_events:
            return 50.0  # No data

        # Get attack moments for both players
        attacks1 = timeline1.detect_timing_attacks()
        attacks2 = timeline2.detect_timing_attacks()

        if not attacks1 or not attacks2:
            return 50.0

        # Count coordinated attacks (within window_seconds)
        coordinated = 0
        total_attacks = max(len(attacks1), len(attacks2))

        for attack1 in attacks1:
            for attack2 in attacks2:
                time_diff = abs(attack1.start_second - attack2.start_second)
                if time_diff <= window_seconds:
                    coordinated += 1
                    break

        # Coordination score
        coordination = (coordinated / total_attacks) * 100 if total_attacks > 0 else 50.0
        return min(100.0, coordination)


def _get_unit_cost(unit_name: str) -> int:
    """Get approximate resource cost for a unit."""
    # Simplified cost map (minerals + gas)
    costs = {
        # Terran
        'SCV': 50, 'Marine': 50, 'Marauder': 100, 'Reaper': 50,
        'Ghost': 200, 'Hellion': 100, 'Hellbat': 100, 'WidowMine': 75,
        'SiegeTank': 150, 'Thor': 300, 'Viking': 150, 'Medivac': 100,
        'Liberator': 150, 'Raven': 100, 'Banshee': 150, 'Battlecruiser': 400,

        # Protoss
        'Probe': 50, 'Zealot': 100, 'Stalker': 125, 'Sentry': 50,
        'Adept': 100, 'HighTemplar': 50, 'DarkTemplar': 125,
        'Immortal': 275, 'Colossus': 300, 'Disruptor': 150,
        'Observer': 25, 'WarpPrism': 200, 'Phoenix': 150,
        'VoidRay': 250, 'Oracle': 150, 'Tempest': 300,
        'Carrier': 350, 'Mothership': 400, 'Archon': 100,

        # Zerg
        'Drone': 50, 'Zergling': 25, 'Baneling': 25, 'Roach': 75,
        'Ravager': 100, 'Hydralisk': 100, 'Lurker': 150, 'Infestor': 100,
        'SwarmHost': 100, 'Ultralisk': 300, 'Queen': 150,
        'Overlord': 100, 'Overseer': 50, 'Mutalisk': 100,
        'Corruptor': 150, 'BroodLord': 150, 'Viper': 100,

        # Structures (high value for base sniping)
        'CommandCenter': 400, 'OrbitalCommand': 150, 'PlanetaryFortress': 150,
        'Nexus': 400, 'Hatchery': 300, 'Lair': 150, 'Hive': 200
    }

    return costs.get(unit_name, 100)  # Default 100 for unknown units
