import os
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from app.exceptions import ValidationError
from app.match_result import ResultSource, StatsSnapshot, supply_at_common_frame, supply_favourite
from app.models import GameMode, MatchPlayer, Race
from app.replay_parser import PlayerData, ReplayData, parse_replay
from app.services.ingestion import ingest_match


@pytest.fixture
def suggested_replay():
    return ReplayData(
        played_at=datetime(2026, 8, 1), game_mode=GameMode.TWO_V_TWO,
        map_name="Test map", duration_seconds=600, replay_hash="no-result-file",
        game_fingerprint="same-game",
        players=[PlayerData(name=f"Player {i}", race=Race.TERRAN,
                            team=1 if i < 2 else 2, won=i < 2) for i in range(4)],
        result_source=ResultSource.SUGGESTED,
        result_evidence={"frame": 100, "team_supply": {"1": 150.0, "2": 40.0}},
    )


def flipped(replay_data):
    return replace(replay_data, players=[replace(p, won=not p.won) for p in replay_data.players])


def test_common_frame_ignores_the_recorders_later_snapshot():
    snapshots = [
        StatsSnapshot(player_id=1, team=1, frame=160, supply_used=50),
        StatsSnapshot(player_id=1, team=1, frame=320, supply_used=59),
        StatsSnapshot(player_id=1, team=1, frame=392, supply_used=70),
        StatsSnapshot(player_id=2, team=2, frame=160, supply_used=40),
        StatsSnapshot(player_id=2, team=2, frame=320, supply_used=56),
    ]
    assert supply_at_common_frame(snapshots) == {"frame": 320, "team_supply": {"1": 59, "2": 56}}


def test_supply_favourite_reports_ratio():
    assert supply_favourite({"frame": 1, "team_supply": {"1": 150.0, "2": 50.0}}) == (1, 3.0)
    assert supply_favourite({"frame": 1, "team_supply": {"1": 10.0, "2": 10.0}}) == (None, 1.0)
    assert supply_favourite(None) == (None, None)


def test_new_match_keeps_its_result_source_and_evidence(db_session, suggested_replay):
    match, _ = ingest_match(db_session, suggested_replay, require_experience=False)
    assert match.result_source == ResultSource.SUGGESTED
    assert match.result_evidence == {"frame": 100, "team_supply": {"1": 150.0, "2": 40.0}}


def test_agreeing_recording_with_a_result_settles_a_suggested_one(db_session, suggested_replay):
    ingest_match(db_session, suggested_replay, require_experience=False)
    other = replace(suggested_replay, replay_hash="has-result-file", result_source=ResultSource.REPLAY)
    match, created = ingest_match(db_session, other, require_experience=False)
    assert not created
    assert match.result_source == ResultSource.REPLAY


def test_disagreeing_recording_is_recorded_not_applied(db_session, suggested_replay):
    ingest_match(db_session, suggested_replay, require_experience=False)
    before = sorted((mp.player.name, mp.won) for mp in db_session.query(MatchPlayer))
    other = replace(flipped(suggested_replay), replay_hash="has-result-file", result_source=ResultSource.REPLAY)
    match, created = ingest_match(db_session, other, "/stored/other.SC2Replay", require_experience=False)
    assert not created
    assert match.result_source == ResultSource.SUGGESTED
    assert match.result_evidence["other_recordings"] == [{"replay_hash": "has-result-file", "winner_team": 2}]
    assert match.replay_hash == "no-result-file"
    assert sorted((mp.player.name, mp.won) for mp in db_session.query(MatchPlayer)) == before


def test_disagreeing_recording_still_rejected_when_result_is_known(db_session, suggested_replay):
    known = replace(suggested_replay, result_source=ResultSource.REPLAY)
    ingest_match(db_session, known, require_experience=False)
    other = replace(flipped(known), replay_hash="another-file")
    with pytest.raises(ValidationError, match="recorded winner"):
        ingest_match(db_session, other, require_experience=False)


FIXTURE_REPLAYS = Path(os.environ.get("SC2MMR_FIXTURE_REPLAYS", Path(__file__).resolve().parents[1] / "replays"))
NO_RESULT_REPLAY = FIXTURE_REPLAYS / "107e2e0dc64a64dc9ea45408c6ac26651fb48cd65418116f389f00aca9e2830b.SC2Replay"
DISPUTED_NO_RESULT_REPLAY = FIXTURE_REPLAYS / "361e31e8c6c844196005748299fc210a9f7740e66b877dff265ee049c6cf8da4.SC2Replay"
NORMAL_REPLAY = FIXTURE_REPLAYS / "0064f1e60fb95eb7041b04ceae6bd3249339f987f540046a3a636692fea74586.SC2Replay"


def require(path):
    if not path.exists():
        pytest.skip(f"replay fixture not available: {path.name}")
    return str(path)


@pytest.mark.local_data
def test_replay_without_a_result_goes_to_the_clear_supply_leader():
    parsed = parse_replay(require(NO_RESULT_REPLAY))
    assert parsed.result_source == ResultSource.SUGGESTED
    assert {p.team for p in parsed.players if p.won} == {2}


@pytest.mark.local_data
def test_match_1168_goes_to_team_2_on_supply():
    parsed = parse_replay(require(DISPUTED_NO_RESULT_REPLAY))
    assert parsed.result_source == ResultSource.SUGGESTED
    assert parsed.result_evidence["team_supply"] == {"1": 153.5, "2": 286.5}
    assert {p.team for p in parsed.players if p.won} == {2}


@pytest.mark.local_data
def test_replay_with_a_result_is_labelled_replay():
    parsed = parse_replay(require(NORMAL_REPLAY))
    assert parsed.result_source == ResultSource.REPLAY
    assert {p.name for p in parsed.players if p.won} == {"ChrisO", "Redevilz"}


@pytest.mark.local_data
def test_a_persons_choice_is_labelled_confirmed():
    parsed = parse_replay(require(DISPUTED_NO_RESULT_REPLAY), manual_winner_team=1)
    assert parsed.result_source == ResultSource.CONFIRMED
    assert {p.team for p in parsed.players if p.won} == {1}


def test_too_close_to_call_goes_to_manual_review(monkeypatch):
    import app.match_result as match_result
    from app.replay_parser import WinnerDeterminationError
    monkeypatch.setattr(match_result, "CLEAR_SUPPLY_LEAD", 5.0)
    with pytest.raises(WinnerDeterminationError, match="clearly show a winner"):
        parse_replay(require(NO_RESULT_REPLAY))
