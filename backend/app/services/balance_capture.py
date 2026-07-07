"""
Balance Prediction Capture Service.

Uplifts data capture around balancing: every balancer suggestion is logged
with its predicted win probability at balance time, then resolved against
the actual match outcome when the replay is uploaded. This gives real
calibration metrics (Brier score, log loss, reliability bins) per balancing
method, instead of only tracking directional accuracy after the fact.

Resolution matches a prediction to a match by the sorted set of all player
IDs (players_key) within a time window around the match's played_at.
"""

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import BalancePrediction, Match, MatchPlayer

logger = logging.getLogger(__name__)

# A balance suggestion is only matched to games played within this window
# after it was generated (plus small backward skew tolerance for clock drift
# between the server and the game client writing played_at).
MATCH_WINDOW_HOURS = 24
CLOCK_SKEW_HOURS = 6


def _ids_key(player_ids: List[int]) -> str:
    return ",".join(map(str, sorted(player_ids)))


class BalancePredictionService:
    """Record balancer predictions and resolve them against match outcomes."""

    @staticmethod
    def record_suggestion(
        db: Session,
        method: str,
        rank: int,
        team1_ids: List[int],
        team2_ids: List[int],
        predicted_team1_win_prob: float,
        match_quality: Optional[float] = None,
        balance_score: Optional[float] = None,
        mmr_difference: Optional[float] = None,
        features: Optional[Dict[str, Any]] = None,
    ) -> BalancePrediction:
        """Log a single suggestion. Caller is responsible for commit."""
        prediction = BalancePrediction(
            created_at=datetime.utcnow(),
            method=method,
            rank=rank,
            players_key=_ids_key(team1_ids + team2_ids),
            team1_ids_key=_ids_key(team1_ids),
            team2_ids_key=_ids_key(team2_ids),
            predicted_team1_win_prob=predicted_team1_win_prob,
            match_quality=match_quality,
            balance_score=balance_score,
            mmr_difference=mmr_difference,
            features_json=json.dumps(features) if features else None,
        )
        db.add(prediction)
        return prediction

    @staticmethod
    def record_suggestions(
        db: Session,
        method: str,
        suggestions: List[Any],
        max_rank: int = 3,
    ) -> int:
        """
        Log the top suggestions from a balance request.

        Accepts app.balancer.TeamSuggestion objects (duck-typed to avoid a
        circular import). Commits at the end; failures are logged and
        swallowed so capture can never break a balance request.
        """
        recorded = 0
        try:
            for rank, s in enumerate(suggestions[:max_rank], start=1):
                features = {
                    "impact_balance_score": getattr(s, "impact_balance_score", None),
                    "playstyle_balance_score": getattr(
                        s, "playstyle_balance_score", None
                    ),
                    "total_synergy": getattr(s, "total_synergy", None),
                    "skill_spread_diff": getattr(s, "skill_spread_diff", None),
                    "component_imbalance": getattr(s, "component_imbalance", None),
                    "synergy_imbalance": getattr(s, "synergy_imbalance", None),
                    "ml_win_probability": getattr(s, "ml_win_probability", None),
                }
                BalancePredictionService.record_suggestion(
                    db,
                    method=method,
                    rank=rank,
                    team1_ids=[p.id for p in s.team_1],
                    team2_ids=[p.id for p in s.team_2],
                    predicted_team1_win_prob=s.win_probability,
                    match_quality=s.match_quality,
                    balance_score=getattr(s, "composite_score", None),
                    mmr_difference=s.mmr_difference,
                    features={k: v for k, v in features.items() if v is not None},
                )
                recorded += 1
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to record balance predictions: {e}")
        return recorded

    @staticmethod
    def resolve_for_match(db: Session, match: Match) -> int:
        """
        Resolve any unresolved predictions for this match's player set.

        Called after MatchPlayer records exist (post rating update).
        Returns the number of predictions resolved.
        """
        participants = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )
        team1_ids = {mp.player_id for mp in participants if mp.team_number == 1}
        team2_ids = {mp.player_id for mp in participants if mp.team_number == 2}
        if not team1_ids or not team2_ids:
            return 0

        players_key = _ids_key(list(team1_ids | team2_ids))
        team1_won = 1 if any(mp.won for mp in participants if mp.team_number == 1) else 0

        window_start = match.played_at - timedelta(hours=MATCH_WINDOW_HOURS)
        window_end = match.played_at + timedelta(hours=CLOCK_SKEW_HOURS)

        candidates = (
            db.query(BalancePrediction)
            .filter(
                BalancePrediction.resolved == 0,
                BalancePrediction.players_key == players_key,
                BalancePrediction.created_at >= window_start,
                BalancePrediction.created_at <= window_end,
            )
            .all()
        )

        resolved = 0
        for pred in candidates:
            pred_team1 = set(map(int, pred.team1_ids_key.split(",")))
            # team1_won is stored relative to the PREDICTION's team 1, so
            # calibration can read (predicted_team1_win_prob, team1_won) directly.
            if pred_team1 == team1_ids:
                pred_side_won = team1_won
            elif pred_team1 == team2_ids:
                # The balancer's team 1 played as match team 2
                pred_side_won = 1 - team1_won
            else:
                # Same player pool but a different split than suggested —
                # this suggestion wasn't the one played; skip it.
                continue

            pred.resolved = 1
            pred.match_id = match.id
            pred.team1_won = pred_side_won
            pred.brier_score = (pred.predicted_team1_win_prob - pred_side_won) ** 2
            pred.resolved_at = datetime.utcnow()
            resolved += 1

        if resolved:
            db.commit()
            logger.info(
                f"Resolved {resolved} balance prediction(s) for match {match.id}"
            )
        return resolved

    # ------------------------------------------------------------------
    # Calibration metrics
    # ------------------------------------------------------------------

    @staticmethod
    def _calibration_from_pairs(
        pairs: List[tuple], n_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Compute calibration metrics from (predicted_team1_prob, team1_won) pairs.
        """
        if not pairs:
            return {
                "count": 0,
                "accuracy": None,
                "brier_score": None,
                "log_loss": None,
                "bins": [],
            }

        eps = 1e-6
        n = len(pairs)
        correct = sum(1 for p, won in pairs if (p > 0.5) == bool(won))
        brier = sum((p - won) ** 2 for p, won in pairs) / n
        log_loss = -sum(
            won * math.log(max(p, eps)) + (1 - won) * math.log(max(1 - p, eps))
            for p, won in pairs
        ) / n

        bins = []
        for i in range(n_bins):
            lo, hi = i / n_bins, (i + 1) / n_bins
            in_bin = [
                (p, won)
                for p, won in pairs
                if (lo <= p < hi) or (i == n_bins - 1 and p == 1.0)
            ]
            if in_bin:
                bins.append(
                    {
                        "range": [round(lo, 2), round(hi, 2)],
                        "count": len(in_bin),
                        "avg_predicted": round(
                            sum(p for p, _ in in_bin) / len(in_bin), 3
                        ),
                        "actual_win_rate": round(
                            sum(won for _, won in in_bin) / len(in_bin), 3
                        ),
                    }
                )

        return {
            "count": n,
            "accuracy": round(correct / n, 3),
            "brier_score": round(brier, 4),
            "log_loss": round(log_loss, 4),
            "bins": bins,
        }

    @staticmethod
    def get_calibration(
        db: Session, method: Optional[str] = None, days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calibration metrics for resolved balancer predictions, grouped by method.
        Only rank-1 suggestions are scored (the pick the balancer recommended).
        """
        query = db.query(BalancePrediction).filter(
            BalancePrediction.resolved == 1, BalancePrediction.rank == 1
        )
        if method:
            query = query.filter(BalancePrediction.method == method)
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(BalancePrediction.created_at >= cutoff)

        predictions = query.all()

        by_method: Dict[str, List[tuple]] = {}
        for pred in predictions:
            # team1_won is stored relative to the prediction's team 1 at
            # resolve time, so the pair reads directly.
            if pred.team1_won is not None:
                by_method.setdefault(pred.method, []).append(
                    (pred.predicted_team1_win_prob, pred.team1_won)
                )

        return {
            m: BalancePredictionService._calibration_from_pairs(pairs)
            for m, pairs in by_method.items()
        }

    @staticmethod
    def get_upload_baseline_calibration(
        db: Session, days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calibration of the upload-time TrueSkill predictions already stored on
        Match rows — the baseline every balancing method must beat.
        """
        query = db.query(Match).filter(Match.predicted_team1_win_prob.isnot(None))
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Match.played_at >= cutoff)

        matches = query.all()
        if not matches:
            return BalancePredictionService._calibration_from_pairs([])

        match_ids = [m.id for m in matches]
        winners: Dict[int, int] = {}
        rows = (
            db.query(MatchPlayer.match_id, MatchPlayer.team_number, MatchPlayer.won)
            .filter(MatchPlayer.match_id.in_(match_ids))
            .all()
        )
        for match_id, team_number, won in rows:
            if team_number == 1 and won:
                winners[match_id] = 1
            elif match_id not in winners:
                winners[match_id] = 0

        pairs = [
            (float(m.predicted_team1_win_prob), winners[m.id])
            for m in matches
            if m.id in winners
        ]
        return BalancePredictionService._calibration_from_pairs(pairs)
