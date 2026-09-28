from dataclasses import replace
from datetime import datetime

import pytest

from app.match_result import ResultSource
from app.models import DerivedDataState, GameMode, Match, MatchPlayer, Race
from app.replay_parser import PlayerData, ReplayData
from app.services import match_results
from app.services.ingestion import ingest_match
from app.services.match_results import (
    ResultChangeError, backfill_result_sources, confirm_result, review_queue, settle_unrecorded_results,
)


def replay(hash_, source=ResultSource.SUGGESTED, supply=(150.0, 40.0), team1_won=True, when=1):
    return ReplayData(
        played_at=datetime(2026, 8, when), game_mode=GameMode.ONE_V_ONE,
        map_name=f"Map {hash_}", duration_seconds=600, replay_hash=hash_, game_fingerprint=hash_,
        players=[PlayerData(name="Ann", race=Race.TERRAN, team=1, won=team1_won),
                 PlayerData(name="Bob", race=Race.ZERG, team=2, won=not team1_won)],
        result_source=source,
        result_evidence={"frame": 100, "team_supply": {"1": supply[0], "2": supply[1]}},
    )


def ingest(db, data, path=None):
    match, _ = ingest_match(db, data, path, require_experience=False)
    return match


def winners(db, match):
    return {mp.team_number for mp in db.query(MatchPlayer).filter_by(match_id=match.id) if mp.won}


def test_queue_lists_only_games_that_need_a_person(db_session):
    ingest(db_session, replay("clear-lead", supply=(150.0, 40.0), when=1))
    ingest(db_session, replay("known", source=ResultSource.REPLAY, when=2))
    closest = ingest(db_session, replay("closest", supply=(100.0, 101.0), when=3))
    less_close = ingest(db_session, replay("less-close", supply=(100.0, 120.0), when=4))
    contradicted = ingest(db_session, replay("contradicted", supply=(150.0, 40.0), when=5))
    contradicted.result_evidence = {**contradicted.result_evidence,
                                    "other_recordings": [{"replay_hash": "x", "winner_team": 2}]}
    db_session.commit()
    settle_unrecorded_results(db_session, dry_run=False)
    contradicted.result_source = ResultSource.SUGGESTED
    for mp in contradicted.participants:
        mp.won = int(mp.team_number == 1)
    db_session.commit()

    queue = review_queue(db_session)
    assert [item.match.id for item in queue] == [contradicted.id, less_close.id, closest.id]


def test_confirming_the_same_winner_does_not_schedule_a_rebuild(db_session):
    match = ingest(db_session, replay("same"))
    assert confirm_result(db_session, match, 1, "Vincent") is False
    assert match.result_source == ResultSource.CONFIRMED
    assert match.result_confirmed_by == "Vincent"
    assert db_session.get(DerivedDataState, 1) is None or db_session.get(DerivedDataState, 1).stale_since is None


def test_flipping_the_winner_rewrites_results_and_marks_ratings_stale(db_session):
    match = ingest(db_session, replay("flip"))
    assert confirm_result(db_session, match, 2, "Vincent") is True
    assert winners(db_session, match) == {2}
    state = db_session.get(DerivedDataState, 1)
    assert state.stale_since is not None
    assert "changed to team 2" in state.stale_reason


def test_confirm_requires_a_name_and_a_real_team(db_session):
    match = ingest(db_session, replay("bad"))
    with pytest.raises(ResultChangeError):
        confirm_result(db_session, match, 3, "Vincent")
    with pytest.raises(ResultChangeError):
        confirm_result(db_session, match, 2, "  ")
    assert winners(db_session, match) == {1}


def unchecked(db, data, path):
    match = ingest(db, data, path)
    match.result_source = None
    db.commit()
    return match


def test_backfill_applies_the_winner_rule(db_session, monkeypatch):
    from app.replay_parser import WinnerDeterminationError
    monkeypatch.setattr(match_results.replay_storage, "materialize_match_replay",
                        lambda stored, _hash: stored if stored and "missing" not in stored else None)
    parses = {
        "has-result": replay("has-result", source=ResultSource.REPLAY),
        "supply-lead": replay("supply-lead"),
        "recorded-other-way": replace(replay("recorded-other-way", source=ResultSource.REPLAY), players=[
            PlayerData(name="Ann", race=Race.TERRAN, team=1, won=False),
            PlayerData(name="Bob", race=Race.ZERG, team=2, won=True)]),
    }

    def parse(path):
        if path == "too-close":
            raise WinnerDeterminationError("no clear winner", team_stats={"frame": 9, "team_supply": {"1": 100, "2": 110}})
        return parses[path]

    matches = {name: unchecked(db_session, replay(name, when=i + 1), name)
               for i, name in enumerate([*parses, "too-close"])}
    missing = unchecked(db_session, replay("gone", when=9), "missing-file")

    dry = backfill_result_sources(db_session, limit=10, dry_run=True, parse=parse)
    assert (dry.replay, dry.suggested, dry.unknown, dry.winner_changes, dry.missing_file) == (2, 1, 1, 2, 1)
    assert all(winners(db_session, m) == {1} for m in matches.values())

    backfill_result_sources(db_session, limit=10, dry_run=False, parse=parse)
    assert matches["has-result"].result_source == ResultSource.REPLAY
    assert matches["supply-lead"].result_source == ResultSource.SUGGESTED
    assert (matches["recorded-other-way"].result_source, winners(db_session, matches["recorded-other-way"])) == (
        ResultSource.REPLAY, {2})
    assert (matches["too-close"].result_source, winners(db_session, matches["too-close"])) == (
        ResultSource.UNKNOWN, set())
    assert (missing.result_source, winners(db_session, missing)) == (None, {1})
    assert review_queue(db_session)[0].match.id == matches["too-close"].id
    assert db_session.get(DerivedDataState, 1).stale_since is not None


def test_settle_follows_supply_and_leaves_unclear_games_unknown(db_session):
    against_supply = ingest(db_session, replay("against", supply=(135.0, 578.0), when=1))
    too_close = ingest(db_session, replay("close", supply=(100.0, 110.0), when=2))
    clear = ingest(db_session, replay("clear", supply=(150.0, 40.0), when=3))

    dry = settle_unrecorded_results(db_session, dry_run=True)
    assert [c["match_id"] for c in dry.changed] == [against_supply.id, too_close.id]
    assert winners(db_session, against_supply) == {1}

    settle_unrecorded_results(db_session, dry_run=False)
    assert (against_supply.result_source, winners(db_session, against_supply)) == (ResultSource.SUGGESTED, {2})
    assert (too_close.result_source, winners(db_session, too_close)) == (ResultSource.UNKNOWN, set())
    assert winners(db_session, clear) == {1}
    assert settle_unrecorded_results(db_session, dry_run=True).changed == []


@pytest.fixture
def client(db_engine):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from app.database import get_db
    from app.main import app

    def get_test_db():
        with Session(db_engine) as db:
            yield db

    app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_review_and_confirm_over_http(client, db_session):
    match = ingest(db_session, replay("http", supply=(100.0, 110.0)))
    settle_unrecorded_results(db_session, dry_run=False)
    queue = client.get("/match-results/review").json()
    assert queue["total"] == 1
    item = queue["items"][0]
    assert (item["result_source"], item["winner_team"], item["supply_favourite_team"]) == (ResultSource.UNKNOWN, None, 2)
    assert item["rosters"] == [{"team": 1, "players": ["Ann"]}, {"team": 2, "players": ["Bob"]}]

    assert client.post(f"/match-results/{match.id}/confirm", json={"winner_team": 5, "confirmed_by": "V"}).status_code == 400
    flipped = client.post(f"/match-results/{match.id}/confirm", json={"winner_team": 2, "confirmed_by": "V"}).json()
    assert flipped["changed"] is True
    assert flipped["item"]["result_source"] == ResultSource.CONFIRMED
    assert client.get("/match-results/review").json()["total"] == 0



def test_replay_falls_back_to_its_hash_when_the_stored_path_is_elsewhere(monkeypatch, tmp_path):
    from app.services import replay_storage
    monkeypatch.setattr(replay_storage, "fetch_replay_by_hash", lambda h: b"replay-bytes" if h == "abc" else None)
    local = replay_storage.materialize_match_replay("/home/someone-else/replays/abc.SC2Replay", "abc")
    with open(local, "rb") as copy:
        assert copy.read() == b"replay-bytes"
    assert replay_storage.materialize_match_replay("/nowhere/x.SC2Replay", "unknown") is None


def test_backfill_rechecks_unknown_and_unrates_games_without_a_clear_winner(db_session, monkeypatch):
    from app.replay_parser import WinnerDeterminationError
    monkeypatch.setattr(match_results.replay_storage, "materialize_match_replay", lambda stored, _hash: stored)
    disputed = unchecked(db_session, replay("disputed"), "disputed")
    disputed.result_source = ResultSource.UNKNOWN
    db_session.commit()

    def parse(path):
        raise WinnerDeterminationError("no clear winner", team_stats={"frame": 9, "team_supply": {"1": 50.0, "2": 60.0}})

    assert backfill_result_sources(db_session, limit=10, dry_run=False, parse=parse).checked == 0
    report = backfill_result_sources(db_session, limit=10, dry_run=False, parse=parse, recheck_unknown=True)
    assert (report.checked, report.unknown) == (1, 1)
    assert disputed.result_source == ResultSource.UNKNOWN
    assert disputed.result_evidence == {"frame": 9, "team_supply": {"1": 50.0, "2": 60.0}}
    assert winners(db_session, disputed) == set()


def test_unknown_games_are_neither_wins_nor_losses(db_session):
    from app.api.players import _batch_recent_form, _calculate_recent_form

    won = ingest(db_session, replay("won", when=1))
    unchecked_result = ingest(db_session, replay("unchecked", when=2))
    unchecked_result.result_source = None
    unknown = ingest(db_session, replay("unknown", supply=(100.0, 110.0), when=3))
    settle_unrecorded_results(db_session, dry_run=False)
    assert unknown.result_source == ResultSource.UNKNOWN

    rated_ids = {m.id for m in db_session.query(Match).filter(Match.is_rated)}
    assert rated_ids == {won.id, unchecked_result.id}

    ann = next(mp.player_id for mp in won.participants if mp.team_number == 1)
    bob = next(mp.player_id for mp in won.participants if mp.team_number == 2)
    assert _calculate_recent_form(db_session, ann) == 1.0
    assert _batch_recent_form(db_session, [ann, bob]) == {ann: 1.0, bob: 0.0}


def test_not_rateable_games_are_unrated_and_leave_the_queue(db_session):
    from app.services.match_results import mark_not_rateable

    ffa = ingest(db_session, replay("ffa", supply=(100.0, 110.0), when=1))
    settle_unrecorded_results(db_session, dry_run=False)
    assert [item.match.id for item in review_queue(db_session)] == [ffa.id]

    with pytest.raises(ResultChangeError):
        mark_not_rateable(db_session, ffa, " ")
    mark_not_rateable(db_session, ffa, "Vincent")

    assert (ffa.result_source, ffa.result_confirmed_by, winners(db_session, ffa)) == (
        ResultSource.NOT_RATEABLE, "Vincent", set())
    assert review_queue(db_session) == []
    assert ffa.id not in {m.id for m in db_session.query(Match).filter(Match.is_rated)}
    assert settle_unrecorded_results(db_session, dry_run=True).changed == []
