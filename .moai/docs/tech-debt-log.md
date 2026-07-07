# Technical Debt & Type Safety Log

This document tracks intentional technical debt, specifically type ignores and architectural trade-offs made during development, to ensure they are addressed in future sessions.

## 1. Type Ignores (# type: ignore)

### `backend/app/services/unified_parser.py`
- **sc2reader.load_replay**: Library lacks comprehensive type stubs.
- **get_discovery_engine**: Conditional import of local module causes mypy to lose track of the callable signature.
- **SQLALCHEMY JSON Columns**: Accessing `PF.build_order_json` as a list requires casts because SQLAlchemy maps it as `Optional[Any]`.

### `backend/app/balancer.py`
- **trueskill**: Library lacks type stubs.
- **win_probability calculations**: Involves complex math/numpy types that are sometimes narrowed with `cast`.

## 2. Architectural Trade-offs

### Match Orchestrator Dependencies
- The `MatchOrchestrator` currently depends on `UnifiedParser`, `RatingSystem`, and `ImpactService`. While unified, this creates a large central service. In the future, this could be refactored into a command-bus or event-driven pattern.

### SQLite Cascades
- SQLite requires manual recreation of tables to add `ON DELETE CASCADE`. The migration script `backend/scripts/migrate_cascades.py` handles this, but any future schema changes must ensure cascades are preserved in the `CREATE TABLE` statements.

## 3. Future Improvements
- **Standardized DTOs**: Transition from simple dataclasses to Pydantic models for internal service communication to enable automated validation.
- **Async Processing**: Offload `orchestrate_match` to a background task (e.g., Celery or FastAPI BackgroundTasks) as parsing is CPU intensive.

## 4. Build-order classification (`detected_build_type`) - deferred, not fixed (2026-07-06)

**Symptom:** `performance_features.detected_build_type` (and the underlying `build_order_json`/`build_order_hash`) is `NULL` for all 5,452 rows in the live DB. The Squad Meta page's "Effective Playstyles"/"Dominant Strategy" tiles have therefore always been empty/fallback in production.

**Root cause, part 1 (plumbing):** `EnhancedReplayParser.parse()` (`backend/app/services/enhanced_parser.py`) works correctly when called directly and standalone - tested against a real replay in `backend/replays/`, it extracted 293/154/144/151 real build-order events for the match's 4 players. So the parser logic itself is not fundamentally broken. Something breaks specifically in the live call path (`MLFeaturesService.extract_and_save_ml_features` → `_parse_replay_enhanced`, wrapped in a silent `except Exception: logger.warning(...)` in `app/api/replays.py`) - not yet pinpointed exactly (leading candidate: the `replay_file_path` handoff, or an exception being swallowed silently in a step upstream of `_extract_build_orders`).

**Root cause, part 2 (calibration, more important):** even with real extracted data, `build_order_classifier.py`'s rule-based classifier (`classify_by_rules`) returned "cheese" at 0.85 confidence for all 4 players in the test match - three different Terran players and one Zerg, at identical confidence. The trigger is `first_army_unit_time < 90 seconds`, which looks too loose: producing any early combat unit for scouting is normal in real macro play, not exclusively an all-in signal. This suggests that even after fixing the plumbing, the classifier would not produce a discriminating, reflective signal - it would likely just say "cheese" for most players regardless of real playstyle.

**Decision:** not fixing either issue. Recommended and agreed with the owner (2026-07-06): remove "Effective Playstyles"/"Dominant Strategy" from Squad Meta rather than repair a classifier that hasn't been shown to work even when fed real data. Re-entry condition: this would need real recalibration/validation (checking classification output against known cheese-vs-macro games) before it's worth the plumbing fix - a research task, not a quick patch.

## 5. Head-to-Head rivalry recalculation - fixed, with two accepted trade-offs (2026-07-06)

**Symptom (fixed):** `player_rivalries` (backing `/h2h`) was a cache table only ever populated by `RivalryService.calculate_all_rivalries`, which was wired to nothing except the manual `POST /h2h/calculate-all` endpoint and a test. It was last run 2025-12-28. By 2026-07-06, 61 of 860 matches (7%) postdated that run, and 318 of 358 real head-to-head pairs (89%) had no row at all - including the single most-played rivalry in the DB (ChrisO vs Stephan, 423 games), which the live API returned as `total_games: 0, "Casual"` while the same response's `recent_matches`/`map_dominance` blocks (computed live via direct SQL) correctly showed real games. Also found while fixing it: AI opponents (`is_ai=1`) were not excluded, so "Computer (Elite)" would have ranked #11 in the top-25 "Biggest Rivalries" (Epic tier) once the cache was refreshed; and `avg_mmr_swing` was computed from a mu-only approximation (`mu_delta * mmr_mu_multiplier`) that silently ignores the sigma term in the real display-MMR formula, diverging from the true `mmr_after - mmr_before` by ~0.2-2.3 points per match sampled.

**Fix:** wired `RivalryService.calculate_all_rivalries(db)` into both live ingestion pipelines - `app/api/replays.py` (`/replays/upload` and `/replays/upload-advanced`, non-blocking try/except, ~32ms measured cost against the current 860-match DB) and `app/services/match_orchestrator.py` (`MatchOrchestrator.orchestrate_match`, same non-blocking pattern already used there for Achievements). Added an `is_ai` exclusion filter (mirroring the `Player.is_ai == 0` filter already used throughout `app/api/leaderboard.py`). Switched `avg_mmr_swing`/`biggest_upset_mmr` to read the stored `mmr_before`/`mmr_after` snapshot directly (falling back to the old mu-based approximation only if those columns are ever NULL - verified 0 NULLs across 5,476 live rows). Ran one backfill via `POST /h2h/calculate-all` to clear the 6-month backlog. All read-only; no rating/MMR computation was touched.

**Accepted trade-off 1 - full rescan per upload:** `calculate_all_rivalries` rescans every match in the DB from scratch on every single upload (no incremental per-pair update, unlike `ImpactService.update_synergies` which is scoped to one match). Fine at current scale (~32ms vs multi-second replay parsing already in the request path) but doesn't scale indefinitely. Re-entry condition: if match volume grows an order of magnitude, replace with an incremental `update_rivalries_for_match(db, match_id)` that only touches the pairs from the new match.

**Accepted trade-off 2 - no delete of orphaned rows:** `calculate_all_rivalries` only inserts/updates rows for pairs it currently finds; it never deletes a stored row whose pair no longer appears in the freshly computed set (e.g. if all of a pair's matches were later removed by an admin script such as `delete_inexperienced_matches.py`). Player-deletion is safe (the `player_rivalries` FKs are `ondelete="CASCADE"`), but a "matches deleted, pair still on record" case would leave a stale row displayed forever. Checked the live DB on 2026-07-06: zero such orphans currently exist. Not fixed because it's a narrow edge case with no current instance; re-entry condition: add a "delete rows not present in this run's `rivalry_data` keys" step if this ever surfaces.

**Not fixed, low value:** `PlayerSummary.wins`/`H2HPlayerSummary.wins` (backend `app/api/headtohead.py`, frontend `types/headtohead.ts`) is fetched and typed but never rendered anywhere in `HeadToHead.tsx`. Harmless dead data, not touched - removing it would be an API-contract change for zero behavior gain.

## 6. Achievements - dormant-but-real system fixed: not wired to live uploads, wrong MMR field, frozen since 2025-12-28 (2026-07-06)

**Symptom:** the achievement system (`backend/app/services/achievement_service.py`, `backend/app/api/achievements.py`, 33 real achievement definitions in `ACHIEVEMENT_DEFINITIONS` at `backend/app/models.py:1021`) had genuine, non-fake awarding logic, but `player_achievements` (181 rows before this fix) hadn't grown since a single manual run of `POST /achievements/check-all` on 2025-12-28. 21 of 40 active players had **zero** achievements despite real play - including Cendol (125 games, 56 wins) who lacked even `FIRST_BLOOD`/`FIRST_WIN`. 61 of 860 matches (7%) postdated the last check.

**Root cause 1 (not wired):** `AchievementService.check_and_award_all` was never called from either live upload endpoint (`app/api/replays.py` `upload_replay` at line 386, `upload_replay_advanced` at line 1422) nor from `MatchOrchestrator._process_match_data` (`app/services/match_orchestrator.py:330`, the scripts/observer pipeline). It was only reachable via the two manual `POST /achievements/check/{id}` and `POST /achievements/check-all` endpoints - `app/api/leaderboard.py:9` even imports `AchievementService` but never calls any of its methods (dead import, left as-is - harmless and removing it is not worth a diff). This confirms the actual root cause of the "zero-award mystery": the table wasn't empty, it was frozen at whatever the last manual trigger caught. (Note: entry 5 above, written earlier the same day, says the Head-to-Head fix used "the same non-blocking pattern already used there for Achievements" for `match_orchestrator.py` - that was not accurate at the time it was written; achievements had no wiring in that file until this entry's fix. It's an accurate statement now.)

**Root cause 2 (wrong field):** `_calculate_player_stats` read `player.hybrid_mmr or player.mmr` for the `mmr_reached` achievement check (`MMR_2500`/`MMR_3000`/`MMR_3500`, "Legendary" tier). `hybrid_mmr` is a different, unbounded, compounding rating variant (see `sc2-rating-theory-reference` §5) - not the display `mmr` the `Player` model docstring calls "Official - Centralized source of truth" and that these thresholds were clearly calibrated against. Measured against the live DB before the fix: 30/33 active players (91%) already exceeded 3500 hybrid_mmr - "Legendary" was almost universal - versus 1/33 (3%) on `player.mmr`, which matches the documented "<5%" legendary rarity exactly. Changed to read `player.mmr` directly (`achievement_service.py:326`).

**Fix:**
- Wired `AchievementService.check_and_award_all(db, player_id, match_id)` into both `app/api/replays.py` upload endpoints (new-match-only, non-blocking try/except, mirroring the pattern already used for ML feature extraction) and into `MatchOrchestrator._process_match_data` (`app/services/match_orchestrator.py`) for the scripts/observer pipeline.
- Fixed the MMR field bug in `achievement_service.py::_calculate_player_stats`.
- Removed dead code in `achievement_service.py`: the `max_resources`/`match_resources` stat+check (no achievement definition ever used it), the `race_variety` check (superseded by `race_games`/`single_race_games`, never defined), and four match-specific requirement types (`first_damage`, `tank_win`, `low_spend_win`, `combat_damage_ratio`) that were listed in the dispatch but had zero implementation in `_check_match_specific_achievement` (always silently returned `False, None`).
- Ran `backend/scripts/backfill_achievements.py` (new script, `--dry-run` supported) after a DB backup (`sc2mmr.db.backup_20260706_215321`) to catch up the historical gap: 181 -> 480 `player_achievements` rows; all 40 active players now have at least one achievement.
- Consolidated three competing frontend achievement-badge implementations down to one: `frontend/src/components/AchievementBadge.tsx` (the atom, hexagon design) is now used directly by `Achievements.tsx`'s catalog grid (replacing a bespoke rounded-card `AchievementCard`), and via `AchievementGrid.tsx` (the collection wrapper - previously also unused anywhere) in `PlayerDetail.tsx`'s trophy tab (replacing a third bespoke `Circle`+`VStack` implementation). Also fixed `frontend/src/types/achievements.ts`'s `PlayerAchievementsResponse` interface, which declared a field `achievements` that never matched the real backend response (`awarded`, per the Pydantic model in `backend/app/api/achievements.py`) - `PlayerDetail.tsx` was already correctly reading `.awarded` at runtime, so the type was simply wrong and silently unchecked (`npm run build` is `vite build` with no `tsc` step, so a mismatch like this never surfaces at build time - see `sc2mmr-build-and-env`'s "why does tsc fail but npm run build succeed?" trap).

**Accepted / not fixed:**
- `fast_win`/`long_win`/`upset_win` requirement types remain in `_check_achievement`'s dispatch list even though no `Achievement` definition currently uses them (only `glass_cannon` among the match-specific types has a live definition). Unlike the four removed stubs, these have real, correct-looking implementations in `_check_match_specific_achievement` - kept as unshipped-but-working content rather than treated as cruft. Re-entry condition: either add matching `Achievement` rows to `ACHIEVEMENT_DEFINITIONS`, or revisit if this reads as clutter later.
- The achievement backfill includes AI/computer opponents (`is_ai=1`) - matches the pre-existing `/achievements/check-all` endpoint's behavior (no `is_ai` filter there), not a new policy decision. Whether AI players should earn achievements at all is a product question, not addressed here.
- `frontend/src/api/achievements.ts`'s `getRarest`/`getLeaderboard` (achievement points leaderboard, rarest-achievement feed) are not called from any page - confirmed dead at the UI layer, but left alone since removing an unused API client method has zero behavioral effect and building the missing UI would be a new feature, not a fix.
- Did not touch MMR/rating calculation anywhere - achievements only read `player.mmr`/`mu`/`sigma`-derived fields, never write them.

---
*Last Updated: 2026-07-06*
