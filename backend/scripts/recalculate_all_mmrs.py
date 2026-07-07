"""
Comprehensive script to recalculate ALL rating systems chronologically.
Updates:
1. TrueSkill (mu, sigma)
2. Hybrid MMR (Performance-adjusted)
3. Recency-Weighted MMR
4. Performance Features (PIM)
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import trueskill
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import (
    Player,
    Match,
    MatchPlayer,
    PlayerMatchMetrics,
    PerformanceFeatures,
)
from app.config import settings
from app.rating_system import RatingSystem
from app.services.pi_calculator import PICalculator
from app.services.handicap_mmr_service import HandicapCorrectedMMRService
from app.services.ml_features_service import MLFeaturesService
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# TrueSkill setup from config
trueskill.setup(
    mu=25.0,
    sigma=8.333,
    beta=settings.trueskill_beta,
    tau=settings.trueskill_tau,
    draw_probability=settings.trueskill_draw_probability,
)


def recalculate():
    engine = create_engine(f"sqlite:///{backend_path}/data/sc2mmr.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    pi_calc = PICalculator()

    try:
        logger.info("Step 1: Resetting all players...")
        players = session.query(Player).all()
        for p in players:
            p.mu = 25.0
            p.sigma = 8.333
            # In the new 100x scale, mu=25 is 3500 MMR
            p.hybrid_mmr = 3500.0
            p.total_games = 0
            p.wins = 0
            p.losses = 0
            p.terran_games = 0
            p.protoss_games = 0
            p.zerg_games = 0
            p.random_games = 0
            p.recency_weighted_mmr = 3500.0
            p.avg_pim = 0.0
            p.last_played = None

        session.commit()

        logger.info("Step 2: Loading matches chronologically...")
        matches = session.query(Match).order_by(Match.played_at.asc()).all()

        # Backup match players info
        match_participants = {}
        all_mps = session.query(MatchPlayer).all()
        for mp in all_mps:
            if mp.match_id not in match_participants:
                match_participants[mp.match_id] = []
            match_participants[mp.match_id].append(
                {
                    "player_id": mp.player_id,
                    "team_number": mp.team_number,
                    "race": mp.race,
                    "won": mp.won,
                }
            )

        logger.info("Step 3: Clearing existing results...")
        session.query(PerformanceFeatures).delete()
        session.query(MatchPlayer).delete()
        session.commit()

        logger.info(f"Step 4: Processing {len(matches)} matches...")

        player_ratings = {
            p.id: {"mu": 25.0, "sigma": 8.333, "hybrid": 3500.0} for p in players
        }

        for idx, match in enumerate(matches, 1):
            participants = match_participants.get(match.id, [])
            if not participants:
                continue

            team_1 = [p for p in participants if p["team_number"] == 1]
            team_2 = [p for p in participants if p["team_number"] == 2]
            if not team_1 or not team_2:
                continue

            # No participant on either team is marked as having won: the
            # winner genuinely could not be determined at ingest time (no
            # stats to fall back on) rather than one team having actually
            # lost. Defaulting to "team 2 wins" here (as the code used to)
            # fabricates a rating outcome from no signal — skip the match
            # entirely instead (void, no rating impact) rather than guess.
            if not any(p["won"] == 1 for p in participants):
                logger.warning(
                    f"Skipping match {match.id}: no winner could be determined "
                    "(no team has any won=True player)"
                )
                continue

            # Prepare TrueSkill ratings
            t1_ratings = [
                trueskill.Rating(
                    mu=player_ratings[p["player_id"]]["mu"],
                    sigma=player_ratings[p["player_id"]]["sigma"],
                )
                for p in team_1
            ]
            t2_ratings = [
                trueskill.Rating(
                    mu=player_ratings[p["player_id"]]["mu"],
                    sigma=player_ratings[p["player_id"]]["sigma"],
                )
                for p in team_2
            ]

            # Rate
            team_1_won = team_1[0]["won"] == 1
            new_ratings = trueskill.rate(
                [t1_ratings, t2_ratings], ranks=[0, 1] if team_1_won else [1, 0]
            )

            # Calculate match averages for PIM
            match_averages = pi_calc.calculate_match_averages(session, match.id)

            # Update each player
            for team_idx, team_data in enumerate([team_1, team_2]):
                for p_idx, p_data in enumerate(team_data):
                    pid = p_data["player_id"]
                    player = session.query(Player).get(pid)
                    if not player:
                        continue

                    old_rating = (
                        t1_ratings[p_idx] if team_idx == 0 else t2_ratings[p_idx]
                    )
                    new_rating = new_ratings[team_idx][p_idx]

                    # 1. Update TrueSkill
                    mu_before, sigma_before = old_rating.mu, old_rating.sigma
                    mu_after, sigma_after = new_rating.mu, new_rating.sigma

                    # 2. Calculate MMR change (display scale)
                    mmr_before = RatingSystem.calculate_display_mmr(
                        mu_before, sigma_before
                    )
                    mmr_after = RatingSystem.calculate_display_mmr(
                        mu_after, sigma_after
                    )
                    raw_change = mmr_after - mmr_before

                    # 3. Create MatchPlayer
                    mp = MatchPlayer(
                        match_id=match.id,
                        player_id=pid,
                        team_number=team_idx + 1,
                        race=p_data["race"],
                        won=p_data["won"],
                        mu_before=mu_before,
                        sigma_before=sigma_before,
                        mu_after=mu_after,
                        sigma_after=sigma_after,
                        mmr_before=mmr_before,
                        mmr_after=mmr_after,
                    )
                    session.add(mp)
                    session.flush()  # Get mp.id

                    # 4. Calculate PIM and Hybrid change
                    perf = pi_calc.calculate_and_store_features(
                        session, mp, raw_change, match_averages
                    )

                    # 5. Update Hybrid MMR
                    change_val = (
                        perf.hybrid_mmr_change
                        if perf.hybrid_mmr_change is not None
                        else 0.0
                    )
                    player_ratings[pid]["hybrid"] += change_val

                    # Update in-memory
                    player_ratings[pid]["mu"] = mu_after
                    player_ratings[pid]["sigma"] = sigma_after

                    # Update Player stats
                    player.mu = mu_after
                    player.sigma = sigma_after
                    player.mmr = mmr_after
                    player.hybrid_mmr = player_ratings[pid]["hybrid"]
                    player.total_games += 1
                    if p_data["won"]:
                        player.wins += 1
                    else:
                        player.losses += 1

                    race_val = (
                        p_data["race"].value
                        if hasattr(p_data["race"], "value")
                        else str(p_data["race"])
                    )
                    race_attr = f"{race_val.lower()}_games"
                    if hasattr(player, race_attr):
                        setattr(player, race_attr, getattr(player, race_attr) + 1)

                    if not player.last_played or match.played_at > player.last_played:
                        player.last_played = match.played_at

            try:
                MLFeaturesService.calculate_and_save_predictions(session, match.id)
            except Exception as e:
                logger.warning(f"ML prediction failed for match {match.id}: {e}")

            if idx % 50 == 0:
                logger.info(f"Processed {idx}/{len(matches)} matches")
                session.commit()

        session.commit()

        logger.info("Step 5: Finalizing Recency-Weighted MMR...")
        for p in players:
            RatingSystem.update_recency_weighted_rating(session, p)
            # Update average PIM
            avg_pim = (
                session.query(func.avg(PerformanceFeatures.pim))
                .join(MatchPlayer)
                .filter(MatchPlayer.player_id == p.id)
                .scalar()
            )
            p.avg_pim = avg_pim or 0.0

        logger.info("Step 6: Updating Handicap-Corrected and Unified MMR...")
        HandicapCorrectedMMRService.update_all_players(session)

        session.commit()
        logger.info("Done! All ratings recalculated.")

    except Exception as e:
        logger.error(f"Error during recalculation: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    recalculate()
