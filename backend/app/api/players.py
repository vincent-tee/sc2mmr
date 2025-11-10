"""
API endpoints for player statistics and management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import Player, MatchPlayer, Match
from ..rating_system import RatingSystem
from pydantic import BaseModel


router = APIRouter(prefix="/players", tags=["players"])


# Request/Response models
class PlayerResponse(BaseModel):
    """Response model for player data."""
    id: int
    name: str
    mu: float
    sigma: float
    mmr: float
    total_games: int
    wins: int
    losses: int
    win_rate: float
    favorite_race: str
    is_core_player: bool
    last_played: Optional[datetime]

    class Config:
        from_attributes = True


class PlayerDetailResponse(BaseModel):
    """Detailed player response with race statistics."""
    id: int
    name: str
    mu: float
    sigma: float
    mmr: float
    total_games: int
    wins: int
    losses: int
    win_rate: float
    is_core_player: bool
    last_played: Optional[datetime]
    race_stats: dict
    recent_matches: List[dict]

    class Config:
        from_attributes = True


class PlayerRankingResponse(BaseModel):
    """Player ranking response."""
    rank: int
    player: PlayerResponse

    class Config:
        from_attributes = True


class CreatePlayerRequest(BaseModel):
    """Request to create a new player."""
    name: str
    is_core_player: bool = True


class CalibratePlayerRequest(BaseModel):
    """Request to calibrate a new outsider player."""
    name: str
    similar_to_player_id: int


@router.get("/", response_model=List[PlayerResponse])
def get_players(
    core_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all players.

    Args:
        core_only: If True, only return core players
        db: Database session

    Returns:
        List of PlayerResponse objects
    """
    query = db.query(Player)

    if core_only:
        query = query.filter(Player.is_core_player == 1)

    players = query.order_by(Player.name).all()

    return [
        PlayerResponse(
            id=p.id,
            name=p.name,
            mu=p.mu,
            sigma=p.sigma,
            mmr=p.mmr,
            total_games=p.total_games,
            wins=p.wins,
            losses=p.losses,
            win_rate=p.win_rate,
            favorite_race=p.favorite_race,
            is_core_player=bool(p.is_core_player),
            last_played=p.last_played
        )
        for p in players
    ]


@router.get("/rankings", response_model=List[PlayerRankingResponse])
def get_player_rankings(
    min_games: int = 5,
    core_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get player rankings by MMR.

    Args:
        min_games: Minimum games played to be ranked
        core_only: If True, only rank core players
        db: Database session

    Returns:
        List of PlayerRankingResponse objects sorted by MMR
    """
    query = db.query(Player).filter(Player.total_games >= min_games)

    if core_only:
        query = query.filter(Player.is_core_player == 1)

    # Sort by MMR (mu - 3*sigma)
    players = query.all()
    players_sorted = sorted(players, key=lambda p: p.mmr, reverse=True)

    return [
        PlayerRankingResponse(
            rank=idx + 1,
            player=PlayerResponse(
                id=p.id,
                name=p.name,
                mu=p.mu,
                sigma=p.sigma,
                mmr=p.mmr,
                total_games=p.total_games,
                wins=p.wins,
                losses=p.losses,
                win_rate=p.win_rate,
                favorite_race=p.favorite_race,
                is_core_player=bool(p.is_core_player),
                last_played=p.last_played
            )
        )
        for idx, p in enumerate(players_sorted)
    ]


@router.get("/{player_id}", response_model=PlayerDetailResponse)
def get_player_details(
    player_id: int,
    recent_matches_limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific player.

    Args:
        player_id: Player ID
        recent_matches_limit: Number of recent matches to include
        db: Database session

    Returns:
        PlayerDetailResponse with full player details

    Raises:
        HTTPException: If player not found
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Race statistics
    race_stats = {
        'Terran': player.terran_games,
        'Protoss': player.protoss_games,
        'Zerg': player.zerg_games,
        'Random': player.random_games
    }

    # Recent matches
    match_players = db.query(MatchPlayer).filter(
        MatchPlayer.player_id == player_id
    ).order_by(MatchPlayer.id.desc()).limit(recent_matches_limit).all()

    recent_matches = []
    for mp in match_players:
        match = db.query(Match).filter(Match.id == mp.match_id).first()
        if match:
            mmr_before = mp.mu_before - (3 * mp.sigma_before)
            mmr_after = mp.mu_after - (3 * mp.sigma_after)

            recent_matches.append({
                'match_id': match.id,
                'played_at': match.played_at.isoformat(),
                'game_mode': match.game_mode.value,
                'map_name': match.map_name,
                'race': mp.race.value,
                'won': bool(mp.won),
                'team_number': mp.team_number,
                'mmr_before': round(mmr_before, 2),
                'mmr_after': round(mmr_after, 2),
                'mmr_change': round(mmr_after - mmr_before, 2)
            })

    return PlayerDetailResponse(
        id=player.id,
        name=player.name,
        mu=player.mu,
        sigma=player.sigma,
        mmr=player.mmr,
        total_games=player.total_games,
        wins=player.wins,
        losses=player.losses,
        win_rate=player.win_rate,
        is_core_player=bool(player.is_core_player),
        last_played=player.last_played,
        race_stats=race_stats,
        recent_matches=recent_matches
    )


@router.post("/", response_model=PlayerResponse)
def create_player(
    request: CreatePlayerRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new player.

    Args:
        request: CreatePlayerRequest
        db: Database session

    Returns:
        PlayerResponse for created player

    Raises:
        HTTPException: If player name already exists
    """
    # Check if player already exists
    existing_player = db.query(Player).filter(Player.name == request.name).first()
    if existing_player:
        raise HTTPException(
            status_code=409,
            detail=f"Player with name '{request.name}' already exists"
        )

    # Create new player
    player = Player(
        name=request.name,
        is_core_player=1 if request.is_core_player else 0
    )

    db.add(player)
    db.commit()
    db.refresh(player)

    return PlayerResponse(
        id=player.id,
        name=player.name,
        mu=player.mu,
        sigma=player.sigma,
        mmr=player.mmr,
        total_games=player.total_games,
        wins=player.wins,
        losses=player.losses,
        win_rate=player.win_rate,
        favorite_race=player.favorite_race,
        is_core_player=bool(player.is_core_player),
        last_played=player.last_played
    )


@router.post("/calibrate", response_model=PlayerResponse)
def calibrate_player(
    request: CalibratePlayerRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new outsider player calibrated to a similar core player.

    Args:
        request: CalibratePlayerRequest
        db: Database session

    Returns:
        PlayerResponse for calibrated player

    Raises:
        HTTPException: If player name exists or similar player not found
    """
    # Check if player already exists
    existing_player = db.query(Player).filter(Player.name == request.name).first()
    if existing_player:
        raise HTTPException(
            status_code=409,
            detail=f"Player with name '{request.name}' already exists"
        )

    try:
        # Calibrate new player
        player = RatingSystem.calibrate_new_player(
            db,
            request.name,
            request.similar_to_player_id
        )

        return PlayerResponse(
            id=player.id,
            name=player.name,
            mu=player.mu,
            sigma=player.sigma,
            mmr=player.mmr,
            total_games=player.total_games,
            wins=player.wins,
            losses=player.losses,
            win_rate=player.win_rate,
            favorite_race=player.favorite_race,
            is_core_player=bool(player.is_core_player),
            last_played=player.last_played
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
