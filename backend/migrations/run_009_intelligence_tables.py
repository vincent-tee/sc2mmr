#!/usr/bin/env python3
"""
Migration script to add feature_suggestions and meta_feedback tables.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine
from sqlalchemy import text


def run_migration():
    """Create new tables for intelligence center."""
    with engine.connect() as connection:
        try:
            # Create feature_suggestions table
            connection.execute(
                text("""
                CREATE TABLE IF NOT EXISTS feature_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_name VARCHAR(100) NOT NULL,
                    description VARCHAR(500) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )

            # Create meta_feedback table
            connection.execute(
                text("""
                CREATE TABLE IF NOT EXISTS meta_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theory VARCHAR(500) NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )

            connection.commit()
            print("✓ Successfully created intelligence center tables")
        except Exception as e:
            print(f"✗ Migration failed: {e}")
            raise


if __name__ == "__main__":
    run_migration()
