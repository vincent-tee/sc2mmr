import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.derived_data import rebuild_derived_data

if __name__ == "__main__":
    db = SessionLocal()
    try:
        print(rebuild_derived_data(db) or "A rebuild is already running")
    finally:
        db.close()
