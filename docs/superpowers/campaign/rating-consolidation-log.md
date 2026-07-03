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
