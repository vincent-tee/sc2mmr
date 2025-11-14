-- Migration: Add team fight metrics to player_match_metrics table
-- Date: 2025-01-14
-- Description: Adds team fight participation and effectiveness metrics for team game analysis

ALTER TABLE player_match_metrics ADD COLUMN team_fight_participation REAL DEFAULT 0.0;
ALTER TABLE player_match_metrics ADD COLUMN team_fight_damage INTEGER DEFAULT 0;
ALTER TABLE player_match_metrics ADD COLUMN team_fight_damage_ratio REAL DEFAULT 0.0;

-- Note: This migration can be safely rerun if it fails (column already exists)
