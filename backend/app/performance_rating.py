"""
Performance-Based Rating Adjustments

Enhances TrueSkill ratings by incorporating individual performance metrics.
This helps identify truly strong players even in team losses and vice versa.
"""
from typing import List, Tuple
from sqlalchemy.orm import Session

from .models import Player, MatchPlayer, PlayerMatchMetrics


class PerformanceRatingAdjuster:
    """
    Adjusts TrueSkill ratings based on individual performance metrics.

    Philosophy:
    - Team outcome (win/loss) determines base rating change via TrueSkill
    - Individual performance can amplify or dampen that change
    - This rewards carrying teams and penalizes getting carried
    """

    # Configuration
    MAX_PERFORMANCE_MULTIPLIER = 1.5  # Max 50% boost to rating change
    MIN_PERFORMANCE_MULTIPLIER = 0.5  # Max 50% reduction to rating change
    PERFORMANCE_WEIGHT = 0.35  # How much performance affects rating vs team result

    @staticmethod
    def calculate_performance_multiplier(
        player_metrics: PlayerMatchMetrics,
        team_metrics: List[PlayerMatchMetrics],
        opponent_metrics: List[PlayerMatchMetrics],
        won: bool
    ) -> float:
        """
        Calculate performance multiplier for rating adjustment.

        Args:
            player_metrics: This player's performance metrics
            team_metrics: All teammates' metrics (including this player)
            opponent_metrics: All opponents' metrics
            won: Whether the player's team won

        Returns:
            Multiplier between MIN and MAX (1.0 = no adjustment)
        """
        if not player_metrics:
            return 1.0

        # Guard against empty metrics lists
        if not team_metrics or not opponent_metrics:
            return 1.0

        # Calculate relative performance vs team
        team_avg_impact = sum(m.overall_impact for m in team_metrics) / len(team_metrics)
        relative_to_team = player_metrics.overall_impact / team_avg_impact if team_avg_impact > 0 else 1.0

        # Calculate relative performance vs opponents
        opponent_avg_impact = sum(m.overall_impact for m in opponent_metrics) / len(opponent_metrics)
        relative_to_opponents = player_metrics.overall_impact / opponent_avg_impact if opponent_avg_impact > 0 else 1.0

        # Combined performance score (higher = better individual performance)
        # Weight team performance more heavily (did you contribute to your team?)
        performance_score = (
            relative_to_team * 0.6 +
            relative_to_opponents * 0.4
        )

        # Convert performance score to multiplier
        # If you won:
        #   - High performance (carried team) = higher multiplier (more MMR gain)
        #   - Low performance (got carried) = lower multiplier (less MMR gain)
        # If you lost:
        #   - High performance (tried hard, team let you down) = higher multiplier (less MMR loss)
        #   - Low performance (you were the problem) = lower multiplier (more MMR loss)

        if won:
            # Winning: reward strong performance, diminish weak performance
            if performance_score > 1.0:
                # Performed above team average
                excess = (performance_score - 1.0) * PerformanceRatingAdjuster.PERFORMANCE_WEIGHT
                multiplier = 1.0 + excess
            else:
                # Performed below team average (got carried)
                deficit = (1.0 - performance_score) * PerformanceRatingAdjuster.PERFORMANCE_WEIGHT
                multiplier = 1.0 - deficit
        else:
            # Losing: cushion strong performance, amplify weak performance
            if performance_score > 1.0:
                # Performed above team average despite loss
                excess = (performance_score - 1.0) * PerformanceRatingAdjuster.PERFORMANCE_WEIGHT
                multiplier = 1.0 + (excess * 0.5)  # Reduce loss less
            else:
                # Performed below team average and lost
                deficit = (1.0 - performance_score) * PerformanceRatingAdjuster.PERFORMANCE_WEIGHT
                multiplier = 1.0 - (deficit * 0.5)  # Increase loss more

        # Clamp to configured bounds
        multiplier = max(
            PerformanceRatingAdjuster.MIN_PERFORMANCE_MULTIPLIER,
            min(PerformanceRatingAdjuster.MAX_PERFORMANCE_MULTIPLIER, multiplier)
        )

        return multiplier

    @staticmethod
    def apply_performance_adjustment(
        db: Session,
        match_player: MatchPlayer,
        performance_multiplier: float
    ) -> Tuple[float, float]:
        """
        Apply performance-based adjustment to a player's rating change.

        This modifies the mu (skill) change while keeping sigma (uncertainty) unchanged,
        since uncertainty is about consistency, not individual performance.

        Args:
            db: Database session
            match_player: MatchPlayer to adjust
            performance_multiplier: Multiplier to apply

        Returns:
            Tuple of (adjusted_mu_after, original_mu_after)
        """
        # Calculate base mu change from TrueSkill
        base_mu_change = match_player.mu_after - match_player.mu_before

        # Apply performance multiplier to the change (not the final value)
        adjusted_mu_change = base_mu_change * performance_multiplier
        adjusted_mu_after = match_player.mu_before + adjusted_mu_change

        # Store original for comparison
        original_mu_after = match_player.mu_after

        # Update the match_player record
        match_player.mu_after = adjusted_mu_after

        # Update the player's current rating
        player = db.query(Player).filter(Player.id == match_player.player_id).first()
        if player:
            player.mu = adjusted_mu_after

        db.commit()

        return adjusted_mu_after, original_mu_after

    @staticmethod
    def adjust_ratings_for_match(db: Session, match_id: int):
        """
        Apply performance adjustments to all players in a match.

        Should be called AFTER TrueSkill ratings have been calculated.

        Args:
            db: Database session
            match_id: Match ID to process
        """
        # Get all players in match with their metrics in a single query (avoid N+1)
        from sqlalchemy.orm import joinedload
        match_players = db.query(MatchPlayer).filter(
            MatchPlayer.match_id == match_id
        ).all()

        # Get all metrics for this match in a single query
        match_player_ids = [mp.id for mp in match_players]
        metrics_list = db.query(PlayerMatchMetrics).filter(
            PlayerMatchMetrics.match_player_id.in_(match_player_ids)
        ).all()

        # Create mapping
        player_metrics_map = {m.match_player_id: m for m in metrics_list}

        # Group by team
        team_1 = [mp for mp in match_players if mp.team_number == 1]
        team_2 = [mp for mp in match_players if mp.team_number == 2]

        team_1_metrics = [player_metrics_map[mp.id] for mp in team_1 if mp.id in player_metrics_map]
        team_2_metrics = [player_metrics_map[mp.id] for mp in team_2 if mp.id in player_metrics_map]

        # Adjust each player
        adjustments = []

        for mp in match_players:
            if mp.id not in player_metrics_map:
                continue  # Skip if no metrics

            metrics = player_metrics_map[mp.id]

            # Determine team and opponent metrics
            if mp.team_number == 1:
                team_metrics = team_1_metrics
                opponent_metrics = team_2_metrics
            else:
                team_metrics = team_2_metrics
                opponent_metrics = team_1_metrics

            # Calculate multiplier
            multiplier = PerformanceRatingAdjuster.calculate_performance_multiplier(
                metrics,
                team_metrics,
                opponent_metrics,
                bool(mp.won)
            )

            # Apply adjustment
            adjusted_mu, original_mu = PerformanceRatingAdjuster.apply_performance_adjustment(
                db,
                mp,
                multiplier
            )

            adjustments.append({
                'player_id': mp.player_id,
                'multiplier': multiplier,
                'original_mu': original_mu,
                'adjusted_mu': adjusted_mu,
                'performance_score': metrics.overall_impact
            })

        return adjustments
