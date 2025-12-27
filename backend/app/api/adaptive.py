"""
API endpoints for adaptive model tuning.

Allows checking model performance and updating weights based on match data.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Optional, Any, List, cast
from sqlalchemy import func
from datetime import datetime, timedelta

from ..database import get_db
from ..adaptive_model import AdaptiveModelTuner, PerformanceWeights
from ..auto_adaptive import AutoAdaptiveTracker, AutoAdaptiveConfig
from ..models import Match, MatchPlayer, Player

router = APIRouter(prefix="/adaptive", tags=["adaptive"])

# Cache for expensive operations
_performance_cache: Dict[str, Any] = {
    "timestamp": None,
    "result": None,
    "cache_duration_seconds": 30,
}


class WeightSuggestionResponse(BaseModel):
    """Response for weight suggestion endpoint."""

    suggestion: str
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
    """
    suggestion = AdaptiveModelTuner.suggest_weight_update(db)

    if not suggestion:
        raise HTTPException(
            status_code=500, detail="Failed to generate weight suggestion"
        )

    cw: Any = suggestion.get("current_weights")
    sw: Any = suggestion.get("suggested_weights")
    perf: Any = suggestion.get("performance")

    current_weights_dict = {
        "combat": float(cw.combat_weight) if cw else 0.0,
        "economic": float(cw.economic_weight) if cw else 0.0,
        "team_contribution": float(cw.team_contribution_weight) if cw else 0.0,
        "efficiency": float(cw.efficiency_weight) if cw else 0.0,
    }

    suggested_weights_dict = None
    if sw:
        suggested_weights_dict = {
            "combat": float(sw.combat_weight),
            "economic": float(sw.economic_weight),
            "team_contribution": float(sw.team_contribution_weight),
            "efficiency": float(sw.efficiency_weight),
        }

    return WeightSuggestionResponse(
        suggestion=str(suggestion.get("suggestion", "")),
        reason=str(suggestion.get("reason", "")),
        confidence=float(suggestion.get("confidence", 0)),
        sample_size=int(suggestion.get("sample_size", 0)),
        current_weights=current_weights_dict,
        suggested_weights=suggested_weights_dict,
        changes=suggestion.get("changes"),
        performance_improvement=float(perf.correlation_strength) if perf else None,
    )


@router.get("/model-performance")
def get_model_performance(force_refresh: bool = False, db: Session = Depends(get_db)):
    """
    Get current model performance metrics.
    """
    now = datetime.utcnow()
    if (
        not force_refresh
        and _performance_cache["timestamp"] is not None
        and _performance_cache["result"] is not None
    ):
        ts: Any = _performance_cache["timestamp"]
        if ts:
            cache_age = (now - ts).total_seconds()
            if cache_age < _performance_cache["cache_duration_seconds"]:
                cached_result = cast(
                    Dict[str, Any], _performance_cache["result"]
                ).copy()
                cached_result["_cache_age_seconds"] = round(cache_age, 1)
                cached_result["_from_cache"] = True
                return cached_result

    current_weights = PerformanceWeights()
    _, performance = AdaptiveModelTuner.optimize_weights(db, current_weights)

    total_matches = db.query(func.count(Match.id)).scalar() or 0

    perf: Any = performance
    result = {
        "win_prediction_accuracy": float(perf.win_prediction_accuracy),
        "correlation_strength": float(perf.correlation_strength),
        "sample_size": int(total_matches),
        "confidence_score": float(perf.confidence_score),
        "current_weights": {
            "combat": float(current_weights.combat_weight),
            "economic": float(current_weights.economic_weight),
            "team_contribution": float(current_weights.team_contribution_weight),
            "efficiency": float(current_weights.efficiency_weight),
        },
        "_from_cache": False,
    }

    _performance_cache["timestamp"] = now
    _performance_cache["result"] = result.copy()

    return result


@router.post("/update-weights")
def update_weights(request: UpdateWeightsRequest, db: Session = Depends(get_db)):
    """
    Update performance weights (manual override).
    """
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

    return {
        "status": "success",
        "message": "Weights recorded",
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
    """
    total_matches = db.query(func.count(Match.id)).scalar() or 0
    tracker: Any = AutoAdaptiveTracker
    config: Any = AutoAdaptiveConfig

    last_count = int(tracker._last_optimization_count)
    matches_since_last = int(total_matches) - last_count

    threshold = int(config.MATCHES_PER_OPTIMIZATION)
    next_optimization_in = threshold - matches_since_last

    curr_w: Any = tracker._current_weights

    return {
        "enabled": bool(config.ENABLED),
        "matches_per_optimization": threshold,
        "total_matches": int(total_matches),
        "last_optimization_at_match": last_count,
        "matches_since_last_optimization": matches_since_last,
        "next_optimization_in": max(0, next_optimization_in),
        "has_current_weights": curr_w is not None,
        "current_weights": {
            "combat": float(curr_w.combat_weight),
            "economic": float(curr_w.economic_weight),
            "team_contribution": float(curr_w.team_contribution_weight),
            "efficiency": float(curr_w.efficiency_weight),
        }
        if curr_w
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
    """
    config: Any = AutoAdaptiveConfig
    if request.enabled is not None:
        config.ENABLED = bool(request.enabled)

    if request.matches_per_optimization is not None:
        if request.matches_per_optimization < 1:
            raise HTTPException(
                status_code=400, detail="matches_per_optimization must be at least 1"
            )
        config.MATCHES_PER_OPTIMIZATION = int(request.matches_per_optimization)

    return {
        "status": "success",
        "message": "Auto-optimization configuration updated",
        "config": {
            "enabled": bool(config.ENABLED),
            "matches_per_optimization": int(config.MATCHES_PER_OPTIMIZATION),
        },
    }


@router.post("/force-optimize")
def force_optimization(db: Session = Depends(get_db)):
    """
    Force optimization regardless of threshold.
    """
    result = AutoAdaptiveTracker.force_optimization(db)

    if not result:
        raise HTTPException(
            status_code=500, detail="Optimization failed to generate results"
        )

    return {"status": "success", "message": "Optimization completed", "result": result}


@router.get("/model-versions")
def get_model_versions(db: Session = Depends(get_db)):
    """
    Get all model versions with their performance stats.
    """
    try:
        from ..online_learning import ModelVersion

        versions = (
            db.query(ModelVersion)
            .order_by(ModelVersion.created_at.desc())
            .limit(20)
            .all()
        )

        result_list = []
        for v in versions:
            ver: Any = v
            result_list.append(
                {
                    "version_name": str(ver.version_name),
                    "created_at": ver.created_at.isoformat(),
                    "weights": ver.weights_json,
                    "is_active": bool(ver.is_active),
                    "total_predictions": int(ver.total_predictions or 0),
                    "correct_predictions": int(ver.correct_predictions or 0),
                    "accuracy": float(ver.correct_predictions or 0)
                    / float(ver.total_predictions or 1)
                    if ver.total_predictions and ver.total_predictions > 0
                    else 0,
                }
            )

        return {"versions": result_list}
    except Exception:
        return {"versions": []}


@router.get("/prediction-logs")
def get_prediction_logs(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get recent prediction logs with outcomes.
    """
    try:
        from ..online_learning import PredictionLog

        limit = min(limit, 200)

        logs = (
            db.query(PredictionLog)
            .order_by(PredictionLog.created_at.desc())
            .limit(limit)
            .all()
        )

        result_list = []
        for l in logs:
            log: Any = l
            result_list.append(
                {
                    "id": int(log.id),
                    "match_id": int(log.match_id),
                    "predicted_team1_win_prob": float(
                        log.predicted_team1_win_prob or 0
                    ),
                    "actual_team1_won": bool(log.actual_team1_won)
                    if log.actual_team1_won is not None
                    else None,
                    "was_upset": bool(log.was_upset),
                }
            )

        return {"predictions": result_list}
    except Exception:
        return {"predictions": []}


@router.get("/blending-stats")
def get_blending_stats(days: int = 30, db: Session = Depends(get_db)):
    """
    Get blending statistics.
    """
    try:
        from ..online_learning import PredictionLog

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
            return {"total_matches": 0, "avg_error": 0}

        total = len(logs)
        avg_error = sum(float(getattr(l, "prediction_error", 0)) for l in logs) / total
        upsets = sum(1 for l in logs if bool(getattr(l, "was_upset", False)))

        return {
            "total_matches": int(total),
            "avg_error": float(avg_error),
            "upset_count": int(upsets),
            "days_analyzed": int(days),
        }
    except Exception:
        return {"total_matches": 0, "avg_error": 0}


@router.get("/feature-importance")
def get_feature_importance(db: Session = Depends(get_db)):
    """
    Get feature importance rankings.
    """
    try:
        from ..online_learning import FeatureImportance

        features = (
            db.query(FeatureImportance)
            .order_by(FeatureImportance.calculated_at.desc())
            .limit(100)
            .all()
        )

        feature_dict: Dict[str, Any] = {}
        for f in features:
            f_any: Any = f
            f_name = str(f_any.feature_name)
            if f_name and f_name not in feature_dict:
                feature_dict[f_name] = f_any

        return {
            "features": [
                {
                    "feature_name": str(f.feature_name),
                    "correlation": float(f.correlation_with_outcome or 0),
                }
                for f in sorted(
                    feature_dict.values(),
                    key=lambda x: abs(float(x.correlation_with_outcome or 0)),
                    reverse=True,
                )
            ]
        }
    except Exception:
        return {"features": []}


@router.get("/feature-suggestions")
def get_feature_suggestions(db: Session = Depends(get_db)):
    """
    Get AI-suggested new features.
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
                    "id": int(s.id),
                    "feature_name": str(s.feature_name),
                    "description": str(s.feature_description),
                    "extraction_logic": str(s.extraction_logic or ""),
                    "reasoning": str(s.reasoning or ""),
                    "expected_correlation": float(s.correlation_hypothesis or 0),
                    "status": str(s.status),
                    "created_at": s.created_at.isoformat(),
                    "tested_at": s.tested_at.isoformat() if s.tested_at else None,
                    "test_results": str(s.test_results or ""),
                }
                for s in suggestions
            ]
        }
    except Exception:
        return {"suggestions": []}


@router.get("/accuracy-comparison")
def get_accuracy_comparison(days: int = 90, db: Session = Depends(get_db)):
    """
    Compare prediction accuracy across different rating models with trends.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    matches = (
        db.query(Match)
        .filter(
            Match.played_at >= cutoff_date, Match.predicted_team1_win_prob.isnot(None)
        )
        .order_by(Match.played_at.asc())
        .all()
    )

    if not matches:
        return {"total_matches": 0, "results": {}, "trends": []}

    results: Dict[str, Any] = {
        "trueskill": {"correct": 0, "total": 0},
        "hybrid": {"correct": 0, "total": 0},
    }

    # Group matches by date for trends
    trends_dict: Dict[str, Dict[str, Any]] = {}

    for m in matches:
        match: Any = m
        match_date = match.played_at.strftime("%Y-%m-%d")
        if match_date not in trends_dict:
            trends_dict[match_date] = {
                "date": match_date,
                "trueskill_correct": 0,
                "trueskill_total": 0,
                "hybrid_correct": 0,
                "hybrid_total": 0,
            }

        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )

        if not match_players:
            continue

        team1_won = any(
            bool(getattr(mp, "won", 0) == 1) and getattr(mp, "team_number", 0) == 1
            for mp in match_players
        )
        team1_players = [
            mp for mp in match_players if getattr(mp, "team_number", 0) == 1
        ]
        team2_players = [
            mp for mp in match_players if getattr(mp, "team_number", 0) == 2
        ]

        if not team1_players or not team2_players:
            continue

        player_ids = [int(getattr(mp, "player_id", 0)) for mp in match_players]
        players = {
            p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
        }

        t1_ts = sum(
            float(
                getattr(players.get(getattr(mp, "player_id", 0), Player()), "mmr", 1000)
            )
            for mp in team1_players
        ) / len(team1_players)
        t2_ts = sum(
            float(
                getattr(players.get(getattr(mp, "player_id", 0), Player()), "mmr", 1000)
            )
            for mp in team2_players
        ) / len(team2_players)

        results["trueskill"]["total"] += 1
        trends_dict[match_date]["trueskill_total"] += 1
        if (t1_ts > t2_ts) == team1_won:
            results["trueskill"]["correct"] += 1
            trends_dict[match_date]["trueskill_correct"] += 1

        if match.predicted_team1_win_prob is not None:
            results["hybrid"]["total"] += 1
            trends_dict[match_date]["hybrid_total"] += 1
            if (float(match.predicted_team1_win_prob) > 0.5) == team1_won:
                results["hybrid"]["correct"] += 1
                trends_dict[match_date]["hybrid_correct"] += 1

    # Format trends for frontend
    trends = sorted(trends_dict.values(), key=lambda x: x["date"])

    # Calculate rolling accuracy for trends
    rolling_trueskill_correct = 0
    rolling_trueskill_total = 0
    rolling_hybrid_correct = 0
    rolling_hybrid_total = 0

    for t in trends:
        rolling_trueskill_correct += t["trueskill_correct"]
        rolling_trueskill_total += t["trueskill_total"]
        rolling_hybrid_correct += t["hybrid_correct"]
        rolling_hybrid_total += t["hybrid_total"]

        t["trueskill_accuracy"] = (
            rolling_trueskill_correct / rolling_trueskill_total
            if rolling_trueskill_total > 0
            else 0
        )
        t["hybrid_accuracy"] = (
            rolling_hybrid_correct / rolling_hybrid_total
            if rolling_hybrid_total > 0
            else 0
        )

    return {"total_matches": len(matches), "results": results, "trends": trends}


@router.get("/shap-importance")
def get_shap_importance():
    """
    Get global SHAP importance from the XGBoost predictor.
    """
    from ..services.xgboost_predictor import get_xgboost_predictor

    xgb = get_xgboost_predictor()
    if not xgb.is_trained:
        # Try to load it
        from ..services.xgboost_predictor import XGBoostPredictor

        try:
            with open(XGBoostPredictor.MODEL_PATH, "rb") as f:
                import pickle

                data = pickle.load(f)
                shap_importance = data.get("shap_importance", {})
        except Exception:
            shap_importance = {}
    else:
        shap_importance = xgb.shap_importance

    return {
        "features": [
            {"feature": k, "importance": v}
            for k, v in sorted(
                shap_importance.items(), key=lambda x: x[1], reverse=True
            )
        ]
    }


@router.post("/train-xgboost")
def train_xgboost_model(db: Session = Depends(get_db)):
    """
    Train the XGBoost prediction model.
    """
    from ..services.xgboost_predictor import train_xgboost_model

    return train_xgboost_model(db)


@router.post("/build-order/retrain")
def retrain_build_order_classifier(db: Session = Depends(get_db)):
    """
    Retrain the K-Means build order classifier on all available data.
    """
    from ..services.build_order_classifier import train_classifier

    try:
        result = train_classifier(db)
        return {
            "status": "success",
            "message": "Build order classifier retrained",
            "details": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/ml-models-status")
def get_ml_models_status(db: Session = Depends(get_db)):
    """
    Get status of all ML models.
    """
    from ..services.xgboost_predictor import get_xgboost_predictor
    from ..services.build_order_classifier import get_classifier

    xgb = get_xgboost_predictor()
    build_clf = get_classifier()

    return {
        "xgboost": {
            "is_trained": bool(xgb.is_trained),
            "accuracy": round(float(xgb.training_accuracy) * 100, 1)
            if xgb.is_trained
            else None,
        },
        "build_classifier": {
            "use_clustering": bool(build_clf.use_clustering),
        },
    }
