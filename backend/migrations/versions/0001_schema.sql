CREATE TABLE achievements (
	id INTEGER NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	flavor_text VARCHAR(300), 
	category VARCHAR(9) NOT NULL, 
	rarity VARCHAR(9) NOT NULL, 
	icon VARCHAR(100), 
	color VARCHAR(20), 
	requirement_type VARCHAR(50) NOT NULL, 
	requirement_threshold FLOAT NOT NULL, 
	requirement_extra VARCHAR(200), 
	points INTEGER DEFAULT 10 NOT NULL, 
	is_hidden INTEGER DEFAULT 0 NOT NULL, 
	is_active INTEGER DEFAULT 1 NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_achievements_category ON achievements (category);

CREATE UNIQUE INDEX ix_achievements_code ON achievements (code);

CREATE INDEX ix_achievements_id ON achievements (id);

CREATE INDEX ix_achievements_rarity ON achievements (rarity);

CREATE TABLE component_accuracy (
	id INTEGER NOT NULL, 
	component_name VARCHAR NOT NULL, 
	predictions_correct INTEGER DEFAULT 0 NOT NULL, 
	predictions_total INTEGER DEFAULT 0 NOT NULL, 
	accuracy FLOAT DEFAULT 0.5 NOT NULL, 
	last_updated DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (component_name)
);

CREATE INDEX ix_component_accuracy_id ON component_accuracy (id);

CREATE TABLE failed_uploads (
	id INTEGER NOT NULL, 
	filename VARCHAR NOT NULL, 
	file_size_bytes INTEGER, 
	replay_hash VARCHAR, 
	replay_file_path VARCHAR, 
	error_type VARCHAR(20) NOT NULL, 
	error_message VARCHAR NOT NULL, 
	error_detail VARCHAR, 
	map_name VARCHAR, 
	game_mode VARCHAR, 
	duration_seconds INTEGER, 
	num_players INTEGER, 
	uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	reviewed INTEGER DEFAULT 0 NOT NULL, 
	review_notes VARCHAR, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_failed_uploads_error_type ON failed_uploads (error_type);

CREATE INDEX ix_failed_uploads_id ON failed_uploads (id);

CREATE INDEX ix_failed_uploads_replay_hash ON failed_uploads (replay_hash);

CREATE INDEX ix_failed_uploads_uploaded_at ON failed_uploads (uploaded_at);

CREATE TABLE feature_suggestions (
	id INTEGER NOT NULL, 
	feature_name VARCHAR(100) NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_feature_suggestions_id ON feature_suggestions (id);

CREATE TABLE live_match_feed (
	id INTEGER NOT NULL, 
	detected_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	match_id INTEGER NOT NULL, 
	map_name VARCHAR NOT NULL, 
	forecast_json JSON NOT NULL, 
	is_active INTEGER DEFAULT 1 NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_live_match_feed_id ON live_match_feed (id);

CREATE TABLE matches (
	id INTEGER NOT NULL, 
	played_at DATETIME NOT NULL, 
	game_mode VARCHAR(13) NOT NULL, 
	map_name VARCHAR NOT NULL, 
	duration_seconds INTEGER NOT NULL, 
	replay_file_path VARCHAR, 
	replay_hash VARCHAR, 
	game_fingerprint VARCHAR, 
	predicted_team1_win_prob FLOAT, 
	predicted_team2_win_prob FLOAT, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_matches_game_fingerprint ON matches (game_fingerprint);

CREATE INDEX ix_matches_id ON matches (id);

CREATE INDEX ix_matches_played_at ON matches (played_at);

CREATE UNIQUE INDEX ix_matches_replay_hash ON matches (replay_hash);

CREATE TABLE meta_feedback (
	id INTEGER NOT NULL, 
	theory VARCHAR(500) NOT NULL, 
	is_active INTEGER DEFAULT 1 NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_meta_feedback_id ON meta_feedback (id);

CREATE TABLE ml_config (
	id INTEGER NOT NULL, 
	config_key VARCHAR NOT NULL, 
	config_value VARCHAR NOT NULL, 
	last_updated DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (config_key)
);

CREATE INDEX ix_ml_config_id ON ml_config (id);

CREATE TABLE player_synergy (
	id INTEGER NOT NULL, 
	player_ids_key VARCHAR NOT NULL, 
	player_count INTEGER NOT NULL, 
	matches_played INTEGER DEFAULT 0 NOT NULL, 
	matches_won INTEGER DEFAULT 0 NOT NULL, 
	win_rate FLOAT DEFAULT 0.0 NOT NULL, 
	synergy_score FLOAT DEFAULT 0.0 NOT NULL, 
	last_updated DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (player_ids_key)
);

CREATE INDEX ix_player_synergy_id ON player_synergy (id);

CREATE TABLE players (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	mu FLOAT DEFAULT 25.0 NOT NULL, 
	sigma FLOAT DEFAULT 8.333 NOT NULL, 
	recency_weighted_mmr FLOAT, 
	hybrid_mmr FLOAT DEFAULT 2000.0, 
	avg_pim FLOAT DEFAULT 0.0, 
	total_games INTEGER DEFAULT 0 NOT NULL, 
	wins INTEGER DEFAULT 0 NOT NULL, 
	losses INTEGER DEFAULT 0 NOT NULL, 
	terran_games INTEGER DEFAULT 0 NOT NULL, 
	protoss_games INTEGER DEFAULT 0 NOT NULL, 
	zerg_games INTEGER DEFAULT 0 NOT NULL, 
	random_games INTEGER DEFAULT 0 NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	last_played DATETIME, 
	is_core_player INTEGER DEFAULT 1 NOT NULL, 
	is_ai INTEGER DEFAULT 0 NOT NULL, 
	session_weighted_mmr FLOAT, 
	last_session_weight_update DATETIME, 
	avg_economic_score FLOAT DEFAULT 0.0 NOT NULL, 
	avg_combat_score FLOAT DEFAULT 0.0 NOT NULL, 
	avg_efficiency_score FLOAT DEFAULT 0.0 NOT NULL, 
	avg_overall_impact FLOAT DEFAULT 0.0 NOT NULL, 
	avg_harassment_score FLOAT DEFAULT 0.0 NOT NULL, 
	avg_first_damage_timing INTEGER, 
	primary_archetype VARCHAR, 
	avg_aggression_score FLOAT DEFAULT 50.0 NOT NULL, 
	recency_weighted_combat FLOAT, 
	recency_weighted_economic FLOAT, 
	recency_weighted_efficiency FLOAT, 
	recency_weighted_overall_impact FLOAT, 
	mmr FLOAT DEFAULT 1833.0 NOT NULL, 
	handicap_corrected_mmr FLOAT, 
	avg_team_handicap FLOAT, 
	outperformance_pct FLOAT, 
	unified_mmr FLOAT, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_players_id ON players (id);

CREATE UNIQUE INDEX ix_players_name ON players (name);

CREATE TABLE balance_predictions (
	id INTEGER NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	method VARCHAR NOT NULL, 
	rank INTEGER DEFAULT 1 NOT NULL, 
	players_key VARCHAR NOT NULL, 
	team1_ids_key VARCHAR NOT NULL, 
	team2_ids_key VARCHAR NOT NULL, 
	predicted_team1_win_prob FLOAT NOT NULL, 
	match_quality FLOAT, 
	balance_score FLOAT, 
	mmr_difference FLOAT, 
	features_json VARCHAR, 
	resolved INTEGER DEFAULT 0 NOT NULL, 
	match_id INTEGER, 
	team1_won INTEGER, 
	brier_score FLOAT, 
	resolved_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(match_id) REFERENCES matches (id) ON DELETE SET NULL
);

CREATE INDEX ix_balance_predictions_id ON balance_predictions (id);

CREATE INDEX ix_balance_predictions_method ON balance_predictions (method);

CREATE INDEX ix_balance_predictions_players_key ON balance_predictions (players_key);

CREATE INDEX ix_balance_predictions_resolved ON balance_predictions (resolved);

CREATE TABLE match_players (
	id INTEGER NOT NULL, 
	match_id INTEGER NOT NULL, 
	player_id INTEGER NOT NULL, 
	team_number INTEGER NOT NULL, 
	race VARCHAR(7) NOT NULL, 
	won INTEGER NOT NULL, 
	mu_before FLOAT NOT NULL, 
	sigma_before FLOAT NOT NULL, 
	mu_after FLOAT NOT NULL, 
	sigma_after FLOAT NOT NULL, 
	mmr_before FLOAT, 
	mmr_after FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(match_id) REFERENCES matches (id) ON DELETE CASCADE, 
	FOREIGN KEY(player_id) REFERENCES players (id) ON DELETE CASCADE
);

CREATE INDEX ix_match_players_id ON match_players (id);

CREATE INDEX ix_match_players_match_id ON match_players (match_id);

CREATE INDEX ix_match_players_player_id ON match_players (player_id);

CREATE TABLE player_achievements (
	id INTEGER NOT NULL, 
	player_id INTEGER NOT NULL, 
	achievement_id INTEGER NOT NULL, 
	earned_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	trigger_match_id INTEGER, 
	trigger_value FLOAT, 
	is_featured INTEGER DEFAULT 0 NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(achievement_id) REFERENCES achievements (id) ON DELETE CASCADE, 
	FOREIGN KEY(player_id) REFERENCES players (id) ON DELETE CASCADE, 
	FOREIGN KEY(trigger_match_id) REFERENCES matches (id) ON DELETE CASCADE
);

CREATE INDEX ix_player_achievements_achievement_id ON player_achievements (achievement_id);

CREATE INDEX ix_player_achievements_id ON player_achievements (id);

CREATE INDEX ix_player_achievements_player_id ON player_achievements (player_id);

CREATE TABLE player_aliases (
	id INTEGER NOT NULL, 
	source_name VARCHAR NOT NULL, 
	target_player_id INTEGER NOT NULL, 
	min_players INTEGER DEFAULT 4 NOT NULL, 
	exclude_1v1 INTEGER DEFAULT 1 NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(target_player_id) REFERENCES players (id) ON DELETE CASCADE
);

CREATE INDEX ix_player_aliases_id ON player_aliases (id);

CREATE UNIQUE INDEX ix_player_aliases_source_name ON player_aliases (source_name);

CREATE TABLE player_rivalries (
	id INTEGER NOT NULL, 
	player1_id INTEGER NOT NULL, 
	player2_id INTEGER NOT NULL, 
	games_against INTEGER DEFAULT 0 NOT NULL, 
	player1_wins INTEGER DEFAULT 0 NOT NULL, 
	player2_wins INTEGER DEFAULT 0 NOT NULL, 
	avg_mmr_swing FLOAT DEFAULT 0.0 NOT NULL, 
	biggest_upset_mmr FLOAT DEFAULT 0.0 NOT NULL, 
	last_match_id INTEGER, 
	last_match_at DATETIME, 
	rivalry_score FLOAT DEFAULT 0.0 NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(player2_id) REFERENCES players (id) ON DELETE CASCADE, 
	FOREIGN KEY(last_match_id) REFERENCES matches (id) ON DELETE CASCADE, 
	FOREIGN KEY(player1_id) REFERENCES players (id) ON DELETE CASCADE
);

CREATE INDEX ix_player_rivalries_id ON player_rivalries (id);

CREATE INDEX ix_player_rivalries_player1_id ON player_rivalries (player1_id);

CREATE INDEX ix_player_rivalries_player2_id ON player_rivalries (player2_id);

CREATE TABLE player_synergies (
	id INTEGER NOT NULL, 
	player1_id INTEGER NOT NULL, 
	player2_id INTEGER NOT NULL, 
	games_together INTEGER DEFAULT 0 NOT NULL, 
	wins_together INTEGER DEFAULT 0 NOT NULL, 
	losses_together INTEGER DEFAULT 0 NOT NULL, 
	synergy_score FLOAT DEFAULT 50.0 NOT NULL, 
	avg_combined_impact FLOAT DEFAULT 0.0 NOT NULL, 
	avg_win_rate FLOAT DEFAULT 0.0 NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(player1_id) REFERENCES players (id) ON DELETE CASCADE, 
	FOREIGN KEY(player2_id) REFERENCES players (id) ON DELETE CASCADE
);

CREATE INDEX ix_player_synergies_id ON player_synergies (id);

CREATE INDEX ix_player_synergies_player1_id ON player_synergies (player1_id);

CREATE INDEX ix_player_synergies_player2_id ON player_synergies (player2_id);

CREATE TABLE performance_features (
	id INTEGER NOT NULL, 
	match_player_id INTEGER NOT NULL, 
	damage_ratio_z FLOAT DEFAULT 0.0 NOT NULL, 
	army_value_ratio_z FLOAT DEFAULT 0.0 NOT NULL, 
	combat_score_z FLOAT DEFAULT 0.0 NOT NULL, 
	spending_efficiency_z FLOAT DEFAULT 0.0 NOT NULL, 
	economic_score_z FLOAT DEFAULT 0.0 NOT NULL, 
	resource_advantage_z FLOAT DEFAULT 0.0 NOT NULL, 
	team_fight_participation_z FLOAT DEFAULT 0.0 NOT NULL, 
	team_fight_damage_ratio_z FLOAT DEFAULT 0.0 NOT NULL, 
	overall_impact_z FLOAT DEFAULT 0.0 NOT NULL, 
	efficiency_score_z FLOAT DEFAULT 0.0 NOT NULL, 
	pim FLOAT DEFAULT 0.0 NOT NULL, 
	pim_combat FLOAT DEFAULT 0.0 NOT NULL, 
	pim_economic FLOAT DEFAULT 0.0 NOT NULL, 
	pim_team FLOAT DEFAULT 0.0 NOT NULL, 
	pim_efficiency FLOAT DEFAULT 0.0 NOT NULL, 
	pim_version VARCHAR(20) DEFAULT 'rule_v1' NOT NULL, 
	raw_mmr_change FLOAT, 
	hybrid_mmr_change FLOAT, 
	build_order_json JSON, 
	build_order_hash VARCHAR(16), 
	detected_build_type VARCHAR(50), 
	upgrades_json JSON, 
	first_attack_upgrade_second INTEGER, 
	first_armor_upgrade_second INTEGER, 
	upgrade_timing_score FLOAT DEFAULT 0.0 NOT NULL, 
	abilities_json JSON, 
	total_abilities INTEGER DEFAULT 0 NOT NULL, 
	abilities_per_minute FLOAT DEFAULT 0.0 NOT NULL, 
	supply_block_seconds INTEGER DEFAULT 0 NOT NULL, 
	early_worker_losses INTEGER DEFAULT 0 NOT NULL, 
	harassment_response_score FLOAT DEFAULT 0.0 NOT NULL, 
	ml_macro_score FLOAT, 
	ml_micro_score FLOAT, 
	ml_predicted_pim FLOAT, 
	ml_win_probability FLOAT, 
	ml_shap_values JSON, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(match_player_id) REFERENCES match_players (id) ON DELETE CASCADE
);

CREATE INDEX ix_performance_features_build_order_hash ON performance_features (build_order_hash);

CREATE INDEX ix_performance_features_id ON performance_features (id);

CREATE UNIQUE INDEX ix_performance_features_match_player_id ON performance_features (match_player_id);

CREATE TABLE player_match_metrics (
	id INTEGER NOT NULL, 
	match_player_id INTEGER NOT NULL, 
	minerals_collected INTEGER DEFAULT 0 NOT NULL, 
	vespene_collected INTEGER DEFAULT 0 NOT NULL, 
	total_resources_collected INTEGER DEFAULT 0 NOT NULL, 
	resources_spent INTEGER DEFAULT 0 NOT NULL, 
	spending_efficiency FLOAT DEFAULT 0.0 NOT NULL, 
	workers_created INTEGER DEFAULT 0 NOT NULL, 
	workers_killed INTEGER DEFAULT 0 NOT NULL, 
	early_workers_killed INTEGER DEFAULT 0 NOT NULL, 
	mid_workers_killed INTEGER DEFAULT 0 NOT NULL, 
	workers_lost INTEGER DEFAULT 0 NOT NULL, 
	early_workers_lost INTEGER DEFAULT 0 NOT NULL, 
	units_trained INTEGER DEFAULT 0 NOT NULL, 
	units_lost INTEGER DEFAULT 0 NOT NULL, 
	units_killed INTEGER DEFAULT 0 NOT NULL, 
	kill_death_ratio FLOAT DEFAULT 1.0 NOT NULL, 
	army_value_built INTEGER DEFAULT 0 NOT NULL, 
	army_value_killed INTEGER DEFAULT 0 NOT NULL, 
	army_value_lost INTEGER DEFAULT 0 NOT NULL, 
	damage_dealt INTEGER DEFAULT 0 NOT NULL, 
	damage_taken INTEGER DEFAULT 0 NOT NULL, 
	damage_ratio FLOAT DEFAULT 0.0 NOT NULL, 
	first_expansion_timing INTEGER, 
	bases_created INTEGER DEFAULT 0 NOT NULL, 
	apm FLOAT DEFAULT 0.0 NOT NULL, 
	supply_block_seconds INTEGER DEFAULT 0 NOT NULL, 
	lethality_score FLOAT DEFAULT 0.0 NOT NULL, 
	unit_composition VARCHAR, 
	economic_score FLOAT DEFAULT 0.0 NOT NULL, 
	combat_score FLOAT DEFAULT 0.0 NOT NULL, 
	efficiency_score FLOAT DEFAULT 0.0 NOT NULL, 
	overall_impact FLOAT DEFAULT 0.0 NOT NULL, 
	team_fight_participation FLOAT DEFAULT 0.0 NOT NULL, 
	team_fight_damage INTEGER DEFAULT 0 NOT NULL, 
	team_fight_damage_ratio FLOAT DEFAULT 0.0 NOT NULL, 
	first_damage_timing INTEGER, 
	early_game_damage INTEGER DEFAULT 0 NOT NULL, 
	mid_game_damage INTEGER DEFAULT 0 NOT NULL, 
	late_game_damage INTEGER DEFAULT 0 NOT NULL, 
	player_archetype VARCHAR, 
	aggression_score FLOAT DEFAULT 50.0 NOT NULL, 
	damage_timeline VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(match_player_id) REFERENCES match_players (id) ON DELETE CASCADE
);

CREATE INDEX ix_player_match_metrics_id ON player_match_metrics (id);

CREATE UNIQUE INDEX ix_player_match_metrics_match_player_id ON player_match_metrics (match_player_id);
