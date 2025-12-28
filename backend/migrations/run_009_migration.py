#!/usr/bin/env python3
"""
Migration script to add ML balancing tables.

This migration adds:
- session_weighted_mmr and last_session_weight_update columns to players
- player_synergy table for duo/trio synergy caching
- component_accuracy table for prediction accuracy tracking
- ml_config table for ML configuration storage

Usage:
    python backend/migrations/run_009_migration.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine
from sqlalchemy import text


def run_migration():
    """Run the ML balancing tables migration."""
    migration_path = os.path.join(
        os.path.dirname(__file__), "009_add_ml_balancing_tables.sql"
    )

    with open(migration_path, "r") as f:
        sql_content = f.read()

    # Split into individual statements (skip comments and empty lines)
    statements = []
    for statement in sql_content.split(";"):
        statement = statement.strip()
        # Skip empty statements and pure comment blocks
        if statement and not statement.startswith("--"):
            # Remove leading comments from statement
            lines = [
                line
                for line in statement.split("\n")
                if not line.strip().startswith("--")
            ]
            clean_statement = "\n".join(lines).strip()
            if clean_statement:
                statements.append(clean_statement)

    with engine.connect() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
                connection.commit()

                # Log what we did
                if "ALTER TABLE" in statement.upper():
                    if "session_weighted_mmr" in statement:
                        print("✓ Added session_weighted_mmr column to players")
                    elif "last_session_weight_update" in statement:
                        print("✓ Added last_session_weight_update column to players")
                elif "CREATE TABLE" in statement.upper():
                    if "player_synergy" in statement:
                        print("✓ Created player_synergy table")
                    elif "component_accuracy" in statement:
                        print("✓ Created component_accuracy table")
                    elif "ml_config" in statement:
                        print("✓ Created ml_config table")
                elif "CREATE INDEX" in statement.upper():
                    if "idx_synergy_players" in statement:
                        print("✓ Created idx_synergy_players index")
                    elif "idx_accuracy_component" in statement:
                        print("✓ Created idx_accuracy_component index")

            except Exception as e:
                error_str = str(e).lower()
                if (
                    "duplicate column name" in error_str
                    or "already exists" in error_str
                ):
                    # Extract what we were trying to add
                    if "session_weighted_mmr" in statement:
                        print("✓ Column session_weighted_mmr already exists, skipping")
                    elif "last_session_weight_update" in statement:
                        print(
                            "✓ Column last_session_weight_update already exists, skipping"
                        )
                    elif (
                        "player_synergy" in statement
                        and "CREATE TABLE" in statement.upper()
                    ):
                        print("✓ Table player_synergy already exists, skipping")
                    elif (
                        "component_accuracy" in statement
                        and "CREATE TABLE" in statement.upper()
                    ):
                        print("✓ Table component_accuracy already exists, skipping")
                    elif (
                        "ml_config" in statement and "CREATE TABLE" in statement.upper()
                    ):
                        print("✓ Table ml_config already exists, skipping")
                    elif "CREATE INDEX" in statement.upper():
                        print(f"✓ Index already exists, skipping")
                    else:
                        print(f"✓ Already exists, skipping: {statement[:50]}...")
                else:
                    print(f"✗ Migration failed: {e}")
                    print(f"  Statement: {statement[:100]}...")
                    raise

    print("\n✓ Migration 009 completed successfully!")


if __name__ == "__main__":
    run_migration()
