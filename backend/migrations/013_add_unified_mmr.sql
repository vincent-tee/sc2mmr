-- Migration: Add unified_mmr column to players table
-- Date: 2025-12-29
-- Purpose: Single source of truth for player skill rating
-- Formula: unified_mmr = handicap_corrected_mmr + (20 * avg_combat_score)

ALTER TABLE players ADD COLUMN unified_mmr FLOAT;

-- Backfill unified_mmr for all players with handicap_corrected_mmr
UPDATE players 
SET unified_mmr = COALESCE(handicap_corrected_mmr, mmr) + (20 * COALESCE(avg_combat_score, 25))
WHERE handicap_corrected_mmr IS NOT NULL OR total_games >= 5;
