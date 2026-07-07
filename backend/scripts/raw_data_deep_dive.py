import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

db_path = Path("/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db")


def deep_dive_analysis():
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
    WHERE p.is_ai = 0 AND p.total_games >= 5
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("No data found")
        return

    print("\n=== RAW DATA DISTRIBUTION & ANOMALY ANALYSIS ===")

    stats = df.describe().transpose()[["mean", "std", "min", "max"]]
    stats["skew"] = df.skew()
    print("\n--- Metric Distributions ---")
    print(stats)

    correlations = df.corr()["won"].sort_values(ascending=False).drop(["won"])
    print("\n--- Win Correlation Ranking ---")
    print(correlations)

    print("\n--- Potential Anomalies (3+ Sigma) ---")
    for col in df.columns:
        if col == "won":
            continue
        mean = df[col].mean()
        std = df[col].std()
        outliers = df[np.abs(df[col] - mean) > (3 * std)]
        if not outliers.empty:
            print(
                f"[{col}]: {len(outliers)} games exceed 3rd sigma (Max: {df[col].max():.1f}, Mean: {mean:.1f})"
            )

    print("\n--- Strategic Insights ---")
    if correlations["damage_dealt"] > correlations["minerals_collected"]:
        ratio = (
            correlations["damage_dealt"] / correlations["minerals_collected"]
            if correlations["minerals_collected"] != 0
            else 99
        )
        print(
            f">> Lethality Bias: Damage is {ratio:.1f}x more correlated with winning than minerals."
        )

    if correlations["workers_lost"] < -0.05:
        print(
            f">> Fragility Warning: Early worker losses ({correlations['workers_lost']:.3f}) are a major predictor of defeat."
        )


if __name__ == "__main__":
    deep_dive_analysis()
