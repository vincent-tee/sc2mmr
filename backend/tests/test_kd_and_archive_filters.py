"""
Tests for the K/D ratio computation and the archive (matches-with-players)
search / game_mode filters, plus the match-details win-probability fallback.
"""
import importlib.util
import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import Match, MatchPlayer, Player, Race, GameMode
from app.advanced_parser import compute_kill_death_ratio, KD_RATIO_CAP


# ---------------------------------------------------------------------------
# K/D formula
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "killed,lost,expected",
    [
        (0, 0, 1.0),  # no combat -> neutral
        (0, 4, 0.0),  # died without killing
        (1, 4, 0.25),
        (3, 2, 1.5),
        (20, 0, KD_RATIO_CAP),  # flawless -> capped
        (50, 1, KD_RATIO_CAP),  # huge ratio -> same cap, no discontinuity
        (10, 1, KD_RATIO_CAP),  # exactly at cap
        (9, 1, 9.0),  # just under cap passes through
    ],
)
def test_compute_kill_death_ratio(killed, lost, expected):
    assert compute_kill_death_ratio(killed, lost) == expected


def test_backfill_script_uses_the_parser_formula():
    """The backfill script must share the parser's function, not a copy."""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "backfill_kd_ratio.py"
    )
    spec = importlib.util.spec_from_file_location("backfill_kd_ratio", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.compute_kill_death_ratio is compute_kill_death_ratio


# ---------------------------------------------------------------------------
# Archive filters + match details (endpoint tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def api_engine():
    db_file = "test_archive_filters.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    if os.path.exists(db_file):
        os.remove(db_file)


@pytest.fixture
def api_session(api_engine):
    SessionLocal = sessionmaker(bind=api_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(api_session):
    def override_get_db():
        yield api_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_match(session, *, game_mode, map_name, players, days_ago=0, probs=None):
    """Create a match with (player, team, won) tuples. probs=(t1, t2) or None."""
    match = Match(
        played_at=datetime.utcnow() - timedelta(days=days_ago),
        game_mode=game_mode,
        map_name=map_name,
        duration_seconds=600,
        predicted_team1_win_prob=probs[0] if probs else None,
        predicted_team2_win_prob=probs[1] if probs else None,
    )
    session.add(match)
    session.flush()
    for player, team, won in players:
        session.add(
            MatchPlayer(
                match_id=match.id,
                player_id=player.id,
                team_number=team,
                race=Race.TERRAN,
                won=1 if won else 0,
                mu_before=25.0 if won else 20.0,
                mu_after=26.0 if won else 19.0,
                sigma_before=6.0,
                sigma_after=5.9,
                # Stored display MMR (what /players/{id}/history charts)
                mmr_before=3500.0 if won else 3000.0,
                mmr_after=3600.0 if won else 2900.0,
            )
        )
    session.commit()
    return match


@pytest.fixture
def seeded(api_session):
    alice = Player(name="Alice", mu=25.0, sigma=8.333)
    bob = Player(name="Bob", mu=25.0, sigma=8.333)
    carol = Player(name="Carol", mu=25.0, sigma=8.333)
    api_session.add_all([alice, bob, carol])
    api_session.flush()

    m1 = _make_match(
        api_session,
        game_mode=GameMode.THREE_V_THREE,
        map_name="Frost LE",
        players=[(alice, 1, True), (bob, 2, False)],
        days_ago=2,
        probs=(0.6, 0.4),
    )
    m2 = _make_match(
        api_session,
        game_mode=GameMode.FOUR_V_FOUR,
        map_name="Deadwing",
        players=[(bob, 1, True), (carol, 2, False)],
        days_ago=1,
    )
    m3 = _make_match(
        api_session,
        game_mode=GameMode.THREE_V_THREE,
        map_name="Golden Wall",
        players=[(carol, 1, True), (alice, 2, False)],
        days_ago=0,
        probs=(0.5, 0.5),
    )
    return {"matches": [m1, m2, m3], "players": [alice, bob, carol]}


def test_no_filters_returns_everything(client, seeded):
    resp = client.get("/replays/matches-with-players")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 3
    assert body["grand_total"] == 3
    assert len(body["matches"]) == 3


def test_game_mode_filter(client, seeded):
    resp = client.get("/replays/matches-with-players", params={"game_mode": "4v4"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 1
    assert body["grand_total"] == 3  # unfiltered archive size still reported
    assert body["matches"][0]["map_name"] == "Deadwing"


def test_unknown_game_mode_is_422(client, seeded):
    resp = client.get("/replays/matches-with-players", params={"game_mode": "6v6"})
    assert resp.status_code == 422
    assert "Unknown game_mode" in resp.json()["detail"]


def test_search_by_player_name(client, seeded):
    resp = client.get("/replays/matches-with-players", params={"search": "carol"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 2
    maps = {m["map_name"] for m in body["matches"]}
    assert maps == {"Deadwing", "Golden Wall"}


def test_search_by_map_name(client, seeded):
    resp = client.get("/replays/matches-with-players", params={"search": "frost"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 1
    assert body["matches"][0]["map_name"] == "Frost LE"


def test_search_escapes_like_metacharacters(client, seeded):
    # "_" is a single-char LIKE wildcard; unescaped it would match every
    # non-empty name. No seeded name contains a literal underscore.
    resp = client.get("/replays/matches-with-players", params={"search": "_"})
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 0

    resp = client.get("/replays/matches-with-players", params={"search": "%"})
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 0


def test_search_and_mode_combined(client, seeded):
    resp = client.get(
        "/replays/matches-with-players",
        params={"search": "alice", "game_mode": "3v3"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 2  # Alice played both 3v3 matches


def test_match_details_persisted_win_prob_passthrough(client, seeded):
    match = seeded["matches"][0]  # has probs (0.6, 0.4)
    resp = client.get(f"/replays/matches/{match.id}")
    assert resp.status_code == 200
    body = resp.json()["match"]
    assert body["predicted_team1_win_prob"] == pytest.approx(0.6)
    assert body["predicted_team2_win_prob"] == pytest.approx(0.4)


def test_match_details_win_prob_fallback_when_null(client, seeded):
    match = seeded["matches"][1]  # created with probs=None
    resp = client.get(f"/replays/matches/{match.id}")
    assert resp.status_code == 200
    body = resp.json()["match"]
    t1, t2 = body["predicted_team1_win_prob"], body["predicted_team2_win_prob"]
    # Recomputed from mu/sigma_before: winner's team had the higher mu (25 vs 20)
    assert t1 is not None and t2 is not None
    assert t1 + t2 == pytest.approx(1.0, abs=1e-6)
    assert t1 > t2


# ---------------------------------------------------------------------------
# Player MMR history (trajectory chart data)
# ---------------------------------------------------------------------------


def test_player_history_chronological_with_display_mmr(client, seeded):
    alice = seeded["players"][0]  # played m1 (won, days_ago=2) and m3 (lost, days_ago=0)
    resp = client.get(f"/players/{alice.id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["player_id"] == alice.id
    assert len(body["history"]) == 2
    played = [e["played_at"] for e in body["history"]]
    assert played == sorted(played)  # chronological
    # The endpoint charts the STORED display MMR (mmr_after column):
    # Alice won m1 (3600) then lost m3 (2900).
    assert body["history"][0]["mmr"] == pytest.approx(3600.0)
    assert body["history"][1]["mmr"] == pytest.approx(2900.0)
    assert body["history"][1]["mmr_change"] == pytest.approx(-100.0)
    assert {"match_id", "map_name", "played_at", "mmr", "won"} <= set(
        body["history"][0]
    )


def test_player_history_unknown_player_404(client, seeded):
    resp = client.get("/players/999999/history")
    assert resp.status_code == 404
