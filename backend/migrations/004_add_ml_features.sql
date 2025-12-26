-- Migration 004: Add ML Features to PerformanceFeatures
-- SPEC-ML-001: Enhanced replay data extraction for ML models

-- Build Order Features
ALTER TABLE performance_features ADD COLUMN build_order_json JSON;
ALTER TABLE performance_features ADD COLUMN build_order_hash VARCHAR(16);
ALTER TABLE performance_features ADD COLUMN detected_build_type VARCHAR(50);

-- Upgrade Features
ALTER TABLE performance_features ADD COLUMN upgrades_json JSON;
ALTER TABLE performance_features ADD COLUMN first_attack_upgrade_second INTEGER;
ALTER TABLE performance_features ADD COLUMN first_armor_upgrade_second INTEGER;
ALTER TABLE performance_features ADD COLUMN upgrade_timing_score FLOAT DEFAULT 0.0;

-- Ability/Micro Features
ALTER TABLE performance_features ADD COLUMN abilities_json JSON;
ALTER TABLE performance_features ADD COLUMN total_abilities INTEGER DEFAULT 0;
ALTER TABLE performance_features ADD COLUMN abilities_per_minute FLOAT DEFAULT 0.0;

-- Macro Features
ALTER TABLE performance_features ADD COLUMN supply_block_seconds INTEGER DEFAULT 0;
ALTER TABLE performance_features ADD COLUMN early_worker_losses INTEGER DEFAULT 0;
ALTER TABLE performance_features ADD COLUMN harassment_response_score FLOAT DEFAULT 0.0;

-- ML Model Outputs
ALTER TABLE performance_features ADD COLUMN ml_macro_score FLOAT;
ALTER TABLE performance_features ADD COLUMN ml_micro_score FLOAT;
ALTER TABLE performance_features ADD COLUMN ml_predicted_pim FLOAT;

-- Index for build clustering
CREATE INDEX IF NOT EXISTS idx_build_order_hash ON performance_features(build_order_hash);
CREATE INDEX IF NOT EXISTS idx_detected_build_type ON performance_features(detected_build_type);
