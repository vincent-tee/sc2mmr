"""Tests for the safe, in-place rating recalculation service.

Covers exactly the properties that made the standalone
scripts/recalculate_all_mmrs.py dangerous per the independent review: it must
never delete/recreate match_players (which would orphan child metric rows),
and it must produce the same result as the trusted chronological policy used
everywhere else (rating_policy.py), not a different, undecayed one.
"""
import trueskill

from app.models import Match, MatchPlayer, Player, PlayerMatchMetrics, Race, GameMode
from app.rating_system import RatingSystem
from app.services.rating_recalculation import recalculate_ratings_in_place


def _make_match(db_session, players_teams, played_at):
    """players_teams: list of (player, team_number, won) tuples."""
    match = Match(played_at=played_at, game_mode=GameMode.TWO_V_TWO,
                  map_name="TestMap", duration_seconds=600)
    db_session.add(match)
    db_session.flush()
    mps = []
    for player, team, won in players_teams:
        mp = MatchPlayer(
            match_id=match.id, player_id=player.id, team_number=team,
            race=Race.TERRAN, won=1 if won else 0,
            mu_before=player.mu, sigma_before=player.sigma,
            mu_after=player.mu, sigma_after=player.sigma,
            mmr_before=player.mmr, mmr_after=player.mmr,
        )
        db_session.add(mp)
        mps.append(mp)
    db_session.flush()
    return match, mps


def test_recalculation_never_deletes_or_recreates_match_players(db_session, player_factory):
    from datetime import datetime, timedelta
    p1, p2, p3, p4 = (player_factory(name=f"R{i}") for i in range(1, 5))
    now = datetime.utcnow()
    _, mps1 = _make_match(db_session, [(p1, 1, True), (p2, 1, True), (p3, 2, False), (p4, 2, False)], now)
    _, mps2 = _make_match(db_session, [(p1, 1, False), (p3, 1, False), (p2, 2, True), (p4, 2, True)],
                           now + timedelta(days=1))
    db_session.commit()

    metric = PlayerMatchMetrics(match_player_id=mps1[0].id, overall_impact=55.0)
    db_session.add(metric)
    db_session.commit()

    before_mp_ids = {mp.id for mp in db_session.query(MatchPlayer).all()}
    before_metric_id = metric.id

    stats = recalculate_ratings_in_place(db_session)

    after_mp_ids = {mp.id for mp in db_session.query(MatchPlayer).all()}
    assert before_mp_ids == after_mp_ids, "match_players rows must be updated in place, never recreated"

    surviving_metric = db_session.get(PlayerMatchMetrics, before_metric_id)
    assert surviving_metric is not None, "child metric row must survive recalculation untouched"
    assert surviving_metric.match_player_id == mps1[0].id, "metric linkage must not be disturbed"

    assert stats["matches_processed"] == 2
    assert stats["players_updated"] == 4


def test_recalculation_matches_pure_trueskill_with_decay(db_session, player_factory):
    """The recalculated mu/sigma must come from the same policy
    (rating_policy.decayed_sigma + rate_teams) as live ingestion, not a
    separate, undecayed implementation."""
    from datetime import datetime, timedelta
    from app.rating_policy import decayed_sigma, typical_session_gap, rate_teams

    p1, p2 = player_factory(name="D1"), player_factory(name="D2")
    day0 = datetime.utcnow()
    day30 = day0 + timedelta(days=30)  # gap long enough that decay should matter
    _make_match(db_session, [(p1, 1, True), (p2, 2, False)], day0)
    _make_match(db_session, [(p1, 1, False), (p2, 2, True)], day30)
    db_session.commit()

    recalculate_ratings_in_place(db_session)

    r1 = trueskill.Rating(mu=25.0, sigma=8.333)
    r2 = trueskill.Rating(mu=25.0, sigma=8.333)
    new1, new2 = rate_teams([r1], [r2], True)
    r1, r2 = new1[0], new2[0]
    # second match: decay applies to both players over the 30-day gap
    r1 = trueskill.Rating(mu=r1.mu, sigma=decayed_sigma(r1.sigma, 30, 1, typical_session_gap([day0])))
    r2 = trueskill.Rating(mu=r2.mu, sigma=decayed_sigma(r2.sigma, 30, 1, typical_session_gap([day0])))
    new1, new2 = rate_teams([r1], [r2], False)
    expected_p1, expected_p2 = new1[0], new2[0]

    actual_p1 = db_session.query(Player).filter(Player.id == p1.id).first()
    actual_p2 = db_session.query(Player).filter(Player.id == p2.id).first()
    assert abs(actual_p1.mu - expected_p1.mu) < 1e-9
    assert abs(actual_p1.sigma - expected_p1.sigma) < 1e-9
    assert abs(actual_p2.mu - expected_p2.mu) < 1e-9
    assert abs(actual_p2.sigma - expected_p2.sigma) < 1e-9


def test_recalculation_skips_matches_with_contradictory_winners(db_session, player_factory):
    """Both-teams-won and no-team-won rows must be excluded from the
    rating transition entirely (voided), not resolved by row order."""
    from datetime import datetime
    p1, p2 = player_factory(name="C1"), player_factory(name="C2")
    match, mps = _make_match(db_session, [(p1, 1, True), (p2, 2, True)], datetime.utcnow())  # both won
    db_session.commit()

    stats = recalculate_ratings_in_place(db_session)
    assert stats["matches_skipped"] == 1
    assert stats["matches_processed"] == 0

    player = db_session.query(Player).filter(Player.id == p1.id).first()
    assert player.mu == 25.0 and player.total_games == 0, "voided match must not affect ratings or stats"


def test_recalculation_formula_consistency(db_session, player_factory):
    from datetime import datetime
    p1, p2 = player_factory(name="F1"), player_factory(name="F2")
    _make_match(db_session, [(p1, 1, True), (p2, 2, False)], datetime.utcnow())
    db_session.commit()

    recalculate_ratings_in_place(db_session)

    for p in (p1, p2):
        player = db_session.query(Player).filter(Player.id == p.id).first()
        expected_mmr = RatingSystem.calculate_display_mmr(player.mu, player.sigma)
        assert abs(player.mmr - expected_mmr) < 1e-6
