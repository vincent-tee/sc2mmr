"""
SC2 MMR Tracker - Main FastAPI Application

A web application to track StarCraft 2 replays for a casual gaming group,
maintain player ratings using TrueSkill, and balance teams for fair matches.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import init_db
from .api import replays, players, teams, impact, adaptive


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
    title="SC2 MMR Tracker",
    description="""
    Track StarCraft 2 replays, maintain player ratings, and balance teams for fair matches.

    ## Features

    * **Replay Upload** - Parse and process SC2 replay files
    * **Player Tracking** - TrueSkill MMR ratings, win rates, and statistics
    * **Team Balancing** - Generate balanced team compositions for fair matches
    * **Player Rankings** - View player rankings and detailed statistics

    ## Main Workflows

    1. **Upload Replays**: POST `/replays/upload` with .SC2Replay file
    2. **View Players**: GET `/players/` to see all players
    3. **Balance Teams**: POST `/teams/balance` with player IDs to get team suggestions
    4. **View Rankings**: GET `/players/rankings` to see player leaderboard
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
