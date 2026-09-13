# Codebase fixes and rating/balance review

Status: implementation and regression verification complete. This document is the durable handoff for the work done.

## Requested scope

Fix the six issues in the codebase review, verify other features, review ratings and balancing, and propose support for human judgment. Keep implementation clear through names and structure. Do not run a historical rating recalculation as part of these changes.

## Implemented

- Shared ingestion service (`app/services/ingestion.py`) for HTTP uploads, advanced uploads, failed-upload retry, manual-winner recovery, and batch ingestion.
- A transaction owner prevents commits inside existing rating helpers from persisting partial matches. SQLite ingestion acquires its writer lock before duplicate checks and rating reads.
- Longer observer replays refresh the existing match without applying the result or incrementing player/synergy counters again. Conflicting winners/participants are rejected.
- Optional enrichment has a separate transaction for each task. Its failure cannot partially commit changes or undo the rated match.
- Upload handlers run as synchronous worker functions. They read at most the configured size limit plus one byte before rejecting oversized files.
- Unique database index for nonempty game fingerprints; migration refuses ambiguous existing duplicates without deleting them.
- Versioned Alembic migration chain, frozen schema baseline, startup upgrade, and Docker packaging. Legacy databases gain missing columns; populated upgrades preserve player ratings.
- Performance adjustments keep stored player MMR and match MMR consistent with mu/sigma (calls the existing, unmodified `RatingSystem.calculate_display_mmr` — no formula change).
- Explicit backend and frontend CI jobs. Backend fixtures use temporary databases. Historical-data checks require an explicitly supplied read-only snapshot.
- Replaced print/boolean-only ability-discovery checks with assertions and temporary-file persistence tests.
- `POST /players/merge` no longer 500s when the source player has an existing `PlayerAlias` pointing at it (it never reassigned `PlayerAlias.target_player_id` before deleting the source, unlike the other related tables) — hit live in production merging DragonKing into ShadowDragon; fixed and deployed the same day. Added `POST /players/aliases` (admin-gated) since alias creation previously only existed as a local-only script that can't reach the deployed database.
- `backend/scripts/batch_upload_replays.py` and `backend/scripts/ingest_external_replays.py` caught `DuplicateReplayError`/`DuplicateGameError` to count and roll back duplicates. `MatchOrchestrator` no longer raises those (it returns `created=False` instead), so both scripts were silently counting every duplicate as a new success. Fixed both to branch on `result.created`; simplified `batch_upload_replays.py`'s three-way duplicate/skipped-game split to a two-way created/already-recorded split, since the underlying distinction (exact-hash vs same-fingerprint-shorter) no longer exists at the ingestion layer.
- Deleted `app/services/match_service.py`, `app/services/replay_service.py`, `app/services/rating_service.py` (~1,700 lines) — fully orphaned by the ingestion-service refactor; no source file imported them except the package `__init__.py` re-export. Confirmed via repo-wide grep before deletion, and confirmed neither of the two live recalculation implementations (`scripts/recalculate_all_mmrs.py`, `POST /players/recalculate-ratings`) used the deleted `RatingService` — those two remain separately implemented and still diverge from each other, which is the still-open question in finding 3 below, not something this cleanup touched. Removed the now-unraised `DuplicateReplayError`/`DuplicateGameError` exception classes for the same reason.

## Verification completed

- 169 tests passed in the isolated backend suite (up from 153 at handoff), 5 local-data checks deselected, 1 known pre-existing failure (`test_ml_pipeline_e2e`, unrelated to this work).
- Added regression coverage that was missing at handoff: alias resolution during ingestion (applies at/above `min_players`, doesn't apply below), two invalid-winner shapes (no winning team, two winning teams) and split-team results, and a failed-upload retry that still fails (record and file are left intact, no ghost match).
- Added a migration regression test proving a pre-existing foreign-key violation (an orphaned `match_players` row) survives migration untouched — no exception, no deletion — closing the "don't silently delete historical records" verification gap.
- Confirmed empirically (not just by reading the code) that the migration baseline has zero drift from `app/models.py`: table set, column set, and index set of a freshly-migrated database match the live SQLAlchemy metadata exactly.
- 8 API regression cases passed: basic/advanced upload idempotency, failure and retry, manual/retry recovery, responsiveness during parsing, and batch-to-HTTP duplicate handling.
- Concurrent observer ingestion test: one match and one rating update.
- Migration tests: empty database, repeated upgrade, missing legacy columns, duplicate refusal without data loss, and (new) pre-existing FK-violation survival.
- Copied the local database using SQLite backup into a temporary directory and upgraded the copy twice. Every pre-existing table row count and every player ID/mu/sigma/MMR value remained identical.
- Frontend lint, typecheck (`tsc --noEmit`), and production build passed after all backend changes. Build retains the same pre-existing warning about a large JavaScript chunk (tracked below, not addressed).
- Reviewed the full diff against file mtimes to confirm the user's concurrent edits (`AuthGate.tsx`, `MatchDetail/index.tsx`, `UploadReplays.tsx`, all dated 2026-07-08, well before this session) were never touched.
- The sandbox hangs even with an empty FastAPI TestClient. Auth/API checks passed when run outside it. This was an environment limitation, not a confirmed application deadlock.

## Remaining implementation/verification work

None outstanding from the original six items. Everything in this section at handoff has been closed:

- ~~Finish cleanup of shared ingestion code and check batch optional-processing behavior.~~ Done — orphaned service files deleted, batch scripts fixed (see Implemented).
- ~~Add/verify regression coverage for alias handling, invalid winners, and failed-upload recovery failure.~~ Done — see Verification completed.
- ~~Review migration constraint parity and existing foreign-key violations; do not silently delete historical records.~~ Done — see Verification completed.
- ~~Run the final complete isolated suite and frontend checks after the last source change.~~ Done.
- ~~Review the final diff for accidental changes and preserve the user's concurrent edits.~~ Done.
- ~~Update this document with final results and any unresolved items.~~ This edit.

Everything below (rating/balancing findings, the human-judgment proposal, and the follow-up/data-repair list) remains as originally written: recommendations and proposals, not changes made. None of them were implemented as part of closing out the remaining-work list above, per the requested scope.

## Rating and balancing findings

These are recommendations, not changes to the current rating formula or balance weights.

1. **Correct the losing-player performance multiplier before a full recalculation.** In `backend/app/performance_rating.py`, above-average performance on a loss produces a multiplier greater than one. Applying it to a negative mu delta increases the loss, opposite the intended cushioning behavior. A below-average loser gets a smaller loss. Specify the desired behavior with monotonicity tests, correct it, then compare the resulting historical ladder on a copy before applying changes.

2. **Use a chronological evaluation as the decision gate.** `backend/tests/test_balance_regression.py` predicts old matches using current `Player` ratings and aggregates. That leaks later results into earlier predictions, so its accuracy assertions are not evidence of prospective performance. Reconstruct state before each match, predict, then update. Group evaluations by gaming session; report Brier score, log loss, calibration, and sample counts alongside winner accuracy. Temporal evaluation follows the rationale in [scikit-learn's cross-validation guide](https://sklearn.org/stable/modules/cross_validation.html).

3. **Align live ingestion and full recalculation.** The recalculation service has a separate update implementation and scales performance adjustments by match-index recency; live ingestion uses the upload update path. Before the deferred merge recalculation, define one rating transition and verify that chronological ingestion and recalculation yield the same final state. Uploading an older replay currently still updates today's state, which is another reason to distinguish ingestion from chronological reconstruction.

4. **Keep the official rating definition, but evaluate the balancing objective separately.** The official display rating is `1000 + 100*mu - 200*sigma`. The default balancer ranks by the difference in summed display MMR, while its probability calculation uses mu/sigma. These can prefer different splits when uncertainty differs. Compare the existing default with the already available composite objective on future recorded games. Do not remove the sigma penalty based only on theoretical preference. [Microsoft's TrueSkill description](https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/) explains the distinct skill-mean and uncertainty estimates.

5. **Do not treat all adaptive weights as effective controls.** `MLMetricsBalancer.calculate_ml_rating()` primarily uses a stored base rating, a teamwork-weighted impact adjustment, and a map bonus. Several supplied metrics/weights appear in the response but do not affect that formula. Simplify the controls to the inputs actually used, or implement and validate the advertised effects. Also replace truthiness fallbacks where zero is a legitimate observed score.

6. **Score calibration per actual game.** `BalancePredictionService` can resolve multiple repeated suggestions for the same game. Its calibration aggregates prediction rows, giving games with repeated button clicks extra weight. Capture which suggestion was selected, keep immutable pre-game predictions and method versions, then score one selected prediction per method/game.

7. **Keep ML optional until it beats the baseline prospectively.** The ML predictor module already records that prior evaluation did not beat the summed-MMR baseline. Avoid increasing complexity based on in-sample fit or current-player historical backtests.

## Human judgment proposal

There is a useful place for it: record the organizer's pre-game assessment alongside the model's suggestion, and let the organizer select or adjust teams. Keep the model estimate visible so disagreements can be examined later.

A small first version could offer:

- “Even”, “Team 1 favored”, or “Team 2 favored”, optionally refined to a win probability.
- Confidence and a short reason: off-race, returning player, current form, communication, map, or known teammate synergy.
- The final chosen roster/split and any swaps, linked to the original suggestion.
- Separate post-game feedback: felt balanced, snowballed early, disconnect, or other unusual circumstances.

Store a judgment record with suggestion ID, immutable team/player IDs, map/race context, model version and probability, human estimate, confidence, reason, author, and submission time. Lock the pre-game estimate once the match starts. Post-game impressions must stay separate from pre-game predictions.

Initially use judgment as a selection aid and a parallel evaluation signal. Do not directly overwrite mu/sigma or train on every subjective vote. Compare model-only and human estimates on later games, then evaluate a bounded blend if there is enough evidence. Any temporary form/off-race adjustment should expire and be visible in the balance explanation.

The existing custom-player, swap-suggestion, and captain-draft paths are possible integration points. A dedicated authenticated judgment endpoint/table would be clearer than repurposing manual metric weights. This feature is a proposal; no judgment UI or endpoint has been implemented in this task.

## Follow-up decisions and data repair

- **DragonKing → ShadowDragon rating reconciliation:** match history, statistics, and alias were merged; TrueSkill mu/sigma were intentionally not recombined. ShadowDragon retains its own rating. A full chronological recalculation to incorporate DragonKing's history is a separate decision. Do not perform it automatically.
- **Existing referential-integrity issues:** a read-only check of the local database found 375 foreign-key violations and zero duplicate nonempty game fingerprints. Migration preserves these existing records and rejects newly introduced violations. Identify ownership and repair on a copy before any live changes. This is not a claim about the deployed database.
- Review the losing-player multiplier and reconcile the two rating update paths before authorizing any historical recalculation.
- Add TypeScript-aware ESLint coverage; the existing lint configuration targets JS/JSX, while `tsc` currently supplies TypeScript checking.
- Reduce the large frontend bundle if startup performance warrants it.

## Operational boundaries

The one exception to "no production deployment": the `PlayerAlias` merge-endpoint bug fix and the new `POST /players/aliases` endpoint (see Implemented) were deployed to Cloud Run the same day, because the DragonKing/ShadowDragon merge the owner requested could not otherwise complete — that fix was reviewed, tested against a copy of the production data, and confirmed with the owner before deploying. Everything else in this document — the Alembic migration chain, the schema baseline, the ingestion-service refactor, the deleted orphaned services, and the batch-script fixes — has been applied to the local working tree and verified locally only; none of it has touched the live database, and no live database migration, historical rating recalculation, or human-judgment feature rollout has been performed. User edits in players/auth/upload/match-detail and the external submodule were preserved (confirmed via file mtimes predating this session).
