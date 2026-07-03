import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

db_path = Path("/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db")


def perform_raw_regression():
    if not db_path.exists():
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)

    query = """
    SELECT 
        mp.won,
        pmm.minerals_collected,
        pmm.vespene_collected,
        pmm.workers_created,
        pmm.units_trained,
        pmm.army_value_built,
        pmm.army_value_killed,
        pmm.damage_dealt,
        pmm.damage_taken,
        pmm.apm,
        pmm.workers_killed,
        pmm.workers_lost,
        pmm.supply_block_seconds,
        pmm.lethality_score
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

    print("\n=== RAW DATA CORRELATION ANALYSIS (Win Prediction) ===")
    print(
        "Identifying which raw replay metrics most strongly correlate with winning.\n"
    )

    correlations = df.corr()["won"].sort_values(ascending=False).drop(["won"])

    print("Raw Metric Correlations with Winning:")
    print(correlations)

    print("\n--- Top Performers ---")
    for i, (metric, val) in enumerate(correlations.head(5).items(), 1):
        print(f"{i}. {metric}: {val:.4f}")

    print("\n--- Performance Killers (Negative Correlation) ---")
    for i, (metric, val) in enumerate(correlations.tail(3).items(), 1):
        print(f"{i}. {metric}: {val:.4f}")

    print("\n--- Formula Refinement Insight ---")
    combat_avg = correlations[
        ["damage_dealt", "army_value_killed", "lethality_score"]
    ].mean()
    eco_avg = correlations[
        ["minerals_collected", "workers_created", "army_value_built"]
    ].mean()

    print(f"Average Combat Raw Correlation: {combat_avg:.4f}")
    print(f"Average Economic Raw Correlation: {eco_avg:.4f}")

    ratio = combat_avg / eco_avg if eco_avg != 0 else 0
    print(f"Combat-to-Economy Importance Ratio: {ratio:.2f}x")

    if ratio > 2.0:
        print(
            ">> Analysis: Combat is exponentially more important than economy for winning in this group."
        )
    elif ratio > 1.2:
        print(">> Analysis: Combat is moderately more important than economy.")
    else:
        print(">> Analysis: Combat and Economy have balanced impact on victory.")


if __name__ == "__main__":
    perform_raw_regression()
