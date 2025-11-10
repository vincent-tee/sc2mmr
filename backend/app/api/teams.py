"""
API endpoints for team balancing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from itertools import combinations

from ..database import get_db
from ..balancer import TeamBalancer, BalancerStats
from ..rating_models import RatingModel, RatingModelService, PlayerRating, ModelComparison, get_model_description
from ..models import Player, MatchPlayer


router = APIRouter(prefix="/teams", tags=["teams"])


# Request/Response models
class BalanceTeamsRequest(BaseModel):
    """Request to balance teams."""
    player_ids: List[int]
    top_n: int = 10


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


class TeamSuggestionResponse(BaseModel):
    """Team suggestion response."""
    team_1: TeamInfo
    team_2: TeamInfo
    mmr_difference: float
    match_quality: float
    win_probability_team_1: float
    win_probability_team_2: float
    fairness_rating: str


@router.post("/balance", response_model=List[TeamSuggestionResponse])
def balance_teams(
    request: BalanceTeamsRequest,
    db: Session = Depends(get_db)
):
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
    # Validate even number of players
    if len(request.player_ids) % 2 != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Need even number of players, got {len(request.player_ids)}"
        )

    # Validate supported game modes
    num_players = len(request.player_ids)
    if num_players not in [6, 8, 10]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported number of players: {num_players}. "
                   "Must be 6 (3v3), 8 (4v4), or 10 (5v5)"
        )

    try:
        # Generate team suggestions
        suggestions = TeamBalancer.balance_teams(
            db,
            request.player_ids,
            top_n=request.top_n
        )

        # Convert to response format
        responses = []
        for suggestion in suggestions:
            # Get detailed analysis
            analysis = BalancerStats.analyze_suggestion(suggestion)

            # Build team 1 info
            team_1_players = [
                PlayerInfo(
                    id=p['id'],
                    name=p['name'],
                    mmr=p['mmr'],
                    mu=p['mu'],
                    sigma=p['sigma']
                )
                for p in [
                    {
                        'id': player.id,
                        'name': player.name,
                        'mmr': player.mmr,
                        'mu': player.mu,
                        'sigma': player.sigma
                    }
                    for player in suggestion.team_1
                ]
            ]

            team_1_info = TeamInfo(
                players=team_1_players,
                total_mmr=analysis['team_1']['total_mmr'],
                avg_mmr=analysis['team_1']['avg_mmr']
            )

            # Build team 2 info
            team_2_players = [
                PlayerInfo(
                    id=p['id'],
                    name=p['name'],
                    mmr=p['mmr'],
                    mu=p['mu'],
                    sigma=p['sigma']
                )
                for p in [
                    {
                        'id': player.id,
                        'name': player.name,
                        'mmr': player.mmr,
                        'mu': player.mu,
                        'sigma': player.sigma
                    }
                    for player in suggestion.team_2
                ]
            ]

            team_2_info = TeamInfo(
                players=team_2_players,
                total_mmr=analysis['team_2']['total_mmr'],
                avg_mmr=analysis['team_2']['avg_mmr']
            )

            # Create response
            responses.append(TeamSuggestionResponse(
                team_1=team_1_info,
                team_2=team_2_info,
                mmr_difference=analysis['balance']['mmr_difference'],
                match_quality=analysis['balance']['match_quality'],
                win_probability_team_1=analysis['balance']['win_probability_team_1'],
                win_probability_team_2=analysis['balance']['win_probability_team_2'],
                fairness_rating=analysis['balance']['fairness_rating']
            ))

        return responses

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/quick-balance", response_model=TeamSuggestionResponse)
def quick_balance(
    request: BalanceTeamsRequest,
    db: Session = Depends(get_db)
):
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
        raise HTTPException(status_code=500, detail="Failed to generate team suggestions")

    return suggestions[0]


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
    request: BalanceWithModelRequest,
    db: Session = Depends(get_db)
):
    """
    Balance teams using a specific rating model.

    Available models:
    - trueskill: Pure TrueSkill (win/loss only)
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
            detail=f"Invalid model: {request.model}. Valid options: {[m.value for m in RatingModel]}"
        )

    # Validate even number of players
    if len(request.player_ids) % 2 != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Need even number of players, got {len(request.player_ids)}"
        )

    # Get player ratings
    all_ratings = RatingModelService.get_all_player_ratings(db, request.player_ids)

    if len(all_ratings) != len(request.player_ids):
        found_ids = {r.player_id for r in all_ratings}
        missing_ids = set(request.player_ids) - found_ids
        raise HTTPException(
            status_code=404,
            detail=f"Players not found: {missing_ids}"
        )

    # Generate all possible team splits
    team_size = len(request.player_ids) // 2
    best_balance = None
    best_quality = -1

    for team1_indices in combinations(range(len(all_ratings)), team_size):
        team1_ratings = [all_ratings[i] for i in team1_indices]
        team2_ratings = [all_ratings[i] for i in range(len(all_ratings)) if i not in team1_indices]

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
            'id': r.player_id,
            'name': r.player_name,
            'rating': r.get_rating(model),
            'trueskill_mmr': r.trueskill_mmr,
            'impact_score': r.overall_impact
        }
        for r in team1_ratings
    ]

    team2_players = [
        {
            'id': r.player_id,
            'name': r.player_name,
            'rating': r.get_rating(model),
            'trueskill_mmr': r.trueskill_mmr,
            'impact_score': r.overall_impact
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
        win_confidence=confidence
    )


@router.post("/compare-models")
def compare_balance_models(
    request: BalanceWithModelRequest,
    db: Session = Depends(get_db)
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
        raise HTTPException(
            status_code=404,
            detail=f"Players not found: {missing_ids}"
        )

    # Compare all models
    results = {}

    for model in RatingModel:
        # Find best balance for this model
        team_size = len(request.player_ids) // 2
        best_balance = None
        best_quality = -1

        for team1_indices in combinations(range(len(all_ratings)), team_size):
            team1_ratings = [all_ratings[i] for i in team1_indices]
            team2_ratings = [all_ratings[i] for i in range(len(all_ratings)) if i not in team1_indices]

            quality = RatingModelService.calculate_match_quality(
                team1_ratings, team2_ratings, model
            )

            if quality > best_quality:
                best_quality = quality
                best_balance = (team1_ratings, team2_ratings)

        if best_balance:
            team1_ratings, team2_ratings = best_balance

            team1_rating = RatingModelService.calculate_team_rating(team1_ratings, model)
            team2_rating = RatingModelService.calculate_team_rating(team2_ratings, model)

            predicted_winner, confidence = RatingModelService.predict_match_winner(
                team1_ratings, team2_ratings, model
            )

            results[model.value] = {
                'model': model.value,
                'description': get_model_description(model),
                'team_1': [r.player_name for r in team1_ratings],
                'team_2': [r.player_name for r in team2_ratings],
                'team_1_rating': team1_rating,
                'team_2_rating': team2_rating,
                'match_quality': best_quality,
                'predicted_winner': predicted_winner,
                'confidence': confidence
            }

    return {
        'player_count': len(request.player_ids),
        'models_compared': len(results),
        'results': results
    }


@router.get("/models")
def list_available_models():
    """
    List all available rating models with descriptions.

    Returns:
        List of models and descriptions
    """
    return {
        'models': [
            {
                'name': model.value,
                'description': get_model_description(model)
            }
            for model in RatingModel
        ]
    }
