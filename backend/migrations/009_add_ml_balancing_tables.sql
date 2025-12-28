-- Migration: Add ML Balancing Tables
-- Session-weighted MMR for faster adaptation
ALTER TABLE players ADD COLUMN session_weighted_mmr FLOAT DEFAULT NULL;
ALTER TABLE players ADD COLUMN last_session_weight_update DATETIME DEFAULT NULL;

-- Synergy cache (duo + trio win rates)
CREATE TABLE IF NOT EXISTS player_synergy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_ids_key TEXT NOT NULL UNIQUE,
    player_count INTEGER NOT NULL,
    matches_played INTEGER DEFAULT 0,
    matches_won INTEGER DEFAULT 0,
    win_rate FLOAT DEFAULT 0.0,
    synergy_score FLOAT DEFAULT 0.0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_synergy_players ON player_synergy(player_ids_key, player_count);

-- Component accuracy tracker (all match history with EMA)
CREATE TABLE IF NOT EXISTS component_accuracy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_name TEXT NOT NULL UNIQUE,
    predictions_correct INTEGER DEFAULT 0,
    predictions_total INTEGER DEFAULT 0,
    accuracy FLOAT DEFAULT 0.5,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_accuracy_component ON component_accuracy(component_name);

-- Recommended weights from regression analysis
CREATE TABLE IF NOT EXISTS ml_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
