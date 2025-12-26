-- Migration 003: Add Performance Features table for Hybrid MMR System
-- SPEC-ML-001: ML-Enhanced Performance Impact System
-- Created: 2025-12-06

-- Add hybrid_mmr and avg_pim to players table
ALTER TABLE players ADD COLUMN hybrid_mmr REAL DEFAULT 2000.0;
ALTER TABLE players ADD COLUMN avg_pim REAL DEFAULT 0.0;

-- Create performance_features table for ML-ready feature storage
CREATE TABLE IF NOT EXISTS performance_features (
    id INTEGER PRIMARY KEY,
    match_player_id INTEGER NOT NULL UNIQUE,

    -- Z-score normalized features (relative to match average)
    damage_ratio_z REAL DEFAULT 0.0,
    army_value_ratio_z REAL DEFAULT 0.0,
    combat_score_z REAL DEFAULT 0.0,
    spending_efficiency_z REAL DEFAULT 0.0,
    economic_score_z REAL DEFAULT 0.0,
    resource_advantage_z REAL DEFAULT 0.0,
    team_fight_participation_z REAL DEFAULT 0.0,
    team_fight_damage_ratio_z REAL DEFAULT 0.0,
    overall_impact_z REAL DEFAULT 0.0,
    efficiency_score_z REAL DEFAULT 0.0,

    -- Calculated PIM values
    pim REAL DEFAULT 0.0,
    pim_combat REAL DEFAULT 0.0,
    pim_economic REAL DEFAULT 0.0,
    pim_team REAL DEFAULT 0.0,
    pim_efficiency REAL DEFAULT 0.0,
    pim_version VARCHAR(20) DEFAULT 'rule_v1',

    -- MMR change tracking
    raw_mmr_change REAL,
    hybrid_mmr_change REAL,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (match_player_id) REFERENCES match_players(id)
);

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_perf_features_match_player ON performance_features(match_player_id);
CREATE INDEX IF NOT EXISTS idx_perf_features_pim ON performance_features(pim);
