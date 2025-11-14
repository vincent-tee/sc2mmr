"""
Script to recalculate all TrueSkill ratings from scratch.

This should be run after merging players to ensure ratings are accurate.

Usage:
    python3 recalculate_ratings.py

This will:
1. Reset all player ratings to defaults
2. Process all matches in chronological order
3. Recalculate TrueSkill ratings
4. Update all MatchPlayer records with correct before/after ratings
"""
import trueskill
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Player, Match, MatchPlayer, PlayerMatchMetrics
from app.database import DATABASE_URL
from app.rating_system import RatingSystem, RECENCY_ENABLED
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TrueSkill setup (same as rating_system.py)
trueskill.setup(
    mu=25.0,
    sigma=8.333,
    beta=4.166,
    tau=0.0833,
    draw_probability=0.0
)


def recalculate_all_ratings(session):
    """
    Recalculate all player ratings from scratch.

    Args:
        session: Database session
    """
    logger.info(f"\n{'='*70}")
    logger.info("RECALCULATING ALL TRUESKILL RATINGS")
    logger.info(f"{'='*70}\n")

    # Step 1: Reset all players to default ratings
    logger.info("Step 1: Resetting all players to default ratings...")
    players = session.query(Player).all()

    for player in players:
        player.mu = 25.0
        player.sigma = 8.333
        player.total_games = 0
        player.wins = 0
        player.losses = 0
        player.terran_games = 0
        player.protoss_games = 0
        player.zerg_games = 0
        player.random_games = 0
        player.recency_weighted_mmr = None
        player.last_played = None

    session.commit()
    logger.info(f"   Reset {len(players)} players to default (mu=25.0, sigma=8.333)")

    # Step 2: Get all matches in chronological order
    logger.info("\nStep 2: Loading all matches in chronological order...")
    matches = session.query(Match).order_by(Match.played_at).all()
    logger.info(f"   Found {len(matches)} matches to process")

    # Step 3: Backup match participation data before deleting
    logger.info("\nStep 3: Backing up match participation data...")
    old_match_players = session.query(MatchPlayer).all()

    # Create a backup structure: match_id -> list of (player_id, team_number, race, won)
    match_participants = {}
    for mp in old_match_players:
        if mp.match_id not in match_participants:
            match_participants[mp.match_id] = []
        match_participants[mp.match_id].append({
            'player_id': mp.player_id,
            'team_number': mp.team_number,
            'race': mp.race,
            'won': mp.won
        })

    logger.info(f"   Backed up participation data for {len(match_participants)} matches")

    # Now delete the old records
    logger.info("\nStep 4: Clearing existing MatchPlayer records...")
    session.query(MatchPlayer).delete()
    session.commit()
    logger.info("   ✓ Cleared all MatchPlayer records")

    # Step 5: Process each match
    logger.info("\nStep 5: Processing matches and recalculating ratings...")
    logger.info(f"   {'Progress':<15} {'Match Date':<20} {'Map':<25} {'Game Mode':<15}")
    logger.info(f"   {'-'*15} {'-'*20} {'-'*25} {'-'*15}")

    # Store current ratings for each player (in memory for speed)
    player_ratings = {}
    for player in players:
        player_ratings[player.id] = {'mu': 25.0, 'sigma': 8.333}

    processed = 0
    skipped = 0

    for idx, match in enumerate(matches, 1):
        if idx % 100 == 0 or idx == len(matches):
            logger.info(f"   {idx}/{len(matches):<10} {str(match.played_at)[:19]:<20} {match.map_name[:23]:<25} {match.game_mode.value:<15}")

        # Get participants for this match
        if match.id not in match_participants:
            skipped += 1
            continue

        participants = match_participants[match.id]

        # Group by team
        team_1 = [p for p in participants if p['team_number'] == 1]
        team_2 = [p for p in participants if p['team_number'] == 2]

        if not team_1 or not team_2:
            skipped += 1
            continue

        # Create TrueSkill Rating objects
        team_1_ratings = [
            trueskill.Rating(
                mu=player_ratings[p['player_id']]['mu'],
                sigma=player_ratings[p['player_id']]['sigma']
            )
            for p in team_1
        ]
        team_2_ratings = [
            trueskill.Rating(
                mu=player_ratings[p['player_id']]['mu'],
                sigma=player_ratings[p['player_id']]['sigma']
            )
            for p in team_2
        ]

        # Determine winner
        team_1_won = team_1[0]['won'] == 1
        ranks = [0, 1] if team_1_won else [1, 0]

        # Calculate new ratings
        try:
            new_ratings = trueskill.rate(
                [team_1_ratings, team_2_ratings],
                ranks=ranks
            )
            new_team_1_ratings = new_ratings[0]
            new_team_2_ratings = new_ratings[1]
        except Exception as e:
            logger.warning(f"   Error calculating ratings for match {match.id}: {e}")
            skipped += 1
            continue

        # Update players and create MatchPlayer records
        for i, participant_data in enumerate(team_1):
            player_id = participant_data['player_id']
            player = session.query(Player).filter(Player.id == player_id).first()

            if not player:
                continue

            old_rating = team_1_ratings[i]
            new_rating = new_team_1_ratings[i]

            # Create MatchPlayer record
            match_player = MatchPlayer(
                match_id=match.id,
                player_id=player.id,
                team_number=1,
                race=participant_data['race'],
                won=participant_data['won'],
                mu_before=old_rating.mu,
                sigma_before=old_rating.sigma,
                mu_after=new_rating.mu,
                sigma_after=new_rating.sigma
            )
            session.add(match_player)

            # Update player in-memory ratings
            player_ratings[player.id] = {'mu': new_rating.mu, 'sigma': new_rating.sigma}

            # Update player stats
            player.total_games += 1
            if participant_data['won']:
                player.wins += 1
            else:
                player.losses += 1

            # Update race stats
            race_name = participant_data['race'].value.lower()
            race_attr = f"{race_name}_games"
            if hasattr(player, race_attr):
                setattr(player, race_attr, getattr(player, race_attr) + 1)

            # Update last_played
            if not player.last_played or match.played_at > player.last_played:
                player.last_played = match.played_at

        for i, participant_data in enumerate(team_2):
            player_id = participant_data['player_id']
            player = session.query(Player).filter(Player.id == player_id).first()

            if not player:
                continue

            old_rating = team_2_ratings[i]
            new_rating = new_team_2_ratings[i]

            # Create MatchPlayer record
            match_player = MatchPlayer(
                match_id=match.id,
                player_id=player.id,
                team_number=2,
                race=participant_data['race'],
                won=participant_data['won'],
                mu_before=old_rating.mu,
                sigma_before=old_rating.sigma,
                mu_after=new_rating.mu,
                sigma_after=new_rating.sigma
            )
            session.add(match_player)

            # Update player in-memory ratings
            player_ratings[player.id] = {'mu': new_rating.mu, 'sigma': new_rating.sigma}

            # Update player stats
            player.total_games += 1
            if participant_data['won']:
                player.wins += 1
            else:
                player.losses += 1

            # Update race stats
            race_name = participant_data['race'].value.lower()
            race_attr = f"{race_name}_games"
            if hasattr(player, race_attr):
                setattr(player, race_attr, getattr(player, race_attr) + 1)

            # Update last_played
            if not player.last_played or match.played_at > player.last_played:
                player.last_played = match.played_at

        processed += 1

        # Commit every 100 matches to avoid memory issues
        if idx % 100 == 0:
            session.commit()

    # Final commit
    session.commit()

    # Step 6: Apply final ratings to players
    logger.info("\nStep 6: Applying final ratings to all players...")
    for player in players:
        if player.id in player_ratings:
            player.mu = player_ratings[player.id]['mu']
            player.sigma = player_ratings[player.id]['sigma']

    session.commit()

    # Step 7: Recalculate recency-weighted MMR if enabled
    if RECENCY_ENABLED:
        logger.info("\nStep 7: Recalculating recency-weighted MMR...")
        for player in players:
            if player.total_games > 0:
                RatingSystem.update_recency_weighted_rating(session, player)
        logger.info(f"   ✓ Updated recency-weighted MMR for {len(players)} players")

    logger.info(f"\n{'='*70}")
    logger.info("✓ RECALCULATION COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"Processed: {processed} matches")
    logger.info(f"Skipped: {skipped} matches")
    logger.info(f"Total players: {len(players)}")
    logger.info(f"{'='*70}\n")

    return True


def main():
    logger.info("\n⚠️  WARNING: This will recalculate ALL player ratings!")
    logger.info("This process will:")
    logger.info("  - Reset all players to default TrueSkill (mu=25.0, sigma=8.333)")
    logger.info("  - Process all matches in chronological order")
    logger.info("  - Recalculate ratings and statistics")
    logger.info("  - Update all MatchPlayer records\n")
    logger.info("This is IRREVERSIBLE. Make a database backup first!\n")

    response = input("Do you want to continue? Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        logger.info("Recalculation cancelled.")
        return

    # Create database session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        recalculate_all_ratings(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
