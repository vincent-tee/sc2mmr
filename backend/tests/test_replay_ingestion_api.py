from dataclasses import replace
from io import BytesIO
from threading import Event
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import replays
from app.advanced_parser import AdvancedReplayData, PlayerMetrics
from app.database import get_db
from app.main import app
from app.models import Match, MatchPlayer, Player, PlayerMatchMetrics, FailedUpload, UploadErrorType
from app.rating_system import RatingSystem
from app.services.match_orchestrator import MatchOrchestrator
from app.types.results import ProcessedMatchResult, PlayerMatchResult
from .test_ingestion import replay, player_state


@pytest.fixture
def client(db_engine, replay, monkeypatch):
    with Session(db_engine) as db:
        db.add_all(Player(name=p.name, total_games=11) for p in replay.players)
        db.commit()
    def get_test_db():
        with Session(db_engine) as db:
            yield db
    app.dependency_overrides[get_db] = get_test_db
    monkeypatch.setattr(replays, "parse_replay", lambda path: replay)
    monkeypatch.setattr(replays, "parse_replay_advanced", lambda path, **kwargs: advanced(replay))
    monkeypatch.setattr(replays, "_save_replay_file", lambda *args: "/stored/replay.SC2Replay")
    monkeypatch.setattr(replays, "post_process_match", lambda *args, **kwargs: None)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


def advanced(replay):
    return AdvancedReplayData(
        basic_data=replay, game_duration_seconds=replay.duration_seconds,
        player_metrics=[PlayerMetrics(player_name=p.name, race=p.race, team=p.team,
                                      won=p.won, overall_impact=50 + i * 10)
                        for i, p in enumerate(replay.players)],
    )


def upload(client, route="/replays/upload"):
    return client.post(route, files={"file": ("test.SC2Replay", BytesIO(b"test"))})


@pytest.mark.parametrize("route", ["/replays/upload", "/replays/upload-advanced"])
def test_upload_retry_is_idempotent(client, db_engine, route):
    first = upload(client, route)
    assert first.status_code == 200, first.text
    assert first.json()["created"] is True
    with Session(db_engine) as db:
        before = player_state(db)
    second = upload(client, route)
    assert second.status_code == 200, second.text
    assert second.json()["created"] is False
    assert second.json()["match_id"] == first.json()["match_id"]
    with Session(db_engine) as db:
        assert player_state(db) == before
        assert db.query(MatchPlayer).count() == 4
        if route.endswith("advanced"):
            assert db.query(PlayerMatchMetrics).count() == 4
        for mp in db.query(MatchPlayer):
            assert mp.player.mmr == pytest.approx(RatingSystem.calculate_display_mmr(mp.player.mu, mp.player.sigma))
            assert mp.mmr_after == pytest.approx(RatingSystem.calculate_display_mmr(mp.mu_after, mp.sigma_after))


@pytest.mark.parametrize("route", ["/replays/upload", "/replays/upload-advanced"])
def test_upload_failure_can_be_retried(client, db_engine, monkeypatch, route):
    original = RatingSystem.update_ratings_from_match
    def fail(work, data, match):
        original(work, data, match)
        raise RuntimeError("injected failure")
    monkeypatch.setattr(RatingSystem, "update_ratings_from_match", fail)
    assert upload(client, route).status_code == 500
    with Session(db_engine) as db:
        assert db.query(Match).count() == 0
        assert all(p.total_games == 11 for p in db.query(Player))
        assert db.query(FailedUpload).count() == 1
    monkeypatch.setattr(RatingSystem, "update_ratings_from_match", original)
    assert upload(client, route).status_code == 200


@pytest.mark.parametrize("action", ["retry", "set-winner"])
def test_failed_upload_recovery_uses_atomic_ingestion(client, db_engine, monkeypatch, action):
    with Session(db_engine) as db:
        failed = FailedUpload(filename="failed.SC2Replay", replay_file_path="/stored/failed",
                              error_type=UploadErrorType.WINNER_DETERMINATION,
                              error_message="unknown winner")
        db.add(failed)
        db.commit()
        upload_id = failed.id
    monkeypatch.setattr(replays.replay_storage, "materialize_local_copy", lambda path: path)
    response = client.post(f"/replays/failed-uploads/{upload_id}/{action}", json={"winner_team": 1})
    assert response.status_code == 200, response.text
    with Session(db_engine) as db:
        assert db.get(FailedUpload, upload_id) is None
        assert db.query(Match).count() == 1
        assert all(p.total_games == 12 for p in db.query(Player))


def test_failed_upload_retry_that_still_fails_leaves_record_intact(client, db_engine, monkeypatch):
    with Session(db_engine) as db:
        failed = FailedUpload(filename="failed.SC2Replay", replay_file_path="/stored/failed",
                              error_type=UploadErrorType.WINNER_DETERMINATION,
                              error_message="unknown winner")
        db.add(failed)
        db.commit()
        upload_id = failed.id
    monkeypatch.setattr(replays.replay_storage, "materialize_local_copy", lambda path: path)

    def still_broken(path):
        raise RuntimeError("still cannot parse this replay")

    monkeypatch.setattr(replays, "parse_replay", still_broken)
    response = client.post(f"/replays/failed-uploads/{upload_id}/retry")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "still_failing"
    with Session(db_engine) as db:
        assert db.get(FailedUpload, upload_id) is not None
        assert db.query(Match).count() == 0


def test_health_remains_responsive_during_parsing(client, monkeypatch, replay):
    entered, release = Event(), Event()
    def slow_parse(path):
        entered.set()
        assert release.wait(5)
        return replay
    monkeypatch.setattr(replays, "parse_replay", slow_parse)
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = executor.submit(upload, client)
        try:
            assert entered.wait(2)
            health = executor.submit(client.get, "/health")
            assert health.result(timeout=2).status_code == 200
        finally:
            release.set()
        assert pending.result(timeout=5).status_code == 200


def test_batch_then_http_upload_does_not_rate_twice(client, db_engine, replay, monkeypatch):
    parsed = ProcessedMatchResult(
        played_at=replay.played_at, game_mode=replay.game_mode, map_name=replay.map_name,
        duration_seconds=replay.duration_seconds, replay_hash=replay.replay_hash,
        game_fingerprint=replay.game_fingerprint,
        players=[PlayerMatchResult(name=p.name, race=p.race, team=p.team, won=p.won)
                 for p in replay.players],
    )
    monkeypatch.setattr(MatchOrchestrator, "_trigger_post_processing", lambda *args: None)
    with Session(db_engine) as db:
        orchestrator = MatchOrchestrator(db)
        monkeypatch.setattr(orchestrator.parser, "parse", lambda *args, **kwargs: parsed)
        result = orchestrator.orchestrate_match("/batch/replay", "batch.SC2Replay")
        assert result.created
        before = player_state(db)
    response = upload(client)
    assert response.status_code == 200, response.text
    assert response.json()["created"] is False
    with Session(db_engine) as db:
        assert player_state(db) == before
