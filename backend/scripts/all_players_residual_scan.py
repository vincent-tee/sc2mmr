"""Read-only: scan EVERY player (not just pre-registered ones) for the
"team beats the win-probability model" residual pattern found for
ShadowDragon, to answer: is this a few individuals, or a sign the rating
formula itself needs recalibrating?

Explicitly exploratory, not confirmatory -- this is the multiple-comparisons
scan named_player_effect_eval.py deliberately avoided by only testing two
pre-named players. Anything found here is a LEAD, not a validated effect: at
~16-18 players tested, a naive 95% CI already expects roughly one false
positive by chance alone. Reported per sc2mmr-research-methodology: numbers,
baseline, and the multiple-comparisons caveat together, not a bare list.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from named_player_effect_eval import load_matches, match_residuals, per_player_signed_residuals, bootstrap_mean_ci
from walkforward_session_eval import DB

MIN_GAMES = 50


def scan(con, label):
    pid_to_name = dict(con.execute("SELECT id, name FROM players").fetchall())
    usable = load_matches(con)
    rows = match_residuals(usable)
    by_player = per_player_signed_residuals(rows)

    results = []
    for pid, vals in by_player.items():
        if len(vals) < MIN_GAMES:
            continue
        ci = bootstrap_mean_ci(vals)
        results.append(dict(
            name=pid_to_name.get(pid, f"id={pid}"), n=len(vals),
            mean=ci["mean"], lo=ci["lo"], hi=ci["hi"],
            survives=ci["lo"] > 0 or ci["hi"] < 0,
        ))
    results.sort(key=lambda r: r["mean"], reverse=True)

    overall_mean = sum(r["mean"] * r["n"] for r in results) / sum(r["n"] for r in results)
    print(f"\n=== {label}: {len(results)} players with >= {MIN_GAMES} games ===")
    print(f"Population-weighted mean residual across all of them: {overall_mean:+.4f} "
          f"(should be ~0 if the model is well-calibrated overall)")
    print(f"{'name':<15} {'n':>5} {'mean':>8} {'95% CI':>20}  survives-alone?")
    for r in results:
        flag = "  <-- CI excludes zero" if r["survives"] else ""
        print(f"{r['name']:<15} {r['n']:>5} {r['mean']:>+8.3f} "
              f"[{r['lo']:>+.3f}, {r['hi']:>+.3f}]{flag}")

    n_tested = len(results)
    n_survive = sum(1 for r in results if r["survives"])
    print(f"\n{n_survive}/{n_tested} players individually clear a 95% CI excluding zero.")
    print(f"Expected by chance alone at n={n_tested}, alpha=0.05, with nothing real happening: "
          f"~{0.05 * n_tested:.1f}")
    return results


def main():
    all_results = {}
    for label, path in [("local dev", DB),
                         ("prod", "file:/home/vtee/.claude/jobs/969106c5/tmp/prod-before.db?mode=ro")]:
        con = sqlite3.connect(path, uri=True)
        all_results[label] = scan(con, label)
        con.close()

    # Cross-dataset consistency check: which names show up as "survives" in BOTH datasets?
    survive_local = {r["name"] for r in all_results["local dev"] if r["survives"]}
    survive_prod = {r["name"] for r in all_results["prod"] if r["survives"]}
    both = survive_local & survive_prod
    print(f"\n=== Cross-dataset check ===")
    print(f"Survives in local dev only: {survive_local - survive_prod}")
    print(f"Survives in prod only: {survive_prod - survive_local}")
    print(f"Survives in BOTH (the only ones worth taking seriously): {both}")


if __name__ == "__main__":
    main()
