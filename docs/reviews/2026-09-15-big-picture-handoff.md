# SC2MMR — big-picture handoff (2026-09-15)

> **Later audit — read before relying on the conclusions below:**
> [Methodology audit and coordination experiment plan](2026-09-15-methodology-audit-and-coordination-plan.md).
> It found that the databases share all local matches, the formula's correlation check measures the wrong quantity, and the player scan applies no multiple-comparisons correction. The probability-calibration improvement reproduced, but several mechanism, replication, null-result, and named-player claims below need the qualifications in that audit. This original handoff is retained as the historical record.

For a fresh, stronger model picking this up cold. Read this before touching rating/balancing code — it exists so you don't re-derive or re-litigate what's already settled, and don't repeat the mistakes already made and fixed here.

## What this project is

A StarCraft II team-balancing and rating system for a ~19-person friend group, 6+ years of match history (860+ games), FastAPI/SQLAlchemy backend, React frontend, deployed on Vercel + Cloud Run + Litestream-replicated SQLite. Owner's stated north star: **"the best balancing with the coolest but most accurate tech"** — both halves matter; a cool technique that doesn't measurably help is not wanted, and neither is settling for a worse baseline out of caution.

## The governing discipline (read this before proposing anything)

This project has a documented history of "ML overselling" as its costliest failure mode: installing impressive-looking machinery, reporting an optimistic number, moving on. The counter-discipline, enforced this session and expected to continue:

1. **State a hypothesis and a kill criterion before running the experiment.**
2. **Validate out-of-sample** — fit any free parameter on earlier sessions only, score on strictly later, untouched sessions. In-sample or full-dataset numbers are not evidence.
3. **Actively try to break your own positive result** before reporting it (alternate metrics, remove outliers, check a second independent dataset, look for confounds) — not just accept the first favorable number.
4. **Multiple-comparisons discipline**: if you scan many candidates (players, features, thresholds), expect a nominal ~5% false-positive rate per comparison and say so; don't report a scan hit as if it were pre-registered.
5. **Every claim states its baseline and sample size next to the number.** "71% accuracy" alone is not a claim; "71% vs 64% baseline, n=837, 95% CI [x,y]" is.
6. Two independent datasets exist for cross-checking: local dev (`backend/data/sc2mmr.db`, 837-860 matches, frozen as of ~2026-07-05) and a production pull (fresher, ~850-874 matches, extends to September). Findings that hold in both are far more trustworthy than single-dataset results.

## What is now the rating-of-record (settled, don't re-litigate)

- **Display MMR** = `1000 + 100*mu - 200*sigma`. This specific doctrine (sigma penalized, "ranks are earned through games") was deliberately chosen over a no-sigma alternative via measured evidence in an earlier campaign phase — don't revert it without new evidence overturning that decision.
- **mu/sigma** come from a *single shared policy module*, `backend/app/rating_policy.py` — inactivity decay, session-gap calculation, and win-probability math all live there, and live ingestion, the balancer, and the offline evaluator all call the same functions. This consolidation is this session's main structural contribution; previously these three paths had silently diverged (different decay handling, different beta values) and nobody had noticed. If you find a fourth divergent implementation, that's a bug — the intent is exactly one.
- **The per-match individual-performance rating adjuster** (`app/performance_rating.py`) was found wired into every live rating path, silently compounding since 2025-11, never validated. It has been disconnected from all live paths (kept in the repo, tested, dormant) pending proper validation via the harness below. Do not re-wire it without running it through that harness first.
- **A full, in-place chronological recalculation** (`app/services/rating_recalculation.py`, exposed as `POST /players/recalculate-ratings`) has been run against production. It replaces the old standalone script's approach (which used a separate DB connection without the app's foreign-key enforcement, deleted and rebuilt rows, and could silently orphan child records) with an update-in-place implementation using the app's own FK-enforced session. This is now the only sanctioned way to recalculate; the old `scripts/recalculate_all_mmrs.py` should be treated as legacy/dangerous, not run again as-is.

## The one validated formula change this session (adopt, don't re-test from scratch)

`win_probability()`'s extra "performance noise" term was a flat `n_players * beta^2` regardless of how converged a player's own rating is. Found via: scanning every player (not just a couple of named ones) for "does this player's team beat the model's own prediction," discovering **Pearson r = +0.56 to +0.61** between a player's skill (mu) and that residual, in both datasets, robust to removing the top outlier. Mechanism: strong/converged players were systematically under-predicted; weak/unconverged players over-predicted.

**Fix, now live:** `variance = sum(sigma_i^2) * (1 + k)` instead of the flat beta term. `k=11` found independently as the true out-of-sample optimum in both datasets (first grid search hit its own boundary at k=5 and was caught before being trusted — always widen a grid that lands on its edge). Held-out log-loss improved +0.09 to +0.10 with bootstrap 95% CIs excluding zero in both datasets; the motivating correlation dropped to near-zero on data the fit never saw. This is prediction-only — it does not touch `trueskill.rate()`, mu, sigma, or display MMR.

## What was tested and killed (don't re-propose without new evidence)

- **Uncertainty-aware team balancing** (rank splits by TrueSkill quality instead of raw MMR difference): no improvement, actually slightly worse, in both datasets. `backend/scripts/uncertainty_aware_balance_eval.py`.
- **Teammate chemistry / pairwise synergy residual**: null in both datasets, survived a stricter-threshold robustness check and a check that the comparison baseline wasn't artificially weak. `backend/scripts/synergy_residual_eval.py`.
- **Composite vs. default balancer objective**: genuinely mixed — composite wins on win-probability closeness, loses on rating-difference closeness, both effects real (CIs exclude zero) but pointing opposite directions. No promotion criterion met; balancer default is unchanged. `backend/scripts/balancer_objective_shootout.py`.

## Open, unresolved leads (real signal, not yet strong enough to act on)

- **One player ("ShadowDragon", formerly merged from "DragonKing" in production only — local dev still has the pre-merge name) shows the highest "team beats prediction" residual of anyone in the dataset** (+0.029 mean, ranks 88th-94th percentile among comparable players, consistent direction in both datasets) but the confidence interval still includes zero. Not proven. `backend/scripts/named_player_effect_eval.py` and `backend/scripts/all_players_residual_scan.py`.
- **A specific qualitative mechanism was reported firsthand** (a top player directing a teammate's play to shut down a particular opponent) for one real match, logged as post-game feedback (`match_id=1163`). One data point. If this kind of report recurs across multiple games for the same player, that becomes a real, testable pattern; right now it's an anecdote worth tracking, not a formula input.
- **The human-judgment/selected-game tracking feature exists specifically to accumulate prospective evidence on both of the above.** It was built this session (`pregame_judgments`, `postgame_feedback`, `balance_selections` tables; `/judgments/*` API; `SelectedGameCapture`/`JudgmentCapture`/`PostgameFeedback`/`MatchBalanceFeedback` frontend components) and verified working end-to-end against production with a real browser test — but it has essentially zero real usage data yet. Nothing about it can be evaluated until organizers actually use it across a meaningful number of games.

## Known-stale / not-yet-reconciled

- **Historical `match.predicted_team1_win_prob` values are stale** relative to the current rating_policy and the recalculation — that field is a per-match snapshot set at ingestion time and is not touched by the recalculation (which only updates `mu_before/after`, `sigma_before/after`). Old matches will show predictions computed under the pre-fix formula/ratings. Cosmetic/historical-accuracy issue on the match-detail page only; does not affect live balancing.
- **375 (local) / 287 (production) orphaned `player_match_metrics` rows** from historical bulk-delete operations that didn't cascade — local dev repaired, production repair endpoint built and tested but not yet run against production as of this writing (confirm current state before assuming either way).
- **A duplicated, low-priority reimplementation of full recalculation logic still exists nowhere else** — the admin endpoint and the recalculation service are now the single implementation; there is no longer a third divergent path (there had been three at session start).
- **The "AI-powered match commentary" feature on the match-detail page is not actually AI** — it's template string interpolation over computed stats, despite the name. A real LLM-based advisory layer (for notes, team explanations, or judgment assistance) was designed in a prior review but never implemented; if building this, the existing design constraints (structured output only, human confirms before anything is applied, never let model output touch mu/sigma directly, validate against a schema, track cost/latency) should be followed rather than re-derived.

## Falsifiable next steps, roughly in order of expected value

1. Get real usage on the judgment/selection tracking feature (zero cost to the codebase, all cost is social/adoption).
2. Once ~50+ prospective selections exist, re-run the residual scan on *that* data instead of retrospective simulation — this is the first chance to actually test "does human judgment beat the model" rather than "does the model fit its own history."
3. If the ShadowDragon lead keeps showing up as more games accumulate (both from natural play and from the "same player + same partner" pattern), it becomes a real candidate for either a documented rating adjustment or an explicit acknowledgment that raw win/loss already captures it and the residual is noise.
4. The composite-vs-default balancer objective tradeoff (point 3 above) is a real, unresolved product decision — someone with product judgment (not just statistics) needs to decide whether "closer to 50/50" or "closer sum-MMR" is the actual design goal, since the data says you can't have both simultaneously here.

## House rules that still apply

Backup before any DB-mutating action. No formula change ships without out-of-sample validation and explicit sign-off. No accuracy claim without a stated baseline and cross-validation. Production infrastructure changes (deploys, scaling config, secrets) require explicit, specific authorization each time — general "keep going" instructions do not cover them, by design.
