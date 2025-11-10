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
