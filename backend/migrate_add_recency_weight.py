"""
Migration script to add recency_weighted_mmr column to existing databases.

This script adds the recency_weighted_mmr column to the players table
and calculates initial values for all existing players.

Usage:
    python migrate_add_recency_weight.py
"""
import sys
from sqlalchemy import text

from app.database import engine, get_db_context, init_db
from app.models import Player
from app.rating_system import RatingSystem


def migrate():
    """Run the migration."""
    print("Starting migration: Add recency_weighted_mmr column")
    print("=" * 60)

    # Check if column already exists
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(players)"))
        columns = [row[1] for row in result]

        if 'recency_weighted_mmr' in columns:
            print("✅ Column 'recency_weighted_mmr' already exists")
        else:
            print("Adding column 'recency_weighted_mmr' to players table...")
            try:
                conn.execute(text(
                    "ALTER TABLE players ADD COLUMN recency_weighted_mmr FLOAT"
                ))
                conn.commit()
                print("✅ Column added successfully")
            except Exception as e:
                print(f"❌ Error adding column: {e}")
                sys.exit(1)

    # Calculate recency-weighted MMR for all existing players
    print("\nCalculating recency-weighted ratings for all players...")
    with get_db_context() as db:
        players = db.query(Player).all()

        if not players:
            print("No players found in database")
            return

        print(f"Processing {len(players)} players...")

        for player in players:
            try:
                RatingSystem.update_recency_weighted_rating(db, player)
                print(f"  ✅ {player.name}: MMR={player.mmr:.2f}, "
                      f"Recency-weighted={player.recency_weighted_mmr:.2f if player.recency_weighted_mmr else 0:.2f}")
            except Exception as e:
                print(f"  ❌ Error processing {player.name}: {e}")

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("\nRecency weighting is now enabled with:")
    print("  - Half-life: 30 days")
    print("  - Recent matches weighted more heavily than older matches")
    print("  - New column 'recency_weighted_mmr' tracks current skill estimate")


if __name__ == "__main__":
    migrate()
