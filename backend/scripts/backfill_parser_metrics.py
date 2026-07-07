#!/usr/bin/env python3
"""
Backfill Script: Reprocess all replays with the fixed UnifiedParser

This script:
1. Finds all matches in the database with replay files
2. Re-parses each replay with the fixed UnifiedParser
3. Updates PlayerMatchMetrics and PerformanceFeatures with correct values

Run with: python scripts/backfill_parser_metrics.py [--dry-run] [--limit N]
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Match, MatchPlayer, PlayerMatchMetrics, PerformanceFeatures
from app.services.unified_parser import UnifiedParser

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def find_replay_file(match: Match, replay_dirs: list) -> str | None:
    """Find replay file for a match."""
    # Try replay_file_path first
    if match.replay_file_path and os.path.exists(match.replay_file_path):
        return match.replay_file_path

    # Try to find by hash
    if match.replay_hash:
        for replay_dir in replay_dirs:
            if not os.path.exists(replay_dir):
                continue
            for f in os.listdir(replay_dir):
                if f.endswith(".SC2Replay"):
                    if match.replay_hash in f:
                        return os.path.join(replay_dir, f)

    return None


def update_metrics(db, match_player: MatchPlayer, player_result, duration_seconds: int):
    """Update PlayerMatchMetrics with parsed data."""
    # Get or create metrics
    metrics = (
        db.query(PlayerMatchMetrics)
        .filter(PlayerMatchMetrics.match_player_id == match_player.id)
        .first()
    )

    if not metrics:
        metrics = PlayerMatchMetrics(match_player_id=match_player.id)
        db.add(metrics)

    # Update all fields from parser
    metrics.minerals_collected = player_result.minerals_collected
    metrics.vespene_collected = player_result.vespene_collected
    metrics.total_resources_collected = player_result.total_resources_collected
    metrics.resources_spent = player_result.resources_spent
    metrics.spending_efficiency = player_result.spending_efficiency
    metrics.workers_created = player_result.workers_created
    metrics.units_trained = player_result.units_trained
    metrics.units_lost = player_result.units_lost
    metrics.units_killed = player_result.units_killed
    metrics.army_value_built = player_result.army_value_built
    metrics.army_value_killed = player_result.army_value_killed
    metrics.army_value_lost = player_result.army_value_lost
    metrics.damage_dealt = player_result.damage_dealt or player_result.army_value_killed
    metrics.damage_taken = player_result.damage_taken or player_result.army_value_lost
    metrics.damage_ratio = player_result.damage_ratio
    metrics.first_expansion_timing = player_result.first_expansion_timing
    metrics.bases_created = player_result.bases_created
    metrics.apm = player_result.apm
    metrics.unit_composition = (
        json.dumps(player_result.unit_composition)
        if player_result.unit_composition
        else None
    )
    metrics.economic_score = player_result.economic_score
    metrics.combat_score = player_result.combat_score
    metrics.efficiency_score = player_result.efficiency_score
    metrics.overall_impact = player_result.overall_impact
    metrics.team_fight_participation = player_result.team_fight_participation
    metrics.team_fight_damage = player_result.team_fight_damage
    metrics.team_fight_damage_ratio = player_result.team_fight_damage_ratio
    metrics.first_damage_timing = player_result.first_damage_timing
    metrics.early_game_damage = player_result.early_game_damage
    metrics.mid_game_damage = player_result.mid_game_damage
    metrics.late_game_damage = player_result.late_game_damage
    metrics.player_archetype = player_result.player_archetype
    metrics.aggression_score = player_result.aggression_score

    # Damage timeline
    if player_result.damage_timeline:
        metrics.damage_timeline = json.dumps(player_result.damage_timeline)

    return metrics


def update_performance_features(
    db, match_player: MatchPlayer, player_result, duration_seconds: int
):
    """Update PerformanceFeatures with parsed data."""
    # Get or create features
    pf = (
        db.query(PerformanceFeatures)
        .filter(PerformanceFeatures.match_player_id == match_player.id)
        .first()
    )

    if not pf:
        pf = PerformanceFeatures(match_player_id=match_player.id)
        db.add(pf)

    # Update ML features
    pf.build_order_json = player_result.build_order
    pf.build_order_hash = player_result.build_order_hash
    pf.upgrades_json = player_result.upgrades
    pf.abilities_json = player_result.ability_usage
    pf.total_abilities = (
        sum(player_result.ability_usage.values()) if player_result.ability_usage else 0
    )
    pf.abilities_per_minute = (
        (pf.total_abilities / (duration_seconds / 60)) if duration_seconds > 0 else 0
    )
    pf.supply_block_seconds = player_result.supply_block_seconds
    pf.early_worker_losses = player_result.early_worker_losses
    pf.harassment_response_score = player_result.harassment_response_score
    pf.detected_build_type = player_result.detected_build_type

    # Extract upgrade timings
    if player_result.upgrades:
        attack_upgrades = [
            u for u in player_result.upgrades if u.get("category") == "attack"
        ]
        armor_upgrades = [
            u for u in player_result.upgrades if u.get("category") == "armor"
        ]
        if attack_upgrades:
            pf.first_attack_upgrade_second = min(u["second"] for u in attack_upgrades)
        if armor_upgrades:
            pf.first_armor_upgrade_second = min(u["second"] for u in armor_upgrades)

    return pf


def backfill_match(
    db, parser: UnifiedParser, match: Match, replay_path: str, dry_run: bool
) -> bool:
    """Backfill a single match with parsed data."""
    try:
        result = parser.parse(replay_path)
    except Exception as e:
        logger.warning(f"Failed to parse {replay_path}: {e}")
        return False

    # Get match players
    match_players = db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()

    # Match parsed players to database players by name
    updated = 0
    for mp in match_players:
        player = mp.player

        # Find matching parsed player
        parsed_player = None
        for p in result.players:
            if p.name == player.name:
                parsed_player = p
                break

        if not parsed_player:
            # Try fuzzy match (name without clan tag)
            for p in result.players:
                if player.name in p.name or p.name in player.name:
                    parsed_player = p
                    break

        if parsed_player:
            if not dry_run:
                update_metrics(db, mp, parsed_player, result.duration_seconds)
                update_performance_features(
                    db, mp, parsed_player, result.duration_seconds
                )
            updated += 1

    if not dry_run and updated > 0:
        db.commit()

    return updated > 0


def main():
    parser = argparse.ArgumentParser(
        description="Backfill match metrics with fixed parser"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually update database"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of matches to process"
    )
    parser.add_argument(
        "--replay-dir", type=str, default="replays", help="Directory containing replays"
    )
    args = parser.parse_args()

    # Connect to database
    engine = create_engine("sqlite:///data/sc2mmr.db")
    Session = sessionmaker(bind=engine)
    db = Session()

    # Initialize parser
    unified_parser = UnifiedParser()

    # Get all matches
    query = db.query(Match).order_by(Match.played_at.desc())
    if args.limit:
        query = query.limit(args.limit)
    matches = query.all()

    logger.info(f"Found {len(matches)} matches to process")
    if args.dry_run:
        logger.info("DRY RUN - no changes will be made")

    replay_dirs = [args.replay_dir, "replays", "../replays", "data/replays"]

    success = 0
    failed = 0
    skipped = 0

    for i, match in enumerate(matches):
        replay_path = find_replay_file(match, replay_dirs)

        if not replay_path:
            skipped += 1
            continue

        if backfill_match(db, unified_parser, match, replay_path, args.dry_run):
            success += 1
        else:
            failed += 1

        if (i + 1) % 10 == 0:
            logger.info(
                f"Progress: {i + 1}/{len(matches)} (success={success}, failed={failed}, skipped={skipped})"
            )

    db.close()

    logger.info(f"""
Backfill Complete:
  Total matches: {len(matches)}
  Successfully updated: {success}
  Failed to parse: {failed}
  Skipped (no replay): {skipped}
  Dry run: {args.dry_run}
""")


if __name__ == "__main__":
    main()
