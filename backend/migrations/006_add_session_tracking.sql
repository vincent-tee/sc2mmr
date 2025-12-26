-- Migration 006: Add Session Tracking and Online Learning Tables
-- Part of ML Improvements: Session-aware learning, Bayesian online updates

-- Player gaming sessions table
-- Tracks continuous play periods for session-aware learning
CREATE TABLE IF NOT EXISTS player_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id),
    session_start DATETIME NOT NULL,
    session_end DATETIME NOT NULL,
    match_count INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,

    -- Session statistics
    avg_performance REAL,
    session_mmr_change REAL DEFAULT 0.0,

    -- Learning metadata
    learning_triggered INTEGER DEFAULT 0,
    learning_triggered_at DATETIME
);

-- Indexes for session queries
CREATE INDEX IF NOT EXISTS idx_player_sessions_player ON player_sessions(player_id);
CREATE INDEX IF NOT EXISTS idx_player_sessions_end ON player_sessions(session_end);
CREATE INDEX IF NOT EXISTS idx_player_sessions_player_end ON player_sessions(player_id, session_end);

-- Model versions table for A/B testing and version tracking
CREATE TABLE IF NOT EXISTS model_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_name VARCHAR(50) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    weights_json TEXT,  -- PerformanceWeights as JSON
    features_used TEXT,  -- List of feature names as JSON

    is_active INTEGER DEFAULT 0,
    is_experimental INTEGER DEFAULT 0,

    -- Performance tracking
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    avg_prediction_error REAL DEFAULT 0.0,

    -- Metadata
    notes TEXT,
    parent_version VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_model_versions_created ON model_versions(created_at);

-- Prediction logs for learning from outcomes
CREATE TABLE IF NOT EXISTS prediction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    model_version VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Predictions
    predicted_team1_win_prob REAL,
    predicted_team2_win_prob REAL,

    -- Actual outcome (filled in after match)
    actual_team1_won INTEGER,

    -- Feature values used for this prediction
    features_json TEXT,

    -- Prediction quality
    prediction_error REAL,
    was_upset INTEGER
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_match ON prediction_logs(match_id);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_model ON prediction_logs(model_version);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_error ON prediction_logs(prediction_error);

-- Feature importance tracking
CREATE TABLE IF NOT EXISTS feature_importance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Importance metrics
    correlation_with_outcome REAL,
    information_gain REAL,
    sample_size INTEGER,

    -- Feature metadata
    feature_type VARCHAR(20),  -- "existing", "experimental", "suggested"
    extraction_method VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_feature_importance_name ON feature_importance(feature_name);
CREATE INDEX IF NOT EXISTS idx_feature_importance_model ON feature_importance(model_version);
CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_importance_name_model ON feature_importance(feature_name, model_version);

-- Feature suggestions from the learning system
CREATE TABLE IF NOT EXISTS feature_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    feature_name VARCHAR(100) NOT NULL,
    feature_description TEXT,
    extraction_logic TEXT,  -- Pseudocode or actual code

    -- Why suggested
    reasoning TEXT,
    correlation_hypothesis REAL,

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, implemented, rejected, testing
    tested_at DATETIME,
    test_results TEXT  -- JSON
);

CREATE INDEX IF NOT EXISTS idx_feature_suggestions_name ON feature_suggestions(feature_name);
CREATE INDEX IF NOT EXISTS idx_feature_suggestions_status ON feature_suggestions(status);
