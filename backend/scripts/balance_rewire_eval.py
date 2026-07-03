"""Phase 5 before/after metric — what the balancer CHOOSES for recent rosters.

For the N most recent historical match rosters (>=4 players, even teams
possible), run TeamBalancer.generate_team_suggestions on the roster's players
and report, for the TOP suggestion: |win_probability - 0.5| (TrueSkill
calibration of the chosen split) and the display-MMR difference of the chosen
split. Read-only. Run BEFORE and AFTER the Phase 5 rewire and diff the means.

Usage: cd backend && python3 scripts/balance_rewire_eval.py [N]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models import Match, MatchPlayer, Player  # noqa: E402
from app.balancer import TeamBalancer, PlayerInfo  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20


def main():
    db = SessionLocal()
    matches = (
        db.query(Match).order_by(Match.played_at.desc()).limit(200).all()
    )
    done = 0
    tot_calib = tot_diff = 0.0
    print(f"{'match':>6} {'players':>7} {'|winprob-0.5|':>13} {'display-MMR diff':>16}")
    for m in matches:
        if done >= N:
            break
        mps = db.query(MatchPlayer).filter(MatchPlayer.match_id == m.id).all()
        pids = list({mp.player_id for mp in mps})
        if len(pids) < 4 or len(pids) % 2 != 0:
            continue
        players = db.query(Player).filter(Player.id.in_(pids)).all()
        if len(players) != len(pids) or any(p.mu is None for p in players):
            continue
        infos = [PlayerInfo.from_player(p) for p in players]
        try:
            top = TeamBalancer.generate_team_suggestions(infos, top_n=1)[0]
        except Exception:
            continue
        calib = abs(top.win_probability - 0.5)
        d_mmr = abs(sum(p.mmr for p in top.team_1) - sum(p.mmr for p in top.team_2))
        tot_calib += calib
        tot_diff += d_mmr
        done += 1
        print(f"{m.id:>6} {len(pids):>7} {calib:>13.4f} {d_mmr:>16.1f}")
    if done:
        print(f"\nmean over {done} rosters: |winprob-0.5| = {tot_calib/done:.4f}, display-MMR diff = {tot_diff/done:.1f}")
    db.close()


if __name__ == "__main__":
    main()
