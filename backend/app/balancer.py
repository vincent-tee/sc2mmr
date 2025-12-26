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
    overall_impact: float  # Average overall impact score
    total_games: int
    aggression_score: float = 50.0  # 0-100, higher = more aggressive playstyle

    @classmethod
    def from_player(cls, player: Player) -> 'PlayerInfo':
        """Create PlayerInfo from Player model."""
        return cls(
            id=player.id,
            name=player.name,
            mu=player.mu,
            sigma=player.sigma,
            mmr=player.mmr,
            overall_impact=player.avg_overall_impact or 50.0,
            total_games=player.total_games,
            aggression_score=player.avg_aggression_score or 50.0
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
    team_1_avg_impact: float = 0.0  # Average impact score for team 1
    team_2_avg_impact: float = 0.0  # Average impact score for team 2
    impact_balance_score: float = 1.0  # How evenly high/low impact players are distributed
    playstyle_balance_score: float = 1.0  # How evenly aggression styles are distributed


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
    def calculate_impact_balance_score(
        team_1: List[PlayerInfo],
        team_2: List[PlayerInfo]
    ) -> Tuple[float, float, float]:
        """
        Calculate how evenly high-impact and low-impact players are distributed.

        Good balance means each team has a mix of:
        - High-impact players (shot callers, strong players)
        - Low-impact players (learning, weaker players)

        Args:
            team_1: List of players on team 1
            team_2: List of players on team 2

        Returns:
            Tuple of (team_1_avg_impact, team_2_avg_impact, balance_score)
            balance_score: 0-1, where 1 = perfect impact distribution
        """
        # Calculate average impact for each team
        team_1_avg = sum(p.overall_impact for p in team_1) / len(team_1) if team_1 else 0
        team_2_avg = sum(p.overall_impact for p in team_2) / len(team_2) if team_2 else 0

        # Calculate balance score based on how close the averages are
        # Perfect balance = same average impact on both teams
        if team_1_avg == 0 and team_2_avg == 0:
            balance_score = 1.0  # No impact data, consider balanced
        else:
            max_avg = max(team_1_avg, team_2_avg)
            min_avg = min(team_1_avg, team_2_avg)
            if max_avg > 0:
                balance_score = min_avg / max_avg
            else:
                balance_score = 1.0

        return team_1_avg, team_2_avg, balance_score

    @staticmethod
    def calculate_playstyle_balance(
        team_1: List[PlayerInfo],
        team_2: List[PlayerInfo]
    ) -> float:
        """
        Calculate playstyle balance score based on aggression distribution.
        
        Best teams have a mix of aggressive (rushers) and defensive (macro) players.
        We want each team to have similar overall aggression levels.
        
        Args:
            team_1: List of players on team 1
            team_2: List of players on team 2
            
        Returns:
            Balance score (0-1), where 1 = perfect playstyle distribution
        """
        # Calculate average aggression for each team
        team_1_aggression = sum(p.aggression_score for p in team_1) / len(team_1) if team_1 else 50
        team_2_aggression = sum(p.aggression_score for p in team_2) / len(team_2) if team_2 else 50
        
        # Calculate balance score (closer = better)
        # Max difference is 100 (0 vs 100), we normalize to 0-1
        aggression_diff = abs(team_1_aggression - team_2_aggression)
        balance_score = 1.0 - (aggression_diff / 100.0)
        
        return balance_score

    @staticmethod
    def generate_team_suggestions(
        players: List[PlayerInfo],
        top_n: int = 10
    ) -> List[TeamSuggestion]:
        """
        Generate balanced team suggestions.

        Supports both even and uneven player counts:
        - Even: Splits players equally (e.g., 6 → 3v3)
        - Odd: Creates uneven teams (e.g., 5 → 3v2, 7 → 4v3)

        Args:
            players: List of available players
            top_n: Number of top suggestions to return

        Returns:
            List of TeamSuggestion objects, sorted by match quality (best first)
        """
        num_players = len(players)

        # Validate minimum players
        if num_players < 2:
            raise ValueError(f"Need at least 2 players, got {num_players}")

        # Determine team sizes
        if num_players % 2 == 0:
            # Even number: equal teams
            team_1_size = num_players // 2
        else:
            # Odd number: larger team gets the extra player
            team_1_size = (num_players // 2) + 1

        # Generate all possible team combinations
        suggestions = []

        # Get all combinations of team_1_size players for team 1
        # Team 2 is automatically the remaining players
        for team_1_indices in combinations(range(num_players), team_1_size):
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

            # Calculate impact balance
            team_1_avg_impact, team_2_avg_impact, impact_balance = TeamBalancer.calculate_impact_balance_score(
                team_1, team_2
            )
            
            # Calculate playstyle balance (rushers vs macro players)
            playstyle_balance = TeamBalancer.calculate_playstyle_balance(team_1, team_2)

            suggestions.append(TeamSuggestion(
                team_1=team_1,
                team_2=team_2,
                team_1_mmr=team_1_mmr,
                team_2_mmr=team_2_mmr,
                mmr_difference=mmr_difference,
                win_probability=win_probability,
                match_quality=match_quality,
                team_1_avg_impact=team_1_avg_impact,
                team_2_avg_impact=team_2_avg_impact,
                impact_balance_score=impact_balance,
                playstyle_balance_score=playstyle_balance
            ))

        # Sort by combined score: 80% match quality + 20% playstyle balance
        # This keeps MMR as primary factor while considering playstyle compatibility
        PLAYSTYLE_WEIGHT = 0.20  # 20% weight for playstyle balance
        suggestions.sort(key=lambda x: (
            -(x.match_quality * (1 - PLAYSTYLE_WEIGHT) + x.playstyle_balance_score * PLAYSTYLE_WEIGHT),
            x.mmr_difference
        ))

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

    @staticmethod
    def balance_with_impact_priority(
        db: Session,
        player_ids: List[int],
        top_n: int = 10,
        impact_weight: float = 0.5
    ) -> List[TeamSuggestion]:
        """
        Balance teams with priority on distributing high-impact and low-impact players evenly.

        This ensures each team gets a mix of:
        - Strong players (high MMR, high impact, shot callers)
        - Weaker players (low MMR, low impact, learning)

        Args:
            db: Database session
            player_ids: List of player IDs to balance
            top_n: Number of suggestions to return
            impact_weight: How much to weight impact balance (0-1)
                          0 = pure MMR balance
                          0.5 = equal weight to MMR and impact
                          1 = pure impact balance

        Returns:
            List of TeamSuggestion objects sorted by combined balance score
        """
        # Fetch players from database
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()

        if len(players) != len(player_ids):
            found_ids = {p.id for p in players}
            missing_ids = set(player_ids) - found_ids
            raise ValueError(f"Players not found: {missing_ids}")

        # Convert to PlayerInfo
        player_infos = [PlayerInfo.from_player(p) for p in players]

        # Generate basic suggestions
        suggestions = TeamBalancer.generate_team_suggestions(player_infos, top_n=100)

        # Re-score suggestions based on combined MMR and impact balance
        for suggestion in suggestions:
            # Combined score: weighted average of match_quality and impact_balance_score
            combined_score = (
                (1 - impact_weight) * suggestion.match_quality +
                impact_weight * suggestion.impact_balance_score
            )
            # Store in match_quality for sorting
            suggestion.match_quality = combined_score

        # Sort by combined score (descending)
        suggestions.sort(key=lambda x: -x.match_quality)

        return suggestions[:top_n]


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
                'fairness_rating': _get_fairness_rating(suggestion.match_quality),
                'team_1_avg_impact': suggestion.team_1_avg_impact,
                'team_2_avg_impact': suggestion.team_2_avg_impact,
                'impact_balance_score': suggestion.impact_balance_score,
                'impact_difference': abs(suggestion.team_1_avg_impact - suggestion.team_2_avg_impact)
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
