import sys
import os
from pathlib import Path
import numpy as np

# Add backend to path
backend_path = Path("/home/vtee/projects/sc2mmr/backend")
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.services.ml_predictor import get_ml_predictor, FeatureExtractor


def test_shap():
    db = SessionLocal()
    predictor = get_ml_predictor()

    # Get a match with participants
    from app.models import Match, MatchPlayer

    match = db.query(Match).join(MatchPlayer).first()
    if not match:
        print("No matches found")
        return

    team1_ids = [mp.player_id for mp in match.participants if mp.team_number == 1]
    team2_ids = [mp.player_id for mp in match.participants if mp.team_number == 2]

    print(f"Testing SHAP for match {match.id} (Teams: {team1_ids} vs {team2_ids})")
    print(f"Is Trained: {predictor.is_trained}")
    print(f"Has Model: {predictor.model is not None}")

    try:
        prediction = predictor.predict(db, team1_ids, team2_ids)
        print(f"Prediction: {prediction['team_1_win_probability']}%")
        print(f"SHAP Impacts: {prediction.get('shap_impacts', [])}")

        if not prediction.get("shap_impacts"):
            print("WARNING: SHAP impacts are EMPTY")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_shap()
