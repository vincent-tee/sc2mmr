-- Migration: Fix duplicate MatchPlayer entries and add unique constraint
-- Purpose: Remove duplicate player entries per match and prevent future duplicates
-- Date: 2025-01-28

-- Step 1: Create a temporary table to identify duplicates
-- Keep the record with the lowest ID (first inserted)
CREATE TEMPORARY TABLE duplicates_to_delete AS
SELECT mp.id
FROM match_players mp
WHERE mp.id NOT IN (
    SELECT MIN(mp2.id)
    FROM match_players mp2
    GROUP BY mp2.match_id, mp2.player_id
);

-- Step 2: Delete metrics associated with duplicate match_players
DELETE FROM player_match_metrics
WHERE match_player_id IN (SELECT id FROM duplicates_to_delete);

-- Step 3: Delete performance_features associated with duplicate match_players
DELETE FROM performance_features
WHERE match_player_id IN (SELECT id FROM duplicates_to_delete);

-- Step 4: Delete the duplicate match_player records
DELETE FROM match_players
WHERE id IN (SELECT id FROM duplicates_to_delete);

-- Step 5: Add unique constraint to prevent future duplicates
CREATE UNIQUE INDEX IF NOT EXISTS idx_match_players_unique 
ON match_players(match_id, player_id);

-- Clean up
DROP TABLE duplicates_to_delete;
