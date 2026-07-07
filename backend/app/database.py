"""
Database connection and session management.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import os

from .models import Base

# Database configuration. The historical default is a module-anchored path
# (immune to cwd mistakes); an explicit DATABASE_URL env var overrides it for
# deployments (e.g. Cloud Run, where the Litestream-restored DB lives at a
# container path). Note this deliberately reads os.environ, not
# settings.database_url - the settings field's relative-path default would
# reintroduce the cwd trap for everyone who doesn't set the env var.
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATABASE_PATH = os.path.join(DATABASE_DIR, "sc2mmr.db")
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{DATABASE_PATH}"

# Create database directory if it doesn't exist
os.makedirs(DATABASE_DIR, exist_ok=True)

# Create engine
_is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    echo=False,  # Set to True for SQL query logging
)


# Enable foreign key constraints for SQLite
if _is_sqlite:

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    This should be called once when the application starts.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database sessions.

    Usage in FastAPI endpoints:
        @app.get("/players")
        def get_players(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions outside of FastAPI.

    Usage:
        with get_db_context() as db:
            players = db.query(Player).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db() -> None:
    """
    Drop all tables and recreate them.
    WARNING: This will delete all data!
    Only use for testing or development.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
