-- Migration 015: Balance prediction capture for calibration tracking
-- Logs balancer suggestions at balance time; resolved against actual
-- match outcomes on replay upload (Brier score / calibration metrics).
-- Note: app startup runs Base.metadata.create_all, so this file documents
-- the schema for existing deployments that apply migrations manually.

CREATE TABLE IF NOT EXISTS balance_predictions (
    id INTEGER PRIMARY KEY,
    created_at DATETIME NOT NULL,
    method VARCHAR NOT NULL,
    rank INTEGER NOT NULL DEFAULT 1,
    players_key VARCHAR NOT NULL,
    team1_ids_key VARCHAR NOT NULL,
    team2_ids_key VARCHAR NOT NULL,
    predicted_team1_win_prob FLOAT NOT NULL,
    match_quality FLOAT,
    balance_score FLOAT,
    mmr_difference FLOAT,
    features_json VARCHAR,
    resolved INTEGER NOT NULL DEFAULT 0,
    match_id INTEGER REFERENCES matches (id) ON DELETE SET NULL,
    team1_won INTEGER,
    brier_score FLOAT,
    resolved_at DATETIME
);

CREATE INDEX IF NOT EXISTS ix_balance_predictions_method ON balance_predictions (method);
CREATE INDEX IF NOT EXISTS ix_balance_predictions_players_key ON balance_predictions (players_key);
CREATE INDEX IF NOT EXISTS ix_balance_predictions_resolved ON balance_predictions (resolved);
