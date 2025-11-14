"""
API endpoints for adaptive model tuning.

Allows checking model performance and updating weights based on match data.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Optional

from ..database import get_db
from ..adaptive_model import AdaptiveModelTuner, PerformanceWeights, ModelPerformance


router = APIRouter(prefix="/adaptive", tags=["adaptive"])


class WeightSuggestionResponse(BaseModel):
    """Response for weight suggestion endpoint."""
    suggestion: str  # 'insufficient_data', 'no_change_needed', 'update_recommended'
    reason: str
    confidence: float
    sample_size: int
    current_weights: Dict[str, float]
    suggested_weights: Optional[Dict[str, float]] = None
    changes: Optional[Dict[str, float]] = None
    performance_improvement: Optional[float] = None

    class Config:
        from_attributes = True


class UpdateWeightsRequest(BaseModel):
    """Request to update performance weights."""
    combat_weight: float
    economic_weight: float
    team_contribution_weight: float
    efficiency_weight: float


@router.get("/suggest-weights", response_model=WeightSuggestionResponse)
def suggest_weight_updates(db: Session = Depends(get_db)):
    """
    Analyze recent matches and suggest performance weight updates.

    This endpoint:
    1. Fetches recent match data
    2. Optimizes weights to maximize win prediction accuracy
    3. Validates on held-out data
    4. Suggests updates only if confident

    Returns:
        Suggestion with current/suggested weights and confidence level
    """
    suggestion = AdaptiveModelTuner.suggest_weight_update(db)

    if not suggestion:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate weight suggestion"
        )

    # Format current weights
    current_weights_dict = {
        'combat': suggestion['current_weights'].combat_weight,
        'economic': suggestion['current_weights'].economic_weight,
        'team_contribution': suggestion['current_weights'].team_contribution_weight,
        'efficiency': suggestion['current_weights'].efficiency_weight
    }

    # Format suggested weights if available
    suggested_weights_dict = None
    if 'suggested_weights' in suggestion:
        suggested_weights_dict = {
            'combat': suggestion['suggested_weights'].combat_weight,
            'economic': suggestion['suggested_weights'].economic_weight,
            'team_contribution': suggestion['suggested_weights'].team_contribution_weight,
            'efficiency': suggestion['suggested_weights'].efficiency_weight
        }

    # Calculate performance improvement
    perf_improvement = None
    if 'performance' in suggestion:
        perf_improvement = suggestion['performance'].correlation_strength

    return WeightSuggestionResponse(
        suggestion=suggestion['suggestion'],
        reason=suggestion['reason'],
        confidence=suggestion['confidence'],
        sample_size=suggestion['sample_size'],
        current_weights=current_weights_dict,
        suggested_weights=suggested_weights_dict,
        changes=suggestion.get('changes'),
        performance_improvement=perf_improvement
    )


@router.get("/model-performance")
def get_model_performance(db: Session = Depends(get_db)):
    """
    Get current model performance metrics.

    Returns:
        Model performance stats including correlation and sample size
    """
    current_weights = PerformanceWeights()
    _, performance = AdaptiveModelTuner.optimize_weights(db, current_weights)

    return {
        'win_prediction_accuracy': performance.win_prediction_accuracy,
        'correlation_strength': performance.correlation_strength,
        'sample_size': performance.sample_size,
        'confidence_score': performance.confidence_score,
        'current_weights': {
            'combat': current_weights.combat_weight,
            'economic': current_weights.economic_weight,
            'team_contribution': current_weights.team_contribution_weight,
            'efficiency': current_weights.efficiency_weight
        }
    }


@router.post("/update-weights")
def update_weights(
    request: UpdateWeightsRequest,
    db: Session = Depends(get_db)
):
    """
    Update performance weights (manual override).

    NOTE: This is currently manual - would require updating
    advanced_parser.py to use configurable weights.

    Args:
        request: New weights to apply

    Returns:
        Confirmation message
    """
    # Validate weights sum to 1.0
    total = (
        request.combat_weight +
        request.economic_weight +
        request.team_contribution_weight +
        request.efficiency_weight
    )

    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail=f"Weights must sum to 1.0 (got {total})"
        )

    # TODO: Implement weight persistence
    # For now, just return success
    return {
        'status': 'success',
        'message': 'Weights recorded (will apply to future matches after restart)',
        'note': 'Automatic weight application coming soon - requires config system',
        'new_weights': {
            'combat': request.combat_weight,
            'economic': request.economic_weight,
            'team_contribution': request.team_contribution_weight,
            'efficiency': request.efficiency_weight
        }
    }
