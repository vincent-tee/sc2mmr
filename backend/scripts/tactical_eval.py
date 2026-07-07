import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import json

db_path = Path("/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db")


def evaluate_tactical_intelligence():
    if not db_path.exists():
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)

    query = """
    SELECT 
        m.id, m.map_name, 
        m.predicted_team1_win_prob,
        (SELECT mp.team_number FROM match_players mp WHERE mp.match_id = m.id AND mp.won = 1 LIMIT 1) as actual_winner
    FROM matches m
    WHERE m.predicted_team1_win_prob IS NOT NULL
    ORDER BY m.played_at DESC
    LIMIT 200
    """
    df_matches = pd.read_sql(query, conn)

    if not df_matches.empty:
        df_matches = df_matches.dropna(subset=["actual_winner"])

        df_matches["pred_win"] = df_matches["predicted_team1_win_prob"] > 0.5
        df_matches["actual_win"] = df_matches["actual_winner"] == 1

        accuracy = (df_matches["pred_win"] == df_matches["actual_win"]).mean()
        print(f"--- ML Engine Prediction Accuracy (Last {len(df_matches)} matches) ---")
        print(f"Accuracy: {accuracy * 100:.1f}%")

        correct = df_matches[df_matches["pred_win"] == df_matches["actual_win"]]
        wrong = df_matches[df_matches["pred_win"] != df_matches["actual_win"]]

        avg_conf_correct = (
            np.mean([max(p, 1 - p) for p in correct["predicted_team1_win_prob"]])
            if not correct.empty
            else 0
        )
        avg_conf_wrong = (
            np.mean([max(p, 1 - p) for p in wrong["predicted_team1_win_prob"]])
            if not wrong.empty
            else 0
        )

        print(f"Avg confidence on CORRECT: {avg_conf_correct * 100:.1f}%")
        print(f"Avg confidence on WRONG: {avg_conf_wrong * 100:.1f}%")

    query = """
    SELECT 
        mp.won,
        pf.ml_shap_values
    FROM match_players mp
    JOIN performance_features pf ON mp.id = pf.match_player_id
    WHERE pf.ml_shap_values IS NOT NULL AND pf.ml_shap_values != '[]'
    """
    df_shap = pd.read_sql(query, conn)

    if not df_shap.empty:
        print(f"\n--- Tactical Factor Validity (SHAP) ---")
        win_impacts = {}
        loss_impacts = {}

        for _, row in df_shap.iterrows():
            won = row["won"]
            try:
                impacts = json.loads(row["ml_shap_values"])
                for imp in impacts:
                    feature = imp["feature"]
                    val = imp["impact"]
                    target_dict = win_impacts if won else loss_impacts
                    if feature not in target_dict:
                        target_dict[feature] = []
                    target_dict[feature].append(val)
            except:
                continue

        print(f"{'Feature':<20} | {'Impact in Wins':<15} | {'Impact in Losses':<15}")
        print("-" * 55)

        all_features = sorted(win_impacts.keys())
        for feat in all_features:
            w_avg = np.mean(win_impacts[feat])
            l_avg = np.mean(loss_impacts.get(feat, [0]))
            print(f"{feat:<20} | {w_avg:>14.3f} | {l_avg:>14.3f}")

        print(
            "\n>> Interpretation: High positive numbers in 'Impact in Wins' mean the feature correctly predicts success."
        )
        print(
            ">> High negative numbers in 'Impact in Losses' mean the feature correctly flags why players lose."
        )

    conn.close()


if __name__ == "__main__":
    evaluate_tactical_intelligence()
