"""
SC2 Replay parser to extract game information from .SC2Replay files.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import hashlib
import sc2reader  # type: ignore
from dataclasses import dataclass
import logging

from .match_result import ResultSource, StatsSnapshot, supply_at_common_frame, supply_winner
from .models import GameMode, Race

logger = logging.getLogger(__name__)

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
    game_fingerprint: str  # Identifies same game from different observers
    result_source: str = ResultSource.REPLAY
    result_evidence: Optional[dict] = None


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


def calculate_game_fingerprint(
    map_name: str,
    played_at: datetime,
    player_names: List[str],
) -> str:
    """
    Calculate a game fingerprint to identify the same game from different observers.

    This fingerprint is based on game-identifying fields that are the same
    regardless of when each player left the game:
    - Map name (normalized to lowercase)
    - Game start time (rounded to the minute)
    - Sorted player names (normalized to lowercase)

    Returns a SHA256 hash of these combined fields.
    """
    # Normalize map name
    normalized_map = map_name.lower().strip()

    # Round timestamp to the minute (ignore seconds for slight variations)
    rounded_time = played_at.replace(second=0, microsecond=0).isoformat()

    # Sort and normalize player names
    sorted_players = sorted([name.lower().strip() for name in player_names])

    # Combine into fingerprint string
    fingerprint_data = f"{normalized_map}|{rounded_time}|{','.join(sorted_players)}"

    # Hash the fingerprint
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


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


def determine_game_mode(players: List[Any]) -> GameMode:
    team_counts = {}
    for p in players:
        team_id = int(getattr(p, "team_id", 0))
        team_counts[team_id] = team_counts.get(team_id, 0) + 1

    if len(team_counts) != 2:
        num_players = len(players)
        if num_players == 2:
            return GameMode.ONE_V_ONE
        return GameMode.TWO_V_TWO

    sizes = sorted(list(team_counts.values()), reverse=True)
    mode_str = f"{sizes[0]}v{sizes[1]}"

    try:
        return GameMode(mode_str)
    except ValueError:
        if sum(sizes) <= 2:
            return GameMode.ONE_V_ONE
        return GameMode.TWO_V_TWO


def parse_replay(
    file_path: str, manual_winner_team: Optional[int] = None
) -> ReplayData:
    """
    Parse a .SC2Replay file and return ReplayData.
    """
    try:
        replay = sc2reader.load_replay(file_path, load_level=4)  # type: ignore
    except Exception as sc2reader_error:
        # sc2reader is pinned and only knows protocol versions it shipped
        # with; a replay from a newer patch can fail here entirely. Try the
        # s2protocol fallback (degraded metrics, but patch-resilient)
        # before giving up on the match.
        logger.warning(
            f"sc2reader failed to load {file_path} ({sc2reader_error}); "
            "trying s2protocol fallback"
        )
        try:
            from .s2protocol_fallback import parse_replay_s2protocol

            return parse_replay_s2protocol(
                file_path, manual_winner_team=manual_winner_team
            )
        except Exception as fallback_error:
            logger.error(
                f"s2protocol fallback also failed for {file_path}: {fallback_error}"
            )
            raise ReplayParseError(str(sc2reader_error))

    try:
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

        # getattr's default only applies when the attribute is missing, not
        # when sc2reader sets it to None (seen on partial/corrupt replays) —
        # `or` catches both cases and was the root cause of a NoneType crash
        # in calculate_game_fingerprint's map_name.lower().
        map_name = getattr(replay, "map_name", None) or "Unknown Map"
        duration_seconds = getattr(getattr(replay, "game_length", None), "seconds", 0)

        # Extract players (both human and AI)
        all_players = getattr(replay, "players", [])

        # Manually extract stats from events if sc2reader didn't populate p.stats
        stats_snapshots = []
        from sc2reader.events import PlayerStatsEvent

        for event in getattr(replay, "events", []):
            if isinstance(event, PlayerStatsEvent):
                p_attr = getattr(event, "player", None)
                if p_attr:
                    stats_snapshots.append(StatsSnapshot(
                        player_id=p_attr.pid,
                        team=int(getattr(p_attr, "team_id", 0)),
                        frame=int(event.frame),
                        supply_used=float(event.food_used),
                    ))

        players_data = []
        evidence = supply_at_common_frame(stats_snapshots)

        winner_team = manual_winner_team
        result_source = ResultSource.CONFIRMED if manual_winner_team is not None else ResultSource.REPLAY
        winners_determined = manual_winner_team is not None or any(
            (getattr(p, "result", "") or "").lower() == "win" for p in all_players
        )

        if not winners_determined:
            teams = {int(getattr(p, "team_id", 0)) for p in all_players}
            favourite = supply_winner(evidence)
            if len(teams) != 2 or favourite is None:
                raise WinnerDeterminationError(
                    "The replay has no recorded result and the stats don't clearly show a winner"
                    if len(teams) == 2 else f"The replay has no recorded result and {len(teams)} teams",
                    team_stats=evidence or {},
                )
            result_source = ResultSource.SUGGESTED
            winner_team = favourite

        for p in all_players:
            team_id = int(getattr(p, "team_id", 0))
            won = False
            if winner_team is not None:
                won = team_id == winner_team
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

        # Calculate game fingerprint for same-game detection
        player_names = [p.name for p in players_data]
        game_fp = calculate_game_fingerprint(map_name, played_at, player_names)

        return ReplayData(
            played_at=played_at,
            game_mode=determine_game_mode(all_players) or GameMode.TWO_V_TWO,
            map_name=str(map_name),
            duration_seconds=int(duration_seconds),
            players=players_data,
            replay_hash=calculate_replay_hash(file_path),
            game_fingerprint=game_fp,
            result_source=result_source,
            result_evidence=evidence,
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
