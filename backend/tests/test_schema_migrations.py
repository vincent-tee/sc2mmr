from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app.schema import upgrade_schema


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/schema.db")
    yield engine
    engine.dispose()


def test_empty_database_upgrade_is_repeatable(engine):
    upgrade_schema(engine)
    upgrade_schema(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0008"
        assert connection.execute(text("SELECT count(*) FROM derived_data_state WHERE id = 1")).scalar() == 1
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    indexes = inspect(engine).get_indexes("matches")
    assert any(index["name"] == "uq_matches_game_fingerprint" and index["unique"] for index in indexes)


def test_selection_migration_preserves_existing_judgments_and_feedback(engine):
    from alembic import command
    from alembic.config import Config
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).parents[1] / 'migrations'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, '0003')
        connection.exec_driver_sql("""
            INSERT INTO pregame_judgments
            (id, created_at, team1_player_ids_key, team2_player_ids_key,
             human_estimate, confidence, reason, author, is_locked)
            VALUES (5, '2026-09-01', '1,2', '3,4', 'EVEN', 'MEDIUM', 'OTHER', 'Organizer', 1)
        """)
        connection.exec_driver_sql("""
            INSERT INTO postgame_feedback (id, created_at, judgment_id, feedback, author)
            VALUES (8, '2026-09-01', 5, 'FELT_BALANCED', 'Organizer')
        """)
    upgrade_schema(engine)
    with engine.connect() as connection:
        assert connection.exec_driver_sql('SELECT id, author, selection_id FROM pregame_judgments').one() == (5, 'Organizer', None)
        assert connection.exec_driver_sql('SELECT id, judgment_id FROM postgame_feedback').one() == (8, 5)
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []


def test_legacy_database_gains_columns_without_losing_history(engine):
    snapshot = Path(__file__).parents[1] / "migrations/versions/0001_schema.sql"
    with engine.begin() as connection:
        for statement in snapshot.read_text().split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement)
        connection.exec_driver_sql("INSERT INTO players (id, name) VALUES (1, 'ShadowDragon')")
        connection.exec_driver_sql("UPDATE players SET mu = 31, sigma = 4 WHERE id = 1")
        connection.exec_driver_sql("ALTER TABLE players DROP COLUMN unified_mmr")
        connection.exec_driver_sql("ALTER TABLE player_match_metrics DROP COLUMN kill_death_ratio")
        connection.exec_driver_sql("DROP INDEX ix_matches_game_fingerprint")
        connection.exec_driver_sql("ALTER TABLE matches DROP COLUMN game_fingerprint")
    upgrade_schema(engine)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT name, mu, sigma FROM players").one() == ("ShadowDragon", 31, 4)
    assert "unified_mmr" in {c["name"] for c in inspect(engine).get_columns("players")}
    assert "kill_death_ratio" in {c["name"] for c in inspect(engine).get_columns("player_match_metrics")}


def test_preexisting_foreign_key_violation_survives_migration_untouched(engine):
    snapshot = Path(__file__).parents[1] / "migrations/versions/0001_schema.sql"
    with engine.begin() as connection:
        for statement in snapshot.read_text().split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement)
        connection.execute(text(
            "INSERT INTO matches (id, played_at, game_mode, map_name, duration_seconds, replay_hash) "
            "VALUES (1, '2026-08-01', 'TWO_V_TWO', 'Test', 600, 'orphan-parent')"
        ))
        nonexistent_player_id = 999
        connection.execute(text(
            "INSERT INTO match_players (id, match_id, player_id, team_number, race, won, "
            "mu_before, sigma_before, mu_after, sigma_after) "
            "VALUES (1, 1, :player_id, 1, 'Terran', 1, 25.0, 8.333, 25.0, 8.333)"
        ), {"player_id": nonexistent_player_id})

    upgrade_schema(engine)

    with engine.connect() as connection:
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        orphan = connection.execute(text(
            "SELECT match_id, player_id FROM match_players WHERE id = 1"
        )).one()
    assert orphan == (1, nonexistent_player_id)
    assert violations == [("match_players", 1, "players", 0)]


def test_duplicate_games_stop_migration_without_deleting_records(engine):
    snapshot = Path(__file__).parents[1] / "migrations/versions/0001_schema.sql"
    with engine.begin() as connection:
        for statement in snapshot.read_text().split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement)
        for replay_hash in ("first", "second"):
            connection.execute(text(
                "INSERT INTO matches (played_at, game_mode, map_name, duration_seconds, "
                "replay_hash, game_fingerprint) VALUES ('2026-08-01', 'TWO_V_TWO', 'Test', 600, :hash, 'duplicate')"
            ), {"hash": replay_hash})
    with pytest.raises(RuntimeError, match="match IDs: 1,2"):
        upgrade_schema(engine)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM matches").scalar() == 2
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
