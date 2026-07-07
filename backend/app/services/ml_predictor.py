"""
ML win-prediction lab, NOT a production balance dependency.

This module is a data-pipeline/model-fitting learning area, kept and
maintained for that purpose after rigorous re-validation (2026-07-06,
see .moai/docs/ml-model-findings.md) showed the win predictor here does not
beat "the team with the higher summed MMR wins" at current data volume
(n=833: 65.8% CV vs 66.3% baseline; McNemar p=0.76). The team balancer
(app/balancer.py) does not depend on this module for its default behavior -
its one optional ML re-rank path defaults off (use_ml=False) and degrades
gracefully if this model isn't trained.

Treat results from here as a lab exercise, not a proven feature: any new
accuracy claim needs the same rigor as the entries in ml-model-findings.md
(fresh baseline, cross-validation, leak audit) before it means anything -
see sc2mmr-research-methodology and sc2mmr-proof-and-analysis-toolkit.
"""
import logging
import math
import pickle
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Match, MatchPlayer, Player, PlayerMatchMetrics

logger = logging.getLogger(__name__)


@dataclass
class TeamFeatures:
    avg_mmr: float = 0.0
    avg_recency_mmr: float = 0.0
    max_mmr: float = 0.0
    mmr_spread: float = 0.0
    mmr_std: float = 0.0
    team_size: int = 0
    total_games: int = 0
    avg_win_rate: float = 0.5
    avg_recent_win_rate: float = 0.5
    avg_win_streak: float = 0.0
    micro_composite: float = 50.0
    macro_composite: float = 50.0
    avg_aggression: float = 50.0
    avg_first_damage_timing: float = 300.0
    avg_teamfight_participation: float = 0.5
    avg_apm: float = 100.0
    avg_damage_ratio: float = 1.0
    avg_early_game_pct: float = 0.33
    avg_late_game_pct: float = 0.33
    army_diversity: float = 0.5
    tech_level: float = 0.5
    avg_unit_efficiency: float = 1.0
    performance_variance: float = 0.0
    form_trend: float = 0.0
    avg_minerals: float = 5000.0
    avg_supply_block: float = 20.0
    avg_first_expansion: float = 120.0
    avg_army_built: float = 5000.0


class FeatureExtractor:
    HIGH_TIER_UNITS = {
        "Battlecruiser",
        "Thor",
        "Raven",
        "Banshee",
        "Liberator",
        "Ghost",
        "Carrier",
        "Tempest",
        "Mothership",
        "Colossus",
        "Disruptor",
        "HighTemplar",
        "Archon",
        "Ultralisk",
        "BroodLord",
        "Viper",
        "Infestor",
        "Lurker",
    }

    @staticmethod
    def get_player_win_streak(db: Session, player_id: int, max_games: int = 10) -> int:
        recent_matches = (
            db.query(MatchPlayer)
            .filter(MatchPlayer.player_id == player_id)
            .join(Match)
            .order_by(Match.played_at.desc())
            .limit(max_games)
            .all()
        )
        streak = 0
        for mp in recent_matches:
            if mp.won:
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def get_recent_win_rate(db: Session, player_id: int, days: int = 30) -> float:
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_matches = (
            db.query(MatchPlayer)
            .filter(MatchPlayer.player_id == player_id)
            .join(Match)
            .filter(Match.played_at >= cutoff)
            .all()
        )
        if not recent_matches:
            return 0.5
        wins = sum(1 for mp in recent_matches if mp.won)
        return wins / len(recent_matches)

    @staticmethod
    def calculate_army_diversity(unit_composition: Dict[str, int]) -> float:
        if not unit_composition:
            return 0.5
        non_combat = {
            "SCV",
            "Probe",
            "Drone",
            "Overlord",
            "Larva",
            "Egg",
            "SupplyDepot",
            "Pylon",
        }
        combat_units = {
            k: v for k, v in unit_composition.items() if k not in non_combat and v > 0
        }
        if not combat_units:
            return 0.5
        total = sum(combat_units.values())
        if total == 0:
            return 0.5
        entropy = 0.0
        for count in combat_units.values():
            if count > 0:
                p = count / total
                entropy -= p * np.log2(p)
        max_entropy = np.log2(len(combat_units)) if len(combat_units) > 1 else 1
        return min(entropy / max_entropy, 1.0) if max_entropy > 0 else 0.5

    @staticmethod
    def calculate_tech_level(unit_composition: Dict[str, int]) -> float:
        if not unit_composition:
            return 0.5
        non_combat = {"SCV", "Probe", "Drone", "Overlord", "Larva", "Egg"}
        combat_units = {
            k: v for k, v in unit_composition.items() if k not in non_combat and v > 0
        }
        total = sum(combat_units.values())
        if total == 0:
            return 0.5
        high_tier_count = sum(
            v for k, v in combat_units.items() if k in FeatureExtractor.HIGH_TIER_UNITS
        )
        return high_tier_count / total

    @staticmethod
    def calculate_unit_efficiency(
        damage_dealt: float, army_value_built: float
    ) -> float:
        if army_value_built <= 0:
            return 1.0
        return min(damage_dealt / army_value_built, 5.0)

    @staticmethod
    def calculate_form_metrics(
        db: Session, player_id: int, limit: int = 10
    ) -> Tuple[float, float]:
        from ..models import MatchPlayer as MP

        recent_metrics = (
            db.query(PlayerMatchMetrics)
            .join(MP, PlayerMatchMetrics.match_player_id == MP.id)
            .filter(MP.player_id == player_id)
            .order_by(MP.id.desc())
            .limit(limit)
            .all()
        )
        if len(recent_metrics) < 3:
            return 0.0, 0.0
        scores = [float(m.overall_impact or 50) for m in recent_metrics]
        variance = float(np.std(scores)) / 25.0
        x = np.arange(len(scores))
        if len(scores) > 1:
            slope = np.polyfit(x, scores, 1)[0]
            trend = slope / 10.0
        else:
            trend = 0.0
        return min(variance, 2.0), max(min(trend, 1.0), -1.0)

    @staticmethod
    def get_player_match_metrics_avg(
        db: Session, player_id: int, limit: int = 20
    ) -> Dict[str, float]:
        from ..models import MatchPlayer as MP, PerformanceFeatures
        import json

        recent_data = (
            db.query(PlayerMatchMetrics, PerformanceFeatures)
            .join(MP, PlayerMatchMetrics.match_player_id == MP.id)
            .outerjoin(
                PerformanceFeatures, PerformanceFeatures.match_player_id == MP.id
            )
            .filter(MP.player_id == player_id)
            .order_by(MP.id.desc())
            .limit(limit)
            .all()
        )
        defaults = {
            "aggression": 50.0,
            "first_damage_timing": 300.0,
            "teamfight_participation": 0.5,
            "apm": 100.0,
            "damage_ratio": 1.0,
            "early_game_pct": 0.33,
            "late_game_pct": 0.33,
            "combat_score": 50.0,
            "economic_score": 50.0,
            "efficiency_score": 50.0,
            "overall_impact": 50.0,
            "army_diversity": 0.5,
            "tech_level": 0.5,
            "unit_efficiency": 1.0,
            "performance_variance": 0.0,
            "form_trend": 0.0,
            "minerals_collected": 5000.0,
            "supply_block_seconds": 20.0,
            "first_expansion_timing": 120.0,
            "army_value_built": 5000.0,
        }
        if not recent_data:
            return defaults
        agg_sums = {k: 0.0 for k in defaults.keys()}
        count = 0
        for m, pf in recent_data:
            count += 1
            agg_sums["aggression"] += float(m.aggression_score or 50)
            agg_sums["first_damage_timing"] += float(m.first_damage_timing or 300)
            agg_sums["teamfight_participation"] += float(
                m.team_fight_participation or 0.5
            )
            agg_sums["apm"] += float(m.apm or 100)
            agg_sums["damage_ratio"] += min(float(m.damage_ratio or 1.0), 10.0)
            agg_sums["combat_score"] += float(m.combat_score or 50)
            agg_sums["economic_score"] += float(m.economic_score or 50)
            agg_sums["efficiency_score"] += float(m.efficiency_score or 50)
            agg_sums["overall_impact"] += float(m.overall_impact or 50)
            total_dmg = float(
                (m.early_game_damage or 0)
                + (m.mid_game_damage or 0)
                + (m.late_game_damage or 0)
            )
            if total_dmg > 0:
                agg_sums["early_game_pct"] += (
                    float(m.early_game_damage or 0) / total_dmg
                )
                agg_sums["late_game_pct"] += float(m.late_game_damage or 0) / total_dmg
            else:
                agg_sums["early_game_pct"] += 0.33
                agg_sums["late_game_pct"] += 0.33
            if m.unit_composition:
                comp = (
                    m.unit_composition
                    if isinstance(m.unit_composition, dict)
                    else json.loads(m.unit_composition)
                )
                agg_sums["army_diversity"] += FeatureExtractor.calculate_army_diversity(
                    comp
                )
                agg_sums["tech_level"] += FeatureExtractor.calculate_tech_level(comp)
            else:
                agg_sums["army_diversity"] += 0.5
                agg_sums["tech_level"] += 0.5
            agg_sums["unit_efficiency"] += FeatureExtractor.calculate_unit_efficiency(
                float(m.damage_dealt or 0), float(m.army_value_built or 1)
            )
            agg_sums["minerals_collected"] += float(m.minerals_collected or 5000)
            agg_sums["supply_block_seconds"] += float(
                pf.supply_block_seconds if pf else 20
            )
            agg_sums["first_expansion_timing"] += float(m.first_expansion_timing or 120)
            agg_sums["army_value_built"] += float(m.army_value_built or 5000)

        if count == 0:
            count = 1
        results = {k: v / count for k, v in agg_sums.items()}
        perf_variance, form_trend = FeatureExtractor.calculate_form_metrics(
            db, player_id
        )
        results["performance_variance"] = perf_variance
        results["form_trend"] = form_trend
        return results

    @staticmethod
    def extract_team_features(db: Session, player_ids: List[int]) -> TeamFeatures:
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        if not players:
            return TeamFeatures()
        features = TeamFeatures()
        features.team_size = len(players)
        mmrs, win_streaks = [], []
        totals = {
            k: 0.0
            for k in [
                "aggression",
                "timing",
                "tf",
                "apm",
                "dmg_ratio",
                "early_pct",
                "late_pct",
                "combat",
                "economic",
                "efficiency",
                "impact",
                "diversity",
                "tech",
                "unit_eff",
                "variance",
                "trend",
                "minerals",
                "supply",
                "first_exp",
                "army_built",
            ]
        }
        for player in players:
            mmr = player.mmr or 1000
            mmrs.append(mmr)
            features.avg_mmr += mmr
            features.avg_recency_mmr += player.recency_weighted_mmr or mmr
            features.total_games += player.total_games or 0
            features.avg_win_rate += player.win_rate if player.win_rate else 0.5
            features.avg_recent_win_rate += FeatureExtractor.get_recent_win_rate(
                db, player.id
            )
            win_streaks.append(FeatureExtractor.get_player_win_streak(db, player.id))
            m = FeatureExtractor.get_player_match_metrics_avg(db, player.id)
            totals["aggression"] += m["aggression"]
            totals["timing"] += m["first_damage_timing"]
            totals["tf"] += m["teamfight_participation"]
            totals["apm"] += m["apm"]
            totals["dmg_ratio"] += m["damage_ratio"]
            totals["early_pct"] += m["early_game_pct"]
            totals["late_pct"] += m["late_game_pct"]
            totals["combat"] += m["combat_score"]
            totals["economic"] += m["economic_score"]
            totals["efficiency"] += m["efficiency_score"]
            totals["impact"] += m["overall_impact"]
            totals["diversity"] += m["army_diversity"]
            totals["tech"] += m["tech_level"]
            totals["unit_eff"] += m["unit_efficiency"]
            totals["variance"] += m["performance_variance"]
            totals["trend"] += m["form_trend"]
            totals["minerals"] += m["minerals_collected"]
            totals["supply"] += m["supply_block_seconds"]
            totals["first_exp"] += m["first_expansion_timing"]
            totals["army_built"] += m["army_value_built"]

        n = len(players)
        if n > 0:
            features.avg_mmr /= n
            features.avg_recency_mmr /= n
            features.avg_win_rate /= n
            features.avg_recent_win_rate /= n
            features.avg_win_streak = sum(win_streaks) / n
            features.avg_aggression = totals["aggression"] / n
            features.avg_first_damage_timing = totals["timing"] / n
            features.avg_teamfight_participation = totals["tf"] / n
            features.avg_apm = totals["apm"] / n
            features.avg_damage_ratio = totals["dmg_ratio"] / n
            features.avg_early_game_pct = totals["early_pct"] / n
            features.avg_late_game_pct = totals["late_pct"] / n
            features.micro_composite = totals["combat"] / n
            features.macro_composite = totals["economic"] / n
            features.army_diversity = totals["diversity"] / n
            features.tech_level = totals["tech"] / n
            features.avg_unit_efficiency = totals["unit_eff"] / n
            features.performance_variance = totals["variance"] / n
            features.form_trend = totals["trend"] / n
            features.avg_minerals = totals["minerals"] / n
            features.avg_supply_block = totals["supply"] / n
            features.avg_first_expansion = totals["first_exp"] / n
            features.avg_army_built = totals["army_built"] / n
        features.max_mmr = max(mmrs) if mmrs else 0
        features.mmr_spread = (max(mmrs) - min(mmrs)) if mmrs else 0
        features.mmr_std = float(np.std(mmrs)) if len(mmrs) > 1 else 0
        return features

    FEATURE_NAMES = [
        "experience_diff",
        "sum_mmr_diff",
        "win_rate_diff",
        "combat_diff",
        "teamfight_diff",
        "aggression_diff",
        "minerals_diff",
        "supply_block_diff",
        "max_mmr_diff",
        "team_size_diff",
        "form_trend_diff",
        "spending_diff",
    ]

    @staticmethod
    def create_match_features(team1: TeamFeatures, team2: TeamFeatures) -> np.ndarray:
        return np.array(
            [
                (team1.total_games - team2.total_games) / 100,
                ((team1.avg_mmr * team1.team_size) - (team2.avg_mmr * team2.team_size))
                / 800,
                team1.avg_win_rate - team2.avg_win_rate,
                (team1.micro_composite - team2.micro_composite) / 50,
                team1.avg_teamfight_participation - team2.avg_teamfight_participation,
                (team2.avg_aggression - team1.avg_aggression) / 50,
                (team1.avg_minerals - team2.avg_minerals) / 1000,
                (team2.avg_supply_block - team1.avg_supply_block) / 30,
                (team1.max_mmr - team2.max_mmr) / 500,
                team1.team_size - team2.team_size,
                team1.form_trend - team2.form_trend,
                (team1.macro_composite - team2.macro_composite) / 50,
            ]
        )


def build_chronological_dataset(
    db: Session, window: int = 20, form_window: int = 10
) -> Tuple[np.ndarray, np.ndarray, List[int]]:
    """
    Build a leak-free (X, y) training set for match-outcome prediction.

    FeatureExtractor.extract_team_features() is fine for predict() on an
    upcoming match (current player state IS the correct historical-up-to-now
    state there), but using it to featurize PAST matches for training is a
    lookahead leak: it reads today's Player.mmr/win_rate and unbounded
    "recent N" queries, which already contain the outcome of the match being
    predicted and everything since. This walks matches chronologically and
    keeps in-memory per-player rolling state that is only ever updated AFTER
    a match's feature vector has been built, so match N's features reflect
    only matches < N. See .moai/docs/ml-model-findings.md, 2026-07-06 entry,
    for the validation that found this (and confirmed removing it changes
    the accuracy verdict).

    mmr uses match_players.mmr_before directly (already a correct pre-match
    snapshot) rather than a reconstructed proxy.
    """
    matches = (
        db.query(Match)
        .filter(Match.played_at.isnot(None))
        .order_by(Match.played_at.asc(), Match.id.asc())
        .all()
    )

    total_games: Dict[int, int] = defaultdict(int)
    wins: Dict[int, int] = defaultdict(int)
    metric_hist: Dict[int, Any] = defaultdict(lambda: deque(maxlen=window))
    impact_hist: Dict[int, Any] = defaultdict(lambda: deque(maxlen=form_window))

    def player_state(pid: int) -> Dict[str, float]:
        games = total_games[pid]
        win_rate = wins[pid] / games if games > 0 else 0.5
        hist = metric_hist[pid]
        if hist:
            combat = sum(h["combat"] for h in hist) / len(hist)
            econ = sum(h["econ"] for h in hist) / len(hist)
            tf = sum(h["tf"] for h in hist) / len(hist)
            aggro = sum(h["aggro"] for h in hist) / len(hist)
            minerals = sum(h["minerals"] for h in hist) / len(hist)
            supply = sum(h["supply"] for h in hist) / len(hist)
        else:
            combat, econ, tf, aggro = 50.0, 50.0, 0.5, 50.0
            minerals, supply = 5000.0, 20.0
        impacts = list(impact_hist[pid])
        if len(impacts) >= 3:
            slope = float(np.polyfit(np.arange(len(impacts)), impacts, 1)[0])
            form_trend = max(min(slope / 10.0, 1.0), -1.0)
        else:
            form_trend = 0.0
        return dict(
            total_games=games, win_rate=win_rate, combat=combat, econ=econ,
            tf=tf, aggro=aggro, minerals=minerals, supply=supply,
            form_trend=form_trend,
        )

    def team_state(rows: List[Tuple[int, float]]) -> Dict[str, float]:
        n = len(rows)
        states = [player_state(pid) for pid, _ in rows]
        mmrs = [mmr for _, mmr in rows]
        return dict(
            total_games=sum(s["total_games"] for s in states),
            avg_mmr=sum(mmrs) / n,
            team_size=n,
            avg_win_rate=sum(s["win_rate"] for s in states) / n,
            micro_composite=sum(s["combat"] for s in states) / n,
            macro_composite=sum(s["econ"] for s in states) / n,
            avg_teamfight_participation=sum(s["tf"] for s in states) / n,
            avg_aggression=sum(s["aggro"] for s in states) / n,
            avg_minerals=sum(s["minerals"] for s in states) / n,
            avg_supply_block=sum(s["supply"] for s in states) / n,
            max_mmr=max(mmrs),
            form_trend=sum(s["form_trend"] for s in states) / n,
        )

    def feature_vector(t1: Dict[str, float], t2: Dict[str, float]) -> np.ndarray:
        return np.array([
            (t1["total_games"] - t2["total_games"]) / 100,
            ((t1["avg_mmr"] * t1["team_size"]) - (t2["avg_mmr"] * t2["team_size"])) / 800,
            t1["avg_win_rate"] - t2["avg_win_rate"],
            (t1["micro_composite"] - t2["micro_composite"]) / 50,
            t1["avg_teamfight_participation"] - t2["avg_teamfight_participation"],
            (t2["avg_aggression"] - t1["avg_aggression"]) / 50,
            (t1["avg_minerals"] - t2["avg_minerals"]) / 1000,
            (t2["avg_supply_block"] - t1["avg_supply_block"]) / 30,
            (t1["max_mmr"] - t2["max_mmr"]) / 500,
            t1["team_size"] - t2["team_size"],
            t1["form_trend"] - t2["form_trend"],
            (t1["macro_composite"] - t2["macro_composite"]) / 50,
        ])

    X: List[np.ndarray] = []
    y: List[int] = []
    match_ids: List[int] = []

    for match in matches:
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )
        team1 = [
            (mp.player_id, mp.mmr_before if mp.mmr_before is not None else 1000.0)
            for mp in match_players if mp.team_number == 1
        ]
        team2 = [
            (mp.player_id, mp.mmr_before if mp.mmr_before is not None else 1000.0)
            for mp in match_players if mp.team_number == 2
        ]
        winner = next((mp.team_number for mp in match_players if mp.won), None)
        if not team1 or not team2 or winner is None:
            continue

        X.append(feature_vector(team_state(team1), team_state(team2)))
        y.append(1 if winner == 1 else 0)
        match_ids.append(match.id)

        # Update rolling state AFTER building this match's feature vector.
        pmm_rows = (
            db.query(PlayerMatchMetrics, MatchPlayer.player_id)
            .join(MatchPlayer, PlayerMatchMetrics.match_player_id == MatchPlayer.id)
            .filter(MatchPlayer.match_id == match.id)
            .all()
        )
        metrics_by_player = {
            pid: dict(
                combat=float(pmm.combat_score) if pmm.combat_score is not None else 50.0,
                econ=float(pmm.economic_score) if pmm.economic_score is not None else 50.0,
                tf=float(pmm.team_fight_participation) if pmm.team_fight_participation is not None else 0.5,
                aggro=float(pmm.aggression_score) if pmm.aggression_score is not None else 50.0,
                minerals=float(pmm.minerals_collected) if pmm.minerals_collected is not None else 5000.0,
                supply=float(pmm.supply_block_seconds) if pmm.supply_block_seconds is not None else 20.0,
                impact=float(pmm.overall_impact) if pmm.overall_impact is not None else 50.0,
            )
            for pmm, pid in pmm_rows
        }
        for team_num, rows in ((1, team1), (2, team2)):
            won_team = team_num == winner
            for pid, _ in rows:
                total_games[pid] += 1
                if won_team:
                    wins[pid] += 1
                m = metrics_by_player.get(pid)
                if m:
                    metric_hist[pid].append(m)
                    impact_hist[pid].append(m["impact"])

    return np.array(X), np.array(y), match_ids


class MLPredictor:
    MODEL_PATH = Path(__file__).parent.parent.parent / "data" / "xgboost_model.pkl"

    def __init__(self):
        self.model: Any = None
        self.is_xgboost = False
        self.is_trained = False
        self.training_accuracy = 0.0
        self.feature_importance: Dict[str, float] = {}
        self.shap_importance: Dict[str, float] = {}

    def _get_model(self):
        from sklearn.linear_model import LogisticRegression

        self.is_xgboost = False
        return LogisticRegression(max_iter=1000, C=1.0, random_state=42)

    def train(self, db: Session, min_matches: int = 10) -> Dict[str, Any]:
        """
        Train on a leak-free chronological feature set (build_chronological_dataset)
        rather than current-player-state features - see that function's docstring
        and .moai/docs/ml-model-findings.md (2026-07-06) for why the previous
        approach's self-reported accuracy was not trustworthy. Reports 5-fold CV
        accuracy (honest, out-of-sample) alongside the same-data baseline
        ("higher summed MMR wins") rather than a single train/test split -
        never report accuracy without the baseline next to it.
        """
        from sklearn.model_selection import StratifiedKFold, cross_val_score

        X_arr, y_arr, _ = build_chronological_dataset(db)
        if len(X_arr) < min_matches:
            return {
                "status": "insufficient_valid_data",
                "valid_matches": len(X_arr),
                "required": min_matches,
            }

        # Baseline: same feature set's sum_mmr_diff sign (index 1), which is
        # leak-free by construction here (mmr_before-derived).
        mmr_diff_idx = FeatureExtractor.FEATURE_NAMES.index("sum_mmr_diff")
        decided = X_arr[:, mmr_diff_idx] != 0
        baseline_accuracy = (
            float(np.mean((X_arr[decided, mmr_diff_idx] > 0) == (y_arr[decided] == 1)))
            if decided.any()
            else None
        )

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(self._get_model(), X_arr, y_arr, cv=cv)
        self.training_accuracy = float(cv_scores.mean())

        # CV estimates out-of-sample accuracy; the deployed model is then fit
        # on all available data (standard practice - CV to evaluate, full fit
        # to ship).
        self.model = self._get_model()
        self.model.fit(X_arr, y_arr)
        self.is_trained = True
        self.feature_importance = dict(
            zip(FeatureExtractor.FEATURE_NAMES, np.abs(self.model.coef_[0]).tolist())
        )
        self._save_model()
        return {
            "status": "success",
            "model_type": "LogisticRegression",
            "samples": len(X_arr),
            "cv_folds": 5,
            "cv_accuracy": round(self.training_accuracy * 100, 1),
            "baseline_accuracy": round(baseline_accuracy * 100, 1) if baseline_accuracy is not None else None,
            # Kept for frontend/API backward-compatibility; both now report
            # the same honest CV figure rather than a leaky train/test split.
            "train_accuracy": round(self.training_accuracy * 100, 1),
            "test_accuracy": round(self.training_accuracy * 100, 1),
            "feature_importance": {
                k: round(v, 4)
                for k, v in sorted(
                    self.feature_importance.items(), key=lambda x: -x[1]
                )[:5]
            },
        }

    def explain_prediction(
        self, feature_vector: np.ndarray, db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        if not self.is_trained or self.model is None:
            return []
        feature_names = FeatureExtractor.FEATURE_NAMES
        results = []
        try:
            if not self.is_xgboost and hasattr(self.model, "coef_"):
                coefs, vals = self.model.coef_[0], feature_vector[0]
                for name, coef, val in zip(feature_names, coefs, vals):
                    impact = float(coef * val)
                    results.append(
                        {"feature": name, "impact": impact, "magnitude": abs(impact)}
                    )
            else:
                import shap
                from .shap_feature_importance import SHAPFeatureImportance

                explainer_wrapper = SHAPFeatureImportance(self.model, feature_names)
                explainer_wrapper.explainer = (
                    shap.TreeExplainer(self.model)
                    if self.is_xgboost
                    else shap.Explainer(self.model, feature_vector)
                )
                shap_values = explainer_wrapper.explain(
                    feature_vector, output_format="array"
                )
                impacts_arr = (
                    shap_values[0, :, 1]
                    if len(shap_values.shape) == 3
                    else shap_values[0]
                    if len(shap_values.shape) == 2
                    else shap_values
                )
                for name, val in zip(feature_names, impacts_arr):
                    results.append(
                        {
                            "feature": name,
                            "impact": float(val),
                            "magnitude": abs(float(val)),
                        }
                    )
            results.sort(key=lambda x: x["magnitude"], reverse=True)
            return results
        except Exception as e:
            logger.error(f"Explanation failed: {e}")
            return []

    def predict(
        self, db: Session, team1_ids: List[int], team2_ids: List[int]
    ) -> Dict[str, Any]:
        if not self.is_trained:
            self._load_model()
        if self.model is None:
            return {
                "error": "Model not trained",
                "team_1_win_probability": 50.0,
                "team_2_win_probability": 50.0,
            }
        t1_f, t2_f = (
            FeatureExtractor.extract_team_features(db, team1_ids),
            FeatureExtractor.extract_team_features(db, team2_ids),
        )
        fv = FeatureExtractor.create_match_features(t1_f, t2_f).reshape(1, -1)
        team1_prob = (
            float(self.model.predict_proba(fv)[0][1]) * 100
            if hasattr(self.model, "predict_proba")
            else (100.0 if self.model.predict(fv)[0] == 1 else 0.0)
        )
        confidence = abs(team1_prob - 50) / 50
        shap_explanations = self.explain_prediction(fv, db)
        key_factors = []
        for exp in shap_explanations[:3]:
            if exp["magnitude"] > 0.01:
                team = "Team 1" if exp["impact"] > 0 else "Team 2"
                factor = exp["feature"].replace("_diff", "").replace("_", " ").title()
                key_factors.append(f"{team} has advantage in {factor}")
        return {
            "predicted_winner": 1 if team1_prob >= 50 else 2,
            "team_1_win_probability": round(team1_prob, 1),
            "team_2_win_probability": round(100 - team1_prob, 1),
            "confidence": "High"
            if confidence > 0.4
            else "Medium"
            if confidence > 0.2
            else "Low",
            "model": f"{'XGBoost' if self.is_xgboost else 'LogisticRegression'} ({self.training_accuracy * 100:.1f}% accuracy)",
            "model_accuracy": round(self.training_accuracy * 100, 1),
            "key_factors": key_factors if key_factors else ["Evenly matched"],
            "shap_impacts": shap_explanations[:5],
        }

    def _save_model(self) -> None:
        try:
            self.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.MODEL_PATH, "wb") as f:
                pickle.dump(
                    {
                        "model": self.model,
                        "is_xgboost": self.is_xgboost,
                        "training_accuracy": self.training_accuracy,
                        "feature_importance": self.feature_importance,
                        "shap_importance": self.shap_importance,
                    },
                    f,
                )
            logger.info(f"Model saved to {self.MODEL_PATH}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def _load_model(self) -> bool:
        try:
            if self.MODEL_PATH.exists():
                with open(self.MODEL_PATH, "rb") as f:
                    data = pickle.load(f)
                    (
                        self.model,
                        self.is_xgboost,
                        self.training_accuracy,
                        self.feature_importance,
                        self.shap_importance,
                        self.is_trained,
                    ) = (
                        data["model"],
                        data["is_xgboost"],
                        data["training_accuracy"],
                        data.get("feature_importance", {}),
                        data.get("shap_importance", {}),
                        True,
                    )
                logger.info(f"Model loaded from {self.MODEL_PATH}")
                return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
        return False


_predictor_instance: Optional[MLPredictor] = None


def get_ml_predictor() -> MLPredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = MLPredictor()
    return _predictor_instance


def train_ml_model(db: Session) -> Dict[str, Any]:
    return get_ml_predictor().train(db)


def predict_with_ml(
    db: Session, team1_ids: List[int], team2_ids: List[int]
) -> Dict[str, Any]:
    return get_ml_predictor().predict(db, team1_ids, team2_ids)
