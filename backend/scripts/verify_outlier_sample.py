"""Read-only: hand-verify a random sample of the dry-run outliers against
raw sc2reader data, instead of trusting one manually-checked example to
stand in for all 571. For each sampled (match, player), confirms whether:
(a) the new parser's value exactly matches the *_army sc2reader fields
    (a pure code-correctness check, should always hold if the fix is right)
(b) the OLD stored value matches some explainable prior formula (the full
    resources_killed/lost aggregate, i.e. "just missing the fix") or is
    unexplainable by either formula (a pre-existing data-quality issue,
    as found for match 4 Stephan)
"""
import csv
import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sc2reader

DB = "file:data/sc2mmr.db?mode=ro"


def sample_outliers(n, seed=42):
    with open("/tmp/reparse_outliers.tsv") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    rng = random.Random(seed)
    return rng.sample(rows, min(n, len(rows)))


def verify_one(con, match_id, player_name, old_value, new_value):
    path = con.execute("SELECT replay_file_path FROM matches WHERE id=?", (match_id,)).fetchone()[0]
    replay = sc2reader.load_replay(path, load_level=4)
    pid = None
    for p in replay.players:
        if p.name == player_name:
            pid = p.pid
    if pid is None:
        return dict(status="NAME_NOT_FOUND")

    last_stats = None
    for e in replay.tracker_events:
        if e.name == "PlayerStatsEvent" and getattr(e, "pid", None) == pid:
            last_stats = e
    if last_stats is None:
        return dict(status="NO_STATS_EVENT")

    army_only = getattr(last_stats, "minerals_killed_army", 0) + getattr(last_stats, "vespene_killed_army", 0)
    full_aggregate = getattr(last_stats, "minerals_killed", 0) + getattr(last_stats, "vespene_killed", 0)

    new_matches_army_only = abs(int(new_value) - army_only) < 2  # int rounding tolerance
    old_matches_full_aggregate = abs(int(old_value) - full_aggregate) < 2
    old_explainable = old_matches_full_aggregate or abs(int(old_value)) < 2

    return dict(
        status="OK", army_only=army_only, full_aggregate=full_aggregate,
        new_matches_army_only=new_matches_army_only,
        old_matches_full_aggregate=old_matches_full_aggregate,
        old_explainable=old_explainable,
    )


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    sample = sample_outliers(n)
    con = sqlite3.connect(DB, uri=True)

    results = []
    for row in sample:
        mid, name = int(row["match_id"]), row["player_name"]
        try:
            v = verify_one(con, mid, name, row["old_value"], row["new_value"])
        except Exception as e:
            v = dict(status="EXCEPTION", error=str(e))
        results.append((mid, name, row["old_value"], row["new_value"], v))

    con.close()

    print(f"Sampled {len(results)} outliers (seed=42, out of 571 total)\n")
    new_correct = old_explained = old_unexplained = errors = 0
    for mid, name, old, new, v in results:
        if v["status"] != "OK":
            errors += 1
            print(f"match {mid} {name}: old={old} new={new} -- {v['status']} {v.get('error','')}")
            continue
        tag_new = "OK" if v["new_matches_army_only"] else "MISMATCH"
        if v["new_matches_army_only"]:
            new_correct += 1
        if v["old_explainable"]:
            old_explained += 1
            tag_old = "explained (matches old full-aggregate formula or ~0)"
        else:
            old_unexplained += 1
            tag_old = "UNEXPLAINED (doesn't match old OR new formula)"
        print(f"match {mid} {name}: old={old} new={new} | "
              f"new-vs-army-only={tag_new} (army_only={v['army_only']}) | "
              f"old: {tag_old} (full_aggregate={v['full_aggregate']})")

    print(f"\n=== Summary over {len(results)} sampled outliers ===")
    print(f"New parser value exactly matches raw *_army sc2reader fields: {new_correct}/{len(results)-errors}")
    print(f"Old stored value explainable (old formula or ~zero): {old_explained}/{len(results)-errors}")
    print(f"Old stored value UNEXPLAINED by either formula: {old_unexplained}/{len(results)-errors}")
    print(f"Errors/exceptions during verification: {errors}")


if __name__ == "__main__":
    main()
