"""
Team balancing algorithm to create fair matches.

The balancer uses TrueSkill ratings to create balanced teams by:
1. Calculating all possible team combinations
2. Predicting match quality for each combination
3. Ranking by balance fairness
"""

from typing import List, Dict, Tuple, Optional, Any, cast
from itertools import combinations
from dataclasses import dataclass
import trueskill  # type: ignore
from sqlalchemy.orm import Session

from .models import Player


@dataclass
class PlayerInfo:
    """Player information for balancing."""

    id: int
    name: str
    mu: float
    sigma: float
    mmr: float  # Conservative rating: mu - 3*sigma
    overall_impact: float  # Average overall impact score
    total_games: int
    aggression_score: float = 50.0  # 0-100, higher = more aggressive playstyle

    @classmethod
    def from_player(cls, player: Player) -> "PlayerInfo":
        """Create PlayerInfo from Player model."""
        return cls(
            id=player.id,
            name=player.name,
            mu=player.mu,
            sigma=player.sigma,
            mmr=player.mmr,
            overall_impact=player.avg_overall_impact or 50.0,
            total_games=player.total_games,
            aggression_score=player.avg_aggression_score or 50.0,
        )


@dataclass
class TeamSuggestion:
    """Suggested team composition."""

    team_1: List[PlayerInfo]
    team_2: List[PlayerInfo]
    team_1_mmr: float
    team_2_mmr: float
    mmr_difference: float
    win_probability: float  # Probability team 1 wins
    match_quality: float  # 0-1, higher is better balanced
    ml_win_probability: Optional[float] = None
    team_1_avg_impact: float = 0.0  # Average impact score for team 1
    team_2_avg_impact: float = 0.0  # Average impact score for team 2
    impact_balance_score: float = (
        1.0  # How evenly high/low impact players are distributed
    )
    playstyle_balance_score: float = 1.0  # How evenly aggression styles are distributed


class TeamBalancer:
    """
    Creates balanced team compositions using TrueSkill.
    """

    @staticmethod
    def get_team_rating(players: List[PlayerInfo]) -> Tuple[float, float]:
        """Calculate combined team rating."""
        team_mu = sum(p.mu for p in players)
        team_sigma = (sum(p.sigma**2 for p in players)) ** 0.5
        return team_mu, team_sigma

    @staticmethod
    def calculate_match_quality(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo]
    ) -> float:
        """Calculate TrueSkill match quality (0-1)."""
        team_1_ratings = [trueskill.Rating(mu=p.mu, sigma=p.sigma) for p in team_1]
        team_2_ratings = [trueskill.Rating(mu=p.mu, sigma=p.sigma) for p in team_2]
        return trueskill.quality([team_1_ratings, team_2_ratings])

    @staticmethod
    def calculate_win_probability(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo]
    ) -> float:
        """Calculate probability that team 1 wins."""
        team_1_mu, team_1_sigma = TeamBalancer.get_team_rating(team_1)
        team_2_mu, team_2_sigma = TeamBalancer.get_team_rating(team_2)

        delta_mu = team_1_mu - team_2_mu
        sum_sigma = (team_1_sigma**2 + team_2_sigma**2) ** 0.5

        from math import erf, sqrt

        win_prob = 0.5 * (1 + erf(delta_mu / (sum_sigma * sqrt(2))))
        return win_prob

    @staticmethod
    def calculate_impact_balance_score(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo]
    ) -> Tuple[float, float, float]:
        """Calculate how evenly high-impact and low-impact players are distributed."""
        team_1_avg = (
            sum(p.overall_impact for p in team_1) / len(team_1) if team_1 else 0
        )
        team_2_avg = (
            sum(p.overall_impact for p in team_2) / len(team_2) if team_2 else 0
        )

        if team_1_avg == 0 and team_2_avg == 0:
            balance_score = 1.0
        else:
            max_avg = max(team_1_avg, team_2_avg)
            min_avg = min(team_1_avg, team_2_avg)
            balance_score = min_avg / max_avg if max_avg > 0 else 1.0

        return team_1_avg, team_2_avg, balance_score

    @staticmethod
    def calculate_playstyle_balance(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo]
    ) -> float:
        """Calculate playstyle balance score."""
        team_1_aggression = (
            sum(p.aggression_score for p in team_1) / len(team_1) if team_1 else 50
        )
        team_2_aggression = (
            sum(p.aggression_score for p in team_2) / len(team_2) if team_2 else 50
        )
        aggression_diff = abs(team_1_aggression - team_2_aggression)
        return 1.0 - (aggression_diff / 100.0)

    @staticmethod
    def generate_team_suggestions(
        players: List[PlayerInfo], top_n: int = 10
    ) -> List[TeamSuggestion]:
        num_players = len(players)
        if num_players < 2:
            raise ValueError(f"Need at least 2 players, got {num_players}")

        if num_players % 2 == 0:
            team_1_size = num_players // 2
        else:
            team_1_size = (num_players // 2) + 1

        suggestions = []
        for team_1_indices in combinations(range(num_players), team_1_size):
            team_1 = [players[i] for i in team_1_indices]
            team_2 = [players[i] for i in range(num_players) if i not in team_1_indices]

            team_1_mmr = sum(p.mmr for p in team_1)
            team_2_mmr = sum(p.mmr for p in team_2)
            mmr_difference = abs(team_1_mmr - team_2_mmr)
            match_quality = TeamBalancer.calculate_match_quality(team_1, team_2)
            win_probability = TeamBalancer.calculate_win_probability(team_1, team_2)
            t1_impact, t2_impact, impact_balance = (
                TeamBalancer.calculate_impact_balance_score(team_1, team_2)
            )
            playstyle_balance = TeamBalancer.calculate_playstyle_balance(team_1, team_2)

            suggestions.append(
                TeamSuggestion(
                    team_1=team_1,
                    team_2=team_2,
                    team_1_mmr=team_1_mmr,
                    team_2_mmr=team_2_mmr,
                    mmr_difference=mmr_difference,
                    win_probability=win_probability,
                    match_quality=match_quality,
                    team_1_avg_impact=t1_impact,
                    team_2_avg_impact=t2_impact,
                    impact_balance_score=impact_balance,
                    playstyle_balance_score=playstyle_balance,
                )
            )

        PLAYSTYLE_WEIGHT = 0.20
        suggestions.sort(
            key=lambda x: (
                -(
                    x.match_quality * (1 - PLAYSTYLE_WEIGHT)
                    + x.playstyle_balance_score * PLAYSTYLE_WEIGHT
                ),
                x.mmr_difference,
            )
        )

        return suggestions[:top_n]

    @staticmethod
    def balance_teams(
        db: Session, player_ids: List[int], top_n: int = 10
    ) -> List[TeamSuggestion]:
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        if len(players) != len(player_ids):
            found_ids = {p.id for p in players}
            missing_ids = set(player_ids) - found_ids
            raise ValueError(f"Players not found: {missing_ids}")

        player_infos = [PlayerInfo.from_player(p) for p in players]
        return TeamBalancer.generate_team_suggestions(player_infos, top_n)

    @staticmethod
    def quick_balance(db: Session, player_ids: List[int]) -> Optional[TeamSuggestion]:
        suggestions = TeamBalancer.balance_teams(db, player_ids, top_n=1)
        return suggestions[0] if suggestions else None

    @staticmethod
    def balance_with_impact_priority(
        db: Session, player_ids: List[int], top_n: int = 10, impact_weight: float = 0.5
    ) -> List[TeamSuggestion]:
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        if len(players) != len(player_ids):
            found_ids = {p.id for p in players}
            missing_ids = set(player_ids) - found_ids
            raise ValueError(f"Players not found: {missing_ids}")

        player_infos = [PlayerInfo.from_player(p) for p in players]
        suggestions = TeamBalancer.generate_team_suggestions(player_infos, top_n=100)

        for suggestion in suggestions:
            combined_score = (
                (1 - impact_weight) * suggestion.match_quality
                + impact_weight * suggestion.impact_balance_score
            )
            suggestion.match_quality = combined_score

        suggestions.sort(key=lambda x: -x.match_quality)
        return suggestions[:top_n]


class BalancerStats:
    """
    Utility to analyze and format team suggestions.
    """

    @staticmethod
    def analyze_suggestion(suggestion: TeamSuggestion) -> Dict[str, Any]:
        """
        Analyze a team suggestion and return detailed statistics.
        """
        team_1_mmrs = [p.mmr for p in suggestion.team_1]
        team_2_mmrs = [p.mmr for p in suggestion.team_2]

        team_1_total = sum(team_1_mmrs)
        team_2_total = sum(team_2_mmrs)

        team_1_avg = team_1_total / len(team_1_mmrs) if team_1_mmrs else 0
        team_2_avg = team_2_total / len(team_2_mmrs) if team_2_mmrs else 0

        # Calculate fairness rating string
        if suggestion.match_quality > 0.8:
            fairness = "Excellent"
        elif suggestion.match_quality > 0.6:
            fairness = "Good"
        elif suggestion.match_quality > 0.4:
            fairness = "Fair"
        else:
            fairness = "Poor"

        return {
            "team_1": {
                "total_mmr": round(team_1_total, 1),
                "avg_mmr": round(team_1_avg, 1),
            },
            "team_2": {
                "total_mmr": round(team_2_total, 1),
                "avg_mmr": round(team_2_avg, 1),
            },
            "balance": {
                "mmr_difference": round(suggestion.mmr_difference, 1),
                "match_quality": round(suggestion.match_quality * 100, 1),
                "win_probability_team_1": round(suggestion.win_probability * 100, 1),
                "win_probability_team_2": round(
                    (1.0 - suggestion.win_probability) * 100, 1
                ),
                "fairness_rating": fairness,
                "team_1_avg_impact": round(suggestion.team_1_avg_impact, 2),
                "team_2_avg_impact": round(suggestion.team_2_avg_impact, 2),
                "impact_balance_score": round(suggestion.impact_balance_score * 100, 1),
                "impact_difference": round(
                    abs(suggestion.team_1_avg_impact - suggestion.team_2_avg_impact), 2
                ),
            },
        }
