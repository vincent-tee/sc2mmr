"""
Impact and Synergy Service

Manages player impact scores and synergy calculations.
Supports recency-weighted impact averages for better prediction accuracy.
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import json
import math
from datetime import datetime, timedelta

from .models import Player, MatchPlayer, PlayerMatchMetrics, PlayerSynergy, Match
from .advanced_parser import PlayerMetrics, calculate_player_synergy
from .config import settings


class ImpactService:
    """Service for managing player impact scores and synergies."""

    @staticmethod
    def save_match_metrics(
        db: Session, match_player_id: int, metrics: PlayerMetrics
    ) -> PlayerMatchMetrics:
        """
        Save detailed metrics for a match player.

        Args:
            db: Database session
            match_player_id: MatchPlayer ID
            metrics: PlayerMetrics to save

        Returns:
            Created PlayerMatchMetrics object
        """
        # Convert unit composition dict to JSON string
        unit_comp_json = (
            json.dumps(metrics.unit_composition) if metrics.unit_composition else None
        )

        # Convert damage timeline to JSON string
        damage_timeline_json = None
        if metrics.damage_timeline:
            damage_timeline_json = metrics.damage_timeline.to_json()

        # Determine archetype from metrics (handle both legacy PlayerMetrics and new PlayerMatchResult)
        archetype = None
        if hasattr(metrics, "detected_build_type"):
            archetype = str(getattr(metrics, "detected_build_type", ""))
        elif hasattr(metrics, "player_archetype") and metrics.player_archetype:
            # Handle enum if it's an enum, otherwise string
            archetype = str(
                getattr(metrics.player_archetype, "value", metrics.player_archetype)
            )

        # Upsert: check if metrics already exist for this match_player
        match_metrics = (
            db.query(PlayerMatchMetrics)
            .filter(PlayerMatchMetrics.match_player_id == match_player_id)
            .first()
        )

        if not match_metrics:
            match_metrics = PlayerMatchMetrics(match_player_id=match_player_id)
            db.add(match_metrics)

        # Update fields
        match_metrics.minerals_collected = metrics.minerals_collected
        match_metrics.vespene_collected = metrics.vespene_collected
        match_metrics.total_resources_collected = metrics.total_resources_collected
        match_metrics.resources_spent = metrics.resources_spent
        match_metrics.spending_efficiency = metrics.spending_efficiency
        match_metrics.workers_created = metrics.workers_created
        match_metrics.units_trained = metrics.units_trained
        match_metrics.units_lost = metrics.units_lost
        match_metrics.units_killed = metrics.units_killed
        match_metrics.army_value_built = metrics.army_value_built
        match_metrics.army_value_killed = metrics.army_value_killed
        match_metrics.army_value_lost = metrics.army_value_lost

        # Ensure damage_dealt is never 0 if army_value_killed is known
        match_metrics.damage_dealt = (
            metrics.damage_dealt or metrics.army_value_killed or 0
        )
        match_metrics.damage_taken = (
            metrics.damage_taken or metrics.army_value_lost or 0
        )

        match_metrics.damage_ratio = metrics.damage_ratio
        match_metrics.first_expansion_timing = metrics.first_expansion_timing
        match_metrics.bases_created = metrics.bases_created
        match_metrics.apm = metrics.apm
        match_metrics.unit_composition = unit_comp_json
        match_metrics.economic_score = metrics.economic_score
        match_metrics.combat_score = metrics.combat_score
        match_metrics.efficiency_score = metrics.efficiency_score
        match_metrics.overall_impact = metrics.overall_impact
        match_metrics.team_fight_participation = metrics.team_fight_participation
        match_metrics.team_fight_damage = metrics.team_fight_damage
        match_metrics.team_fight_damage_ratio = metrics.team_fight_damage_ratio
        match_metrics.first_damage_timing = metrics.first_damage_timing
        match_metrics.early_game_damage = metrics.early_game_damage
        match_metrics.mid_game_damage = metrics.mid_game_damage
        match_metrics.late_game_damage = metrics.late_game_damage
        match_metrics.player_archetype = archetype
        match_metrics.aggression_score = metrics.aggression_score
        match_metrics.damage_timeline = damage_timeline_json

        db.flush()  # Flush to get ID, but don't commit yet (let caller commit)

        return match_metrics

    @staticmethod
    def update_player_averages(db: Session, player_id: int):
        """
        Update a player's average impact scores based on all their matches.

        Uses recency weighting (same as MMR) so recent performance matters more.
        This aligns impact metrics with recency-weighted MMR for better predictions.

        Args:
            db: Database session
            player_id: Player ID to update
        """
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return

        # Get all match metrics for this player with match date for recency weighting
        metrics_with_dates = (
            db.query(PlayerMatchMetrics, Match.played_at)
            .join(MatchPlayer, PlayerMatchMetrics.match_player_id == MatchPlayer.id)
            .join(Match, MatchPlayer.match_id == Match.id)
            .filter(MatchPlayer.player_id == player_id)
            .all()
        )

        if not metrics_with_dates:
            return

        # Calculate recency-weighted averages
        now = datetime.utcnow()
        half_life_days = settings.recency_half_life_days
        use_recency = settings.recency_enabled

        weighted_econ = 0.0
        weighted_combat = 0.0
        weighted_efficiency = 0.0
        weighted_impact = 0.0
        total_weight = 0.0

        for metrics, played_at in metrics_with_dates:
            if use_recency and played_at:
                # Calculate recency weight using exponential decay
                days_ago = (now - played_at).total_seconds() / 86400.0
                weight = math.pow(0.5, days_ago / half_life_days)
            else:
                weight = 1.0

            weighted_econ += metrics.economic_score * weight
            weighted_combat += metrics.combat_score * weight
            weighted_efficiency += metrics.efficiency_score * weight
            weighted_impact += metrics.overall_impact * weight
            total_weight += weight

        if total_weight > 0:
            player.avg_economic_score = weighted_econ / total_weight
            player.avg_combat_score = weighted_combat / total_weight
            player.avg_efficiency_score = weighted_efficiency / total_weight
            player.avg_overall_impact = weighted_impact / total_weight

        db.commit()

    @staticmethod
    def update_synergies(db: Session, match_id: int):
        """
        Update synergy scores for all player pairs in a match.

        Args:
            db: Database session
            match_id: Match ID to process
        """
        # Get all players in this match
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
        )

        # Group by team
        team_1_players = [mp for mp in match_players if mp.team_number == 1]
        team_2_players = [mp for mp in match_players if mp.team_number == 2]

        # Update synergies within each team
        ImpactService._update_team_synergies(db, team_1_players)
        ImpactService._update_team_synergies(db, team_2_players)

    @staticmethod
    def _update_team_synergies(db: Session, team_players: List[MatchPlayer]):
        """
        Update synergies for all pairs within a team.

        Args:
            db: Database session
            team_players: List of MatchPlayer objects on the same team
        """
        # Get all pairs of players
        for i in range(len(team_players)):
            for j in range(i + 1, len(team_players)):
                player1_id = team_players[i].player_id
                player2_id = team_players[j].player_id
                won = team_players[i].won  # Both have same result

                # Ensure consistent ordering (smaller ID first)
                if player1_id > player2_id:
                    player1_id, player2_id = player2_id, player1_id

                # Get or create synergy record
                synergy = (
                    db.query(PlayerSynergy)
                    .filter(
                        and_(
                            PlayerSynergy.player1_id == player1_id,
                            PlayerSynergy.player2_id == player2_id,
                        )
                    )
                    .first()
                )

                if not synergy:
                    synergy = PlayerSynergy(
                        player1_id=player1_id,
                        player2_id=player2_id,
                        games_together=0,
                        wins_together=0,
                        losses_together=0,
                    )
                    db.add(synergy)

                # Update counts
                synergy.games_together += 1
                if won:
                    synergy.wins_together += 1
                else:
                    synergy.losses_together += 1

                synergy.avg_win_rate = (
                    synergy.wins_together / synergy.games_together
                ) * 100
                synergy.updated_at = datetime.utcnow()

        # Commit all synergy updates at once (more efficient than per-pair commits)
        db.commit()

        # Recalculate synergy scores for all pairs in this team
        for i in range(len(team_players)):
            for j in range(i + 1, len(team_players)):
                player1_id = team_players[i].player_id
                player2_id = team_players[j].player_id

                if player1_id > player2_id:
                    player1_id, player2_id = player2_id, player1_id

                ImpactService._calculate_synergy_score(db, player1_id, player2_id)

    @staticmethod
    def _calculate_synergy_score(db: Session, player1_id: int, player2_id: int):
        """
        Calculate and update synergy score for a player pair.

        Args:
            db: Database session
            player1_id: First player ID (should be < player2_id)
            player2_id: Second player ID
        """
        # Get synergy record
        synergy = (
            db.query(PlayerSynergy)
            .filter(
                and_(
                    PlayerSynergy.player1_id == player1_id,
                    PlayerSynergy.player2_id == player2_id,
                )
            )
            .first()
        )

        if not synergy or synergy.games_together < 3:
            # Need at least 3 games to calculate meaningful synergy
            return

        # Get all matches where both players were on the same team
        matches_together = (
            db.query(MatchPlayer).filter(MatchPlayer.player_id == player1_id).all()
        )

        player1_metrics_list = []
        player2_metrics_list = []

        for mp1 in matches_together:
            # Check if player2 was in same match and same team
            mp2 = (
                db.query(MatchPlayer)
                .filter(
                    and_(
                        MatchPlayer.match_id == mp1.match_id,
                        MatchPlayer.player_id == player2_id,
                        MatchPlayer.team_number == mp1.team_number,
                    )
                )
                .first()
            )

            if mp2:
                # Get metrics for both players
                metrics1 = (
                    db.query(PlayerMatchMetrics)
                    .filter(PlayerMatchMetrics.match_player_id == mp1.id)
                    .first()
                )
                metrics2 = (
                    db.query(PlayerMatchMetrics)
                    .filter(PlayerMatchMetrics.match_player_id == mp2.id)
                    .first()
                )

                if metrics1 and metrics2:
                    # Convert to PlayerMetrics objects
                    pm1 = ImpactService._db_metrics_to_player_metrics(metrics1, mp1)
                    pm2 = ImpactService._db_metrics_to_player_metrics(metrics2, mp2)

                    player1_metrics_list.append(pm1)
                    player2_metrics_list.append(pm2)

        if len(player1_metrics_list) >= 3:
            # Calculate synergy using the algorithm
            synergy_score = calculate_player_synergy(
                player1_metrics_list, player2_metrics_list
            )

            # Calculate average combined impact
            avg_combined = sum(
                m1.overall_impact + m2.overall_impact
                for m1, m2 in zip(player1_metrics_list, player2_metrics_list)
            ) / len(player1_metrics_list)

            synergy.synergy_score = synergy_score
            synergy.avg_combined_impact = avg_combined

            db.commit()

    @staticmethod
    def _db_metrics_to_player_metrics(
        db_metrics: PlayerMatchMetrics, match_player: MatchPlayer
    ) -> PlayerMetrics:
        """
        Convert database metrics to PlayerMetrics object.

        Args:
            db_metrics: PlayerMatchMetrics from database
            match_player: MatchPlayer object

        Returns:
            PlayerMetrics object
        """
        unit_comp = (
            json.loads(db_metrics.unit_composition)
            if db_metrics.unit_composition
            else {}
        )

        return PlayerMetrics(
            player_name="",  # Not needed for synergy calc
            race="",  # Not needed
            team=match_player.team_number,
            won=bool(match_player.won),
            minerals_collected=db_metrics.minerals_collected,
            vespene_collected=db_metrics.vespene_collected,
            total_resources_collected=db_metrics.total_resources_collected,
            resources_spent=db_metrics.resources_spent,
            spending_efficiency=db_metrics.spending_efficiency,
            workers_created=db_metrics.workers_created,
            units_trained=db_metrics.units_trained,
            units_lost=db_metrics.units_lost,
            units_killed=db_metrics.units_killed,
            army_value_built=db_metrics.army_value_built,
            army_value_killed=db_metrics.army_value_killed,
            army_value_lost=db_metrics.army_value_lost,
            damage_dealt=db_metrics.damage_dealt,
            damage_taken=db_metrics.damage_taken,
            damage_ratio=db_metrics.damage_ratio,
            first_expansion_timing=db_metrics.first_expansion_timing,
            bases_created=db_metrics.bases_created,
            apm=db_metrics.apm,
            unit_composition=unit_comp,
            economic_score=db_metrics.economic_score,
            combat_score=db_metrics.combat_score,
            efficiency_score=db_metrics.efficiency_score,
            overall_impact=db_metrics.overall_impact,
        )

    @staticmethod
    def get_player_synergies(
        db: Session, player_id: int, min_games: int = 3
    ) -> List[Tuple[Player, PlayerSynergy]]:
        """
        Get all synergies for a player.

        Args:
            db: Database session
            player_id: Player ID
            min_games: Minimum games together to include

        Returns:
            List of (other_player, synergy) tuples, sorted by synergy score
        """
        # Get synergies where player is player1
        synergies1 = (
            db.query(PlayerSynergy)
            .filter(
                and_(
                    PlayerSynergy.player1_id == player_id,
                    PlayerSynergy.games_together >= min_games,
                )
            )
            .all()
        )

        # Get synergies where player is player2
        synergies2 = (
            db.query(PlayerSynergy)
            .filter(
                and_(
                    PlayerSynergy.player2_id == player_id,
                    PlayerSynergy.games_together >= min_games,
                )
            )
            .all()
        )

        results = []

        for synergy in synergies1:
            other_player = (
                db.query(Player).filter(Player.id == synergy.player2_id).first()
            )
            if other_player:
                results.append((other_player, synergy))

        for synergy in synergies2:
            other_player = (
                db.query(Player).filter(Player.id == synergy.player1_id).first()
            )
            if other_player:
                results.append((other_player, synergy))

        # Sort by synergy score (descending)
        results.sort(key=lambda x: x[1].synergy_score, reverse=True)

        return results

    @staticmethod
    def get_top_synergies(
        db: Session, min_games: int = 5, limit: int = 10
    ) -> List[Tuple[Player, Player, PlayerSynergy]]:
        """
        Get top synergies across all players.

        Args:
            db: Database session
            min_games: Minimum games together
            limit: Maximum results to return

        Returns:
            List of (player1, player2, synergy) tuples
        """
        synergies = (
            db.query(PlayerSynergy)
            .filter(PlayerSynergy.games_together >= min_games)
            .order_by(PlayerSynergy.synergy_score.desc())
            .limit(limit)
            .all()
        )

        results = []
        for synergy in synergies:
            player1 = db.query(Player).filter(Player.id == synergy.player1_id).first()
            player2 = db.query(Player).filter(Player.id == synergy.player2_id).first()
            if player1 and player2:
                results.append((player1, player2, synergy))

        return results
