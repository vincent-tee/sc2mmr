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
        # Settings that were removed (hybrid MMR, PIM weights, online learning)
        # may still be set in an existing .env; ignore them instead of
        # refusing to start.
        extra="ignore",
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

    # Win-probability PREDICTION only, not trueskill.rate() updates above.
    # Out-of-sample-validated, see rating-consolidation-log.md Session 9.
    win_probability_variance_scale: float = 11.0

    # ==========================================================================
    # MMR Display Configuration
    # ==========================================================================
    mmr_base: int = 1000  # Base MMR for display
    mmr_mu_multiplier: int = (
        100  # Multiplier for mu (increased from 40 for dramatic changes)
    )

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

    # Hours between a player's games before the next one counts as a new
    # session (used to work out each player's typical gap between sessions).
    session_gap_hours: float = 4.0

    # ==========================================================================
    # API Configuration
    # ==========================================================================
    api_title: str = "SC2 MMR Tracker API"
    api_version: str = "2.1.0"
    api_description: str = "StarCraft 2 MMR tracking system with TrueSkill rating"

    # ==========================================================================
    # Access Control (for hosting the app online)
    # ==========================================================================
    # Master switch. False (default) = app behaves exactly as before: fully
    # open, intended for localhost/LAN use only. True = every endpoint except
    # /health and /auth/* requires the shared group password session cookie.
    auth_enabled: bool = False
    # The shared squad password. Must be set when auth_enabled is True or
    # logins are rejected with a config error.
    group_password: str = ""
    # Public-read mode: anonymous GETs are allowed (browse the ladder without
    # logging in) while every write - uploads included - still requires the
    # session. Replay downloads and the API docs stay session-gated even for
    # GET: downloads are the one path where a stored file reaches someone's
    # machine (malware-distribution defense), and /docs is developer surface.
    auth_public_read: bool = False
    # Secret for signing session cookies. If empty while auth is enabled, a
    # random per-process secret is generated at startup (works, but everyone
    # is logged out whenever the server restarts - set it in production).
    auth_secret: str = ""
    # Session cookie lifetime (default one year; each device re-logs-in ~annually).
    auth_session_days: int = 365
    # Cookie attributes. The frontend reaches the API same-origin via the
    # Vercel /api proxy (see frontend/vercel.json), so the session cookie is
    # first-party to the app domain and SameSite=Lax is correct - and Lax
    # blocks cross-site POST from carrying the cookie, which closes the CSRF
    # write vector. (If you ever call Cloud Run cross-site directly again,
    # you'd need SameSite=None + Secure, which reopens CSRF - keep the proxy.)
    # For local testing with auth over plain http, set AUTH_COOKIE_SECURE=false.
    auth_cookie_secure: bool = True
    auth_cookie_samesite: str = "lax"  # "none" | "lax" | "strict"
    # Extra shared secret (X-Admin-Token header) required for destructive
    # admin endpoints (rating recalc, player merge, ML retrain, bulk
    # recalculations). Empty (default) = not enforced, preserving current
    # local behavior.
    admin_token: str = ""

    # ==========================================================================
    # Replay Processing Configuration
    # ==========================================================================
    max_replay_size_mb: int = 50  # Maximum replay file size in MB
    failed_replays_dir: str = "failed_replays"  # Directory for failed replay storage

    # Replay Storage Configuration
    replay_storage_enabled: bool = True  # Enable saving replay files
    replay_storage_dir: str = "replays"  # Directory for successful replay storage
    # When set (e.g. "my-sc2mmr-replays"), replay files are stored in this
    # GCS bucket instead of local directories - required on Cloud Run, whose
    # filesystem is ephemeral. Needs the google-cloud-storage package and
    # application-default credentials (automatic on Cloud Run).
    replay_gcs_bucket: str = ""

    # Enrich manually-uploaded replays (POST /replays/upload) with true
    # engine-derived damage/economy stats from CommandCenter, in the
    # background after the response is sent (never blocks the upload
    # request). Requires the Docker SC2 4.10 Linux setup; also confirmed
    # 2026-07-03 that the SC2 engine can fail to start in headless/sandboxed
    # environments, so this stays opt-in even when
    # is_commandcenter_available() reports true.
    upload_cc_enrichment_enabled: bool = False

    # ==========================================================================
    # Logging Configuration
    # ==========================================================================
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures we only parse environment variables once.
    """
    return Settings()


# Global settings instance for easy import
settings = get_settings()
