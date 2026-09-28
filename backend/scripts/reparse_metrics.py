"""Re-parse stored replays with the upload parser, then diff or apply the results.

  shard  Parse every Nth replay file into JSONL rows. Reads no database; run
         several shards in parallel. Rows are keyed by replay hash (the file name).
  diff   Compare rows with a database's stored metrics. Read-only.
  apply  Save rows into a database exactly as an upload would, then mark derived
         data stale so ratings-side aggregates rebuild. WRITES: back up the DB first.
  push   Send rows to a server's /maintenance/metrics-reparse in batches (admin token).

Examples:
  python3 scripts/reparse_metrics.py shard --replays replays --shard 0 --of 8 --out /tmp/rows
  DATABASE_URL=sqlite:////tmp/prod.db python3 scripts/reparse_metrics.py diff --rows /tmp/rows
  python3 scripts/reparse_metrics.py push --rows /tmp/rows --api https://... --token ... [--apply]
"""

import argparse
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def iter_rows(rows_dir: Path):
    for shard_file in sorted(rows_dir.glob("shard_*.jsonl")):
        with open(shard_file) as rows:
            for line in rows:
                if line.strip():
                    yield json.loads(line)


def shard(args) -> None:
    from app.services.metrics_reparse import reparse_row

    logging.disable(logging.CRITICAL)
    replays = sorted(Path(args.replays).glob("*.SC2Replay"))
    mine = [path for i, path in enumerate(replays) if i % args.of == args.shard]
    args.out.mkdir(parents=True, exist_ok=True)
    parsed = failed = 0
    started = time.time()
    with open(args.out / f"shard_{args.shard}.jsonl", "w") as out, \
            open(args.out / f"shard_{args.shard}.errors", "w") as errors:
        for path in mine:
            try:
                out.write(json.dumps(reparse_row(str(path), path.stem)) + "\n")
                parsed += 1
            except Exception as error:
                failed += 1
                errors.write(f"{path.name}\t{type(error).__name__}: {error}\n")
    print(json.dumps({"shard": args.shard, "of": args.of, "files": len(mine), "parsed": parsed,
                      "failed": failed, "seconds": round(time.time() - started)}))


def diff_or_apply(args, dry_run: bool) -> None:
    from app.database import SessionLocal
    from app.services.metrics_reparse import apply_reparsed_rows

    logging.disable(logging.CRITICAL)
    db = SessionLocal()
    try:
        report = apply_reparsed_rows(db, iter_rows(args.rows), dry_run=dry_run)
    finally:
        db.close()
    print(json.dumps(report.summary(), indent=2))


def push(args) -> None:
    batch, sent = [], 0

    def send(rows):
        body = json.dumps({"rows": rows}).encode()
        request = urllib.request.Request(
            f"{args.api.rstrip('/')}/maintenance/metrics-reparse?dry_run={'false' if args.apply else 'true'}",
            data=body, method="POST",
            headers={"Content-Type": "application/json", "X-Admin-Token": args.token})
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read())

    totals = {"matches": 0, "unmatched_replays": 0, "players_updated": 0, "players_unmatched": 0}
    for row in iter_rows(args.rows):
        batch.append(row)
        if len(batch) == args.batch:
            result = send(batch)
            sent += len(batch)
            batch = []
            for key in totals:
                totals[key] += result[key]
            print(f"sent {sent} replays: {totals}", flush=True)
    if batch:
        result = send(batch)
        for key in totals:
            totals[key] += result[key]
    print(json.dumps({"applied": args.apply, **totals}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    shard_cmd = commands.add_parser("shard")
    shard_cmd.add_argument("--replays", required=True)
    shard_cmd.add_argument("--shard", type=int, required=True)
    shard_cmd.add_argument("--of", type=int, required=True)
    shard_cmd.add_argument("--out", type=Path, required=True)
    for name in ("diff", "apply"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--rows", type=Path, required=True)
    push_cmd = commands.add_parser("push")
    push_cmd.add_argument("--rows", type=Path, required=True)
    push_cmd.add_argument("--api", required=True)
    push_cmd.add_argument("--token", required=True)
    push_cmd.add_argument("--batch", type=int, default=5)
    push_cmd.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.command == "shard":
        shard(args)
    elif args.command == "push":
        push(args)
    else:
        diff_or_apply(args, dry_run=args.command == "diff")


if __name__ == "__main__":
    main()
