# Parser field audit: what's real, what's dead, what's new

Written 2026-09-16 for a higher-order model to review, following up on the 2026-09-15
replay-metrics review and the same day's Tier 1/4 fixes (see
[2026-09-15-replay-metrics-review.md](2026-09-15-replay-metrics-review.md) and
`.claude/skills/sc2mmr-failure-archaeology/SKILL.md` entries 16-18). Every claim below was
checked against either live code (`backend/app/advanced_parser.py`,
`backend/app/services/unified_parser.py`) or real replay data in `backend/data/sc2mmr.db`
(858 locally-available replays) — no claim here is inferred from documentation alone.

## 1. Confirmed working, backfilled

`army_value_built`, `army_value_killed`, `army_value_lost`, `spending_efficiency` on
`player_match_metrics`. Fixed in commits `b2c79b0`/`a5f9f22`, hand-verified 20/20 against
raw sc2reader `PlayerStatsEvent.*_army` fields, backfilled to 3,599 rows on the local dev DB
2026-09-16 (backup: `sc2mmr.db.backup_20260916_164659_pre_metrics_backfill`). Full detail:
`.moai/docs/tech-debt-log.md` entry 7. `spending_efficiency` has weaker verification than the
army-value fields — checked for a sane distribution (median ≈0.90, no degenerate clustering
at 0 or 1 across a 469-row sample) but never cross-checked against a raw-field ground truth.

## 2. Confirmed dead — computed nowhere, or computed and discarded

| Field | Status | Evidence |
|---|---|---|
| `unit_composition` (`UnifiedParser` path) | Always `{}`. `grep unit_composition app/services/unified_parser.py` returns nothing — the field is never assigned, only defaults to empty via the dataclass. | Sampled 469 rows from a fresh `UnifiedParser` parse: 0/469 non-empty. Meanwhile 1917/4802 (40%) of currently-stored rows have real data, sourced from `advanced_parser.py`'s independent `UnitBornEvent`-based tracking (`app/advanced_parser.py:585-589,727-732`). Two parsers, one has it, one doesn't. |
| `peak_active_workers` | Computed in `advanced_parser.py` (`app/advanced_parser.py:57,340,708-709`), used internally to help derive `economic_score` (`:928,972`), but **has no `player_match_metrics` column** — the number is folded into one composite score and never itself persisted or exposed. | `grep peak_active_workers app/models.py` → no hits. |
| `unknown_unit_types` | Computed per-parse (`app/advanced_parser.py:96,630-631,650-651`) as a coverage-gap counter, but never persisted or surfaced anywhere past the in-memory dataclass — no DB column, no log aggregation, no dashboard. | `grep unknown_unit_types app/models.py` → no hits. |

## 3. New finding: `killer_pid`/location on `UnitDiedEvent` is usable, contrary to the 2026-09-15 review's caution about position data

The 2026-09-15 review warned that "positions from tracker events are selective, periodic,
and incomplete" — true for generic unit-position snapshots, but **not** for death location.
Every `UnitDiedEvent` carries `x`, `y`, `location`, `killer_pid`, `killing_player_id` directly
on the event (verified via `vars(event)` on a live replay). Coverage, measured across 20,730
death events from 8 replays: **`killer_pid` populated on 15,620/20,730 (75.4%)**. This means
"who dealt this kill, and roughly where" is answerable for three-quarters of deaths today,
with zero new extraction infrastructure — it's sitting on an event both parsers already
iterate for army-value/K-D tracking. This is the concrete, narrow first step toward the
"directed/spatial kill events" capability the 2026-09-15 review flagged as the top
recommendation for a real coordination-signal analysis (previously assumed to require new,
larger extraction work).

Not yet checked: accuracy of `location` as "where the fight happened" vs. "where the unit
happened to be standing" (e.g., a sniped worker at home base isn't a team fight), and whether
75% killer-attribution coverage holds outside this 8-replay sample.

## 4. New bug found: mineral-patch depletion counted as a unit kill

In `advanced_parser.py`'s `UnitDiedEvent` handler (`app/advanced_parser.py:614-633`), the
kill-tracking branch is:

```python
if hasattr(event, "killer_pid") and event.killer_pid in player_metrics:
    k_pid = event.killer_pid
    if unit_cost is not None:
        player_metrics[k_pid].army_value_killed += unit_cost
    else:
        player_metrics[k_pid].unknown_unit_types[unit_name] = ...
    player_metrics[k_pid].units_killed += 1   # <-- unconditional
```

`units_killed` increments regardless of whether `unit_cost` was known — so any "unit" that
dies with a real `killer_pid` counts as a kill, including things that aren't combat kills at
all. Checked directly against raw replay data: **mining out a mineral patch sets
`killer_pid` to the harvesting player** (verified on 8 real `MineralField750` deaths — every
one had a concrete `killer_pid`, `unit.owner = None`). Across a 60-replay sample, mineral-node
deaths (`MineralField`, `MineralField750`, `LabMineralField`, `LabMineralField750` combined)
totaled **2,864 events — roughly 48 per match, ~12 per player** — all counted toward
`units_killed` (and therefore `kill_death_ratio`) as if they were combat kills. This
contaminates a stat that's actually used (`kill_death_ratio` is a real displayed/consumed
field, consolidated to one source in commit `9ec0b35`). Not yet measured: how much this
shifts `kill_death_ratio` in aggregate, or whether it's evenly distributed across
players/races (Zerg's early game involves proportionally more mineral-patch mining-out from
faster expansion, so this may not be a neutral bias). **Not fixed. Not backfilled.**

Other non-combat "kills" sharing the same unconditional-increment bug, by frequency
(60-replay sample): `InvisibleTargetDummy` (15,304 — Widow Mine mechanic, unclear real
combat correlation), `Broodling`/`BroodlingEscort` (14,384 — Infestor summons, arguably real
combat since these die in fights), `Interceptor` (5,082 — Carrier's summoned fighters, same),
`MULE` (4,100 — Terran calldown). Larva (27,309 occurrences) is mostly safe: 1,775/1,828
sampled Larva deaths had `killer_pid = None` (morph, not a kill) vs. only 53 with a killer set.

## 5. Missing unit-cost aliases (real units, real costs, just not aliased)

Same class of fix as the 2026-09-15 session's `VikingFighter`/`HellionTank`/`Cyclone`
aliases, found by re-running the same coverage scan: `WarpGate` (structure, likely
intentionally excluded — see below), `ThorAP` (Thor's anti-air mode; `Thor` = 300 in
`UNIT_COSTS`), `WidowMineBurrowed` (`WidowMine` = 75), `BattleHellion` (Hellion's mode name;
`Hellion` = 100), `CreepTumorBurrowed` (support structure, cost TBD). Structures generally
(`Pylon`, `SupplyDepot`, `Barracks`, `Factory`, `OrbitalCommand`, `Assimilator`, etc.) are
confirmed **absent from `UNIT_COSTS` by design** — army value is scoped to combat units, not
economy/infrastructure — so their appearance in `unknown_unit_types` is expected noise, not a
gap, unless a future feature wants "structure value lost" as a separate stat.

## 6. Unaudited this session — composite/derived fields

`economic_score`, `combat_score`, `efficiency_score`, `overall_impact` on all 3,599
backfilled rows still reflect the **pre-fix** army values (the raw inputs were corrected;
the composites derived from them were not recomputed — confirmed this does not cascade into
`Player.avg_*` since `ImpactService.update_player_averages` averages the composite columns
directly, not the raw ones, so no player-level staleness was introduced, but the row-level
composites are now internally inconsistent with their own inputs).
`team_fight_participation`/`team_fight_damage_ratio` rely on a 10-second event-gap heuristic
for grouping engagements (`_detect_team_engagements`, bug-fixed this session for dropping the
final group, but the 10s window itself is unvalidated). `damage_timeline` is explicitly
documented as an estimation hack, not measured data (`sc2mmr-failure-archaeology` entry 2).
`detected_build_type`/`player_archetype` classifier is known-unreliable (`tech-debt-log`
entry 4 — fires "cheese" on any early combat unit).

## Update 2026-09-17: items 2 and 3 actioned

- `unit_composition` ported into `UnifiedParser` (§2 question 3) -- done.
- Mineral-patch depletion (§4 question 2) fixed in both parsers, and the historical
  backfill included it -- not left as accepted noise.
- New capability from §3 also shipped: a `kill_events` table now stores raw
  killer/victim/unit/second/x/y observations. Measured at full-corpus scale (858 replays,
  944,869 events): **84.6% killer coverage** (799,418/944,869), higher than the 75%
  measured on the original 8-replay sample.
- Full detail, exact row counts, and what was deliberately left out (composite-score
  formulas, `units_killed` counting "Unknown"-typed units): `.moai/docs/tech-debt-log.md`
  entry 7's 2026-09-17 update.

## Open questions for review

1. Now that killer coverage is measured at 84.6% corpus-wide, is that high enough to build
   a real per-player "early damage dealt, and roughly where" feature, or does the missing
   ~15% bias toward a specific damage type (AoE/splash) in a way that would skew it?
