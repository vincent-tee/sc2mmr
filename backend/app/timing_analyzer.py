"""
Timing Analysis for Player Archetypes

Tracks WHEN damage/events happen to identify:
- Rush/cheese players (early damage)
- Timing attack specialists (mid-game spikes)
- Late-game players (economy -> late army)
- Aggressive vs defensive playstyles
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import sc2reader


class PlayerArchetype(str, Enum):
    """Player playstyle archetype based on timing analysis."""
    RUSHER = "Rusher"  # Heavy early aggression (0-5min)
    TIMING_ATTACKER = "Timing Attacker"  # Mid-game spike (6-10min)
    LATE_GAME = "Late Game"  # Patient, strong late (12+min)
    ALL_IN = "All-In"  # Single massive attack
    BALANCED = "Balanced"  # Consistent throughout
    DEFENDER = "Defender"  # Reactive, low early damage


@dataclass
class TimingWindow:
    """Damage/actions in a specific time window."""
    start_second: int
    end_second: int
    damage_dealt: int = 0
    units_killed: int = 0
    army_value_built: int = 0
    bases_taken: int = 0


@dataclass
class TimingProfile:
    """Complete timing profile for a player."""
    player_name: str

    # Time windows (game seconds)
    early_game: TimingWindow  # 0-300s (0-5min)
    mid_game: TimingWindow    # 300-600s (5-10min)
    late_game: TimingWindow   # 600+ (10+min)

    # Key timings
    first_damage_timing: Optional[int] = None  # When first kill
    first_expansion_timing: Optional[int] = None
    peak_damage_window: Optional[str] = None  # "early", "mid", or "late"

    # Archetype
    archetype: Optional[PlayerArchetype] = None
    aggression_score: float = 0.0  # 0-100, higher = more aggressive

    def __post_init__(self):
        """Calculate derived metrics."""
        self._calculate_peak_damage_window()
        self._determine_archetype()

    def _calculate_peak_damage_window(self):
        """Determine when most damage was dealt."""
        windows = {
            "early": self.early_game.damage_dealt,
            "mid": self.mid_game.damage_dealt,
            "late": self.late_game.damage_dealt
        }
        self.peak_damage_window = max(windows, key=windows.get)

    def _determine_archetype(self):
        """Determine player archetype from timing data."""
        early_dmg = self.early_game.damage_dealt
        mid_dmg = self.mid_game.damage_dealt
        late_dmg = self.late_game.damage_dealt
        total_dmg = early_dmg + mid_dmg + late_dmg

        if total_dmg == 0:
            self.archetype = PlayerArchetype.DEFENDER
            self.aggression_score = 20.0
            return

        # Calculate damage distribution
        early_pct = (early_dmg / total_dmg) * 100
        mid_pct = (mid_dmg / total_dmg) * 100
        late_pct = (late_dmg / total_dmg) * 100

        # Rusher: >50% damage in first 5 minutes
        if early_pct > 50 and self.first_damage_timing and self.first_damage_timing < 180:
            self.archetype = PlayerArchetype.RUSHER
            self.aggression_score = 90.0

        # Timing Attacker: >50% damage in mid-game, or sharp spike
        elif mid_pct > 50 or (mid_pct > 40 and mid_dmg > early_dmg * 2):
            self.archetype = PlayerArchetype.TIMING_ATTACKER
            self.aggression_score = 75.0

        # All-in: Single window dominates (>70%) regardless of timing
        elif max(early_pct, mid_pct, late_pct) > 70:
            self.archetype = PlayerArchetype.ALL_IN
            self.aggression_score = 85.0

        # Late game: >50% damage after 10 minutes
        elif late_pct > 50:
            self.archetype = PlayerArchetype.LATE_GAME
            self.aggression_score = 50.0

        # Balanced: Consistent damage throughout
        elif max(early_pct, mid_pct, late_pct) < 50:
            self.archetype = PlayerArchetype.BALANCED
            self.aggression_score = 65.0

        # Defender: Low overall damage
        else:
            self.archetype = PlayerArchetype.DEFENDER
            self.aggression_score = 35.0


class TimingAnalyzer:
    """Analyzes timing patterns from replay tracker events."""

    @staticmethod
    def analyze_timing(replay: Any, player_id: int) -> TimingProfile:  # replay is sc2reader.Replay object
        """
        Analyze timing patterns for a player.

        Args:
            replay: Loaded sc2reader Replay object
            player_id: Player ID to analyze

        Returns:
            TimingProfile with timing data
        """
        # Initialize time windows
        early_game = TimingWindow(start_second=0, end_second=300)
        mid_game = TimingWindow(start_second=300, end_second=600)
        late_game = TimingWindow(start_second=600, end_second=99999)

        first_damage_timing = None
        first_expansion_timing = None

        # Get player name
        player = next((p for p in replay.players if p.pid == player_id), None)
        player_name = player.name if player else "Unknown"

        # Process tracker events
        if hasattr(replay, 'tracker_events'):
            for event in replay.tracker_events:
                game_second = event.second

                # Unit died events (damage proxy)
                if event.name == 'UnitDiedEvent':
                    if hasattr(event, 'killer_pid') and event.killer_pid == player_id:
                        # This player got a kill
                        # Try to get unit type name from various possible attributes
                        try:
                            unit_name = getattr(event, 'unit_type_name', None) or \
                                       getattr(event, 'unit_type', None) or \
                                       getattr(getattr(event, 'unit', None), 'name', None) or \
                                       'Unknown'
                        except AttributeError:
                            unit_name = 'Unknown'

                        if unit_name == 'Unknown':
                            continue  # Skip if we can't determine the unit type

                        unit_cost = _get_unit_value(unit_name)

                        # Track first damage
                        if first_damage_timing is None:
                            first_damage_timing = game_second

                        # Add to appropriate window
                        if game_second < 300:
                            early_game.damage_dealt += unit_cost
                            early_game.units_killed += 1
                        elif game_second < 600:
                            mid_game.damage_dealt += unit_cost
                            mid_game.units_killed += 1
                        else:
                            late_game.damage_dealt += unit_cost
                            late_game.units_killed += 1

                # Unit born events (for expansions and army builds)
                elif event.name == 'UnitBornEvent':
                    if event.control_pid == player_id:
                        # Try to get unit type name from various possible attributes
                        try:
                            unit_name = getattr(event, 'unit_type_name', None) or \
                                       getattr(event, 'unit_type', None) or \
                                       getattr(getattr(event, 'unit', None), 'name', None) or \
                                       'Unknown'
                        except AttributeError:
                            unit_name = 'Unknown'

                        if unit_name == 'Unknown':
                            continue  # Skip if we can't determine the unit type

                        unit_cost = _get_unit_value(unit_name)

                        # Track expansions
                        if unit_name in ['CommandCenter', 'Nexus', 'Hatchery']:
                            if first_expansion_timing is None and game_second > 0:
                                # First base is at start, second is expansion
                                first_expansion_timing = game_second

                            # Count bases by window
                            if game_second < 300:
                                early_game.bases_taken += 1
                            elif game_second < 600:
                                mid_game.bases_taken += 1
                            else:
                                late_game.bases_taken += 1

                        # Track army value built
                        if not _is_worker(unit_name) and unit_cost > 50:
                            if game_second < 300:
                                early_game.army_value_built += unit_cost
                            elif game_second < 600:
                                mid_game.army_value_built += unit_cost
                            else:
                                late_game.army_value_built += unit_cost

        return TimingProfile(
            player_name=player_name,
            early_game=early_game,
            mid_game=mid_game,
            late_game=late_game,
            first_damage_timing=first_damage_timing,
            first_expansion_timing=first_expansion_timing
        )

    @staticmethod
    def calculate_timing_compatibility(
        profile1: TimingProfile,
        profile2: TimingProfile
    ) -> float:
        """
        Calculate how well two players' timings align.

        Compatible timings:
        - Both rush (coordinate early aggression)
        - One rush + one late-game (complementary)
        - Similar peak damage windows

        Args:
            profile1: First player's timing profile
            profile2: Second player's timing profile

        Returns:
            Compatibility score (0-100)
        """
        # Same archetype can be good (coordinate) or bad (compete for resources)
        archetype_score = 0.0

        if profile1.archetype == profile2.archetype:
            # Same type - coordinate well
            if profile1.archetype in [PlayerArchetype.RUSHER, PlayerArchetype.TIMING_ATTACKER]:
                archetype_score = 80.0  # Rush together = strong
            elif profile1.archetype == PlayerArchetype.LATE_GAME:
                archetype_score = 75.0  # Both macro = solid
            else:
                archetype_score = 65.0  # Balanced is fine
        else:
            # Different types - complementary
            archetypes = {profile1.archetype, profile2.archetype}

            # Rush + Late game = good (one attacks, one defends)
            if {PlayerArchetype.RUSHER, PlayerArchetype.LATE_GAME}.issubset(archetypes):
                archetype_score = 85.0

            # Timing + Late game = good (sequential pressure)
            elif {PlayerArchetype.TIMING_ATTACKER, PlayerArchetype.LATE_GAME}.issubset(archetypes):
                archetype_score = 80.0

            # Rush + Timing = good (continuous pressure)
            elif {PlayerArchetype.RUSHER, PlayerArchetype.TIMING_ATTACKER}.issubset(archetypes):
                archetype_score = 75.0

            # Any + Balanced = decent
            elif PlayerArchetype.BALANCED in archetypes:
                archetype_score = 70.0

            # Defender combos
            elif PlayerArchetype.DEFENDER in archetypes:
                # Defender + aggressive = complement
                if any(a in archetypes for a in [PlayerArchetype.RUSHER, PlayerArchetype.TIMING_ATTACKER]):
                    archetype_score = 75.0
                else:
                    archetype_score = 60.0  # Two defenders = weak

            else:
                archetype_score = 65.0

        # Peak damage window alignment
        window_score = 0.0
        if profile1.peak_damage_window == profile2.peak_damage_window:
            window_score = 80.0  # Attack together
        else:
            window_score = 70.0  # Staggered attacks can work

        # Aggression balance
        aggression_diff = abs(profile1.aggression_score - profile2.aggression_score)
        aggression_score = max(50.0, 100.0 - aggression_diff)

        # Overall compatibility (weighted)
        compatibility = (
            archetype_score * 0.5 +
            window_score * 0.3 +
            aggression_score * 0.2
        )

        return compatibility

    @staticmethod
    def recommend_team_composition(
        profiles: List[TimingProfile],
        team_size: int
    ) -> Dict:
        """
        Recommend team composition based on timing profiles.

        Args:
            profiles: List of player timing profiles
            team_size: Size of each team

        Returns:
            Dictionary with composition recommendations
        """
        # Count archetypes
        archetype_counts = {}
        for profile in profiles:
            archetype_counts[profile.archetype] = archetype_counts.get(profile.archetype, 0) + 1

        # Ideal composition (for 3v3 example):
        # - 1 Rusher (early pressure)
        # - 1 Timing/Balanced (mid-game)
        # - 1 Late game (insurance)

        recommendations = {
            "total_players": len(profiles),
            "team_size": team_size,
            "archetype_distribution": archetype_counts,
            "recommendations": []
        }

        if team_size == 3:
            recommendations["recommendations"] = [
                "Ideal: 1 Rusher + 1 Timing/Balanced + 1 Late Game",
                "Good: 2 Rush + 1 Late (aggressive start)",
                "Safe: 1 Rush + 2 Late (conservative)",
                "Avoid: 3 Defenders (too passive)"
            ]
        elif team_size == 4:
            recommendations["recommendations"] = [
                "Ideal: 1-2 Rushers + 1-2 Timing + 1 Late Game",
                "Good: Mix of aggressive and late-game players",
                "Avoid: All one archetype"
            ]

        return recommendations


def _get_unit_value(unit_name: str) -> int:
    """Get resource cost for a unit (simplified)."""
    # Import from advanced_parser or use simplified version
    cost_map = {
        'Marine': 50, 'Marauder': 100, 'SiegeTank': 150,
        'Zealot': 100, 'Stalker': 125, 'Immortal': 275,
        'Zergling': 25, 'Roach': 75, 'Hydralisk': 100,
        'CommandCenter': 400, 'Nexus': 400, 'Hatchery': 300
    }
    return cost_map.get(unit_name, 100)


def _is_worker(unit_name: str) -> bool:
    """Check if unit is a worker."""
    return unit_name in ['SCV', 'Probe', 'Drone']
