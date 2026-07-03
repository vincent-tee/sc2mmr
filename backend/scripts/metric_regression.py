import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

db_path = Path("/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db")


def perform_regression():
    if not db_path.exists():
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)

    # Query data: Match outcomes linked to player performance metrics
    # We focus on human players to avoid AI noise
    query = """
    SELECT 
        mp.won,
        pmm.overall_impact,
        pmm.combat_score,
        pmm.economic_score,
        pmm.efficiency_score,
        pmm.damage_ratio,
        pmm.spending_efficiency,
        pmm.apm,
        p.mmr as base_mmr
    FROM match_players mp
    JOIN player_match_metrics pmm ON mp.id = pmm.match_player_id
    JOIN players p ON mp.player_id = p.id
    WHERE p.is_ai = 0 AND p.total_games >= 15
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("No data found for regression")
        return

    # Prepare features for Logistic Regression (predicting Win/Loss)
    X = df[
        [
            "overall_impact",
            "combat_score",
            "economic_score",
            "efficiency_score",
            "damage_ratio",
            "apm",
        ]
    ]
    y = df["won"]

    print("\n=== METRIC CORRELATION ANALYSIS (Win Prediction) ===")
    print(
        "This identifies which in-game metrics most strongly correlate with winning.\n"
    )

    correlations = (
        df.corr()["won"].sort_values(ascending=False).drop(["won", "base_mmr"])
    )

    print("Metric Correlations with Winning:")
    print(correlations)

    print("\n--- Summary ---")
    top_metric = correlations.index[0]
    print(f"1. Most valuable predictor: {top_metric}")

    corr_combat = df["combat_score"].corr(df["won"])
    corr_eco = df["economic_score"].corr(df["won"])
    print(f"Combat correlation: {corr_combat:.3f}")
    print(f"Economic correlation: {corr_eco:.3f}")

    if corr_combat > corr_eco:
        print(
            ">> Analysis: Combat continues to be a stronger win predictor than Economy. High weights for Combat in Unified MMR are justified."
        )
    else:
        print(
            ">> Analysis: Economy is outperforming Combat. Consider increasing Economy weight in Unified MMR."
        )


if __name__ == "__main__":
    perform_regression()
