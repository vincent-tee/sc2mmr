import sys
sys.path.insert(0, '/home/vtee/projects/sc2mmr/backend')
from app.database import SessionLocal
from app.models import Player
from sqlalchemy import desc, func

db = SessionLocal()
players = (
    db.query(Player)
    .filter(Player.is_ai == 0, Player.total_games > 0)
    .order_by(desc(func.coalesce(Player.unified_mmr, Player.mmr)))
    .limit(30)
    .all()
)
lines = []
lines.append("Rank | Name | MMR (unified) | Raw MMR | Games | W-L | Win%")
lines.append("-" * 70)
for i, p in enumerate(players):
    display = p.unified_mmr or p.mmr
    wr = f'{p.win_rate*100:.1f}%'
    wl = f'{p.wins}W-{p.losses}L'
    lines.append(f"{i+1} | {p.name} | {round(display)} | {round(p.mmr)} | {p.total_games} | {wl} | {wr}")

with open('/home/vtee/projects/sc2mmr/leaderboard_out.txt', 'w') as f:
    f.write('\n'.join(lines))
print('Done. Wrote', len(players), 'players.')
db.close()
