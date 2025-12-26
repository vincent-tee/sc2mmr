-- Migration 007: Add ML Prediction Columns to PerformanceFeatures
-- Optimizing ML feature access by storing SHAP values and win probabilities

ALTER TABLE performance_features ADD COLUMN ml_win_probability FLOAT;
ALTER TABLE performance_features ADD COLUMN ml_shap_values JSON;
