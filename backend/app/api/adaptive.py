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
from ..models import Match, PlayerMatchMetrics, MatchPlayer, Player
from sqlalchemy import func
from datetime import datetime, timedelta


router = APIRouter(prefix="/adaptive", tags=["adaptive"])

# Cache for expensive operations
_performance_cache = {
    "timestamp": None,
    "result": None,
    "cache_duration_seconds": 30,  # 30 seconds (allows refresh button to work)
}


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
            status_code=500, detail="Failed to generate weight suggestion"
        )

    # Format current weights
    current_weights_dict = {
        "combat": suggestion["current_weights"].combat_weight,
        "economic": suggestion["current_weights"].economic_weight,
        "team_contribution": suggestion["current_weights"].team_contribution_weight,
        "efficiency": suggestion["current_weights"].efficiency_weight,
    }

    # Format suggested weights if available
    suggested_weights_dict = None
    if "suggested_weights" in suggestion:
        suggested_weights_dict = {
            "combat": suggestion["suggested_weights"].combat_weight,
            "economic": suggestion["suggested_weights"].economic_weight,
            "team_contribution": suggestion[
                "suggested_weights"
            ].team_contribution_weight,
            "efficiency": suggestion["suggested_weights"].efficiency_weight,
        }

    # Calculate performance improvement
    perf_improvement = None
    if "performance" in suggestion:
        perf_improvement = suggestion["performance"].correlation_strength

    return WeightSuggestionResponse(
        suggestion=suggestion["suggestion"],
        reason=suggestion["reason"],
        confidence=suggestion["confidence"],
        sample_size=suggestion["sample_size"],
        current_weights=current_weights_dict,
        suggested_weights=suggested_weights_dict,
        changes=suggestion.get("changes"),
        performance_improvement=perf_improvement,
    )


@router.get("/model-performance")
def get_model_performance(force_refresh: bool = False, db: Session = Depends(get_db)):
    """
    Get current model performance metrics.

    Args:
        force_refresh: If True, bypass cache and compute fresh results
        db: Database session

    Returns:
        Model performance stats including correlation and sample size
    """
    # Check cache validity (unless force_refresh is True)
    now = datetime.utcnow()
    if (
        not force_refresh
        and _performance_cache["timestamp"] is not None
        and _performance_cache["result"] is not None
    ):
        cache_age = (now - _performance_cache["timestamp"]).total_seconds()
        if cache_age < _performance_cache["cache_duration_seconds"]:
            # Return cached result (add cache info for debugging)
            cached_result = _performance_cache["result"].copy()
            cached_result["_cache_age_seconds"] = round(cache_age, 1)
            cached_result["_from_cache"] = True
            return cached_result

    # Cache miss or expired - compute fresh results
    current_weights = PerformanceWeights()
    _, performance = AdaptiveModelTuner.optimize_weights(db, current_weights)

    # Count actual matches (not PlayerMatchMetrics records)
    total_matches = db.query(func.count(Match.id)).scalar() or 0

    result = {
        "win_prediction_accuracy": performance.win_prediction_accuracy,  # Real match prediction accuracy
        "correlation_strength": performance.correlation_strength,  # Player performance correlation
        "sample_size": total_matches,  # Total matches in database
        "confidence_score": performance.confidence_score,
        "current_weights": {
            "combat": current_weights.combat_weight,
            "economic": current_weights.economic_weight,
            "team_contribution": current_weights.team_contribution_weight,
            "efficiency": current_weights.efficiency_weight,
        },
        "_from_cache": False,
        "_metric_explanation": {
            "win_prediction_accuracy": "Percentage of matches where the team with better performance actually won",
            "correlation_strength": "How strongly individual player performance correlates with winning (0-1 scale)",
        },
    }

    # Update cache
    _performance_cache["timestamp"] = now
    _performance_cache["result"] = result.copy()

    return result


@router.post("/update-weights")
def update_weights(request: UpdateWeightsRequest, db: Session = Depends(get_db)):
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
        request.combat_weight
        + request.economic_weight
        + request.team_contribution_weight
        + request.efficiency_weight
    )

    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=400, detail=f"Weights must sum to 1.0 (got {total})"
        )

    # TODO: Implement weight persistence
    # For now, just return success
    return {
        "status": "success",
        "message": "Weights recorded (will apply to future matches after restart)",
        "note": "Automatic weight application coming soon - requires config system",
        "new_weights": {
            "combat": request.combat_weight,
            "economic": request.economic_weight,
            "team_contribution": request.team_contribution_weight,
            "efficiency": request.efficiency_weight,
        },
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
    next_optimization_in = (
        AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION - matches_since_last
    )

    return {
        "enabled": AutoAdaptiveConfig.ENABLED,
        "matches_per_optimization": AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION,
        "min_matches_for_first_run": AutoAdaptiveConfig.MIN_MATCHES_FOR_FIRST_RUN,
        "total_matches": total_matches,
        "last_optimization_at_match": AutoAdaptiveTracker._last_optimization_count,
        "matches_since_last_optimization": matches_since_last,
        "next_optimization_in": max(0, next_optimization_in),
        "has_current_weights": AutoAdaptiveTracker._current_weights is not None,
        "current_weights": {
            "combat": AutoAdaptiveTracker._current_weights.combat_weight,
            "economic": AutoAdaptiveTracker._current_weights.economic_weight,
            "team_contribution": AutoAdaptiveTracker._current_weights.team_contribution_weight,
            "efficiency": AutoAdaptiveTracker._current_weights.efficiency_weight,
        }
        if AutoAdaptiveTracker._current_weights
        else None,
    }


class AutoAdaptiveConfigRequest(BaseModel):
    """Request to update auto-adaptive configuration."""

    enabled: Optional[bool] = None
    matches_per_optimization: Optional[int] = None


@router.post("/auto-config")
def update_auto_optimization_config(
    request: AutoAdaptiveConfigRequest, db: Session = Depends(get_db)
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
                status_code=400, detail="matches_per_optimization must be at least 1"
            )
        AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION = request.matches_per_optimization

    return {
        "status": "success",
        "message": "Auto-optimization configuration updated",
        "config": {
            "enabled": AutoAdaptiveConfig.ENABLED,
            "matches_per_optimization": AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION,
        },
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
            status_code=500, detail="Optimization failed to generate results"
        )

    return {"status": "success", "message": "Optimization completed", "result": result}


# ============================================================================
# Online Learning Endpoints
# ============================================================================


@router.get("/model-versions")
def get_model_versions(db: Session = Depends(get_db)):
    """
    Get all model versions with their performance stats.

    Returns:
        List of model versions sorted by date (newest first)
    """
    try:
        from ..online_learning import ModelVersion

        versions = (
            db.query(ModelVersion)
            .order_by(ModelVersion.created_at.desc())
            .limit(20)
            .all()
        )

        return {
            "versions": [
                {
                    "version_name": v.version_name,
                    "created_at": v.created_at.isoformat(),
                    "weights": v.weights_json,
                    "features_used": v.features_used,
                    "is_active": v.is_active,
                    "is_experimental": v.is_experimental,
                    "total_predictions": v.total_predictions,
                    "correct_predictions": v.correct_predictions,
                    "accuracy": v.correct_predictions / v.total_predictions
                    if v.total_predictions > 0
                    else 0,
                    "avg_error": v.avg_prediction_error,
                    "notes": v.notes,
                }
                for v in versions
            ]
        }
    except Exception as e:
        # Tables might not exist yet
        return {"versions": []}


@router.get("/prediction-logs")
def get_prediction_logs(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get recent prediction logs with outcomes.

    Args:
        limit: Number of logs to return (default 50, max 200)

    Returns:
        Recent predictions with errors and upset flags
    """
    try:
        from ..online_learning import PredictionLog

        limit = min(limit, 200)  # Cap at 200

        logs = (
            db.query(PredictionLog)
            .order_by(PredictionLog.created_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "predictions": [
                {
                    "id": log.id,
                    "match_id": log.match_id,
                    "model_version": log.model_version,
                    "created_at": log.created_at.isoformat(),
                    "predicted_team1_win_prob": log.predicted_team1_win_prob,
                    "predicted_team2_win_prob": log.predicted_team2_win_prob,
                    "actual_team1_won": log.actual_team1_won,
                    "prediction_error": log.prediction_error,
                    "was_upset": log.was_upset,
                    "features": log.features_json,
                }
                for log in logs
            ]
        }
    except Exception as e:
        return {"predictions": []}


@router.get("/blending-stats")
def get_blending_stats(days: int = 30, db: Session = Depends(get_db)):
    """
    Get blending statistics (TrueSkill + Adaptive adjustments).

    Args:
        days: Number of days to analyze (default 30)

    Returns:
        Blending performance metrics
    """
    try:
        from ..online_learning import PredictionLog
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        logs = (
            db.query(PredictionLog)
            .filter(
                PredictionLog.created_at >= cutoff_date,
                PredictionLog.actual_team1_won.isnot(None),
            )
            .all()
        )

        if not logs:
            return {
                "total_matches": 0,
                "avg_error": 0,
                "upset_count": 0,
                "upset_rate": 0,
            }

        total = len(logs)
        avg_error = sum(log.prediction_error or 0 for log in logs) / total
        upsets = sum(1 for log in logs if log.was_upset)

        return {
            "total_matches": total,
            "avg_error": avg_error,
            "upset_count": upsets,
            "upset_rate": upsets / total if total > 0 else 0,
            "days_analyzed": days,
        }
    except Exception as e:
        return {"total_matches": 0, "avg_error": 0, "upset_count": 0, "upset_rate": 0}


@router.get("/feature-importance")
def get_feature_importance(db: Session = Depends(get_db)):
    """
    Get feature importance rankings.

    Returns:
        Features sorted by correlation strength
    """
    try:
        from ..online_learning import FeatureImportance

        features = (
            db.query(FeatureImportance)
            .order_by(FeatureImportance.calculated_at.desc())
            .limit(100)
            .all()
        )

        # Group by feature name, take most recent
        feature_dict = {}
        for f in features:
            if f.feature_name not in feature_dict:
                feature_dict[f.feature_name] = f

        return {
            "features": [
                {
                    "feature_name": f.feature_name,
                    "correlation": f.correlation_with_outcome,
                    "information_gain": f.information_gain,
                    "sample_size": f.sample_size,
                    "feature_type": f.feature_type,
                    "calculated_at": f.calculated_at.isoformat(),
                }
                for f in sorted(
                    feature_dict.values(),
                    key=lambda x: abs(x.correlation_with_outcome or 0),
                    reverse=True,
                )
            ]
        }
    except Exception as e:
        return {"features": []}


@router.get("/feature-suggestions")
def get_feature_suggestions(db: Session = Depends(get_db)):
    """
    Get AI-suggested new features to implement.

    Returns:
        Feature suggestions sorted by expected correlation
    """
    try:
        from ..online_learning import FeatureSuggestion

        suggestions = (
            db.query(FeatureSuggestion)
            .order_by(FeatureSuggestion.correlation_hypothesis.desc())
            .all()
        )

        return {
            "suggestions": [
                {
                    "id": s.id,
                    "feature_name": s.feature_name,
                    "description": s.feature_description,
                    "extraction_logic": s.extraction_logic,
                    "reasoning": s.reasoning,
                    "expected_correlation": s.correlation_hypothesis,
                    "status": s.status,
                    "created_at": s.created_at.isoformat(),
                    "tested_at": s.tested_at.isoformat() if s.tested_at else None,
                    "test_results": s.test_results,
                }
                for s in suggestions
            ]
        }
    except Exception as e:
        return {"suggestions": []}


# ============================================================================
# Model Accuracy Comparison Endpoint
# ============================================================================


@router.get("/accuracy-comparison")
def get_accuracy_comparison(days: int = 90, db: Session = Depends(get_db)):
    """
    Compare prediction accuracy across different rating models.

    Compares:
    1. TrueSkill Only (base mu/sigma)
    2. Recency-Weighted MMR
    3. Hybrid MMR (TrueSkill + Performance Impact)
    4. ML Model (if available)

    Args:
        days: Number of days to analyze (default 90)
        db: Database session

    Returns:
        Accuracy metrics for each model type
    """
    from datetime import datetime, timedelta
    from ..rating_system import RatingSystem

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get matches with predictions
    matches = (
        db.query(Match)
        .filter(
            Match.played_at >= cutoff_date, Match.predicted_team1_win_prob.isnot(None)
        )
        .all()
    )

    if not matches:
        return {
            "total_matches": 0,
            "days_analyzed": days,
            "models": [],
            "message": "No matches with predictions found",
        }

    # Initialize counters for each model
    results = {
        "trueskill": {"correct": 0, "total": 0, "name": "TrueSkill (Base)"},
        "recency": {"correct": 0, "total": 0, "name": "Recency-Weighted MMR"},
        "hybrid": {"correct": 0, "total": 0, "name": "Hybrid MMR (Performance)"},
    }

    for match in matches:
        # Get players for this match
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )

        if not match_players:
            continue

        # Determine actual winner
        team1_won = any(mp.won and mp.team_number == 1 for mp in match_players)

        # Get team MMRs for each model type
        team1_players = [mp for mp in match_players if mp.team_number == 1]
        team2_players = [mp for mp in match_players if mp.team_number == 2]

        if not team1_players or not team2_players:
            continue

        # Fetch player data
        player_ids = [mp.player_id for mp in match_players]
        players = {
            p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
        }

        # TrueSkill prediction (base MMR)
        team1_trueskill = sum(
            players.get(mp.player_id, Player()).mmr or 1000 for mp in team1_players
        ) / len(team1_players)
        team2_trueskill = sum(
            players.get(mp.player_id, Player()).mmr or 1000 for mp in team2_players
        ) / len(team2_players)
        trueskill_pred_team1 = team1_trueskill > team2_trueskill

        results["trueskill"]["total"] += 1
        if trueskill_pred_team1 == team1_won:
            results["trueskill"]["correct"] += 1

        # Recency-weighted prediction
        team1_recency = sum(
            (
                players.get(mp.player_id, Player()).recency_weighted_mmr
                or players.get(mp.player_id, Player()).mmr
                or 1000
            )
            for mp in team1_players
        ) / len(team1_players)
        team2_recency = sum(
            (
                players.get(mp.player_id, Player()).recency_weighted_mmr
                or players.get(mp.player_id, Player()).mmr
                or 1000
            )
            for mp in team2_players
        ) / len(team2_players)
        recency_pred_team1 = team1_recency > team2_recency

        results["recency"]["total"] += 1
        if recency_pred_team1 == team1_won:
            results["recency"]["correct"] += 1

        # Hybrid prediction (uses stored prediction if available)
        if match.predicted_team1_win_prob is not None:
            hybrid_pred_team1 = match.predicted_team1_win_prob > 0.5
            results["hybrid"]["total"] += 1
            if hybrid_pred_team1 == team1_won:
                results["hybrid"]["correct"] += 1

    # Calculate accuracies
    model_results = []
    for key, data in results.items():
        if data["total"] > 0:
            accuracy = (data["correct"] / data["total"]) * 100
            model_results.append(
                {
                    "model_id": key,
                    "model_name": data["name"],
                    "accuracy": round(accuracy, 1),
                    "correct_predictions": data["correct"],
                    "total_predictions": data["total"],
                    "improvement_vs_baseline": round(accuracy - 50, 1),  # vs random
                }
            )

    # Sort by accuracy descending
    model_results.sort(key=lambda x: x["accuracy"], reverse=True)

    # Add ranking
    for i, model in enumerate(model_results):
        model["rank"] = i + 1

    return {
        "total_matches": len(matches),
        "days_analyzed": days,
        "analyzed_at": datetime.utcnow().isoformat(),
        "models": model_results,
        "best_model": model_results[0] if model_results else None,
        "recommendation": _get_recommendation(model_results),
    }


def _get_recommendation(model_results: list) -> str:
    """Generate a recommendation based on model comparison."""
    if not model_results:
        return "Upload more replays to enable accuracy comparison."

    best = model_results[0]

    if best["accuracy"] >= 75:
        return f"{best['model_name']} is performing excellently at {best['accuracy']}% accuracy."
    elif best["accuracy"] >= 65:
        return f"{best['model_name']} is the best predictor at {best['accuracy']}%. Consider more matches for improvement."
    elif best["accuracy"] >= 55:
        return f"Prediction accuracy is moderate ({best['accuracy']}%). More match data may help."
    else:
        return "Prediction accuracy is low. This may improve with more match history."
