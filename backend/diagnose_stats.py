from app.database import SessionLocal
from app.models import Match, MatchPlayer, PlayerMatchMetrics
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def diagnose():
    db = SessionLocal()
    try:
        matches = db.query(Match).all()
        total_matches = len(matches)
        incomplete_matches = 0

        print(f"{'Match ID':<10} | {'Played At':<20} | {'Status'}")
        print("-" * 50)

        for m in matches:
            # Check if all players in this match have valid stats
            metrics = (
                db.query(PlayerMatchMetrics)
                .join(MatchPlayer)
                .filter(MatchPlayer.match_id == m.id)
                .all()
            )

            if not metrics:
                status = "❌ MISSING ALL METRICS"
                incomplete_matches += 1
            else:
                # Check if metrics are actually zero
                total_minerals = sum(me.minerals_collected or 0 for me in metrics)
                total_damage = sum(me.damage_dealt or 0 for me in metrics)
                total_workers = sum(me.workers_created or 0 for me in metrics)

                if total_minerals < 1000 or total_damage == 0:
                    status = f"⚠️ INCOMPLETE (Min: {total_minerals}, Dmg: {total_damage}, Workers: {total_workers})"
                    incomplete_matches += 1
                else:
                    status = "✅ COMPLETE"

            # Only print incomplete or first few
            if "✅" not in status or m.id <= 5:
                print(f"{m.id:<10} | {str(m.played_at):<20} | {status}")

        print("-" * 50)
        print(f"Total Matches: {total_matches}")
        print(f"Incomplete Matches: {incomplete_matches}")

    finally:
        db.close()


if __name__ == "__main__":
    diagnose()
