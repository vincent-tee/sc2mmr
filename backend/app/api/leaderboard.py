from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case, cast, Float
from pydantic import BaseModel

from ..database import get_db
from ..models import Player, MatchPlayer, PlayerMatchMetrics, Match
from ..services import AchievementService
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
    # recent-form only: real table fields instead of cramming into extra_info.
    # secondary_value doubles as win rate % for this category.
    games_played: Optional[int] = None
    form_icon: Optional[str] = None


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
            "icon": "🏆",
        },
        {
            "key": "recent-form",
            "name": "Recent Form",
            "description": "Performance weighted by the squad's last 30 matches (10-match half-life) - you only appear if you played in at least one",
            "unit": "MMR",
            "icon": "📊",
        },
        {
            "key": "combat",
            "name": "Combat",
            "description": "Damage dealers and unit killers",
            "unit": "score",
            "icon": "⚔️",
        },
        {
            "key": "winrate",
            "name": "Win Rate",
            "description": "Highest win percentage (min 20 games)",
            "unit": "%",
            "icon": "📈",
        },
        {
            "key": "winstreak",
            "name": "Hot Streak",
            "description": "Longest winning streak",
            "unit": "wins",
            "icon": "🔥",
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


@router.get("/recent-form", response_model=List[LeaderboardEntry])
async def get_recent_form_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(10, ge=0),
    half_life_matches: int = Query(10, ge=5, le=50),
    max_matches: int = Query(30, ge=10, le=100),
    db: Session = Depends(get_db),
):
    """
    Leaderboard based on match-weighted recency MMR, scoped to a GLOBAL
    window: the squad's most recent `max_matches` matches by real date
    (Match.played_at), not each player's own personal last N. A player who
    doesn't appear in any of those matches doesn't appear on this board at
    all - that's the recency filter, and it falls out of the window
    definition for free rather than needing a separate activity gate.

    Weighting is still by POSITION, not calendar days (doesn't penalize a
    player who missed a few recent games but is still clearly active) -
    but position here is the match's GLOBAL rank within the squad-wide
    window (0 = the squad's single most recent match), not the player's own
    personal rank. So if you weren't in the squad's most recent match but
    were in its 3rd-most-recent, your best game this window starts at
    global rank 2's weight, not rank 0's - reflecting that even your most
    recent appearance is a bit behind the squad's current pulse.

    Default: half-life of 10 matches (global rank 10 has 50% weight, rank 20 has 25%).
    """
    # The squad's most recent `max_matches` matches, by real date, globally.
    recent_matches = (
        db.query(Match)
        .filter(Match.played_at.isnot(None))
        .order_by(desc(Match.played_at))
        .limit(max_matches)
        .all()
    )
    global_rank = {m.id: i for i, m in enumerate(recent_matches)}
    if not global_rank:
        return []

    match_players = (
        db.query(MatchPlayer)
        .join(Player, MatchPlayer.player_id == Player.id)
        .filter(
            MatchPlayer.match_id.in_(global_rank.keys()),
            Player.total_games >= min_games,
            Player.is_core_player == 1,
            Player.is_ai == 0,
        )
        .all()
    )

    by_player: Dict[int, List[MatchPlayer]] = {}
    for mp in match_players:
        by_player.setdefault(mp.player_id, []).append(mp)

    players_by_id = {
        p.id: p
        for p in db.query(Player).filter(Player.id.in_(by_player.keys())).all()
    }

    results = []
    for player_id, appearances in by_player.items():
        p = players_by_id[player_id]
        # Most recent appearance first, by the match's global rank.
        appearances.sort(key=lambda mp: global_rank[mp.match_id])

        weighted_sum = 0.0
        weight_total = 0.0
        recent_wins = 0
        recent_games = min(5, len(appearances))

        for i, mp in enumerate(appearances):
            if mp.mmr_after is None:
                continue
            rank = global_rank[mp.match_id]
            weight = 0.5 ** (rank / half_life_matches)
            weighted_sum += mp.mmr_after * weight
            weight_total += weight
            if i < 5 and mp.won and mp.match.is_rated:
                recent_wins += 1

        if weight_total == 0:
            continue

        recent_mmr = weighted_sum / weight_total
        recent_form = recent_wins / recent_games if recent_games > 0 else 0.5
        form_icon = "🔥" if recent_form >= 0.7 else ("❄️" if recent_form <= 0.3 else "")
        is_new, is_active, days_since = compute_activity_flags(p.total_games, p.last_played)

        results.append({
            "player_id": p.id,
            "name": p.name,
            "recent_mmr": recent_mmr,
            "matches_used": len(appearances),
            "recent_form": recent_form,
            "form_icon": form_icon,
            "is_new": is_new,
            "is_active": is_active,
            "days_since_played": days_since,
        })

    results.sort(key=lambda x: x["recent_mmr"], reverse=True)

    return [
        {
            "rank": i + 1,
            "player_id": r["player_id"],
            "name": r["name"],
            "value": round(r["recent_mmr"], 1),
            "secondary_value": round(r["recent_form"] * 100, 0),  # win rate %, over last 5 games in-window
            "extra_info": f"{r['matches_used']}/{len(global_rank)} of squad's last games",
            "games_played": r["matches_used"],
            "form_icon": r["form_icon"],
            "is_new": r["is_new"],
            "is_active": r["is_active"],
            "days_since_played": r["days_since_played"],
        }
        for i, r in enumerate(results[:limit])
    ]


@router.get("/specialists", response_model=List[LeaderboardEntry])
async def get_specialist_leaderboard(
    category: str = Query(
        "combat", regex="^(combat|economic|efficiency|teamwork|apm)$"
    ),
    limit: int = Query(20, ge=1, le=100),
    min_games: int = Query(5, ge=0),
    db: Session = Depends(get_db),
):
    col = {
        "combat": Player.avg_combat_score,
        "economic": Player.avg_economic_score,
        "efficiency": Player.avg_efficiency_score,
        "teamwork": Player.avg_overall_impact,
        "apm": Player.avg_aggression_score,
    }[category]
    players = (
        db.query(Player)
        .filter(Player.total_games >= min_games, Player.is_ai == 0)
        .order_by(desc(col))
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": i + 1,
            "player_id": p.id,
            "name": p.name,
            "value": round(getattr(p, col.name), 1),
            "secondary_value": p.mmr,
            "extra_info": f"Rank: {p.mmr:.0f} MMR",
        }
        for i, p in enumerate(players)
    ]


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


@router.get("/winstreak", response_model=List[LeaderboardEntry])
async def get_winstreak_leaderboard(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
):
    players = (
        db.query(Player)
        .filter(Player.total_games >= 5, Player.is_core_player == 1, Player.is_ai == 0)
        .all()
    )
    streaks = []
    for player in players:
        matches = (
            db.query(MatchPlayer.won)
            .filter(MatchPlayer.player_id == player.id)
            .join(Match)
            .filter(Match.is_rated)
            .order_by(Match.played_at)
            .all()
        )
        ms, cs = 0, 0
        for m in matches:
            if m.won:
                cs += 1
                ms = max(ms, cs)
            else:
                cs = 0
        streaks.append({"player": player, "max_streak": ms, "current_streak": cs})
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


@router.get("/longest-matches", response_model=List[LeaderboardEntry])
async def get_longest_matches_leaderboard(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
):
    """Each player's own single longest match, ranked descending."""
    players = (
        db.query(Player)
        .filter(Player.total_games >= 5, Player.is_core_player == 1, Player.is_ai == 0)
        .all()
    )
    longest = []
    for player in players:
        best = (
            db.query(Match)
            .join(MatchPlayer)
            .filter(MatchPlayer.player_id == player.id)
            .order_by(desc(Match.duration_seconds))
            .first()
        )
        if best:
            longest.append({"player": player, "match": best})
    ranked = sorted(longest, key=lambda x: x["match"].duration_seconds, reverse=True)[:limit]
    return [
        {
            "rank": i + 1,
            "player_id": e["player"].id,
            "name": e["player"].name,
            "value": e["match"].duration_seconds,
            "extra_info": f"{e['match'].map_name}",
        }
        for i, e in enumerate(ranked)
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
