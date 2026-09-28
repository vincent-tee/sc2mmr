from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ValidationError
from app.models import Base, Match, MatchPlayer, Player, PlayerAlias, PlayerSynergy, Race, GameMode
from app.replay_parser import ReplayData, PlayerData
from app.rating_system import RatingSystem
from app.services.ingestion import ingest_match, post_process_match, run_optional_processing


@pytest.fixture
def replay():
    return ReplayData(
        played_at=datetime(2026, 8, 1), game_mode=GameMode.TWO_V_TWO,
        map_name="Test map", duration_seconds=600, replay_hash="first-file",
        game_fingerprint="same-game",
        players=[PlayerData(name=f"Player {i}", race=Race.TERRAN,
                            team=1 if i < 2 else 2, won=i < 2) for i in range(4)],
    )


def player_state(db):
    return [(p.name, p.mu, p.sigma, p.mmr, p.total_games, p.wins, p.losses)
            for p in db.scalars(select(Player).order_by(Player.name))]


def test_rating_failure_rolls_back_commits_and_retry_succeeds(db_session, replay, monkeypatch):
    original = RatingSystem.update_ratings_from_match

    def fail_after_rating_commit(db, replay_data, match):
        original(db, replay_data, match)
        raise RuntimeError("rating failure")

    monkeypatch.setattr(RatingSystem, "update_ratings_from_match", fail_after_rating_commit)
    with pytest.raises(RuntimeError, match="rating failure"):
        ingest_match(db_session, replay, require_experience=False)
    assert db_session.query(Match).count() == 0
    assert db_session.query(Player).count() == 0
    monkeypatch.setattr(RatingSystem, "update_ratings_from_match", original)
    _, created = ingest_match(db_session, replay, require_experience=False)
    assert created
    assert all(p.total_games == 1 for p in db_session.query(Player))


def test_longer_observer_replay_preserves_rating_and_synergy(db_session, replay):
    match, _ = ingest_match(db_session, replay, require_experience=False)
    before = player_state(db_session)
    synergy_before = [(s.games_together, s.wins_together) for s in db_session.query(PlayerSynergy)]
    longer = replace(replay, replay_hash="observer-file", duration_seconds=900)
    refreshed, created = ingest_match(db_session, longer, "/stored/observer.SC2Replay", require_experience=False)
    assert not created
    assert refreshed.id == match.id
    assert refreshed.duration_seconds == 900
    assert player_state(db_session) == before
    assert [(s.games_together, s.wins_together) for s in db_session.query(PlayerSynergy)] == synergy_before
    assert db_session.query(MatchPlayer).count() == 4


def test_metrics_failure_preserves_original_replay(db_session, replay):
    match, _ = ingest_match(db_session, replay, require_experience=False)
    def fail(db, match):
        match.map_name = "partially changed"
        db.commit()
        raise RuntimeError("metrics failure")
    with pytest.raises(RuntimeError):
        ingest_match(db_session, replace(replay, duration_seconds=900), save_metrics=fail,
                     require_experience=False)
    db_session.refresh(match)
    assert match.map_name == replay.map_name
    assert match.duration_seconds == 600


def test_conflicting_winner_cannot_overwrite_existing_match(db_session, replay):
    ingest_match(db_session, replay, require_experience=False)
    before = player_state(db_session)
    changed = replace(replay, players=[replace(p, won=not p.won) for p in replay.players])
    with pytest.raises(ValidationError, match="conflicts"):
        ingest_match(db_session, changed, require_experience=False)
    assert player_state(db_session) == before


def test_experience_rejection_does_not_leave_ghost_match(db_session, replay):
    with pytest.raises(ValidationError, match="experience"):
        ingest_match(db_session, replay)
    assert db_session.query(Match).count() == 0


def test_optional_failure_cannot_commit_partial_changes(db_session, replay):
    match, _ = ingest_match(db_session, replay, require_experience=False)
    def fail(work):
        work.get(Match, match.id).map_name = "partial"
        work.commit()
        raise RuntimeError("optional failure")
    run_optional_processing(db_session, "test", fail)
    assert db_session.get(Match, match.id).map_name == replay.map_name


def test_post_processing_a_new_match_does_not_raise(db_session, replay):
    match, created = ingest_match(db_session, replay, require_experience=False)
    post_process_match(db_session, match.id, created)


def test_app_engine_waits_for_sqlite_writer_lock():
    from app.database import engine
    with engine.connect() as connection:
        busy_timeout_ms = connection.exec_driver_sql("PRAGMA busy_timeout").scalar()
    assert busy_timeout_ms >= 30_000


def test_database_rejects_duplicate_fingerprints(db_session, replay):
    ingest_match(db_session, replay, require_experience=False)
    db_session.add(Match(played_at=replay.played_at, game_mode=replay.game_mode,
                         map_name=replay.map_name, duration_seconds=600,
                         replay_hash="other", game_fingerprint=replay.game_fingerprint))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_concurrent_observer_uploads_count_game_once(tmp_path, replay):
    from concurrent.futures import ThreadPoolExecutor
    engine = create_engine(f"sqlite:///{tmp_path}/concurrent.db", connect_args={"timeout": 15})
    Base.metadata.create_all(engine)
    def ingest(index):
        with Session(engine) as db:
            _, created = ingest_match(db, replace(replay, replay_hash=f"file-{index}"),
                                      require_experience=False)
            return created
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert sorted(executor.map(ingest, range(2))) == [False, True]
        with Session(engine) as db:
            assert db.query(Match).count() == 1
            assert all(p.total_games == 1 for p in db.query(Player))
    finally:
        engine.dispose()


def test_replay_with_no_winning_team_is_rejected(db_session, replay):
    nobody_won = replace(replay, players=[replace(p, won=False) for p in replay.players])
    with pytest.raises(ValidationError, match="two teams and one winning team"):
        ingest_match(db_session, nobody_won, require_experience=False)
    assert db_session.query(Match).count() == 0


def players_with_won_overridden(players, won_by_index):
    updated = list(players)
    for index, won in won_by_index.items():
        updated[index] = replace(updated[index], won=won)
    return updated


def test_replay_with_two_winning_teams_is_rejected(db_session, replay):
    assert replay.players[0].team == 1 and replay.players[2].team == 2
    both_teams_won = replace(
        replay, players=players_with_won_overridden(replay.players, {0: True, 2: True})
    )
    with pytest.raises(ValidationError, match="two teams and one winning team"):
        ingest_match(db_session, both_teams_won, require_experience=False)
    assert db_session.query(Match).count() == 0


def test_teammates_disagreeing_on_the_winner_is_rejected(db_session, replay):
    assert replay.players[0].team == 1 and replay.players[1].team == 1
    contradictory_result = replace(
        replay, players=players_with_won_overridden(replay.players, {0: True, 1: False})
    )
    with pytest.raises(ValidationError, match="conflicting results"):
        ingest_match(db_session, contradictory_result, require_experience=False)
    assert db_session.query(Match).count() == 0


def test_ingestion_resolves_alias_to_canonical_player(db_session, replay):
    canonical = Player(name="Canonical")
    db_session.add(canonical)
    db_session.commit()
    db_session.add(PlayerAlias(source_name="Player 0", target_player_id=canonical.id))
    db_session.commit()

    match, created = ingest_match(db_session, replay, require_experience=False)

    assert created
    assert db_session.query(Player).filter(Player.name == "Player 0").first() is None
    canonical_mp = (
        db_session.query(MatchPlayer)
        .filter(MatchPlayer.match_id == match.id, MatchPlayer.player_id == canonical.id)
        .first()
    )
    assert canonical_mp is not None
    assert canonical_mp.won == 1
    assert db_session.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).count() == 4


def test_alias_below_min_players_does_not_apply(db_session, replay):
    canonical = Player(name="Canonical")
    db_session.add(canonical)
    db_session.commit()
    db_session.add(PlayerAlias(source_name="Player 0", target_player_id=canonical.id))
    db_session.commit()

    one_v_one = replace(
        replay, game_mode=GameMode.ONE_V_ONE,
        players=[replay.players[0], replace(replay.players[2], team=2)],
    )
    ingest_match(db_session, one_v_one, require_experience=False)

    assert db_session.query(Player).filter(Player.name == "Player 0").first() is not None


def another_players_copy(replay, seconds_later=8, duration_seconds=540):
    return replace(replay, replay_hash="teammate-file", game_fingerprint="teammate-fingerprint",
                   played_at=replay.played_at + timedelta(seconds=seconds_later),
                   duration_seconds=duration_seconds)


def test_same_game_recorded_by_another_player_counts_once(db_session, replay):
    match, _ = ingest_match(db_session, replay, require_experience=False)
    before = player_state(db_session)
    same_game, created = ingest_match(db_session, another_players_copy(replay), require_experience=False)
    assert not created
    assert same_game.id == match.id
    assert db_session.query(Match).count() == 1
    assert player_state(db_session) == before


def test_rematch_with_the_same_players_on_the_same_map_is_a_new_game(db_session, replay):
    ingest_match(db_session, replay, require_experience=False)
    rematch = another_players_copy(replay, seconds_later=12 * 60, duration_seconds=600)
    _, created = ingest_match(db_session, rematch, require_experience=False)
    assert created
    assert db_session.query(Match).count() == 2


def test_game_aborted_in_the_lobby_is_rejected(db_session, replay):
    with pytest.raises(ValidationError, match="aborted"):
        ingest_match(db_session, replace(replay, duration_seconds=4), require_experience=False)
    assert db_session.query(Match).count() == 0
