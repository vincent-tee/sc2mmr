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
    is_ai: bool = False
    difficulty: Optional[str] = None


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
    Only supports team games (2v2 and above).
    """
    mode_map = {
        # 2 players = 1v1, not supported
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

        # Extract basic info - use replay date, not upload date
        # Try multiple date attributes in order of preference
        played_at = getattr(replay, "utc_date", None)
        if played_at is None:
            played_at = getattr(replay, "date", None)
        if played_at is None:
            played_at = getattr(replay, "start_time", None)
        if played_at is None:
            # Fallback to file modification time
            import os

            file_mtime = os.path.getmtime(file_path)
            played_at = datetime.fromtimestamp(file_mtime)

        map_name = getattr(replay, "map_name", "Unknown Map")
        duration_seconds = getattr(getattr(replay, "game_length", None), "seconds", 0)

        # Extract players (both human and AI)
        all_players = getattr(replay, "players", [])

        players_data = []
        team_stats: Dict[int, Dict[str, float]] = {}

        for p in all_players:
            team_id = int(getattr(p, "team_id", 0))
            if team_id not in team_stats:
                team_stats[team_id] = {
                    "supply": 0.0,
                    "resources_collected": 0.0,
                    "resources_current": 0.0,  # Resources at end of game (for quit detection)
                }

            # Gather stats for winner determination fallback
            if hasattr(p, "stats") and p.stats:
                stats = p.stats
                team_stats[team_id]["supply"] += float(
                    getattr(stats, "supply_produced", 0) or 0
                )
                team_stats[team_id]["resources_collected"] += float(
                    getattr(stats, "minerals_collected", 0) or 0
                ) + float(getattr(stats, "vespene_collected", 0) or 0)
                # Current resources at time of game end (for quit scenarios)
                team_stats[team_id]["resources_current"] += float(
                    getattr(stats, "minerals_current", 0) or 0
                ) + float(getattr(stats, "vespene_current", 0) or 0)

        # Determine winners
        winners_determined = False
        if manual_winner_team is not None:
            winners_determined = True
        else:
            # Check if sc2reader already found a winner
            for p in all_players:
                result = getattr(p, "result", "") or ""
                if result.lower() == "win":
                    winners_determined = True
                    break

        if not winners_determined and len(team_stats) == 2:
            # Try our heuristic - use combined resources as fallback
            t1, t2 = list(team_stats.keys())
            s1, s2 = team_stats[t1]["supply"], team_stats[t2]["supply"]
            r1, r2 = (
                team_stats[t1]["resources_collected"],
                team_stats[t2]["resources_collected"],
            )

            # First try: significant advantage in supply or resources collected
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
                # Fallback: Use total resources (collected) - whoever has more wins
                # This handles quit scenarios where one team just has more stuff
                total_r1 = team_stats[t1]["resources_collected"]
                total_r2 = team_stats[t2]["resources_collected"]

                if total_r1 > total_r2:
                    manual_winner_team = t1
                    logger.info(
                        f"Winner determined by total resources: Team {t1} ({total_r1:.0f}) > Team {t2} ({total_r2:.0f})"
                    )
                elif total_r2 > total_r1:
                    manual_winner_team = t2
                    logger.info(
                        f"Winner determined by total resources: Team {t2} ({total_r2:.0f}) > Team {t1} ({total_r1:.0f})"
                    )
                else:
                    # Truly tied - extremely rare, use supply as final tiebreaker
                    if s1 >= s2:
                        manual_winner_team = t1
                    else:
                        manual_winner_team = t2
                    logger.info(
                        f"Winner determined by supply tiebreaker: Team {manual_winner_team}"
                    )

        for p in all_players:
            team_id = int(getattr(p, "team_id", 0))
            won = False
            if manual_winner_team is not None:
                won = team_id == manual_winner_team
            else:
                result = getattr(p, "result", "") or ""
                won = result.lower() == "win"

            is_ai = not getattr(p, "is_human", False)
            difficulty = getattr(p, "difficulty", None) if is_ai else None

            # For AI, use a more descriptive name if possible
            p_name = str(p.name)
            if is_ai and difficulty:
                p_name = f"Computer ({difficulty})"

            players_data.append(
                PlayerData(
                    name=p_name,
                    race=normalize_race_name(str(p.play_race)),
                    team=team_id,
                    won=won,
                    is_ai=is_ai,
                    difficulty=difficulty,
                )
            )

        return ReplayData(
            played_at=played_at,
            game_mode=determine_game_mode(len(getattr(replay, "players", [])))
            or GameMode.TWO_V_TWO,
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

    # Reject 1v1 games - only team games are supported
    num_players = len(replay_data.players)
    if num_players < 4:
        return (
            False,
            f"Only team games (2v2+) are supported. This appears to be a {num_players}-player game.",
        )

    # Check for valid team game mode
    if replay_data.game_mode == GameMode.ONE_V_ONE:
        return (
            False,
            "1v1 games are not supported. Only team games (2v2, 3v3, 4v4, 5v5) are tracked.",
        )

    return True, None
