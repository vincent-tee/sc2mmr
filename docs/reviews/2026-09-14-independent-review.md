# Independent architecture, changes, and balancing review

Initially reviewed 2026-09-14 against the working tree and HEAD, including untracked judgment code and the modified C++ submodule. The initial review changed only this document. After the owner authorized implementation, the balance-priority work below was added locally. Earlier review/campaign documents describe different snapshots; the original findings are retained below as the review baseline.

## First priority — Improve actual team balance

Owner priority, confirmed after this review: focus the next implementation on better balance, ahead of broader architecture cleanup or a DeepSeek integration. This is the implementation order; the security findings below still apply, especially before releasing judgment capture.

1. **Make evaluation match live ratings.** Include the same inactivity decay and configuration. Evaluate later gaming sessions using only earlier information, and verify live/reconstruction parity before trusting comparisons.
2. **Improve probability calibration.** Current predictions appear overconfident. Fit calibration on earlier sessions and measure Brier score, log loss, and calibration on unseen sessions before using it to select teams.
3. **Compare team-selection objectives.** Keep summed display MMR as the baseline. Compare it with selecting teams closest to a calibrated 50% win probability, using skill spread and teammate synergy as secondary criteria. Calibration alone may not change which split is closest to 50%; measure the resulting team choices. Historical outcomes cannot establish how unplayed splits would have performed, so record future selections and outcomes.
4. **Put organizer input in team generation.** Capture off-race, returning-player status, current form, and requested swaps. Begin with visible, temporary overrides. Preserve the original suggestion, final teams, locked pre-game judgment, and eventual match association so the value of human input can be measured. Address judgment privacy, validation, and locking as part of this feature.
5. **Measure the experience as well as the winner.** Collect a simple post-game “close / one-sided” assessment and flag disconnects or unusual circumstances. Keep subjective feedback separate from pre-game predictions: an even predicted win probability does not guarantee an enjoyable match.

**Next implementation scope:** fix evaluation parity, add immutable selected-team tracking, and integrate organizer judgment plus post-game feedback into the normal flow. Keep the current balancing default until a candidate demonstrates improvement on held-out sessions and prospective games. Avoid unrelated refactors and historical recalculation as part of this scope.

**DeepSeek comes later:** consider it for interpreting organizer notes or explaining candidate teams after reliable capture and evaluation exist. It has no demonstrated advantage as this application's balancing engine; any advice should remain separately tracked and experimentally evaluated.

## Balance-priority implementation — 2026-09-14

Implemented locally following the owner's “okay start working” and “keep going” instructions. No deployment, historical recalculation, live database repair, or paid API calls were performed.

### Implemented behavior

- **Shared live/evaluation policy:** `app/rating_policy.py` owns inactivity sigma adjustment, typical-session-gap calculation, configured TrueSkill updates, and probability calculation. Live ingestion and the chronological evaluator use these functions. The balancer uses the same probability calculation. Historical context queries exclude dates after the game being evaluated.
- **Configuration correction:** prediction previously used the library constant `trueskill.BETA` even though rating updates used configured beta. Prediction now uses configured beta. Newly captured suggestions use `mmr_v2` / `composite_v2` to distinguish them from older probabilities. The official display-MMR formula and default minimum-MMR-gap objective remain unchanged; corrected probabilities can affect tie-breaking.
- **Evaluation:** rejects duplicate players and inconsistent winners, includes inactivity, uses session-block accuracy bootstrapping, and fits a symmetric probability temperature on the first 75% of complete sessions before evaluating the last 25%. The fitted calibration is an offline candidate, not applied to live balancing.
- **Selected-game workflow:** normal TeamGenerator suggestions now include persisted prediction IDs and immutable rating/configuration snapshots. All returned default/composite suggestions are captured, including lower-ranked alternatives. Organizers can swap one player from each team, record race context, enter a human probability/confidence/reason, save, and choose **Start game with these teams**. Swaps use the original rating snapshot to recompute the model estimate and do not change player ratings. Off-race/form notes are observations for this game, not automatic numerical rating modifiers.
- **Immutability and recovery:** game start atomically locks the judgment and creates one selection per suggestion. Duplicate starts and stale edits are rejected; saved/locked assessments restore after revisiting team generation. New teams require a fresh suggestion. Final-roster changes create a different draft rather than editing an older roster's judgment.
- **Replay association:** after upload, the match page offers compatible pre-game selections for organizer confirmation. Association requires the same teams (either orientation), matching map when recorded, and a start timestamp before the replay's game time within two hours. Repeated games are never automatically assigned on roster alone. Each selection and match can be linked once; linked judgments and feedback follow that association. Clock mismatches can leave no valid candidate; they are not silently treated as prospective predictions.
- **Feedback and scoring:** match detail now includes close/one-sided/early-snowball/disconnect feedback. `/judgments/selections/calibration` scores one explicitly selected game per row, including lower-ranked choices and swaps, and reports human/model results on the same human-scored games. Legacy inferred calibration stays separate and cannot be reweighted by later judgments. New v2 suggestions are excluded from the old clock-skew resolver.
- **Capture safeguards:** judgment reads require a session even in public-read mode. Writes retain the existing admin-token policy. Added probability/roster/context/link validation, explicit-null rejection, bounded text and paginated reads. Completed matches reject new “pre-game” judgments. Migration `0004` adds selection storage without rebuilding historical participant tables.

### Current evaluation evidence

Read-only evaluation of 837 usable games across 102 sessions, using the corrected live policy:

| Last 25% of sessions (272 games) | Brier | Log loss |
| --- | --- | --- |
| Raw configured TrueSkill probabilities | 0.2558 | 0.7515 |
| Temperature 2.0, fitted on the earlier 565 games only | 0.2350 | 0.6626 |

Across the whole dataset, summed display-MMR winner accuracy is 64.7% and the TrueSkill probability pick is 64.1% (834 non-tied games). These replace the initial review's simplified-policy numbers for this evaluator. The held-out calibration result is promising evidence from one historical split, not proof of better future team choices. A symmetric temperature alone does not change which split is closest to 50%.

### Remaining balance work

Collect confirmed selections and post-game feedback prospectively, then evaluate calibration and candidate team-selection objectives across later sessions. Keep the default objective until there is evidence to promote a replacement. DeepSeek remains deferred. Guest/custom-player suggestions do not yet have stable identities for selected-game tracking, so the UI explains that tracking requires registered players.

The old destructive `scripts/recalculate_all_mmrs.py` remains outside this implementation. It still needs a separate safe redesign; the parity claim here covers live ingestion versus the new chronological evaluator, not that maintenance script or reconstruction of today's already-backfilled production ratings.

## Original findings in the changes (review baseline)

### 1. P1 — Judgment notes are anonymously readable in public-read mode

`backend/app/api/judgments.py:211` and `:326` expose complete judgments/feedback, including author and free-text notes. `RequireSessionMiddleware` allows anonymous GETs when `auth_public_read` is enabled; `_is_protected_read` in `backend/app/auth.py` does not include judgments. This contradicts the new module's claim that reads require a session. An anonymous visitor can enumerate organizer comments about players, even though writes are admin-gated.

Require a session explicitly for judgment/feedback reads, or deliberately publish a redacted response. Add tests for anonymous access with public-read enabled. This finding is conditional on that deployment mode, not a claim about the running production configuration.

### 2. P2 — Normal pre-game judgments cannot be attached to the eventual match

`CreateJudgmentRequest.match_id` can only reference an already-existing match (`judgments.py:164`). Matches are created after replay upload. `UpdateJudgmentRequest` excludes match linkage, and the prediction resolver only updates `BalancePrediction`, not `PregameJudgment`. There is no later attachment endpoint. Consequently, a normal judgment starts with `match_id=null` and stays absent from `GET /judgments?match_id=...` indefinitely. A prediction join can help offline when a prediction ID exists, but does not implement this API lifecycle.

The UI gap is larger: `JudgmentCapture` is mounted only in `JudgmentsDemo`, not TeamGenerator; `TeamSuggestionResponse` does not return a persisted prediction ID. The demo submits `demo-harness` and a fixed 0.5 probability, so it is not collecting the actual model's prediction.

Return an immutable suggestion ID, mount capture on a selected suggestion, and introduce a planned-game record with start time, final teams, and eventual match association. Handle repeated games with the same teams and swapped team orientation explicitly. Keep demo records out of evaluation.

### 3. P2 — Invalid judgments can be stored; explicit null edits crash

`judgments.py:60–89` validates only nonempty team lists. It accepts nonexistent, duplicate, and overlapping player IDs, out-of-range probabilities, and mismatched race context. A supplied prediction ID is checked for existence but its roster/probability/version is not checked against the client snapshot. Feedback likewise accepts unrelated judgment and match IDs.

Reproduction payload: team 1 `[999,999]`, team 2 `[999]`, human probability `7`, model probability `-2`, with valid enum values. The request model accepts it, and the create handler has no further checks. `PATCH` with `{"confidence":null}` passes validation and attempts to write NULL into a NOT NULL column, raising an unhandled database error.

Validate finite probabilities in [0,1], unique/disjoint real rosters, context membership, and linkage consistency. Copy authoritative model fields from the stored suggestion, accounting for team orientation. Distinguish omitted patch fields from explicitly invalid null values. Bound note/list sizes and paginate list endpoints.

### 4. P2 — Locking does not guarantee immutable pre-game data

`judgments.py:249–259` reads `is_locked`, then performs an unconditional update at commit. An edit that reads before a concurrent lock can commit after the lock. SQLite serializes writes, but this code does not acquire its write lock before the check. Locking is also entirely manual: completed matches accept new unlocked “pre-game” judgments and their estimates can be revised after results are known.

Use an atomic conditional update (`WHERE is_locked=0`, check affected rows) and an explicit game-start/finalization lifecycle. Store submitted/started/locked timestamps and revisions. Exclude late or unlocked estimates from prospective evaluation. A manually self-reported author is attribution, not a verified identity.

### 5. P2 — Walk-forward evaluator is not evaluating the live transition

`backend/scripts/walkforward_session_eval.py:178–211` advances only `trueskill.rate()`. Live ingestion also calls `RatingSystem.apply_skill_decay` at `backend/app/rating_system.py:459`, changing sigma before prediction and rating. The standalone recalculation script omits that decay too. Thus the campaign's claim that ordering is the only remaining divergence is incorrect: even chronological input diverges after qualifying inactivity gaps. The evaluator also hardcodes configuration and accepts contradictory winner rows by letting the last winning row select the winner.

Extract a shared rating transition with explicit prior state, elapsed time, configuration, and historical context. Test live/reconstruction parity using games separated by inactivity, and reject malformed outcomes consistently. Until then label the evaluator a pure-TrueSkill candidate baseline. Removing the performance adjustment from ingestion was intentional and is not the missing step here.

### 6. P2 — New TypeScript lint coverage currently fails CI checks

`npm run lint` reports five `no-explicit-any` errors: `frontend/src/api/endpoints.ts:37`, `frontend/src/pages/TeamGenerator/BalanceResults.tsx:47,52,62`, and `frontend/src/pages/TeamGenerator/index.tsx:144`. There is also an upload callback dependency warning. These older usages are newly surfaced by the ESLint change; the current tree does not satisfy the claimed clean lint result. Resolve the types using the new tactical interfaces instead of weakening lint globally.

### 7. P2 — Changing the demo roster leaves edits attached to the old judgment

`frontend/src/components/JudgmentCapture.tsx:93` retains its saved judgment in local state; `handleSubmit` updates that ID whenever it exists. `JudgmentsDemo.tsx:111` changes roster/map props without resetting or remounting the component. Save a judgment for one roster, change the roster inputs, then edit: the old record is modified while the form presents the new context. A locked old judgment also remains locked for the new roster.

Key capture by immutable suggestion identity or explicitly reset on identity changes, with protection for unsaved edits. Use the saved snapshot when displaying an existing judgment.

## Architecture assessment and existing risks

The FastAPI/SQLAlchemy backend and React frontend are proportionate to a friend-group application. Shared ingestion, isolated tests, migrations, and keeping subjective feedback separate from ratings are good foundations. No microservice split is needed.

The principal architectural weakness is duplicated rating meaning: live rating updates, the reconstruction script, the walk-forward script, display MMR, and the adaptive balancer have independent logic. The adaptive balancer still prefers `unified_mmr` while the default balancer uses display MMR. Its “form” adjustment uses lifetime average impact rather than a recent-versus-baseline difference; its calculated recency value is unused. Restricting advertised weight keys is an improvement, but does not make this a validated form model. If manual weights omit `teamwork`, the rating silently uses 1.0 while `weights_used` omits that effective default.

An existing high-priority maintenance hazard remains in `backend/scripts/recalculate_all_mmrs.py:94`: it deletes all MatchPlayer rows and recreates them, while PlayerMatchMetrics and other tables reference their IDs. Its independent SQLite engine does not install the application's foreign-key hook. This can orphan or misassociate existing child records; new judgment/prediction records also rely on stable history. Change reconstruction to update rows in place, use the common database setup, preserve IDs, and prove child-record parity on a disposable copy before any future execution. The script was not run in this review.

The shared-password/admin-token scheme is reasonable only if its limitations are intentional. `require_admin` is a no-op without ADMIN_TOKEN; a group session then has all organizer privileges. Store provider secrets server-side for any future API integration. The browser's existing localStorage admin credential should not become the DeepSeek credential store. No deployed secrets or configuration were inspected.

The C++ changes add a score accessor and copy score fields into a Python dictionary. Static inspection found no confirmed issue in those additions; native compilation and SC2 runtime/lifecycle behavior were not tested. Frontend build success likewise does not prove the new manual chunks run correctly in a browser.

## Balancing evidence and improvement plan

The read-only walk-forward script ran on the current local data: **837 usable matches / 102 sessions**. It reported:

| Metric | Result |
| --- | --- |
| Summed display-MMR winner accuracy | 551/834 = 66.1% |
| TrueSkill probability winner accuracy | 541/834 = 64.9% |
| TrueSkill Brier score | 0.2367 |
| TrueSkill log loss | 0.7022 |
| Match-bootstrap accuracy difference, TS minus display | -1.2 percentage points; 95% interval -3.1 to +0.7 |

Three tied predictions are excluded from winner accuracy. These are results for the script's simplified transition, not validated live-system estimates. Its bootstrap samples individual games despite repeated players and sessions; use session-block resampling for uncertainty. The interval does not establish that one method is superior.

Calibration is the clearest candidate for improvement: predictions averaging 0.961 won 80.3% of the time (117 games); those averaging 0.051 won 29.2% (48 games). This suggests overconfidence. Log loss is worse than a constant 0.5 forecast (approximately 0.6931), despite improved winner accuracy and Brier score versus that constant baseline. Fit probability calibration only on earlier sessions and evaluate on later untouched sessions; do not fit and report on this same full dataset.

Suggested order:

1. Make the evaluation transition match the intended live policy, then freeze a chronological session split and metric definitions.
2. Compare current display-MMR balancing with calibrated win-probability balancing and a small composite candidate. Include uncertainty and sample sizes. Keep the current default until evidence supports a change.
3. Treat `balancer_objective_shootout.py` as an objective tradeoff diagnostic only. It uses present-day ratings and model-derived scores, not outcomes under alternate teams. Requiring improvement on minimum MMR difference inherently favors the default that already minimizes that quantity. It also omits live synergy inputs when calling the composite objective. None of this establishes that unplayed alternate teams would have produced better games.
4. Record the actual selected suggestion, not merely a judgment referencing it. Current calibration deduplication improves repeated-click weighting, but a late judgment can change which historical prediction is selected; selection should be immutable before play. Retain lower-ranked suggestions if they were actually chosen.
5. Evaluate map and teammate effects as residual performance after accounting for baseline strength, with shrinkage for small samples. Raw pair/map win rate can double-count strong players and opponents. Use bounded, expiring off-race/form adjustments only as separately measured candidates.

## Human judgment and future DeepSeek augmentation

First finish the selected-suggestion → locked pre-game judgment → completed match → separate feedback lifecycle. Capture a human probability, confidence, reason, and the final roster. Keep human-only and model-only evaluation separate initially. Subjective post-game balance is a useful secondary outcome, but a close win probability is not the same thing as an enjoyable match.

For a future provider integration, use a backend advisory service receiving a small snapshot of candidate teams, rating uncertainty, race/map context, and approved organizer notes. Ask for structured context flags, supported reasons, and an optional candidate preference. Have the organizer accept any adjustment, then recompute teams/probabilities deterministically. Do not let model text directly mutate mu/sigma or execute tools/database commands.

DeepSeek documents JSON output via `response_format={"type":"json_object"}` and notes possible empty responses and truncation. Validate its output against an application schema, including known player/candidate IDs; valid JSON alone does not establish valid advice. See [DeepSeek JSON Output documentation](https://api-docs.deepseek.com/guides/json_mode/), checked 2026-09-14.

Keep the provider/model configurable, set short timeouts and request/token budgets, cache by immutable snapshot plus model/prompt version, and retain deterministic balancing on failure. Treat notes as untrusted data, minimize identifying information, and record cost/latency/version alongside advice. First collect advice without applying it and compare later outcomes. No provider was called with player data, and no claim that DeepSeek is cheaper for this workload was verified; measure actual cost per useful accepted suggestion.

## Verification and limits

- Backend: `python -m pytest -q -m 'not local_data'` — **233 passed, 7 deselected**. Tests used temporary databases. Historical/other local-data cases were excluded.
- Frontend: typecheck and production build passed. Lint failed as described above. Largest UI chunk remains about 633 kB uncompressed / 208 kB gzip.
- Read-only walk-forward evaluation completed; full output is temporarily at `/tmp/sc2mmr-walkforward-review.txt`.
- Static review covered the changed backend/frontend files, new migration/tests/scripts, ingestion/rating/balancing integration, authentication, and the native diff. A standalone supplementary HTTP probe hung and was interrupted; do not mistake it for a completed HTTP regression check.
- No production deployment, historical recalculation, data repair, provider integration, native compilation, browser smoke test, or comprehensive dependency vulnerability audit was performed. Findings are not a certification that the rest of the application is bug-free.
