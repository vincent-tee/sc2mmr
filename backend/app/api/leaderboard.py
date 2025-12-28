"""
Leaderboard API endpoints for SC2 MMR Tracking.

Provides rankings across multiple categories:
- Overall MMR
- Win Rate
- Games Played
- Achievement Points
- Combat Stats (Damage Kings)
- Economic Stats
- Best Duos
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from pydantic import BaseModel

from ..database import get_db
from ..models import Player, PlayerSynergy, MatchPlayer, PlayerMatchMetrics, Match
from ..services import AchievementService

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


# ============================================================================
# Response Models
# ============================================================================


class LeaderboardEntry(BaseModel):
    """Generic leaderboard entry."""

    rank: int
    player_id: int
    name: str
    value: float
    secondary_value: Optional[float] = None
    extra_info: Optional[str] = None


class DuoLeaderboardEntry(BaseModel):
    """Duo leaderboard entry."""

    rank: int
    player1_id: int
    player1_name: str
    player2_id: int
    player2_name: str
    wins_together: int
    games_together: int
    win_rate: float
    synergy_score: float


class CategoryInfo(BaseModel):
    """Category metadata."""

    key: str
    name: str
    description: str
    unit: str


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/categories")
async def get_leaderboard_categories():
    """Get available leaderboard categories."""
    return [
        {
            "key": "mmr",
            "name": "Squad MMR",
            "description": "Recency-weighted skill rating (Default)",
            "unit": "MMR",
            "icon": "🏆",
        },
        {
            "key": "trueskill",
            "name": "TrueSkill",
            "description": "Pure mathematical skill rating (Stable)",
            "unit": "MMR",
            "icon": "🔢",
        },
        {
            "key": "hybrid",
            "name": "Hybrid MMR",
            "description": "Performance-adjusted skill rating (Alpha)",
            "unit": "MMR",
            "icon": "🧪",
        },
        {
            "key": "winrate",
            "name": "Win Rate",
            "description": "Highest win percentage (min 20 games)",
            "unit": "%",
            "icon": "📈",
        },
        {
            "key": "games",
            "name": "Most Games",
            "description": "Total matches played",
            "unit": "games",
            "icon": "🎮",
        },
        {
            "key": "achievements",
            "name": "Achievement Points",
            "description": "Total achievement score",
            "unit": "pts",
            "icon": "🎖️",
        },
        {
            "key": "damage",
            "name": "Damage Kings",
            "description": "Highest average damage per game",
            "unit": "dmg",
            "icon": "⚔️",
        },
        {
            "key": "kills",
            "name": "Unit Slayers",
            "description": "Most units killed on average",
            "unit": "kills",
            "icon": "💀",
        },
        {
            "key": "winstreak",
            "name": "Best Win Streak",
            "description": "Longest winning streak ever",
            "unit": "games",
            "icon": "🔥",
        },
        {
            "key": "duos",
            "name": "Best Duos",
            "description": "Most successful partner combinations",
            "unit": "wins",
            "icon": "🤝",
        },
    ]


@router.get("/mmr", response_model=List[LeaderboardEntry])
async def get_mmr_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(5, ge=0),
    db: Session = Depends(get_db),
):
    """Get players ranked by Recency-Weighted MMR."""
    players = (
        db.query(Player)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
        )
        .order_by(desc(Player.recency_weighted_mmr))
        .limit(limit)
        .all()
    )

    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": round(p.recency_weighted_mmr or p.mmr, 1),
            "secondary_value": p.total_games,
            "extra_info": f"{p.wins}W {p.losses}L",
        }
        for i, p in enumerate(players)
    ]


@router.get("/trueskill", response_model=List[LeaderboardEntry])
async def get_trueskill_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(5, ge=0),
    db: Session = Depends(get_db),
):
    """Get players ranked by pure TrueSkill display MMR (1000 + 100*mu)."""
    # Note: mmr is a property, so we sort by mu which is equivalent
    players = (
        db.query(Player)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
        )
        .order_by(desc(Player.mu))
        .limit(limit)
        .all()
    )

    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": round(p.mmr, 1),
            "secondary_value": p.mu,
            "extra_info": f"mu: {p.mu:.2f}, sigma: {p.sigma:.2f}",
        }
        for i, p in enumerate(players)
    ]


@router.get("/hybrid", response_model=List[LeaderboardEntry])
async def get_hybrid_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(5, ge=0),
    db: Session = Depends(get_db),
):
    """Get players ranked by Hybrid Performance-Adjusted MMR."""
    players = (
        db.query(Player)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
        )
        .order_by(desc(Player.hybrid_mmr))
        .limit(limit)
        .all()
    )

    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": round(p.hybrid_mmr or p.mmr, 1),
            "secondary_value": p.avg_pim,
            "extra_info": f"Avg PIM: {p.avg_pim:+.2f}" if p.avg_pim else "No metrics",
        }
        for i, p in enumerate(players)
    ]


@router.get("/winrate", response_model=List[LeaderboardEntry])
async def get_winrate_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(20, ge=5),
    db: Session = Depends(get_db),
):
    """Get players ranked by win rate (minimum games required)."""
    players = (
        db.query(Player)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
        )
        .all()
    )

    # Calculate win rates
    ranked = sorted(players, key=lambda p: p.win_rate, reverse=True)[:limit]

    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": round(p.win_rate * 100, 1),
            "secondary_value": p.total_games,
            "extra_info": f"{p.wins}W {p.losses}L",
        }
        for i, p in enumerate(ranked)
    ]


@router.get("/games", response_model=List[LeaderboardEntry])
async def get_games_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get players ranked by total games played."""
    players = (
        db.query(Player)
        .filter(
            Player.is_core_player == 1,
        )
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


@router.get("/achievements", response_model=List[LeaderboardEntry])
async def get_achievements_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get players ranked by achievement points."""
    results = AchievementService.get_achievement_leaderboard(db, limit)

    return [
        {
            "rank": i + 1,
            "player_id": r["player_id"],
            "name": r["name"],
            "value": r["total_points"],
            "secondary_value": r["total_achievements"],
            "extra_info": f"{r['total_achievements']} badges",
        }
        for i, r in enumerate(results)
    ]


@router.get("/damage", response_model=List[LeaderboardEntry])
async def get_damage_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(10, ge=1),
    db: Session = Depends(get_db),
):
    """Get players ranked by average damage dealt."""
    results = (
        db.query(
            Player.id,
            Player.name,
            Player.total_games,
            func.avg(PlayerMatchMetrics.damage_dealt).label("avg_damage"),
            func.max(PlayerMatchMetrics.damage_dealt).label("max_damage"),
        )
        .join(MatchPlayer, Player.id == MatchPlayer.player_id)
        .join(PlayerMatchMetrics, MatchPlayer.id == PlayerMatchMetrics.match_player_id)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
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
    """Get players ranked by average units killed."""
    results = (
        db.query(
            Player.id,
            Player.name,
            Player.total_games,
            func.avg(PlayerMatchMetrics.units_killed).label("avg_kills"),
            func.max(PlayerMatchMetrics.units_killed).label("max_kills"),
        )
        .join(MatchPlayer, Player.id == MatchPlayer.player_id)
        .join(PlayerMatchMetrics, MatchPlayer.id == PlayerMatchMetrics.match_player_id)
        .filter(
            Player.total_games >= min_games,
            Player.is_core_player == 1,
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


@router.get("/winstreak", response_model=List[LeaderboardEntry])
async def get_winstreak_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get players ranked by their best win streak ever."""
    # Calculate win streaks from match history
    players = (
        db.query(Player)
        .filter(
            Player.total_games >= 5,
            Player.is_core_player == 1,
        )
        .all()
    )

    streaks = []
    for player in players:
        matches = (
            db.query(MatchPlayer)
            .filter(MatchPlayer.player_id == player.id)
            .join(Match)
            .order_by(Match.played_at)
            .all()
        )

        max_streak = 0
        current_streak = 0
        for mp in matches:
            if mp.won:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        streaks.append(
            {
                "player": player,
                "max_streak": max_streak,
                "current_streak": current_streak,
            }
        )

    # Sort by max streak
    ranked = sorted(streaks, key=lambda x: x["max_streak"], reverse=True)[:limit]

    return [
        {
            "rank": i + 1,
            "player_id": s["player"].id,
            "name": s["player"].name,
            "value": s["max_streak"],
            "secondary_value": s["current_streak"],
            "extra_info": f"Current: {s['current_streak']}",
        }
        for i, s in enumerate(ranked)
    ]


@router.get("/duos", response_model=List[DuoLeaderboardEntry])
async def get_duos_leaderboard(
    limit: int = Query(20, ge=1, le=50),
    min_games: int = Query(10, ge=3),
    sort_by: str = Query("wins", enum=["wins", "winrate", "synergy"]),
    db: Session = Depends(get_db),
):
    """Get the best duo partnerships."""
    query = db.query(PlayerSynergy).filter(PlayerSynergy.games_together >= min_games)

    synergies = query.all()

    # Get player names
    player_ids = set()
    for s in synergies:
        player_ids.add(s.player1_id)
        player_ids.add(s.player2_id)

    players = {
        p.id: p.name for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }

    # Calculate win rates and sort
    duos = []
    for s in synergies:
        win_rate = (
            (s.wins_together / s.games_together * 100) if s.games_together > 0 else 0
        )
        duos.append(
            {
                "synergy": s,
                "win_rate": win_rate,
                "player1_name": players.get(s.player1_id, "Unknown"),
                "player2_name": players.get(s.player2_id, "Unknown"),
            }
        )

    # Sort based on requested criteria
    if sort_by == "wins":
        duos.sort(key=lambda x: x["synergy"].wins_together, reverse=True)
    elif sort_by == "winrate":
        duos.sort(key=lambda x: x["win_rate"], reverse=True)
    else:
        duos.sort(key=lambda x: x["synergy"].synergy_score, reverse=True)

    return [
        {
            "rank": i + 1,
            "player1_id": d["synergy"].player1_id,
            "player1_name": d["player1_name"],
            "player2_id": d["synergy"].player2_id,
            "player2_name": d["player2_name"],
            "wins_together": d["synergy"].wins_together,
            "games_together": d["synergy"].games_together,
            "win_rate": round(d["win_rate"], 1),
            "synergy_score": round(d["synergy"].synergy_score, 1),
        }
        for i, d in enumerate(duos[:limit])
    ]


@router.get("/race/{race}")
async def get_race_leaderboard(
    race: str,
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(10, ge=1),
    db: Session = Depends(get_db),
):
    """Get players ranked by performance with a specific race."""
    race_column = {
        "terran": Player.terran_games,
        "protoss": Player.protoss_games,
        "zerg": Player.zerg_games,
    }.get(race.lower())

    if not race_column:
        return {"error": "Invalid race. Use: terran, protoss, or zerg"}

    players = (
        db.query(Player)
        .filter(
            race_column >= min_games,
            Player.is_core_player == 1,
        )
        .order_by(desc(race_column))
        .limit(limit)
        .all()
    )

    race_map = {
        "terran": "terran_games",
        "protoss": "protoss_games",
        "zerg": "zerg_games",
    }
    race_attr = race_map[race.lower()]

    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": getattr(p, race_attr),
            "secondary_value": round(p.recency_weighted_mmr or p.mmr, 1),
            "extra_info": f"MMR: {round(p.recency_weighted_mmr or p.mmr, 0)}",
        }
        for i, p in enumerate(players)
    ]
