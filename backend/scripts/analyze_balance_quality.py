#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Match, MatchPlayer, Player, GroupSynergy
from app.balancer import TeamBalancer, PlayerInfo
from itertools import combinations


def get_db():
    engine = create_engine("sqlite:///data/sc2mmr.db")
    Session = sessionmaker(bind=engine)
    return Session()


def calculate_team_synergy(p_list, synergy_map):
    syn = 0
    p_ids = [p.id for p in p_list]
    for pair in combinations(p_ids, 2):
        key = ",".join(map(str, sorted(pair)))
        syn += synergy_map.get(key, 0)
    if len(p_ids) >= 3:
        for trio in combinations(p_ids, 3):
            key = ",".join(map(str, sorted(trio)))
            syn += synergy_map.get(key, 0)
    return syn


def analyze_balance():
    db = get_db()
    matches = db.query(Match).filter(Match.played_at.isnot(None)).all()

    synergies = (
        db.query(GroupSynergy).filter(GroupSynergy.player_count.in_([2, 3])).all()
    )
    synergy_map = {s.player_ids_key: s.synergy_score for s in synergies}

    results = []

    for match in matches:
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )
        if len(match_players) < 2:
            continue

        team1_ids = [mp.player_id for mp in match_players if mp.team_number == 1]
        team2_ids = [mp.player_id for mp in match_players if mp.team_number == 2]
        if not team1_ids or not team2_ids:
            continue

        actual_winner = (
            1 if any(mp.won for mp in match_players if mp.team_number == 1) else 2
        )
        players = db.query(Player).filter(Player.id.in_(team1_ids + team2_ids)).all()
        player_map = {p.id: PlayerInfo.from_player(p) for p in players}

        t1_players = [player_map[pid] for pid in team1_ids if pid in player_map]
        t2_players = [player_map[pid] for pid in team2_ids if pid in player_map]
        if not t1_players or not t2_players:
            continue

        t1_unified = sum(p.unified_mmr for p in t1_players)
        t2_unified = sum(p.unified_mmr for p in t2_players)
        mmr_diff = abs(t1_unified - t2_unified)

        t1_syn = calculate_team_synergy(t1_players, synergy_map)
        t2_syn = calculate_team_synergy(t2_players, synergy_map)

        total_syn = t1_syn + t2_syn
        syn_imbalance = abs(t1_syn - t2_syn)
        balanced_syn_score = total_syn - syn_imbalance

        results.append(
            {
                "match_id": match.id,
                "mmr_diff": mmr_diff,
                "total_syn": total_syn,
                "syn_imbalance": syn_imbalance,
                "balanced_syn_score": balanced_syn_score,
                "actual_winner": actual_winner,
                "predicted_winner_mmr": 1 if t1_unified >= t2_unified else 2,
            }
        )

    results_sorted_total = sorted(results, key=lambda x: -x["total_syn"])
    results_sorted_balanced = sorted(results, key=lambda x: -x["balanced_syn_score"])

    top_total = results_sorted_total[: len(results) // 4]
    top_balanced = results_sorted_balanced[: len(results) // 4]

    total_acc = sum(
        1 for r in top_total if r["predicted_winner_mmr"] == r["actual_winner"]
    ) / len(top_total)
    balanced_acc = sum(
        1 for r in top_balanced if r["predicted_winner_mmr"] == r["actual_winner"]
    ) / len(top_balanced)

    print(f"Accuracy (Matches with highest Total Synergy): {total_acc:.1%}")
    print(f"Accuracy (Matches with highest Balanced Synergy): {balanced_acc:.1%}")

    db.close()


if __name__ == "__main__":
    analyze_balance()
