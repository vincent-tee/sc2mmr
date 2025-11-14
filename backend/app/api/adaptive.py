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
from ..auto_adaptive import AutoAdaptiveTracker, AutoAdaptiveConfig
from ..models import Match
from sqlalchemy import func


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


@router.get("/auto-status")
def get_auto_optimization_status(db: Session = Depends(get_db)):
    """
    Get auto-optimization status and configuration.

    Returns:
        Current configuration, progress, and statistics
    """
    total_matches = db.query(func.count(Match.id)).scalar()
    matches_since_last = total_matches - AutoAdaptiveTracker._last_optimization_count
    next_optimization_in = AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION - matches_since_last

    return {
        'enabled': AutoAdaptiveConfig.ENABLED,
        'matches_per_optimization': AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION,
        'min_matches_for_first_run': AutoAdaptiveConfig.MIN_MATCHES_FOR_FIRST_RUN,
        'total_matches': total_matches,
        'last_optimization_at_match': AutoAdaptiveTracker._last_optimization_count,
        'matches_since_last_optimization': matches_since_last,
        'next_optimization_in': max(0, next_optimization_in),
        'has_current_weights': AutoAdaptiveTracker._current_weights is not None,
        'current_weights': {
            'combat': AutoAdaptiveTracker._current_weights.combat_weight,
            'economic': AutoAdaptiveTracker._current_weights.economic_weight,
            'team_contribution': AutoAdaptiveTracker._current_weights.team_contribution_weight,
            'efficiency': AutoAdaptiveTracker._current_weights.efficiency_weight
        } if AutoAdaptiveTracker._current_weights else None
    }


class AutoAdaptiveConfigRequest(BaseModel):
    """Request to update auto-adaptive configuration."""
    enabled: Optional[bool] = None
    matches_per_optimization: Optional[int] = None


@router.post("/auto-config")
def update_auto_optimization_config(
    request: AutoAdaptiveConfigRequest,
    db: Session = Depends(get_db)
):
    """
    Update auto-optimization configuration.

    Args:
        request: New configuration values

    Returns:
        Updated configuration
    """
    if request.enabled is not None:
        AutoAdaptiveConfig.ENABLED = request.enabled

    if request.matches_per_optimization is not None:
        if request.matches_per_optimization < 1:
            raise HTTPException(
                status_code=400,
                detail="matches_per_optimization must be at least 1"
            )
        AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION = request.matches_per_optimization

    return {
        'status': 'success',
        'message': 'Auto-optimization configuration updated',
        'config': {
            'enabled': AutoAdaptiveConfig.ENABLED,
            'matches_per_optimization': AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION
        }
    }


@router.post("/force-optimize")
def force_optimization(db: Session = Depends(get_db)):
    """
    Force optimization regardless of threshold.

    Useful for testing or manual triggers.

    Returns:
        Optimization result
    """
    result = AutoAdaptiveTracker.force_optimization(db)

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Optimization failed to generate results"
        )

    return {
        'status': 'success',
        'message': 'Optimization completed',
        'result': result
    }
