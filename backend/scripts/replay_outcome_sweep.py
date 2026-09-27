import json
import logging
import os
import sqlite3
import sys
import warnings
from multiprocessing import Pool
from pathlib import Path

import sc2reader

DB = "file:" + str(Path(__file__).resolve().parents[1] / "data/sc2mmr.db") + "?mode=ro"
PARALLEL_PARSERS = 10


def final_stats_by_player(replay):
    final = {}
    for event in replay.tracker_events:
        if event.name == "PlayerStatsEvent" and event.player:
            final[event.pid] = event
    return final


def team_totals(players, teams, final_stats):
    totals = {team: dict(food=0.0, bank=0.0, killed=0.0, lost=0.0, n=0) for team in teams}
    for player in players:
        team = totals[player.team_id]
        team["n"] += 1
        stats = final_stats.get(player.pid)
        if stats:
            team["food"] += stats.food_used
            team["bank"] += stats.minerals_current + stats.vespene_current
            team["killed"] += stats.resources_killed
            team["lost"] += stats.resources_lost
    return totals


def leave_order(replay, teams):
    return sorted((event.second, event.player.team_id) for event in replay.game_events
                  if event.name == "PlayerLeaveEvent" and getattr(event, "player", None)
                  and getattr(event.player, "team_id", None) in teams)


def replay_outcome(match_id_and_path):
    match_id, path = match_id_and_path
    try:
        replay = sc2reader.load_replay(path, load_level=4)
    except Exception as parse_error:
        return dict(mid=match_id, error=str(parse_error)[:80])
    players = [p for p in replay.players if getattr(p, "team_id", None)]
    teams = sorted({p.team_id for p in players})
    if len(teams) != 2:
        return dict(mid=match_id, error=f"{len(teams)} teams")
    recorded_winners = {p.team_id for p in players if (p.result or "").lower() == "win"}
    return dict(mid=match_id, teams=teams, result=list(recorded_winners),
                agg=team_totals(players, teams, final_stats_by_player(replay)),
                leaves=leave_order(replay, teams), length=replay.game_length.seconds)


def quiet_worker():
    warnings.filterwarnings("ignore")
    logging.disable(logging.CRITICAL)


def main(out_path):
    con = sqlite3.connect(DB, uri=True)
    replays_on_disk = [(match_id, path) for match_id, path in con.execute(
        "SELECT id, replay_file_path FROM matches WHERE replay_file_path IS NOT NULL")
        if os.path.exists(path)]
    con.close()
    with Pool(PARALLEL_PARSERS, initializer=quiet_worker) as pool:
        outcomes = pool.map(replay_outcome, replays_on_disk, chunksize=4)
    with open(out_path, "w") as out:
        json.dump(outcomes, out)
    print(len(outcomes), "replays analysed")


if __name__ == "__main__":
    main(sys.argv[1])
