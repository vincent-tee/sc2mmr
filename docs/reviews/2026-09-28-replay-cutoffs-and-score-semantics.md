# Replay departure, recording coverage, and score-screen accuracy

Read-only investigation, 2026-09-28. No production updates or builds.

## Findings and evidence

Match 1168 was downloaded from its recorded GCS object and verified against
SHA-256 `361e31e8c6c844196005748299fc210a9f7740e66b877dff265ee049c6cf8da4`.
The replay covers 38,792 game loops / 1,731 real seconds and has no explicit
winner. The upload logs identify `Tuonela LE (96).SC2Replay` and the advanced
HTTP upload path. This investigation does not confirm its winner manually.

The parser library explicitly documents that PlayerStatsEvent continues
for departed players, including a dedicated snapshot when a player leaves:
https://github.com/ggtracker/sc2reader/blob/upstream/sc2reader/events/tracker.py

Direct inspection of 1168 agrees:

| Player | Departure | Departure bank | Last observed bank | Later stat snapshots |
| --- | --- | ---: | ---: | ---: |
| ShadowDragon | frame 35,999, ~26:46 | 2,814 | 1 | 18 |
| Sirhc | frame 38,542, ~28:40 | 366 | 0 | 2 |
| ChrisO | frame 38,792, 28:51 | 14,776 | 14,776 | 0 |

ShadowDragon's army-killed resource value increases from 12,300 at departure
to 15,000 at the last tracker snapshot. The later units still exist in the
recording; later activity cannot automatically be attributed to his own
commands. Resource redistribution is a possible explanation for bank drops,
but a bank drop alone does not prove a specific transfer mechanism.

The final player snapshots are not simultaneous: ChrisO's last is 38,792;
the other players' last is 38,720, about 3.2 seconds earlier. The last common
regular checkpoint is 38,720. A team comparison should disclose or remove
that time mismatch, not silently compare different moments as exact.

Game-event user IDs and tracker player IDs differ in this replay. Resolve
leave events through sc2reader's `event.player` mapping. Matching raw
`PlayerLeaveEvent.pid` against `PlayerStatsEvent.pid` assigns departures to
the wrong players. Observers also have leave events: match 1167 ends with
observer shunmanFan leaving after the participant result has been recorded.

## Recommended capture contract

Store independent concepts rather than a single implicit end time:

- Replay observation end frame and duration.
- Each participant's departure frame, if observed; never infer it merely
  from zero supply/workers, inactivity, or another person's departure.
- Result provenance: explicit replay result, human-confirmed, suggested, or
  unknown. Result certainty is separate from stat coverage.
- For each stat bundle: source/parser version, frame, coverage cutoff reason,
  and whether each value is measured, estimated, or unavailable.

Preserve two views:

1. **Player contribution through departure.** Freeze each player's own
   summary at their departure event, or at recording end if no departure was
   observed. Prefer the dedicated departure snapshot; retain the preceding
   snapshot as well, and fall back to the last snapshot before departure if
   a dedicated event is missing or already reflects redistribution. Do not
   mix cumulative totals from one cutoff with a bank balance from another.
   Count actions, production, combat, and time averages only through the
   chosen cutoff. Later unit activity remains available separately.
2. **Observed game state at a common time.** Continue tracking all original
   player slots to the recording endpoint. Use a common checkpoint for
   team supply/army comparisons, or show each snapshot's age. This view is
   appropriate for inspecting the match and suggesting its likely outcome.
   Do not sum player-departure snapshots taken at different times as if they
   described one final team army.

When the recording ends without a result, say "Recorded through 28:51 —
result unconfirmed." Do not assert that the recorder quit unless recorder
identity and departure evidence establish that. When a result is known,
show it independently from the coverage timestamp. Replay playback ending
is not proof that the underlying match ended at that moment. Another
participant's longer recording can extend coverage after same-game/roster
validation; keep source provenance and avoid combining cumulative counters
by addition.

## Economy: fix the metric meaning as well as the cutoff

The live advanced parser currently writes bank + remaining/queued assets
as `total_resources_collected`, overwriting it at every snapshot. Destroyed
assets disappear from that proxy. Its `resources_spent` is remaining/queued
assets, not cumulative spending. Thus Sirhc's production value of 2,275
"collected" is not a trustworthy lifetime harvest total. The unified parser
uses a different proxy which adds losses; the two paths are inconsistent.

Best available method for true cumulative economy is to sample engine
ScoreDetails at the selected cutoff. Blizzard defines `collected_minerals`,
`collected_vespene`, and refund-adjusted `spent_minerals`/`spent_vespene`:
https://github.com/Blizzard/s2client-proto/blob/master/s2clientprotocol/score.proto

The existing CommandCenter adapter exposes these fields, but currently
collects final scores in `on_game_end`; it does not yet capture the required
per-player departure scores. Its availability/version compatibility must be
validated before relying on it. This investigation did not run the engine.

For a fast tracker-only fallback:

- Expose bank, income rate, workers, and remaining/queued asset value under
  those names; preserve unknown as null rather than an invented zero.
- A ledger estimate including losses is closer to harvested resources but
  still needs starting assets, refunds, morphs and transfers accounted for.
- Integrating sampled income rates is also only an estimate; rate units,
  sampling intervals and replay speed need validation against engine totals.
- Read bank directly. `collected - spent` is not a universal bank identity
  in a team game with starting resources and transfers.
- Do not take per-field maxima to hide decreases: that combines different
  times and can produce a physically impossible economy row.

## Summary and Military

- Compute APM and time-based averages over the player's observed active
  interval, and show the interval. Distinguish approximate sampled durations
  from exact event counts.
- The advanced parser currently increments supply-block time twice for each
  blocked snapshot, each time by a hardcoded 10 seconds. Regular tracker
  intervals in 1168 are 160 loops, about 7.14 real seconds. Integrate observed
  intervals once, cap at the player's cutoff, and handle extra departure
  snapshots without adding a full nominal interval.
- "Army remaining", cumulative "Army produced", "Army killed", and
  "Army lost" are separate metrics. Do not substitute one for another.
- The live parser sets `damage_dealt = army_value_killed` and
  `damage_taken = army_value_lost`. Those are resource costs, not HP damage.
  Rename them or obtain actual damage from engine counters; do not present
  the same value twice under different meanings.
- The advanced path leaves `army_value_built` at its default zero. A missing
  implementation should show unavailable, not "built no army".
- Production reconstruction must handle starting units, morphs, canceled
  construction, ownership/control changes, and temporary units. Validate
  event reconstruction against engine score categories before calling it
  exact. Categorized engine counters should remain categorized: all units
  plus structures is not synonymous with army.

## Supply-based winner suggestion check

Reused the existing `winner_sweep.json` analysis (not a new full parse),
restricted to IDs retained in the cleaned `prod_rebuild.db`, games at least
60 seconds long, two teams, and exactly one explicit recorded winning team.
There are 525 eligible replay records. All players, including AI, contribute
to team supply in this analysis.

| Required supply ratio | Suggestions | Correct against recorded result | Incorrect |
| --- | ---: | ---: | ---: |
| Greater than 1 | 525 | 519 | 6 |
| Greater than 1.5 | 514 | 511 | 3 |
| Greater than 2 | 480 | 477 | 3 |
| Greater than 3 | 387 | 385 | 2 |

Reparsed all three 1.5x counterexamples directly: matches 369, 511 and 724
still have recorded results opposite to the larger-supply team. Also
reparsed 1167 as a recent known-result comparison. Examples: 369 records
Team 1 winning with 15 supply versus Team 2's 192; 724 records Team 2 winning
with 124 versus Team 1's 326. These are counterexamples to using total supply
as certainty, not proof of why those games ended that way.

511/514 (~99.4%) is agreement conditional on having an explicit result, not
validated accuracy on incomplete/no-result recordings. That population is
selected differently. Raising the ratio alone does not eliminate errors.
Keep supply as a visible suggestion, consider army value and leave sequence
as supporting evidence, and validate on independently labeled partial
recordings before enabling automatic inferred results. Never replace an
explicit result using these heuristics.

## Implementation sequence

1. Add one shared extraction layer for participant identity, event clocks,
   departure and observation endpoints, and snapshot selection. Use it from
   both parsers and the backfill path.
2. Persist cutoff/source metadata and separate departure/end snapshots;
   extend the API to expose them without changing existing ratings.
3. Fix supply-block duration and misleading metric labels; expose absent
   army production/true damage/cumulative economy as unavailable until a
   correct extractor is available.
4. Add optional engine enrichment at matching cutoffs for exact economy
   and damage. It must preserve provenance and not overwrite a departure
   snapshot with an observation-end snapshot.
5. Show a default "Until player left" view and an optional "At recording
   end" view. Label partial recordings and use a common-time team summary.
6. Verify on early departure, recorder departure, observer-recorded finish,
   missing dedicated snapshots, transfers/shared control, and normal finish.
   Compare to in-client scores before backfilling production.

No parser, UI, database, or production rating changes were made during this
investigation. Raw diagnostic scripts and observations are in
`/tmp/sc2mmr-replay-research/`.

## Status at handoff — 2026-09-28

### Completed checks

- Traced match 1168 from the production upload log through the advanced
  parser. Its no-result replay was assigned a winner by the resource/supply
  fallback. The replay itself has no explicit result.
- Replayed the winner audit over 783 retained matches and 858 cached replay
  analyses. There are 237 no-result replay analyses; 22 remain unrated and
  215 have stored ratings. Of those 215 rated no-result games, 67 disagree
  with a 1.5x supply suggestion. These are review candidates, not confirmed
  errors.
- Compared six duplicate-recording pairs. They had 6,862 shared player
  snapshots and zero differences before the shorter recording ended.
- Checked identity handling on a reference corpus. Observers are present in
  event streams and must be excluded from participant metrics. The alias
  `DemonSlayer -> ShadowDragon` resolved correctly in the sampled matches.
  One old snapshot comparison exposed `theEngineer` versus `LayManFan`; the
  current alias inventory must be checked against the live database before
  treating that as a production defect.
- Sampled four replay builds plus match 1168. Morph/type-change events,
  ownership changes, missing ability metadata, friendly-fire deaths, and
  unfinished structure deaths all occur in real files. Match 1168 had 39
  missing ability events, 3,003 type changes, one teammate-attributed death,
  and eight unfinished structure deaths.
- Ran 26 focused parser/clock/accounting tests: all passed.

### Confirmed blockers and defects

- The engine adapter imports and finds `/home/vtee/StarCraftII`, but its
  metrics collector does not expose the `get_score` or
  `set_replay_perspective` methods that the parser calls. Its direct
  end-of-game probe returned no scores. Exact comparison with the in-client
  Economy/Summary/Military screens is therefore still unverified.
- The unified parser counts workers in `army_value_built`; both lightweight
  metric paths fail to account for morphs/type changes as production events.
- Friendly-fire deaths are counted as ordinary kills in the sampled parser
  paths. Ownership changes are observed in some replays but are not yet
  represented in a shared attribution contract.
- Advanced and unified parsers return different participant counts/metric
  shapes on at least one sampled replay (match 724: 8 versus 7 records).
  The paths must not silently overwrite each other during backfill.
- The production score screen presents estimates as Economy/Military facts:
  the stored “collected,” “spent,” and “damage” fields do not have those
  exact meanings.

### Still to do

1. Decide the result policy: explicit result, manual confirmation, or a
   clearly labeled suggestion. Do not automatically rate no-result games
   from supply alone. Build the 215-match review queue and separately inspect
   the 67 supply-conflict candidates.
2. Implement one shared event identity/cutoff layer. Resolve leave events via
   `event.player`, freeze player metrics at departure, retain recording-end
   observations, and select a common frame for team comparisons.
3. Replace misleading metric names and definitions. Keep bank, income rate,
   remaining supply, army remaining, army killed/lost, and estimates separate;
   mark unavailable values null rather than zero.
4. Fix accounting semantics: exclude workers from army, handle morphs and
   cancellations, distinguish opponent kills from friendly fire, preserve
   ownership changes, and correct supply-block elapsed-time integration.
5. Repair or replace the CommandCenter adapter, then run a labeled score
   comparison across normal finishes, player quits, recorder quits, AI games,
   patch versions, and shared-control/observer cases.
6. Add regression fixtures for match 1168, an early player departure, a
   recorder departure, a duplicate recording pair, a morph-heavy replay, and
   a friendly-fire/ownership-change replay. Only after those pass should any
   historical metrics or ratings be backfilled.

This document is a review and handoff, not an implementation approval. No
code, database, production winner, rating, or deployment was changed by the
checks above.

## Implemented — 2026-09-28 (branch `feature/replay-results-and-metrics`)

- **Result provenance** (`app/match_result.py`, migration 0007): every match stores
  `result_source` (`replay` / `suggested` / `confirmed` / `unknown`) plus team supply at
  the last common stats frame. The stats heuristic is unchanged; its winners are only
  labelled. `/match-results/review` orders doubtful results first; `/confirm` records a
  person's decision and a changed winner marks derived data stale. `/match-results/backfill`
  labels older matches from their stored replays. Local run: 301 suggested of 860, 122 of
  them against the supply evidence (worst: match 583, 8 vs 209 supply).
- **Departure cutoffs** (`app/metric_accounting.py`, migration 0008): leaves resolved via
  `event.player`, observers ignored, a leave on the final frame is `recording_end`. Each
  player's stats stop at their cutoff. Fixture tests pin 1168 to this document's numbers
  (ShadowDragon bank 2,814 / army killed 12,300 at 26:46; Sirhc bank 366).
- **Accounting fixes:** supply block integrates real snapshot intervals once (old rule
  overstated ~2.8×); friendly fire and neutral deaths are not kills; workers are not army in
  the unified parser; worker kills/losses shown separately; misleading "damage" and
  "collected" labels renamed in the UI and commentary.
- **History re-parse** (`scripts/reparse_metrics.py`): all 879 prod replays re-parsed with
  the upload parser (0 failures) and saved through the upload's own save path, so history
  matches new uploads. Rehearsed on a prod snapshot: 783 matches, 4,947 player rows; no MMR
  changed, achievements unchanged (506); 214 of 759 match MVPs change because the unified
  and upload parsers used different impact formulas.

Still open: CommandCenter engine adapter; morph-aware production (`army_value_built`
stays unavailable on the upload path and needs a table-rebuild migration to become
nullable); 23 prod matches with no participants. The map bonus (+100/−50 MMR by map win rate) was removed along with the map picker: it predicted nothing and made recommended splits less even in 36 of 80 recent rosters.

### Winner rule and balancer checks — 2026-09-28 (later)

- **Winner rule.** On 564 prod games that record a result (result hidden): the original
  bank/supply rule picks the winner 92.9%; supply at the last common frame with a >1.25×
  lead 99.5% (McNemar 34 vs 0, p≈1e-10). But re-rating history with the supply rule on the
  76 disputed no-result games made ratings predict *worse* (66.4% → 64.0%, p=0.18), and
  leaving them unrated was slightly better (67.0%, p=0.61) — quits behave differently from
  finished games. Adopted: suggest a winner only when both rules agree (99.4% on finished
  games, 93% coverage); otherwise the upload goes to manual review, unrated. Stored results
  are not bulk-flipped; the review queue surfaces disagreements.
- **Balancer terms.** 5×5-fold CV on 761 prod games, pre-match features only: ratings alone
  63.2%; + within-team skill spread 63.2%; + impact components 62.0% (McNemar p=1.0 / 0.49).
  The Teams page never used those terms (it ranks by MMR difference then win chance); the
  unused composite objective and `/teams/balance-composite` were removed.
- **Metrics.** APM removed from the UI and from the efficiency score (spending + supply
  block only); the empty Army Built column removed. Batch ingestion (`MatchOrchestrator`)
  now uses the upload parser, winner rule and save path; the unified parser is retired.
- **Cleanup.** The duplicate-games cleanup now also removes matches with no players
  (23 on prod, nothing else in the prod plan).

### Winner rule revised — 2026-09-28 (owner decision)

The owner overrode the both-rules-agree rule after seeing match 1028 labelled a Team 1 win at 135 vs 578
supply. The rule is now: recorded result, else the clear supply leader (>1.25× at the last common frame,
99.5% on games with a known result), else **unknown** — unrated (every participant `won=0`, MMR before =
after) and first in the review queue until a person confirms. Stored results are settled with the same
rule (`POST /match-results/settle`, and `backfill?recheck_unknown=true` for the 377 prod games whose
replays were previously unreadable), then ratings are rebuilt. The earlier re-rating test (66.4% → 64.0%,
p=0.18, not significant) was accepted as the cost of correct history. On prod: 11 of 100 suggested
results flip (incl. 1028); of the 377 rechecked, 252 have a recorded result, 115 a clear supply lead, and 10
stay unknown (414, 452, 595, 738, 740, 801, 822, 867, 882, 903). Match 1168 goes to Team 2 (286.5 vs 153.5).
Unknown games count as neither win nor loss: `Match.is_rated` (NULL-safe) filters recent form, streaks,
race/build win rates, head-to-head, rivalries, coaching, achievement streaks, calibration and the MMR
chart; the UI and commentary show "No result".
