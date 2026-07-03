"""
merge_players.py — Merge a duplicate player record into a canonical one.

Usage:
    python merge_players.py --from-id 225 --into-name "DragonKing"

What it does:
  1. Looks up both players and prints a summary for confirmation.
  2. Reassigns all match_players rows from the duplicate to the canonical player.
  3. Handles synergies and rivalries that reference the duplicate.
  4. Deletes the duplicate player record.
  5. Does NOT recalculate MMR — run recalculate_all_mmrs.py afterwards.
"""

import argparse
import sys
import os

# Allow running from project root or scripts/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.database import SessionLocal
from backend.app.models import Player, MatchPlayer, PlayerSynergy, PlayerRivalry, PlayerAchievement
from sqlalchemy import or_, and_


def merge_players(from_id: int, into_name: str = None, into_id: int = None, dry_run: bool = False):
    db = SessionLocal()
    try:
        # ── 1. Look up both players ───────────────────────────────────────────
        source = db.query(Player).filter(Player.id == from_id).first()
        if not source:
            print(f"ERROR: No player with ID {from_id}")
            return

        if into_id:
            target = db.query(Player).filter(Player.id == into_id).first()
        else:
            target = db.query(Player).filter(Player.name == into_name).first()

        if not target:
            print(f"ERROR: Could not find target player (id={into_id}, name={into_name})")
            return

        if source.id == target.id:
            print("ERROR: Source and target are the same player.")
            return

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Merge plan:")
        print(f"  FROM: [{source.id}] {source.name}  ({source.total_games} games, MMR {round(source.unified_mmr or source.mmr)})")
        print(f"  INTO: [{target.id}] {target.name}  ({target.total_games} games, MMR {round(target.unified_mmr or target.mmr)})")

        # Count affected rows
        mp_count = db.query(MatchPlayer).filter(MatchPlayer.player_id == source.id).count()
        print(f"\n  match_players to reassign : {mp_count}")

        synergy_count = db.query(PlayerSynergy).filter(
            or_(PlayerSynergy.player1_id == source.id, PlayerSynergy.player2_id == source.id)
        ).count()
        print(f"  synergies referencing duplicate: {synergy_count}")

        rivalry_count = db.query(PlayerRivalry).filter(
            or_(PlayerRivalry.player1_id == source.id, PlayerRivalry.player2_id == source.id)
        ).count()
        print(f"  rivalries referencing duplicate: {rivalry_count}")

        ach_count = db.query(PlayerAchievement).filter(PlayerAchievement.player_id == source.id).count()
        print(f"  achievements to reassign: {ach_count}")

        if dry_run:
            print("\n[DRY RUN] No changes made.")
            return

        confirm = input("\nProceed? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Aborted.")
            return

        # ── 2. Reassign match_players ─────────────────────────────────────────
        # Check for any matches where both players already appear (can't have duplicates in same match)
        from sqlalchemy import text
        conflict_sql = text("""
            SELECT mp1.match_id
            FROM match_players mp1
            JOIN match_players mp2 ON mp1.match_id = mp2.match_id
            WHERE mp1.player_id = :from_id AND mp2.player_id = :into_id
        """)
        conflicts = db.execute(conflict_sql, {"from_id": source.id, "into_id": target.id}).fetchall()
        if conflicts:
            conflict_ids = [r[0] for r in conflicts]
            print(f"\nWARNING: {len(conflict_ids)} match(es) already have both players. "
                  f"Duplicate match_player rows for these will be deleted (not reassigned):")
            print(f"  Match IDs: {conflict_ids}")
            # Delete the source player's rows in those conflict matches
            db.query(MatchPlayer).filter(
                MatchPlayer.player_id == source.id,
                MatchPlayer.match_id.in_(conflict_ids)
            ).delete(synchronize_session=False)

        # Reassign remaining
        db.query(MatchPlayer).filter(MatchPlayer.player_id == source.id).update(
            {MatchPlayer.player_id: target.id}, synchronize_session=False
        )
        print(f"✓ Reassigned match_players")

        # ── 3. Handle synergies ───────────────────────────────────────────────
        # Delete synergies that would duplicate now
        db.query(PlayerSynergy).filter(
            or_(PlayerSynergy.player1_id == source.id, PlayerSynergy.player2_id == source.id)
        ).delete(synchronize_session=False)
        print(f"✓ Removed synergies referencing duplicate (will be rebuilt on recalculate)")

        # ── 4. Handle rivalries ───────────────────────────────────────────────
        db.query(PlayerRivalry).filter(
            or_(PlayerRivalry.player1_id == source.id, PlayerRivalry.player2_id == source.id)
        ).delete(synchronize_session=False)
        print(f"✓ Removed rivalries referencing duplicate (will be rebuilt on recalculate)")

        # ── 5. Reassign achievements ──────────────────────────────────────────
        db.query(PlayerAchievement).filter(PlayerAchievement.player_id == source.id).update(
            {PlayerAchievement.player_id: target.id}, synchronize_session=False
        )
        print(f"✓ Reassigned achievements")

        # ── 6. Delete duplicate player ────────────────────────────────────────
        db.delete(source)
        db.commit()
        print(f"\n✅ Deleted duplicate player [{source.id}] '{source.name}'")
        print(f"\nNow run: python backend/scripts/recalculate_all_mmrs.py")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge a duplicate player into a canonical one.")
    parser.add_argument("--from-id", type=int, required=True, help="ID of the duplicate player to remove")
    parser.add_argument("--into-id", type=int, default=None, help="ID of the canonical player to keep (preferred)")
    parser.add_argument("--into-name", type=str, default=None, help="Name of the canonical player to keep")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    args = parser.parse_args()

    if not args.into_id and not args.into_name:
        print("ERROR: Provide either --into-id or --into-name")
        sys.exit(1)

    merge_players(from_id=args.from_id, into_name=args.into_name, dry_run=args.dry_run, into_id=args.into_id)
