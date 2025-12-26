from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, text

from ..database import get_db
from ..models import Player, PlayerRivalry, Match
from ..services.rivalry_service import RivalryService
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/h2h",
    tags=["head-to-head"],
    responses={404: {"description": "Not found"}},
)

# ---------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------


class PlayerSummary(BaseModel):
    id: int
    name: str
    mmr: float
    wins: int
    favorite_race: str


class HeadToHeadStats(BaseModel):
    total_games: int
    player1_wins: int
    player2_wins: int
    win_rate_player1: float
    last_match_date: Optional[datetime]
    avg_mmr_swing: float
    rivalry_score: float
    rivalry_intensity: str


class MatchSummary(BaseModel):
    match_id: int
    date: datetime
    winner_id: int
    map_name: str
    duration_seconds: int


class HeadToHeadResponse(BaseModel):
    player1: PlayerSummary
    player2: PlayerSummary
    head_to_head: HeadToHeadStats
    recent_matches: List[MatchSummary]


class RivalryResponse(BaseModel):
    player1_id: int
    player1_name: str
    player2_id: int
    player2_name: str
    games: int
    score: float
    intensity: str


# ---------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------


def get_intensity_label(score: float) -> str:
    if score >= 80:
        return "Epic"
    if score >= 60:
        return "Fierce"
    if score >= 40:
        return "Competitive"
    return "Casual"


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------


@router.post("/calculate-all")
def calculate_all_rivalries(db: Session = Depends(get_db)):
    """
    Force recalculation of all player rivalries.
    """
    count = RivalryService.calculate_all_rivalries(db)
    return {"message": f"Updated {count} rivalry records"}


@router.get("/biggest-rivalries", response_model=List[RivalryResponse])
def get_biggest_rivalries(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get the most intense rivalries across the entire server.
    """
    rivalries = (
        db.query(PlayerRivalry)
        .order_by(desc(PlayerRivalry.rivalry_score))
        .limit(limit)
        .all()
    )

    results = []
    for r in rivalries:
        results.append(
            RivalryResponse(
                player1_id=r.player1_id,
                player1_name=r.player1.name,
                player2_id=r.player2_id,
                player2_name=r.player2.name,
                games=r.games_against,
                score=r.rivalry_score,
                intensity=get_intensity_label(r.rivalry_score),
            )
        )
    return results


@router.get("/{player_id}/rivals", response_model=List[RivalryResponse])
def get_player_rivals(player_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """
    Get top rivals for a specific player.
    """
    # Find rivalries where this player is either p1 or p2
    rivalries = (
        db.query(PlayerRivalry)
        .filter(
            or_(
                PlayerRivalry.player1_id == player_id,
                PlayerRivalry.player2_id == player_id,
            )
        )
        .order_by(desc(PlayerRivalry.rivalry_score))
        .limit(limit)
        .all()
    )

    results = []
    for r in rivalries:
        results.append(
            RivalryResponse(
                player1_id=r.player1_id,
                player1_name=r.player1.name,
                player2_id=r.player2_id,
                player2_name=r.player2.name,
                games=r.games_against,
                score=r.rivalry_score,
                intensity=get_intensity_label(r.rivalry_score),
            )
        )
    return results


@router.get("/{player1_id}/{player2_id}", response_model=HeadToHeadResponse)
def get_head_to_head(player1_id: int, player2_id: int, db: Session = Depends(get_db)):
    """
    Get detailed breakdown of two players against each other.
    """
    # Ensure ordered look up
    p1_id, p2_id = min(player1_id, player2_id), max(player1_id, player2_id)

    # 1. Fetch Players
    p1 = db.query(Player).filter(Player.id == p1_id).first()
    p2 = db.query(Player).filter(Player.id == p2_id).first()

    if not p1 or not p2:
        raise HTTPException(status_code=404, detail="One or both players not found")

    # 2. Fetch or Calculate Rivalry Stats
    rivalry = (
        db.query(PlayerRivalry)
        .filter(
            and_(PlayerRivalry.player1_id == p1_id, PlayerRivalry.player2_id == p2_id)
        )
        .first()
    )

    # Defaults if no games played yet
    stats = HeadToHeadStats(
        total_games=0,
        player1_wins=0,
        player2_wins=0,
        win_rate_player1=0.0,
        last_match_date=None,
        avg_mmr_swing=0.0,
        rivalry_score=0.0,
        rivalry_intensity="Casual",
    )

    if rivalry:
        # Map DB p1/p2 wins to requested p1/p2 wins
        # Since we ordered IDs at start, p1_id corresponds to rivalry.player1_id
        # and p2_id corresponds to rivalry.player2_id

        # However, the user might have requested /h2h/B/A (where B > A)
        # In that case, p1_id=A, p2_id=B.
        # But we need to return "player1" as the first one in URL?
        # The spec says:
        # GET /h2h/{player1_id}/{player2_id}
        # Response: player1: { ... }, player2: { ... }
        # Ideally response matches the requested order.

        # Let's map back to requested order.
        is_swapped = player1_id > player2_id

        # Database values are for (min_id, max_id)
        db_p1_wins = rivalry.player1_wins
        db_p2_wins = rivalry.player2_wins

        req_p1_wins = db_p2_wins if is_swapped else db_p1_wins
        req_p2_wins = db_p1_wins if is_swapped else db_p2_wins

        stats = HeadToHeadStats(
            total_games=rivalry.games_against,
            player1_wins=req_p1_wins,
            player2_wins=req_p2_wins,
            win_rate_player1=req_p1_wins / rivalry.games_against
            if rivalry.games_against > 0
            else 0.0,
            last_match_date=rivalry.last_match_at,
            avg_mmr_swing=rivalry.avg_mmr_swing,
            rivalry_score=rivalry.rivalry_score,
            rivalry_intensity=get_intensity_label(rivalry.rivalry_score),
        )

    # 3. Get Recent Matches
    # Query matches where both participated on opposite teams
    # This is complex in SQL. Easier to filter python side if not too many?
    # Or rely on MatchPlayers.

    # Actually, we can use the Rivalry object if we stored last matches, but we only store Last Match ID.
    # So we need to query matches.
    # JOIN MatchPlayer mp1, MatchPlayer mp2 on map1.match_id = mp2.match_id
    # WHERE mp1.player_id = X AND mp2.player_id = Y
    # AND mp1.team != mp2.team

    # OR reuse logic from SERVICE? But service was bulk.
    # Let's do a direct query.

    query = text("""
    SELECT m.id, m.played_at, m.map_name, m.duration_seconds,
           mp1.won as p1_won, mp2.won as p2_won
    FROM matches m
    JOIN match_players mp1 ON m.id = mp1.match_id
    JOIN match_players mp2 ON m.id = mp2.match_id
    WHERE mp1.player_id = :p1_id 
      AND mp2.player_id = :p2_id
      AND mp1.team_number != mp2.team_number
    ORDER BY m.played_at DESC
    LIMIT 5
    """)
    # Using raw SQL for performance/simplicity on self-join
    result = db.execute(query, {"p1_id": player1_id, "p2_id": player2_id}).fetchall()

    recent_matches = []
    for row in result:
        winner_id = player1_id if row.p1_won else player2_id
        recent_matches.append(
            MatchSummary(
                match_id=row.id,
                date=row.played_at,
                winner_id=winner_id,
                map_name=row.map_name,
                duration_seconds=row.duration_seconds,
            )
        )

    # Construct response in requested order
    req_p1 = p2 if player1_id == p2_id else p1
    req_p2 = p1 if player1_id == p2_id else p2

    return HeadToHeadResponse(
        player1=PlayerSummary(
            id=req_p1.id,
            name=req_p1.name,
            mmr=req_p1.mmr,
            wins=req_p1.wins,
            favorite_race=req_p1.favorite_race,
        ),
        player2=PlayerSummary(
            id=req_p2.id,
            name=req_p2.name,
            mmr=req_p2.mmr,
            wins=req_p2.wins,
            favorite_race=req_p2.favorite_race,
        ),
        head_to_head=stats,
        recent_matches=recent_matches,
    )
