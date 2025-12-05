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
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ==========================================================================
    # TrueSkill Rating Configuration
    # ==========================================================================
    trueskill_mu: float = 25.0           # Initial skill estimate
    trueskill_sigma: float = 8.333       # Initial uncertainty
    trueskill_beta: float = 4.166        # Skill class width (half of sigma)
    trueskill_tau: float = 0.0833        # Dynamics factor (skill change per day)
    trueskill_draw_probability: float = 0.0  # No draws in SC2

    # ==========================================================================
    # MMR Display Configuration
    # ==========================================================================
    mmr_base: int = 1000                 # Base MMR for display
    mmr_mu_multiplier: int = 40          # Multiplier for mu in display MMR
    mmr_sigma_multiplier: int = 120      # Multiplier for sigma in conservative MMR

    # ==========================================================================
    # Recency Weighting Configuration
    # ==========================================================================
    recency_half_life_days: int = 60     # Half-life for recency weighting
    recency_enabled: bool = True         # Enable/disable recency weighting

    # ==========================================================================
    # API Configuration
    # ==========================================================================
    api_title: str = "SC2 MMR Tracker API"
    api_version: str = "2.1.0"
    api_description: str = "StarCraft 2 MMR tracking system with TrueSkill rating"

    # ==========================================================================
    # Replay Processing Configuration
    # ==========================================================================
    max_replay_size_mb: int = 50         # Maximum replay file size in MB
    failed_replays_dir: str = "failed_replays"  # Directory for failed replay storage

    # ==========================================================================
    # Logging Configuration
    # ==========================================================================
    log_level: str = "INFO"              # Logging level


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures we only parse environment variables once.
    """
    return Settings()


# Global settings instance for easy import
settings = get_settings()
