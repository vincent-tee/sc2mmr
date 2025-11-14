-- Migration: Add replay_file_path column to failed_uploads table
-- Date: 2025-01-14
-- Description: Adds replay_file_path column to store replay files for manual review

-- Add replay_file_path column if it doesn't exist
-- SQLite doesn't support ALTER TABLE IF EXISTS, so this will error if column already exists
-- Run this manually or handle the error gracefully

ALTER TABLE failed_uploads ADD COLUMN replay_file_path VARCHAR;

-- Note: This migration can be safely rerun if it fails (column already exists)
