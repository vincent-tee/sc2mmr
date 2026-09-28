from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from app.models import GameMode, Match, MatchPlayer, PlayerMatchMetrics, Race
from app.replay_parser import ReplayData, PlayerData
from app.services.game_cleanup import plan_cleanup, remove_matches
from app.services.ingestion import ingest_match


@pytest.fixture
def replay():
    return ReplayData(
        played_at=datetime(2026, 8, 1, 12, 10), game_mode=GameMode.TWO_V_TWO,
        map_name="Test map", duration_seconds=600, replay_hash="recorder-file",
        game_fingerprint="recorder-fingerprint",
        players=[PlayerData(name=f"Player {i}", race=Race.TERRAN,
                            team=1 if i < 2 else 2, won=i < 2) for i in range(4)],
    )


def store_second_copy(db, original, duration_seconds, seconds_later=5, team1_won=True):
    copy = Match(played_at=original.played_at + timedelta(seconds=seconds_later),
                 game_mode=original.game_mode, map_name=original.map_name,
                 duration_seconds=duration_seconds, replay_hash=f"copy-{duration_seconds}")
    db.add(copy)
    db.flush()
    for mp in original.participants:
        won = (mp.team_number == 1) == team1_won
        db.add(MatchPlayer(match_id=copy.id, player_id=mp.player_id, team_number=mp.team_number,
                           race=mp.race, won=int(won), mu_before=25, sigma_before=8,
                           mu_after=25, sigma_after=8))
    db.commit()
    return copy


def test_plan_keeps_the_longer_copy_of_a_game_stored_twice(db_session, replay):
    original, _ = ingest_match(db_session, replay, require_experience=False)
    truncated = store_second_copy(db_session, original, duration_seconds=420, team1_won=False)

    plan = plan_cleanup(db_session)

    assert [(c.kept_match_id, c.removed_match_id, c.winners_agree) for c in plan.duplicate_copies] == [
        (original.id, truncated.id, False)]
    assert plan.aborted_match_ids == []


def test_plan_flags_aborted_games_and_ignores_rematches(db_session, replay):
    ingest_match(db_session, replay, require_experience=False)
    rematch = replace(replay, replay_hash="rematch", game_fingerprint="rematch",
                      played_at=replay.played_at + timedelta(minutes=12))
    ingest_match(db_session, rematch, require_experience=False)
    aborted = Match(played_at=replay.played_at + timedelta(hours=1), game_mode=replay.game_mode,
                    map_name=replay.map_name, duration_seconds=3, replay_hash="lobby")
    db_session.add(aborted)
    db_session.commit()

    plan = plan_cleanup(db_session)

    assert plan.aborted_match_ids == [aborted.id]
    assert plan.duplicate_copies == []


def test_removing_a_copy_removes_its_participants_and_metrics(db_session, replay):
    original, _ = ingest_match(db_session, replay, require_experience=False)
    copy = store_second_copy(db_session, original, duration_seconds=420)
    copy_participant = db_session.query(MatchPlayer).filter(MatchPlayer.match_id == copy.id).first()
    db_session.add(PlayerMatchMetrics(match_player_id=copy_participant.id))
    db_session.commit()

    remove_matches(db_session, plan_cleanup(db_session).match_ids_to_remove)

    assert [m.id for m in db_session.query(Match)] == [original.id]
    assert db_session.query(MatchPlayer).count() == 4
    assert db_session.query(PlayerMatchMetrics).count() == 0


def test_plan_flags_games_with_no_players(db_session, replay):
    ingest_match(db_session, replay, require_experience=False)
    empty = Match(played_at=datetime(2026, 8, 2), game_mode=GameMode.TWO_V_TWO,
                  map_name="Other map", duration_seconds=600, replay_hash="no-players")
    db_session.add(empty)
    db_session.commit()
    plan = plan_cleanup(db_session)
    assert plan.empty_match_ids == [empty.id]
    assert plan.match_ids_to_remove == [empty.id]
