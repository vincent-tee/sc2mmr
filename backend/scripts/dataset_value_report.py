import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

db_path = Path("/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db")


def analyze_dataset():
    if not db_path.exists():
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)

    matches_count = pd.read_sql("SELECT COUNT(*) FROM matches", conn).iloc[0, 0]
    players_count = pd.read_sql(
        "SELECT COUNT(*) FROM players WHERE is_ai = 0", conn
    ).iloc[0, 0]
    print(f"--- Dataset Overview ---")
    print(f"Total Matches: {matches_count}")
    print(f"Human Players: {players_count}")

    query = """
    SELECT 
        won, damage_dealt, damage_ratio, spending_efficiency, 
        army_value_killed, army_value_built, apm, 
        overall_impact, economic_score, combat_score
    FROM match_players mp
    JOIN player_match_metrics pmm ON mp.id = pmm.match_player_id
    JOIN players p ON mp.player_id = p.id
    WHERE p.is_ai = 0
    """
    df = pd.read_sql(query, conn)
    correlations = df.corr()["won"].sort_values(ascending=False)
    print(f"\n--- Win Correlation Factors (Top 5) ---")
    print(correlations[1:6])

    # 3. Synergy Power Couples
    query = """
    SELECT p1.name as player1, p2.name as player2, games_together, synergy_score, win_rate
    FROM player_synergy ps
    JOIN players p1 ON ps.player_ids_key LIKE p1.id || ',%' OR ps.player_ids_key LIKE '%,' || p1.id || ',%'
    JOIN players p2 ON ps.player_ids_key LIKE '%,' || p2.id
    WHERE games_together >= 10 AND player_count = 2
    ORDER BY synergy_score DESC
    LIMIT 5
    """
    synergy_df = pd.read_sql(
        "SELECT player_ids_key, matches_played, synergy_score, win_rate FROM player_synergy WHERE player_count = 2 AND matches_played >= 10 ORDER BY synergy_score DESC LIMIT 5",
        conn,
    )
    print(f"\n--- Top Synergy Pairs (Min 10 games) ---")
    for _, row in synergy_df.iterrows():
        pids = row["player_ids_key"].split(",")
        names = []
        for pid in pids:
            name = pd.read_sql(f"SELECT name FROM players WHERE id = {pid}", conn).iloc[
                0, 0
            ]
            names.append(name)
        print(
            f"{' + '.join(names)}: {row['win_rate'] * 100:.1f}% WR (Score: {row['synergy_score']:.1f})"
        )

    # 4. Map Imbalance Check
    query = """
    SELECT map_name, COUNT(*) as games, AVG(predicted_team1_win_prob) as avg_t1_prob
    FROM matches
    GROUP BY map_name
    HAVING games >= 20
    ORDER BY games DESC
    """
    map_df = pd.read_sql(query, conn)
    print(f"\n--- Map Popularity ---")
    print(map_df[["map_name", "games"]])

    conn.close()


if __name__ == "__main__":
    analyze_dataset()
