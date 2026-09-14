"""Tests for the narrow, investigated FK-violation repair."""
from datetime import datetime

from sqlalchemy import text

from app.models import Match, MatchPlayer, PlayerMatchMetrics, Race, GameMode
from app.services.fk_repair import repair_orphaned_metrics


def _match_with_metric(db_session, player):
    match = Match(played_at=datetime.utcnow(), game_mode=GameMode.ONE_V_ONE,
                  map_name="M", duration_seconds=300)
    db_session.add(match)
    db_session.flush()
    mp = MatchPlayer(match_id=match.id, player_id=player.id, team_number=1,
                      race=Race.TERRAN, won=1, mu_before=25, sigma_before=8.333,
                      mu_after=25, sigma_after=8.333)
    db_session.add(mp)
    db_session.flush()
    metric = PlayerMatchMetrics(match_player_id=mp.id, overall_impact=50.0)
    db_session.add(metric)
    db_session.commit()
    return match, mp, metric


def test_repairs_orphaned_metrics_only(db_session, player_factory):
    p = player_factory(name="Repair1")
    match, mp, orphan_metric = _match_with_metric(db_session, p)

    # Create the surviving row BEFORE deleting the other one, so SQLite can't
    # reuse the deleted rowid and accidentally collide with it below.
    p2 = player_factory(name="Repair2")
    _, _, surviving_metric = _match_with_metric(db_session, p2)

    # Simulate the known historical cause: delete the match_players row via
    # a raw connection that doesn't enforce FKs, leaving the metric orphaned
    # (exactly how the real 375/287-row violations were created).
    db_session.execute(text("PRAGMA foreign_keys=OFF"))
    db_session.execute(text("DELETE FROM match_players WHERE id=:id"), {"id": mp.id})
    db_session.commit()
    db_session.execute(text("PRAGMA foreign_keys=ON"))

    result = repair_orphaned_metrics(db_session)
    assert result["repaired"] == 1
    assert result["remaining_violations"] == 0

    assert db_session.get(PlayerMatchMetrics, orphan_metric.id) is None
    assert db_session.get(PlayerMatchMetrics, surviving_metric.id) is not None


def test_refuses_to_touch_unknown_violation_shapes(db_session, player_factory):
    p = player_factory(name="Unknown1")
    match = Match(played_at=datetime.utcnow(), game_mode=GameMode.ONE_V_ONE,
                  map_name="M", duration_seconds=300)
    db_session.add(match)
    db_session.commit()
    mp = MatchPlayer(match_id=match.id, player_id=p.id, team_number=1,
                      race=Race.TERRAN, won=1, mu_before=25, sigma_before=8.333,
                      mu_after=25, sigma_after=8.333)
    db_session.add(mp)
    db_session.commit()

    db_session.execute(text("PRAGMA foreign_keys=OFF"))
    db_session.execute(text("DELETE FROM matches WHERE id=:id"), {"id": match.id})
    db_session.commit()
    db_session.execute(text("PRAGMA foreign_keys=ON"))

    before_count = db_session.query(MatchPlayer).filter(MatchPlayer.id == mp.id).count()
    result = repair_orphaned_metrics(db_session)

    assert result["repaired"] == 0
    assert result["skipped_unknown_categories"]
    after_count = db_session.query(MatchPlayer).filter(MatchPlayer.id == mp.id).count()
    assert before_count == after_count == 1, "must not touch an uncharacterized violation shape"


def test_no_violations_is_a_clean_noop(db_session):
    result = repair_orphaned_metrics(db_session)
    assert result["repaired"] == 0
    assert result["remaining_violations"] == 0
