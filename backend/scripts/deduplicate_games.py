#!/usr/bin/env python3
"""
Deduplicate games based on game fingerprint.

This script finds games that are the same (same map, players, and start time)
but recorded by different observers with different leave times. It keeps
only the version with the longest duration (most data).

Usage:
    # Dry run (show what would be deleted)
    python scripts/deduplicate_games.py --dry-run

    # Actually delete duplicates
    python scripts/deduplicate_games.py

    # Also backfill fingerprints for existing matches
    python scripts/deduplicate_games.py --backfill
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Match, MatchPlayer, PerformanceFeatures
from app.replay_parser import calculate_game_fingerprint
from app.database import get_db, engine


def calculate_fingerprint_for_match(
    session, match: Match
) -> str:
    """Calculate game fingerprint for an existing match."""
    # Get player names for this match
    match_players = (
        session.query(MatchPlayer)
        .filter(MatchPlayer.match_id == match.id)
        .all()
    )

    player_names = []
    for mp in match_players:
        player = mp.player
        if player:
            player_names.append(player.name)

    # Calculate fingerprint
    return calculate_game_fingerprint(
        map_name=match.map_name,
        played_at=match.played_at,
        player_names=player_names,
    )


def find_duplicates(session, dry_run: bool = True) -> Dict[str, List[Match]]:
    """Find all duplicate games based on fingerprint."""
    print("\n🔍 Scanning for duplicate games...")

    # Get all matches
    matches = session.query(Match).order_by(Match.played_at).all()
    print(f"   Found {len(matches)} total matches")

    # Group by fingerprint
    fingerprint_groups: Dict[str, List[Match]] = defaultdict(list)

    for match in matches:
        # Use existing fingerprint or calculate it
        if match.game_fingerprint:
            fp = match.game_fingerprint
        else:
            fp = calculate_fingerprint_for_match(session, match)
            if not dry_run:
                match.game_fingerprint = fp

        fingerprint_groups[fp].append(match)

    # Find groups with duplicates
    duplicate_groups = {
        fp: matches
        for fp, matches in fingerprint_groups.items()
        if len(matches) > 1
    }

    print(f"   Found {len(duplicate_groups)} groups with duplicates")
    return duplicate_groups


def show_duplicates(duplicate_groups: Dict[str, List[Match]]) -> None:
    """Display duplicate groups."""
    if not duplicate_groups:
        print("\n✅ No duplicates found!")
        return

    print("\n📋 Duplicate Games Found:")
    print("=" * 80)

    for fp, matches in duplicate_groups.items():
        # Sort by duration (longest first)
        sorted_matches = sorted(matches, key=lambda m: m.duration_seconds, reverse=True)
        keeper = sorted_matches[0]
        to_delete = sorted_matches[1:]

        print(f"\n🎮 Game: {keeper.map_name} on {keeper.played_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Fingerprint: {fp[:16]}...")
        print(f"   KEEP:   Match #{keeper.id} - {keeper.duration_seconds}s")
        for m in to_delete:
            print(f"   DELETE: Match #{m.id} - {m.duration_seconds}s (shorter by {keeper.duration_seconds - m.duration_seconds}s)")


def delete_duplicates(
    session,
    duplicate_groups: Dict[str, List[Match]],
    dry_run: bool = True
) -> Tuple[int, int]:
    """Delete shorter duplicates, keeping the longest version."""
    deleted_count = 0
    kept_count = 0

    for fp, matches in duplicate_groups.items():
        # Sort by duration (longest first)
        sorted_matches = sorted(matches, key=lambda m: m.duration_seconds, reverse=True)
        keeper = sorted_matches[0]
        to_delete = sorted_matches[1:]

        kept_count += 1

        for match in to_delete:
            if dry_run:
                print(f"   [DRY RUN] Would delete match #{match.id}")
            else:
                # Delete related records first
                session.query(PerformanceFeatures).filter(
                    PerformanceFeatures.match_player_id.in_(
                        session.query(MatchPlayer.id).filter(
                            MatchPlayer.match_id == match.id
                        )
                    )
                ).delete(synchronize_session=False)

                session.query(MatchPlayer).filter(
                    MatchPlayer.match_id == match.id
                ).delete()

                session.delete(match)
                print(f"   Deleted match #{match.id}")

            deleted_count += 1

    return deleted_count, kept_count


def backfill_fingerprints(session, dry_run: bool = True) -> int:
    """Backfill fingerprints for matches that don't have them."""
    print("\n🔧 Backfilling fingerprints for existing matches...")

    matches_without_fp = (
        session.query(Match)
        .filter(Match.game_fingerprint.is_(None))
        .all()
    )

    print(f"   Found {len(matches_without_fp)} matches without fingerprints")

    updated = 0
    for match in matches_without_fp:
        fp = calculate_fingerprint_for_match(session, match)
        if dry_run:
            print(f"   [DRY RUN] Would set fingerprint for match #{match.id}")
        else:
            match.game_fingerprint = fp
        updated += 1

    return updated


def main():
    parser = argparse.ArgumentParser(
        description="Deduplicate games based on game fingerprint"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Backfill fingerprints for existing matches",
    )
    args = parser.parse_args()

    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("\n" + "=" * 60)
        print("🎮 SC2MMR Game Deduplication Tool")
        print("=" * 60)

        if args.dry_run:
            print("⚠️  DRY RUN MODE - No changes will be made")

        # Backfill fingerprints first if requested
        if args.backfill:
            updated = backfill_fingerprints(session, args.dry_run)
            if not args.dry_run:
                session.commit()
                print(f"\n✅ Updated {updated} matches with fingerprints")

        # Find duplicates
        duplicate_groups = find_duplicates(session, args.dry_run)

        # Show what we found
        show_duplicates(duplicate_groups)

        if duplicate_groups:
            # Delete duplicates
            print("\n🗑️  Removing shorter duplicates...")
            deleted, kept = delete_duplicates(session, duplicate_groups, args.dry_run)

            if not args.dry_run:
                session.commit()
                print(f"\n✅ Deleted {deleted} duplicate matches")
                print(f"✅ Kept {kept} matches (longest version of each game)")
                print("\n⚠️  You may want to recalculate ratings:")
                print("   python scripts/recalculate_all_mmrs.py")
            else:
                print(f"\n📊 Summary (DRY RUN):")
                print(f"   Would delete: {deleted} matches")
                print(f"   Would keep: {kept} matches")
        else:
            print("\n✅ No duplicates to remove!")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
