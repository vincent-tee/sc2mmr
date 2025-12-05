"""
Pytest configuration and fixtures for SC2 MMR Tracker tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models import Base, Player


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def player_factory(db_session: Session):
    """
    Factory fixture to create Player objects with database defaults applied.

    Usage:
        player = player_factory(name="TestPlayer")
        player = player_factory(name="Custom", mu=30.0, sigma=5.0)
    """
    def _create_player(**kwargs):
        # Ensure name is provided
        if 'name' not in kwargs:
            kwargs['name'] = "TestPlayer"

        player = Player(**kwargs)
        db_session.add(player)
        db_session.flush()  # This applies SQLAlchemy defaults
        return player

    return _create_player
