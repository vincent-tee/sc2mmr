import random
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import (
    Base, DerivedDataState, GameMode, Match, MatchPlayer, Player, PlayerRivalry, Race,
)
from app.replay_parser import ReplayData, PlayerData
from app.services import derived_data
from app.services.derived_data import (
    REBUILD_DEBOUNCE, claim_rebuild, derived_data_state, mark_stale, rebuild_derived_data,
    rebuild_if_due,
)
from app.services.ingestion import ingest_match

PLAYERS = ["Ann", "Ben", "Cat", "Dan", "Eve", "Fay"]


def fresh_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Session(engine)


def history(games=18, seed=7):
    rng = random.Random(seed)
    start = datetime(2026, 8, 1, 12, 0)
    replays = []
    for i in range(games):
        team1 = set(rng.sample(PLAYERS, 3))
        team1_won = rng.random() < 0.5
        played_at = start + timedelta(days=(i // 6) * 7, minutes=(i % 6) * 25)
        replays.append(ReplayData(
            played_at=played_at, game_mode=GameMode.THREE_V_THREE, map_name=f"Map {i % 4}",
            duration_seconds=600, replay_hash=f"game-{i}", game_fingerprint=f"game-{i}",
            players=[PlayerData(name=name, race=Race.TERRAN, team=1 if name in team1 else 2,
                                won=(name in team1) == team1_won) for name in PLAYERS],
        ))
    return replays


def ingest_all(db, replays):
    for replay in replays:
        ingest_match(db, replay, require_experience=False)


def ratings(db):
    return {p.name: (round(p.mu, 9), round(p.sigma, 9), round(p.mmr, 6), p.total_games, p.wins, p.losses)
            for p in db.query(Player)}


def snapshots(db):
    return {(mp.match.replay_hash, mp.player.name): (round(mp.mu_before, 9), round(mp.sigma_before, 9),
                                                     round(mp.mu_after, 9), round(mp.sigma_after, 9))
            for mp in db.query(MatchPlayer)}


def win_probabilities(db):
    return {m.replay_hash: round(m.predicted_team1_win_prob, 9) for m in db.query(Match)}


def rivalries(db):
    names = dict(db.query(Player.id, Player.name).all())
    return sorted((names[r.player1_id], names[r.player2_id], r.player1_wins, r.games_against)
                  for r in db.query(PlayerRivalry))


def test_out_of_order_uploads_plus_rebuild_equal_in_order_uploads():
    replays = history()
    in_order, shuffled = fresh_session(), fresh_session()
    ingest_all(in_order, replays)
    out_of_order = replays[:]
    random.Random(3).shuffle(out_of_order)
    ingest_all(shuffled, out_of_order)
    assert ratings(shuffled) != ratings(in_order)

    rebuild_derived_data(shuffled)

    assert ratings(shuffled) == ratings(in_order)
    assert snapshots(shuffled) == snapshots(in_order)
    assert win_probabilities(shuffled) == win_probabilities(in_order)
    rebuild_derived_data(in_order)
    assert rivalries(shuffled) == rivalries(in_order)


def test_rebuilding_twice_changes_nothing():
    db = fresh_session()
    ingest_all(db, history())
    rebuild_derived_data(db)
    first = (ratings(db), snapshots(db), win_probabilities(db), rivalries(db))
    rebuild_derived_data(db)
    assert (ratings(db), snapshots(db), win_probabilities(db), rivalries(db)) == first


def test_only_an_out_of_order_upload_marks_data_stale():
    replays = history(6)
    db = fresh_session()
    ingest_all(db, replays[1:])
    assert derived_data_state(db).stale_since is None

    ingest_match(db, replays[0], require_experience=False)

    state = derived_data_state(db)
    assert state.stale_since is not None
    assert state.rebuild_due_at == pytest.approx(state.stale_since + REBUILD_DEBOUNCE, abs=timedelta(seconds=5))


def test_each_new_stale_mark_pushes_the_rebuild_back():
    db = fresh_session()
    first = datetime(2026, 9, 1, 12, 0)
    mark_stale(db, "first", now=first)
    mark_stale(db, "second", now=first + timedelta(minutes=1))
    state = derived_data_state(db)
    assert state.stale_since == first
    assert state.rebuild_due_at == first + timedelta(minutes=1) + REBUILD_DEBOUNCE
    assert state.stale_reason == "second"


def test_rebuild_waits_until_due_then_clears_the_stale_flag():
    db = fresh_session()
    ingest_all(db, history(4))
    marked_at = datetime.utcnow()
    mark_stale(db, "late upload", now=marked_at)
    db.commit()

    assert rebuild_if_due(db, now=marked_at + REBUILD_DEBOUNCE - timedelta(seconds=1)) is None
    assert derived_data_state(db).stale_since is not None

    assert rebuild_if_due(db, now=marked_at + REBUILD_DEBOUNCE) is not None
    state = derived_data_state(db)
    assert state.stale_since is None
    assert state.rebuild_due_at is None
    assert state.rebuilding_started_at is None
    assert state.last_rebuilt_at is not None


def test_a_running_rebuild_blocks_another_until_its_claim_expires():
    db = fresh_session()
    now = datetime(2026, 9, 1, 12, 0)
    assert claim_rebuild(db, now, only_when_due=False)
    assert not claim_rebuild(db, now + timedelta(minutes=5), only_when_due=False)
    assert claim_rebuild(db, now + derived_data.ABANDONED_REBUILD_AFTER + timedelta(seconds=1),
                         only_when_due=False)


def test_a_failed_rebuild_changes_nothing_and_stays_due(monkeypatch):
    db = fresh_session()
    shuffled = history(6)
    shuffled.reverse()
    ingest_all(db, shuffled)
    before = ratings(db)

    def fail_after_ratings(work):
        from app.services.rating_recalculation import recalculate_ratings_in_place
        recalculate_ratings_in_place(work)
        raise RuntimeError("boom")

    monkeypatch.setattr(derived_data, "rebuild_all", fail_after_ratings)
    with pytest.raises(RuntimeError):
        rebuild_derived_data(db)

    assert ratings(db) == before
    state = db.get(DerivedDataState, 1)
    assert state.stale_since is not None
    assert state.rebuilding_started_at is None
    assert "boom" in state.last_error
