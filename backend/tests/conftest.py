"""
Pytest configuration and fixtures for SC2 MMR Tracker tests.
"""
import pytest
import os
import tempfile
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

_test_directory = tempfile.TemporaryDirectory(prefix="sc2mmr-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_directory.name}/api.db"
os.environ["AUTH_ENABLED"] = "false"
os.environ["AUTH_PUBLIC_READ"] = "false"
os.environ["ADMIN_TOKEN"] = ""

from app.models import Base, Player


@pytest.fixture(scope="session", autouse=True)
def isolated_application_database():
    from app.database import engine, init_db

    init_db()
    yield
    engine.dispose()
    _test_directory.cleanup()


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database engine."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


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
