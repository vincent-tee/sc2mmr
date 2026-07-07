import sqlite3
import os

db_path = "/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db"

if not os.path.exists(db_path):
    # Try alternate path
    db_path = "/home/vtee/projects/sc2mmr/data/sc2mmr.db"
    if not os.path.exists(db_path):
        print(f"Database not found")
        exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

query = """
SELECT name, mmr, unified_mmr, handicap_corrected_mmr, outperformance_pct, avg_combat_score, total_games, wins, losses, is_ai
FROM players 
WHERE is_core_player = 1 AND is_ai = 0
ORDER BY unified_mmr DESC 
LIMIT 20;
"""

print(
    f"{'Rank':<4} {'Name':<15} {'Unified':<8} {'Raw':<8} {'HC MMR':<8} {'Outperf%':<10} {'Combat':<8} {'Games':<6}"
)
print("-" * 80)

try:
    cursor.execute(query)
    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        name = row["name"]
        unified = f"{row['unified_mmr']:.0f}" if row["unified_mmr"] else "N/A"
        raw = f"{row['mmr']:.0f}"
        hc_mmr = (
            f"{row['handicap_corrected_mmr']:.0f}"
            if row["handicap_corrected_mmr"]
            else "N/A"
        )
        outperf = (
            f"{row['outperformance_pct']:+.1f}%"
            if row["outperformance_pct"]
            else "0.0%"
        )
        combat = f"{row['avg_combat_score']:.1f}" if row["avg_combat_score"] else "0.0"
        games = row["total_games"]
        print(
            f"{i:<4} {name:<15} {unified:<8} {raw:<8} {hc_mmr:<8} {outperf:<10} {combat:<8} {games:<6}"
        )
except Exception as e:
    print(f"Error: {e}")

conn.close()
