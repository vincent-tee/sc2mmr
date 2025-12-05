"""
SC2 MMR Tracker - Main FastAPI Application

A web application to track StarCraft 2 replays for a casual gaming group,
maintain player ratings using TrueSkill, and balance teams for fair matches.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .database import init_db
from .api import replays, players, teams, impact, adaptive
from .config import settings

# Configure logging using settings
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup and shutdown events.
    """
    # Startup: Initialize database
    init_db()
    print("Database initialized successfully")
    yield
    # Shutdown: Clean up resources (if needed)
    print("Application shutting down")


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan
)

# CORS middleware for frontend
# Uses settings.cors_origins instead of wildcard ["*"] for security
# In development: ["http://localhost:5173", "http://localhost:3000"]
# In production: Set CORS_ORIGINS env var to your domain(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(replays.router)
app.include_router(players.router)
app.include_router(teams.router)
app.include_router(impact.router)
app.include_router(adaptive.router)


@app.get("/")
def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "SC2 MMR Tracker",
        "version": "2.0.0",
        "description": "Track SC2 replays with advanced metrics, player impact, and team balancing",
        "endpoints": {
            "docs": "/docs",
            "replays": "/replays",
            "players": "/players",
            "teams": "/teams",
            "impact": "/impact"
        },
        "features": {
            "basic": [
                "Replay upload and processing",
                "TrueSkill MMR ratings",
                "Player statistics",
                "Team balancing"
            ],
            "advanced": [
                "Economic & combat metrics",
                "Damage dealt/taken tracking",
                "Army composition analysis",
                "Player impact scores",
                "Synergy detection",
                "Role-based rankings"
            ]
        }
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy"}


@app.get("/version")
def version_check():
    """
    Version check endpoint - verify backend is running latest code.
    """
    # Check if WinnerDeterminationError is available
    has_winner_determination_error = False
    try:
        from .replay_parser import WinnerDeterminationError
        has_winner_determination_error = True
    except ImportError:
        pass

    # Check if uneven team support exists
    has_uneven_team_support = False
    try:
        from .models import GameMode
        has_uneven_team_support = hasattr(GameMode, 'FOUR_V_THREE')
    except:
        pass

    return {
        "version": "2.1.0",
        "features": {
            "winner_determination_error_handling": has_winner_determination_error,
            "uneven_team_support": has_uneven_team_support
        },
        "status": "up-to-date" if (has_winner_determination_error and has_uneven_team_support) else "outdated"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
