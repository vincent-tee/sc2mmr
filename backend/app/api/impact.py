"""
API endpoints for player impact and synergy statistics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
import json
from collections import defaultdict

from ..database import get_db
from ..models import Player, MatchPlayer, PlayerMatchMetrics, PlayerSynergy
from ..impact_service import ImpactService
from ..damage_timeline import DamageTimeline, DamageTimelineExtractor


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
    db: Session = Depends(get_db),
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
        "overall": lambda p: p.avg_overall_impact,
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
                overall_impact=p.avg_overall_impact,
            ),
            total_games=p.total_games,
            win_rate=p.win_rate,
        )
        for p in players_sorted
    ]


@router.get("/players/{player_id}/matches", response_model=List[MatchMetricsResponse])
def get_player_match_metrics(
    player_id: int, limit: int = 20, db: Session = Depends(get_db)
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
    match_players = (
        db.query(MatchPlayer)
        .filter(MatchPlayer.player_id == player_id)
        .order_by(MatchPlayer.id.desc())
        .limit(limit)
        .all()
    )

    results = []
    for mp in match_players:
        metrics = (
            db.query(PlayerMatchMetrics)
            .filter(PlayerMatchMetrics.match_player_id == mp.id)
            .first()
        )

        if metrics:
            results.append(
                MatchMetricsResponse(
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
                    first_expansion_timing=metrics.first_expansion_timing,
                )
            )

    return results


@router.get("/players/{player_id}/synergies", response_model=PlayerSynergyListResponse)
def get_player_synergies(
    player_id: int, min_games: int = 3, db: Session = Depends(get_db)
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

        synergy_responses.append(
            SynergyResponse(
                player1_id=p1_id,
                player1_name=p1_name,
                player2_id=p2_id,
                player2_name=p2_name,
                games_together=synergy.games_together,
                wins_together=synergy.wins_together,
                win_rate=synergy.win_rate_together,
                synergy_score=synergy.synergy_score,
                avg_combined_impact=synergy.avg_combined_impact,
            )
        )

    return PlayerSynergyListResponse(
        player_id=player.id, player_name=player.name, synergies=synergy_responses
    )


@router.get("/synergies/top", response_model=List[SynergyResponse])
def get_top_synergies(
    min_games: int = 5, limit: int = 10, db: Session = Depends(get_db)
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
            avg_combined_impact=synergy.avg_combined_impact,
        )
        for player1, player2, synergy in top_synergies
    ]


@router.get("/leaderboard/{category}")
def get_impact_leaderboard(
    category: str,  # economic, combat, efficiency, overall, damage, resources
    min_games: int = 5,
    limit: int = 10,
    db: Session = Depends(get_db),
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
        players_sorted = sorted(
            players, key=lambda p: p.avg_economic_score, reverse=True
        )
        score_key = "avg_economic_score"
    elif category == "combat":
        players_sorted = sorted(players, key=lambda p: p.avg_combat_score, reverse=True)
        score_key = "avg_combat_score"
    elif category == "efficiency":
        players_sorted = sorted(
            players, key=lambda p: p.avg_efficiency_score, reverse=True
        )
        score_key = "avg_efficiency_score"
    elif category == "overall":
        players_sorted = sorted(
            players, key=lambda p: p.avg_overall_impact, reverse=True
        )
        score_key = "avg_overall_impact"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    players_sorted = players_sorted[:limit]

    leaderboard = []
    for rank, player in enumerate(players_sorted, 1):
        leaderboard.append(
            {
                "rank": rank,
                "player_id": player.id,
                "player_name": player.name,
                "score": getattr(player, score_key),
                "total_games": player.total_games,
                "win_rate": player.win_rate,
                "mmr": player.mmr,
            }
        )

    return {"category": category, "min_games": min_games, "leaderboard": leaderboard}


# Damage Timeline Endpoints


class TimingAttackResponse(BaseModel):
    """Timing attack response."""

    start_second: int
    start_time: str  # MM:SS format
    end_second: int
    peak_second: int
    peak_time: str  # MM:SS format
    total_damage: int
    peak_damage: int
    duration_seconds: int


class DamageSpikeResponse(BaseModel):
    """Damage spike response."""

    second: int
    time: str  # MM:SS format
    damage: int


class DamageTimelineResponse(BaseModel):
    """Damage timeline analysis response."""

    match_id: int
    player_name: str
    total_damage: int
    first_damage_second: Optional[int]
    first_damage_time: Optional[str]
    peak_damage_second: Optional[int]
    peak_damage_time: Optional[str]
    peak_damage_amount: Optional[int]
    damage_distribution: dict  # {early, mid, late}
    timing_attacks: List[TimingAttackResponse]
    damage_spikes: List[DamageSpikeResponse]
    consistency_score: float


@router.get(
    "/players/{player_id}/matches/{match_id}/timeline",
    response_model=DamageTimelineResponse,
)
def get_match_damage_timeline(
    player_id: int, match_id: int, db: Session = Depends(get_db)
):
    """
    Get detailed damage timeline for a specific match.

    Args:
        player_id: Player ID
        match_id: Match ID
        db: Database session

    Returns:
        DamageTimelineResponse with timeline analysis

    Raises:
        HTTPException: If player or match not found
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Find the match player record
    match_player = (
        db.query(MatchPlayer)
        .filter(MatchPlayer.match_id == match_id, MatchPlayer.player_id == player_id)
        .first()
    )

    if not match_player:
        raise HTTPException(
            status_code=404, detail="Player did not participate in this match"
        )

    # Get metrics with timeline
    metrics = (
        db.query(PlayerMatchMetrics)
        .filter(PlayerMatchMetrics.match_player_id == match_player.id)
        .first()
    )

    if not metrics or not metrics.damage_timeline:
        raise HTTPException(
            status_code=404, detail="Damage timeline not available for this match"
        )

    # Parse timeline
    timeline = DamageTimeline.from_json(metrics.damage_timeline)

    # Get first damage
    first_damage_sec = timeline.get_first_damage_second()
    first_damage_time = None
    if first_damage_sec:
        mins = first_damage_sec // 60
        secs = first_damage_sec % 60
        first_damage_time = f"{mins}:{secs:02d}"

    # Get peak damage
    peak_data = timeline.get_peak_damage_second()
    peak_sec, peak_dmg = None, None
    peak_time = None
    if peak_data:
        peak_sec, peak_dmg = peak_data
        mins = peak_sec // 60
        secs = peak_sec % 60
        peak_time = f"{mins}:{secs:02d}"

    # Detect timing attacks
    timing_attacks = timeline.detect_timing_attacks()
    timing_attack_responses = [
        TimingAttackResponse(
            start_second=attack.start_second,
            start_time=attack.start_time_display,
            end_second=attack.end_second,
            peak_second=attack.peak_second,
            peak_time=attack.peak_time_display,
            total_damage=attack.total_damage,
            peak_damage=attack.peak_damage,
            duration_seconds=attack.duration_seconds,
        )
        for attack in timing_attacks
    ]

    # Get damage spikes
    spikes = timeline.get_damage_spikes()
    spike_responses = [
        DamageSpikeResponse(
            second=spike.second, time=spike.time_display, damage=spike.damage
        )
        for spike in spikes[:10]  # Top 10 spikes
    ]

    return DamageTimelineResponse(
        match_id=match_id,
        player_name=player.name,
        total_damage=timeline.get_total_damage(),
        first_damage_second=first_damage_sec,
        first_damage_time=first_damage_time,
        peak_damage_second=peak_sec,
        peak_damage_time=peak_time,
        peak_damage_amount=peak_dmg,
        damage_distribution=timeline.get_damage_distribution(),
        timing_attacks=timing_attack_responses,
        damage_spikes=spike_responses,
        consistency_score=timeline.calculate_consistency_score(),
    )


@router.get("/matches/{match_id}/coordination")
def get_match_team_coordination(match_id: int, db: Session = Depends(get_db)):
    """
    Analyze team coordination in a match based on attack timing.

    Args:
        match_id: Match ID
        db: Database session

    Returns:
        Team coordination analysis

    Raises:
        HTTPException: If match not found
    """
    # Get all players in the match
    match_players = db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()

    if not match_players:
        raise HTTPException(status_code=404, detail="Match not found")

    # Group by team
    team_1 = [mp for mp in match_players if mp.team_number == 1]
    team_2 = [mp for mp in match_players if mp.team_number == 2]

    def analyze_team_coordination(team_players):
        """Analyze coordination within a team."""
        timelines = []

        for mp in team_players:
            metrics = (
                db.query(PlayerMatchMetrics)
                .filter(PlayerMatchMetrics.match_player_id == mp.id)
                .first()
            )

            if metrics and metrics.damage_timeline:
                player = db.query(Player).filter(Player.id == mp.player_id).first()
                timeline = DamageTimeline.from_json(metrics.damage_timeline)
                timelines.append(
                    {
                        "player_name": player.name if player else "Unknown",
                        "timeline": timeline,
                        "first_damage": timeline.get_first_damage_second(),
                    }
                )

        if len(timelines) < 2:
            return {"coordination_score": None, "analysis": "Not enough data"}

        # Calculate pairwise coordination
        coordination_scores = []
        for i in range(len(timelines)):
            for j in range(i + 1, len(timelines)):
                score = DamageTimelineExtractor.calculate_coordination_score(
                    timelines[i]["timeline"], timelines[j]["timeline"]
                )
                coordination_scores.append(
                    {
                        "player1": timelines[i]["player_name"],
                        "player2": timelines[j]["player_name"],
                        "score": score,
                    }
                )

        avg_coordination = sum(cs["score"] for cs in coordination_scores) / len(
            coordination_scores
        )

        return {
            "coordination_score": avg_coordination,
            "pairwise_scores": coordination_scores,
            "first_damages": [
                {"player": t["player_name"], "first_damage_second": t["first_damage"]}
                for t in timelines
            ],
        }

    team_1_analysis = analyze_team_coordination(team_1)
    team_2_analysis = analyze_team_coordination(team_2)

    return {"match_id": match_id, "team_1": team_1_analysis, "team_2": team_2_analysis}


@router.get("/players/{player_id}/attack-patterns")
def get_player_attack_patterns(
    player_id: int, limit: int = 20, db: Session = Depends(get_db)
):
    """
    Analyze player's attack timing patterns across matches.

    Args:
        player_id: Player ID
        limit: Number of recent matches to analyze
        db: Database session

    Returns:
        Attack pattern analysis

    Raises:
        HTTPException: If player not found
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Get recent matches
    match_players = (
        db.query(MatchPlayer)
        .filter(MatchPlayer.player_id == player_id)
        .order_by(MatchPlayer.id.desc())
        .limit(limit)
        .all()
    )

    first_damage_timings = []
    timing_attacks_by_time: Dict[int, int] = defaultdict(int)  # Group by minute
    damage_distributions: Dict[str, List[float]] = {"early": [], "mid": [], "late": []}

    for mp in match_players:
        metrics = (
            db.query(PlayerMatchMetrics)
            .filter(PlayerMatchMetrics.match_player_id == mp.id)
            .first()
        )

        if metrics:
            # First damage timing
            if metrics.first_damage_timing:
                first_damage_timings.append(metrics.first_damage_timing)

            # Damage distribution
            if metrics.damage_timeline:
                timeline = DamageTimeline.from_json(metrics.damage_timeline)
                dist = timeline.get_damage_distribution()
                damage_distributions["early"].append(dist["early"])
                damage_distributions["mid"].append(dist["mid"])
                damage_distributions["late"].append(dist["late"])

                # Track timing attacks by minute
                attacks = timeline.detect_timing_attacks()
                for attack in attacks:
                    minute = attack.start_second // 60
                    timing_attacks_by_time[minute] += 1

    # Calculate averages
    avg_first_damage = None
    if first_damage_timings:
        avg_first_damage = sum(first_damage_timings) / len(first_damage_timings)

    avg_damage_dist = {}
    for phase in ["early", "mid", "late"]:
        if damage_distributions[phase]:
            avg_damage_dist[phase] = sum(damage_distributions[phase]) / len(
                damage_distributions[phase]
            )
        else:
            avg_damage_dist[phase] = 0

    # Determine preferred attack timing
    preferred_timing = None
    if timing_attacks_by_time:
        preferred_timing = max(timing_attacks_by_time.items(), key=lambda x: x[1])

    return {
        "player_id": player_id,
        "player_name": player.name,
        "matches_analyzed": len(match_players),
        "avg_first_damage_second": avg_first_damage,
        "avg_first_damage_time": f"{int(avg_first_damage // 60)}:{int(avg_first_damage % 60):02d}"
        if avg_first_damage
        else None,
        "avg_damage_distribution": avg_damage_dist,
        "preferred_attack_timing_minute": preferred_timing[0]
        if preferred_timing
        else None,
        "timing_attack_frequency": dict(timing_attacks_by_time),
        "archetype": player.primary_archetype,
        "aggression_score": player.avg_aggression_score,
    }
