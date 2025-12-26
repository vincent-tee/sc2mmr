#!/usr/bin/env python3
"""
Migration script to add Performance Features table and Hybrid MMR columns.

SPEC-ML-001: ML-Enhanced Performance Impact System

This migration:
1. Adds hybrid_mmr and avg_pim columns to players table
2. Creates performance_features table for ML feature storage
3. Initializes hybrid_mmr from current display MMR for existing players

Usage:
    python backend/migrations/run_003_migration.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine
from sqlalchemy import text


def run_migration():
    """Add Hybrid MMR system tables and columns."""
    print("=" * 60)
    print("SPEC-ML-001: Hybrid MMR System Migration")
    print("=" * 60)

    with engine.connect() as connection:
        # Step 1: Add hybrid_mmr column to players
        try:
            connection.execute(text(
                "ALTER TABLE players ADD COLUMN hybrid_mmr REAL DEFAULT 2000.0"
            ))
            print("✓ Added hybrid_mmr column to players")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("✓ hybrid_mmr column already exists")
            else:
                print(f"✗ Failed to add hybrid_mmr: {e}")

        # Step 2: Add avg_pim column to players
        try:
            connection.execute(text(
                "ALTER TABLE players ADD COLUMN avg_pim REAL DEFAULT 0.0"
            ))
            print("✓ Added avg_pim column to players")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("✓ avg_pim column already exists")
            else:
                print(f"✗ Failed to add avg_pim: {e}")

        # Step 3: Create performance_features table
        try:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS performance_features (
                    id INTEGER PRIMARY KEY,
                    match_player_id INTEGER NOT NULL UNIQUE,

                    -- Z-score normalized features
                    damage_ratio_z REAL DEFAULT 0.0,
                    army_value_ratio_z REAL DEFAULT 0.0,
                    combat_score_z REAL DEFAULT 0.0,
                    spending_efficiency_z REAL DEFAULT 0.0,
                    economic_score_z REAL DEFAULT 0.0,
                    resource_advantage_z REAL DEFAULT 0.0,
                    team_fight_participation_z REAL DEFAULT 0.0,
                    team_fight_damage_ratio_z REAL DEFAULT 0.0,
                    overall_impact_z REAL DEFAULT 0.0,
                    efficiency_score_z REAL DEFAULT 0.0,

                    -- Calculated PIM values
                    pim REAL DEFAULT 0.0,
                    pim_combat REAL DEFAULT 0.0,
                    pim_economic REAL DEFAULT 0.0,
                    pim_team REAL DEFAULT 0.0,
                    pim_efficiency REAL DEFAULT 0.0,
                    pim_version VARCHAR(20) DEFAULT 'rule_v1',

                    -- MMR change tracking
                    raw_mmr_change REAL,
                    hybrid_mmr_change REAL,

                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (match_player_id) REFERENCES match_players(id)
                )
            """))
            print("✓ Created performance_features table")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ performance_features table already exists")
            else:
                print(f"✗ Failed to create performance_features table: {e}")

        # Step 4: Create indexes
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_perf_features_match_player "
                "ON performance_features(match_player_id)"
            ))
            print("✓ Created index on match_player_id")
        except Exception as e:
            print(f"Note: Index creation: {e}")

        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_perf_features_pim "
                "ON performance_features(pim)"
            ))
            print("✓ Created index on pim")
        except Exception as e:
            print(f"Note: Index creation: {e}")

        connection.commit()

        # Step 5: Initialize hybrid_mmr from current display MMR
        print("\nInitializing hybrid_mmr for existing players...")
        try:
            # Update hybrid_mmr = 1000 + 40*mu for all existing players
            result = connection.execute(text("""
                UPDATE players
                SET hybrid_mmr = 1000 + (40 * mu)
                WHERE hybrid_mmr IS NULL OR hybrid_mmr = 2000.0
            """))
            connection.commit()
            print(f"✓ Initialized hybrid_mmr for {result.rowcount} players")
        except Exception as e:
            print(f"Note: Initialization: {e}")

    print("\n" + "=" * 60)
    print("✓ Migration completed successfully!")
    print("=" * 60)
    print("\nSummary:")
    print("- players.hybrid_mmr: Performance-adjusted MMR")
    print("- players.avg_pim: Average Performance Impact Modifier")
    print("- performance_features: ML-ready feature store")
    print("\nHybrid MMR system is now ready for use.")
    print("Set HYBRID_MMR_ENABLED=true in config to activate.")


if __name__ == "__main__":
    run_migration()
