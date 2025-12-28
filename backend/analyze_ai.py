from app.database import SessionLocal
from app.models import Player
import json


def analyze_ai_stats():
    db = SessionLocal()
    try:
        ai_players = db.query(Player).filter(Player.is_ai == 1).all()
        stats = []
        for p in ai_players:
            stats.append(
                {
                    "name": p.name,
                    "mmr": p.mmr,
                    "total_games": p.total_games,
                    "win_rate": p.win_rate,
                    "overall_impact": p.avg_overall_impact,
                }
            )
        print(json.dumps(stats, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    analyze_ai_stats()
