"""
Standardized match result types for sc2mmr.
Serves as the interface between parsers and services.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from ..models import GameMode, Race


@dataclass
class PlayerMatchResult:
    """
    Detailed performance metrics for a single player's participation in a match.
    """

    name: str
    race: Race
    team: int
    won: bool

    # Economic metrics
    minerals_collected: int = 0
    vespene_collected: int = 0
    total_resources_collected: int = 0
    resources_spent: int = 0
    spending_efficiency: float = 0.0
    workers_created: int = 0

    # Army & Combat
    units_trained: int = 0
    units_lost: int = 0
    units_killed: int = 0
    army_value_built: int = 0
    army_value_killed: int = 0
    army_value_lost: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    damage_ratio: float = 0.0

    # Timings (in game seconds)
    first_expansion_timing: Optional[int] = None
    first_army_timing: Optional[int] = None
    first_damage_timing: Optional[int] = None
    bases_created: int = 1

    # Mechanics & Performance
    apm: float = 0.0
    supply_block_seconds: int = 0
    lethality_score: float = 0.0
    workers_killed: int = 0
    early_workers_killed: int = 0
    mid_workers_killed: int = 0
    workers_lost: int = 0
    early_workers_lost: int = 0
    early_worker_losses: int = 0
    kill_death_ratio: float = 1.0
    player_archetype: str = "Tactical Balanced"
    harassment_response_score: float = 0.0
    detected_build_type: str = "unknown"

    # Composition & Timeline
    unit_composition: Dict[str, int] = field(default_factory=dict)
    damage_timeline: Dict[int, int] = field(default_factory=dict)

    # Impact Scores
    economic_score: float = 0.0
    combat_score: float = 0.0
    efficiency_score: float = 0.0
    overall_impact: float = 0.0

    # Team metrics
    team_fight_participation: float = 0.0
    team_fight_damage: int = 0
    team_fight_damage_ratio: float = 0.0

    # ML Features
    build_order: List[Dict[str, Any]] = field(default_factory=list)
    build_order_hash: str = ""
    upgrades: List[Dict[str, Any]] = field(default_factory=list)
    ability_usage: Dict[str, int] = field(default_factory=dict)

    # Timing analysis metrics
    early_game_damage: int = 0
    mid_game_damage: int = 0
    late_game_damage: int = 0
    aggression_score: float = 50.0


@dataclass
class ProcessedMatchResult:
    """
    Standardized container for a fully parsed match.
    """

    played_at: datetime
    game_mode: GameMode
    map_name: str
    duration_seconds: int
    replay_hash: str
    players: List[PlayerMatchResult]
    replay_file_path: Optional[str] = None
    game_fingerprint: Optional[str] = None  # Identifies same game from different observers

    @property
    def winners(self) -> List[PlayerMatchResult]:
        return [p for p in self.players if p.won]

    @property
    def losers(self) -> List[PlayerMatchResult]:
        return [p for p in self.players if not p.won]

    def get_player(self, name: str) -> Optional[PlayerMatchResult]:
        for p in self.players:
            if p.name == name:
                return p
        return None
