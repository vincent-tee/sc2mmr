import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from backend.app.database import SessionLocal
from backend.app.models import MatchPlayer, Player, Match
from sqlalchemy.orm import joinedload

db = SessionLocal()
player = db.query(Player).filter(Player.name.ilike('%dragon%')).first()
print(f'Player: {player.name} (ID: {player.id}), total games: {player.total_games}')

mps = (
    db.query(MatchPlayer)
    .options(joinedload(MatchPlayer.match))
    .join(Match)
    .filter(MatchPlayer.player_id == player.id)
    .order_by(Match.played_at.desc())
    .limit(5)
    .all()
)
print('\nMost recent 5 matches via API logic:')
for mp in mps:
    print(f'  Match {mp.match.id} on {mp.match.played_at} | mmr_before: {mp.mmr_before}, mmr_after: {mp.mmr_after}')
db.close()
