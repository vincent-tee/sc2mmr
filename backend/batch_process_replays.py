"""
Batch Replay Processor

This script processes multiple replay files in chronological order,
showing predictions before each match to demonstrate how ratings evolve.

Usage:
    python batch_process_replays.py /path/to/replay/folder
    python batch_process_replays.py /path/to/replay/folder --verbose
    python batch_process_replays.py /path/to/replay/folder --show-predictions
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

from app.database import get_db_context, init_db
from app.models import Player, Match
from app.replay_parser import parse_replay, validate_replay_data, ReplayParseError
from app.rating_system import RatingSystem
from app.balancer import TeamBalancer, PlayerInfo


def find_replay_files(folder_path: str) -> List[str]:
    """
    Find all .SC2Replay files in the given folder.

    Args:
        folder_path: Path to search for replays

    Returns:
        List of replay file paths
    """
    replay_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.SC2Replay'):
                replay_files.append(os.path.join(root, file))
    return replay_files


def sort_replays_by_date(replay_files: List[str]) -> List[Tuple[str, datetime]]:
    """
    Parse replays and sort by date played.

    Args:
        replay_files: List of replay file paths

    Returns:
        List of tuples (file_path, date_played), sorted by date
    """
    replays_with_dates = []

    print(f"Parsing {len(replay_files)} replay files to extract dates...")

    for file_path in replay_files:
        try:
            replay_data = parse_replay(file_path)
            replays_with_dates.append((file_path, replay_data.played_at))
        except ReplayParseError as e:
            print(f"Warning: Skipping {os.path.basename(file_path)}: {e}")
        except Exception as e:
            print(f"Error parsing {os.path.basename(file_path)}: {e}")

    # Sort by date
    replays_with_dates.sort(key=lambda x: x[1])

    return replays_with_dates


def predict_match_outcome(replay_data, db) -> dict:
    """
    Predict match outcome before processing the replay.

    Args:
        replay_data: Parsed replay data
        db: Database session

    Returns:
        Dictionary with prediction details
    """
    # Get or create players (without updating ratings)
    team_1_players = []
    team_2_players = []

    for player_data in replay_data.players:
        player = db.query(Player).filter(Player.name == player_data.name).first()
        if not player:
            # New player - use default ratings
            player_info = PlayerInfo(
                id=0,
                name=player_data.name,
                mu=25.0,
                sigma=8.333,
                mmr=25.0 - (3 * 8.333)
            )
        else:
            player_info = PlayerInfo.from_player(player)

        if player_data.team == 1:
            team_1_players.append(player_info)
        else:
            team_2_players.append(player_info)

    # Calculate team ratings
    team_1_mu, team_1_sigma = TeamBalancer.get_team_rating(team_1_players)
    team_2_mu, team_2_sigma = TeamBalancer.get_team_rating(team_2_players)

    # Calculate win probability
    win_prob = TeamBalancer.calculate_win_probability(team_1_players, team_2_players)

    # Calculate match quality
    match_quality = TeamBalancer.calculate_match_quality(team_1_players, team_2_players)

    # Determine prediction
    predicted_winner = 1 if win_prob > 0.5 else 2
    actual_winner = 1 if replay_data.players[0].won else 2

    return {
        'team_1_players': [p.name for p in team_1_players],
        'team_2_players': [p.name for p in team_2_players],
        'team_1_mmr': sum(p.mmr for p in team_1_players),
        'team_2_mmr': sum(p.mmr for p in team_2_players),
        'win_probability_team_1': win_prob,
        'win_probability_team_2': 1 - win_prob,
        'match_quality': match_quality,
        'predicted_winner': predicted_winner,
        'actual_winner': actual_winner,
        'prediction_correct': predicted_winner == actual_winner
    }


def process_replay_batch(
    replay_folder: str,
    verbose: bool = False,
    show_predictions: bool = False
):
    """
    Process all replays in a folder chronologically.

    Args:
        replay_folder: Path to folder containing replays
        verbose: Show detailed output
        show_predictions: Show predictions before processing each replay
    """
    # Initialize database
    init_db()

    # Find all replay files
    print(f"\nSearching for replays in: {replay_folder}")
    replay_files = find_replay_files(replay_folder)

    if not replay_files:
        print("No replay files found!")
        return

    print(f"Found {len(replay_files)} replay files")

    # Sort by date
    sorted_replays = sort_replays_by_date(replay_files)

    if not sorted_replays:
        print("No valid replays to process!")
        return

    print(f"\nProcessing {len(sorted_replays)} replays in chronological order...")
    print("=" * 80)

    # Statistics
    total_processed = 0
    total_skipped = 0
    prediction_stats = {'correct': 0, 'incorrect': 0}

    with get_db_context() as db:
        for idx, (file_path, date_played) in enumerate(sorted_replays, 1):
            print(f"\n[{idx}/{len(sorted_replays)}] Processing replay from {date_played}")
            print(f"File: {os.path.basename(file_path)}")

            try:
                # Parse replay
                replay_data = parse_replay(file_path)

                # Validate
                is_valid, error_msg = validate_replay_data(replay_data)
                if not is_valid:
                    print(f"❌ Validation failed: {error_msg}")
                    total_skipped += 1
                    continue

                # Check for duplicate
                existing = db.query(Match).filter(
                    Match.replay_hash == replay_data.replay_hash
                ).first()

                if existing:
                    print(f"⏭️  Skipped (already processed)")
                    total_skipped += 1
                    continue

                # Show prediction if requested
                if show_predictions:
                    prediction = predict_match_outcome(replay_data, db)

                    print(f"\n📊 PREDICTION:")
                    print(f"   Team 1: {', '.join(prediction['team_1_players'])}")
                    print(f"   Team 1 MMR: {prediction['team_1_mmr']:.1f}")
                    print(f"   Team 2: {', '.join(prediction['team_2_players'])}")
                    print(f"   Team 2 MMR: {prediction['team_2_mmr']:.1f}")
                    print(f"   Win Probability - Team 1: {prediction['win_probability_team_1']:.1%}")
                    print(f"   Win Probability - Team 2: {prediction['win_probability_team_2']:.1%}")
                    print(f"   Match Quality: {prediction['match_quality']:.3f}")
                    print(f"   Predicted Winner: Team {prediction['predicted_winner']}")
                    print(f"   Actual Winner: Team {prediction['actual_winner']}")

                    if prediction['prediction_correct']:
                        print(f"   ✅ Prediction CORRECT!")
                        prediction_stats['correct'] += 1
                    else:
                        print(f"   ❌ Prediction INCORRECT")
                        prediction_stats['incorrect'] += 1

                # Create match
                match = Match(
                    played_at=replay_data.played_at,
                    game_mode=replay_data.game_mode,
                    map_name=replay_data.map_name,
                    duration_seconds=replay_data.duration_seconds,
                    replay_file_path=file_path,
                    replay_hash=replay_data.replay_hash
                )
                db.add(match)
                db.flush()

                # Update ratings
                RatingSystem.update_ratings_from_match(db, replay_data, match)

                print(f"✅ Processed successfully")
                print(f"   Map: {replay_data.map_name}")
                print(f"   Mode: {replay_data.game_mode.value}")
                print(f"   Players: {len(replay_data.players)}")

                if verbose:
                    # Show rating changes
                    print(f"\n   Rating updates:")
                    for player_data in replay_data.players:
                        player = db.query(Player).filter(
                            Player.name == player_data.name
                        ).first()
                        if player:
                            recent_mmr_str = f", Recent MMR={player.recency_weighted_mmr:.2f}" if player.recency_weighted_mmr is not None else ""
                            print(f"      {player.name}: MMR = {player.mmr:.2f} "
                                  f"(mu={player.mu:.2f}, sigma={player.sigma:.2f}){recent_mmr_str}")

                total_processed += 1

            except ReplayParseError as e:
                print(f"❌ Parse error: {e}")
                total_skipped += 1
            except Exception as e:
                print(f"❌ Error: {e}")
                total_skipped += 1

    # Final statistics
    print("\n" + "=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Total replays processed: {total_processed}")
    print(f"Total replays skipped: {total_skipped}")

    if show_predictions and (prediction_stats['correct'] + prediction_stats['incorrect']) > 0:
        total_predictions = prediction_stats['correct'] + prediction_stats['incorrect']
        accuracy = (prediction_stats['correct'] / total_predictions) * 100
        print(f"\nPrediction Accuracy: {accuracy:.1f}%")
        print(f"Correct predictions: {prediction_stats['correct']}")
        print(f"Incorrect predictions: {prediction_stats['incorrect']}")
        print(f"\nNote: Accuracy improves as more replays are processed and ratings stabilize!")

    # Show final player rankings
    with get_db_context() as db:
        players = db.query(Player).filter(Player.total_games >= 3).all()
        players_sorted = sorted(players, key=lambda p: p.mmr, reverse=True)

        if players_sorted:
            print(f"\n📊 FINAL PLAYER RANKINGS (min 3 games)")
            print("-" * 90)
            print(f"{'Rank':<6} {'Player':<20} {'MMR':<10} {'Recent MMR':<12} {'Record':<12} {'Win Rate':<10}")
            print("-" * 90)
            for idx, player in enumerate(players_sorted, 1):
                record = f"{player.wins}-{player.losses}"
                recent_mmr = f"{player.recency_weighted_mmr:.2f}" if player.recency_weighted_mmr is not None else "N/A"
                print(f"{idx:<6} {player.name:<20} {player.mmr:>8.2f}  "
                      f"{recent_mmr:>10}  {record:<12} {player.win_rate:>7.1f}%")

            print("\nNote: 'Recent MMR' weights recent matches more heavily (60-day half-life).")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Batch process SC2 replays in chronological order'
    )
    parser.add_argument(
        'folder',
        help='Path to folder containing .SC2Replay files'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output including rating changes'
    )
    parser.add_argument(
        '-p', '--show-predictions',
        action='store_true',
        help='Show match predictions before processing each replay'
    )

    args = parser.parse_args()

    # Validate folder exists
    if not os.path.isdir(args.folder):
        print(f"Error: Folder not found: {args.folder}")
        sys.exit(1)

    # Process replays
    process_replay_batch(args.folder, args.verbose, args.show_predictions)


if __name__ == "__main__":
    main()
