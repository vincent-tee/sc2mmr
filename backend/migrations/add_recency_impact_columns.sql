-- Migration: Add recency-weighted impact columns
-- These columns store performance metrics weighted by recency (60-day half-life)

ALTER TABLE players ADD COLUMN recency_weighted_combat REAL;
ALTER TABLE players ADD COLUMN recency_weighted_economic REAL;
ALTER TABLE players ADD COLUMN recency_weighted_efficiency REAL;
ALTER TABLE players ADD COLUMN recency_weighted_overall_impact REAL;

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_players_recency_weighted_mmr ON players(recency_weighted_mmr);
CREATE INDEX IF NOT EXISTS idx_players_recency_weighted_overall_impact ON players(recency_weighted_overall_impact);
