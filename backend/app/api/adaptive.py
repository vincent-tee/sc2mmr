"""
API endpoints for adaptive model tuning.

Allows checking model performance and updating weights based on match data.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Optional, Any, List, cast
from sqlalchemy import func
from datetime import datetime, timedelta

from ..database import get_db

logger = logging.getLogger(__name__)
from ..adaptive_model import AdaptiveModelTuner, PerformanceWeights
from ..auto_adaptive import AutoAdaptiveTracker, AutoAdaptiveConfig
from ..models import Match, MatchPlayer, Player, FeatureSuggestion, MetaFeedback

router = APIRouter(prefix="/adaptive", tags=["adaptive"])

# Cache for expensive operations
_performance_cache: Dict[str, Any] = {
    "timestamp": None,
    "result": None,
    "cache_duration_seconds": 30,
}


class FeatureSuggestionRequest(BaseModel):
    """Request to suggest a new feature."""

    feature_name: str
    description: str


class MetaFeedbackRequest(BaseModel):
    """Request to submit meta feedback."""

    theory: str


@router.get("/test")
def test_adaptive():
    return {"status": "ok"}


@router.get("/feature-suggestions")
def get_feature_suggestions(db: Session = Depends(get_db)):
    """
    Get all suggested features.
    """
    suggestions = (
        db.query(FeatureSuggestion).order_by(FeatureSuggestion.created_at.desc()).all()
    )
    return {
        "suggestions": [
            {
                "id": s.id,
                "feature_name": s.feature_name,
                "description": s.description,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in suggestions
        ]
    }


@router.post("/feature-suggestions")
def create_feature_suggestion(
    request: FeatureSuggestionRequest, db: Session = Depends(get_db)
):
    """
    Suggest a new feature for the ML model.
    """
    suggestion = FeatureSuggestion(
        feature_name=request.feature_name, description=request.description
    )
    db.add(suggestion)
    db.commit()
    return {"status": "success", "message": "Suggestion received"}


@router.get("/meta-feedback")
def get_meta_feedback(db: Session = Depends(get_db)):
    """
    Get all active squad theories.
    """
    theories = (
        db.query(MetaFeedback)
        .filter(MetaFeedback.is_active == 1)
        .order_by(MetaFeedback.created_at.desc())
        .all()
    )
    return {
        "theories": [
            {
                "id": t.id,
                "theory": t.theory,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in theories
        ]
    }


@router.post("/meta-feedback")
def create_meta_feedback(request: MetaFeedbackRequest, db: Session = Depends(get_db)):
    """
    Submit a new squad theory.
    """
    feedback = MetaFeedback(theory=request.theory)
    db.add(feedback)
    db.commit()
    return {"status": "success", "message": "Theory recorded"}


@router.get("/accuracy-comparison")
def get_accuracy_comparison(days: int = 90, db: Session = Depends(get_db)):
    """
    Compare prediction accuracy across different rating models with trends.

    Returns both stored prediction accuracy AND cross-validated model accuracy.
    """
    from ..services.ml_predictor import get_ml_predictor, FeatureExtractor
    import numpy as np

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
        )
        t2_ts = sum(
            float(
                getattr(players.get(getattr(mp, "player_id", 0), Player()), "mmr", 1000)
            )
            for mp in team2_players
        )

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

    # Calculate cross-validated accuracy (more reliable than stored predictions)
    #
    # Uses the same leak-free chronological dataset as MLPredictor.train() -
    # NOT FeatureExtractor.extract_team_features() per match, which reads
    # current Player-row aggregates and leaks each match's own outcome (and
    # everything since) into its own "historical" features. See
    # .moai/docs/ml-model-findings.md, 2026-07-06 entry.
    cv_accuracy = None
    baseline_accuracy = None
    cv_training_size = 0
    try:
        from sklearn.model_selection import StratifiedKFold, cross_val_score
        from sklearn.linear_model import LogisticRegression
        from ..services.ml_predictor import build_chronological_dataset

        X_arr, y_arr, _ = build_chronological_dataset(db)

        if len(X_arr) >= 10:
            mmr_diff_idx = FeatureExtractor.FEATURE_NAMES.index("sum_mmr_diff")
            decided = X_arr[:, mmr_diff_idx] != 0
            if decided.any():
                baseline_accuracy = round(
                    float(np.mean((X_arr[decided, mmr_diff_idx] > 0) == (y_arr[decided] == 1))) * 100,
                    1,
                )

            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            lr = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
            cv_scores = cross_val_score(lr, X_arr, y_arr, cv=cv)
            cv_accuracy = round(cv_scores.mean() * 100, 1)
            cv_training_size = len(X_arr)
    except Exception as e:
        logger.warning(f"CV accuracy calculation failed: {e}")
        cv_training_size = 0

    return {
        "total_matches": len(matches),
        "results": results,
        "trends": trends,
        "cv_accuracy": cv_accuracy,
        "baseline_accuracy": baseline_accuracy,
        "cv_training_size": cv_training_size,
    }


@router.get("/balance-method-success-rate")
def get_balance_method_success_rate(db: Session = Depends(get_db)):
    """
    Get success rate percentages for each balance method.

    Returns prediction accuracy for:
    - trueskill: Pure TrueSkill MMR comparison
    - session: Session-weighted MMR (recent matches weighted 3x)
    - ml-metrics: ML model combining metrics with adaptive weights
    """
    from ..services.ml_predictor import get_ml_predictor, FeatureExtractor
    import numpy as np

    # Get matches from last 90 days for success rate calculation
    cutoff_date = datetime.utcnow() - timedelta(days=90)

    matches = (
        db.query(Match)
        .filter(Match.played_at >= cutoff_date)
        .order_by(Match.played_at.desc())
        .all()
    )

    if not matches:
        return {
            "trueskill": {"success_rate": 50.0, "total_matches": 0},
            "session": {"success_rate": 50.0, "total_matches": 0},
            "ml-metrics": {"success_rate": 50.0, "total_matches": 0},
        }

    results: Dict[str, Dict[str, Any]] = {
        "trueskill": {"correct": 0, "total": 0},
        "session": {"correct": 0, "total": 0},
        "ml-metrics": {"correct": 0, "total": 0},
    }

    for m in matches:
        match: Any = m
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )

        if not match_players:
            continue

        team1_players = [mp for mp in match_players if mp.team_number == 1]
        team2_players = [mp for mp in match_players if mp.team_number == 2]

        if not team1_players or not team2_players:
            continue

        team1_won = any(bool(mp.won) for mp in team1_players)

        # Get player data
        player_ids = [mp.player_id for mp in match_players]
        players = {
            p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
        }

        # TrueSkill: Compare total team MMR
        t1_mmr = sum(
            float(players.get(mp.player_id, Player()).mmr or 1000)
            for mp in team1_players
        )
        t2_mmr = sum(
            float(players.get(mp.player_id, Player()).mmr or 1000)
            for mp in team2_players
        )

        results["trueskill"]["total"] += 1
        if (t1_mmr > t2_mmr) == team1_won:
            results["trueskill"]["correct"] += 1

        # Session-weighted: Compare total session MMR if available
        t1_session = sum(
            float(
                getattr(
                    players.get(mp.player_id, Player()), "session_weighted_mmr", None
                )
                or players.get(mp.player_id, Player()).mmr
                or 1000
            )
            for mp in team1_players
        )
        t2_session = sum(
            float(
                getattr(
                    players.get(mp.player_id, Player()), "session_weighted_mmr", None
                )
                or players.get(mp.player_id, Player()).mmr
                or 1000
            )
            for mp in team2_players
        )

        results["session"]["total"] += 1
        if (t1_session > t2_session) == team1_won:
            results["session"]["correct"] += 1

        # ML-metrics: Use stored prediction if available
        if match.predicted_team1_win_prob is not None:
            results["ml-metrics"]["total"] += 1
            if (float(match.predicted_team1_win_prob) > 0.5) == team1_won:
                results["ml-metrics"]["correct"] += 1

    # Calculate success rate percentages
    response = {}
    for method, data in results.items():
        if data["total"] > 0:
            success_rate = round((data["correct"] / data["total"]) * 100, 1)
        else:
            success_rate = 50.0  # Default to 50% if no data
        response[method] = {
            "success_rate": success_rate,
            "total_matches": data["total"],
        }

    return response


@router.get("/shap-importance")
def get_shap_importance():
    """
    Get global SHAP importance from ML predictor.
    Falls back to native feature importance if SHAP is not available.
    """
    from ..services.ml_predictor import get_ml_predictor, MLPredictor

    ml = get_ml_predictor()
    if not ml.is_trained:
        # Try to load it
        try:
            with open(MLPredictor.MODEL_PATH, "rb") as f:
                import pickle

                data = pickle.load(f)
                # Try SHAP first, fall back to feature_importance
                shap_importance = data.get("shap_importance", {})
                if not shap_importance:
                    shap_importance = data.get("feature_importance", {})
        except Exception:
            shap_importance = {}
    else:
        # Use SHAP if available, otherwise use feature_importance
        shap_importance = (
            ml.shap_importance if ml.shap_importance else ml.feature_importance
        )

    return {
        "features": [
            {"feature": k, "importance": v}
            for k, v in sorted(
                shap_importance.items(), key=lambda x: x[1], reverse=True
            )
        ]
    }


@router.post("/train-ml-model")
def train_ml_model_endpoint(db: Session = Depends(get_db)):
    """
    Train the ML prediction model.
    """
    from ..services.ml_predictor import train_ml_model

    return train_ml_model(db)


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
    from ..services.ml_predictor import get_ml_predictor
    from ..services.build_order_classifier import get_classifier

    ml = get_ml_predictor()
    # Auto-load model if not loaded
    if not ml.is_trained:
        ml._load_model()

    build_clf = get_classifier()

    return {
        # LogisticRegression, not XGBoost - see ml_predictor.py MLPredictor._get_model().
        # This CV accuracy is NOT a proven improvement over the "higher summed
        # MMR wins" baseline (see .moai/docs/ml-model-findings.md, 2026-07-06) -
        # lab/diagnostic status only, not a product claim.
        "win_predictor": {
            "is_trained": bool(ml.is_trained),
            "accuracy": round(float(ml.training_accuracy) * 100, 1)
            if ml.is_trained
            else None,
        },
        "build_classifier": {
            "use_clustering": bool(build_clf.use_clustering),
        },
    }
