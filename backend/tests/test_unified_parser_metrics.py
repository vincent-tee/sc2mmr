"""Tests for two UnifiedParser bugs found in the 2026-09-15 metrics review:
the final engagement group was never flushed, and team_fight_damage_ratio
was computed before damage_dealt was set (always dividing by the max(1, 0)
floor instead of the real value).
"""
from app.services.unified_parser import UnifiedParser
from app.types.results import PlayerMatchResult
from app.models import Race


def _player(name, damage_timeline, army_value_killed=0):
    return PlayerMatchResult(
        name=name, race=Race.TERRAN, team=1, won=True,
        damage_timeline=damage_timeline, army_value_killed=army_value_killed,
    )


def test_final_engagement_group_is_not_dropped():
    """3+ players fighting at consecutive seconds with no trailing gap --
    the loop ends while still inside the group, which previously meant it
    was silently never flushed."""
    parser = UnifiedParser()
    players = [
        _player("A", {10: 50, 11: 50, 12: 50}),
        _player("B", {10: 50, 11: 50, 12: 50}),
        _player("C", {10: 50, 11: 50, 12: 50}),
    ]
    engagements = parser._detect_team_engagements(players)
    assert engagements == [{"start": 10, "end": 12}]


def test_engagement_detection_still_flushes_mid_sequence_groups():
    """An engagement followed by a real gap must still be detected (this
    was already working; guards against breaking it while fixing the above)."""
    parser = UnifiedParser()
    players = [
        _player("A", {10: 50, 11: 50, 12: 50, 100: 50, 101: 50, 102: 50}),
        _player("B", {10: 50, 11: 50, 12: 50, 100: 50, 101: 50, 102: 50}),
        _player("C", {10: 50, 11: 50, 12: 50, 100: 50, 101: 50, 102: 50}),
    ]
    engagements = parser._detect_team_engagements(players)
    assert engagements == [{"start": 10, "end": 12}, {"start": 100, "end": 102}]


def test_team_fight_damage_ratio_uses_real_damage_dealt_not_the_floor():
    """Reproduces the review's synthetic example: 300 total resource-value
    units for the receiver across an engagement window, army_value_killed
    =1000. The correct ratio under this codebase's own definition is
    300/1000 = 0.3, not 300 (dividing by max(1, 0) instead of max(1, 1000),
    which is what happened when the ratio was computed before damage_dealt
    was set)."""
    parser = UnifiedParser()
    # Seconds 10-12 form one 3-player engagement (>=3 consecutive seconds,
    # >=3 players active in that window) so it actually gets flushed.
    players = [
        _player("A", {10: 100, 11: 100, 12: 100}, army_value_killed=1000),
        _player("B", {10: 50, 11: 50, 12: 50}, army_value_killed=1000),
        _player("C", {10: 50, 11: 50, 12: 50}, army_value_killed=1000),
    ]
    parser._calculate_damage_metrics(players)
    engagements = parser._detect_team_engagements(players)
    assert engagements == [{"start": 10, "end": 12}]
    for r in players:
        parser._calculate_team_fight_metrics(r, engagements)
    parser._calculate_derived_metrics(players)

    assert players[0].damage_dealt == 1000  # sanity: set before the ratio needed it
    assert players[0].team_fight_damage_ratio == 300 / 1000
