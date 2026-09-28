"""
Impact and Synergy Service

Manages player impact scores and synergy calculations.
Supports recency-weighted impact averages for better prediction accuracy.
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import json
import math
from datetime import datetime, timedelta

from .models import Player, MatchPlayer, PlayerMatchMetrics, Match, KillEvent
from .advanced_parser import PlayerMetrics
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
            if isinstance(metrics.damage_timeline, dict):
                damage_timeline_json = json.dumps(metrics.damage_timeline)
            elif hasattr(metrics.damage_timeline, 'to_json'):
                damage_timeline_json = metrics.damage_timeline.to_json()
            else:
                damage_timeline_json = json.dumps(metrics.damage_timeline)

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
        match_metrics.peak_active_workers = metrics.peak_active_workers
        match_metrics.units_trained = metrics.units_trained
        match_metrics.units_lost = metrics.units_lost
        match_metrics.units_killed = metrics.units_killed
        match_metrics.kill_death_ratio = metrics.kill_death_ratio
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

        # New Mechanics Fields
        match_metrics.workers_killed = metrics.workers_killed
        match_metrics.early_workers_killed = metrics.early_workers_killed
        match_metrics.mid_workers_killed = metrics.mid_workers_killed
        match_metrics.workers_lost = metrics.workers_lost
        match_metrics.early_workers_lost = metrics.early_workers_lost
        match_metrics.kill_death_ratio = metrics.kill_death_ratio
        match_metrics.supply_block_seconds = metrics.supply_block_seconds
        match_metrics.stats_cutoff_second = getattr(metrics, "stats_cutoff_second", None)
        match_metrics.stats_cutoff_reason = getattr(metrics, "stats_cutoff_reason", None)
        match_metrics.lethality_score = metrics.lethality_score

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
    def save_kill_events(db: Session, match_id: int, kill_events: List[Dict]) -> int:
        """See docs/reviews/2026-09-16-parser-field-audit.md section 3."""
        if not kill_events:
            return 0
        name_to_player_id = dict(
            db.query(Player.name, Player.id)
            .join(MatchPlayer, MatchPlayer.player_id == Player.id)
            .filter(MatchPlayer.match_id == match_id)
            .all()
        )
        for ev in kill_events:
            db.add(KillEvent(
                match_id=match_id,
                killer_player_id=name_to_player_id.get(ev["killer_name"]),
                victim_player_id=name_to_player_id.get(ev["victim_name"]),
                unit_type=ev["unit_type"],
                game_second=ev["game_second"],
                x=ev.get("x"),
                y=ev.get("y"),
            ))
        db.flush()
        return len(kill_events)

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
