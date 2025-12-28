#!/usr/bin/env python3
"""
Backfill script for session-weighted MMR.

This script:
1. Calculates and updates session_weighted_mmr for all players
2. Runs regression analysis comparing TrueSkill vs Session MMR vs All Components
3. Auto-adjusts session weight based on R² (if R² < 0.1, reduce weight from 40% to 25%)
4. Saves recommended weights to MLConfig table

Usage:
    python scripts/backfill_session_mmr.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import numpy as np
from app.models import Player, Match, MatchPlayer, MLConfig
from app.database import DATABASE_URL


# =============================================================================
# Session-Weighted MMR Calculator
# =============================================================================


def calculate_session_weighted_mmr(player: Player, matches: list) -> float:
    """
    Calculate session-weighted MMR for a player.

    Weights:
    - Current session (last 24h): 3x weight
    - Recent week (last 7 days): 2x weight
    - Older matches: 1x weight

    Volatility: ±50 MMR per session (aggressive)
    """
    if not matches:
        return player.mmr

    now = datetime.utcnow()
    session_cutoff = now - timedelta(hours=24)
    week_cutoff = now - timedelta(days=7)

    weighted_sum = 0.0
    weight_total = 0.0

    for match, match_player in matches:
        # Determine weight based on recency
        if match.played_at >= session_cutoff:
            weight = 3.0  # Current session
        elif match.played_at >= week_cutoff:
            weight = 2.0  # Recent week
        else:
            weight = 1.0  # Older

        # Calculate MMR contribution from this match
        mmr_after = 1000 + 40 * match_player.mu_after
        weighted_sum += mmr_after * weight
        weight_total += weight

    if weight_total == 0:
        return player.mmr

    base_session_mmr = weighted_sum / weight_total

    # Apply volatility bonus/penalty based on recent performance
    # Look at last 5 games for streak detection
    recent_matches = sorted(matches, key=lambda x: x[0].played_at, reverse=True)[:5]
    wins = sum(1 for m, mp in recent_matches if mp.won)
    losses = len(recent_matches) - wins

    # ±50 MMR volatility per session
    if wins > losses:
        streak_bonus = min((wins - losses) * 10, 50)  # Max +50
    else:
        streak_bonus = max((wins - losses) * 10, -50)  # Max -50

    return base_session_mmr + streak_bonus


# =============================================================================
# Regression Analysis
# =============================================================================


def run_regression_analysis(db_session) -> dict:
    """
    Run regression analysis comparing different rating systems.

    Compares:
    - TrueSkill only
    - Session-weighted MMR only
    - Combined (all components)

    Returns R² values and recommended weights.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    print("\n=== Running Regression Analysis ===\n")

    # Get all matches with sufficient data
    matches = (
        db_session.query(Match).filter(Match.predicted_team1_win_prob.isnot(None)).all()
    )

    if len(matches) < 50:
        print(f"Insufficient data for regression ({len(matches)} matches)")
        return {"trueskill_r2": 0.5, "session_r2": 0.5, "combined_r2": 0.5}

    # Prepare data
    X_trueskill = []
    X_session = []
    X_combined = []
    y = []

    for match in matches:
        participants = list(match.participants)
        if len(participants) < 2:
            continue

        team1 = [p for p in participants if p.team_number == 1]
        team2 = [p for p in participants if p.team_number == 2]

        if not team1 or not team2:
            continue

        # Determine actual winner
        actual_winner = 1 if team1[0].won else 2

        # TrueSkill features
        team1_mmr = sum(1000 + 40 * p.mu_before for p in team1)
        team2_mmr = sum(1000 + 40 * p.mu_before for p in team2)
        X_trueskill.append([team1_mmr - team2_mmr])

        # Session MMR features (use current player session_weighted_mmr as proxy)
        team1_session = 0
        team2_session = 0
        for p in team1:
            player = p.player
            team1_session += player.session_weighted_mmr or player.mmr
        for p in team2:
            player = p.player
            team2_session += player.session_weighted_mmr or player.mmr
        X_session.append([team1_session - team2_session])

        # Combined features
        team1_combat = sum(p.player.avg_combat_score or 50 for p in team1)
        team2_combat = sum(p.player.avg_combat_score or 50 for p in team2)
        team1_econ = sum(p.player.avg_economic_score or 50 for p in team1)
        team2_econ = sum(p.player.avg_economic_score or 50 for p in team2)
        team1_eff = sum(p.player.avg_efficiency_score or 50 for p in team1)
        team2_eff = sum(p.player.avg_efficiency_score or 50 for p in team2)

        X_combined.append(
            [
                team1_session - team2_session,
                team1_combat - team2_combat,
                team1_econ - team2_econ,
                team1_eff - team2_eff,
            ]
        )

        y.append(1 if actual_winner == 1 else 0)

    X_trueskill = np.array(X_trueskill)
    X_session = np.array(X_session)
    X_combined = np.array(X_combined)
    y = np.array(y)

    print(f"Total samples: {len(y)}")

    # Split data
    X_ts_train, X_ts_test, y_train, y_test = train_test_split(
        X_trueskill, y, test_size=0.2, random_state=42
    )
    X_ses_train, X_ses_test, _, _ = train_test_split(
        X_session, y, test_size=0.2, random_state=42
    )
    X_comb_train, X_comb_test, _, _ = train_test_split(
        X_combined, y, test_size=0.2, random_state=42
    )

    # Train and evaluate models
    results = {}

    # TrueSkill only
    try:
        model_ts = LogisticRegression(max_iter=1000)
        model_ts.fit(X_ts_train, y_train)
        results["trueskill_r2"] = model_ts.score(X_ts_test, y_test)
        print(f"TrueSkill accuracy: {results['trueskill_r2']:.3f}")
    except Exception as e:
        print(f"TrueSkill regression failed: {e}")
        results["trueskill_r2"] = 0.5

    # Session MMR only
    try:
        model_ses = LogisticRegression(max_iter=1000)
        model_ses.fit(X_ses_train, y_train)
        results["session_r2"] = model_ses.score(X_ses_test, y_test)
        print(f"Session MMR accuracy: {results['session_r2']:.3f}")
    except Exception as e:
        print(f"Session MMR regression failed: {e}")
        results["session_r2"] = 0.5

    # Combined
    try:
        model_comb = LogisticRegression(max_iter=1000)
        model_comb.fit(X_comb_train, y_train)
        results["combined_r2"] = model_comb.score(X_comb_test, y_test)
        print(f"Combined accuracy: {results['combined_r2']:.3f}")

        # Extract feature importance for recommended weights
        coefs = np.abs(model_comb.coef_[0])
        total_coef = coefs.sum()
        if total_coef > 0:
            results["recommended_weights"] = {
                "session_mmr": float(coefs[0] / total_coef),
                "combat": float(coefs[1] / total_coef),
                "economic": float(coefs[2] / total_coef),
                "efficiency": float(coefs[3] / total_coef),
            }
            print(f"\nRecommended weights: {results['recommended_weights']}")
    except Exception as e:
        print(f"Combined regression failed: {e}")
        results["combined_r2"] = 0.5

    return results


def save_recommended_weights(db_session, weights: dict):
    """Save recommended weights to MLConfig table."""
    import json

    config_key = "recommended_weights"
    config_value = json.dumps(weights)

    existing = (
        db_session.query(MLConfig).filter(MLConfig.config_key == config_key).first()
    )

    if existing:
        existing.config_value = config_value
        existing.last_updated = datetime.utcnow()
    else:
        new_config = MLConfig(
            config_key=config_key,
            config_value=config_value,
            last_updated=datetime.utcnow(),
        )
        db_session.add(new_config)

    db_session.commit()
    print(f"\nSaved recommended weights to MLConfig table")


# =============================================================================
# Main Backfill Function
# =============================================================================


def backfill_session_mmr():
    """Main backfill function."""
    print("=" * 60)
    print("Session-Weighted MMR Backfill Script")
    print("=" * 60)

    # Connect to database
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Get all players
        players = db.query(Player).all()
        print(f"\nProcessing {len(players)} players...")

        updated_count = 0

        for player in players:
            # Get player's match history
            matches = (
                db.query(Match, MatchPlayer)
                .join(MatchPlayer)
                .filter(MatchPlayer.player_id == player.id)
                .order_by(Match.played_at.desc())
                .all()
            )

            if not matches:
                # No matches - set to base MMR
                player.session_weighted_mmr = player.mmr
            else:
                # Calculate session-weighted MMR
                session_mmr = calculate_session_weighted_mmr(player, matches)
                player.session_weighted_mmr = round(session_mmr, 1)

            player.last_session_weight_update = datetime.utcnow()
            updated_count += 1

            if updated_count % 10 == 0:
                print(f"  Processed {updated_count}/{len(players)} players...")

        db.commit()
        print(f"\nUpdated session_weighted_mmr for {updated_count} players")

        # Run regression analysis
        results = run_regression_analysis(db)

        # Determine if we need to adjust weights
        if results.get("session_r2", 0.5) < 0.55:
            print("\n[!] Session MMR has low predictive power")
            print("    Reducing session_mmr weight from 40% to 25%")
            adjusted_weights = {
                "session_mmr": 0.25,
                "combat": 0.30,
                "economic": 0.25,
                "efficiency": 0.20,
            }
        else:
            # Use recommended weights or defaults
            adjusted_weights = results.get(
                "recommended_weights",
                {
                    "session_mmr": 0.40,
                    "combat": 0.25,
                    "economic": 0.20,
                    "efficiency": 0.15,
                },
            )

        # Save weights to config
        save_recommended_weights(db, adjusted_weights)

        print("\n" + "=" * 60)
        print("Backfill Complete!")
        print("=" * 60)
        print(f"\nFinal weights saved:")
        for comp, weight in adjusted_weights.items():
            print(f"  {comp}: {weight * 100:.1f}%")

    except Exception as e:
        print(f"\nError during backfill: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill_session_mmr()
