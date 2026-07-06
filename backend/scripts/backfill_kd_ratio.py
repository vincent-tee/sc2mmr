#!/usr/bin/env python3
"""
Backfill kill_death_ratio in player_match_metrics.

Historically the parser stored units_killed / units_lost correctly but never
computed kill_death_ratio, so every row carries the dataclass default of 1.0.
This script recomputes kill_death_ratio from the already-stored unit counts -
no replay re-parsing required. The formula mirrors the parser fix:

    units_lost  > 0  -> units_killed / units_lost
    units_killed > 0 (and units_lost == 0) -> 10.0  (capped flawless engagement)
    otherwise        -> 1.0  (no combat recorded)

Safety:
    * You MUST pass --db explicitly. There is no default DB path, so this can
      never silently mutate the production database.
    * Unless --no-backup is given, the target DB is copied to
      "<db>.kd_backup" before any write (house rule: back up before writing).
    * Pass --dry-run to only print the before/after distribution.

Usage:
    python backend/scripts/backfill_kd_ratio.py --db /path/to/copy.db
    python backend/scripts/backfill_kd_ratio.py --db /path/to/copy.db --dry-run
"""

import argparse
import shutil
import sqlite3
import sys
from collections import Counter


def distribution(conn: sqlite3.Connection) -> dict:
    """Bucket kill_death_ratio values to summarise the current state."""
    buckets: Counter = Counter()
    total = 0
    distinct = set()
    for (v,) in conn.execute("SELECT kill_death_ratio FROM player_match_metrics"):
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


def compute_kd(units_killed, units_lost) -> float:
    killed = units_killed or 0
    lost = units_lost or 0
    if lost > 0:
        return killed / lost
    if killed > 0:
        return 10.0
    return 1.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True, help="Path to the SQLite DB to update")
    ap.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    ap.add_argument("--no-backup", action="store_true", help="Skip the .kd_backup copy")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        before = distribution(conn)
        print(f"BEFORE: {before}")

        rows = conn.execute(
            "SELECT id, units_killed, units_lost FROM player_match_metrics"
        ).fetchall()
        updates = [
            (compute_kd(uk, ul), rid) for (rid, uk, ul) in rows
        ]

        if args.dry_run:
            preview = distribution_from_updates(updates)
            print(f"WOULD-BE AFTER (dry run): {preview}")
            return 0

        if not args.no_backup:
            backup = f"{args.db}.kd_backup"
            shutil.copy2(args.db, backup)
            print(f"Backed up DB to {backup}")

        conn.executemany(
            "UPDATE player_match_metrics SET kill_death_ratio = ? WHERE id = ?",
            updates,
        )
        conn.commit()

        after = distribution(conn)
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


def distribution_from_updates(updates) -> dict:
    buckets: Counter = Counter()
    distinct = set()
    for kd, _ in updates:
        distinct.add(round(kd, 4))
        if abs(kd - 1.0) < 1e-9:
            buckets["exactly 1.00"] += 1
        elif kd < 1.0:
            buckets["< 1.00 (net losses)"] += 1
        else:
            buckets["> 1.00 (net kills)"] += 1
    return {
        "total": len(updates),
        "buckets": dict(buckets),
        "distinct_values": len(distinct),
    }


if __name__ == "__main__":
    sys.exit(main())
