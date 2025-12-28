-- Migration: Add updated_at column to matches table
-- Purpose: Track when matches are re-uploaded with new features
-- Date: 2025-01-28

-- Add updated_at column with default value
ALTER TABLE matches ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Set initial updated_at to created_at for existing records
UPDATE matches SET updated_at = created_at WHERE updated_at IS NULL;
