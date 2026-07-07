#!/usr/bin/env python3
"""
Backfill TrueSkill Win Probability Predictions

Recalculates predicted_team1_win_prob using: P(T1) = Φ((Σμ1 - Σμ2) / √(Σσ1² + Σσ2²))

Usage: cd backend && python scripts/backfill_trueskill_predictions.py [--dry-run]
"""

import sys
import os
import argparse
import math
from scipy.stats import norm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Match, MatchPlayer


def calculate_trueskill_win_probability(team1_mu_sigmas, team2_mu_sigmas):
    team1_mu = sum(mu for mu, _ in team1_mu_sigmas)
    team2_mu = sum(mu for mu, _ in team2_mu_sigmas)

    team1_sigma_sq = sum(sigma**2 for _, sigma in team1_mu_sigmas)
    team2_sigma_sq = sum(sigma**2 for _, sigma in team2_mu_sigmas)

    total_sigma = math.sqrt(team1_sigma_sq + team2_sigma_sq)

    if total_sigma == 0:
        return 0.5, 0.5

    delta_mu = team1_mu - team2_mu
    team1_win_prob = float(norm.cdf(delta_mu / total_sigma))

    return team1_win_prob, 1.0 - team1_win_prob


def backfill_predictions(dry_run=False):
    db = SessionLocal()

    try:
        matches = db.query(Match).filter(Match.played_at.isnot(None)).all()
        print(f"Found {len(matches)} matches to process")

        updated = 0
        skipped = 0

        for match in matches:
            match_players = (
                db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
            )

            team1_players = [mp for mp in match_players if mp.team_number == 1]
            team2_players = [mp for mp in match_players if mp.team_number == 2]

            if not team1_players or not team2_players:
                skipped += 1
                continue

            if any(
                mp.mu_before is None or mp.sigma_before is None for mp in match_players
            ):
                print(f"  Match {match.id}: Missing mu_before/sigma_before, skipping")
                skipped += 1
                continue

            team1_ratings = [(mp.mu_before, mp.sigma_before) for mp in team1_players]
            team2_ratings = [(mp.mu_before, mp.sigma_before) for mp in team2_players]

            new_t1_prob, new_t2_prob = calculate_trueskill_win_probability(
                team1_ratings, team2_ratings
            )

            old_t1_prob = match.predicted_team1_win_prob

            if old_t1_prob is not None:
                if abs(new_t1_prob - old_t1_prob) < 0.001:
                    continue

            if dry_run:
                print(
                    f"  Match {match.id}: Would update {old_t1_prob:.1%} -> {new_t1_prob:.1%}"
                )
            else:
                match.predicted_team1_win_prob = new_t1_prob
                match.predicted_team2_win_prob = new_t2_prob
                updated += 1

                if updated % 20 == 0:
                    db.commit()
                    print(f"  Processed {updated} matches...")

        if not dry_run:
            db.commit()

        print()
        print("=" * 60)
        print(f"Total: {len(matches)} | Updated: {updated} | Skipped: {skipped}")

        if dry_run:
            print("\n[DRY RUN - no changes made]")
        else:
            print(f"\n✓ Successfully updated {updated} match predictions")

    finally:
        db.close()


def show_sample(match_id=None):
    db = SessionLocal()

    try:
        if match_id:
            matches = [db.query(Match).filter(Match.id == match_id).first()]
            if not matches[0]:
                print(f"Match {match_id} not found")
                return
        else:
            matches = (
                db.query(Match)
                .filter(Match.played_at.isnot(None))
                .order_by(Match.id.desc())
                .limit(5)
                .all()
            )

        for match in matches:
            match_players = (
                db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
            )

            team1 = [mp for mp in match_players if mp.team_number == 1]
            team2 = [mp for mp in match_players if mp.team_number == 2]

            if not team1 or not team2:
                continue

            team1_ratings = [(mp.mu_before, mp.sigma_before) for mp in team1]
            team2_ratings = [(mp.mu_before, mp.sigma_before) for mp in team2]

            new_t1, new_t2 = calculate_trueskill_win_probability(
                team1_ratings, team2_ratings
            )

            print(f"\nMatch {match.id}:")
            print(
                f"  Current:    T1={match.predicted_team1_win_prob:.1%} | T2={match.predicted_team2_win_prob:.1%}"
            )
            print(f"  Calculated: T1={new_t1:.1%} | T2={new_t2:.1%}")
            print(
                f"  Delta:      {abs(new_t1 - (match.predicted_team1_win_prob or 0.5)):.1%}"
            )
            print(f"  Team 1: {sum(mp.mu_before for mp in team1):.1f} total mu")
            print(f"  Team 2: {sum(mp.mu_before for mp in team2):.1f} total mu")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill TrueSkill predictions")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes",
    )
    parser.add_argument(
        "--sample", action="store_true", help="Show sample calculations"
    )
    parser.add_argument(
        "--match", type=int, help="Show calculation for specific match ID"
    )

    args = parser.parse_args()

    if args.sample or args.match:
        show_sample(args.match)
    else:
        backfill_predictions(dry_run=args.dry_run)
