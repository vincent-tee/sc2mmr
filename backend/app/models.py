"""
Database models for SC2 MMR tracking system.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class Player(Base):
    """
    Represents a player in the system.

    TrueSkill rating consists of:
    - mu: skill estimate (default 25.0)
    - sigma: uncertainty (default 8.333, decreases with more games)
    """
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)

    # TrueSkill rating
    mu = Column(Float, default=25.0, nullable=False)
    sigma = Column(Float, default=8.333, nullable=False)

    # Recency-weighted MMR (weights recent matches more heavily)
    recency_weighted_mmr = Column(Float, nullable=True)

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

    # Relationships
    match_participations = relationship("MatchPlayer", back_populates="player")

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_games == 0:
            return 0.0
        return (self.wins / self.total_games) * 100

    @property
    def mmr(self) -> float:
        """
        Conservative skill estimate for balancing.
        mu - 3*sigma gives ~99.7% confidence lower bound.
        """
        return self.mu - (3 * self.sigma)

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
    TWO_V_TWO = "2v2"
    THREE_V_THREE = "3v3"
    FOUR_V_FOUR = "4v4"
    FIVE_V_FIVE = "5v5"


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
        """Calculate the MMR change from this match."""
        mmr_before = self.mu_before - (3 * self.sigma_before)
        mmr_after = self.mu_after - (3 * self.sigma_after)
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
