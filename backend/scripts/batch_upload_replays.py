#!/usr/bin/env python3
"""
Batch upload replays from a directory.

Usage:
    python scripts/batch_upload_replays.py /path/to/replays
    python scripts/batch_upload_replays.py /path/to/replays --dry-run
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.services.match_orchestrator import MatchOrchestrator
from app.exceptions import (
    DuplicateReplayError,
    DuplicateGameError,
    ReplayParseError,
    WinnerDeterminationError,
)
from sqlalchemy.orm import sessionmaker


def find_replays(directory: str) -> List[str]:
    """Find all .SC2Replay files in directory."""
    replays = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.SC2Replay'):
                replays.append(os.path.join(root, file))
    return sorted(replays)


def upload_replays(
    directory: str,
    dry_run: bool = False,
) -> Tuple[int, int, int, int]:
    """
    Upload all replays from a directory.

    Returns: (success, duplicates, skipped_games, errors)
    """
    Session = sessionmaker(bind=engine)

    replays = find_replays(directory)
    total = len(replays)

    print(f"\n{'=' * 60}")
    print(f"🎮 SC2MMR Batch Replay Upload")
    print(f"{'=' * 60}")
    print(f"📁 Directory: {directory}")
    print(f"📊 Found {total} replay files")

    if dry_run:
        print("⚠️  DRY RUN MODE - No uploads will occur")
        return (0, 0, 0, 0)

    success = 0
    duplicates = 0
    skipped_games = 0  # Same game, shorter replay
    errors = 0

    print(f"\n🚀 Starting upload...\n")

    for i, replay_path in enumerate(replays, 1):
        filename = os.path.basename(replay_path)

        # Progress indicator every 50 replays
        if i % 50 == 0 or i == total:
            print(f"📊 Progress: {i}/{total} ({success} new, {duplicates} exact dupes, {skipped_games} same-game dupes, {errors} errors)")

        # Create fresh session for each replay to avoid autoflush issues
        session = Session()
        session.expire_on_commit = False

        try:
            orchestrator = MatchOrchestrator(session)
            result = orchestrator.orchestrate_match(
                file_path=replay_path,
                filename=filename,
                use_advanced_parser=True,
            )
            session.commit()
            success += 1

        except DuplicateReplayError as e:
            # Exact same replay file
            duplicates += 1
            try:
                session.rollback()
            except:
                pass

        except DuplicateGameError as e:
            # Same game but new replay has less data
            skipped_games += 1
            try:
                session.rollback()
            except:
                pass

        except WinnerDeterminationError as e:
            # Can't determine winner - skip silently
            errors += 1
            try:
                session.rollback()
            except:
                pass

        except ReplayParseError as e:
            # Parse error - might be 1v1 or other unsupported format
            errors += 1
            try:
                session.rollback()
            except:
                pass

        except Exception as e:
            errors += 1
            try:
                session.rollback()
            except:
                pass

        finally:
            try:
                session.close()
            except:
                pass
            # Dispose connection to force fresh state
            session = None

    return success, duplicates, skipped_games, errors


def main():
    parser = argparse.ArgumentParser(
        description="Batch upload SC2 replays from a directory"
    )
    parser.add_argument(
        "directory",
        help="Directory containing .SC2Replay files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count files, don't upload",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"❌ Directory not found: {args.directory}")
        sys.exit(1)

    success, duplicates, skipped_games, errors = upload_replays(
        args.directory,
        args.dry_run,
    )

    if not args.dry_run:
        print(f"\n{'=' * 60}")
        print(f"✅ Upload Complete!")
        print(f"{'=' * 60}")
        print(f"   ✅ New matches added:     {success}")
        print(f"   🔄 Exact duplicates:      {duplicates}")
        print(f"   📋 Same-game (shorter):   {skipped_games}")
        print(f"   ⚠️  Errors/unsupported:   {errors}")
        print(f"{'=' * 60}")

        if success > 0:
            print(f"\n💡 Tip: Run rating recalculation if needed:")
            print(f"   python scripts/recalculate_all_mmrs.py")


if __name__ == "__main__":
    main()
