"""Read-only dry run: re-parse replays with the fixed UnifiedParser and
compare against currently-stored metrics. Writes NOTHING to the database.

This is deliberately a comparison pass, not a backfill -- the 2026-09-15
replay metrics review explicitly recommends building a validation corpus
before any historical reparse actually overwrites data. Run in batches,
inspect the summary after each, and only consider an actual backfill once
several batches look sane (few exceptions, expected-direction deltas, no
wild outliers).
"""
import sqlite3
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.unified_parser import UnifiedParser

DB = "file:data/sc2mmr.db?mode=ro"


def stored_metrics_for_match(con, match_id):
    rows = con.execute("""
        SELECT p.name, pmm.army_value_killed, pmm.army_value_lost,
               pmm.spending_efficiency, pmm.workers_created,
               pmm.total_resources_collected, pmm.army_value_built
        FROM match_players mp
        JOIN players p ON p.id = mp.player_id
        LEFT JOIN player_match_metrics pmm ON pmm.match_player_id = mp.id
        WHERE mp.match_id = ?
    """, (match_id,)).fetchall()
    return {name: dict(army_value_killed=avk, army_value_lost=avl,
                        spending_efficiency=se, workers_created=wc,
                        total_resources_collected=trc, army_value_built=avb)
            for name, avk, avl, se, wc, trc, avb in rows}


def run_batch(match_ids, con):
    parser = UnifiedParser()
    ok, failed = 0, 0
    exceptions = []
    army_killed_deltas, spending_eff_deltas, army_built_deltas = [], [], []
    outliers = []
    no_name_match = 0

    for mid, path in match_ids:
        try:
            result = parser.parse(path)
        except Exception as e:
            failed += 1
            exceptions.append((mid, path, str(e)))
            continue
        ok += 1
        stored = stored_metrics_for_match(con, mid)
        for pr in result.players:
            s = stored.get(pr.name)
            if s is None or s["army_value_killed"] is None:
                no_name_match += 1
                continue
            delta = pr.army_value_killed - s["army_value_killed"]
            army_killed_deltas.append(delta)
            spending_eff_deltas.append(pr.spending_efficiency - s["spending_efficiency"])
            if s["army_value_built"] is not None:
                army_built_deltas.append(pr.army_value_built - s["army_value_built"])
            if abs(delta) > 20000:
                outliers.append((mid, pr.name, delta, s["army_value_killed"], pr.army_value_killed))

    return dict(
        ok=ok, failed=failed, exceptions=exceptions, no_name_match=no_name_match,
        army_killed_deltas=army_killed_deltas, spending_eff_deltas=spending_eff_deltas,
        army_built_deltas=army_built_deltas, outliers=outliers,
    )


def summarize(label, r):
    print(f"\n=== {label} ===")
    print(f"parsed OK: {r['ok']}, failed: {r['failed']}, "
          f"player-rows with no matching stored metric: {r['no_name_match']}")
    if r["exceptions"]:
        print("Exceptions:")
        for mid, path, err in r["exceptions"][:5]:
            print(f"  match {mid} ({path}): {err}")
    ak = r["army_killed_deltas"]
    se = r["spending_eff_deltas"]
    if ak:
        ak_sorted = sorted(ak)
        n = len(ak_sorted)
        print(f"army_value_killed delta (new - old), n={n}: "
              f"min={ak_sorted[0]}, median={ak_sorted[n//2]}, max={ak_sorted[-1]}, "
              f"mean={sum(ak)/n:.1f}")
        negative_frac = sum(1 for d in ak if d < 0) / n
        print(f"  fraction that decreased (expected, since non-army value is now excluded): {negative_frac:.1%}")
    if se:
        se_sorted = sorted(se)
        n = len(se_sorted)
        print(f"spending_efficiency delta (new - old), n={n}: "
              f"min={se_sorted[0]:.3f}, median={se_sorted[n//2]:.3f}, max={se_sorted[-1]:.3f}")
    ab = r["army_built_deltas"]
    if ab:
        ab_sorted = sorted(ab)
        n = len(ab_sorted)
        print(f"army_value_built delta (new - old), n={n}: "
              f"min={ab_sorted[0]}, median={ab_sorted[n//2]}, max={ab_sorted[-1]}, mean={sum(ab)/n:.1f}")
    if r["outliers"]:
        print(f"Outliers (|delta| > 20000), {len(r['outliers'])}:")
        for mid, name, delta, old, new in r["outliers"][:10]:
            print(f"  match {mid} {name}: {old} -> {new} (delta {delta:+d})")


def main():
    import logging
    import os
    logging.getLogger("app.services.unified_parser").setLevel(logging.ERROR)  # suppress per-match unknown-unit-cost noise

    con = sqlite3.connect(DB, uri=True)
    rows = con.execute("""
        SELECT id, replay_file_path FROM matches
        WHERE replay_file_path IS NOT NULL AND replay_file_path != ''
        ORDER BY id
    """).fetchall()
    rows = [(mid, path) for mid, path in rows if os.path.exists(path)]
    print(f"Total matches with a locally-available replay file: {len(rows)}")

    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end = int(sys.argv[3]) if len(sys.argv) > 3 else len(rows)

    all_ak, all_se, all_ab = [], [], []
    total_ok = total_failed = total_no_match = 0
    all_exceptions, all_outliers = [], []

    i = start
    while i < end:
        batch = rows[i:i + batch_size]
        if not batch:
            break
        r = run_batch(batch, con)
        total_ok += r["ok"]
        total_failed += r["failed"]
        total_no_match += r["no_name_match"]
        all_ak.extend(r["army_killed_deltas"])
        all_se.extend(r["spending_eff_deltas"])
        all_ab.extend(r["army_built_deltas"])
        all_exceptions.extend(r["exceptions"])
        all_outliers.extend(r["outliers"])

        flag = " <-- flagged: failures or many outliers, check this batch" if (
            r["failed"] > 0 or len(r["outliers"]) > len(batch) * 0.3
        ) else ""
        print(f"batch [{i}:{i+len(batch)}]: ok={r['ok']} failed={r['failed']} "
              f"outliers={len(r['outliers'])}{flag}")
        if r["exceptions"]:
            for mid, path, err in r["exceptions"]:
                print(f"    EXCEPTION match {mid}: {err}")
        i += batch_size

    print(f"\n=== TOTAL: {total_ok} parsed OK, {total_failed} failed, "
          f"{total_no_match} player-rows with no stored-metric match ===")
    summarize("cumulative", dict(
        ok=total_ok, failed=0, exceptions=[], no_name_match=total_no_match,
        army_killed_deltas=all_ak, spending_eff_deltas=all_se,
        army_built_deltas=all_ab, outliers=[],
    ))
    print(f"\nTotal outliers (|army_value_killed delta| > 20000) across all batches: {len(all_outliers)}")
    with open("/tmp/reparse_outliers.tsv", "w") as f:
        f.write("match_id\tplayer_name\told_value\tnew_value\tdelta\n")
        for mid, name, delta, old, new in all_outliers:
            f.write(f"{mid}\t{name}\t{old}\t{new}\t{delta}\n")
    print(f"Full outlier list written to /tmp/reparse_outliers.tsv ({len(all_outliers)} rows)")
    con.close()


if __name__ == "__main__":
    main()
