-- Migration 012: add kill_death_ratio to player_match_metrics.
-- The parser computes it at upload time (app/advanced_parser.py,
-- compute_kill_death_ratio); 1.0 is the neutral "no combat" default.
-- Existing rows can be recomputed from stored unit counts with
-- backend/scripts/backfill_kd_ratio.py.
ALTER TABLE player_match_metrics ADD COLUMN kill_death_ratio REAL DEFAULT 1.0;
