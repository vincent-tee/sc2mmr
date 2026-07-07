#!/usr/bin/env python3
"""
Backtest: composite balance objective vs pure MMR-difference.

For every historical even-teams match, reconstruct pre-match ratings from the
MatchPlayer snapshots (mu_before/sigma_before/mmr_before) and score the split
that was actually played with both objectives. Then, for each objective, take
the quartile of matches it rates as best-balanced and check how balanced those
games actually were (favorite win rate near 50% = genuinely balanced).

Caveats:
- Player component scores (combat/economic/...) are present-day aggregates,
  not historical snapshots — mild hindsight leakage on the component term.
- Synergy is excluded (no historical snapshot).

Run: python scripts/backtest_composite_objective.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.balancer import PlayerInfo, TeamBalancer, DEFAULT_COMPOSITE_WEIGHTS
from app.models import Match, MatchPlayer, Player


def build_player_info(mp: MatchPlayer, player: Player) -> PlayerInfo:
    """PlayerInfo with pre-match rating snapshot, present-day components."""
    return PlayerInfo(
        id=player.id,
        name=player.name,
        mu=mp.mu_before,
        sigma=mp.sigma_before,
        mmr=mp.mmr_before if mp.mmr_before is not None else player.mmr,
        overall_impact=player.avg_overall_impact or 50.0,
        total_games=player.total_games,
        aggression_score=player.avg_aggression_score or 50.0,
        avg_first_damage_timing=player.avg_first_damage_timing or 300,
        avg_combat_score=player.avg_combat_score or 25,
        economic_score=player.avg_economic_score or 60.0,
        efficiency_score=player.avg_efficiency_score or 55.0,
    )


def main() -> None:
    engine = create_engine("sqlite:///./data/sc2mmr.db")
    db = sessionmaker(bind=engine)()

    matches = db.query(Match).order_by(Match.played_at).all()
    players = {p.id: p for p in db.query(Player).all()}

    rows = []
    for match in matches:
        mps = db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        team1 = [mp for mp in mps if mp.team_number == 1]
        team2 = [mp for mp in mps if mp.team_number == 2]
        # Even teams only — the balancer's target scenario
        if not team1 or len(team1) != len(team2):
            continue

        t1 = [build_player_info(mp, players[mp.player_id]) for mp in team1]
        t2 = [build_player_info(mp, players[mp.player_id]) for mp in team2]

        win_prob = TeamBalancer.calculate_win_probability(t1, t2)
        quality = TeamBalancer.calculate_match_quality(t1, t2)
        spread = TeamBalancer.calculate_skill_spread_diff(t1, t2)
        comp_imb = TeamBalancer.calculate_component_imbalance(t1, t2)
        composite = TeamBalancer.compute_composite_score(
            win_probability=win_prob,
            match_quality=quality,
            skill_spread_diff=spread,
            component_imbalance=comp_imb,
            synergy_imbalance=0.0,
            weights=DEFAULT_COMPOSITE_WEIGHTS,
        )
        mmr_diff = abs(sum(p.mmr for p in t1) - sum(p.mmr for p in t2))
        team1_won = 1 if any(mp.won for mp in team1) else 0

        rows.append(
            {
                "match_id": match.id,
                "mode": match.game_mode.value,
                "win_prob": win_prob,
                "composite": composite,
                "mmr_diff": mmr_diff,
                "team1_won": team1_won,
            }
        )

    print(f"Scored {len(rows)} even-team matches\n")

    # Overall calibration of the TrueSkill win prob (shared by both objectives)
    brier = sum((r["win_prob"] - r["team1_won"]) ** 2 for r in rows) / len(rows)
    acc = sum(1 for r in rows if (r["win_prob"] > 0.5) == bool(r["team1_won"])) / len(
        rows
    )
    print(f"TrueSkill (snapshot) predictor: accuracy={acc:.3f} brier={brier:.4f}")
    print("(Brier 0.25 = coin flip; lower = better calibrated)\n")

    def favorite_win_rate(subset) -> float:
        """Win rate of the pre-match favorite. 0.5 = perfectly balanced games."""
        fav_wins = sum(
            1
            for r in subset
            if (r["team1_won"] == 1) == (r["win_prob"] > 0.5)
        )
        return fav_wins / len(subset)

    k = len(rows) // 4
    by_composite = sorted(rows, key=lambda r: r["composite"], reverse=True)[:k]
    by_mmr_diff = sorted(rows, key=lambda r: r["mmr_diff"])[:k]

    print(f"Top-quartile 'best balanced' matches per objective (n={k}):")
    print(
        f"  composite objective : favorite win rate = "
        f"{favorite_win_rate(by_composite):.3f} "
        f"(avg |win_prob-0.5| = {sum(abs(r['win_prob']-0.5) for r in by_composite)/k:.3f})"
    )
    print(
        f"  mmr-diff objective  : favorite win rate = "
        f"{favorite_win_rate(by_mmr_diff):.3f} "
        f"(avg |win_prob-0.5| = {sum(abs(r['win_prob']-0.5) for r in by_mmr_diff)/k:.3f})"
    )
    print("\ncloser to 0.500 = that objective's 'balanced' picks were truly balanced")

    overlap = len(
        {r["match_id"] for r in by_composite} & {r["match_id"] for r in by_mmr_diff}
    )
    print(f"overlap between the two quartiles: {overlap}/{k}")


if __name__ == "__main__":
    main()
