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
from ..rating_models import (
    RatingModel,
    RatingModelService,
    PlayerRating,
    ModelComparison,
    get_model_description,
)
from ..models import Player, MatchPlayer, PlayerSynergy
from ..services.ai_mmr_service import get_ai_mmr, get_all_ai_difficulties
from ..services.adaptive_balancer import (
    MLMetricsBalancer,
    ComponentAccuracyTracker,
)


router = APIRouter(prefix="/teams", tags=["teams"])


# =============================================================================
# ML Metrics Balancing Request/Response Models
# =============================================================================


class BalanceWithMLMetricsRequest(BaseModel):
    """Request to balance teams using ML metrics."""

    player_ids: List[int]
    use_adaptive_weights: bool = True
    manual_weights: Optional[dict] = None


class MLPlayerBreakdown(BaseModel):
    """Player breakdown with ML component scores."""

    player_id: int
    player_name: str
    session_mmr: float
    combat: float
    economic: float
    efficiency: float
    ml_rating: float
    total_games: int


class TeamMLBreakdown(BaseModel):
    """Team breakdown with ML totals and synergy."""

    players: List[MLPlayerBreakdown]
    total_ml_rating: float
    synergy_bonus: float


class MLBalanceResponse(BaseModel):
    """Response for ML-based team balancing."""

    team_1: TeamMLBreakdown
    team_2: TeamMLBreakdown
    balance_score: float
    weights_used: dict
    component_accuracies: dict
    is_adaptive: bool


# Request/Response models
class BalanceTeamsRequest(BaseModel):
    """Request to balance teams."""

    player_ids: List[int]
    top_n: int = 10
    ai_difficulty: Optional[str] = (
        None  # "easy", "medium", "hard", "very_hard", "elite"
    )


class PlayerInfo(BaseModel):
    """Player information in team suggestion."""

    id: int
    name: str
    mmr: float
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

    # Generate suggestions
    suggestions = TeamBalancer.generate_team_suggestions(
        player_infos, top_n=request.top_n
    )

    # Convert to response format
    responses = []
    for suggestion in suggestions:
        analysis = BalancerStats.analyze_suggestion(suggestion)

        def to_player_info(p: BalancerPlayerInfo) -> PlayerInfo:
            return PlayerInfo(id=p.id, name=p.name, mmr=p.mmr, mu=p.mu, sigma=p.sigma)

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
            db, request.player_ids, top_n=request.top_n
        )

        # Convert to response format
        responses = []
        for suggestion in suggestions:
            # Get detailed analysis
            analysis = BalancerStats.analyze_suggestion(suggestion)

            # Build team 1 info
            team_1_players = [
                PlayerInfo(
                    id=p["id"],
                    name=p["name"],
                    mmr=p["mmr"],
                    mu=p["mu"],
                    sigma=p["sigma"],
                )
                for p in [
                    {
                        "id": player.id,
                        "name": player.name,
                        "mmr": player.mmr,
                        "mu": player.mu,
                        "sigma": player.sigma,
                    }
                    for player in suggestion.team_1
                ]
            ]

            team_1_info = TeamInfo(
                players=team_1_players,
                total_mmr=analysis["team_1"]["total_mmr"],
                avg_mmr=analysis["team_1"]["avg_mmr"],
            )

            # Build team 2 info
            team_2_players = [
                PlayerInfo(
                    id=p["id"],
                    name=p["name"],
                    mmr=p["mmr"],
                    mu=p["mu"],
                    sigma=p["sigma"],
                )
                for p in [
                    {
                        "id": player.id,
                        "name": player.name,
                        "mmr": player.mmr,
                        "mu": player.mu,
                        "sigma": player.sigma,
                    }
                    for player in suggestion.team_2
                ]
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


class BalanceWithImpactRequest(BaseModel):
    """Request to balance teams with impact consideration."""

    player_ids: List[int]
    top_n: int = 10
    impact_weight: float = 0.5  # 0-1: how much to prioritize impact balance


@router.post("/balance-with-impact", response_model=List[TeamSuggestionResponse])
def balance_teams_with_impact(
    request: BalanceWithImpactRequest, db: Session = Depends(get_db)
):
    """
    Balance teams with consideration for high-impact vs low-impact player distribution.

    This ensures each team gets a mix of:
    - Strong players (high MMR, high impact, shot callers)
    - Weaker players (lower MMR, lower impact, learning players)

    Args:
        request: BalanceWithImpactRequest with player IDs and impact weight
        db: Database session

    Returns:
        List of TeamSuggestionResponse objects, sorted by balanced score

    Impact Weight:
        - 0.0 = Pure MMR balance (ignores impact scores)
        - 0.5 = Equal weight to MMR and impact distribution (recommended)
        - 1.0 = Pure impact balance (ignores MMR, only balances impact)

    Raises:
        HTTPException: If invalid number of players or players not found
    """
    # Validate minimum players
    num_players = len(request.player_ids)
    if num_players < 2:
        raise HTTPException(
            status_code=400, detail=f"Need at least 2 players, got {num_players}"
        )

    if num_players > 20:
        raise HTTPException(
            status_code=400,
            detail=f"Too many players: {num_players}. Maximum is 20 players (10v10)",
        )

    # Validate impact_weight
    if not (0 <= request.impact_weight <= 1):
        raise HTTPException(
            status_code=400,
            detail=f"impact_weight must be between 0 and 1, got {request.impact_weight}",
        )

    try:
        # Generate impact-aware team suggestions
        suggestions = TeamBalancer.balance_with_impact_priority(
            db,
            request.player_ids,
            top_n=request.top_n,
            impact_weight=request.impact_weight,
        )

        # Convert to response format (same as balance_teams endpoint)
        responses = []
        for suggestion in suggestions:
            analysis = BalancerStats.analyze_suggestion(suggestion)

            team_1_players = [
                PlayerInfo(
                    id=player.id,
                    name=player.name,
                    mmr=player.mmr,
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

            team_2_players = [
                PlayerInfo(
                    id=player.id,
                    name=player.name,
                    mmr=player.mmr,
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


# Multi-Model Balancing Endpoints


class BalanceWithModelRequest(BaseModel):
    """Request to balance teams using specific rating model."""

    player_ids: List[int]
    model: str = "trueskill"  # trueskill, impact, hybrid_balanced, etc.


class ModelBalanceResponse(BaseModel):
    """Team balance response with model info."""

    model: str
    model_description: str
    team_1: List[dict]
    team_2: List[dict]
    team_1_rating: float
    team_2_rating: float
    rating_difference: float
    match_quality: float
    predicted_winner: int
    win_confidence: float


@router.post("/balance-with-model", response_model=ModelBalanceResponse)
def balance_teams_with_model(
    request: BalanceWithModelRequest, db: Session = Depends(get_db)
):
    """
    Balance teams using a specific rating model.

    Available models:
    - trueskill: Pure TrueSkill (win/loss only)
    - session: Session-weighted MMR (recent matches heavy)
    - impact: Pure performance metrics (100% impact)
    - hybrid_balanced: 50/50 TrueSkill and Impact
    - hybrid_skill_heavy: 70% TrueSkill, 30% Impact
    - hybrid_impact_heavy: 30% TrueSkill, 70% Impact
    - impact_combat: 100% combat score
    - impact_economic: 100% economic score
    - ensemble: Optimized weighted combination

    Args:
        request: BalanceWithModelRequest
        db: Database session

    Returns:
        ModelBalanceResponse with balanced teams

    Raises:
        HTTPException: If invalid model or players not found
    """
    # Validate model
    try:
        model = RatingModel(request.model)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model: {request.model}. Valid options: {[m.value for m in RatingModel]}",
        )

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

    # Get player ratings
    all_ratings = RatingModelService.get_all_player_ratings(db, request.player_ids)

    if len(all_ratings) != len(request.player_ids):
        found_ids = {r.player_id for r in all_ratings}
        missing_ids = set(request.player_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"Players not found: {missing_ids}")

    # Generate all possible team splits
    # Support both even and uneven player counts
    if num_players % 2 == 0:
        team_1_size = num_players // 2
    else:
        team_1_size = (num_players // 2) + 1

    best_balance = None
    best_quality = -1

    for team1_indices in combinations(range(len(all_ratings)), team_1_size):
        team1_ratings = [all_ratings[i] for i in team1_indices]
        team2_ratings = [
            all_ratings[i] for i in range(len(all_ratings)) if i not in team1_indices
        ]

        # Calculate match quality for this split
        quality = RatingModelService.calculate_match_quality(
            team1_ratings, team2_ratings, model
        )

        if quality > best_quality:
            best_quality = quality
            best_balance = (team1_ratings, team2_ratings)

    if not best_balance:
        raise HTTPException(status_code=500, detail="Failed to generate balanced teams")

    team1_ratings, team2_ratings = best_balance

    # Calculate ratings
    team1_rating = RatingModelService.calculate_team_rating(team1_ratings, model)
    team2_rating = RatingModelService.calculate_team_rating(team2_ratings, model)

    # Predict winner
    predicted_winner, confidence = RatingModelService.predict_match_winner(
        team1_ratings, team2_ratings, model
    )

    # Format response
    team1_players = [
        {
            "id": r.player_id,
            "name": r.player_name,
            "rating": r.get_rating(model),
            "trueskill_mmr": r.trueskill_mmr,
            "impact_score": r.overall_impact,
        }
        for r in team1_ratings
    ]

    team2_players = [
        {
            "id": r.player_id,
            "name": r.player_name,
            "rating": r.get_rating(model),
            "trueskill_mmr": r.trueskill_mmr,
            "impact_score": r.overall_impact,
        }
        for r in team2_ratings
    ]

    return ModelBalanceResponse(
        model=model.value,
        model_description=get_model_description(model),
        team_1=team1_players,
        team_2=team2_players,
        team_1_rating=team1_rating,
        team_2_rating=team2_rating,
        rating_difference=abs(team1_rating - team2_rating),
        match_quality=best_quality,
        predicted_winner=predicted_winner,
        win_confidence=confidence,
    )


@router.post("/compare-models")
def compare_balance_models(
    request: BalanceWithModelRequest, db: Session = Depends(get_db)
):
    """
    Compare all rating models for the same set of players.

    Shows how different models would balance the same players,
    helping you choose which model works best for your group.

    Args:
        request: BalanceWithModelRequest (model field ignored)
        db: Database session

    Returns:
        Comparison of all models

    Raises:
        HTTPException: If players not found
    """
    # Get player ratings
    all_ratings = RatingModelService.get_all_player_ratings(db, request.player_ids)

    if len(all_ratings) != len(request.player_ids):
        found_ids = {r.player_id for r in all_ratings}
        missing_ids = set(request.player_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"Players not found: {missing_ids}")

    # Compare all models
    results = {}

    # Determine team sizes (support uneven)
    num_players = len(request.player_ids)
    if num_players % 2 == 0:
        team_1_size = num_players // 2
    else:
        team_1_size = (num_players // 2) + 1

    for model in RatingModel:
        # Find best balance for this model
        best_balance = None
        best_quality = -1

        for team1_indices in combinations(range(len(all_ratings)), team_1_size):
            team1_ratings = [all_ratings[i] for i in team1_indices]
            team2_ratings = [
                all_ratings[i]
                for i in range(len(all_ratings))
                if i not in team1_indices
            ]

            quality = RatingModelService.calculate_match_quality(
                team1_ratings, team2_ratings, model
            )

            if quality > best_quality:
                best_quality = quality
                best_balance = (team1_ratings, team2_ratings)

        if best_balance:
            team1_ratings, team2_ratings = best_balance

            team1_rating = RatingModelService.calculate_team_rating(
                team1_ratings, model
            )
            team2_rating = RatingModelService.calculate_team_rating(
                team2_ratings, model
            )

            predicted_winner, confidence = RatingModelService.predict_match_winner(
                team1_ratings, team2_ratings, model
            )

            results[model.value] = {
                "model": model.value,
                "description": get_model_description(model),
                "team_1": [r.player_name for r in team1_ratings],
                "team_2": [r.player_name for r in team2_ratings],
                "team_1_rating": team1_rating,
                "team_2_rating": team2_rating,
                "match_quality": best_quality,
                "predicted_winner": predicted_winner,
                "confidence": confidence,
            }

    return {
        "player_count": len(request.player_ids),
        "models_compared": len(results),
        "results": results,
    }


@router.get("/models")
def list_available_models():
    """
    List all available rating models with descriptions.

    Returns:
        List of models and descriptions
    """
    return {
        "models": [
            {"name": model.value, "description": get_model_description(model)}
            for model in RatingModel
        ]
    }


# =============================================================================
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


# =============================================================================
# ML Metrics Balancing Endpoint (Session-Weighted + In-Game Metrics + Synergy)
# =============================================================================


@router.post("/balance-with-ml-metrics", response_model=MLBalanceResponse)
def balance_teams_with_ml_metrics(
    request: BalanceWithMLMetricsRequest, db: Session = Depends(get_db)
):
    """
    Balance teams using ML metrics including:
    - Session-weighted MMR (40% default weight)
    - Combat score (25%)
    - Economic score (20%)
    - Efficiency score (15%)
    - Synergy bonus (pairs + trios, max +15)

    Weights can be:
    - Adaptive: Automatically adjusted based on prediction accuracy (recommended)
    - Manual: User-specified custom weights

    Args:
        request: BalanceWithMLMetricsRequest with player IDs and weight preferences
        db: Database session

    Returns:
        MLBalanceResponse with detailed team breakdowns and synergy bonuses
    """
    # Validate minimum players
    num_players = len(request.player_ids)
    if num_players < 2:
        raise HTTPException(
            status_code=400, detail=f"Need at least 2 players, got {num_players}"
        )

    if num_players > 20:
        raise HTTPException(
            status_code=400,
            detail=f"Too many players: {num_players}. Maximum is 20 players (10v10)",
        )

    try:
        # Get balance suggestion
        suggestion = MLMetricsBalancer.balance_teams(
            player_ids=request.player_ids,
            db=db,
            use_adaptive_weights=request.use_adaptive_weights,
            manual_weights=request.manual_weights,
        )

        # Get component accuracies
        components = ["session_mmr", "combat", "economic", "efficiency"]
        accuracies = {
            comp: ComponentAccuracyTracker.get_component_accuracy(comp, db)
            for comp in components
        }

        # Convert to response format
        team_1_players = [
            MLPlayerBreakdown(
                player_id=p.player_id,
                player_name=p.player_name,
                session_mmr=p.session_mmr,
                combat=p.combat,
                economic=p.economic,
                efficiency=p.efficiency,
                ml_rating=p.ml_rating,
                total_games=p.total_games,
            )
            for p in suggestion.team1
        ]

        team_2_players = [
            MLPlayerBreakdown(
                player_id=p.player_id,
                player_name=p.player_name,
                session_mmr=p.session_mmr,
                combat=p.combat,
                economic=p.economic,
                efficiency=p.efficiency,
                ml_rating=p.ml_rating,
                total_games=p.total_games,
            )
            for p in suggestion.team2
        ]

        return MLBalanceResponse(
            team_1=TeamMLBreakdown(
                players=team_1_players,
                total_ml_rating=suggestion.team1_total,
                synergy_bonus=suggestion.team1_synergy,
            ),
            team_2=TeamMLBreakdown(
                players=team_2_players,
                total_ml_rating=suggestion.team2_total,
                synergy_bonus=suggestion.team2_synergy,
            ),
            balance_score=suggestion.balance_score,
            weights_used=suggestion.weights_used,
            component_accuracies=accuracies,
            is_adaptive=request.use_adaptive_weights,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML balancing error: {str(e)}")
