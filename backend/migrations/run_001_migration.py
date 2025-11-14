#!/usr/bin/env python3
"""
Migration script to add replay_file_path column to failed_uploads table.

Usage:
    python backend/migrations/run_001_migration.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine

def run_migration():
    """Add replay_file_path column to failed_uploads table."""
    with engine.connect() as connection:
        try:
            connection.execute("ALTER TABLE failed_uploads ADD COLUMN replay_file_path VARCHAR")
            connection.commit()
            print("✓ Successfully added replay_file_path column to failed_uploads table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("✓ Column replay_file_path already exists, skipping migration")
            else:
                print(f"✗ Migration failed: {e}")
                raise

if __name__ == "__main__":
    run_migration()
