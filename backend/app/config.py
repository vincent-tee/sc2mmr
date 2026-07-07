"""
Centralized configuration for SC2 MMR Tracker backend.

This module provides a single source of truth for all configuration values,
supporting environment variable overrides for deployment flexibility.

Usage:
    from app.config import settings

    # Access configuration
    db_url = settings.database_url
    cors_origins = settings.cors_origins
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden via environment variables.
    Example: DATABASE_URL=postgresql://... will override database_url
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ==========================================================================
    # Database Configuration
    # ==========================================================================
    database_url: str = "sqlite:///./data/sc2mmr.db"

    # ==========================================================================
    # CORS Configuration
    # ==========================================================================
    # List of allowed origins for CORS
    # In production, set CORS_ORIGINS="https://your-domain.com,https://app.your-domain.com"
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5175",
    ]

    # ==========================================================================
    # TrueSkill Rating Configuration
    # ==========================================================================
    trueskill_mu: float = 25.0  # Initial skill estimate
    trueskill_sigma: float = 8.333  # Initial uncertainty
    trueskill_beta: float = 5.0  # Performance variance (increased from 4.166)
    trueskill_tau: float = 0.25  # Dynamics factor (increased from 0.0833)
    trueskill_draw_probability: float = 0.0  # No draws in SC2

    # ==========================================================================
    # MMR Display Configuration
    # ==========================================================================
    mmr_base: int = 1000  # Base MMR for display
    mmr_mu_multiplier: int = (
        100  # Multiplier for mu (increased from 40 for dramatic changes)
    )
    mmr_sigma_multiplier: int = 300  # Multiplier for sigma (scaled with mu multiplier)

    # ==========================================================================
    # Recency Weighting Configuration
    # ==========================================================================
    recency_half_life_days: int = (
        90  # Half-life for recency weighting (increased from 60)
    )
    recency_enabled: bool = True  # Enable/disable recency weighting

    # ==========================================================================
    # Adaptive Decay Configuration
    # ==========================================================================
    adaptive_decay_enabled: bool = True  # Enable per-player adaptive decay
    adaptive_decay_multiplier: float = 2.0  # Start decay after 2x normal gap
    min_games_for_adaptive_decay: int = (
        5  # Minimum games to calculate player's typical gap
    )

    # ==========================================================================
    # Online Learning Configuration
    # ==========================================================================
    # Retraining thresholds (optimized for infrequent play sessions)
    retrain_threshold: int = 8  # Matches before retraining (was 30)
    min_matches_for_training: int = 30  # Minimum matches to start learning (was 100)
    training_window: int = 200  # Recent matches for training (was 500)

    # Session-aware learning
    session_gap_hours: float = 4.0  # Hours between matches to define new session
    session_weight_multiplier: float = (
        2.0  # Weight multiplier for current session matches
    )

    # Bayesian online updating
    bayesian_online_enabled: bool = True  # Enable incremental updates after each match
    upset_learning_boost: float = 1.5  # Learning boost for upset matches
    feature_importance_ema_alpha: float = (
        0.15  # EMA alpha for feature importance updates
    )

    # ==========================================================================
    # API Configuration
    # ==========================================================================
    api_title: str = "SC2 MMR Tracker API"
    api_version: str = "2.1.0"
    api_description: str = "StarCraft 2 MMR tracking system with TrueSkill rating"

    # ==========================================================================
    # Replay Processing Configuration
    # ==========================================================================
    max_replay_size_mb: int = 50  # Maximum replay file size in MB
    failed_replays_dir: str = "failed_replays"  # Directory for failed replay storage

    # Replay Storage Configuration
    replay_storage_enabled: bool = True  # Enable saving replay files
    replay_storage_dir: str = "replays"  # Directory for successful replay storage

    # Replay Observer Configuration
    observer_enabled: bool = True
    watch_directory: str = "/mnt/c/Users/tru_n/Documents/StarCraft II/Accounts/396750040/1-S2-1-11883598/Replays/Multiplayer"
    observer_debounce_seconds: float = 2.0  # Wait for file write to complete
    observer_initial_scan: bool = True  # Scan directory on startup
    # CommandCenter parser requires matching SC2 Linux version (only 4.10 available)
    # Disabled by default - enable when Docker SC2 setup is complete
    observer_use_cc_parser: bool = False  # Use high-fidelity CommandCenter parser

    # Enrich manually-uploaded replays (POST /replays/upload) with true
    # engine-derived damage/economy stats from CommandCenter, in the
    # background after the response is sent (never blocks the upload
    # request). Same SC2-version caveat as observer_use_cc_parser above;
    # also confirmed 2026-07-03 that the SC2 engine can fail to start in
    # headless/sandboxed environments, so this stays opt-in even when
    # is_commandcenter_available() reports true.
    upload_cc_enrichment_enabled: bool = False

    # ==========================================================================
    # Logging Configuration
    # ==========================================================================
    log_level: str = "INFO"

    # ==========================================================================
    # Hybrid MMR Configuration (SPEC-ML-001)
    # ==========================================================================
    # Enable/disable hybrid MMR system
    # Soft-retired 2026-07-02 (rating consolidation campaign Phase 6):
    # superseded by the display-MMR rating of record; column drop pending.
    hybrid_mmr_enabled: bool = False

    # PIM (Performance Impact Modifier) bounds
    pim_min: float = -0.5  # Minimum PIM value (50% less MMR change)
    pim_max: float = 0.5  # Maximum PIM value (50% more MMR change)

    # PIM calculation version
    pim_version: str = "rule_v1"  # "rule_v1" (weighted formula) or future "ml_v1"

    # PIM Weight Configuration (must sum to 1.0)
    # Combat metrics (40% total)
    pim_weight_damage_ratio: float = 0.15
    pim_weight_army_value_ratio: float = 0.15
    pim_weight_combat_score: float = 0.10

    # Economic metrics (25% total)
    pim_weight_spending_efficiency: float = 0.10
    pim_weight_economic_score: float = 0.10
    pim_weight_resource_advantage: float = 0.05

    # Team contribution metrics (25% total)
    pim_weight_team_fight_participation: float = 0.10
    pim_weight_team_fight_damage_ratio: float = 0.10
    pim_weight_overall_impact: float = 0.05

    # Efficiency metrics (10% total)
    pim_weight_efficiency_score: float = 0.10


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures we only parse environment variables once.
    """
    return Settings()


# Global settings instance for easy import
settings = get_settings()
