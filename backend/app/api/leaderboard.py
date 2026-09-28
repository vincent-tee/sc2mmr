from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, cast, Float
from pydantic import BaseModel

from ..database import get_db
from ..models import Player, MatchPlayer, PlayerMatchMetrics, Match
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


class CategoryInfo(BaseModel):
    key: str
    name: str
    description: str
    unit: str


@router.get("/categories")
async def get_leaderboard_categories():
    return [
        {
            "key": "mmr",
            "name": "MMR",
            "description": "Display MMR - the rating of record (TrueSkill mu/sigma)",
            "unit": "MMR",
        },
        {
            "key": "winrate",
            "name": "Win Rate",
            "description": "Highest win percentage (min 20 games)",
            "unit": "%",
        },
    ]


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


@router.get("/games", response_model=List[LeaderboardEntry])
async def get_games_leaderboard(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
):
    players = (
        db.query(Player)
        .filter(Player.is_core_player == 1, Player.is_ai == 0)
        .order_by(desc(Player.total_games))
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": p.total_games,
            "secondary_value": round(p.win_rate * 100, 1),
            "extra_info": f"{p.wins}W {p.losses}L",
        }
        for i, p in enumerate(players)
    ]


@router.get("/damage", response_model=List[LeaderboardEntry])
async def get_damage_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(10, ge=1),
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            Player.id,
            Player.name,
            Player.total_games,
            func.avg(PlayerMatchMetrics.damage_dealt).label("avg_damage"),
            func.max(PlayerMatchMetrics.damage_dealt).label("max_damage"),
        )
        .join(MatchPlayer)
        .join(PlayerMatchMetrics)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
            Player.is_ai == 0,
        )
        .group_by(Player.id)
        .order_by(desc("avg_damage"))
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": i + 1,
            "player_id": r.id,
            "name": r.name,
            "value": round(r.avg_damage or 0, 0),
            "secondary_value": r.max_damage,
            "extra_info": f"Max: {r.max_damage:,.0f}",
        }
        for i, r in enumerate(results)
    ]


@router.get("/kills", response_model=List[LeaderboardEntry])
async def get_kills_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(10, ge=1),
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            Player.id,
            Player.name,
            Player.total_games,
            func.avg(PlayerMatchMetrics.units_killed).label("avg_kills"),
            func.max(PlayerMatchMetrics.units_killed).label("max_kills"),
        )
        .join(MatchPlayer)
        .join(PlayerMatchMetrics)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
            Player.is_ai == 0,
        )
        .group_by(Player.id)
        .order_by(desc("avg_kills"))
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": i + 1,
            "player_id": r.id,
            "name": r.name,
            "value": round(r.avg_kills or 0, 0),
            "secondary_value": r.max_kills,
            "extra_info": f"Max: {r.max_kills:,.0f}",
        }
        for i, r in enumerate(results)
    ]


@router.get("/race/{race}")
async def get_race_leaderboard(
    race: str,
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(10, ge=1),
    db: Session = Depends(get_db),
):
    col = {
        "terran": Player.terran_games,
        "protoss": Player.protoss_games,
        "zerg": Player.zerg_games,
    }.get(race.lower())
    if not col:
        return {"error": "Invalid race"}
    players = (
        db.query(Player)
        .filter(col >= min_games, Player.is_core_player == 1, Player.is_ai == 0)
        .order_by(desc(col))
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": getattr(p, col.name),
            "secondary_value": p.mmr,
            "extra_info": f"MMR: {p.mmr:.0f}",
        }
        for i, p in enumerate(players)
    ]


class MetaReportResponse(BaseModel):
    squad_win_rate_by_race: Dict[str, float]
    top_compositions: List[Dict[str, Any]]
    most_effective_archetypes: List[Dict[str, Any]]


@router.get("/meta-report", response_model=MetaReportResponse)
async def get_squad_meta_report(db: Session = Depends(get_db)):
    from ..models import MatchPlayer, PerformanceFeatures, Race

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
    archs = (
        db.query(
            PerformanceFeatures.detected_build_type,
            func.avg(MatchPlayer.won).label("wr"),
            func.count(MatchPlayer.id).label("c"),
        )
        .join(MatchPlayer)
        .join(Match, MatchPlayer.match_id == Match.id)
        .filter(PerformanceFeatures.detected_build_type.isnot(None), Match.is_rated)
        .group_by(PerformanceFeatures.detected_build_type)
        .having(func.count(MatchPlayer.id) >= 10)
        .order_by(desc("wr"))
        .all()
    )
    return MetaReportResponse(
        squad_win_rate_by_race=wr_map,
        top_compositions=[],
        most_effective_archetypes=[
            {"type": a[0], "win_rate": round(float(a[1] or 0) * 100, 1), "games": a[2]}
            for a in archs
        ],
    )
