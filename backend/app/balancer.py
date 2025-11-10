"""
Team balancing algorithm to create fair matches.

The balancer uses TrueSkill ratings to create balanced teams by:
1. Calculating all possible team combinations
2. Predicting match quality for each combination
3. Ranking by balance fairness
"""
from typing import List, Dict, Tuple, Optional
from itertools import combinations
from dataclasses import dataclass
import trueskill
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

    @classmethod
    def from_player(cls, player: Player) -> 'PlayerInfo':
        """Create PlayerInfo from Player model."""
        return cls(
            id=player.id,
            name=player.name,
            mu=player.mu,
            sigma=player.sigma,
            mmr=player.mmr
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
    match_quality: float    # 0-1, higher is better balanced


class TeamBalancer:
    """
    Creates balanced team compositions using TrueSkill.
    """

    @staticmethod
    def get_team_rating(players: List[PlayerInfo]) -> Tuple[float, float]:
        """
        Calculate combined team rating.

        Args:
            players: List of PlayerInfo objects

        Returns:
            Tuple of (team_mu, team_sigma)
        """
        # Sum of individual mus
        team_mu = sum(p.mu for p in players)

        # Combined sigma (variance adds, so sqrt of sum of squares)
        team_sigma = (sum(p.sigma ** 2 for p in players)) ** 0.5

        return team_mu, team_sigma

    @staticmethod
    def calculate_match_quality(
        team_1: List[PlayerInfo],
        team_2: List[PlayerInfo]
    ) -> float:
        """
        Calculate TrueSkill match quality (0-1, higher is better).

        Match quality represents how "fair" or "balanced" a match is.
        Higher values mean the match is more competitive.

        Args:
            team_1: List of players on team 1
            team_2: List of players on team 2

        Returns:
            Match quality value between 0 and 1
        """
        # Create TrueSkill Rating objects
        team_1_ratings = [[trueskill.Rating(mu=p.mu, sigma=p.sigma) for p in team_1]]
        team_2_ratings = [[trueskill.Rating(mu=p.mu, sigma=p.sigma) for p in team_2]]

        # Calculate match quality
        quality = trueskill.quality([team_1_ratings[0], team_2_ratings[0]])

        return quality

    @staticmethod
    def calculate_win_probability(
        team_1: List[PlayerInfo],
        team_2: List[PlayerInfo]
    ) -> float:
        """
        Calculate probability that team 1 wins.

        Args:
            team_1: List of players on team 1
            team_2: List of players on team 2

        Returns:
            Probability (0-1) that team 1 wins
        """
        team_1_mu, team_1_sigma = TeamBalancer.get_team_rating(team_1)
        team_2_mu, team_2_sigma = TeamBalancer.get_team_rating(team_2)

        # Combined sigma for the match
        delta_mu = team_1_mu - team_2_mu
        sum_sigma = (team_1_sigma ** 2 + team_2_sigma ** 2) ** 0.5

        # Calculate win probability using cumulative normal distribution
        # We use the TrueSkill environment's cdf
        from math import erf, sqrt
        win_prob = 0.5 * (1 + erf(delta_mu / (sum_sigma * sqrt(2))))

        return win_prob

    @staticmethod
    def generate_team_suggestions(
        players: List[PlayerInfo],
        top_n: int = 10
    ) -> List[TeamSuggestion]:
        """
        Generate balanced team suggestions.

        Args:
            players: List of available players
            top_n: Number of top suggestions to return

        Returns:
            List of TeamSuggestion objects, sorted by match quality (best first)
        """
        num_players = len(players)

        # Validate even number of players
        if num_players % 2 != 0:
            raise ValueError(f"Need even number of players, got {num_players}")

        team_size = num_players // 2

        # Generate all possible team combinations
        suggestions = []

        # Get all combinations of team_size players for team 1
        # Team 2 is automatically the remaining players
        for team_1_indices in combinations(range(num_players), team_size):
            team_1 = [players[i] for i in team_1_indices]
            team_2 = [players[i] for i in range(num_players) if i not in team_1_indices]

            # Calculate team MMRs (conservative ratings)
            team_1_mmr = sum(p.mmr for p in team_1)
            team_2_mmr = sum(p.mmr for p in team_2)
            mmr_difference = abs(team_1_mmr - team_2_mmr)

            # Calculate match quality
            match_quality = TeamBalancer.calculate_match_quality(team_1, team_2)

            # Calculate win probability
            win_probability = TeamBalancer.calculate_win_probability(team_1, team_2)

            suggestions.append(TeamSuggestion(
                team_1=team_1,
                team_2=team_2,
                team_1_mmr=team_1_mmr,
                team_2_mmr=team_2_mmr,
                mmr_difference=mmr_difference,
                win_probability=win_probability,
                match_quality=match_quality
            ))

        # Sort by match quality (descending) and MMR difference (ascending)
        suggestions.sort(key=lambda x: (-x.match_quality, x.mmr_difference))

        return suggestions[:top_n]

    @staticmethod
    def balance_teams(
        db: Session,
        player_ids: List[int],
        top_n: int = 10
    ) -> List[TeamSuggestion]:
        """
        Balance teams for given player IDs.

        Args:
            db: Database session
            player_ids: List of player IDs to balance
            top_n: Number of suggestions to return

        Returns:
            List of TeamSuggestion objects
        """
        # Fetch players from database
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()

        if len(players) != len(player_ids):
            found_ids = {p.id for p in players}
            missing_ids = set(player_ids) - found_ids
            raise ValueError(f"Players not found: {missing_ids}")

        # Convert to PlayerInfo
        player_infos = [PlayerInfo.from_player(p) for p in players]

        # Generate suggestions
        return TeamBalancer.generate_team_suggestions(player_infos, top_n)

    @staticmethod
    def quick_balance(
        db: Session,
        player_ids: List[int]
    ) -> TeamSuggestion:
        """
        Get the single best balanced team composition.

        Args:
            db: Database session
            player_ids: List of player IDs to balance

        Returns:
            Best TeamSuggestion
        """
        suggestions = TeamBalancer.balance_teams(db, player_ids, top_n=1)
        return suggestions[0] if suggestions else None


class BalancerStats:
    """Statistics and analysis for team balancing."""

    @staticmethod
    def analyze_suggestion(suggestion: TeamSuggestion) -> Dict:
        """
        Provide detailed analysis of a team suggestion.

        Args:
            suggestion: TeamSuggestion to analyze

        Returns:
            Dictionary with analysis metrics
        """
        return {
            'team_1': {
                'players': [p.name for p in suggestion.team_1],
                'total_mmr': suggestion.team_1_mmr,
                'avg_mmr': suggestion.team_1_mmr / len(suggestion.team_1),
                'player_details': [
                    {
                        'name': p.name,
                        'mmr': p.mmr,
                        'mu': p.mu,
                        'sigma': p.sigma
                    }
                    for p in suggestion.team_1
                ]
            },
            'team_2': {
                'players': [p.name for p in suggestion.team_2],
                'total_mmr': suggestion.team_2_mmr,
                'avg_mmr': suggestion.team_2_mmr / len(suggestion.team_2),
                'player_details': [
                    {
                        'name': p.name,
                        'mmr': p.mmr,
                        'mu': p.mu,
                        'sigma': p.sigma
                    }
                    for p in suggestion.team_2
                ]
            },
            'balance': {
                'mmr_difference': suggestion.mmr_difference,
                'match_quality': suggestion.match_quality,
                'win_probability_team_1': suggestion.win_probability,
                'win_probability_team_2': 1 - suggestion.win_probability,
                'fairness_rating': _get_fairness_rating(suggestion.match_quality)
            }
        }

    @staticmethod
    def compare_suggestions(suggestions: List[TeamSuggestion]) -> List[Dict]:
        """
        Compare multiple team suggestions.

        Args:
            suggestions: List of TeamSuggestion objects

        Returns:
            List of analysis dictionaries
        """
        return [BalancerStats.analyze_suggestion(s) for s in suggestions]


def _get_fairness_rating(match_quality: float) -> str:
    """
    Convert match quality to human-readable fairness rating.

    Args:
        match_quality: Match quality value (0-1)

    Returns:
        Fairness rating string
    """
    if match_quality >= 0.9:
        return "Excellent"
    elif match_quality >= 0.75:
        return "Very Good"
    elif match_quality >= 0.6:
        return "Good"
    elif match_quality >= 0.4:
        return "Fair"
    else:
        return "Poor"
