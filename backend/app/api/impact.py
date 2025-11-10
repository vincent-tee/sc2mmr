"""
API endpoints for player impact and synergy statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json

from ..database import get_db
from ..models import Player, MatchPlayer, PlayerMatchMetrics, PlayerSynergy
from ..impact_service import ImpactService


router = APIRouter(prefix="/impact", tags=["impact"])


# Response models
class ImpactScoresResponse(BaseModel):
    """Player impact scores."""
    economic_score: float
    combat_score: float
    efficiency_score: float
    overall_impact: float


class PlayerImpactResponse(BaseModel):
    """Player with impact scores."""
    id: int
    name: str
    mmr: float
    avg_impact: ImpactScoresResponse
    total_games: int
    win_rate: float


class MatchMetricsResponse(BaseModel):
    """Detailed match metrics."""
    match_id: int
    player_name: str
    race: str
    won: bool

    # Economic
    minerals_collected: int
    vespene_collected: int
    total_resources: int
    workers_created: int

    # Combat
    units_killed: int
    units_lost: int
    damage_dealt: int
    damage_taken: int
    damage_ratio: float

    # Scores
    economic_score: float
    combat_score: float
    efficiency_score: float
    overall_impact: float

    # Other
    apm: float
    first_expansion_timing: Optional[int]


class SynergyResponse(BaseModel):
    """Synergy between two players."""
    player1_id: int
    player1_name: str
    player2_id: int
    player2_name: str
    games_together: int
    wins_together: int
    win_rate: float
    synergy_score: float
    avg_combined_impact: float


class PlayerSynergyListResponse(BaseModel):
    """List of synergies for a player."""
    player_id: int
    player_name: str
    synergies: List[SynergyResponse]


@router.get("/players", response_model=List[PlayerImpactResponse])
def get_players_by_impact(
    sort_by: str = "overall",  # economic, combat, efficiency, overall
    min_games: int = 5,
    db: Session = Depends(get_db)
):
    """
    Get players ranked by impact scores.

    Args:
        sort_by: Sort by which impact score (economic, combat, efficiency, overall)
        min_games: Minimum games played
        db: Database session

    Returns:
        List of players with impact scores
    """
    players = db.query(Player).filter(Player.total_games >= min_games).all()

    # Sort by requested metric
    sort_key_map = {
        "economic": lambda p: p.avg_economic_score,
        "combat": lambda p: p.avg_combat_score,
        "efficiency": lambda p: p.avg_efficiency_score,
        "overall": lambda p: p.avg_overall_impact
    }

    sort_key = sort_key_map.get(sort_by, sort_key_map["overall"])
    players_sorted = sorted(players, key=sort_key, reverse=True)

    return [
        PlayerImpactResponse(
            id=p.id,
            name=p.name,
            mmr=p.mmr,
            avg_impact=ImpactScoresResponse(
                economic_score=p.avg_economic_score,
                combat_score=p.avg_combat_score,
                efficiency_score=p.avg_efficiency_score,
                overall_impact=p.avg_overall_impact
            ),
            total_games=p.total_games,
            win_rate=p.win_rate
        )
        for p in players_sorted
    ]


@router.get("/players/{player_id}/matches", response_model=List[MatchMetricsResponse])
def get_player_match_metrics(
    player_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get detailed match metrics for a player.

    Args:
        player_id: Player ID
        limit: Maximum matches to return
        db: Database session

    Returns:
        List of detailed match metrics
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Get recent matches
    match_players = db.query(MatchPlayer).filter(
        MatchPlayer.player_id == player_id
    ).order_by(MatchPlayer.id.desc()).limit(limit).all()

    results = []
    for mp in match_players:
        metrics = db.query(PlayerMatchMetrics).filter(
            PlayerMatchMetrics.match_player_id == mp.id
        ).first()

        if metrics:
            results.append(MatchMetricsResponse(
                match_id=mp.match_id,
                player_name=player.name,
                race=mp.race.value,
                won=bool(mp.won),
                minerals_collected=metrics.minerals_collected,
                vespene_collected=metrics.vespene_collected,
                total_resources=metrics.total_resources_collected,
                workers_created=metrics.workers_created,
                units_killed=metrics.units_killed,
                units_lost=metrics.units_lost,
                damage_dealt=metrics.damage_dealt,
                damage_taken=metrics.damage_taken,
                damage_ratio=metrics.damage_ratio,
                economic_score=metrics.economic_score,
                combat_score=metrics.combat_score,
                efficiency_score=metrics.efficiency_score,
                overall_impact=metrics.overall_impact,
                apm=metrics.apm,
                first_expansion_timing=metrics.first_expansion_timing
            ))

    return results


@router.get("/players/{player_id}/synergies", response_model=PlayerSynergyListResponse)
def get_player_synergies(
    player_id: int,
    min_games: int = 3,
    db: Session = Depends(get_db)
):
    """
    Get synergies for a specific player.

    Args:
        player_id: Player ID
        min_games: Minimum games together
        db: Database session

    Returns:
        List of synergies with other players
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    synergies = ImpactService.get_player_synergies(db, player_id, min_games)

    synergy_responses = []
    for other_player, synergy in synergies:
        # Determine which is player1 and player2
        if synergy.player1_id == player_id:
            p1_id, p1_name = player.id, player.name
            p2_id, p2_name = other_player.id, other_player.name
        else:
            p1_id, p1_name = other_player.id, other_player.name
            p2_id, p2_name = player.id, player.name

        synergy_responses.append(SynergyResponse(
            player1_id=p1_id,
            player1_name=p1_name,
            player2_id=p2_id,
            player2_name=p2_name,
            games_together=synergy.games_together,
            wins_together=synergy.wins_together,
            win_rate=synergy.win_rate_together,
            synergy_score=synergy.synergy_score,
            avg_combined_impact=synergy.avg_combined_impact
        ))

    return PlayerSynergyListResponse(
        player_id=player.id,
        player_name=player.name,
        synergies=synergy_responses
    )


@router.get("/synergies/top", response_model=List[SynergyResponse])
def get_top_synergies(
    min_games: int = 5,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get top player synergies across all players.

    Args:
        min_games: Minimum games together
        limit: Maximum results
        db: Database session

    Returns:
        List of top synergies
    """
    top_synergies = ImpactService.get_top_synergies(db, min_games, limit)

    return [
        SynergyResponse(
            player1_id=player1.id,
            player1_name=player1.name,
            player2_id=player2.id,
            player2_name=player2.name,
            games_together=synergy.games_together,
            wins_together=synergy.wins_together,
            win_rate=synergy.win_rate_together,
            synergy_score=synergy.synergy_score,
            avg_combined_impact=synergy.avg_combined_impact
        )
        for player1, player2, synergy in top_synergies
    ]


@router.get("/leaderboard/{category}")
def get_impact_leaderboard(
    category: str,  # economic, combat, efficiency, overall, damage, resources
    min_games: int = 5,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get leaderboard for specific impact category.

    Args:
        category: Category to rank by
        min_games: Minimum games played
        limit: Maximum results
        db: Database session

    Returns:
        Leaderboard with rankings
    """
    players = db.query(Player).filter(Player.total_games >= min_games).all()

    # Define sorting keys
    if category == "economic":
        players_sorted = sorted(players, key=lambda p: p.avg_economic_score, reverse=True)
        score_key = "avg_economic_score"
    elif category == "combat":
        players_sorted = sorted(players, key=lambda p: p.avg_combat_score, reverse=True)
        score_key = "avg_combat_score"
    elif category == "efficiency":
        players_sorted = sorted(players, key=lambda p: p.avg_efficiency_score, reverse=True)
        score_key = "avg_efficiency_score"
    elif category == "overall":
        players_sorted = sorted(players, key=lambda p: p.avg_overall_impact, reverse=True)
        score_key = "avg_overall_impact"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    players_sorted = players_sorted[:limit]

    leaderboard = []
    for rank, player in enumerate(players_sorted, 1):
        leaderboard.append({
            "rank": rank,
            "player_id": player.id,
            "player_name": player.name,
            "score": getattr(player, score_key),
            "total_games": player.total_games,
            "win_rate": player.win_rate,
            "mmr": player.mmr
        })

    return {
        "category": category,
        "min_games": min_games,
        "leaderboard": leaderboard
    }
