"""
Migration script to recreate the database with ON DELETE CASCADE support.
"""

import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, reset_db


def migrate():
    print("Starting database migration (recreation)...")
    print(f"Database path: {engine.url}")

    # Drop and recreate all tables
    # This is the most reliable way to update foreign key constraints in SQLite
    reset_db()

    print("Database successfully recreated with new constraints.")


if __name__ == "__main__":
    migrate()
