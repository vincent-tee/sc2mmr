from datetime import datetime

import pytest

from app.models import GameMode, MatchPlayer, Player, PlayerMatchMetrics, Race
from app.replay_parser import ReplayData, PlayerData
from app.services.ingestion import ingest_match
from app.services.metrics_backfill import BACKFILLED_FIELDS, apply_metrics_rows


@pytest.fixture
def match(db_session):
    replay = ReplayData(
        played_at=datetime(2026, 8, 1), game_mode=GameMode.TWO_V_TWO, map_name="Test map",
        duration_seconds=600, replay_hash="replay-hash", game_fingerprint="fingerprint",
        players=[PlayerData(name=f"Player {i}", race=Race.TERRAN,
                            team=1 if i < 2 else 2, won=i < 2) for i in range(4)],
    )
    recorded, _ = ingest_match(db_session, replay, require_experience=False)
    return recorded


def row_for(db_session, player_name, army_value_killed):
    player = db_session.query(Player).filter(Player.name == player_name).one()
    row = {name: 0 for name in BACKFILLED_FIELDS}
    row.update(replay_hash="replay-hash", player_id=player.id,
               army_value_killed=army_value_killed, unit_composition={"Marine": 3})
    return row


def stored_army_value_killed(db_session, player_name):
    return (db_session.query(PlayerMatchMetrics.army_value_killed)
            .join(MatchPlayer).join(Player).filter(Player.name == player_name).scalar())


def test_backfill_updates_existing_rows_and_creates_missing_ones(db_session, match):
    participant = db_session.query(MatchPlayer).join(Player).filter(Player.name == "Player 0").one()
    db_session.add(PlayerMatchMetrics(match_player_id=participant.id, army_value_killed=1))
    db_session.commit()

    stats = apply_metrics_rows(db_session, [row_for(db_session, "Player 0", 5000),
                                            row_for(db_session, "Player 1", 7000)])

    assert (stats.updated, stats.created, stats.unmatched) == (1, 1, 0)
    assert stored_army_value_killed(db_session, "Player 0") == 5000
    assert stored_army_value_killed(db_session, "Player 1") == 7000


def test_backfill_skips_players_who_are_not_in_the_match(db_session, match):
    outsider = Player(name="Outsider")
    db_session.add(outsider)
    db_session.commit()
    row = row_for(db_session, "Player 0", 5000)
    row["player_id"] = outsider.id

    stats = apply_metrics_rows(db_session, [row])

    assert stats.unmatched == 1
    assert db_session.query(PlayerMatchMetrics).count() == 0
