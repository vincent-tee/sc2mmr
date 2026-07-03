"""
API endpoints for team balancing.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from itertools import combinations

from ..database import get_db
from ..balancer import TeamBalancer, BalancerStats
from ..models import Player, MatchPlayer, PlayerSynergy
from ..services.ai_mmr_service import get_ai_mmr, get_all_ai_difficulties
from ..services.adaptive_balancer import ComponentAccuracyTracker


router = APIRouter(prefix="/teams", tags=["teams"])


# Request/Response models
class BalanceTeamsRequest(BaseModel):
    """Request to balance teams."""

    player_ids: List[int]
    top_n: int = 10
    map_name: Optional[str] = None
    ai_difficulty: Optional[str] = (
        None  # "easy", "medium", "hard", "very_hard", "elite"
    )


class PlayerInfo(BaseModel):
    """Player information in team suggestion."""

    id: int
    name: str
    mmr: float
    unified_mmr: Optional[float] = None
    mu: float
    sigma: float


class TeamInfo(BaseModel):
    """Team information."""

    players: List[PlayerInfo]
    total_mmr: float
    avg_mmr: float
    has_ai: bool = False
    ai_mmr: Optional[float] = None


class TeamSuggestionResponse(BaseModel):
    """Team suggestion response."""

    team_1: TeamInfo
    team_2: TeamInfo
    mmr_difference: float
    match_quality: float
    win_probability_team_1: float
    win_probability_team_2: float
    fairness_rating: str
    team_1_avg_impact: float = 0.0
    team_2_avg_impact: float = 0.0
    impact_balance_score: float = 1.0
    impact_difference: float = 0.0


class CustomPlayerInfo(BaseModel):
    """Information for a custom (non-DB) player."""

    name: str
    mmr: float = 1000.0
    mu: float = 25.0
    sigma: float = 8.333
    overall_impact: float = 50.0
    total_games: int = 0


class BalanceWithCustomPlayersRequest(BaseModel):
    """Request to balance teams with both DB and custom players."""

    player_ids: List[int]
    custom_players: List[CustomPlayerInfo]
    top_n: int = 3


@router.post(
    "/balance-with-custom-players", response_model=List[TeamSuggestionResponse]
)
def balance_with_custom_players(
    request: BalanceWithCustomPlayersRequest, db: Session = Depends(get_db)
):
    """
    Balance teams using a mix of database players and custom (guest) players.
    """
    from ..balancer import PlayerInfo as BalancerPlayerInfo

    # Get DB players
    db_players = db.query(Player).filter(Player.id.in_(request.player_ids)).all()
    player_infos = [BalancerPlayerInfo.from_player(p) for p in db_players]

    # Add custom players
    for idx, cp in enumerate(request.custom_players):
        player_infos.append(
            BalancerPlayerInfo(
                id=-(idx + 1),  # Negative IDs for custom players
                name=cp.name,
                mu=cp.mu,
                sigma=cp.sigma,
                mmr=cp.mmr,
                overall_impact=cp.overall_impact,
                total_games=cp.total_games,
            )
        )

    if len(player_infos) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players total")

    # Fetch synergy data
    from ..models import GroupSynergy

    synergies = (
        db.query(GroupSynergy).filter(GroupSynergy.player_count.in_([2, 3])).all()
    )
    synergy_map = {s.player_ids_key: s.synergy_score for s in synergies}

    # Generate suggestions
    suggestions = TeamBalancer.generate_team_suggestions(
        player_infos, top_n=request.top_n, synergy_data=synergy_map
    )

    # Convert to response format
    responses = []
    for suggestion in suggestions:
        analysis = BalancerStats.analyze_suggestion(suggestion)

        def to_player_info(p: BalancerPlayerInfo) -> PlayerInfo:
            return PlayerInfo(
                id=p.id,
                name=p.name,
                mmr=p.mmr,
                unified_mmr=p.unified_mmr,
                mu=p.mu,
                sigma=p.sigma,
            )

        responses.append(
            TeamSuggestionResponse(
                team_1=TeamInfo(
                    players=[to_player_info(p) for p in suggestion.team_1],
                    total_mmr=analysis["team_1"]["total_mmr"],
                    avg_mmr=analysis["team_1"]["avg_mmr"],
                ),
                team_2=TeamInfo(
                    players=[to_player_info(p) for p in suggestion.team_2],
                    total_mmr=analysis["team_2"]["total_mmr"],
                    avg_mmr=analysis["team_2"]["avg_mmr"],
                ),
                mmr_difference=analysis["balance"]["mmr_difference"],
                match_quality=analysis["balance"]["match_quality"],
                win_probability_team_1=analysis["balance"]["win_probability_team_1"],
                win_probability_team_2=analysis["balance"]["win_probability_team_2"],
                fairness_rating=analysis["balance"]["fairness_rating"],
                team_1_avg_impact=analysis["balance"]["team_1_avg_impact"],
                team_2_avg_impact=analysis["balance"]["team_2_avg_impact"],
                impact_balance_score=analysis["balance"]["impact_balance_score"],
                impact_difference=analysis["balance"]["impact_difference"],
            )
        )

    return responses


@router.post("/balance", response_model=List[TeamSuggestionResponse])
def balance_teams(request: BalanceTeamsRequest, db: Session = Depends(get_db)):
    """
    Generate balanced team suggestions for given players.

    This is the PRIMARY FEATURE of the application.

    Args:
        request: BalanceTeamsRequest with player IDs
        db: Database session

    Returns:
        List of TeamSuggestionResponse objects, sorted by balance quality

    Raises:
        HTTPException: If invalid number of players or players not found
    """
    # Validate minimum players
    num_players = len(request.player_ids)
    if num_players < 2:
        raise HTTPException(
            status_code=400, detail=f"Need at least 2 players, got {num_players}"
        )

    # Maximum reasonable limit
    if num_players > 20:
        raise HTTPException(
            status_code=400,
            detail=f"Too many players: {num_players}. Maximum is 20 players (10v10)",
        )

    try:
        # Generate team suggestions
        suggestions = TeamBalancer.balance_teams(
            db, request.player_ids, top_n=request.top_n, map_name=request.map_name
        )

        # Convert to response format
        responses = []
        for suggestion in suggestions:
            # Get detailed analysis
            analysis = BalancerStats.analyze_suggestion(suggestion)

            # Build team 1 info
            team_1_players = [
                PlayerInfo(
                    id=player.id,
                    name=player.name,
                    mmr=player.mmr,
                    unified_mmr=player.unified_mmr,
                    mu=player.mu,
                    sigma=player.sigma,
                )
                for player in suggestion.team_1
            ]

            team_1_info = TeamInfo(
                players=team_1_players,
                total_mmr=analysis["team_1"]["total_mmr"],
                avg_mmr=analysis["team_1"]["avg_mmr"],
            )

            # Build team 2 info
            team_2_players = [
                PlayerInfo(
                    id=player.id,
                    name=player.name,
                    mmr=player.mmr,
                    unified_mmr=player.unified_mmr,
                    mu=player.mu,
                    sigma=player.sigma,
                )
                for player in suggestion.team_2
            ]

            team_2_info = TeamInfo(
                players=team_2_players,
                total_mmr=analysis["team_2"]["total_mmr"],
                avg_mmr=analysis["team_2"]["avg_mmr"],
            )

            # Create response
            responses.append(
                TeamSuggestionResponse(
                    team_1=team_1_info,
                    team_2=team_2_info,
                    mmr_difference=analysis["balance"]["mmr_difference"],
                    match_quality=analysis["balance"]["match_quality"],
                    win_probability_team_1=analysis["balance"][
                        "win_probability_team_1"
                    ],
                    win_probability_team_2=analysis["balance"][
                        "win_probability_team_2"
                    ],
                    fairness_rating=analysis["balance"]["fairness_rating"],
                    team_1_avg_impact=analysis["balance"]["team_1_avg_impact"],
                    team_2_avg_impact=analysis["balance"]["team_2_avg_impact"],
                    impact_balance_score=analysis["balance"]["impact_balance_score"],
                    impact_difference=analysis["balance"]["impact_difference"],
                )
            )

        return responses

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/quick-balance", response_model=TeamSuggestionResponse)
def quick_balance(request: BalanceTeamsRequest, db: Session = Depends(get_db)):
    """
    Get the single best balanced team composition.

    Args:
        request: BalanceTeamsRequest with player IDs
        db: Database session

    Returns:
        Single best TeamSuggestionResponse

    Raises:
        HTTPException: If invalid number of players or players not found
    """
    # Use the balance_teams endpoint with top_n=1
    request.top_n = 1
    suggestions = balance_teams(request, db)

    if not suggestions:
        raise HTTPException(
            status_code=500, detail="Failed to generate team suggestions"
        )

    return suggestions[0]


# =============================================================================
# AI-Aware Balancing Endpoint
# =============================================================================


class BalanceWithAIRequest(BaseModel):
    """Request to balance teams with an AI player."""

    player_ids: List[int]
    ai_difficulty: str = (
        "hard"  # "very_easy", "easy", "medium", "hard", "very_hard", "elite"
    )


class AIBalanceResponse(BaseModel):
    """Team balance response with AI placement info."""

    team_1: TeamInfo
    team_2: TeamInfo
    mmr_difference: float
    match_quality: float
    win_probability_team_1: float
    win_probability_team_2: float
    fairness_rating: str
    ai_info: dict  # Details about the AI placement


@router.post("/balance-with-ai", response_model=AIBalanceResponse)
def balance_teams_with_ai(request: BalanceWithAIRequest, db: Session = Depends(get_db)):
    """
    Balance teams including an AI player slot.

    The AI is treated as a virtual player with a fixed MMR based on difficulty.
    It will be placed on the team that needs it most to balance the match.

    Args:
        request: BalanceWithAIRequest with player IDs and AI difficulty
        db: Database session

    Returns:
        AIBalanceResponse with balanced teams and AI placement info
    """
    from ..balancer import PlayerInfo as BalancerPlayerInfo

    # Validate AI difficulty
    ai_mmr = get_ai_mmr(request.ai_difficulty)
    available = get_all_ai_difficulties()

    if request.ai_difficulty.lower() not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid AI difficulty. Available: {list(available.keys())}",
        )

    # Get human players
    players = db.query(Player).filter(Player.id.in_(request.player_ids)).all()

    if len(players) != len(request.player_ids):
        found_ids = {p.id for p in players}
        missing = set(request.player_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"Players not found: {missing}")

    # Convert to balancer format
    player_infos = [BalancerPlayerInfo.from_player(p) for p in players]

    # Calculate total MMR for each potential team split
    num_total = len(player_infos) + 1  # +1 for AI

    # Determine team sizes (AI makes it even or stays uneven)
    if num_total % 2 == 0:
        team_1_size_humans = num_total // 2
    else:
        team_1_size_humans = (num_total // 2) + 1

    # Try all combinations with AI on each team
    best_balance = None
    best_quality = -1
    best_ai_team = None

    # Option 1: AI on Team 1
    for team1_size in range(1, len(player_infos)):
        for team1_indices in combinations(range(len(player_infos)), team1_size):
            team1_humans = [player_infos[i] for i in team1_indices]
            team2_humans = [
                player_infos[i]
                for i in range(len(player_infos))
                if i not in team1_indices
            ]

            # Try AI on Team 1
            team1_mmr_with_ai = sum(p.mmr for p in team1_humans) + ai_mmr
            team2_mmr = sum(p.mmr for p in team2_humans)
            diff_ai_t1 = abs(team1_mmr_with_ai - team2_mmr)

            # Try AI on Team 2
            team1_mmr = sum(p.mmr for p in team1_humans)
            team2_mmr_with_ai = sum(p.mmr for p in team2_humans) + ai_mmr
            diff_ai_t2 = abs(team1_mmr - team2_mmr_with_ai)

            # Pick better option
            if diff_ai_t1 < diff_ai_t2:
                quality = 1.0 / (1.0 + diff_ai_t1 / 1000)  # Simple quality metric
                if quality > best_quality:
                    best_quality = quality
                    best_balance = (team1_humans, team2_humans)
                    best_ai_team = 1
            else:
                quality = 1.0 / (1.0 + diff_ai_t2 / 1000)
                if quality > best_quality:
                    best_quality = quality
                    best_balance = (team1_humans, team2_humans)
                    best_ai_team = 2

    if not best_balance:
        raise HTTPException(status_code=500, detail="Failed to balance teams")

    team1_humans, team2_humans = best_balance

    # Calculate final MMRs
    if best_ai_team == 1:
        team1_total = sum(p.mmr for p in team1_humans) + ai_mmr
        team2_total = sum(p.mmr for p in team2_humans)
        team1_count = len(team1_humans) + 1
        team2_count = len(team2_humans)
    else:
        team1_total = sum(p.mmr for p in team1_humans)
        team2_total = sum(p.mmr for p in team2_humans) + ai_mmr
        team1_count = len(team1_humans)
        team2_count = len(team2_humans) + 1

    # Calculate win probability (simplified)
    total_mmr = team1_total + team2_total
    win_prob_t1 = team1_total / total_mmr if total_mmr > 0 else 0.5

    # Build response
    team1_player_infos = [
        PlayerInfo(id=p.id, name=p.name, mmr=p.mmr, mu=p.mu, sigma=p.sigma)
        for p in team1_humans
    ]
    team2_player_infos = [
        PlayerInfo(id=p.id, name=p.name, mmr=p.mmr, mu=p.mu, sigma=p.sigma)
        for p in team2_humans
    ]

    mmr_diff = abs(team1_total - team2_total)

    # Fairness rating
    if mmr_diff < 50:
        fairness = "Excellent"
    elif mmr_diff < 150:
        fairness = "Good"
    elif mmr_diff < 300:
        fairness = "Fair"
    else:
        fairness = "Unbalanced"

    return AIBalanceResponse(
        team_1=TeamInfo(
            players=team1_player_infos,
            total_mmr=team1_total,
            avg_mmr=team1_total / team1_count,
            has_ai=(best_ai_team == 1),
            ai_mmr=ai_mmr if best_ai_team == 1 else None,
        ),
        team_2=TeamInfo(
            players=team2_player_infos,
            total_mmr=team2_total,
            avg_mmr=team2_total / team2_count,
            has_ai=(best_ai_team == 2),
            ai_mmr=ai_mmr if best_ai_team == 2 else None,
        ),
        mmr_difference=mmr_diff,
        match_quality=best_quality,
        win_probability_team_1=round(win_prob_t1 * 100, 1),
        win_probability_team_2=round((1 - win_prob_t1) * 100, 1),
        fairness_rating=fairness,
        ai_info={
            "difficulty": request.ai_difficulty,
            "mmr": ai_mmr,
            "placed_on_team": best_ai_team,
            "reason": f"AI placed on Team {best_ai_team} to minimize MMR difference",
        },
    )


@router.get("/ai-difficulties")
def list_ai_difficulties():
    """List available AI difficulty levels and their MMR values."""
    return {
        "difficulties": get_all_ai_difficulties(),
        "config_path": "backend/config/ai_mmr.json",
        "note": "Edit the config file to recalibrate AI MMR values",
    }


# Match Prediction Endpoint (Phase 1 Feature)
# =============================================================================


class PredictMatchRequest(BaseModel):
    """Request to predict match outcome."""

    team_1_ids: List[int]
    team_2_ids: List[int]


class SynergyInfo(BaseModel):
    """Synergy information between two players."""

    player1_name: str
    player2_name: str
    games_together: int
    win_rate: float
    synergy_score: float


class TeamPredictionInfo(BaseModel):
    """Detailed team prediction info."""

    players: List[PlayerInfo]
    total_mmr: float
    avg_mmr: float
    win_probability: float
    synergies: List[SynergyInfo]
    avg_synergy_score: float
    team_chemistry: str  # "Strong", "Average", "Weak", "Unknown"


class MatchPredictionResponse(BaseModel):
    """Enhanced match prediction response."""

    team_1: TeamPredictionInfo
    team_2: TeamPredictionInfo
    predicted_winner: int  # 1 or 2
    confidence: str  # "High", "Medium", "Low"
    upset_potential: bool  # True if underdog has good synergy
    match_quality: float
    factors: List[str]  # Explanation of prediction factors


@router.post("/predict", response_model=MatchPredictionResponse)
def predict_match(request: PredictMatchRequest, db: Session = Depends(get_db)):
    """
    Predict match outcome with detailed analysis.

    Factors in:
    - Team MMR difference
    - Player synergies (historical performance together)
    - Match quality (how competitive the match should be)

    Args:
        request: Teams to predict
        db: Database session

    Returns:
        Detailed match prediction with confidence and factors
    """
    from ..balancer import TeamBalancer
    from ..balancer import PlayerInfo as BalancerPlayerInfo

    # Get players
    team_1_players = db.query(Player).filter(Player.id.in_(request.team_1_ids)).all()
    team_2_players = db.query(Player).filter(Player.id.in_(request.team_2_ids)).all()

    if len(team_1_players) != len(request.team_1_ids):
        raise HTTPException(status_code=404, detail="Some team 1 players not found")
    if len(team_2_players) != len(request.team_2_ids):
        raise HTTPException(status_code=404, detail="Some team 2 players not found")

    # Convert to balancer format
    t1_info = [BalancerPlayerInfo.from_player(p) for p in team_1_players]
    t2_info = [BalancerPlayerInfo.from_player(p) for p in team_2_players]

    # Calculate base predictions
    win_prob_t1 = TeamBalancer.calculate_win_probability(t1_info, t2_info)
    match_quality = TeamBalancer.calculate_match_quality(t1_info, t2_info)

    # Get synergies for each team
    def get_team_synergies(players: List[Player]) -> tuple:
        synergies = []
        total_score = 0
        count = 0

        for i, p1 in enumerate(players):
            for p2 in players[i + 1 :]:
                # Ensure player1_id < player2_id for lookup
                pid1, pid2 = min(p1.id, p2.id), max(p1.id, p2.id)
                syn = (
                    db.query(PlayerSynergy)
                    .filter(
                        PlayerSynergy.player1_id == pid1,
                        PlayerSynergy.player2_id == pid2,
                    )
                    .first()
                )

                if syn and syn.games_together >= 3:
                    wr = (
                        syn.wins_together / syn.games_together
                        if syn.games_together > 0
                        else 0.5
                    )
                    synergies.append(
                        SynergyInfo(
                            player1_name=p1.name if p1.id == pid1 else p2.name,
                            player2_name=p2.name if p2.id == pid2 else p1.name,
                            games_together=syn.games_together,
                            win_rate=round(wr * 100, 1),
                            synergy_score=round(syn.synergy_score, 1),
                        )
                    )
                    total_score += syn.synergy_score
                    count += 1

        avg_score = total_score / count if count > 0 else 50.0

        if avg_score >= 52:
            chemistry = "Strong"
        elif avg_score >= 48:
            chemistry = "Average"
        elif count > 0:
            chemistry = "Weak"
        else:
            chemistry = "Unknown"

        return synergies, avg_score, chemistry

    t1_synergies, t1_avg_syn, t1_chem = get_team_synergies(team_1_players)
    t2_synergies, t2_avg_syn, t2_chem = get_team_synergies(team_2_players)

    # Calculate MMR totals
    t1_total_mmr = sum(p.mmr for p in team_1_players)
    t2_total_mmr = sum(p.mmr for p in team_2_players)
    t1_avg_mmr = t1_total_mmr / len(team_1_players)
    t2_avg_mmr = t2_total_mmr / len(team_2_players)

    # Determine prediction factors
    factors = []

    mmr_diff = abs(t1_total_mmr - t2_total_mmr)
    if mmr_diff > 800:
        factors.append(f"Large MMR gap ({mmr_diff:.0f} total difference)")
    elif mmr_diff < 200:
        factors.append("Very close MMR - could go either way")

    if t1_chem == "Strong" and t2_chem != "Strong":
        factors.append("Team 1 has better synergy")
    elif t2_chem == "Strong" and t1_chem != "Strong":
        factors.append("Team 2 has better synergy")

    if match_quality > 0.4:
        factors.append("High match quality - competitive game expected")
    elif match_quality < 0.2:
        factors.append("Low match quality - one-sided match likely")

    # Determine confidence
    if abs(win_prob_t1 - 0.5) > 0.25:
        confidence = "High"
    elif abs(win_prob_t1 - 0.5) > 0.1:
        confidence = "Medium"
    else:
        confidence = "Low"

    # Check for upset potential
    upset_potential = False
    if win_prob_t1 < 0.4 and t1_chem == "Strong":
        upset_potential = True
        factors.append("⚡ Upset alert: Team 1 underdogs have strong chemistry!")
    elif win_prob_t1 > 0.6 and t2_chem == "Strong":
        upset_potential = True
        factors.append("⚡ Upset alert: Team 2 underdogs have strong chemistry!")

    predicted_winner = 1 if win_prob_t1 >= 0.5 else 2

    # Build response
    return MatchPredictionResponse(
        team_1=TeamPredictionInfo(
            players=[
                PlayerInfo(id=p.id, name=p.name, mmr=p.mmr, mu=p.mu, sigma=p.sigma)
                for p in team_1_players
            ],
            total_mmr=round(t1_total_mmr, 1),
            avg_mmr=round(t1_avg_mmr, 1),
            win_probability=round(win_prob_t1 * 100, 1),
            synergies=t1_synergies,
            avg_synergy_score=round(t1_avg_syn, 1),
            team_chemistry=t1_chem,
        ),
        team_2=TeamPredictionInfo(
            players=[
                PlayerInfo(id=p.id, name=p.name, mmr=p.mmr, mu=p.mu, sigma=p.sigma)
                for p in team_2_players
            ],
            total_mmr=round(t2_total_mmr, 1),
            avg_mmr=round(t2_avg_mmr, 1),
            win_probability=round((1 - win_prob_t1) * 100, 1),
            synergies=t2_synergies,
            avg_synergy_score=round(t2_avg_syn, 1),
            team_chemistry=t2_chem,
        ),
        predicted_winner=predicted_winner,
        confidence=confidence,
        upset_potential=upset_potential,
        match_quality=round(match_quality, 3),
        factors=factors if factors else ["Evenly matched teams"],
    )


# =============================================================================
# ML-Optimized Prediction Endpoint (81.1% Accuracy)
# =============================================================================


class MLPredictRequest(BaseModel):
    """Request for ML-optimized prediction."""

    team_1_ids: List[int]
    team_2_ids: List[int]


@router.post("/predict-ml")
def predict_match_ml(request: MLPredictRequest, db: Session = Depends(get_db)):
    """
    Predict match outcome using ML-optimized model (81.1% accuracy).

    This uses a Logistic Regression model trained on match history with
    optimized feature weights. Features include:
    - Recent win rate (most important: 1.85 weight)
    - Win streak momentum (0.54 weight)
    - Economic score (0.31 weight)
    - Combat score (0.22 weight)
    - Overall impact (0.13 weight)
    - Efficiency (0.13 weight)
    - Recency MMR (0.05 weight)

    Args:
        request: Teams to predict
        db: Database session

    Returns:
        ML prediction with confidence and key factors
    """
    from ..services.ml_prediction_service import MLPredictionService

    try:
        prediction = MLPredictionService.predict_match(
            db, request.team_1_ids, request.team_2_ids
        )
        return prediction
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


class BalanceQualityMetrics(BaseModel):
    """Historical balance quality statistics."""

    total_matches: int
    matches_with_data: int
    avg_mmr_difference: float
    median_mmr_difference: float
    pct_within_100: float  # % of matches with MMR diff <= 100
    pct_within_200: float
    pct_within_300: float
    prediction_accuracy: float  # % where higher-MMR team won
    close_game_accuracy: float  # Prediction accuracy on close games
    lopsided_games: int  # Games with > 500 MMR diff
    closest_match: dict
    most_lopsided_match: dict


@router.get("/balance-quality", response_model=BalanceQualityMetrics)
def get_balance_quality_metrics(db: Session = Depends(get_db)):
    """
    Get historical balance quality metrics.

    Analyzes all past matches to show:
    - Average MMR difference between teams
    - % of matches within various thresholds (100, 200, 300 MMR)
    - Prediction accuracy (did higher MMR team win?)
    - Close game vs lopsided game breakdown

    Use this to evaluate how well the balancer is working.

    Returns:
        BalanceQualityMetrics with detailed statistics
    """
    from ..models import Match, MatchPlayer
    import statistics

    # Get all matches with their team compositions
    matches = db.query(Match).filter(Match.played_at.isnot(None)).all()

    match_data = []
    for match in matches:
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )

        team1_players = [mp for mp in match_players if mp.team_number == 1]
        team2_players = [mp for mp in match_players if mp.team_number == 2]

        if not team1_players or not team2_players:
            continue

        # Get player MMRs at time of match (using current MMR as proxy)
        team1_mmr = 0
        team2_mmr = 0

        for mp in team1_players:
            player = db.query(Player).filter(Player.id == mp.player_id).first()
            if player:
                team1_mmr += player.mmr

        for mp in team2_players:
            player = db.query(Player).filter(Player.id == mp.player_id).first()
            if player:
                team2_mmr += player.mmr

        mmr_diff = abs(team1_mmr - team2_mmr)
        team1_won = any(mp.won for mp in team1_players)
        higher_mmr_won = (team1_mmr > team2_mmr) == team1_won

        match_data.append(
            {
                "match_id": match.id,
                "team1_mmr": team1_mmr,
                "team2_mmr": team2_mmr,
                "mmr_diff": mmr_diff,
                "team1_won": team1_won,
                "higher_mmr_won": higher_mmr_won,
                "played_at": match.played_at,
            }
        )

    if not match_data:
        raise HTTPException(status_code=404, detail="No matches found")

    # Calculate metrics
    mmr_diffs = [m["mmr_diff"] for m in match_data]
    avg_diff = statistics.mean(mmr_diffs)
    median_diff = statistics.median(mmr_diffs)

    within_100 = sum(1 for d in mmr_diffs if d < 100) / len(mmr_diffs) * 100
    within_200 = sum(1 for d in mmr_diffs if d < 200) / len(mmr_diffs) * 100
    within_300 = sum(1 for d in mmr_diffs if d < 300) / len(mmr_diffs) * 100

    prediction_acc = (
        sum(1 for m in match_data if m["higher_mmr_won"]) / len(match_data) * 100
    )

    # Close game accuracy (games with < 300 MMR diff)
    close_games = [m for m in match_data if m["mmr_diff"] < 300]
    close_acc = (
        sum(1 for m in close_games if m["higher_mmr_won"]) / len(close_games) * 100
        if close_games
        else 0
    )

    lopsided = sum(1 for d in mmr_diffs if d > 500)

    # Find closest and most lopsided matches
    closest = min(match_data, key=lambda x: x["mmr_diff"])
    most_lopsided = max(match_data, key=lambda x: x["mmr_diff"])

    return BalanceQualityMetrics(
        total_matches=len(matches),
        matches_with_data=len(match_data),
        avg_mmr_difference=round(avg_diff, 1),
        median_mmr_difference=round(median_diff, 1),
        pct_within_100=round(within_100, 1),
        pct_within_200=round(within_200, 1),
        pct_within_300=round(within_300, 1),
        prediction_accuracy=round(prediction_acc, 1),
        close_game_accuracy=round(close_acc, 1),
        lopsided_games=lopsided,
        closest_match={
            "match_id": closest["match_id"],
            "mmr_diff": closest["mmr_diff"],
            "played_at": str(closest["played_at"]) if closest["played_at"] else None,
        },
        most_lopsided_match={
            "match_id": most_lopsided["match_id"],
            "mmr_diff": most_lopsided["mmr_diff"],
            "played_at": str(most_lopsided["played_at"])
            if most_lopsided["played_at"]
            else None,
        },
    )
