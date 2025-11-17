#!/usr/bin/env python3
"""
Reset Database Script
Clears all match/replay data while preserving player records (or optionally clear everything).
"""
from app.database import SessionLocal, engine
from app.models import (
    Match, MatchPlayer, PlayerMatchMetrics, FailedUpload,
    Player, PlayerSynergy
)
from sqlalchemy import text

def reset_matches_only():
    """Clear all match data but keep players."""
    db = SessionLocal()
    try:
        print("Clearing match data...")

        # Delete in correct order (foreign key constraints)
        deleted_metrics = db.query(PlayerMatchMetrics).delete()
        print(f"  - Deleted {deleted_metrics} PlayerMatchMetrics")

        deleted_match_players = db.query(MatchPlayer).delete()
        print(f"  - Deleted {deleted_match_players} MatchPlayer records")

        deleted_matches = db.query(Match).delete()
        print(f"  - Deleted {deleted_matches} Match records")

        deleted_failed = db.query(FailedUpload).delete()
        print(f"  - Deleted {deleted_failed} FailedUpload records")

        # Reset player stats but keep records
        players = db.query(Player).all()
        for player in players:
            player.total_games = 0
            player.wins = 0
            player.losses = 0
            player.mmr = 1500.0
            player.mu = 25.0
            player.sigma = 8.333
            player.last_played = None
            player.protoss_games = 0
            player.terran_games = 0
            player.zerg_games = 0

        print(f"  - Reset {len(players)} player stats to defaults")

        # Clear synergies
        deleted_synergies = db.query(PlayerSynergy).delete()
        print(f"  - Deleted {deleted_synergies} PlayerSynergy records")

        db.commit()
        print("\n✅ Match data cleared! Players preserved with reset stats.")
        print("   Players will start with default MMR (1500) and TrueSkill (25.0/8.333)")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
    finally:
        db.close()


def reset_everything():
    """Clear EVERYTHING including players."""
    db = SessionLocal()
    try:
        print("⚠️  CLEARING ALL DATA (including players)...")

        deleted_metrics = db.query(PlayerMatchMetrics).delete()
        print(f"  - Deleted {deleted_metrics} PlayerMatchMetrics")

        deleted_match_players = db.query(MatchPlayer).delete()
        print(f"  - Deleted {deleted_match_players} MatchPlayer records")

        deleted_matches = db.query(Match).delete()
        print(f"  - Deleted {deleted_matches} Match records")

        deleted_failed = db.query(FailedUpload).delete()
        print(f"  - Deleted {deleted_failed} FailedUpload records")

        deleted_synergies = db.query(PlayerSynergy).delete()
        print(f"  - Deleted {deleted_synergies} PlayerSynergy records")

        deleted_players = db.query(Player).delete()
        print(f"  - Deleted {deleted_players} Player records")

        # Reset auto-increment (if table exists)
        try:
            db.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('players', 'matches', 'match_players', 'player_match_metrics', 'failed_uploads', 'player_synergies')"))
            print(f"  - Reset auto-increment counters")
        except Exception:
            # sqlite_sequence table doesn't exist, that's fine
            pass

        db.commit()
        print("\n✅ Database completely cleared! Fresh start ready.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
    finally:
        db.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 reset_database.py matches     # Clear matches, keep players")
        print("  python3 reset_database.py everything  # Clear everything")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == 'matches':
        confirm = input("Clear all matches but keep players? (yes/no): ")
        if confirm.lower() == 'yes':
            reset_matches_only()
        else:
            print("Cancelled.")

    elif mode == 'everything':
        confirm = input("⚠️  Clear EVERYTHING including players? (yes/no): ")
        if confirm.lower() == 'yes':
            reset_everything()
        else:
            print("Cancelled.")

    else:
        print(f"Unknown mode: {mode}")
        print("Use 'matches' or 'everything'")
