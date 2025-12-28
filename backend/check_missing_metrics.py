from app.database import SessionLocal
from app.models import Match, MatchPlayer, PlayerMatchMetrics
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

db = SessionLocal()
try:
    matches = db.query(Match).all()
    missing = 0
    for m in matches:
        has_metrics = (
            db.query(PlayerMatchMetrics)
            .join(MatchPlayer)
            .filter(MatchPlayer.match_id == m.id)
            .first()
            is not None
        )
        if not has_metrics:
            missing += 1
    print(f"Total matches in DB: {len(matches)}")
    print(f"Matches missing metrics: {missing}")
finally:
    db.close()
