#!/usr/bin/env python3
"""
Debug script to test replay parsing and identify issues.
Usage: python debug_replays.py <replay_file_path>
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.replay_parser import parse_replay, ReplayParseError
import sc2reader
import traceback


def debug_replay(file_path):
    """Debug a single replay file to identify parsing issues."""
    print(f"\n{'='*60}")
    print(f"Debugging: {os.path.basename(file_path)}")
    print(f"{'='*60}\n")

    # Step 1: Try sc2reader directly
    print("Step 1: Testing sc2reader library...")
    try:
        replay = sc2reader.load_replay(file_path, load_level=4)
        print(f"✓ sc2reader loaded successfully")
        print(f"  - Date: {replay.date if hasattr(replay, 'date') else replay.start_time}")
        print(f"  - Map: {replay.map_name}")
        print(f"  - Duration: {replay.game_length.seconds if hasattr(replay, 'game_length') else 'N/A'}s")
        print(f"  - Game Version: {replay.release_string if hasattr(replay, 'release_string') else 'Unknown'}")

        # Check players
        human_players = [p for p in replay.players if p.is_human]
        print(f"  - Human Players: {len(human_players)}")

        # Show player details
        print("\n  Player Details:")
        for p in human_players:
            print(f"    - {p.name} (Team {p.team_id}, {p.play_race}, Result: {p.result})")

        # Check for uneven teams
        team_counts = {}
        for p in human_players:
            team_counts[p.team_id] = team_counts.get(p.team_id, 0) + 1

        if len(set(team_counts.values())) > 1:
            print(f"\n  ⚠️  UNEVEN TEAMS DETECTED: {team_counts}")
            print(f"      Current system only supports even team sizes")

    except Exception as e:
        print(f"✗ sc2reader failed: {e}")
        print(f"\nFull traceback:")
        traceback.print_exc()
        print("\n⚠️  This is a sc2reader library issue. Possible causes:")
        print("   - Replay from unsupported SC2 version")
        print("   - Corrupt replay file")
        print("   - Custom game mode not supported")
        return

    # Step 2: Try our parser
    print(f"\n{'='*60}")
    print("Step 2: Testing our replay_parser...")
    try:
        replay_data = parse_replay(file_path)
        print("✓ Parse successful!")
        print(f"  - Game Mode: {replay_data.game_mode.value}")
        print(f"  - Players: {len(replay_data.players)}")
        print(f"  - Winner: Team {'1' if replay_data.players[0].won else '2'}")

    except ReplayParseError as e:
        print(f"✗ Parse failed: {e}")
        print(f"\nError type: {type(e).__name__}")

        # Categorize the error
        error_str = str(e)
        if "Invalid number of players" in error_str:
            print("\n⚠️  UNSUPPORTED GAME MODE")
            print("   Current system only supports: 2v2, 3v3, 4v4, 5v5")
        elif "Uneven team sizes" in error_str:
            print("\n⚠️  UNEVEN TEAMS")
            print("   Current system requires equal team sizes")
            print("   To support uneven teams, code changes are needed")
        elif "Cannot determine winner" in error_str or "Unable to determine" in error_str:
            print("\n⚠️  WINNER DETERMINATION ISSUE")
            print("   This replay needs manual review in the Failed Uploads page")
        else:
            print("\n⚠️  OTHER PARSE ERROR")
            print("   Check the error message above for details")

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_replays.py <replay_file_path>")
        print("\nYou can also pass multiple files:")
        print("  python debug_replays.py replay1.SC2Replay replay2.SC2Replay")
        sys.exit(1)

    replay_files = sys.argv[1:]

    for replay_file in replay_files:
        if not os.path.exists(replay_file):
            print(f"✗ File not found: {replay_file}")
            continue

        debug_replay(replay_file)

    print(f"\n{'='*60}")
    print("Debugging complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
