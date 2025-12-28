"""
Verification script for database cascade deletes.
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_context
from app.models import (
    Match,
    Player,
    MatchPlayer,
    PlayerMatchMetrics,
    PerformanceFeatures,
    GameMode,
    Race,
)


def verify_cascades():
    print("Verifying cascade deletes...")

    with get_db_context() as db:
        # 1. Create test data
        import uuid

        player_name = f"TestPlayer_{uuid.uuid4().hex[:8]}"
        player = Player(name=player_name, mu=25.0, sigma=8.333)
        db.add(player)
        db.commit()
        db.refresh(player)

        match = Match(
            played_at=datetime.utcnow(),
            game_mode=GameMode.TWO_V_TWO,
            map_name="Test Map",
            duration_seconds=1200,
        )
        db.add(match)
        db.commit()
        db.refresh(match)

        match_player = MatchPlayer(
            match_id=match.id,
            player_id=player.id,
            team_number=1,
            race=Race.TERRAN,
            won=1,
            mu_before=25.0,
            sigma_before=8.333,
            mu_after=26.0,
            sigma_after=8.2,
        )
        db.add(match_player)
        db.commit()
        db.refresh(match_player)

        metrics = PlayerMatchMetrics(
            match_player_id=match_player.id, minerals_collected=1000
        )
        db.add(metrics)

        features = PerformanceFeatures(match_player_id=match_player.id, pim=0.1)
        db.add(features)
        db.commit()

        match_id = match.id
        mp_id = match_player.id

        print(f"Created Match {match_id} with MatchPlayer {mp_id}")

        # 2. Delete the match
        print(f"Deleting Match {match_id}...")
        db.delete(match)
        db.commit()

        # 3. Verify deletions
        mp = db.query(MatchPlayer).filter(MatchPlayer.id == mp_id).first()
        met = (
            db.query(PlayerMatchMetrics)
            .filter(PlayerMatchMetrics.match_player_id == mp_id)
            .first()
        )
        feat = (
            db.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp_id)
            .first()
        )

        success = True
        if mp:
            print("ERROR: MatchPlayer was NOT deleted!")
            success = False
        else:
            print("SUCCESS: MatchPlayer was deleted.")

        if met:
            print("ERROR: PlayerMatchMetrics was NOT deleted!")
            success = False
        else:
            print("SUCCESS: PlayerMatchMetrics was deleted.")

        if feat:
            print("ERROR: PerformanceFeatures was NOT deleted!")
            success = False
        else:
            print("SUCCESS: PerformanceFeatures was deleted.")

        if success:
            print("\nALL CASCADE DELETES VERIFIED SUCCESSFULLY!")
        else:
            print("\nCASCADE DELETE VERIFICATION FAILED!")
            sys.exit(1)


if __name__ == "__main__":
    verify_cascades()
