"""
Database models for SC2 MMR tracking system.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class Player(Base):
    """
    Represents a player in the system.

    TrueSkill rating consists of:
    - mu: skill estimate (default 25.0)
    - sigma: uncertainty (default 8.333, decreases with more games)

    Hybrid MMR System:
    - mmr: Display MMR based on TrueSkill (1000 + 40*mu)
    - hybrid_mmr: Performance-adjusted MMR that accounts for in-game metrics
    - avg_pim: Average Performance Impact Modifier across all games
    """
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)

    # TrueSkill rating
    mu = Column(Float, default=25.0, nullable=False)
    sigma = Column(Float, default=8.333, nullable=False)

    # Recency-weighted MMR (weights recent matches more heavily)
    recency_weighted_mmr = Column(Float, nullable=True)

    # Hybrid MMR System (SPEC-ML-001)
    # Performance-adjusted MMR that combines TrueSkill with in-game metrics
    hybrid_mmr = Column(Float, default=2000.0, nullable=True)  # Defaults to starting display MMR
    avg_pim = Column(Float, default=0.0, nullable=True)  # Average Performance Impact Modifier

    # Statistics
    total_games = Column(Integer, default=0, nullable=False)
    wins = Column(Integer, default=0, nullable=False)
    losses = Column(Integer, default=0, nullable=False)

    # Race statistics
    terran_games = Column(Integer, default=0, nullable=False)
    protoss_games = Column(Integer, default=0, nullable=False)
    zerg_games = Column(Integer, default=0, nullable=False)
    random_games = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_played = Column(DateTime, nullable=True)
    is_core_player = Column(Integer, default=1, nullable=False)  # 1 for core, 0 for outsider

    # Average impact scores (calculated from all matches)
    avg_economic_score = Column(Float, default=0.0)
    avg_combat_score = Column(Float, default=0.0)
    avg_efficiency_score = Column(Float, default=0.0)
    avg_overall_impact = Column(Float, default=0.0)

    # Timing profile (averaged across all games)
    avg_first_damage_timing = Column(Integer, nullable=True)
    primary_archetype = Column(String, nullable=True)  # Most common archetype
    avg_aggression_score = Column(Float, default=50.0)

    # Recency-weighted impact scores (60-day half-life decay)
    # These weight recent performance more heavily than older games
    recency_weighted_combat = Column(Float, nullable=True)
    recency_weighted_economic = Column(Float, nullable=True)
    recency_weighted_efficiency = Column(Float, nullable=True)
    recency_weighted_overall_impact = Column(Float, nullable=True)

    # Relationships
    match_participations = relationship("MatchPlayer", back_populates="player")

    @property
    def win_rate(self) -> float:
        """Calculate win rate as decimal (0.0 to 1.0)."""
        if self.total_games == 0:
            return 0.0
        return self.wins / self.total_games

    @property
    def mmr(self) -> float:
        """
        Scaled MMR for display and balancing.

        Uses the centralized display MMR formula from RatingSystem:
        MMR = 1000 + 40*mu

        Sigma (uncertainty) is kept internal for matchmaking quality but doesn't
        affect displayed rating. This prevents inactive players from having their
        displayed MMR penalized when only their uncertainty increases.

        This gives approximately:
        - New players: ~2000 MMR (mu=25)
        - Experienced players: 800-2400 MMR range
        - Higher MMR = better skill

        See RatingSystem.calculate_display_mmr() for the authoritative implementation.
        """
        # Import here to avoid circular imports
        from .rating_system import RatingSystem
        return RatingSystem.calculate_display_mmr(self.mu)

    @property
    def favorite_race(self) -> str:
        """Determine player's most played race."""
        races = {
            'Terran': self.terran_games,
            'Protoss': self.protoss_games,
            'Zerg': self.zerg_games,
            'Random': self.random_games
        }
        if max(races.values()) == 0:
            return 'Unknown'
        return max(races, key=races.get)


class GameMode(str, enum.Enum):
    """Enum for different game modes."""
    # Even team modes
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

    id = Column(Integer, primary_key=True, index=True)

    # Game details
    played_at = Column(DateTime, nullable=False, index=True)
    game_mode = Column(SQLEnum(GameMode), nullable=False)
    map_name = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=False)

    # Replay information
    replay_file_path = Column(String, nullable=True)
    replay_hash = Column(String, unique=True, nullable=True, index=True)  # To prevent duplicate uploads

    # Win probability predictions (calculated before match from TrueSkill ratings)
    predicted_team1_win_prob = Column(Float, nullable=True)  # 0.0 to 1.0
    predicted_team2_win_prob = Column(Float, nullable=True)  # 0.0 to 1.0
    # Note: team1 + team2 should equal 1.0 (complementary probabilities)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    participants = relationship("MatchPlayer", back_populates="match")


class MatchPlayer(Base):
    """
    Links players to matches with their performance details.
    This is a many-to-many relationship table with additional attributes.
    """
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)

    # Match details
    team_number = Column(Integer, nullable=False)  # 1 or 2
    race = Column(SQLEnum(Race), nullable=False)
    won = Column(Integer, nullable=False)  # 1 for win, 0 for loss

    # Rating snapshot (before and after this match)
    mu_before = Column(Float, nullable=False)
    sigma_before = Column(Float, nullable=False)
    mu_after = Column(Float, nullable=False)
    sigma_after = Column(Float, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="participants")
    player = relationship("Player", back_populates="match_participations")

    @property
    def mmr_change(self) -> float:
        """
        Calculate the MMR change from this match.

        Uses the display MMR formula (1000 + 40*mu) to match what users see
        in Player.mmr. This ensures consistency between displayed ratings
        and match history.

        Note: Uses display MMR (not conservative) because users expect the
        change to match the difference they see in their profile.
        """
        from .rating_system import RatingSystem
        mmr_before = RatingSystem.calculate_display_mmr(self.mu_before)
        mmr_after = RatingSystem.calculate_display_mmr(self.mu_after)
        return mmr_after - mmr_before


class PlayerMatchMetrics(Base):
    """
    Detailed performance metrics for a player in a specific match.
    Extends MatchPlayer with advanced statistics.
    """
    __tablename__ = "player_match_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to MatchPlayer
    match_player_id = Column(Integer, ForeignKey("match_players.id"), nullable=False, unique=True, index=True)

    # Economic metrics
    minerals_collected = Column(Integer, default=0)
    vespene_collected = Column(Integer, default=0)
    total_resources_collected = Column(Integer, default=0)
    resources_spent = Column(Integer, default=0)
    spending_efficiency = Column(Float, default=0.0)
    workers_created = Column(Integer, default=0)

    # Army metrics
    units_trained = Column(Integer, default=0)
    units_lost = Column(Integer, default=0)
    units_killed = Column(Integer, default=0)
    army_value_built = Column(Integer, default=0)
    army_value_killed = Column(Integer, default=0)
    army_value_lost = Column(Integer, default=0)

    # Combat metrics
    damage_dealt = Column(Integer, default=0)
    damage_taken = Column(Integer, default=0)
    damage_ratio = Column(Float, default=0.0)

    # Timing metrics (game seconds)
    first_expansion_timing = Column(Integer, nullable=True)
    bases_created = Column(Integer, default=0)

    # Mechanics
    apm = Column(Float, default=0.0)

    # Unit composition (stored as JSON string)
    unit_composition = Column(String, nullable=True)  # JSON: {"Marine": 50, "Marauder": 20}

    # Impact scores
    economic_score = Column(Float, default=0.0)
    combat_score = Column(Float, default=0.0)
    efficiency_score = Column(Float, default=0.0)
    overall_impact = Column(Float, default=0.0)

    # Team game metrics
    team_fight_participation = Column(Float, default=0.0)  # % of team fights participated in (0-1)
    team_fight_damage = Column(Integer, default=0)  # Damage dealt in multi-player engagements
    team_fight_damage_ratio = Column(Float, default=0.0)  # Team fight damage / total damage

    # Timing analysis
    first_damage_timing = Column(Integer, nullable=True)  # Game seconds
    early_game_damage = Column(Integer, default=0)  # 0-5min
    mid_game_damage = Column(Integer, default=0)    # 5-10min
    late_game_damage = Column(Integer, default=0)   # 10+min
    player_archetype = Column(String, nullable=True)  # Rusher, TimingAttacker, LateGame, etc.
    aggression_score = Column(Float, default=50.0)  # 0-100

    # Second-by-second damage timeline (sparse storage)
    damage_timeline = Column(String, nullable=True)  # JSON: {187: 250, 325: 1200, ...}
    # Only stores seconds where damage occurred - typically 20-100 events per game
    # Key = game second, Value = damage dealt that second


class PlayerSynergy(Base):
    """
    Tracks synergy between pairs of players.
    """
    __tablename__ = "player_synergies"

    id = Column(Integer, primary_key=True, index=True)

    # Player pair (always store with player1_id < player2_id for consistency)
    player1_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    player2_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)

    # Synergy metrics
    games_together = Column(Integer, default=0)
    wins_together = Column(Integer, default=0)
    losses_together = Column(Integer, default=0)

    # Synergy score (0-100)
    synergy_score = Column(Float, default=50.0)

    # Average performance together
    avg_combined_impact = Column(Float, default=0.0)
    avg_win_rate = Column(Float, default=0.0)

    # Last updated
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def win_rate_together(self) -> float:
        """Calculate win rate when playing together."""
        if self.games_together == 0:
            return 0.0
        return (self.wins_together / self.games_together) * 100


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

    id = Column(Integer, primary_key=True, index=True)

    # File information
    filename = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    replay_hash = Column(String, nullable=True, index=True)
    replay_file_path = Column(String, nullable=True)  # Saved file path for manual review

    # Error details
    error_type = Column(SQLEnum(UploadErrorType), nullable=False, index=True)
    error_message = Column(String, nullable=False)
    error_detail = Column(String, nullable=True)  # Full stack trace or additional context

    # Match metadata (if partially parsed)
    map_name = Column(String, nullable=True)
    game_mode = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    num_players = Column(Integer, nullable=True)

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Review status
    reviewed = Column(Integer, default=0, nullable=False)  # 0 = not reviewed, 1 = reviewed
    review_notes = Column(String, nullable=True)


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

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to MatchPlayer
    match_player_id = Column(Integer, ForeignKey("match_players.id"), nullable=False, unique=True, index=True)

    # =========================================================================
    # Z-score normalized features (relative to match average)
    # Positive = above average, Negative = below average
    # =========================================================================

    # Combat metrics (40% weight in rule-based formula)
    damage_ratio_z = Column(Float, default=0.0)
    army_value_ratio_z = Column(Float, default=0.0)
    combat_score_z = Column(Float, default=0.0)

    # Economic metrics (25% weight)
    spending_efficiency_z = Column(Float, default=0.0)
    economic_score_z = Column(Float, default=0.0)
    resource_advantage_z = Column(Float, default=0.0)

    # Team contribution metrics (25% weight)
    team_fight_participation_z = Column(Float, default=0.0)
    team_fight_damage_ratio_z = Column(Float, default=0.0)
    overall_impact_z = Column(Float, default=0.0)

    # Efficiency metrics (10% weight)
    efficiency_score_z = Column(Float, default=0.0)

    # =========================================================================
    # Calculated Performance Impact Modifier
    # =========================================================================

    # PIM value (range: -0.5 to +0.5)
    pim = Column(Float, default=0.0)

    # PIM breakdown by category (for transparency/debugging)
    pim_combat = Column(Float, default=0.0)
    pim_economic = Column(Float, default=0.0)
    pim_team = Column(Float, default=0.0)
    pim_efficiency = Column(Float, default=0.0)

    # Version of PIM calculation algorithm used
    pim_version = Column(String(20), default="rule_v1")

    # =========================================================================
    # MMR Change Tracking
    # =========================================================================

    # Raw TrueSkill MMR change (without PIM adjustment)
    raw_mmr_change = Column(Float, nullable=True)

    # Hybrid MMR change (with PIM applied)
    hybrid_mmr_change = Column(Float, nullable=True)

    # =========================================================================
    # Enhanced ML Features (Phase 2A - SPEC-ML-001)
    # =========================================================================

    # Build Order Features
    build_order_json = Column(JSON, nullable=True)  # Full build sequence
    build_order_hash = Column(String(16), nullable=True, index=True)  # For clustering
    detected_build_type = Column(String(50), nullable=True)  # "rush", "macro", "timing", "cheese"

    # Upgrade Features
    upgrades_json = Column(JSON, nullable=True)  # [{second, name, category}]
    first_attack_upgrade_second = Column(Integer, nullable=True)
    first_armor_upgrade_second = Column(Integer, nullable=True)
    upgrade_timing_score = Column(Float, default=0.0)  # Z-score vs average

    # Ability/Micro Features
    abilities_json = Column(JSON, nullable=True)  # {"Stim": 15, "EMP": 3}
    total_abilities = Column(Integer, default=0)
    abilities_per_minute = Column(Float, default=0.0)

    # Macro Features
    supply_block_seconds = Column(Integer, default=0)
    early_worker_losses = Column(Integer, default=0)
    harassment_response_score = Column(Float, default=0.0)  # 0-100

    # ML Model Outputs (Phase 2B+)
    ml_macro_score = Column(Float, nullable=True)  # 0-100
    ml_micro_score = Column(Float, nullable=True)  # 0-100
    ml_predicted_pim = Column(Float, nullable=True)  # ML model prediction

    # =========================================================================
    # Metadata
    # =========================================================================

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    match_player = relationship("MatchPlayer", backref="performance_features")


# ============================================================================
# Achievement System Models (Phase 2)
# ============================================================================

class AchievementCategory(str, enum.Enum):
    """Categories for organizing achievements."""
    MILESTONE = "milestone"      # Games played, wins, etc.
    STREAK = "streak"            # Win/loss streaks
    COMBAT = "combat"            # Damage, kills, etc.
    ECONOMIC = "economic"        # Resources, efficiency
    TEAMWORK = "teamwork"        # Synergy, team contribution
    VARIETY = "variety"          # Race diversity, map variety
    SPECIAL = "special"          # Unique/rare achievements
    MEME = "meme"                # Funny/inside joke achievements
    ESPORTS = "esports"          # Commentary-style epic achievements


class AchievementRarity(str, enum.Enum):
    """Rarity tiers for achievements."""
    COMMON = "common"            # Easy to get (50%+ players)
    UNCOMMON = "uncommon"        # Moderate difficulty (25-50%)
    RARE = "rare"                # Challenging (10-25%)
    EPIC = "epic"                # Very difficult (5-10%)
    LEGENDARY = "legendary"      # Elite status (< 5%)
    MYTHIC = "mythic"            # One-of-a-kind or near impossible


class Achievement(Base):
    """
    Defines an achievement/badge that players can earn.
    """
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    flavor_text = Column(String(300), nullable=True)

    # Classification
    category = Column(SQLEnum(AchievementCategory), nullable=False, index=True)
    rarity = Column(SQLEnum(AchievementRarity), nullable=False, index=True)

    # Visual
    icon = Column(String(100), nullable=True)
    color = Column(String(20), nullable=True)

    # Requirements
    requirement_type = Column(String(50), nullable=False)
    requirement_threshold = Column(Float, nullable=False)
    requirement_extra = Column(String(200), nullable=True)

    # Metadata
    points = Column(Integer, default=10)
    is_hidden = Column(Integer, default=0)
    is_active = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    player_achievements = relationship("PlayerAchievement", back_populates="achievement")


class PlayerAchievement(Base):
    """
    Links players to their earned achievements.
    """
    __tablename__ = "player_achievements"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False, index=True)

    # When earned
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Context (what triggered it)
    trigger_match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    trigger_value = Column(Float, nullable=True)

    # Display
    is_featured = Column(Integer, default=0)

    # Relationships
    player = relationship("Player", backref="player_achievements")
    achievement = relationship("Achievement", back_populates="player_achievements")


class PlayerRivalry(Base):
    """
    Tracks head-to-head rivalry between two players.
    """
    __tablename__ = "player_rivalries"

    id = Column(Integer, primary_key=True, index=True)

    # Player pair (always store with player1_id < player2_id for consistency)
    player1_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    player2_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)

    # Games against each other (on opposite teams)
    games_against = Column(Integer, default=0)
    player1_wins = Column(Integer, default=0)
    player2_wins = Column(Integer, default=0)

    # Intensity metrics
    avg_mmr_swing = Column(Float, default=0.0)
    biggest_upset_mmr = Column(Float, default=0.0)

    # Last meeting
    last_match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    last_match_at = Column(DateTime, nullable=True)

    # Rivalry score (calculated)
    rivalry_score = Column(Float, default=0.0)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    player1 = relationship("Player", foreign_keys=[player1_id], backref="rivalries_as_player1")
    player2 = relationship("Player", foreign_keys=[player2_id], backref="rivalries_as_player2")


# ============================================================================
# Achievement Definitions - The Fun Part!
# ============================================================================

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
