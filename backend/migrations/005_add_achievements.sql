-- Migration 005: Add Achievement System Tables
-- Part of Phase 2: Achievements, Leaderboard, Head-to-Head

-- Achievement definitions table
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500) NOT NULL,
    flavor_text VARCHAR(300),
    category VARCHAR(20) NOT NULL,  -- milestone, streak, combat, economic, teamwork, variety, special, meme, esports
    rarity VARCHAR(20) NOT NULL,    -- common, uncommon, rare, epic, legendary, mythic
    icon VARCHAR(100),
    color VARCHAR(20),
    requirement_type VARCHAR(50) NOT NULL,
    requirement_threshold REAL NOT NULL,
    requirement_extra VARCHAR(200),
    points INTEGER DEFAULT 10,
    is_hidden INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Player achievements (many-to-many with extra fields)
CREATE TABLE IF NOT EXISTS player_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id),
    achievement_id INTEGER NOT NULL REFERENCES achievements(id),
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    trigger_match_id INTEGER REFERENCES matches(id),
    trigger_value REAL,
    is_featured INTEGER DEFAULT 0,
    UNIQUE(player_id, achievement_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_achievements_code ON achievements(code);
CREATE INDEX IF NOT EXISTS idx_achievements_category ON achievements(category);
CREATE INDEX IF NOT EXISTS idx_achievements_rarity ON achievements(rarity);
CREATE INDEX IF NOT EXISTS idx_player_achievements_player ON player_achievements(player_id);
CREATE INDEX IF NOT EXISTS idx_player_achievements_achievement ON player_achievements(achievement_id);
CREATE INDEX IF NOT EXISTS idx_player_achievements_earned ON player_achievements(earned_at);

-- Head-to-head rivalry tracking table
CREATE TABLE IF NOT EXISTS player_rivalries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_id INTEGER NOT NULL REFERENCES players(id),
    player2_id INTEGER NOT NULL REFERENCES players(id),
    -- Games against each other (on opposite teams)
    games_against INTEGER DEFAULT 0,
    player1_wins INTEGER DEFAULT 0,
    player2_wins INTEGER DEFAULT 0,
    -- Intensity metrics
    avg_mmr_swing REAL DEFAULT 0.0,
    biggest_upset_mmr REAL DEFAULT 0.0,
    -- Last meeting
    last_match_id INTEGER REFERENCES matches(id),
    last_match_at DATETIME,
    -- Rivalry score (calculated)
    rivalry_score REAL DEFAULT 0.0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player1_id, player2_id),
    CHECK(player1_id < player2_id)  -- Ensure consistent ordering
);

CREATE INDEX IF NOT EXISTS idx_rivalries_player1 ON player_rivalries(player1_id);
CREATE INDEX IF NOT EXISTS idx_rivalries_player2 ON player_rivalries(player2_id);
CREATE INDEX IF NOT EXISTS idx_rivalries_score ON player_rivalries(rivalry_score DESC);
