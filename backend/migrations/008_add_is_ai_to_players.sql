-- Migration 008: Add is_ai column to players table
-- Description: Adds a flag to identify computer/AI players for historical impact tracking and balancing.

-- Add is_ai column
ALTER TABLE players ADD COLUMN is_ai INTEGER DEFAULT 0;

-- Optional: Update any existing "Computer" players if they exist (based on name pattern)
-- This is a heuristic and might not be 100% accurate for all naming conventions,
-- but helps bootstrap existing data.
UPDATE players SET is_ai = 1 WHERE name LIKE 'Computer %';
