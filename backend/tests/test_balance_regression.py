#!/usr/bin/env python3
"""
Balance Method Regression Test

Compares prediction accuracy of different balance methods against historical match outcomes:
1. TrueSkill (baseline) - Pure mu/sigma MMR
2. Session-Weighted - Recency-weighted MMR
3. ML-Metrics - Weighted performance components + synergy

Also performs component-level regression on ML-metrics weights.

Run with: pytest tests/test_balance_regression.py -v -s
"""

import pytest
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import Match, MatchPlayer, Player
from app.rating_system import RatingSystem
from app.services.adaptive_balancer import MLMetricsBalancer, ComponentAccuracyTracker


@dataclass
class PredictionResult:
    """Result of a prediction for a single match."""

    match_id: int
    predicted_winner: int  # 1 or 2
    actual_winner: int  # 1 or 2
    confidence: float  # Difference in team scores (higher = more confident)
    correct: bool


@dataclass
class RegressionReport:
    """Full regression report for a balance method."""

    method_name: str
    total_matches: int
    correct_predictions: int
    accuracy: float
    high_confidence_accuracy: float  # Accuracy on matches with confidence > median
    low_confidence_accuracy: float  # Accuracy on matches with confidence <= median
    avg_confidence: float


class BalanceMethodPredictor:
    """Predicts match winners using different balance methods."""

    def __init__(self, db: Session):
        self.db = db
        self._player_cache: Dict[int, Player] = {}

    def _get_player(self, player_id: int) -> Optional[Player]:
        """Get player from cache or database."""
        if player_id not in self._player_cache:
            player = self.db.query(Player).filter(Player.id == player_id).first()
            if player:
                self._player_cache[player_id] = player
        return self._player_cache.get(player_id)

    def predict_trueskill(
        self, team1_ids: List[int], team2_ids: List[int]
    ) -> Tuple[int, float]:
        """Predict winner using pure TrueSkill MMR."""
        team1_total = 0.0
        team2_total = 0.0

        for pid in team1_ids:
            player = self._get_player(pid)
            if player:
                team1_total += player.mmr

        for pid in team2_ids:
            player = self._get_player(pid)
            if player:
                team2_total += player.mmr

        diff = team1_total - team2_total
        winner = 1 if diff >= 0 else 2
        confidence = abs(diff)

        return winner, confidence

    def predict_session(
        self, team1_ids: List[int], team2_ids: List[int]
    ) -> Tuple[int, float]:
        """Predict winner using session-weighted MMR."""
        team1_total = 0.0
        team2_total = 0.0

        for pid in team1_ids:
            player = self._get_player(pid)
            if player:
                # Use session_weighted_mmr if available, else fallback to mmr
                team1_total += player.session_weighted_mmr or player.mmr

        for pid in team2_ids:
            player = self._get_player(pid)
            if player:
                team2_total += player.session_weighted_mmr or player.mmr

        diff = team1_total - team2_total
        winner = 1 if diff >= 0 else 2
        confidence = abs(diff)

        return winner, confidence

    def predict_ml_metrics(
        self,
        team1_ids: List[int],
        team2_ids: List[int],
        weights: Optional[Dict[str, float]] = None,
    ) -> Tuple[int, float]:
        """Predict winner using ML-weighted metrics."""
        if weights is None:
            weights = ComponentAccuracyTracker.DEFAULT_WEIGHTS

        team1_total = 0.0
        team2_total = 0.0

        for pid in team1_ids:
            player = self._get_player(pid)
            if player:
                rating, _ = MLMetricsBalancer.calculate_ml_rating(
                    player, weights, self.db
                )
                team1_total += rating

        for pid in team2_ids:
            player = self._get_player(pid)
            if player:
                rating, _ = MLMetricsBalancer.calculate_ml_rating(
                    player, weights, self.db
                )
                team2_total += rating

        diff = team1_total - team2_total
        winner = 1 if diff >= 0 else 2
        confidence = abs(diff)

        return winner, confidence


def get_historical_matches(db: Session) -> List[Tuple[int, List[int], List[int], int]]:
    """
    Get all historical matches with team compositions and winners.

    Returns: List of (match_id, team1_player_ids, team2_player_ids, winner_team)
    """
    matches = db.query(Match).filter(Match.played_at.isnot(None)).all()
    results = []

    for match in matches:
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )

        team1_ids = [mp.player_id for mp in match_players if mp.team_number == 1]
        team2_ids = [mp.player_id for mp in match_players if mp.team_number == 2]

        # Skip invalid matches
        if not team1_ids or not team2_ids:
            continue

        # Determine winner
        team1_won = any(mp.won for mp in match_players if mp.team_number == 1)
        winner = 1 if team1_won else 2

        results.append((match.id, team1_ids, team2_ids, winner))

    return results


def run_regression(
    db: Session,
    method_name: str,
    predict_fn,
    matches: List[Tuple[int, List[int], List[int], int]],
) -> RegressionReport:
    """Run regression test for a given prediction method."""
    predictions: List[PredictionResult] = []

    for match_id, team1_ids, team2_ids, actual_winner in matches:
        predicted_winner, confidence = predict_fn(team1_ids, team2_ids)
        correct = predicted_winner == actual_winner

        predictions.append(
            PredictionResult(
                match_id=match_id,
                predicted_winner=predicted_winner,
                actual_winner=actual_winner,
                confidence=confidence,
                correct=correct,
            )
        )

    # Calculate metrics
    total = len(predictions)
    correct_count = sum(1 for p in predictions if p.correct)
    accuracy = correct_count / total if total > 0 else 0.0

    # Split by confidence
    confidences = sorted([p.confidence for p in predictions])
    median_conf = confidences[len(confidences) // 2] if confidences else 0

    high_conf = [p for p in predictions if p.confidence > median_conf]
    low_conf = [p for p in predictions if p.confidence <= median_conf]

    high_conf_acc = (
        sum(1 for p in high_conf if p.correct) / len(high_conf) if high_conf else 0
    )
    low_conf_acc = (
        sum(1 for p in low_conf if p.correct) / len(low_conf) if low_conf else 0
    )

    avg_confidence = sum(p.confidence for p in predictions) / total if total > 0 else 0

    return RegressionReport(
        method_name=method_name,
        total_matches=total,
        correct_predictions=correct_count,
        accuracy=accuracy,
        high_confidence_accuracy=high_conf_acc,
        low_confidence_accuracy=low_conf_acc,
        avg_confidence=avg_confidence,
    )


def run_component_regression(
    db: Session,
    matches: List[Tuple[int, List[int], List[int], int]],
    predictor: BalanceMethodPredictor,
) -> Dict[str, float]:
    """
    Run regression on individual ML components to measure their predictive power.

    Tests each component in isolation to see how well it predicts outcomes.
    """
    components = ["session_mmr", "teamwork", "combat", "economic", "efficiency"]
    component_accuracies = {}

    for component in components:
        # Create weights with only this component
        weights = {c: 0.0 for c in components}
        weights[component] = 1.0

        predictions_correct = 0
        total = 0

        for match_id, team1_ids, team2_ids, actual_winner in matches:
            predicted, _ = predictor.predict_ml_metrics(team1_ids, team2_ids, weights)
            if predicted == actual_winner:
                predictions_correct += 1
            total += 1

        accuracy = predictions_correct / total if total > 0 else 0.0
        component_accuracies[component] = accuracy

    return component_accuracies


class TestBalanceRegression:
    """Regression tests for balance methods."""

    @pytest.fixture(scope="class")
    def db_session(self):
        """Create database session."""
        engine = create_engine("sqlite:///data/sc2mmr.db")
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture(scope="class")
    def historical_matches(self, db_session):
        """Get all historical matches."""
        return get_historical_matches(db_session)

    @pytest.fixture(scope="class")
    def predictor(self, db_session):
        """Create predictor instance."""
        return BalanceMethodPredictor(db_session)

    def test_trueskill_baseline(self, db_session, historical_matches, predictor):
        """Test TrueSkill baseline accuracy."""
        report = run_regression(
            db_session, "TrueSkill", predictor.predict_trueskill, historical_matches
        )

        print(f"\n{'=' * 60}")
        print(f"TRUESKILL BASELINE")
        print(f"{'=' * 60}")
        print(f"Total Matches: {report.total_matches}")
        print(f"Accuracy: {report.accuracy:.1%}")
        print(f"High Confidence Accuracy: {report.high_confidence_accuracy:.1%}")
        print(f"Low Confidence Accuracy: {report.low_confidence_accuracy:.1%}")

        # TrueSkill should be better than random (50%)
        assert report.accuracy > 0.50, (
            f"TrueSkill accuracy {report.accuracy:.1%} should be > 50%"
        )

    def test_session_weighted(self, db_session, historical_matches, predictor):
        """Test session-weighted MMR accuracy."""
        report = run_regression(
            db_session,
            "Session-Weighted",
            predictor.predict_session,
            historical_matches,
        )

        print(f"\n{'=' * 60}")
        print(f"SESSION-WEIGHTED MMR")
        print(f"{'=' * 60}")
        print(f"Total Matches: {report.total_matches}")
        print(f"Accuracy: {report.accuracy:.1%}")
        print(f"High Confidence Accuracy: {report.high_confidence_accuracy:.1%}")
        print(f"Low Confidence Accuracy: {report.low_confidence_accuracy:.1%}")

        assert report.accuracy > 0.50, (
            f"Session accuracy {report.accuracy:.1%} should be > 50%"
        )

    def test_ml_metrics(self, db_session, historical_matches, predictor):
        """Test ML-metrics accuracy with default weights."""
        report = run_regression(
            db_session, "ML-Metrics", predictor.predict_ml_metrics, historical_matches
        )

        print(f"\n{'=' * 60}")
        print(f"ML-METRICS (Default Weights)")
        print(f"{'=' * 60}")
        print(f"Weights: {ComponentAccuracyTracker.DEFAULT_WEIGHTS}")
        print(f"Total Matches: {report.total_matches}")
        print(f"Accuracy: {report.accuracy:.1%}")
        print(f"High Confidence Accuracy: {report.high_confidence_accuracy:.1%}")
        print(f"Low Confidence Accuracy: {report.low_confidence_accuracy:.1%}")

        assert report.accuracy > 0.50, (
            f"ML-Metrics accuracy {report.accuracy:.1%} should be > 50%"
        )

    def test_component_regression(self, db_session, historical_matches, predictor):
        """Test individual component predictive power."""
        component_acc = run_component_regression(
            db_session, historical_matches, predictor
        )

        print(f"\n{'=' * 60}")
        print(f"COMPONENT-LEVEL REGRESSION")
        print(f"{'=' * 60}")
        print("Individual component accuracy when used in isolation:")
        for component, acc in sorted(component_acc.items(), key=lambda x: -x[1]):
            print(f"  {component}: {acc:.1%}")

        # At least session_mmr should be predictive
        assert component_acc["session_mmr"] > 0.50, "session_mmr should be predictive"

    def test_method_comparison(self, db_session, historical_matches, predictor):
        """Compare all methods and print summary."""
        methods = [
            ("TrueSkill", predictor.predict_trueskill),
            ("Session-Weighted", predictor.predict_session),
            ("ML-Metrics", predictor.predict_ml_metrics),
        ]

        reports = []
        for name, fn in methods:
            report = run_regression(db_session, name, fn, historical_matches)
            reports.append(report)

        print(f"\n{'=' * 60}")
        print(f"METHOD COMPARISON SUMMARY")
        print(f"{'=' * 60}")
        print(f"{'Method':<20} {'Accuracy':>10} {'High Conf':>12} {'Low Conf':>10}")
        print("-" * 60)

        best_method = max(reports, key=lambda r: r.accuracy)
        for r in reports:
            marker = " *" if r == best_method else ""
            print(
                f"{r.method_name:<20} {r.accuracy:>9.1%} {r.high_confidence_accuracy:>11.1%} {r.low_confidence_accuracy:>9.1%}{marker}"
            )

        print(f"\n* Best method: {best_method.method_name}")

        # ML-Metrics should be competitive with TrueSkill
        trueskill_acc = next(
            r.accuracy for r in reports if r.method_name == "TrueSkill"
        )
        ml_acc = next(r.accuracy for r in reports if r.method_name == "ML-Metrics")

        # Allow ML to be within 5% of TrueSkill (it may or may not beat it depending on data)
        assert ml_acc >= trueskill_acc - 0.05, (
            f"ML-Metrics ({ml_acc:.1%}) should be within 5% of TrueSkill ({trueskill_acc:.1%})"
        )


def run_standalone():
    """Run regression as standalone script with detailed output."""
    engine = create_engine("sqlite:///data/sc2mmr.db")
    Session = sessionmaker(bind=engine)
    db = Session()

    print("\n" + "=" * 70)
    print("BALANCE METHOD REGRESSION TEST")
    print("=" * 70)

    matches = get_historical_matches(db)
    print(f"\nLoaded {len(matches)} historical matches for analysis")

    predictor = BalanceMethodPredictor(db)

    # Run all methods
    methods = [
        ("TrueSkill (Baseline)", predictor.predict_trueskill),
        ("Session-Weighted", predictor.predict_session),
        ("ML-Metrics", predictor.predict_ml_metrics),
    ]

    reports = []
    for name, fn in methods:
        report = run_regression(db, name, fn, matches)
        reports.append(report)

    # Print summary
    print(f"\n{'=' * 70}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 70}")
    print(f"\n{'Method':<25} {'Accuracy':>10} {'High Conf':>12} {'Low Conf':>10}")
    print("-" * 60)

    for r in sorted(reports, key=lambda x: -x.accuracy):
        print(
            f"{r.method_name:<25} {r.accuracy:>9.1%} {r.high_confidence_accuracy:>11.1%} {r.low_confidence_accuracy:>9.1%}"
        )

    # Component regression
    print(f"\n{'=' * 70}")
    print("COMPONENT REGRESSION (ML-Metrics)")
    print(f"{'=' * 70}")
    component_acc = run_component_regression(db, matches, predictor)
    print("\nPredictive power of each component in isolation:")
    for component, acc in sorted(component_acc.items(), key=lambda x: -x[1]):
        bar = "#" * int(acc * 50)
        print(f"  {component:<15} {acc:>6.1%} {bar}")

    # Recommendations
    print(f"\n{'=' * 70}")
    print("ANALYSIS")
    print(f"{'=' * 70}")

    best = max(reports, key=lambda r: r.accuracy)
    trueskill_acc = next(r.accuracy for r in reports if "TrueSkill" in r.method_name)
    ml_acc = next(r.accuracy for r in reports if "ML-Metrics" in r.method_name)

    print(f"\nBest performing method: {best.method_name} ({best.accuracy:.1%})")
    print(
        f"ML-Metrics vs TrueSkill: {'+' if ml_acc > trueskill_acc else ''}{(ml_acc - trueskill_acc) * 100:.1f}%"
    )

    if ml_acc > trueskill_acc:
        print("\nML-Metrics OUTPERFORMS TrueSkill baseline.")
    elif ml_acc >= trueskill_acc - 0.02:
        print("\nML-Metrics performs COMPARABLY to TrueSkill.")
    else:
        print("\nML-Metrics underperforms TrueSkill. Consider weight tuning.")

    db.close()


if __name__ == "__main__":
    run_standalone()
