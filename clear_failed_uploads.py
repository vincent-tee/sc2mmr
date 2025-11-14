#!/usr/bin/env python3
"""
Clear all failed uploads from the database.
Usage: python clear_failed_uploads.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import SessionLocal
from app.models import FailedUpload


def clear_failed_uploads():
    """Delete all failed upload records."""
    db = SessionLocal()
    try:
        # Count before deletion
        count = db.query(FailedUpload).count()
        print(f"Found {count} failed upload(s) in database")

        if count == 0:
            print("Nothing to delete!")
            return

        # Confirm deletion
        response = input(f"Delete all {count} failed upload(s)? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return

        # Delete all failed uploads
        deleted = db.query(FailedUpload).delete()
        db.commit()

        print(f"✓ Successfully deleted {deleted} failed upload(s)")

    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    clear_failed_uploads()
