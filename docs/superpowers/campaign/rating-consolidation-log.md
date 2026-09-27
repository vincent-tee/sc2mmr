# Rating Consolidation Campaign — Log

Append-only. One dated entry per session: phase, commands run, numbers observed, gate verdicts, open questions. Next session starts by reading this file, then `.claude/skills/sc2mmr-rating-consolidation-campaign/SKILL.md`.

---

## 2026-07-02 — Session 1: Phase 0 (baseline snapshot) + Phase 1 (rating census)

Executor: Claude (Fable 5) session, owner present.

### Phase 0 — Baseline snapshot: COMPLETE, gate PASS

**0.1 Backup:** `backend/data/sc2mmr.db.backup_20260702_182116` (40,300,544 bytes) — verified present.

**0.2 State numbers (all exactly match the skill's expected values — zero drift):**

| Metric | Value |
|---|---|
| matches / players / match_players | 863 / 160 / 5,661 |
| matches with complete combat metrics | 706 (81.8%) |
| migration 015 columns (`unified_mmr_before/after`) | ABSENT |
| players with non-null `unified_mmr` | 19 |

Top-10 by unified_mmr (core, non-AI, ≥15 games): Stephan 4652.8 (730g), HahaLolo 4429.3 (204g), Sirhc 4275.1 (198g), shunmanFan 4142.5 (544g), androidsine 4019.0 (73g), DragonKing 3858.3 (394g), ChrisO 3687.5 (843g), LayManFan 3525.6 (198g), Tingmore 3381.8 (619g), banzo 3314.5 (201g).

Quirk on record: `Computer (Elite)` (AI, 24 games) holds unified_mmr 4196.4 — would rank 4th without the `is_ai=0` filter. Queued for Phase 6 data fix.

**0.3 Baseline anchors (team-SUM variant, chronological pre-match values):**

| Predictor | Accuracy |
|---|---|
| **THE baseline: higher sum(`mmr_before`) wins** | **553/860 = 64.3%** |
| higher sum(`mu_before`) wins | 537/860 = 62.4% |
| stored `predicted_team1_win_prob` > 0.5 | 543/859 = 63.2% |

Within ±0.0% of the skill's expected values. NOTE: stored `mmr_before` embeds the −200σ formula (Phase 3); Phase 2 must use the mu/sigma simulator.

**0.4 Test suite:** `4 failed, 59 passed` — exactly the expected four: 3× `test_basic` display-MMR TypeErrors (= the Phase 3 conflict) + `test_ml_pipeline_e2e` (unrelated, experience-gate; tracked separately via sc2mmr-validation-and-qa).

**Gate verdict: PASS — no drift since 2026-07-02 skill authoring; proceed to Phase 1.**

### Phase 1 — Rating census: COMPLETE, success criterion met (zero `?` cells)

Storage (players table): `mu`, `sigma`, `mmr`, `recency_weighted_mmr`, `hybrid_mmr`, `session_weighted_mmr`, `handicap_corrected_mmr`, `unified_mmr` — 6 rating columns + mu/sigma, as expected.

**Census table — final (every cell grep-proven this session):**

| # | Variant | Stored | Computed by | Consumed by (grep-proven) | Status |
|---|---|---|---|---|---|
| 1 | `mmr` (display TrueSkill) | players.mmr; match_players.mmr_before/after | `rating_system.py:calculate_display_mmr` (CONFLICTED formula, Phase 3) | `/leaderboard/raw_mmr` (no frontend caller); `/teams/balance-with-ai` (sums p.mmr); `/teams/predict`; `/players/{id}/history` chart; base of HC-MMR | base layer — keep (formula TBD Phase 3) |
| 2 | `unified_mmr` | players (19 rows), NO per-match history | `handicap_mmr_service.py:171` (LIVE formula ≠ both specs) | `/leaderboard/mmr` = the default leaderboard (frontend `leaderboardApi.getMMR` ✓); balancer team sums `balancer.py:149-151` (display only, NOT sort key); players API; analyze_balance_quality | rating-of-record CANDIDATE (Phase 2 must validate) |
| 3 | `handicap_corrected_mmr` | players (19 rows) | same service | `/leaderboard/trueskill` (NO frontend caller); `/teams/balance-true-skill` (endpoint BROKEN, see below) | retirement candidate after Phase 2 |
| 4 | `hybrid_mmr` (PIM) | players (160 rows) | `rating_system.py` hybrid block (`hybrid_mmr_enabled=True`) + recalc script | `/leaderboard/hybrid` (NO frontend caller); players API detail | retirement candidate (soft-retire via config flag first) |
| 5 | `recency_weighted_mmr` | players (160 rows) | `rating_system.py:360-388`; `rating_service.py:782-804` | players API responses (players.py:86,313); ML feature inputs (ml_predictor.py:325, ml_prediction_service.py:82); adaptive_balancer.py:205; component_accuracy_tracker (formula base). NO leaderboard endpoint reads it — `/leaderboard/recent-form` recomputes inline from mp.mmr_after (confirmed: zero hits in leaderboard.py) | retirement candidate; ML feature deps must be rewired first |
| 6 | `session_weighted_mmr` | players (18 rows) | `session_weighted_ratings.py` + `scripts/backfill_session_mmr.py` | adaptive_balancer (deprecated endpoint); `app/api/adaptive.py` router (mounted). **UI: MLIntelligence.tsx calls `/adaptive/*` endpoints** (accuracy-comparison, shap-importance, models status, prediction-logs, train) — so retiring the adaptive router breaks the ML Intelligence page; session_weighted_mmr itself has NO direct frontend reference | retirement candidate; MLIntelligence page is the blocking consumer of the router (not of the column) |
| 7 | timing_adjusted (derived, not stored) | — | `balancer.py:29-30` PlayerInfo bonus | `/teams/balance-timing-adjusted` only (endpoint BROKEN; no frontend caller) | retirement candidate |
| 8 | blended rating | — | `app/blended_rating.py` AND `app/services/blended_rating.py` (divergent twins) | **DEAD — grep for imports returns nothing** (only hit is a def inside the module itself) | confirmed dead code; Phase 6 delete |

**Frontend consumption (verified):** leaderboard calls = `/leaderboard/mmr`, `recent-form`, `specialists`, `winrate`, `winstreak`, `duos`, `trios`, `meta-report`, plus `/impact/leaderboard/{category}`. Teams calls = `balance`, `quick-balance`, `balance-with-custom-players`, `balance-with-ai` (via ai-difficulties flow), `predict`, `balance-with-impact`*, `balance-with-model`, `compare-models`, `models`. NO frontend calls to: `leaderboard/hybrid`, `leaderboard/trueskill`, `leaderboard/raw_mmr`, `balance-true-skill`, `balance-timing-adjusted`.

*`balance-with-impact` is referenced only inside `frontend/src/api/endpoints.ts:118` (`balanceWithImpact`) — **no page component calls it** (grep outside api/ returns nothing). The broken endpoint is therefore not user-reachable.

**Broken endpoints re-confirmed this session:** `teams.py` calls `TeamBalancer.balance_with_impact_priority` (:627), `balance_teams_timing_adjusted` (:1447), `balance_teams_true_skill` (:1616) — none of these methods exist in the working-tree `balancer.py` (methods present: generate_team_suggestions, balance_teams, quick_balance, analyze_suggestion + helpers). All three endpoints 500 on invocation. Owner decision pending (fix vs retire in Phase 6).

**Formula divergence on record (Phase 2/4 blocker):** live `unified_mmr` = `hc_mmr + min(1200, 25·min(combat,60) + 4·eco + 2·eff)` (`handicap_mmr_service.py:144-171`) vs SPEC-UNIFIED-MMR (`hc + 20·combat`) vs trajectory design (`raw + handicap·3000 + 20·combat`). Three formulas on paper; Phase 2 arms D (spec) and E (live) will measure both.

**Success criterion: MET** — zero `?` cells remain; every claim above is backed by a grep/query run this session.

### Open questions carried forward
1. Phase 2: build `scripts/rating_shootout.py` (read-only, mu/sigma-derived variants A, A′, A″, B, C, D, E; McNemar vs A per binding rule 2.1(5)).
2. [OWNER GATE] queued for after Phase 2 evidence: display-MMR sigma decision (Phase 3); fate of the 3 broken team endpoints; AI-player unified_mmr fix.
3. Note for Phase 6 preconditions discovered this session: MLIntelligence page is the live consumer of the `/adaptive` router; `recency_weighted_mmr` feeds ML predictor features and must be rewired before column retirement; `balanceWithImpact` frontend API function is itself dead code.

**Next session: Phase 2 — predictive shoot-out.**

---

## 2026-07-02 — Session 2: Phase 2 (predictive shoot-out) + branch 2.4 (coefficient re-fit)

Executor: Claude (Fable 5) session, owner present.

### Method

Simulator: `backend/scripts/rating_shootout.py` (new, read-only, `mode=ro`). Chronological pass over all 863 matches (`played_at ASC`); every variant derived per match from stored `mu_before/sigma_before`; handicap outperformance and combat/eco/eff averages use PRIOR matches only (design-doc running-stats algorithm; expected-WR base = arm-A display values; spec combat default 25.0, live defaults 20/50/50). Ties excluded (3). Verdict rule as pre-registered in the skill: beats baseline iff delta>0 AND McNemar exact p<0.05, or delta≥+2pp with p<0.10.

### Results — full history (n≈860 decided)

| Arm | Accuracy | Δ vs A | McNemar b/c | p | bootstrap 95% CI |
|---|---|---|---|---|---|
| A: 1000+100μ (no-sigma) | 533/860 = 62.0% | — | — | — | — |
| **A′: 1000+100μ−200σ** | **553/860 = 64.3%** | **+2.3pp** | 29/49 | **0.0308** | [+0.2%, +4.4%] |
| A″: 1000+100μ−300σ | 555/860 = 64.5% | +2.6pp | 46/68 | 0.0487 | [+0.1%, +4.9%] |
| B: TrueSkill win-prob | 537/860 = 62.4% | +0.5pp | 12/16 | 0.57 | [−0.7%, +1.6%] |
| C: A + outperf×3000 | 523/861 = 60.7% | −1.2pp | 77/67 | 0.45 | [−3.8%, +1.5%] |
| D: C + 20×combat (SPEC unified) | 522/862 = 60.6% | −1.4pp | 75/64 | 0.40 | [−4.1%, +1.5%] |
| E: C + min(1200, 25c+4e+2f) (LIVE unified) | 524/862 = 60.8% | −1.2pp | 76/67 | 0.50 | [−4.0%, +1.6%] |

Complete-metrics subset (n=706): same ordering — A′ 64.8% (p=0.033 vs A), A″ 64.9%; C/D/E ≈ A (60.0–62.4%, all p=1.0). F (hybrid/PIM chain): not measured (recorded per skill option). A′ vs A″ head-to-head: 17/19 discordant, p=0.87 — statistically indistinguishable.

### Branch 2.4 — coefficient re-fit (`backend/scripts/rating_shootout_grid.py`, read-only)

147-cell grid (σ-coef {0,200,300} × handicap {0..4000} × combat {0..30}), chronological 5-block nested CV (best cell selected on 4 blocks, scored on the 5th). **Out-of-fold accuracy of the select-best-cell procedure: 543/862 = 63.0% — WORSE than plain A′ (64.3%) and A″ (64.5%).** Full grid shows accuracy flat-to-declining in both handicap and combat directions at every sigma level; all predictive signal is in the sigma coefficient. The re-fit FAILS.

### GATE P2 verdict (per pre-registered rules)

1. **Neither D nor E beats A** — both are ~1.2–1.4pp WORSE. The re-fit branch also failed.
2. Therefore the rating-of-record candidate = best of {A, A′, C} = **A′ (1000+100μ−200σ)**, with A″ statistically tied (choice between them is a churn/product call, not an evidence call; A′ matches the current DB and working-tree code).
3. **NEGATIVE RESULT, recorded prominently: the "+2.2–2.6pp unified MMR lift" (SPEC-UNIFIED-MMR, n≈153–300 era) does NOT replicate at n=863 under honest no-lookahead evaluation. The handicap correction (×3000) and combat bonus (20× or live 25×+eco+eff) are RETIRED as accuracy claims.** Corroborating evidence: the lookahead unified proxy scores 64.9% (Phase 0 reference row) while honest D/E score 60.6–60.8% — the earlier validation's lift is consistent with lookahead contamination (fenced path #6 symptom).
4. Phase 3 evidence delivered as a by-product: A vs A′ = 62.0% vs 64.3%, McNemar p=0.031 — the −200σ side wins on prediction.

**[OWNER GATE] presented to owner this session: crown A′ (or A″) as rating-of-record candidate; disposition of handicap/combat components (retire from rating-of-record; optionally keep as display-only stats). Awaiting owner decision — Phases 3+ blocked on it.**

### Notes
- Caveat for honesty: prediction accuracy is the campaign's promotion metric, but the handicap correction was originally motivated by leaderboard *fairness* (balancing bias), not prediction. The owner may knowingly keep such components as display-only stats; they may not be part of the rating-of-record without predictive evidence (north star: cool-but-proven).
- S2/S3 (ablations, sigma-aware balancing with Brier calibration) remain open solution-menu items if the owner wants deeper investigation before deciding.
- SKILL.md Phase 2.3/Phase 3 expected numbers updated with these measured results (maintainer rule).

---

## 2026-07-02 — Session 3: GATE P2 + Phase 3 (display-MMR doctrine) — RESOLVED & EXECUTED

Executor: Claude (Fable 5) session, owner present.

### Owner decisions (GATE P2 + Phase 3 combined, decided 2026-07-02)

1. **Rating of record = A′: display MMR = 1000 + 100·mu − 200·sigma.** Rationale: measured winner (64.3% vs 62.0%, McNemar p=0.031); statistically tied with A″ (p=0.87) but matches the current DB and working-tree code (least churn); resolves the sigma doctrine toward "earned ranks" WITH predictive evidence.
2. **Handicap correction + combat bonus → display-only stats.** Retired from the rating of record (accuracy claims retired in Session 2). `unified_mmr` / `handicap_corrected_mmr` columns queued for Phase 6 retirement; outperformance % and combat score remain as player-card stats.

### Execution (per Phase 3 runbook, routed through change-control)

1. **Backup:** `data/sc2mmr.db.backup_20260702_183611` (fresh, pre-recalc).
2. **Code + tests made consistent as one change:**
   - `app/rating_system.py:calculate_display_mmr` docstring now records the settled doctrine with the measured evidence.
   - `tests/test_basic.py`: the 3 failing tests rewritten to the −200σ doctrine (formula asserted directly; new-player default 1833 ≈ formula value; sigma-penalty monotonicity asserted). Class runs 18/18 green.
   - **NOT committed to git** — the entire working tree is intentionally uncommitted (owner's in-flight state); committing is deferred to the owner. Deviation from the runbook's "commit as ONE change" noted here.
3. **Full recalc:** `scripts/recalculate_all_mmrs.py` ran clean (all 6 steps incl. recency + HC/unified update).
4. **Validation (all success criteria MET):**
   - `pytest -q` → **1 failed, 62 passed** — only `test_ml_pipeline_e2e` remains (pre-existing, tracked separately).
   - Formula spot-check: ChrisO 2952.8, Stephan 3856.7, Tingmore 2807.7 — stored == formula, diff 0.000 for all three.
   - Row counts intact: 863 / 160 / 5,661.

### Before/after leaderboard diff (unified_mmr top-10, for owner acknowledgment)

| # | Before (Session 1) | After recalc |
|---|---|---|
| 1 | Stephan 4652.8 | Stephan 4801.8 |
| 2 | HahaLolo 4429.3 | Sirhc 4416.3 (↑1) |
| 3 | Sirhc 4275.1 | HahaLolo 4284.1 (↓1) |
| 4 | shunmanFan 4142.5 | shunmanFan 4227.0 |
| 5 | androidsine 4019.0 | androidsine 4045.6 |
| 6 | DragonKing 3858.3 | DragonKing 3833.4 |
| 7 | ChrisO 3687.5 | ChrisO 3762.4 |
| 8 | LayManFan 3525.6 | Tingmore 3663.7 (↑1) |
| 9 | Tingmore 3381.8 | LayManFan 3417.3 (↓1) |
| 10 | banzo 3314.5 | Redevilz 3387.1 (banzo out) |

New rating-of-record (display mmr) top-10: Stephan 3856.7, Sirhc 3533.9, HahaLolo 3436.9, shunmanFan 3417.5, androidsine 3091.3, ChrisO 2952.8, DragonKing 2875.4, LayManFan 2831.6, Tingmore 2807.7, Cotton 2659.2.

### State after Session 3

- Phase 0 ✅, Phase 1 ✅, Phase 2 ✅ (incl. 2.4), Phase 3 ✅. The 3 test_basic failures are GONE; the sigma conflict is CLOSED.
- **Next: Phase 4 — unified MMR trajectory storage, ADAPTED per the owner's decisions: migration 015 stores the rating-of-record history (display MMR before/after already exists on match_players → Phase 4 reduces to wiring `/players/{id}/history` to the rating of record + chart labels; assess whether new columns are even needed now that rating-of-record == display MMR). Then Phase 5 (balancer rewire to display MMR / win-prob), Phase 6 (retire unified/HC/hybrid/recency/session/blended + broken endpoints, per census preconditions).**
- Skill-record sync dispatched: validation-and-qa (test record), theory-reference (formula conflict), failure-archaeology (entry 1), change-control (Rule 2 incident), debugging-playbook (§5) — updated to reflect the resolution.

---

## 2026-07-02 — Session 4: Phase 4+5 (wire leaderboard/chart/balancer to the rating of record)

Executor: Claude (Fable 5) session, owner present.

### Phase 4 — trajectory storage: COLLAPSED BY THE PHASE 3 DECISION
Rating of record = display MMR, and `match_players.mmr_before/after` already stores its per-match history. Migration 015 and the backfill script are UNNECESSARY — `/players/{id}/history` already returns `mp.mmr_after`, so chart == rating of record natively. The 2026-03-23 trajectory design is superseded (its problem — chart vs badge mismatch — is killed by making the badge read `player.mmr` instead of adding unified history columns). Remaining Phase 4 work (frontend labels) folded into Phase 5's frontend pass.

### Phase 5 — rewire (backend executed this session)
- `app/api/leaderboard.py` `/mmr`: sorts and returns `Player.mmr` (was `unified_mmr`); unified-not-null filter removed.
- `app/balancer.py` `generate_team_suggestions`: team sums = display MMR; **sort key changed from `(-match_quality, |wp-0.5|)` to `(mmr_difference, |wp-0.5|)`** — the rating of record is now decisive.
- `/players/{id}/history`: no change needed (already rating-of-record).
- Frontend consumption rewire + labels + rank-tier threshold adjustment + review: dispatched to a frontend agent (report pending; will be appended).

### Pre-registered criterion: FAILED, adjudicated with evidence (owner may veto)
Before/after on the 20 most recent even rosters (`scripts/balance_rewire_eval.py`, new, read-only):
| Metric | Before | After | Criterion |
|---|---|---|---|
| mean rating-of-record diff of chosen split | 180.5 | **122.0** | decrease ✓ |
| mean TrueSkill \|win-prob − 0.5\| of chosen split | 0.0636 | 0.0915 | ≤ +0.01 ✗ |

Investigation (binding S3 obligation): binned-sort compromises don't exist (bins up to 200 MMR never switch the choice — the objectives genuinely disagree); **Brier scores on all 863 real matches: TrueSkill win-prob 0.2829, Elo-mapped display MMR 0.2906–0.3381 — BOTH worse than a constant 0.5 (0.2500), i.e., both probability oracles are overconfident/miscalibrated on deliberately-balanced matches.** The criterion's oracle (TrueSkill wp) therefore has no standing to veto; the sign-accuracy evidence (display MMR 64.3% vs TrueSkill wp 62.4%, Phase 2) favors the new sort. DECISION: keep the rating-of-record sort; adjudication recorded here for owner veto. Side effect to watch: displayed win probabilities on chosen splits can sit further from 50% (they are overconfident anyway — a calibration fix is queued as research-frontier material).
- Lookahead tripwire `analyze_balance_quality.py`: 66.5% / 69.3% (before: 66.5% / 69.8%) — movement attributable to the Phase 3 recalc, not the balancer edit.
- Tests: 62 passed / 1 failed (unchanged).

---

## 2026-07-02 — Session 5: Phase 6 batch 1 (soft retirements + dead code)

Executor: Claude (Fable 5) session, owner present. Owner sign-off: "continue with phase 6". Code-only session (no DB mutation; no backup needed; no recalc — no formula changed).

### Executed retirements (each grep-proven zero consumers first)
1. **Blended twins DELETED**: `app/blended_rating.py` + `app/services/blended_rating.py` (zero importers re-proven). Grep now returns 0 refs.
2. **Three broken team endpoints DELETED** (methods were absent from balancer.py; zero frontend page callers): `/teams/balance-with-impact`, `/teams/balance-timing-adjusted`, `/teams/balance-true-skill` — 482 lines removed from `app/api/teams.py` incl. their request/response models. Repair during surgery: `ModelBalanceResponse`, `BalanceWithModelRequest`, `BalanceQualityMetrics` were co-located in the deleted spans but still used by surviving routes — restored verbatim (first two from HEAD, third reconstructed from its constructor call). Import + full suite verified after.
3. **Five uncalled leaderboard endpoints DELETED**: `/leaderboard/hybrid`, `/trueskill`, `/raw_mmr`, `/tactical`, `/achievements` (frontend's getByCategory is a closed switch over {mmr, recent-form, combat, winrate, winstreak, duos, trios} — proof captured). `/categories` mmr description fixed to display MMR.
4. **hybrid_mmr SOFT-RETIRED**: `hybrid_mmr_enabled` default flipped to False (config.py:143) — rating_system's hybrid block now skipped. Note: `recalculate_all_mmrs.py` still writes hybrid values unconditionally (flag not consulted there); harmless staleness until the column drop, recorded as a Phase 6 batch-2 item.
5. **AI data fix**: `HandicapCorrectedMMRService.update_all_players` now NULLs unified/HC/outperformance for `is_ai=1` players and excludes AI from the update loop — kills the `Computer (Elite)` top-5 unified quirk at next update.

### Validation (per-retirement success criteria)
- Grep proofs: 0 references to the three deleted team endpoints, 0 to blended_rating.
- `pytest -q`: **62 passed / 1 failed** (unchanged; only test_ml_pipeline_e2e).
- Live boot on :8001: `/health` 200; `/leaderboard/mmr` 200 serving display MMR (Stephan 3856.7 top); `POST /teams/balance` 200 and the chosen split verified minimal-diff (303.4 for the top-4 roster; enumeration-checked); all 8 deleted endpoints return 404.

### Deferred (preconditions recorded in Phase 1 census)
- `session_weighted_mmr` + `/adaptive` router: BLOCKED — MLIntelligence page is a live consumer of `/adaptive/*`. Owner decision needed on that page's fate.
- `recency_weighted_mmr`: BLOCKED — feeds `ml_predictor.py:325` / `ml_prediction_service.py:82` features; rewire first.
- `/teams/balance-with-model`, `/compare-models`, `/models`, `/predict-ml` + `rating_models.py`: frontend api functions exist; page-level usage unverified — batch 2.
- **Column DROPS** (`unified_mmr`, `handicap_corrected_mmr`, `hybrid_mmr`, `recency_weighted_mmr`, `session_weighted_mmr` on players) = migration 016 + backup + owner sign-off — batch 2, after the frontend rewire settles.

### Session 4/5 addendum — frontend rewire + review COMPLETE (agent report, 2026-07-02)

Frontend fully rewired to the rating of record (`player.mmr`): badge/sort/VS-screen/team-total consumption switched in PlayerDetail, Players, HeadToHead, LineupPredictor, Home, PlayerCard, TeamGenerator (14 files). Rank tiers recalibrated for the display scale (Bronze<1500 … GM 3800+; top-10 maps to 1 GM / 3 Master / 5 Diamond / 1 Plat). Review fixed three latent bugs beyond the rewire: (1) guest/AI mu inversion in TeamGenerator understated mu by ~16.7 (win probabilities were skewed for guests) — corrected to `mu = (mmr − 1000 + 200σ)/100`; (2) RatingSystem page displayed a wrong formula (300σ) — now 200σ with recomputed examples; (3) dead `balanceWithImpact` API function removed. Verification: `npm run build` passes, lint clean, tsc baseline 122 → 122 (zero added).

Backend follow-ups from the review, applied same session: `BalancerStats.analyze_suggestion` now uses `p.mmr` (was unified — inconsistent aggregates in /teams/balance); `ai_mmr.json` (both copies) recalibrated from the unified scale to the display scale by top-human ratio ×0.803, rounded to 50: very_easy 1200, easy 1600, medium 2100, hard 2550, very_hard 3050, elite 3600 (preserves elite-just-below-top-human relationship; old values were 1500–4500). Balance regression tests pass (5/5); full suite 62 passed / 1 failed (unchanged).

**Phase 4: SUPERSEDED (no migration needed). Phase 5: DONE. Phase 6 batch 1: DONE. Chart == badge == balancer == leaderboard, all on `player.mmr`.**

---

## 2026-07-06 — Session 6: re-test HC-MMR/unified-MMR prediction accuracy on corrected match data

Executor: Claude (Sonnet 5) session, owner present. Context: this session found and fixed
two data-integrity bugs upstream of every prior campaign measurement — (a) ~172 matches
where the winner couldn't be determined were silently defaulted to "team 2 wins" (parser
bug, fixed), and (b) 15 duplicate matches (same game recorded twice by different
uploaders, one pair with contradictory winners) were removed. n went from 871 to 856
matches at the DB level (833 usable for chronological prediction after excluding
winner-less/one-sided rosters). Every prior Session 2/3 number (60.6-60.8% for the
unified-MMR arms, 62.0% no-sigma baseline, 64.3% -200sigma baseline) was measured
BEFORE these fixes. Owner asked: does the verdict change on corrected data?

**Hypothesis:** HC-MMR / unified MMR's core mechanism (correct a player's rating based on
how they perform relative to what their team's handicap predicted) is a real, previously
untested idea on its own terms - but this project's own prior measurement said it doesn't
survive chronological no-lookahead re-validation. Given the correction only fixed ~20% of
labels and removed <2% of matches, I predict the qualitative verdict is unchanged: HC-MMR
team-sum will NOT beat plain mmr_before team-sum by a statistically real margin, though
the exact percentages will shift slightly with the corrected n.

**Setup:** Extended the leak-free chronological walker (same pattern as
`revalidate_ml_predictor_leakfree.py`) to also reconstruct HC-MMR chronologically per
match: for each player, using ONLY matches strictly before the current one, compute
recency-weighted outperformance (weight relative to *that match's* date, not today -
the production `get_player_handicap_stats` weights relative to `datetime.utcnow()`,
which is itself a lookahead source this harness removes), requiring >=15 prior games
(`HandicapCorrectedMMRService.MIN_GAMES`) or falling back to plain `mmr_before` (matches
production's NULL-for-insufficient-history gate). Formula ported verbatim from
`app/services/handicap_mmr_service.py` (dampening, expected-WR, OUTPERFORMANCE_MULTIPLIER=3000,
confidence=min(1,games/40), inactivity decay). Compared team-sum(plain mmr_before) vs
team-sum(HC-MMR-adjusted) as winner predictors on the same n=833 matches: fresh baseline,
McNemar exact test, bootstrap CI. Script: `backend/scripts/revalidate_hcmmr_leakfree.py`,
read-only.

**Predicted:** HC-MMR team-sum accuracy within +/-1pp of plain team-sum (66.3%); McNemar
p >= 0.05; bootstrap CI on the delta includes zero.

**Observed** (n=833 usable matches, script:
`backend/scripts/revalidate_hcmmr_leakfree.py`, read-only):

| Method | Result |
|---|---|
| Plain team-sum `mmr_before` | 550/830 = 66.3% |
| HC-MMR-adjusted team-sum (leak-free, chronological) | 552/830 = **66.5%** |
| McNemar exact (HC-MMR vs plain) | plain-only-right=40, hc-only-right=42, n_disagree=82, **p=0.91** |
| Bootstrap CI (1000 resamples) | mean +0.3%, **95% CI [−1.8%, +2.4%]** (includes zero), positive in 59% of resamples |

**Verdict: Refuted, consistent with the prior campaign finding.** +0.2pp raw
delta, McNemar p=0.91 (nowhere near significant), bootstrap CI spans zero.
Even after removing the two data-integrity bugs that affected ~20% of match
labels, HC-MMR's outperformance-based correction still does not predict
actual outcomes better than plain display MMR. This settles the open
question from Session 4/5: the corrected data does NOT change the verdict —
Sessions 2/3's finding (unified-MMR arms below baseline) was not an artifact
of the mislabeled data, it holds on clean data too.

**Important scope note on what this does and doesn't prove:** this tests
"does HC-MMR/unified-MMR predict who wins an *already-formed* historical
matchup better than plain MMR." It does NOT directly test "does using
HC-MMR to *construct* team splits produce more competitive games" — that
would require counterfactual data (splits that were never actually played)
that doesn't exist. But the mechanism HC-MMR relies on (a player's
rating-vs-performance gap is real, learnable signal) is the same mechanism
that would have to be true for split-construction to help either — and
that premise itself just failed a third independent test (Session 2/3's
original run, today's ML feature-search entry above, and this one). Absent
new data or a different mechanism, there's no evidence base left to justify
keeping HC-MMR/unified-MMR as anything other than a display-only stat.

**Next:** This directly unblocks Phase 6 batch 2 (`unified_mmr`,
`handicap_corrected_mmr`, `recency_weighted_mmr`, `session_weighted_mmr`
column drops) — the last blocker recorded in Session 5 was "owner decision
needed on the MLIntelligence page's fate," which was resolved in the same
conversation as this experiment (owner decision: strip the ML-as-product
surface, keep the pipeline as an explicit labeled lab, decouple the balancer
from it entirely). Re-entry condition for HC-MMR specifically: a genuinely
new mechanism or substantially more data - not re-running this same test
again without either.

---

## 2026-09-14 — Session 7: leak-free walk-forward evaluation harness (Brier/log-loss/calibration, session-grouped)

Executor: Claude (Sonnet 5) session. Context: `tests/test_balance_regression.py`
predicts past matches using `players.mmr` (present-day rating), which leaks
every later match's outcome into the prediction. Prior sessions (2/3/6) already
established this qualitatively for winner-accuracy using stored `mu_before` /
`sigma_before` and separately for HC-MMR; this session builds a reusable,
general-purpose harness that (a) derives pre-match state from a fresh in-memory
TrueSkill simulation rather than trusting stored `mu_before` (verified: DB
insertion order does not match `played_at` order — 854/860 positions differ,
because replays are backfilled/reprocessed out of chronological order), (b)
scores full probability calibration (Brier, log loss, reliability table), not
just winner accuracy, and (c) groups results by inferred gaming session.

**Hypothesis:** the live TrueSkill win-probability formula
(`RatingSystem.calculate_win_probability`, includes the beta variance term)
should be at least competitive with, and ideally beat, the naive "higher
summed display MMR wins" baseline once every trace of lookahead is removed.

**Setup:** New script `backend/scripts/walkforward_session_eval.py` (read-only,
`mode=ro`, never touches `data/sc2mmr.db`). Walks all 837 usable matches
(2-team, real winner, `played_at` known) in chronological order; maintains an
in-memory `trueskill.Rating` per player starting at the config defaults
(mu=25.0, sigma=8.333, beta=5.0, tau=0.25); for each match, predicts P(team1
wins) from the pre-match ratings only, records the prediction, then calls
`trueskill.rate()` with the real outcome to advance state (matches
`sc2mmr-proof-and-analysis-toolkit` Recipe 9 exactly). The naive baseline uses
the SAME in-memory chronological state fed through the settled display-MMR
formula (1000+100mu-200sigma), summed per team — never `players.mmr`. Gaming
sessions inferred from `played_at` gaps (>4h = new session; gap histogram is
cleanly bimodal — 758/859 consecutive gaps <1h, only 1 between 6h-48h, 100 are
>48h, so any threshold in that range gives an identical partition); 102
sessions found, 98 with >=3 matches.

**Correctness note caught before finalizing:** the first draft of the script
called module-level `trueskill.rate()` without first calling
`trueskill.setup()`, so state ADVANCEMENT silently ran on the trueskill
library's own defaults (beta=4.166, tau=0.0833, draw_probability=0.1) while
PREDICTION used the app's real params (beta=5.0) — an internal inconsistency,
and draw_probability=0.1 is simply wrong for SC2 (no draws). Fixed by calling
`trueskill.setup(mu=25.0, sigma=8.333, beta=5.0, tau=0.25,
draw_probability=0.0)` once at the top of `main()`, mirroring the exact call
`app/rating_system.py` makes at import time. All numbers below are from the
corrected run.

**Observed** (n=837, `python3 backend/scripts/walkforward_session_eval.py`):

| Metric | TrueSkill win-probability | Naive baseline (sum display-MMR, leak-free) | Old leaky number (for contrast) |
|---|---|---|---|
| Winner accuracy | 541/834 = **64.9%** (3 ties excluded) | 551/834 = **66.1%** (3 ties excluded) | 66.3% (`test_balance_regression.py` standalone run, uses present-day `players.mmr` for every historical match) |
| Brier score | 0.2367 | — (not a probabilistic model) | — |
| Log loss | 0.7022 | — | — |
| Bootstrap (1000 resamples), TrueSkill − baseline delta | mean **−1.2%**, 95% CI **[−3.1%, +0.7%]** (spans zero), positive in only 11% of resamples | | |
| Per-session (n>=3, 98 sessions) | TrueSkill beat the baseline in only **18/98** sessions | | |

Calibration table (predicted P(team1 wins) vs actual team1 win rate, 10
buckets): reasonably well calibrated in the middle (0.5-0.8 buckets track
actual rate within ~6pp) but overconfident at the extremes — the [0.9,1.0)
bucket predicts a mean of 0.961 but the actual rate is only 0.803, and
[0.8,0.9) predicts 0.847 vs actual 0.653. The model is too sure of itself on
lopsided-looking matchups.

**Verdict: Refuted (again) — the rating system's win-probability formula does
NOT beat the naive baseline once lookahead is removed; the two are
statistically indistinguishable and the naive baseline is nominally ahead
(and slightly more so than the pre-fix run — the corrected, higher tau/draw
params make the model's sigma trajectory wider and its predictions less
sharp).** This is consistent with, and now extends with proper probabilistic
scoring, every prior no-lookahead finding in this campaign (Sessions 2/3/6:
unified/HC MMR components don't survive; here the base TrueSkill
win-probability formula itself doesn't clearly beat "just sum the display
MMR" either). The gap between the leaky number (66.3%) and the leak-free
numbers (64.9%/66.1%) is smaller than intuition suggests (~0.2-1.4pp) at the
current dataset size, but the leaky number is still inadmissible as a
forward-looking accuracy claim per house rule 3 — the direction of the bias
(leaky ≥ leak-free) is exactly what the no-lookahead doctrine predicts, even
if the magnitude here is modest.

**Next:** `tests/test_balance_regression.py` now documents this limitation
in its module docstring and points here rather than being rewritten in place
(its existing loose assertions — TrueSkill > 50%, ML-metrics within 5% of
TrueSkill — still hold and remain useful as a coarse catastrophic-regression
tripwire). This change adds zero new pytest failures: a full-suite run the
same session showed 202 passed / 2 failed / 5 skipped, but the 2nd failure
(`test_schema_migrations.py::test_empty_database_upgrade_is_repeatable`) and
the extra passing tests both come from a different, parallel in-flight
change (new `backend/migrations/versions/0003_add_judgment_tables.py` and
`backend/tests/test_performance_rating.py`, neither touched by this session)
— not from anything in this entry. `test_ml_pipeline_e2e` remains the one
failure attributable to pre-existing, tracked debt (section 3b of
`sc2mmr-validation-and-qa`). Open follow-up if anyone wants to push on this:
the overconfidence at the [0.8,1.0) probability range is a concrete,
falsifiable target — a beta/tau retune or a shrinkage correction on extreme
probabilities is a candidate next experiment, not yet attempted.

---

## 2026-09-14 — Session 8: retire the un-validated mu-level performance adjuster; reconcile ingestion vs. recalculation

Executor: Claude (Sonnet 5) session, owner present.

**Trigger:** owner asked to reconcile the two divergent rating-transition
implementations flagged in `docs/reviews/2026-09-14-codebase-and-balancing.md`
finding 3 (live ingestion vs. `scripts/recalculate_all_mmrs.py`). A same-session
parallel agent had just fixed a sign bug in
`PerformanceRatingAdjuster.calculate_performance_multiplier` (the loss branch
cushioned bad performances and punished good ones — backwards). Investigating
*why* the two paths diverged, rather than just merging code, surfaced that the
adjuster itself was the actual fork, not a copy-paste accident.

**Findings (all read-only until the fix below):**

1. `PerformanceRatingAdjuster` was added 2025-11-13 (commit `2fda4f0`,
   "Add performance-based rating adjustments and AI-powered match
   commentary") — nine months before this campaign started 2026-07-02. It has
   never appeared in this log, never been run through the Phase 2 shoot-out,
   and has never been called anywhere in `scripts/recalculate_all_mmrs.py`'s
   history (`git log -p --follow` on the script returns zero hits for the
   class name). It mutates `mu` directly, distinct from the (already
   deprioritized) display-level combat/handicap bonuses this campaign
   retired in Phase 2/6 — a separate un-validated formula component had been
   quietly compounding in parallel the whole time.
2. It applies to any match with advanced/parsed metrics attached —
   789 of 860 matches (92%) qualify, not a corner case.
3. Only 4 matches (1146-1149, the most recent by `played_at`, all
   2026-07-05) showed measurable drift from pure TrueSkill at investigation
   time, purely because the 2026-07-02 Phase 3 recalc reset everyone to pure
   TrueSkill and no recalc had run since — the small blast radius was a
   timing accident, not evidence the adjuster is harmless; left alone it
   would have kept compounding on every future advanced upload.
4. A **third**, previously uncatalogued rating-transition implementation was
   found live: `POST /players/recalculate-ratings`
   (`app/api/players.py:520`, admin-gated). It re-derives TrueSkill from
   scratch chronologically like the script, but also applies the same
   adjuster plus its own recency-weighted blend (0.3x at the oldest match,
   1.0x at the newest) that exists nowhere else in the codebase. Grep against
   `frontend/src` and `tests/` for `recalculate-ratings` /
   `recalculate_all_ratings` returned zero hits — unreachable from the UI and
   completely untested, i.e. safe to change without a visible behavior
   change for any real user.
5. Ordering divergence (Session 7 already found DB insertion order disagrees
   with `played_at` order for 854/860 matches) means a byte-identical shared
   transition function still cannot guarantee live ingestion and a full
   recalc converge to the same intermediate history for backfilled data —
   only a full recalc run is authoritative. Recorded as a permanent,
   accepted limitation, not something this session attempted to solve.

**Decision (owner, this session):** strip the mu-level performance adjuster
from the rating of record entirely — pure TrueSkill mu/sigma, matching what
`recalculate_all_mmrs.py` has always computed. Rationale given: every
"smarter" adjustment this campaign has ever measured (Phase 2's unified D/E
variants, Session 7's leak-free win-probability check) has lost to or tied
the simpler baseline; there is zero measured evidence for this specific
adjuster either way since it was never run through Phase 2; and the project
already has a dedicated, separately-tracked channel for individual
performance signal (`hybrid_mmr`/PIM) — mutating the core TrueSkill state
directly would recreate the "eighth rating variant" anti-pattern (fenced
path 1) this campaign exists to prevent. `performance_rating.py` and
`tests/test_performance_rating.py` are kept in the repo, correct and tested,
but disconnected from both live paths — if anyone wants to try this again,
it goes through the walk-forward harness (Session 7,
`scripts/walkforward_session_eval.py`) as a new candidate arm first.

**Changes made:**

- `app/services/ingestion.py`: removed the `PerformanceRatingAdjuster` import
  and the `adjust_ratings_for_match` call in `ingest_match` (previously fired
  whenever `save_metrics` was supplied — i.e. every advanced upload, retry,
  and observer-ingested match).
- `app/api/players.py` (`POST /players/recalculate-ratings`): removed the
  performance-adjustment-plus-recency-blend block entirely; the endpoint now
  does the same pure-TrueSkill re-derivation as the script. Simplified
  `RecalculationStats` to drop the now-meaningless
  `matches_with_performance_adjustments` / `avg_performance_multiplier` /
  etc. fields (unused by any frontend code or test — confirmed by grep
  before removing).
- Full backend suite before and after: 220 passed / 5 skipped / 1
  pre-existing failure (`test_ml_pipeline_e2e`), unchanged.

**Live recalculation executed (house rule 1 + 2):**

```
cp data/sc2mmr.db data/sc2mmr.db.backup_20260914_171132
python3 scripts/recalculate_all_mmrs.py
```

Counts unchanged (860 matches / 159 players / 5,476 match_players — the
159-player count reflects earlier session work in this same conversation,
not this recalc). Top-10 leaderboard by `mmr` shifted by at most ~3.3 MMR
(DragonKing 2982.1 → 2978.8, the largest mover) since only 4 matches had ever
carried the adjuster's effect — consistent with finding 3 above. Spot-check:
re-derived pure `trueskill.rate()` on stored `mu_before/sigma_before` for
matches 1144-1149 now matches stored `mu_after` for all 36 `match_players`
rows to within 1e-6 (previously 20/36 of those rows deviated). Full suite
re-run post-recalc: 220 passed / 5 skipped / 1 pre-existing failure,
unchanged.

**Verdict:** ingestion, the recalculation script, and the admin
recalculation endpoint now compute the identical mathematical rating
transition (pure TrueSkill). The remaining, accepted gap is ordering only
(finding 5) — resolved by running a full recalc after any bulk historical
backfill, not by this change. This is a local-only recalculation
(`backend/data/sc2mmr.db`), not a production deployment; see
`reference-live-deployment` — nothing here has touched Cloud Run.

**Open follow-up:** the third-implementation discovery (finding 4) means
`POST /players/recalculate-ratings` is now functionally redundant with
`scripts/recalculate_all_mmrs.py` except that it doesn't touch
`hybrid_mmr`/`recency_weighted_mmr`/`unified_mmr`/`handicap_corrected_mmr`
the way the script does. Not resolved this session — a real fix is either
deleting the endpoint (it's unreachable from the UI) or making it delegate
to the same underlying logic as the script instead of maintaining a fourth
partial reimplementation.

---

## 2026-09-15 — Session 9: skill-dependent variance fix for win_probability (ADOPTED)

Executor: Claude (Sonnet 5) session, owner present.

**Trigger:** while running `named_player_effect_eval.py`'s full-population
residual scan (every player with >=50 games, not just pre-registered names),
the owner noticed the highest-residual players were also the highest-mu
players. Checked properly: Pearson r=+0.610 (local dev, 837 matches) and
+0.563 (prod, 851 matches) between a player's final chronological mu and
their team's mean signed prediction residual, both 95% bootstrap CIs
excluding zero ([+0.312,+0.803] and [+0.308,+0.784]), and unmoved by
removing the top outlier (Stephan) from either dataset (+0.616 / +0.559).
Mechanism: `win_probability`'s extra performance-noise term was
`n_players * beta^2` — fixed regardless of how converged a player's own
sigma is, so it under-predicts confident/converged teams and over-predicts
uncertain ones.

**Fix tested:** replace the fixed term with one that scales off each
player's own sigma: `variance = sum(sigma_i^2) * (1 + k)`, k fit by grid
search on log loss on the earlier 75% of sessions only. First grid search
(0-5.0) hit the search boundary at k=5.0 — caught before trusting it,
widened to confirm log loss actually bottoms out (it does, around k=10-12,
then rises back toward the "always predict 50%" floor as k→∞ for k in the
thousands) before refining. True optimum: **k=11 in both datasets,
independently.**

**Held-out (last 25% of sessions, never used for fitting) results:**

| | Local dev | Prod |
|---|---|---|
| Log-loss improvement vs fixed beta=5.0 | +0.0924 | +0.0963 |
| Session-block bootstrap 95% CI | [+0.0402, +0.1507] | [+0.0415, +0.1532] |
| Resamples favoring the fix | 100% | 100% |
| Held-out mu-residual correlation | +0.007 → **-0.004** | +0.011 → **-0.001** |

Both datasets converge on the same k independently, the CI excludes zero by
a wide margin, and the correlation that motivated the fix is eliminated on
data the fit never saw. This clears the bar every other candidate this
session failed to clear.

**Caveat on process:** the motivating correlation was found by looking at
the full dataset, not a blind pre-registration from the start — but the fix
itself was then fit on train and scored on strictly held-out test in two
independent datasets, which is real out-of-sample evidence, not just a
good-looking full-sample number.

**Adopted:** `app/rating_policy.py::win_probability` now takes
`variance_scale` (default `settings.win_probability_variance_scale = 11.0`)
instead of `beta`; `POLICY_VERSION` bumped to `trueskill-decay-v3`. Does
NOT touch `trueskill.rate()` / `environment()` — `trueskill_beta` still
governs actual rating updates unchanged; this is prediction-only. Updated
the one other call site that snapshotted the old parameter name
(`balance_capture.py`'s suggestion capture now stores `variance_scale`
instead of `beta`; `judgments.py`'s swap-recompute reads the new key). Old
snapshots using the old key can't be affected — the 2-hour freshness check
on suggestion swaps already expires anything from before this deploy.

**Verification:** `pytest -q` → 264 passed / 5 skipped / 1 pre-existing
failure (`test_ml_pipeline_e2e`), up from 263 (one new test asserting the
new formula shape, one rewritten to test `variance_scale` instead of the
retired `beta` parameter). Re-ran `walkforward_session_eval.py` against the
real, wired-in code (not the scratch candidate script) post-change: held-out
raw log loss 0.6591 — better than even Session 7/8's *temperature-corrected*
number (0.6626), and the holdout fitted temperature is now exactly 1.0
(no further post-hoc correction wanted), suggesting this fixes the root
cause the temperature hack was papering over rather than adding a second
patch on top of it.

**Not touched:** display MMR / mu / sigma (rating of record unaffected),
the balancer's default objective (still unchanged pending its own
evidence), `scripts/walkforward_session_eval.py` and
`scripts/skill_dependent_variance_eval.py` remain as the analysis record.

---

## 2026-09-28 — Session 10: per-race offsets and faster dynamics (NOT ADOPTED)

**Trigger:** owner asked to recalibrate Stephan (recent Zerg "unstoppable and
indicative of his current skill") and ShadowDragon (now plays random).

**Data:** fresh `litestream restore` of prod (878 matches, 855 usable, to
2026-09-27). The walk-forward state at tau=0.25 reproduces prod's stored
`players.mmr` exactly for all 16 players with >=50 games.

**Residual scan, live formula (`all_players_residual_scan.scan`):** Stephan
+0.022 [-0.012, +0.057], ShadowDragon +0.008 [-0.041, +0.052]; 1/16 players
clear zero (ChrisO), ~0.8 expected by chance. Stephan's recent-Zerg half
(`stephan_race_recency_eval.py`) is +0.119 [+0.016, +0.222], but that is a
post-hoc slice. ShadowDragon's random era is ~30 games since 2026-07: too few
to resolve anything for him specifically.

**Experiment:** `backend/scripts/race_offset_eval.py [DB_URI]` (s0=0
reproduces the live `win_probability` path to 2e-15).

*Model (arms B/C):* each player has a base rating N(mu_b, sigma_b^2) plus,
per race played, an offset N(mu_o, sigma_o^2) with prior N(0, s0^2). A match
is rated on the composite (mu_b + mu_o, sigma_b^2 + sigma_o^2), and the
posterior shift is split between components in proportion to their variance
(exact for a sum of independent Gaussians; the induced base/offset covariance
is dropped). Inactivity decay and tau apply to the base only.

*Arms:* A incumbent (tau 0.25, k 11). B per-race, predicting with the race
actually played (an oracle: the balancer can't know it). C per-race,
predicting with the expectation over the player's race mix in their last 20
games (what the balancer could use). D single rating, tau fit on train.
s0, tau and k are fit by log loss on the earlier 75% of sessions only.

*Kill criterion (pre-registered):* adopt only if held-out log-loss gain over
A has a session-block bootstrap 95% CI excluding zero on both gates. Gate 1
scores `win_probability`; gate 2 scores the summed display-MMR difference
the default balancer sorts by (logistic scale fit on train). Gate 2 was added
after gate 1 had run, because a win-probability gain alone doesn't show the
balancer's ranking improved. B passing while C fails would mean per-race
ratings only help if the balancer is told each player's race.

Session-grouped 75/25 split, params fit on train only. Games stored twice
(`walkforward_session_eval.duplicated_game_ids`, see Session 11) are rated
in every walk but never scored: the second copy's "pre-match" prediction
already contains the first copy's outcome. Held-out n=215 (from 2024-11-03).
Numbers below are that leak-free rerun (the first run scored duplicates;
same verdicts).

| Arm | Fit | Gate 1: win_probability gain | Gate 2: display-MMR gain |
|---|---|---|---|
| B per-race, oracle race | s0=3, k=9 | +0.0037 [-0.0041, +0.0106] | +0.0066 [-0.0004, +0.0131] |
| C per-race, recent race mix | s0=2, k=10 | +0.0028 [-0.0008, +0.0065] | +0.0035 [-0.0000, +0.0073] |
| D tau 0.25 -> 0.5 | tau=0.5, k=10 | +0.0070 [+0.0008, +0.0138] | +0.0028 [-0.0031, +0.0095] |

B and C fail both gates, even with the oracle race (C's gate 2 lower bound
is at zero: the closest near-miss, worth retesting as data grows). D passes
gate 1 (monotone over tau 0.35-0.6, so not a spike) but fails gate 2, the
balancer's own sort key. Winner accuracy is flat across all arms.

**What D would do if adopted anyway:** Stephan +205 display MMR, Sirhc +116,
Cyrexg -208, INterprime -175, Cendol -169, Redevilz -133, ShadowDragon -4.

**Verdict:** no change to the rating of record. Tau is the lead worth
retesting as the held-out window grows.

---

## 2026-09-28 — Session 11: data audit, closeness-scored objective, suggestion resolution fix

**Replay ground truth** (`backend/scripts/replay_outcome_sweep.py`, all 858
local replays parsed): 555 record an in-game result, 300 do not. On the 555,
the DB winner matches the replay 555/555.

**Findings (recorded, not acted on; each needs owner sign-off):**

All comparisons below score only ground-truth (recorded-result) matches
that are not part of a duplicated game; the first pass scored duplicate
copies, which leaks outcomes and flipped the dedup conclusion.

1. **Disputed winners.** On the 300 no-result replays, final supply, resources
   killed and first-team-to-leave agree with each other ~95%, and each is
   95-99% accurate on the 555 recorded ones. They unanimously contradict the
   stored winner on 92 matches (83 ingested in 2026-01). Re-rating with those
   92 flipped predicts ground-truth games WORSE (n=465: 68.2% -> 64.7%,
   log loss -0.0230, CI [-0.0383, -0.0076]). The stored labels beat the
   replay-state signals there (these replays end when the recorder leaves, so
   their final state isn't the final result). Not relabeled. Open question for
   the owner: how were winners set for the 2026-01 batch?
2. **68 games are stored twice** (local and prod): same map and roster,
   starts seconds apart, two players' replays, different hashes;
   `game_fingerprint` never matched them. 16 pairs store opposite winners.
   Dropping the second copy is prediction-neutral (log loss -0.0007, CI
   [-0.0042, +0.0032]), so removing them is a pure correctness fix. It needs
   owner sign-off (match deletion) and a fingerprint rule that tolerates a
   few seconds of start-time difference.
3. **`player_match_metrics` is unreliable at the team level.** On ground-truth
   matches, team `army_value_killed` picks the winner 61.3%; the replay's own
   `resources_killed` picks it 94.6%. This feeds `avg_combat_score`, the
   composite objective's `components` term, and the ML features. Parser and
   backfill project.
4. The parser's no-result fallback compares unspent bank
   (`minerals_current`), not resources collected. Left alone: the
   supply-advantage branch makes it 92.1% on recorded replays, but final
   supply alone is 98.9%.

**Objective shoot-out on a realized outcome**
(`backend/scripts/closeness_objective_eval.py SWEEP.json [DB_URI]`).
Earlier comparisons scored each objective on its own yardstick; this one
scores both against how lopsided the game actually was. Margin = team1
replay `resources_killed` share, ground-truth (recorded-result) replays
only, duplicated games excluded; closeness = |share - 0.5|. Predictors from
leak-free walk-forward state: |summed display-MMR gap| vs
|win_probability - 0.5|. *Kill criterion (pre-registered):* switch the
default only if Spearman(WP) exceeds Spearman(MMR) with a session-block 95%
CI on the difference excluding zero. The trade share picks the recorded winner 95.0% (n=461).
Spearman with realized lopsidedness: MMR gap +0.038, win-prob gap -0.002;
WP - MMR = -0.040, CI [-0.104, +0.018]. **Default stays summed display
MMR.** Neither pre-match gap meaningfully predicts blowouts among
played games.

**Changed: suggestion-to-match resolution** (`app/services/balance_capture.py`).
v2 suggestions were never resolved: the old +/-24h window let a late-uploaded
earlier game claim a fresh suggestion, so v2 was excluded outright. On prod,
`played_at` is the game's END (suggestions are made 1-2 min after a game
ends), and played games start 1-5 min after their suggestion. New rule: link
only if the game's start (played_at - duration) is within 10 min after the
suggestion (2 min clock skew), exact split only, all methods. A same-roster
rematch can't start inside that window because the previous game has to
finish first, and a late-uploaded earlier game starts before the suggestion.
Matches with no recorded duration are never linked, since their start can't
be derived. This reverses the Session 9-era decision to keep v2 out of
inferred resolution; the explicit selection flow (`balance_selection.py`) is
untouched and remains the prospective-evidence path. Only 4 of ~14 games
since 2026-07 used a suggested split: the owner uses the balancer
occasionally and picks teams by hand otherwise, but uploads every replay, so
most matches have no suggestion to link. `get_calibration` still
counts rank-1 suggestions only, so a played rank-2/3 suggestion resolves but
only shows up in selection calibration. On prod it reproduces the 4 correct
historical links and drops 2 wrong ones.

**Fixed: `tests/test_ml_pipeline_e2e.py`.** Its long-standing failure was test
setup, not the pipeline: it uploads into an empty DB, so the team-experience
upload gate rejected every replay. The test now patches that gate (as it
already mocks the predictor). The pipeline it covers is live: build orders
are produced for recent prod uploads and the frontend reads the commentary /
SHAP endpoint.

Tests: `tests/test_balance_capture.py` (+4 timing regressions; helpers now
set `played_at` as the end time), `tests/test_composite_balancer.py`
helper, `tests/test_ml_pipeline_e2e.py` gate patch. Suite: 300 passed /
5 skipped / 0 failed.
