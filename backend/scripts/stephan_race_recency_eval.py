"""Read-only: is Stephan's Zerg specifically stronger, and stronger recently?

Owner's claim (2026-09-15): Stephan's Zerg has felt more devastating lately.
Pre-registered as two sub-checks:

A. Race split: does Stephan's TEAM beat the win-probability model more when
   he plays Zerg than when he plays Terran (leak-free, same model as
   named_player_effect_eval.py)?
B. Recency trend, Zerg only: within his Zerg games specifically, has his own
   box-score performance (overall_impact) trended upward over time, and is
   his second-half-of-Zerg-history team-beats-prediction residual bigger
   than his first-half?

Caveat up front, not after the numbers: splitting by race and then by time
leaves small subsets (roughly 80-90 games per half at best). Any CI here
will be wide. This is a first look, not a proof either way -- same standard
as every other check this session.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sqlite3
from named_player_effect_eval import load_matches, match_residuals, bootstrap_mean_ci
from walkforward_session_eval import DB


def stephan_games_with_race(con, name="Stephan"):
    pid = con.execute("SELECT id FROM players WHERE name=?", (name,)).fetchone()[0]
    race_by_match = dict(con.execute(
        "SELECT match_id, race FROM match_players WHERE player_id=?", (pid,)
    ).fetchall())
    return pid, race_by_match


def race_split_residuals(con, label):
    pid, race_by_match = stephan_games_with_race(con)
    usable = load_matches(con)  # already played_at-ascending; match id order is NOT reliable (backfilled history)
    rows = match_residuals(usable)

    by_race = {"TERRAN": [], "ZERG": []}
    for seq, r in enumerate(rows):  # `seq` preserves the true chronological position
        race = race_by_match.get(r["mid"])
        if race not in by_race:
            continue
        signed = r["residual"] if pid in r["t1_ids"] else (-r["residual"] if pid in r["t2_ids"] else None)
        if signed is not None:
            by_race[race].append((seq, signed))

    print(f"\n=== {label}: Stephan's team-beats-prediction residual, by race ===")
    for race, vals in by_race.items():
        if len(vals) < 10:
            print(f"  {race}: n={len(vals)} -- too few to assess")
            continue
        signed_only = [v for _, v in vals]
        ci = bootstrap_mean_ci(signed_only)
        print(f"  {race}: n={len(vals)}, mean signed residual={ci['mean']:+.3f}, "
              f"95% CI [{ci['lo']:+.3f}, {ci['hi']:+.3f}]")

    return by_race


def zerg_recency_check(con, label, by_race):
    zerg = sorted(by_race["ZERG"], key=lambda x: x[0])  # sort by match id (chronological in this schema)
    n = len(zerg)
    if n < 20:
        print(f"\n=== {label}: not enough Zerg games ({n}) for a recency split ===")
        return
    half = n // 2
    first_half = [v for _, v in zerg[:half]]
    second_half = [v for _, v in zerg[half:]]
    ci_first = bootstrap_mean_ci(first_half)
    ci_second = bootstrap_mean_ci(second_half)
    print(f"\n=== {label}: Zerg games split in half chronologically (n={half} each) ===")
    print(f"  Earlier Zerg games:  mean residual={ci_first['mean']:+.3f}, 95% CI [{ci_first['lo']:+.3f}, {ci_first['hi']:+.3f}]")
    print(f"  Recent Zerg games:   mean residual={ci_second['mean']:+.3f}, 95% CI [{ci_second['lo']:+.3f}, {ci_second['hi']:+.3f}]")

    # Own box-score trend (less confounded by teammates than the team-outcome residual).
    pid, race_by_match = stephan_games_with_race(con)
    impact_rows = con.execute("""
        SELECT mp.match_id, m.played_at, pmm.overall_impact
        FROM match_players mp
        JOIN matches m ON m.id = mp.match_id
        JOIN player_match_metrics pmm ON pmm.match_player_id = mp.id
        WHERE mp.player_id = ? AND mp.race = 'ZERG' AND pmm.overall_impact IS NOT NULL
        ORDER BY m.played_at ASC
    """, (pid,)).fetchall()
    if len(impact_rows) >= 20:
        vals = [r[2] for r in impact_rows]
        half2 = len(vals) // 2
        print(f"\n  Own overall_impact (box score, n={len(vals)} Zerg games with data):")
        print(f"    Earlier half mean={statistics.mean(vals[:half2]):.1f}, "
              f"Recent half mean={statistics.mean(vals[half2:]):.1f}")
    else:
        print(f"\n  Only {len(impact_rows)} Zerg games have overall_impact recorded -- too few for a trend.")


def main():
    for label, path in [("local dev", DB),
                         ("prod", "file:/home/vtee/.claude/jobs/969106c5/tmp/prod-before.db?mode=ro")]:
        con = sqlite3.connect(path, uri=True)
        by_race = race_split_residuals(con, label)
        zerg_recency_check(con, label, by_race)
        con.close()


if __name__ == "__main__":
    main()
