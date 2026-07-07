#!/usr/bin/env python3
"""
Backfill kill_death_ratio in player_match_metrics.

Historically the parser stored units_killed / units_lost correctly but never
computed kill_death_ratio, so every row carries the dataclass default of 1.0.
This script recomputes kill_death_ratio from the already-stored unit counts -
no replay re-parsing required. The formula is imported from
app.advanced_parser.compute_kill_death_ratio, the same function the parser
uses at upload time, so the two can never drift.

Safety:
    * You MUST pass --db explicitly. There is no default DB path, so this can
      never silently mutate the production database.
    * Unless --no-backup is given, the target DB is backed up to
      "<db>.kd_backup" via SQLite's online backup API (sqlite3
      Connection.backup), which is WAL-safe - unlike a plain file copy, it
      captures committed transactions still living in the -wal sidecar.
    * If a non-empty -wal sidecar exists, a live writer (e.g. the running
      backend) may be using the DB; the script warns and requires --force.
    * Pass --dry-run to only print the before/after distribution.

Usage:
    python backend/scripts/backfill_kd_ratio.py --db /path/to/copy.db
    python backend/scripts/backfill_kd_ratio.py --db /path/to/copy.db --dry-run
"""

import argparse
import os
import sqlite3
import sys
from collections import Counter

# Make `app` importable when run as `python backend/scripts/backfill_kd_ratio.py`.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.advanced_parser import compute_kill_death_ratio  # noqa: E402


def summarize(values) -> dict:
    """Bucket kill_death_ratio values to summarise a distribution."""
    buckets: Counter = Counter()
    total = 0
    distinct = set()
    for v in values:
        total += 1
        if v is None:
            buckets["NULL"] += 1
            continue
        distinct.add(round(v, 4))
        if abs(v - 1.0) < 1e-9:
            buckets["exactly 1.00"] += 1
        elif v < 1.0:
            buckets["< 1.00 (net losses)"] += 1
        else:
            buckets["> 1.00 (net kills)"] += 1
    return {"total": total, "buckets": dict(buckets), "distinct_values": len(distinct)}


def db_distribution(conn: sqlite3.Connection) -> dict:
    return summarize(
        v for (v,) in conn.execute("SELECT kill_death_ratio FROM player_match_metrics")
    )


def safe_backup(conn: sqlite3.Connection, db_path: str) -> str:
    """Back up via SQLite's online backup API (WAL-safe, consistent)."""
    backup_path = f"{db_path}.kd_backup"
    dest = sqlite3.connect(backup_path)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return backup_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True, help="Path to the SQLite DB to update")
    ap.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    ap.add_argument("--no-backup", action="store_true", help="Skip the .kd_backup copy")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Proceed even if a -wal sidecar suggests a live writer",
    )
    args = ap.parse_args()

    wal_path = f"{args.db}-wal"
    if os.path.exists(wal_path) and os.path.getsize(wal_path) > 0 and not args.dry_run:
        print(
            f"WARNING: {wal_path} exists and is non-empty - a live process "
            "(e.g. the running backend) may be writing to this DB."
        )
        if not args.force:
            print("Refusing to write. Stop the writer or pass --force.")
            return 1

    conn = sqlite3.connect(args.db)
    try:
        before = db_distribution(conn)
        print(f"BEFORE: {before}")

        rows = conn.execute(
            "SELECT id, units_killed, units_lost FROM player_match_metrics"
        ).fetchall()
        updates = [
            (compute_kill_death_ratio(uk or 0, ul or 0), rid) for (rid, uk, ul) in rows
        ]

        if args.dry_run:
            preview = summarize(kd for kd, _ in updates)
            print(f"WOULD-BE AFTER (dry run): {preview}")
            return 0

        if not args.no_backup:
            backup = safe_backup(conn, args.db)
            print(f"Backed up DB to {backup} (online backup API)")

        conn.executemany(
            "UPDATE player_match_metrics SET kill_death_ratio = ? WHERE id = ?",
            updates,
        )
        conn.commit()

        after = db_distribution(conn)
        print(f"AFTER: {after}")
        # A few sample rows for eyeballing.
        samples = conn.execute(
            "SELECT units_killed, units_lost, kill_death_ratio "
            "FROM player_match_metrics LIMIT 8"
        ).fetchall()
        print("SAMPLES (killed, lost, kd):")
        for s in samples:
            print(f"  {s}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
