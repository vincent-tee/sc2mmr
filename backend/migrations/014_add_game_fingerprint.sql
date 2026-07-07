-- Migration: Add game_fingerprint column to matches table
-- Purpose: Enable detection of same game from different observers (different leave times)
-- The fingerprint is based on: map_name + played_at (rounded to minute) + sorted player names

-- Add the game_fingerprint column
ALTER TABLE matches ADD COLUMN game_fingerprint TEXT;

-- Create an index for faster lookup during duplicate detection
CREATE INDEX IF NOT EXISTS idx_matches_game_fingerprint ON matches(game_fingerprint);
