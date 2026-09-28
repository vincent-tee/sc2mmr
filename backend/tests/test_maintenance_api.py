from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models import GameMode, Match, MatchPlayer, Race
from app.replay_parser import ReplayData, PlayerData
from app.services.ingestion import ingest_match


@pytest.fixture
def client(db_engine):
    def get_test_db():
        with Session(db_engine) as db:
            yield db

    app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def seed_game_recorded_twice_and_an_aborted_lobby(db_engine):
    replay = ReplayData(
        played_at=datetime(2026, 8, 1, 12, 10), game_mode=GameMode.TWO_V_TWO, map_name="Test map",
        duration_seconds=600, replay_hash="recorder", game_fingerprint="recorder",
        players=[PlayerData(name=f"P{i}", race=Race.TERRAN, team=1 if i < 2 else 2, won=i < 2)
                 for i in range(4)],
    )
    with Session(db_engine) as db:
        original, _ = ingest_match(db, replay, require_experience=False)
        copy = Match(played_at=replay.played_at + timedelta(seconds=6), game_mode=replay.game_mode,
                     map_name=replay.map_name, duration_seconds=420, replay_hash="teammate")
        aborted = Match(played_at=replay.played_at + timedelta(hours=1), game_mode=replay.game_mode,
                        map_name=replay.map_name, duration_seconds=3, replay_hash="lobby")
        db.add_all([copy, aborted])
        db.flush()
        for mp in db.query(MatchPlayer).filter(MatchPlayer.match_id == original.id).all():
            db.add(MatchPlayer(match_id=copy.id, player_id=mp.player_id, team_number=mp.team_number,
                               race=mp.race, won=mp.won, mu_before=25, sigma_before=8,
                               mu_after=25, sigma_after=8))
        db.commit()
        return original.id, copy.id, aborted.id


def test_duplicate_cleanup_previews_then_applies_only_the_previewed_games(client, db_engine):
    original_id, copy_id, aborted_id = seed_game_recorded_twice_and_an_aborted_lobby(db_engine)

    preview = client.post("/maintenance/duplicate-games", json={}).json()
    assert preview["applied"] is False
    assert preview["removed_match_ids"] == sorted([copy_id, aborted_id])
    assert [c["kept_match_id"] for c in preview["duplicate_copies"]] == [original_id]

    mismatched = client.post("/maintenance/duplicate-games",
                             json={"apply": True, "expected_removed_match_ids": [copy_id]})
    assert mismatched.status_code == 409

    applied = client.post("/maintenance/duplicate-games",
                          json={"apply": True, "expected_removed_match_ids": preview["removed_match_ids"]})
    assert applied.status_code == 200
    with Session(db_engine) as db:
        assert [m.id for m in db.query(Match)] == [original_id]

    status = client.get("/maintenance/derived-data").json()
    assert status["stale"] is True
    assert "Removed 2" in status["stale_reason"]


def test_forced_rebuild_clears_the_stale_flag(client, db_engine):
    seed_game_recorded_twice_and_an_aborted_lobby(db_engine)
    preview = client.post("/maintenance/duplicate-games", json={}).json()
    client.post("/maintenance/duplicate-games",
                json={"apply": True, "expected_removed_match_ids": preview["removed_match_ids"]})

    rebuilt = client.post("/maintenance/derived-data/rebuild")

    assert rebuilt.status_code == 200
    assert rebuilt.json()["stale"] is False
    assert rebuilt.json()["last_rebuilt_at"] is not None
