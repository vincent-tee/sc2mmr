"""
Delete matches where at least one team lacks an experienced player (>10 games).

Rule: Each team must have at least one player with >10 total games.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.models import Match, MatchPlayer, Player

def main():
    db = SessionLocal()
    try:
        print("=== DELETING MATCHES WITH INEXPERIENCED TEAMS ===")
        print()
        print("Rule: Each team must have ≥1 player with >10 games")
        print()

        matches_to_delete = []

        matches = db.query(Match).all()
        print(f"Scanning {len(matches)} total matches...")

        for match in matches:
            match_players = db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()

            team1_has_experienced = False
            team2_has_experienced = False

            for mp in match_players:
                player = db.query(Player).filter(Player.id == mp.player_id).first()
                if player:
                    if mp.team_number == 1 and player.total_games > 10:
                        team1_has_experienced = True
                    elif mp.team_number == 2 and player.total_games > 10:
                        team2_has_experienced = True

            # Delete if EITHER team lacks experienced player
            if not team1_has_experienced or not team2_has_experienced:
                matches_to_delete.append(match.id)

        print(f"Found {len(matches_to_delete)} matches to delete")
        print()
        print(f"Match IDs: {matches_to_delete}")
        print()

        if matches_to_delete:
            # Delete matches (CASCADE will delete related MatchPlayer, PlayerMatchMetrics, etc.)
            for match_id in matches_to_delete:
                match = db.query(Match).filter(Match.id == match_id).first()
                if match:
                    db.delete(match)

            db.commit()
            print(f"✅ Successfully deleted {len(matches_to_delete)} matches")
        else:
            print("No matches to delete")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
