"""
SC2 Replay parser to extract game information from .SC2Replay files.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import hashlib
import sc2reader  # type: ignore
from dataclasses import dataclass
import logging

from .models import GameMode, Race

logger = logging.getLogger(__name__)

# Constants for winner determination thresholds
SUPPLY_ADVANTAGE_THRESHOLD = 1.5  # Supply advantage to determine winner
RESOURCES_ADVANTAGE_THRESHOLD = 1.3  # Resource advantage to determine winner
EARLY_QUIT_THRESHOLD_MINUTES = 10  # Minutes to consider an early quit
CRASH_THRESHOLD_MINUTES = 3  # Minutes to consider a crash or test game


@dataclass
class PlayerData:
    """Data class for player information extracted from replay."""

    name: str
    race: Race
    team: int
    won: bool


@dataclass
class ReplayData:
    """Data class for complete replay information."""

    played_at: datetime
    game_mode: GameMode
    map_name: str
    duration_seconds: int
    players: List[PlayerData]
    replay_hash: str


class ReplayParseError(Exception):
    """Custom exception for replay parsing errors."""

    pass


class WinnerDeterminationError(Exception):
    """Custom exception for when winner cannot be determined automatically."""

    def __init__(self, message: str, team_stats: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.team_stats = team_stats or {}


def calculate_replay_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of replay file to detect duplicates.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def normalize_race_name(race_name: str) -> Race:
    """
    Convert sc2reader race name to our Race enum.
    """
    race_mapping = {
        "Terr": Race.TERRAN,
        "Prot": Race.PROTOSS,
        "Zerg": Race.ZERG,
        "Random": Race.RANDOM,
    }

    if race_name in race_mapping:
        return race_mapping[race_name]

    race_lower = race_name.lower()
    if "terr" in race_lower:
        return Race.TERRAN
    elif "prot" in race_lower:
        return Race.PROTOSS
    elif "zerg" in race_lower:
        return Race.ZERG
    elif "random" in race_lower:
        return Race.RANDOM

    return Race.RANDOM


def determine_game_mode(num_players: int) -> Optional[GameMode]:
    """
    Determine game mode based on number of players.
    """
    mode_map = {
        2: GameMode.TWO_V_TWO,
        4: GameMode.TWO_V_TWO,
        6: GameMode.THREE_V_THREE,
        8: GameMode.FOUR_V_FOUR,
        10: GameMode.FIVE_V_FIVE,
    }
    return mode_map.get(num_players)


def parse_replay(
    file_path: str, manual_winner_team: Optional[int] = None
) -> ReplayData:
    """
    Parse a .SC2Replay file and return ReplayData.
    """
    try:
        replay = sc2reader.load_replay(file_path, load_level=4)  # type: ignore

        # Extract basic info
        played_at = getattr(replay, "utc_date", datetime.utcnow())
        map_name = getattr(replay, "map_name", "Unknown Map")
        duration_seconds = getattr(getattr(replay, "game_length", None), "seconds", 0)

        # Extract players
        human_players = [
            p for p in getattr(replay, "players", []) if getattr(p, "is_human", False)
        ]

        players_data = []
        team_stats: Dict[int, Dict[str, float]] = {}

        for p in human_players:
            team_id = int(getattr(p, "team_id", 0))
            if team_id not in team_stats:
                team_stats[team_id] = {"supply": 0.0, "resources": 0.0}

            # Simple winner determination proxy if result is missing
            if hasattr(p, "stats") and p.stats:
                team_stats[team_id]["supply"] += float(
                    getattr(p.stats, "supply_produced", 0)
                )
                team_stats[team_id]["resources"] += float(
                    getattr(p.stats, "minerals_collected", 0)
                )

        # Determine winners
        winners_determined = False
        if manual_winner_team is not None:
            winners_determined = True
        else:
            # Check if sc2reader already found a winner
            for p in human_players:
                result = getattr(p, "result", "") or ""
                if result.lower() == "win":
                    winners_determined = True
                    break

        if not winners_determined and len(team_stats) == 2:
            # Try our heuristic
            t1, t2 = list(team_stats.keys())
            s1, s2 = team_stats[t1]["supply"], team_stats[t2]["supply"]
            r1, r2 = team_stats[t1]["resources"], team_stats[t2]["resources"]

            if (
                s1 > s2 * SUPPLY_ADVANTAGE_THRESHOLD
                or r1 > r2 * RESOURCES_ADVANTAGE_THRESHOLD
            ):
                manual_winner_team = t1
            elif (
                s2 > s1 * SUPPLY_ADVANTAGE_THRESHOLD
                or r2 > r1 * RESOURCES_ADVANTAGE_THRESHOLD
            ):
                manual_winner_team = t2
            else:
                raise WinnerDeterminationError(
                    "Could not determine winner from stats",
                    team_stats={str(k): v for k, v in team_stats.items()},
                )

        for p in human_players:
            team_id = int(getattr(p, "team_id", 0))
            won = False
            if manual_winner_team is not None:
                won = team_id == manual_winner_team
            else:
                result = getattr(p, "result", "") or ""
                won = result.lower() == "win"

            players_data.append(
                PlayerData(
                    name=str(p.name),
                    race=normalize_race_name(str(p.play_race)),
                    team=team_id,
                    won=won,
                )
            )

        return ReplayData(
            played_at=played_at,
            game_mode=determine_game_mode(len(human_players)) or GameMode.TWO_V_TWO,
            map_name=str(map_name),
            duration_seconds=int(duration_seconds),
            players=players_data,
            replay_hash=calculate_replay_hash(file_path),
        )
    except Exception as e:
        if isinstance(e, WinnerDeterminationError):
            raise
        logger.error(f"Error parsing replay {file_path}: {e}")
        raise ReplayParseError(str(e))


def validate_replay_data(replay_data: ReplayData) -> Tuple[bool, Optional[str]]:
    """
    Perform validation on parsed replay data.
    """
    if not replay_data.players:
        return False, "No human players found"

    if replay_data.duration_seconds < CRASH_THRESHOLD_MINUTES * 60:
        return False, f"Game too short ({replay_data.duration_seconds}s)"

    return True, None
