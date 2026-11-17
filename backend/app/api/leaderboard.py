from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, cast, Float
from pydantic import BaseModel

from ..database import get_db
from ..models import Player, MatchPlayer, Match
from .players import compute_activity_flags, active_only_clause

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    name: str
    value: float
    secondary_value: Optional[float] = None
    extra_info: Optional[str] = None
    is_new: bool = False
    is_active: bool = True
    days_since_played: Optional[int] = None


@router.get("/mmr", response_model=List[LeaderboardEntry])
async def get_mmr_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(15, ge=0),
    active_only: bool = Query(
        False,
        description=(
            "Hide legacy players — established (>=15 games) players inactive "
            "2+ years, or new (<15 games) players inactive 6+ months"
        ),
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Player).filter(
        Player.total_games >= min_games,
        Player.is_core_player == 1,
        Player.is_ai == 0,
    )
    if active_only:
        query = query.filter(active_only_clause())

    players = query.order_by(desc(Player.mmr)).limit(limit).all()

    result = []
    for i, p in enumerate(players):
        is_new, is_active, days_since = compute_activity_flags(p.total_games, p.last_played)
        result.append(
            {
                "rank": i + 1,
                "player_id": p.id,
                "name": p.name,
                "value": p.mmr,
                "secondary_value": p.total_games,
                "extra_info": f"{p.wins}W {p.losses}L",
                "is_new": is_new,
                "is_active": is_active,
                "days_since_played": days_since,
            }
        )
    return result


@router.get("/winrate", response_model=List[LeaderboardEntry])
async def get_winrate_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(20, ge=5),
    db: Session = Depends(get_db),
):
    players = (
        db.query(Player)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
            Player.is_ai == 0,
        )
        .order_by(desc(cast(Player.wins, Float) / cast(Player.total_games, Float)))
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": round(p.win_rate * 100, 1),
            "secondary_value": p.total_games,
            "extra_info": f"{p.wins}W {p.losses}L",
        }
        for i, p in enumerate(players)
    ]


class MetaReportResponse(BaseModel):
    squad_win_rate_by_race: Dict[str, float]
    top_compositions: List[Dict[str, Any]]
    most_effective_archetypes: List[Dict[str, Any]]


@router.get("/meta-report", response_model=MetaReportResponse)
async def get_squad_meta_report(db: Session = Depends(get_db)):
    from ..models import MatchPlayer, Race

    wr_map = {}
    for r in [Race.TERRAN, Race.PROTOSS, Race.ZERG]:
        wr = (
            db.query(func.avg(MatchPlayer.won)).join(Match)
            .filter(MatchPlayer.race == r, Match.is_rated).scalar()
        )
        count = (
            db.query(func.count(MatchPlayer.id)).filter(MatchPlayer.race == r).scalar()
        )
        if count and count > 0:
            wr_map[r.value] = round(float(wr or 0) * 100, 1)
    return MetaReportResponse(
        squad_win_rate_by_race=wr_map,
        top_compositions=[],
        most_effective_archetypes=[],
    )
