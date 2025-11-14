"""
Script to merge two player records into one.

Usage:
    python3 merge_players.py <duplicate_name> <primary_name>

Example:
    python3 merge_players.py "demonslayer" "dragonking"

This will merge all data from demonslayer into dragonking, then delete demonslayer.
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Player, MatchPlayer, PlayerSynergy, PlayerMatchMetrics
from app.database import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def merge_players(session, duplicate_name: str, primary_name: str):
    """
    Merge duplicate player into primary player.

    Args:
        session: Database session
        duplicate_name: Name of player to merge FROM (will be deleted)
        primary_name: Name of player to merge INTO (will be kept)
    """
    # Fetch both players
    duplicate = session.query(Player).filter(Player.name == duplicate_name).first()
    primary = session.query(Player).filter(Player.name == primary_name).first()

    if not duplicate:
        logger.error(f"Duplicate player '{duplicate_name}' not found in database")
        return False

    if not primary:
        logger.error(f"Primary player '{primary_name}' not found in database")
        return False

    logger.info(f"\n{'='*60}")
    logger.info(f"MERGING PLAYERS")
    logger.info(f"{'='*60}")
    logger.info(f"FROM (will be deleted): {duplicate_name} (ID: {duplicate.id})")
    logger.info(f"  - Total games: {duplicate.total_games}")
    logger.info(f"  - W/L: {duplicate.wins}/{duplicate.losses}")
    logger.info(f"  - MMR: {duplicate.mmr:.0f} (mu={duplicate.mu:.2f}, sigma={duplicate.sigma:.2f})")
    logger.info(f"\nINTO (will be kept): {primary_name} (ID: {primary.id})")
    logger.info(f"  - Total games: {primary.total_games}")
    logger.info(f"  - W/L: {primary.wins}/{primary.losses}")
    logger.info(f"  - MMR: {primary.mmr:.0f} (mu={primary.mu:.2f}, sigma={primary.sigma:.2f})")
    logger.info(f"{'='*60}\n")

    # Confirm merge
    response = input(f"Proceed with merge? This will DELETE '{duplicate_name}' and move all their data to '{primary_name}'. Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        logger.info("Merge cancelled.")
        return False

    try:
        # Step 1: Update all MatchPlayer records
        match_players = session.query(MatchPlayer).filter(
            MatchPlayer.player_id == duplicate.id
        ).all()

        logger.info(f"\n1. Updating {len(match_players)} MatchPlayer records...")
        for mp in match_players:
            mp.player_id = primary.id

        # Step 2: Handle PlayerSynergy records
        logger.info(f"\n2. Merging PlayerSynergy records...")

        # Get all synergies involving the duplicate player
        synergies_as_p1 = session.query(PlayerSynergy).filter(
            PlayerSynergy.player1_id == duplicate.id
        ).all()
        synergies_as_p2 = session.query(PlayerSynergy).filter(
            PlayerSynergy.player2_id == duplicate.id
        ).all()

        logger.info(f"   - Found {len(synergies_as_p1)} synergies where duplicate is player1")
        logger.info(f"   - Found {len(synergies_as_p2)} synergies where duplicate is player2")

        # Update or merge synergies
        for syn in synergies_as_p1:
            other_player_id = syn.player2_id

            # Check if primary already has synergy with this player
            existing = session.query(PlayerSynergy).filter(
                ((PlayerSynergy.player1_id == primary.id) & (PlayerSynergy.player2_id == other_player_id)) |
                ((PlayerSynergy.player1_id == other_player_id) & (PlayerSynergy.player2_id == primary.id))
            ).first()

            if existing:
                # Merge the stats
                logger.info(f"   - Merging synergy with player {other_player_id}")
                existing.games_together += syn.games_together
                existing.wins_together += syn.wins_together
                existing.losses_together += syn.losses_together
                # Recalculate averages
                if existing.games_together > 0:
                    existing.avg_win_rate = (existing.wins_together / existing.games_together) * 100
                session.delete(syn)
            else:
                # Just update the player ID
                logger.info(f"   - Moving synergy with player {other_player_id}")
                syn.player1_id = primary.id

        for syn in synergies_as_p2:
            other_player_id = syn.player1_id

            # Check if primary already has synergy with this player
            existing = session.query(PlayerSynergy).filter(
                ((PlayerSynergy.player1_id == primary.id) & (PlayerSynergy.player2_id == other_player_id)) |
                ((PlayerSynergy.player1_id == other_player_id) & (PlayerSynergy.player2_id == primary.id))
            ).first()

            if existing:
                # Merge the stats
                logger.info(f"   - Merging synergy with player {other_player_id}")
                existing.games_together += syn.games_together
                existing.wins_together += syn.wins_together
                existing.losses_together += syn.losses_together
                # Recalculate averages
                if existing.games_together > 0:
                    existing.avg_win_rate = (existing.wins_together / existing.games_together) * 100
                session.delete(syn)
            else:
                # Just update the player ID
                logger.info(f"   - Moving synergy with player {other_player_id}")
                syn.player2_id = primary.id

        # Step 3: Merge player statistics
        logger.info(f"\n3. Merging player statistics...")

        # Combine game counts
        primary.total_games += duplicate.total_games
        primary.wins += duplicate.wins
        primary.losses += duplicate.losses

        # Combine race stats
        primary.terran_games += duplicate.terran_games
        primary.protoss_games += duplicate.protoss_games
        primary.zerg_games += duplicate.zerg_games
        primary.random_games += duplicate.random_games

        # Update last_played to the most recent
        if duplicate.last_played:
            if not primary.last_played or duplicate.last_played > primary.last_played:
                primary.last_played = duplicate.last_played

        # Use created_at from the earlier record
        if duplicate.created_at < primary.created_at:
            primary.created_at = duplicate.created_at

        # Keep the higher is_core_player value (1 = core, 0 = outsider)
        if duplicate.is_core_player > primary.is_core_player:
            primary.is_core_player = duplicate.is_core_player

        logger.info(f"   - New total games: {primary.total_games}")
        logger.info(f"   - New W/L: {primary.wins}/{primary.losses}")
        logger.info(f"   - Win rate: {primary.win_rate*100:.1f}%")

        # Step 4: Recalculate TrueSkill rating based on ALL matches
        logger.info(f"\n4. TrueSkill rating will need to be recalculated...")
        logger.info(f"   NOTE: You should run recalculate_ratings.py after this merge")
        logger.info(f"   to properly recalculate TrueSkill ratings from match history")

        # Step 5: Recalculate impact scores (average across all matches)
        logger.info(f"\n5. Recalculating impact score averages...")

        # Get all match_player records for primary player
        all_match_players = session.query(MatchPlayer).filter(
            MatchPlayer.player_id == primary.id
        ).all()

        # Get metrics for all matches
        total_economic = 0
        total_combat = 0
        total_efficiency = 0
        total_impact = 0
        metrics_count = 0

        for mp in all_match_players:
            metrics = session.query(PlayerMatchMetrics).filter(
                PlayerMatchMetrics.match_player_id == mp.id
            ).first()

            if metrics:
                total_economic += metrics.economic_score
                total_combat += metrics.combat_score
                total_efficiency += metrics.efficiency_score
                total_impact += metrics.overall_impact
                metrics_count += 1

        if metrics_count > 0:
            primary.avg_economic_score = total_economic / metrics_count
            primary.avg_combat_score = total_combat / metrics_count
            primary.avg_efficiency_score = total_efficiency / metrics_count
            primary.avg_overall_impact = total_impact / metrics_count
            logger.info(f"   - Recalculated averages from {metrics_count} matches")

        # Step 6: Delete the duplicate player
        logger.info(f"\n6. Deleting duplicate player '{duplicate_name}'...")
        session.delete(duplicate)

        # Commit all changes
        session.commit()

        logger.info(f"\n{'='*60}")
        logger.info(f"✓ MERGE COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Player '{duplicate_name}' has been merged into '{primary_name}'")
        logger.info(f"\nFinal stats for '{primary_name}':")
        logger.info(f"  - Total games: {primary.total_games}")
        logger.info(f"  - W/L: {primary.wins}/{primary.losses} ({primary.win_rate*100:.1f}% win rate)")
        logger.info(f"  - Favorite race: {primary.favorite_race}")
        logger.info(f"\nIMPORTANT: Run 'python3 recalculate_ratings.py' to recalculate TrueSkill ratings!")
        logger.info(f"{'='*60}\n")

        return True

    except Exception as e:
        logger.error(f"\nERROR during merge: {e}", exc_info=True)
        session.rollback()
        logger.info("\nMerge failed and was rolled back. No changes were made.")
        return False


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 merge_players.py <duplicate_name> <primary_name>")
        print("\nExample:")
        print("  python3 merge_players.py 'demonslayer' 'dragonking'")
        print("\nThis will merge all data from demonslayer INTO dragonking,")
        print("then delete demonslayer. Choose carefully which name to keep!")
        sys.exit(1)

    duplicate_name = sys.argv[1]
    primary_name = sys.argv[2]

    # Create database session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        success = merge_players(session, duplicate_name, primary_name)
        sys.exit(0 if success else 1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
