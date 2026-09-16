# Replay parsing and ingestion: clearer metrics

Reviewed 2026-09-15 at the owner's request. This is a code review plus small read-only probes, not a deployed parser change or a full historical reparse. Read alongside the [methodology audit](2026-09-15-methodology-audit-and-coordination-plan.md).

## Recommendation

Improve measurement definitions, time alignment, and extraction consistency before adding composite scores. Keep a fast event decoder for routine ingestion; use SC2 engine observations as a separately versioned optional source where compatible. A parser-library replacement alone will not fix the present problems.

Priority order: common clock and explicit metric units; real PlayerStats snapshots; stable player identity and parse provenance; directed/spatial kill events and complete build timelines; then a narrowly validated coordination analysis.

## Observed ingestion paths

- The upload UI (`frontend/src/pages/UploadReplays.tsx`) calls `uploadAdvanced`, which calls `/replays/upload-advanced`. This uses `parse_replay_advanced`, which first invokes the basic parser and then loads the replay again with sc2reader level 4. It persists advanced metrics through `save_advanced_metrics` and runs optional enhanced feature extraction.
- `/replays/upload` uses basic `parse_replay`, persists the match without an advanced-metric callback, and runs enhanced feature extraction. Engine enrichment is scheduled only on this route when `upload_cc_enrichment_enabled` is enabled (default false).
- Batch and external ingestion scripts use `MatchOrchestrator`, which uses `UnifiedParser`. Despite its name/docstring, UnifiedParser is not the only active metrics parser.
- The basic parser's s2protocol fallback decodes match metadata/results, not rich tracker metrics. The advanced path subsequently requires sc2reader to succeed again, so the basic fallback does not guarantee advanced-upload recovery.
- Atomic match persistence is shared in `services/ingestion.py`. Preserve that useful consolidation; consolidate extraction independently rather than introducing a competing persistence path.

## Confirmed timing mismatch on two actual replay files

Environment: installed sc2reader 1.8.0. Read-only `sc2reader.load_replay(path, load_level=4)` probes:

| Replay hash/file prefix | SC2 version | replay.game_length seconds | Frames | Maximum tracker event.second |
|---|---|---:|---:|---:|
| 0064f1e60fb95eb7 | 5.0.15.95841 | 782 | 17529 | 1095 |
| 00fa59764cde6c4 | 5.0.14.94137 | 1149 | 25744 | 1608 |

Files are in `backend/replays/` with `.SC2Replay` extension. `real_length` equals `game_length` in these samples. The installed tracker implementation explicitly sets `self.second = self.frame >> 4`, i.e. 16 loops/second. These replays' duration uses approximately 22.4 loops/second. Therefore `event.second < 300` selects approximately the first 214 Faster-clock seconds, not five minutes. This impacts build timing, worker-loss windows, damage windows, and derived timing scores.

Store integer game loops as the canonical raw timestamp. Convert using one declared clock function and replay speed/build metadata. For modern Faster replays, use 22.4 loops per displayed second, verified against replay duration. Do not blindly apply a 1.4 correction to all historical files or values whose provenance is unknown. Preserve the old derivation version when reprocessing.

Supply-block code in both advanced and unified paths adds 10 per blocked PlayerStats event. In the first sample, stats for player 1 occur at frames 1,160,320,480,640: intervals are about 7.14 Faster seconds. Additional final/leave snapshots also make constant-per-event accumulation wrong. Integrate actual sample intervals and name this a sampled supply-cap exposure estimate; snapshots do not establish continuous exact production blockage.

## Metric definitions currently drift

1. `advanced_parser` sets `damage_dealt = army_value_killed` and `damage_taken = army_value_lost`. `DamageTimelineExtractor` records resource-cost-weighted UnitDied events, not HP damage. Optional CC enrichment overwrites the same damage fields with engine life/shield damage. `ImpactService.save_match_metrics` further substitutes killed value when damage is zero. These quantities must have separate columns/definitions.
2. The advanced spending-efficiency estimate is `(army_value_killed + army_value_lost) / estimated_resources_collected`, capped. Destroying enemy units is not spending one's resources. A new spending measure needs explicit collection/spending semantics; do not carry this formula into a renamed "efficiency" field.
3. The advanced resource-collection proxy sums currently invested, in-progress, and banked resources but omits lost resources. UnifiedParser uses a different proxy including losses but omitting in-progress. Neither is a certified total-collected measure: transfers, initial assets, transformations, refunds, and accounting categories require explicit handling. Keep observed resource bank and income rate separate from inferred totals.
4. `PlayerStatsEvent.resources_killed/lost` aggregate army, economy, and technology. Fields called `army_value_*` can therefore include non-army assets. Preserve category and mineral/gas breakdowns.
5. The hand-maintained cost tables return 100 for unknown units and use approximate mineral-like values despite a minerals-plus-gas docstring. Morphs and mode changes complicate cumulative production cost. Unknown costs should remain unknown, with counts and coverage reported.
6. The advanced unit composition stores only the top five counts, dropping rare counter-units that could matter to the proposed coordination question.
7. `workers_created` combines creation counting with a peak-active-workers comparison. Split starting workers, produced workers, active workers at time t, peak workers, and losses.

## Missing features and reproducible UnifiedParser defects

- `EnhancedReplayParser._extract_resource_checkpoints()` iterates checkpoint times but appends no observations. Its comment implies periodic snapshots are unavailable; actual tracker events provide them. `_extract_supply_blocks()` is `pass`. Do not treat resulting empty/zero feature fields as measurements.
- UnifiedParser's engagement loop does not flush its final group. A synthetic input of three players with event values at seconds 10,11,12 produces no engagement.
- UnifiedParser calculates team-fight ratios before `_calculate_derived_metrics` initializes `damage_dealt`. A read-only probe with 300 resource-value units in a supplied engagement and `army_value_killed=1000` yields `team_fight_damage_ratio=300`, which remains 300 after `damage_dealt` becomes 1000. Expected ratio under its own resource-value definition would be 0.3. This bug concerns the Unified/batch path, not the separately implemented advanced engagement function.
- Both engagement concepts group temporal kill activity across all players without spatial localization. Simultaneous independent fights can be merged. A healer/support player without a credited kill may be excluded. Call existing outputs temporal multi-player kill activity, not validated team-fight participation.
- Advanced parsing can synthesize evenly spaced events when the kill timeline is empty but cumulative killed value is positive. Do not fabricate timing observations. Prior audit found no exact synthetic fingerprint in the inspected production snapshot; contamination of those rows was not demonstrated.

## Existing replay data can support much clearer measurements

### A. Player state snapshots: first implementation priority

Preserve every PlayerStatsEvent with replay player ID, game loop, minerals/gas bank, income rates, worker count, supply used/cap, and resource-value category counters. Compute 3/5/8/10-minute summaries with a documented last-observed-at-or-before rule, recording observation age. A game that ends before a checkpoint has no observation there, not zero.

Useful outputs: worker count at five minutes; army supply or explicitly defined active-army value at a checkpoint; banked-resource exposure; sampled supply-cap exposure; category-specific losses and kills during a fixed window. Retain timing resolution and missingness. These are easier to interpret than overall impact.

### B. Directed losses and build transitions

Persist unit tag (index plus recycle), unit type at event time, owner/controller at event time, killer player/unit where available, game loop, and death coordinates. Preserve missing attribution and friendly-fire/neutral distinctions. Use snapshot counters for authoritative cumulative categories and event sums for attribution; report their discrepancy instead of scaling event values until they match.

Retain full UnitInit/Done/Born/TypeChange/OwnerChange and upgrade events. Distinguish started, completed, canceled, morphed, and mode-switched objects. This supports counter-unit timing and weak-teammate loss patterns without conflating unit transformations with new production.

### C. Coordination signals: observed behavior, not inferred intent

In the first real replay probe there were 10 PingEvents, 1 ChatEvent (content not inspected), 560 UnitDiedEvents, and 44 UnitPositionsEvents. Death events expose victim/killer references and x/y; positions exist but are sparse. Camera, selection, and command events also exist. Do not assume every replay has equivalent coverage.

Potential targeted analysis: candidate captain ping at location L, followed by teammate commands toward L and jointly localized subsequent combat. Compare with matched non-ping windows and other senders, controlling current combat/context; a reaction to an ongoing attack can otherwise look like leadership. Use a fixed response window defined before effect inspection. Lack of pings does not mean lack of coordination; voice communications are not recorded in these events.

For counter-play, link opponent composition observed in the event record to subsequent teammate build transitions, but avoid asserting the player had seen those units. Omniscient replay data are not player knowledge. Camera/command changes can strengthen behavioral evidence but do not prove verbal instruction or perception.

Positions from tracker events are selective, periodic, and incomplete. They are enough to improve crude time-only grouping, not an exact full-map movement reconstruction. Do not infer precise arrival times or absence from combat from absent position events.

## Proposed ingestion/storage contract

Use one normalized event/metric contract behind all HTTP, retry, backfill, and batch paths. sc2reader is the practical high-level adapter; s2protocol can provide a separately tested raw-event adapter for supported builds when needed. It is a decoder, not a complete semantic replacement.

Recommended flow:

`immutable replay artifact -> versioned parse run -> observed events/snapshots -> versioned derived metrics -> explicit published metric set`.

- Preserve replay file hash, game fingerprint, build/base build, speed, game loops, parser/dependency version, metric schema version, parse time, coverage, and warnings.
- Map replay protocol player IDs to database identities once, with alias resolution and validation; reuse across every metric source. CC orchestration currently assumes list order maps to PID, while CC enrichment and enhanced extraction use name matching that can miss aliases.
- Use per-source/per-metric availability (`observed`, `estimated`, `unavailable`, `failed`) and units; nullable fields distinguish unknown from measured zero. Old rows with unknown provenance stay marked unknown until reparsed.
- Preserve multiple observer replay artifacts for one match. Pick or combine sources with explicit coverage rules; longer duration alone does not certify a richer parse. Current ingest refreshes the same hash or a longer alternative without a metric-quality comparison.
- Separate recorded/inferred/manual winner provenance and conflicts; metadata acceptance does not certify metric completeness.
- Make enrichment a durable retryable job keyed by replay hash and parser/schema version. Basic match ingestion can succeed while metrics are pending. FastAPI background tasks plus logs are not a durable record of completed enrichment.
- Reparse into staging or a new parse version, validate, then publish deliberately. Keep stable match/player IDs. Never rerate matches merely because metric extraction was retried.
- Store raw normalized artifacts as compressed files if convenient; SQLite needs only parse manifests, useful queryable snapshots/events, and summaries. This group does not need a distributed analytics stack.

## Engine replay: optional and separately validated

The existing CommandCenter integration is a useful possible source of actual damage, healing, and score counters. It requires compatible SC2 replay playback and is disabled by default for uploads; do not enable it merely because a binary exists. The currently configured environment mentions SC2 4.10, whereas the probed replays are 5.0.14/5.0.15. Actual compatibility was not tested here.

Store engine-derived life/shield damage and economic counters separately from event-derived destroyed value. Record engine version, perspective/player ID, replay completion, and observation sampling. Recompute dependent summaries from a consistent source/version; current enrichment can replace raw fields without refreshing their associated composites/averages. Materialize GCS replay paths before local-only decoders; the current CC enrichment passes stored paths straight to sc2reader.

Even engine observations provide sampled state and cumulative counters, not automatic proof of per-hit attacker attribution or verbal leadership. Use them first as an independent validation source for compatible replay fixtures, then decide whether the operational cost is justified.

## Concrete acceptance checks before historical backfill

Build a small fixed replay corpus spanning races, team sizes, available builds, morphs, cancellations, worker losses, early exits, and multiple observer files where available. Include actual alias cases and decoder failures. Do not assert those cases all exist without inspecting the corpus.

Required checks:

1. All derived event times align with declared duration/clock; raw loops preserved. End/leave snapshots do not add an assumed interval.
2. Same artifact/version produces identical normalized data through upload and batch routes. Duplicate processing does not duplicate events or change ratings.
3. Known zero remains zero; unimplemented/unavailable metrics remain unavailable. Unknown-unit costs are counted, not assigned 100.
4. Every parse source maps all participants correctly or explicitly reports missing identities. No silent alias-dependent omissions.
5. Separate economy/army/technology and minerals/gas counters reconcile to their documented aggregate; event-counter disagreement is visible, not normalized away.
6. Final engagement is retained; ratios have coherent units and denominators; simultaneous spatially separate fights are not automatically merged.
7. Selected checkpoint values, worker losses, and build completions agree with replay inspection or compatible engine observations within documented sampling tolerance.
8. Report parse completeness and failure rates by build/source before publication. Do not claim downstream rating accuracy improvement from better extraction alone.

## Sources checked

- [Blizzard s2protocol](https://github.com/Blizzard/s2protocol): supported stream types, unit lifecycle/tag handling, periodic selective positions, and tracker limitations.
- [sc2reader tracker documentation](https://sc2reader.readthedocs.io/en/latest/events/tracker.html): periodic PlayerStats events plus extra end/leave events; lifecycle and ownership events. Local installed source and real replay probes were used for the actual timing diagnosis.
- [Blizzard protocol](https://raw.githubusercontent.com/Blizzard/s2client-proto/master/docs/protocol.md): GameLoop clock, Faster 22.4 loops/second, replay stepping and observation interfaces.
- [Blizzard score schema](https://raw.githubusercontent.com/Blizzard/s2client-proto/master/s2clientprotocol/score.proto): explicit spending/collection, life/shield damage, healing, category and idle-time semantics. Idle times may accumulate across multiple workers/buildings; they are not necessarily wall-clock durations.

No parser fixes or historical data mutations were performed. Recommended next implementation is the clock/provenance/snapshot foundation and regression corpus, before additional leadership scoring.
