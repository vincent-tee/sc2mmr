from dataclasses import asdict
from datetime import datetime

from app.advanced_parser import PlayerMetrics
from app.models import DerivedDataState, GameMode, MatchPlayer, PlayerMatchMetrics, Race
from app.replay_parser import PlayerData, ReplayData
from app.services.ingestion import ingest_match
from app.services.metrics_reparse import apply_reparsed_rows


def stored_match(db):
    replay = ReplayData(
        played_at=datetime(2026, 8, 1), game_mode=GameMode.ONE_V_ONE, map_name="Map",
        duration_seconds=600, replay_hash="the-file", game_fingerprint="the-file",
        players=[PlayerData(name="Ann", race=Race.TERRAN, team=1, won=True),
                 PlayerData(name="Bob", race=Race.ZERG, team=2, won=False)],
    )
    match, _ = ingest_match(db, replay, require_experience=False)
    return match


def row(supply_block=30):
    players = [PlayerMetrics(player_name=name, race="Terran", team=team, won=team == 1,
                             supply_block_seconds=supply_block, workers_killed=4, stats_cutoff_second=590,
                             stats_cutoff_reason="recording_end")
               for name, team in (("Ann", 1), ("Bob", 2))]
    return {"replay_hash": "the-file", "num_players": 2, "players": [asdict(p) for p in players], "kill_events": []}


def ann_metrics(db):
    mp = db.query(MatchPlayer).join(MatchPlayer.player).filter_by(name="Ann").one()
    return db.query(PlayerMatchMetrics).filter_by(match_player_id=mp.id).one_or_none()


def test_dry_run_reports_without_writing(db_session):
    stored_match(db_session)
    report = apply_reparsed_rows(db_session, [row(), {**row(), "replay_hash": "unknown"}], dry_run=True)
    assert (report.matches, report.unmatched_replays, report.players_updated) == (1, 1, 2)
    assert ann_metrics(db_session) is None


def test_apply_saves_like_an_upload_and_schedules_a_rebuild(db_session):
    stored_match(db_session)
    apply_reparsed_rows(db_session, [row(supply_block=40)], dry_run=False)
    saved = ann_metrics(db_session)
    assert (saved.supply_block_seconds, saved.workers_killed) == (40, 4)
    assert (saved.stats_cutoff_second, saved.stats_cutoff_reason) == (590, "recording_end")
    assert db_session.get(DerivedDataState, 1).stale_since is not None

    report = apply_reparsed_rows(db_session, [row(supply_block=12)], dry_run=True)
    assert report.summary()["fields"]["supply_block_seconds"] == {
        "changed": 2, "median_change": -28.0, "mean_change": -28.0, "largest_drop": -28.0, "largest_rise": -28.0,
    }
