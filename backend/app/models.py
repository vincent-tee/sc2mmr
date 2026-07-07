"""
Database models for SC2 MMR tracking system.

Uses SQLAlchemy 2.0 Mapped type annotations for proper type checking.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
import enum


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Player(Base):
    """
    Represents a player in the system.

    TrueSkill rating consists of:
    - mu: skill estimate (default 25.0)
    - sigma: uncertainty (default 8.333, decreases with more games)

    Hybrid MMR System:
    - mmr: Display MMR based on TrueSkill (1000 + 100*mu - 200*sigma)
    - hybrid_mmr: Performance-adjusted MMR that accounts for in-game metrics
    - avg_pim: Average Performance Impact Modifier across all games
    """

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    # TrueSkill rating
    mu: Mapped[float] = mapped_column(Float, default=25.0, nullable=False)
    sigma: Mapped[float] = mapped_column(Float, default=8.333, nullable=False)

    # Recency-weighted MMR (weights recent matches more heavily)
    recency_weighted_mmr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Hybrid MMR System (SPEC-ML-001)
    # Performance-adjusted MMR that combines TrueSkill with in-game metrics
    hybrid_mmr: Mapped[Optional[float]] = mapped_column(
        Float, default=2000.0, nullable=True
    )  # Defaults to starting display MMR
    avg_pim: Mapped[Optional[float]] = mapped_column(
        Float, default=0.0, nullable=True
    )  # Average Performance Impact Modifier

    # Statistics
    total_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Race statistics
    terran_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    protoss_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    zerg_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    random_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_played: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_core_player: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # 1 for core, 0 for outsider
    is_ai: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 1 for AI/Computer player, 0 for human

    # Session-weighted MMR for faster adaptation (ML Balancing)
    session_weighted_mmr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_session_weight_update: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Average impact scores (calculated from all matches)
    avg_economic_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_combat_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_efficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_overall_impact: Mapped[float] = mapped_column(Float, default=0.0)
    avg_harassment_score: Mapped[float] = mapped_column(Float, default=0.0)  # NEW

    # Timing profile (averaged across all games)
    avg_first_damage_timing: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    primary_archetype: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Most common archetype
    avg_aggression_score: Mapped[float] = mapped_column(Float, default=50.0)

    # Recency-weighted impact scores (60-day half-life decay)
    # These weight recent performance more heavily than older games
    recency_weighted_combat: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    recency_weighted_economic: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    recency_weighted_efficiency: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    recency_weighted_overall_impact: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Relationships
    match_participations: Mapped[List["MatchPlayer"]] = relationship(
        "MatchPlayer", back_populates="player", passive_deletes=True
    )

    @property
    def win_rate(self) -> float:
        """Calculate win rate as decimal (0.0 to 1.0)."""
        if self.total_games == 0:
            return 0.0
        return float(self.wins) / float(self.total_games)

    # Display MMR (Official) - Centralized source of truth
    # Calculated as: 1000 + 100*mu - 200*sigma
    mmr: Mapped[float] = mapped_column(Float, default=1833.0, nullable=False)

    # Handicap-Corrected MMR (intermediate calculation)
    # Accounts for balancing bias where top players are put on weaker teams
    # Formula: mmr + (outperformance * 3000)
    # Where outperformance = actual_win_rate - expected_win_rate_given_handicap
    handicap_corrected_mmr: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    avg_team_handicap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outperformance_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Unified MMR (THE primary rating - SPEC-UNIFIED-MMR)
    # Formula: handicap_corrected_mmr + (20 * avg_combat_score)
    # Combines TrueSkill + handicap correction + combat contribution
    unified_mmr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    @property
    def favorite_race(self) -> str:
        """Determine player's most played race."""
        races: dict[str, int] = {
            "Terran": self.terran_games,
            "Protoss": self.protoss_games,
            "Zerg": self.zerg_games,
            "Random": self.random_games,
        }
        if max(races.values()) == 0:
            return "Unknown"
        return max(races, key=lambda k: races[k])


class GameMode(str, enum.Enum):
    """Enum for different game modes."""

    # Even team modes
    ONE_V_ONE = "1v1"
    TWO_V_TWO = "2v2"
    THREE_V_THREE = "3v3"
    FOUR_V_FOUR = "4v4"
    FIVE_V_FIVE = "5v5"

    # Uneven team modes
    TWO_V_ONE = "2v1"
    THREE_V_ONE = "3v1"
    THREE_V_TWO = "3v2"
    FOUR_V_ONE = "4v1"
    FOUR_V_TWO = "4v2"
    FOUR_V_THREE = "4v3"
    FIVE_V_ONE = "5v1"
    FIVE_V_TWO = "5v2"
    FIVE_V_THREE = "5v3"
    FIVE_V_FOUR = "5v4"


class Race(str, enum.Enum):
    """Enum for StarCraft 2 races."""

    TERRAN = "Terran"
    PROTOSS = "Protoss"
    ZERG = "Zerg"
    RANDOM = "Random"


class Match(Base):
    """
    Represents a single game/match.
    """

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Game details
    played_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    game_mode: Mapped[GameMode] = mapped_column(SQLEnum(GameMode), nullable=False)
    map_name: Mapped[str] = mapped_column(String, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    # Replay information
    replay_file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    replay_hash: Mapped[Optional[str]] = mapped_column(
        String, unique=True, nullable=True, index=True
    )  # To prevent duplicate uploads
    game_fingerprint: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )  # Identifies same game from different observers (map+time+players)

    # Win probability predictions (calculated before match from TrueSkill ratings)
    predicted_team1_win_prob: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0.0 to 1.0
    predicted_team2_win_prob: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0.0 to 1.0
    # Note: team1 + team2 should equal 1.0 (complementary probabilities)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )  # Tracks when match data was re-uploaded/updated

    # Relationships
    participants: Mapped[List["MatchPlayer"]] = relationship(
        "MatchPlayer", back_populates="match", passive_deletes=True
    )


class MatchPlayer(Base):
    """
    Represents a player's participation in a specific match.
    Stores a snapshot of the player's rating at the time of the match.
    """

    __tablename__ = "match_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Match details
    team_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    race: Mapped[Race] = mapped_column(SQLEnum(Race), nullable=False)
    won: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 for win, 0 for loss

    # Rating snapshot (before and after this match)
    mu_before: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_before: Mapped[float] = mapped_column(Float, nullable=False)
    mu_after: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Official MMR snapshot (calculated from mu/sigma)
    mmr_before: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mmr_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    @property
    def mmr_change(self) -> float:
        """Calculate the MMR change from this match."""
        if self.mmr_after is not None and self.mmr_before is not None:
            return self.mmr_after - self.mmr_before
        return 0.0

    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="participants")
    player: Mapped["Player"] = relationship(
        "Player", back_populates="match_participations"
    )
    performance_features: Mapped[Optional["PerformanceFeatures"]] = relationship(
        "PerformanceFeatures",
        back_populates="match_player",
        uselist=False,
        passive_deletes=True,
    )
    metrics: Mapped[Optional["PlayerMatchMetrics"]] = relationship(
        "PlayerMatchMetrics",
        back_populates="match_player",
        uselist=False,
        passive_deletes=True,
    )


class PlayerMatchMetrics(Base):
    """
    Detailed performance metrics for a player in a specific match.
    Extends MatchPlayer with advanced statistics.
    """

    __tablename__ = "player_match_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to MatchPlayer
    match_player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("match_players.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Economic metrics
    minerals_collected: Mapped[int] = mapped_column(Integer, default=0)
    vespene_collected: Mapped[int] = mapped_column(Integer, default=0)
    total_resources_collected: Mapped[int] = mapped_column(Integer, default=0)
    resources_spent: Mapped[int] = mapped_column(Integer, default=0)
    spending_efficiency: Mapped[float] = mapped_column(Float, default=0.0)
    workers_created: Mapped[int] = mapped_column(Integer, default=0)
    workers_killed: Mapped[int] = mapped_column(Integer, default=0)
    early_workers_killed: Mapped[int] = mapped_column(Integer, default=0)
    mid_workers_killed: Mapped[int] = mapped_column(Integer, default=0)
    workers_lost: Mapped[int] = mapped_column(Integer, default=0)
    early_workers_lost: Mapped[int] = mapped_column(Integer, default=0)

    # Army metrics
    units_trained: Mapped[int] = mapped_column(Integer, default=0)
    units_lost: Mapped[int] = mapped_column(Integer, default=0)
    units_killed: Mapped[int] = mapped_column(Integer, default=0)
    army_value_built: Mapped[int] = mapped_column(Integer, default=0)
    army_value_killed: Mapped[int] = mapped_column(Integer, default=0)
    army_value_lost: Mapped[int] = mapped_column(Integer, default=0)
    kill_death_ratio: Mapped[float] = mapped_column(Float, default=1.0)

    # Combat metrics
    damage_dealt: Mapped[int] = mapped_column(Integer, default=0)
    damage_taken: Mapped[int] = mapped_column(Integer, default=0)
    damage_ratio: Mapped[float] = mapped_column(Float, default=0.0)

    # Timing metrics (game seconds)
    first_expansion_timing: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    bases_created: Mapped[int] = mapped_column(Integer, default=0)

    # Mechanics
    apm: Mapped[float] = mapped_column(Float, default=0.0)
    supply_block_seconds: Mapped[int] = mapped_column(Integer, default=0)
    lethality_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Unit composition (stored as JSON string)
    unit_composition: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # JSON: {"Marine": 50, "Marauder": 20}

    # Impact scores
    economic_score: Mapped[float] = mapped_column(Float, default=0.0)
    combat_score: Mapped[float] = mapped_column(Float, default=0.0)
    efficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_impact: Mapped[float] = mapped_column(Float, default=0.0)

    # Team game metrics
    team_fight_participation: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # % of team fights participated in (0-1)
    team_fight_damage: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Damage dealt in multi-player engagements
    team_fight_damage_ratio: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # Team fight damage / total damage

    # Timing analysis
    first_damage_timing: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Game seconds
    early_game_damage: Mapped[int] = mapped_column(Integer, default=0)  # 0-5min
    mid_game_damage: Mapped[int] = mapped_column(Integer, default=0)  # 5-10min
    late_game_damage: Mapped[int] = mapped_column(Integer, default=0)  # 10+min
    player_archetype: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Rusher, TimingAttacker, LateGame, etc.
    aggression_score: Mapped[float] = mapped_column(Float, default=50.0)  # 0-100

    # Second-by-second damage timeline (sparse storage)
    damage_timeline: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # JSON: {187: 250, 325: 1200, ...}
    # Only stores seconds where damage occurred - typically 20-100 events per game
    # Key = game second, Value = damage dealt that second

    # Relationship
    match_player: Mapped["MatchPlayer"] = relationship(
        "MatchPlayer", back_populates="metrics"
    )


class PlayerSynergy(Base):
    """
    Tracks synergy between pairs of players.
    """

    __tablename__ = "player_synergies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Player pair (always store with player1_id < player2_id for consistency)
    player1_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player2_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Synergy metrics
    games_together: Mapped[int] = mapped_column(Integer, default=0)
    wins_together: Mapped[int] = mapped_column(Integer, default=0)
    losses_together: Mapped[int] = mapped_column(Integer, default=0)

    # Synergy score (0-100)
    synergy_score: Mapped[float] = mapped_column(Float, default=50.0)

    # Average performance together
    avg_combined_impact: Mapped[float] = mapped_column(Float, default=0.0)
    avg_win_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Last updated
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    player1: Mapped["Player"] = relationship("Player", foreign_keys=[player1_id])
    player2: Mapped["Player"] = relationship("Player", foreign_keys=[player2_id])

    @property
    def win_rate_together(self) -> float:
        """Calculate win rate when playing together."""
        if self.games_together == 0:
            return 0.0
        return (float(self.wins_together) / float(self.games_together)) * 100


class UploadErrorType(enum.Enum):
    """Types of replay upload errors."""

    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    WINNER_DETERMINATION = "winner_determination"
    UNSUPPORTED_MODE = "unsupported_mode"
    CORRUPT_FILE = "corrupt_file"
    OTHER = "other"


class FailedUpload(Base):
    """
    Tracks replay files that failed to process.

    This helps identify problematic replays that need manual review or
    algorithm improvements to handle edge cases.
    """

    __tablename__ = "failed_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # File information
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    replay_hash: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    replay_file_path: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Saved file path for manual review

    # Error details
    error_type: Mapped[UploadErrorType] = mapped_column(
        SQLEnum(UploadErrorType), nullable=False, index=True
    )
    error_message: Mapped[str] = mapped_column(String, nullable=False)
    error_detail: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Full stack trace or additional context

    # Match metadata (if partially parsed)
    map_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    game_mode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    num_players: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Review status
    reviewed: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0 = not reviewed, 1 = reviewed
    review_notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class PerformanceFeatures(Base):
    """
    ML-ready feature store for Performance Impact Modifier (PIM) calculation.

    Stores normalized metrics (z-scores) and calculated PIM for each player's
    match performance. This enables:
    - Rule-based PIM calculation (Phase 1)
    - ML model training data collection (Phase 2)
    - A/B testing between rule-based and ML approaches (Phase 3)

    SPEC-ML-001 Implementation.
    """

    __tablename__ = "performance_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to MatchPlayer
    match_player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("match_players.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # =========================================================================
    # Z-score normalized features (relative to match average)
    # Positive = above average, Negative = below average
    # =========================================================================

    # Combat metrics (40% weight in rule-based formula)
    damage_ratio_z: Mapped[float] = mapped_column(Float, default=0.0)
    army_value_ratio_z: Mapped[float] = mapped_column(Float, default=0.0)
    combat_score_z: Mapped[float] = mapped_column(Float, default=0.0)

    # Economic metrics (25% weight)
    spending_efficiency_z: Mapped[float] = mapped_column(Float, default=0.0)
    economic_score_z: Mapped[float] = mapped_column(Float, default=0.0)
    resource_advantage_z: Mapped[float] = mapped_column(Float, default=0.0)

    # Team contribution metrics (25% weight)
    team_fight_participation_z: Mapped[float] = mapped_column(Float, default=0.0)
    team_fight_damage_ratio_z: Mapped[float] = mapped_column(Float, default=0.0)
    overall_impact_z: Mapped[float] = mapped_column(Float, default=0.0)

    # Efficiency metrics (10% weight)
    efficiency_score_z: Mapped[float] = mapped_column(Float, default=0.0)

    # =========================================================================
    # Calculated Performance Impact Modifier
    # =========================================================================

    # PIM value (range: -0.5 to +0.5)
    pim: Mapped[float] = mapped_column(Float, default=0.0)

    # PIM breakdown by category (for transparency/debugging)
    pim_combat: Mapped[float] = mapped_column(Float, default=0.0)
    pim_economic: Mapped[float] = mapped_column(Float, default=0.0)
    pim_team: Mapped[float] = mapped_column(Float, default=0.0)
    pim_efficiency: Mapped[float] = mapped_column(Float, default=0.0)

    # Version of PIM calculation algorithm used
    pim_version: Mapped[str] = mapped_column(String(20), default="rule_v1")

    # =========================================================================
    # MMR Change Tracking
    # =========================================================================

    # Raw TrueSkill MMR change (without PIM adjustment)
    raw_mmr_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Hybrid MMR change (with PIM applied)
    hybrid_mmr_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # =========================================================================
    # Enhanced ML Features (Phase 2A - SPEC-ML-001)
    # =========================================================================

    # Build Order Features
    build_order_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Full build sequence
    build_order_hash: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, index=True
    )  # For clustering
    detected_build_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # "rush", "macro", "timing", "cheese"

    # Upgrade Features
    upgrades_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # [{second, name, category}]
    first_attack_upgrade_second: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    first_armor_upgrade_second: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    upgrade_timing_score: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # Z-score vs average

    # Ability/Micro Features
    abilities_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # {"Stim": 15, "EMP": 3}
    total_abilities: Mapped[int] = mapped_column(Integer, default=0)
    abilities_per_minute: Mapped[float] = mapped_column(Float, default=0.0)

    # Macro Features
    supply_block_seconds: Mapped[int] = mapped_column(Integer, default=0)
    early_worker_losses: Mapped[int] = mapped_column(Integer, default=0)
    harassment_response_score: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # 0-100

    # ML Model Outputs (Phase 2B+)
    ml_macro_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0-100
    ml_micro_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0-100
    ml_predicted_pim: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # ML model prediction
    ml_win_probability: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # ML model win probability
    ml_shap_values: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # SHAP feature importance values

    # =========================================================================
    # Metadata
    # =========================================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationship
    match_player: Mapped["MatchPlayer"] = relationship(
        "MatchPlayer", back_populates="performance_features"
    )


class AchievementCategory(str, enum.Enum):
    """Categories for organizing achievements."""

    MILESTONE = "milestone"  # Games played, wins, etc.
    STREAK = "streak"  # Win/loss streaks
    COMBAT = "combat"  # Damage, kills, etc.
    ECONOMIC = "economic"  # Resources, efficiency
    TEAMWORK = "teamwork"  # Synergy, team contribution
    VARIETY = "variety"  # Race diversity, map variety
    SPECIAL = "special"  # Unique/rare achievements
    MEME = "meme"  # Funny/inside joke achievements
    ESPORTS = "esports"  # Commentary-style epic achievements


class AchievementRarity(str, enum.Enum):
    """Rarity tiers for achievements."""

    COMMON = "common"  # Easy to get (50%+ players)
    UNCOMMON = "uncommon"  # Moderate difficulty (25-50%)
    RARE = "rare"  # Challenging (10-25%)
    EPIC = "epic"  # Very difficult (5-10%)
    LEGENDARY = "legendary"  # Elite status (< 5%)
    MYTHIC = "mythic"  # One-of-a-kind or near impossible


class Achievement(Base):
    """
    Defines an achievement/badge that players can earn.
    """

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identity
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    flavor_text: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Classification
    category: Mapped[AchievementCategory] = mapped_column(
        SQLEnum(AchievementCategory), nullable=False, index=True
    )
    rarity: Mapped[AchievementRarity] = mapped_column(
        SQLEnum(AchievementRarity), nullable=False, index=True
    )

    # Visual
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Requirements
    requirement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    requirement_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    requirement_extra: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Metadata
    points: Mapped[int] = mapped_column(Integer, default=10)
    is_hidden: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    player_achievements: Mapped[List["PlayerAchievement"]] = relationship(
        "PlayerAchievement", back_populates="achievement", passive_deletes=True
    )


class PlayerAchievement(Base):
    """
    Links players to their earned achievements.
    """

    __tablename__ = "player_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    achievement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("achievements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When earned
    earned_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Context (what triggered it)
    trigger_match_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=True
    )
    trigger_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Display
    is_featured: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    player: Mapped["Player"] = relationship("Player", backref="player_achievements")
    achievement: Mapped["Achievement"] = relationship(
        "Achievement", back_populates="player_achievements"
    )


class PlayerRivalry(Base):
    """
    Tracks head-to-head rivalry between two players.
    """

    __tablename__ = "player_rivalries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Player pair (always store with player1_id < player2_id for consistency)
    player1_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player2_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Games against each other (on opposite teams)
    games_against: Mapped[int] = mapped_column(Integer, default=0)
    player1_wins: Mapped[int] = mapped_column(Integer, default=0)
    player2_wins: Mapped[int] = mapped_column(Integer, default=0)

    # Intensity metrics
    avg_mmr_swing: Mapped[float] = mapped_column(Float, default=0.0)
    biggest_upset_mmr: Mapped[float] = mapped_column(Float, default=0.0)

    # Last meeting
    last_match_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=True
    )
    last_match_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Rivalry score (calculated)
    rivalry_score: Mapped[float] = mapped_column(Float, default=0.0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    player1: Mapped["Player"] = relationship(
        "Player", foreign_keys=[player1_id], backref="rivalries_as_player1"
    )
    player2: Mapped["Player"] = relationship(
        "Player", foreign_keys=[player2_id], backref="rivalries_as_player2"
    )


class FeatureSuggestion(Base):
    """
    Suggested new features for the ML model.
    """

    __tablename__ = "feature_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, reviewed, implemented
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlayerAlias(Base):
    """
    Canonical name mapping for players with multiple accounts/barcodes.
    Allows conditional mapping (e.g., only for team games).
    """

    __tablename__ = "player_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_name: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    target_player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )

    min_players: Mapped[int] = mapped_column(Integer, default=4)
    exclude_1v1: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    target_player: Mapped["Player"] = relationship("Player", backref="aliases")


class MetaFeedback(Base):
    """
    User feedback or "squad theories" about match dynamics.
    """

    __tablename__ = "meta_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    theory: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Integer, default=1
    )  # 1 for active, 0 for inactive
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupSynergy(Base):
    """
    Cache duo/trio synergy scores for ML balancing.

    Unlike PlayerSynergy which tracks pairs of players via foreign keys,
    this table uses a composite string key (e.g., "1,2,3") to efficiently
    cache synergy for any group size (duos, trios, etc.).
    """

    __tablename__ = "player_synergy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_ids_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    player_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    matches_won: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    synergy_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ComponentAccuracy(Base):
    """
    Track prediction accuracy by component across all history.

    Uses Exponential Moving Average (EMA) to weight recent predictions
    more heavily while still considering historical performance.
    """

    __tablename__ = "component_accuracy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    predictions_correct: Mapped[int] = mapped_column(Integer, default=0)
    predictions_total: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.5)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MLConfig(Base):
    """
    Store ML configuration like recommended weights from regression analysis.

    Key-value store for ML system configuration parameters.
    """

    __tablename__ = "ml_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    config_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    config_value: Mapped[str] = mapped_column(String, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BalancePrediction(Base):
    """
    Captures a balancer suggestion at balance time so it can later be
    resolved against the actual match outcome (calibration tracking).

    players_key is the sorted comma-separated IDs of ALL players in the
    suggestion; it is used to match a prediction to an uploaded replay.
    """

    __tablename__ = "balance_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Which objective produced this suggestion (e.g. "mmr_v1", "composite_v1")
    method: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # Position of this suggestion in the returned list (1 = top pick)
    rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    players_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    team1_ids_key: Mapped[str] = mapped_column(String, nullable=False)
    team2_ids_key: Mapped[str] = mapped_column(String, nullable=False)

    # Prediction snapshot at balance time
    predicted_team1_win_prob: Mapped[float] = mapped_column(Float, nullable=False)
    match_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    balance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mmr_difference: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # JSON blob of objective components (spread/component/synergy terms)
    features_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Resolution against the actual match
    resolved: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, index=True
    )
    match_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True
    )
    team1_won: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    brier_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class LiveMatchFeed(Base):
    """
    Feed for live match detection events.
    Enables '10/10' Strategic Forecast feature.
    """

    __tablename__ = "live_match_feed"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    match_id: Mapped[int] = mapped_column(Integer, nullable=False)
    map_name: Mapped[str] = mapped_column(String, nullable=False)
    forecast_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Integer, default=1)


ACHIEVEMENT_DEFINITIONS = [
    # =======================================================================
    # MILESTONE ACHIEVEMENTS (Games & Wins)
    # =======================================================================
    {
        "code": "FIRST_BLOOD",
        "name": "First Blood",
        "description": "Play your first match",
        "flavor_text": "Everyone starts somewhere. Welcome to the battlefield!",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.COMMON,
        "icon": "🎮",
        "requirement_type": "games_played",
        "requirement_threshold": 1,
        "points": 5,
    },
    {
        "code": "GETTING_STARTED",
        "name": "Getting Started",
        "description": "Play 10 matches",
        "flavor_text": "You're starting to get the hang of this.",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.COMMON,
        "icon": "🌱",
        "requirement_type": "games_played",
        "requirement_threshold": 10,
        "points": 10,
    },
    {
        "code": "VETERAN",
        "name": "Veteran",
        "description": "Play 50 matches",
        "flavor_text": "You've seen some things. Things that can't be unseen.",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "⭐",
        "requirement_type": "games_played",
        "requirement_threshold": 50,
        "points": 25,
    },
    {
        "code": "CENTURION",
        "name": "Centurion",
        "description": "Play 100 matches",
        "flavor_text": "100 games. That's dedication. Or addiction. Maybe both.",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.RARE,
        "icon": "💯",
        "requirement_type": "games_played",
        "requirement_threshold": 100,
        "points": 50,
    },
    {
        "code": "NO_LIFE",
        "name": "No Life",
        "description": "Play 150+ matches",
        "flavor_text": "Touch grass? Never heard of her.",
        "category": AchievementCategory.MEME,
        "rarity": AchievementRarity.EPIC,
        "icon": "🎯",
        "requirement_type": "games_played",
        "requirement_threshold": 150,
        "points": 100,
    },
    {
        "code": "FIRST_WIN",
        "name": "Victory Tastes Sweet",
        "description": "Win your first match",
        "flavor_text": "The first of many... or is it?",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.COMMON,
        "icon": "🏆",
        "requirement_type": "wins",
        "requirement_threshold": 1,
        "points": 5,
    },
    {
        "code": "DOUBLE_DIGITS",
        "name": "Double Digits",
        "description": "Win 10 matches",
        "flavor_text": "You can count your wins on two hands now!",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.COMMON,
        "icon": "✌️",
        "requirement_type": "wins",
        "requirement_threshold": 10,
        "points": 15,
    },
    {
        "code": "WINNING_MACHINE",
        "name": "Winning Machine",
        "description": "Win 50 matches",
        "flavor_text": "Your opponents fear the queue when you're online.",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.RARE,
        "icon": "🤖",
        "requirement_type": "wins",
        "requirement_threshold": 50,
        "points": 50,
    },
    # =======================================================================
    # STREAK ACHIEVEMENTS
    # =======================================================================
    {
        "code": "HOT_STREAK_3",
        "name": "Getting Warm",
        "description": "Win 3 matches in a row",
        "flavor_text": "Is it getting hot in here?",
        "category": AchievementCategory.STREAK,
        "rarity": AchievementRarity.COMMON,
        "icon": "🔥",
        "requirement_type": "win_streak",
        "requirement_threshold": 3,
        "points": 10,
    },
    {
        "code": "HOT_STREAK_5",
        "name": "On Fire",
        "description": "Win 5 matches in a row",
        "flavor_text": "Someone call the fire department!",
        "category": AchievementCategory.STREAK,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "🔥🔥",
        "requirement_type": "win_streak",
        "requirement_threshold": 5,
        "points": 25,
    },
    {
        "code": "HOT_STREAK_10",
        "name": "Unstoppable",
        "description": "Win 10 matches in a row",
        "flavor_text": "THE UNSTOPPABLE FORCE! Is this player even human?!",
        "category": AchievementCategory.ESPORTS,
        "rarity": AchievementRarity.EPIC,
        "icon": "💥",
        "requirement_type": "win_streak",
        "requirement_threshold": 10,
        "points": 75,
    },
    {
        "code": "HOT_STREAK_15",
        "name": "God Mode Activated",
        "description": "Win 15+ matches in a row",
        "flavor_text": "Is this legal? Someone check if they're smurfing!",
        "category": AchievementCategory.ESPORTS,
        "rarity": AchievementRarity.LEGENDARY,
        "icon": "👑",
        "requirement_type": "win_streak",
        "requirement_threshold": 15,
        "points": 150,
    },
    {
        "code": "COLD_STREAK_3",
        "name": "Bad Day",
        "description": "Lose 3 matches in a row",
        "flavor_text": "Hey, it happens to the best of us.",
        "category": AchievementCategory.STREAK,
        "rarity": AchievementRarity.COMMON,
        "icon": "❄️",
        "requirement_type": "loss_streak",
        "requirement_threshold": 3,
        "points": 5,
        "is_hidden": True,
    },
    {
        "code": "COLD_STREAK_5",
        "name": "Rough Patch",
        "description": "Lose 5 matches in a row",
        "flavor_text": "Have you tried turning your computer off and on again?",
        "category": AchievementCategory.STREAK,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "🥶",
        "requirement_type": "loss_streak",
        "requirement_threshold": 5,
        "points": 10,
        "is_hidden": True,
    },
    {
        "code": "COLD_STREAK_10",
        "name": "The Tilt Lord",
        "description": "Lose 10+ matches in a row",
        "flavor_text": "At this point, it's impressive. Respect the commitment.",
        "category": AchievementCategory.MEME,
        "rarity": AchievementRarity.RARE,
        "icon": "🧊",
        "requirement_type": "loss_streak",
        "requirement_threshold": 10,
        "points": 25,
        "is_hidden": True,
    },
    # =======================================================================
    # COMBAT ACHIEVEMENTS
    # =======================================================================
    {
        "code": "DAMAGE_DEALER",
        "name": "Damage Dealer",
        "description": "Deal 50,000+ damage in a single match",
        "flavor_text": "Your enemies felt that one.",
        "category": AchievementCategory.COMBAT,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "⚔️",
        "requirement_type": "match_damage",
        "requirement_threshold": 50000,
        "points": 20,
    },
    {
        "code": "NUKE_LAUNCHER",
        "name": "Nuke Launcher",
        "description": "Deal 100,000+ damage in a single match",
        "flavor_text": "Nuclear launch detected! Oh wait, that's just your army.",
        "category": AchievementCategory.COMBAT,
        "rarity": AchievementRarity.RARE,
        "icon": "☢️",
        "requirement_type": "match_damage",
        "requirement_threshold": 100000,
        "points": 50,
    },
    {
        "code": "WALKING_APOCALYPSE",
        "name": "Walking Apocalypse",
        "description": "Deal 200,000+ damage in a single match",
        "flavor_text": "SOMEBODY STOP THIS PERSON! They're a walking war crime!",
        "category": AchievementCategory.ESPORTS,
        "rarity": AchievementRarity.EPIC,
        "icon": "💀",
        "requirement_type": "match_damage",
        "requirement_threshold": 200000,
        "points": 100,
    },
    {
        "code": "UNIT_SLAYER_500",
        "name": "Unit Slayer",
        "description": "Kill 500+ units in a single match",
        "flavor_text": "Their army? Deleted.",
        "category": AchievementCategory.COMBAT,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "🗡️",
        "requirement_type": "match_kills",
        "requirement_threshold": 500,
        "points": 20,
    },
    {
        "code": "MASS_MURDERER",
        "name": "Mass Extinction Event",
        "description": "Kill 1,000+ units in a single match",
        "flavor_text": "You didn't just win. You erased them from existence.",
        "category": AchievementCategory.COMBAT,
        "rarity": AchievementRarity.RARE,
        "icon": "💣",
        "requirement_type": "match_kills",
        "requirement_threshold": 1000,
        "points": 50,
    },
    # =======================================================================
    # TEAMWORK ACHIEVEMENTS
    # =======================================================================
    {
        "code": "DYNAMIC_DUO",
        "name": "Dynamic Duo",
        "description": "Win 10+ games with the same partner",
        "flavor_text": "You two should start a band or something.",
        "category": AchievementCategory.TEAMWORK,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "🤝",
        "requirement_type": "duo_wins",
        "requirement_threshold": 10,
        "points": 25,
    },
    {
        "code": "POWER_COUPLE",
        "name": "Power Couple",
        "description": "Win 25+ games with the same partner",
        "flavor_text": "When's the wedding?",
        "category": AchievementCategory.TEAMWORK,
        "rarity": AchievementRarity.RARE,
        "icon": "💑",
        "requirement_type": "duo_wins",
        "requirement_threshold": 25,
        "points": 50,
    },
    {
        "code": "SOULMATES",
        "name": "Soulmates",
        "description": "Win 40+ games with the same partner",
        "flavor_text": "This is true love. Romeo & Juliet have nothing on you.",
        "category": AchievementCategory.SPECIAL,
        "rarity": AchievementRarity.EPIC,
        "icon": "💕",
        "requirement_type": "duo_wins",
        "requirement_threshold": 40,
        "points": 100,
    },
    {
        "code": "HIGH_SYNERGY",
        "name": "Perfect Chemistry",
        "description": "Achieve 70%+ win rate with a partner (10+ games)",
        "flavor_text": "The chemistry is off the charts!",
        "category": AchievementCategory.TEAMWORK,
        "rarity": AchievementRarity.RARE,
        "icon": "⚗️",
        "requirement_type": "duo_winrate",
        "requirement_threshold": 70,
        "points": 50,
    },
    # =======================================================================
    # VARIETY ACHIEVEMENTS
    # =======================================================================
    {
        "code": "RACE_MASTER_T",
        "name": "Terran Commander",
        "description": "Play 50+ games as Terran",
        "flavor_text": "The boys in blue march to victory.",
        "category": AchievementCategory.VARIETY,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "🔵",
        "color": "blue",
        "requirement_type": "race_games",
        "requirement_threshold": 50,
        "requirement_extra": '{"race": "Terran"}',
        "points": 25,
    },
    {
        "code": "RACE_MASTER_P",
        "name": "Protoss Zealot",
        "description": "Play 50+ games as Protoss",
        "flavor_text": "My life for Aiur!",
        "category": AchievementCategory.VARIETY,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "🟡",
        "color": "gold",
        "requirement_type": "race_games",
        "requirement_threshold": 50,
        "requirement_extra": '{"race": "Protoss"}',
        "points": 25,
    },
    {
        "code": "RACE_MASTER_Z",
        "name": "Swarm Lord",
        "description": "Play 50+ games as Zerg",
        "flavor_text": "The swarm grows stronger.",
        "category": AchievementCategory.VARIETY,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "🟣",
        "color": "purple",
        "requirement_type": "race_games",
        "requirement_threshold": 50,
        "requirement_extra": '{"race": "Zerg"}',
        "points": 25,
    },
    {
        "code": "ONE_TRICK_PONY",
        "name": "One Trick Pony",
        "description": "Play 100+ games with only one race",
        "flavor_text": "Why fix what isn't broken?",
        "category": AchievementCategory.VARIETY,
        "rarity": AchievementRarity.RARE,
        "icon": "🐴",
        "requirement_type": "single_race_games",
        "requirement_threshold": 100,
        "points": 40,
    },
    # =======================================================================
    # MMR ACHIEVEMENTS
    # =======================================================================
    {
        "code": "MMR_2500",
        "name": "Rising Star",
        "description": "Reach 2500 MMR",
        "flavor_text": "You're starting to turn heads.",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "⬆️",
        "requirement_type": "mmr_reached",
        "requirement_threshold": 2500,
        "points": 25,
    },
    {
        "code": "MMR_3000",
        "name": "Elite Status",
        "description": "Reach 3000 MMR",
        "flavor_text": "Welcome to the big leagues.",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.RARE,
        "icon": "🌟",
        "requirement_type": "mmr_reached",
        "requirement_threshold": 3000,
        "points": 50,
    },
    {
        "code": "MMR_3500",
        "name": "Legendary",
        "description": "Reach 3500 MMR",
        "flavor_text": "You are among the gods now.",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.LEGENDARY,
        "icon": "👑",
        "requirement_type": "mmr_reached",
        "requirement_threshold": 3500,
        "points": 150,
    },
    # =======================================================================
    # MEME ACHIEVEMENTS
    # =======================================================================
    {
        "code": "GLASS_CANNON",
        "name": "Glass Cannon",
        "description": "Deal top damage but also take most damage on team",
        "flavor_text": "You deal it, you take it. Fair's fair.",
        "category": AchievementCategory.MEME,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "🔮",
        "requirement_type": "glass_cannon",
        "requirement_threshold": 1,
        "points": 20,
    },
    {
        "code": "DEDICATED_WARRIOR",
        "name": "Dedicated Warrior",
        "description": "Play games on 7 different days",
        "flavor_text": "Consistency is key.",
        "category": AchievementCategory.MILESTONE,
        "rarity": AchievementRarity.UNCOMMON,
        "icon": "📆",
        "requirement_type": "unique_days",
        "requirement_threshold": 7,
        "points": 20,
    },
]
