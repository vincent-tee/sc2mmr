"""
SC2 Replay parser to extract game information from .SC2Replay files.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib
import sc2reader
from dataclasses import dataclass

from .models import GameMode, Race


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


def calculate_replay_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of replay file to detect duplicates.

    Args:
        file_path: Path to the replay file

    Returns:
        Hex digest of the file hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def normalize_race_name(race_name: str) -> Race:
    """
    Convert sc2reader race name to our Race enum.

    Args:
        race_name: Race name from sc2reader

    Returns:
        Race enum value
    """
    race_mapping = {
        'Terr': Race.TERRAN,
        'Prot': Race.PROTOSS,
        'Zerg': Race.ZERG,
        'Random': Race.RANDOM,
    }

    # Try direct mapping first
    if race_name in race_mapping:
        return race_mapping[race_name]

    # Try case-insensitive partial match
    race_lower = race_name.lower()
    if 'terr' in race_lower:
        return Race.TERRAN
    elif 'prot' in race_lower:
        return Race.PROTOSS
    elif 'zerg' in race_lower:
        return Race.ZERG
    elif 'random' in race_lower:
        return Race.RANDOM

    # Default to Random if unknown
    return Race.RANDOM


def determine_game_mode(num_players: int) -> Optional[GameMode]:
    """
    Determine game mode from number of players.

    Args:
        num_players: Total number of players in the game

    Returns:
        GameMode enum or None if invalid
    """
    mode_mapping = {
        4: GameMode.TWO_V_TWO,
        6: GameMode.THREE_V_THREE,
        8: GameMode.FOUR_V_FOUR,
        10: GameMode.FIVE_V_FIVE,
    }
    return mode_mapping.get(num_players)


def determine_winner_from_stats(replay, human_players: List) -> Tuple[Optional[int], Dict]:
    """
    Attempt to determine the winning team from game stats when result is ambiguous.
    This handles cases where players quit early.

    Args:
        replay: sc2reader replay object
        human_players: List of human players from the replay

    Returns:
        Tuple of (winning team number (1 or 2) or None, stats dictionary)
    """
    stats = {
        'team_1': {'players_still_in': 0, 'supply': 0, 'resources': 0, 'players': []},
        'team_2': {'players_still_in': 0, 'supply': 0, 'resources': 0, 'players': []}
    }

    try:
        # Group players by team
        team_1_players = [p for p in human_players if p.team_id == 1]
        team_2_players = [p for p in human_players if p.team_id == 2]

        # Collect player-level stats
        for p in team_1_players:
            player_info = {
                'name': p.name,
                'still_in': not hasattr(p, 'recorder_finished') or p.recorder_finished is None,
                'supply': getattr(p, 'supply', 0),
                'resources': 0
            }
            if hasattr(p, 'stats') and p.stats:
                player_info['resources'] = getattr(p.stats, 'resources_collected', 0)
            stats['team_1']['players'].append(player_info)

            if player_info['still_in']:
                stats['team_1']['players_still_in'] += 1
            stats['team_1']['supply'] += player_info['supply']
            stats['team_1']['resources'] += player_info['resources']

        for p in team_2_players:
            player_info = {
                'name': p.name,
                'still_in': not hasattr(p, 'recorder_finished') or p.recorder_finished is None,
                'supply': getattr(p, 'supply', 0),
                'resources': 0
            }
            if hasattr(p, 'stats') and p.stats:
                player_info['resources'] = getattr(p.stats, 'resources_collected', 0)
            stats['team_2']['players'].append(player_info)

            if player_info['still_in']:
                stats['team_2']['players_still_in'] += 1
            stats['team_2']['supply'] += player_info['supply']
            stats['team_2']['resources'] += player_info['resources']

        # Method 1: Check who stayed in the game longest
        if stats['team_1']['players_still_in'] > stats['team_2']['players_still_in']:
            return 1, stats
        elif stats['team_2']['players_still_in'] > stats['team_1']['players_still_in']:
            return 2, stats

        # Method 2: Compare army value / supply at end of game
        if stats['team_1']['supply'] > stats['team_2']['supply'] * 1.5:
            return 1, stats
        elif stats['team_2']['supply'] > stats['team_1']['supply'] * 1.5:
            return 2, stats

        # Method 3: Check resources collected (more resources = likely winning)
        if stats['team_1']['resources'] > stats['team_2']['resources'] * 1.3:
            return 1, stats
        elif stats['team_2']['resources'] > stats['team_1']['resources'] * 1.3:
            return 2, stats

    except Exception:
        # If stats analysis fails, return None with empty stats
        pass

    return None, stats


def parse_replay(file_path: str) -> ReplayData:
    """
    Parse a StarCraft 2 replay file and extract relevant information.

    Args:
        file_path: Path to the .SC2Replay file

    Returns:
        ReplayData object with extracted information

    Raises:
        ReplayParseError: If replay cannot be parsed or is invalid
    """
    try:
        # Load the replay with detailed stats
        replay = sc2reader.load_replay(file_path, load_level=4)

        # Calculate replay hash for duplicate detection
        replay_hash = calculate_replay_hash(file_path)

        # Extract basic game information
        played_at = replay.date if hasattr(replay, 'date') else replay.start_time
        map_name = replay.map_name
        duration_seconds = replay.game_length.seconds if hasattr(replay, 'game_length') else 0

        # Extract player information
        players: List[PlayerData] = []
        human_players = [p for p in replay.players if p.is_human]

        # Determine game mode
        num_players = len(human_players)
        game_mode = determine_game_mode(num_players)

        if game_mode is None:
            raise ReplayParseError(
                f"Invalid number of players: {num_players}. "
                "Expected 4 (2v2), 6 (3v3), 8 (4v4), or 10 (5v5)"
            )

        # Extract player data (first pass - basic info)
        for player in human_players:
            # Get player name (handle various name formats)
            name = player.name
            if hasattr(player, 'clan_tag') and player.clan_tag:
                # Remove clan tag if present
                name = name.replace(f"[{player.clan_tag}]", "").strip()

            # Get race
            race = normalize_race_name(player.play_race)

            # Get team and result
            team = player.team_id
            won = player.result == "Win"

            players.append(PlayerData(
                name=name,
                race=race,
                team=team,
                won=won
            ))

        # Validate we have two teams
        teams = set(p.team for p in players)
        if len(teams) != 2:
            raise ReplayParseError(f"Expected 2 teams, found {len(teams)}")

        # Validate team sizes are equal
        team_sizes = {}
        for team in teams:
            team_sizes[team] = sum(1 for p in players if p.team == team)

        if len(set(team_sizes.values())) != 1:
            raise ReplayParseError(
                f"Uneven team sizes: {team_sizes}. "
                f"Expected equal teams for {game_mode.value}"
            )

        # Check if winner is clear from results
        team_1_won = any(p.won for p in players if p.team == 1)
        team_2_won = any(p.won for p in players if p.team == 2)

        # If result is ambiguous (early quit scenario), determine winner from stats
        if team_1_won == team_2_won:
            winning_team, team_stats = determine_winner_from_stats(replay, human_players)

            if winning_team is None:
                # Unable to determine winner even with stats
                # Build detailed error message with team comparisons
                game_duration_minutes = duration_seconds / 60
                quit_players = [p.name for p in human_players if hasattr(p, 'recorder_finished') and p.recorder_finished]

                # Format team stats for error message
                stats_msg = "\n\nTeam Stats Comparison:"
                stats_msg += f"\n  Team 1:"
                stats_msg += f"\n    Players still in: {team_stats['team_1']['players_still_in']}"
                stats_msg += f"\n    Total supply: {team_stats['team_1']['supply']}"
                stats_msg += f"\n    Total resources: {team_stats['team_1']['resources']:,}"
                for player in team_stats['team_1']['players']:
                    stats_msg += f"\n      - {player['name']}: {'IN GAME' if player['still_in'] else 'QUIT'} | Supply: {player['supply']} | Resources: {player['resources']:,}"

                stats_msg += f"\n  Team 2:"
                stats_msg += f"\n    Players still in: {team_stats['team_2']['players_still_in']}"
                stats_msg += f"\n    Total supply: {team_stats['team_2']['supply']}"
                stats_msg += f"\n    Total resources: {team_stats['team_2']['resources']:,}"
                for player in team_stats['team_2']['players']:
                    stats_msg += f"\n      - {player['name']}: {'IN GAME' if player['still_in'] else 'QUIT'} | Supply: {player['supply']} | Resources: {player['resources']:,}"

                if game_duration_minutes < 10 and quit_players:
                    # Likely someone quit in early/mid game
                    raise ReplayParseError(
                        f"Cannot determine winner - player(s) quit at {game_duration_minutes:.1f} minutes. "
                        f"Quitters: {', '.join(quit_players)}. "
                        f"This replay was not played to completion and has ambiguous results.{stats_msg}\n\n"
                        f"Suggestion: Manually verify which team should have won based on the stats above."
                    )
                elif not quit_players and game_duration_minutes < 3:
                    # Very short game, might be a crash or test
                    raise ReplayParseError(
                        f"Game too short ({game_duration_minutes:.1f} minutes) with no clear winner. "
                        f"This may be a test game, crash, or incomplete replay.{stats_msg}"
                    )
                else:
                    # Other ambiguous scenario
                    raise ReplayParseError(
                        f"Unable to determine game winner from {game_duration_minutes:.1f} minute game. "
                        f"Game may have ended abnormally (disconnection, draw, or corrupted replay data).{stats_msg}\n\n"
                        f"The stats are too close to automatically determine a winner. Manual verification recommended."
                    )

            # Update player won status based on determined winner
            print(f"✓ Determined winner from game stats: Team {winning_team} (ambiguous quit scenario)")
            for i, player in enumerate(players):
                players[i] = PlayerData(
                    name=player.name,
                    race=player.race,
                    team=player.team,
                    won=(player.team == winning_team)
                )

        # Create and return ReplayData
        return ReplayData(
            played_at=played_at,
            game_mode=game_mode,
            map_name=map_name,
            duration_seconds=duration_seconds,
            players=players,
            replay_hash=replay_hash
        )

    except ReplayParseError:
        raise
    except Exception as e:
        raise ReplayParseError(f"Failed to parse replay: {str(e)}") from e


def validate_replay_data(replay_data: ReplayData) -> Tuple[bool, Optional[str]]:
    """
    Validate that replay data meets requirements.

    Args:
        replay_data: Parsed replay data

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check we have players
    if not replay_data.players:
        return False, "No players found in replay"

    # Check game mode is valid
    if replay_data.game_mode not in [GameMode.TWO_V_TWO, GameMode.THREE_V_THREE, GameMode.FOUR_V_FOUR, GameMode.FIVE_V_FIVE]:
        return False, f"Invalid game mode: {replay_data.game_mode}"

    # Check each team has same number of players
    team_1_count = sum(1 for p in replay_data.players if p.team == 1)
    team_2_count = sum(1 for p in replay_data.players if p.team == 2)

    if team_1_count != team_2_count:
        return False, f"Uneven teams: Team 1 has {team_1_count}, Team 2 has {team_2_count}"

    # Check exactly one winning team
    team_1_won = any(p.won for p in replay_data.players if p.team == 1)
    team_2_won = any(p.won for p in replay_data.players if p.team == 2)

    if team_1_won == team_2_won:
        return False, "Invalid game result: both teams won or both lost"

    # Check all players on winning team won
    for player in replay_data.players:
        team_won = (player.team == 1 and team_1_won) or (player.team == 2 and team_2_won)
        if player.won != team_won:
            return False, f"Inconsistent results: player {player.name} result doesn't match team"

    return True, None
