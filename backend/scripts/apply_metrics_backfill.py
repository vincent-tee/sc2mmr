import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.metrics_backfill import apply_metrics_rows


def main(shard_dir):
    rows = [json.loads(line) for shard in sorted(shard_dir.glob("shard_*.jsonl"))
            for line in shard.read_text().splitlines() if line.strip()]
    if not rows:
        print(f"No shard rows found in {shard_dir}")
        return
    db = SessionLocal()
    try:
        print(apply_metrics_rows(db, rows))
    finally:
        db.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
