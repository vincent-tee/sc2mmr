"""
API endpoints for team balancing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from ..database import get_db
from ..balancer import TeamBalancer, BalancerStats


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
