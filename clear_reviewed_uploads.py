#!/usr/bin/env python3
"""
Clear only reviewed failed uploads, keep unreviewed ones.
Usage: python clear_reviewed_uploads.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import SessionLocal
from app.models import FailedUpload


def clear_reviewed_uploads():
    """Delete only reviewed failed upload records."""
    db = SessionLocal()
    try:
        # Count reviewed and unreviewed
        reviewed_count = db.query(FailedUpload).filter(FailedUpload.reviewed == True).count()
        unreviewed_count = db.query(FailedUpload).filter(FailedUpload.reviewed == False).count()

        print(f"Found {reviewed_count} reviewed failed upload(s)")
        print(f"Found {unreviewed_count} unreviewed failed upload(s)")

        if reviewed_count == 0:
            print("Nothing to delete!")
            return

        # Confirm deletion
        response = input(f"\nDelete {reviewed_count} reviewed failed upload(s)? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return

        # Delete only reviewed failed uploads
        deleted = db.query(FailedUpload).filter(FailedUpload.reviewed == True).delete()
        db.commit()

        print(f"✓ Successfully deleted {deleted} reviewed failed upload(s)")
        print(f"  Kept {unreviewed_count} unreviewed failed upload(s)")

    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    clear_reviewed_uploads()
