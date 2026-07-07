-- Migration: Add handicap-corrected MMR column
-- This corrects for balancing bias where top players are systematically
-- put on weaker teams to balance the game.
--
-- The handicap_corrected_mmr accounts for:
-- 1. Average team handicap the player faces (weaker/stronger teammates)
-- 2. Expected win rate given that handicap
-- 3. Actual win rate (outperformance)
--
-- Players who win more than expected given their handicap get a bonus.

ALTER TABLE players ADD COLUMN handicap_corrected_mmr FLOAT DEFAULT NULL;
ALTER TABLE players ADD COLUMN avg_team_handicap FLOAT DEFAULT NULL;
ALTER TABLE players ADD COLUMN outperformance_pct FLOAT DEFAULT NULL;
