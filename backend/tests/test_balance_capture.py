"""
Tests for BalancePredictionService calibration deduplication.

Covers the "repeated regenerate clicks" scenario: an organizer who hits
"suggest teams" several times before settling on one split should not have
that game count more heavily in calibration than a game where the first
suggestion was accepted immediately.
"""
from datetime import datetime, timedelta

import pytest

from app.models import GameMode, Match, MatchPlayer, Race
from app.services.balance_capture import BalancePredictionService


GAME_LENGTH = timedelta(minutes=10)


def _make_match(db_session, team1_ids, team2_ids, team1_won, started_at):
    match = Match(
        played_at=started_at + GAME_LENGTH,
        game_mode=GameMode.TWO_V_TWO,
        map_name="TestMap",
        duration_seconds=int(GAME_LENGTH.total_seconds()),
    )
    db_session.add(match)
    db_session.flush()

    for pid in team1_ids:
        db_session.add(
            MatchPlayer(
                match_id=match.id,
                player_id=pid,
                team_number=1,
                race=Race.TERRAN,
                won=1 if team1_won else 0,
                mu_before=25.0,
                sigma_before=8.333,
                mu_after=25.0,
                sigma_after=8.333,
            )
        )
    for pid in team2_ids:
        db_session.add(
            MatchPlayer(
                match_id=match.id,
                player_id=pid,
                team_number=2,
                race=Race.PROTOSS,
                won=0 if team1_won else 1,
                mu_before=25.0,
                sigma_before=8.333,
                mu_after=25.0,
                sigma_after=8.333,
            )
        )
    db_session.flush()
    return match


def _suggested_then_played_game(
    db_session, player_factory, name_prefix, num_suggest_clicks, win_prob, started_at
):
    """Record `num_suggest_clicks` identical suggestions for a freshly-created
    4-player game, then play and resolve it. Returns (match, resolved_count)."""
    p1, p2, p3, p4 = (player_factory(name=f"{name_prefix}{i}") for i in range(1, 5))
    team1_ids, team2_ids = [p1.id, p2.id], [p3.id, p4.id]

    for _ in range(num_suggest_clicks):
        BalancePredictionService.record_suggestion(
            db_session,
            method="mmr_v1",
            rank=1,
            team1_ids=team1_ids,
            team2_ids=team2_ids,
            predicted_team1_win_prob=win_prob,
        )
    db_session.commit()

    match = _make_match(db_session, team1_ids, team2_ids, team1_won=True, started_at=started_at)
    resolved_count = BalancePredictionService.resolve_for_match(db_session, match)
    return match, resolved_count


class TestCalibrationDeduplication:
    def test_repeated_regenerate_counts_once(self, db_session, player_factory):
        """
        A game suggested 3 times (regenerate clicks) before being played must
        contribute the same calibration weight (1 scored pair) as a game
        suggested once.
        """
        starts_shortly_after = datetime.utcnow() + timedelta(minutes=2)
        win_prob = 0.65

        _, resolved_a = _suggested_then_played_game(
            db_session, player_factory, "A", num_suggest_clicks=3, win_prob=win_prob,
            started_at=starts_shortly_after
        )
        assert resolved_a == 3  # every regenerate click resolves individually

        _, resolved_b = _suggested_then_played_game(
            db_session, player_factory, "B", num_suggest_clicks=1, win_prob=win_prob,
            started_at=starts_shortly_after
        )
        assert resolved_b == 1

        # Dedup happens in calibration, not in resolution: 2 games in, 2 scored.
        calibration = BalancePredictionService.get_calibration(
            db_session, method="mmr_v1"
        )
        method_stats = calibration["mmr_v1"]
        assert method_stats["count"] == 2

        # Compares against the full stats (not just the count) to confirm each
        # game contributes one full-weight pair, not a partial/duplicated one.
        both_games_won_team1 = [(win_prob, 1), (win_prob, 1)]
        expected = BalancePredictionService._calibration_from_pairs(both_games_won_team1)
        assert method_stats["brier_score"] == expected["brier_score"]
        assert method_stats["accuracy"] == expected["accuracy"]
        assert method_stats["log_loss"] == expected["log_loss"]

    def test_different_splits_for_same_players_only_score_the_played_one(
        self, db_session, player_factory
    ):
        """
        If regenerating produces a *different* split and only one is ever
        played, resolve_for_match already only resolves the matching split
        (unmatched ones are skipped, per its own logic) -- calibration must
        not need to do anything extra here, this just guards against a
        regression that would resolve the wrong split.
        """
        p1, p2, p3, p4 = (player_factory(name=f"C{i}") for i in range(1, 5))
        starts_shortly_after = datetime.utcnow() + timedelta(minutes=2)

        first_split = ([p1.id, p2.id], [p3.id, p4.id])
        played_split = ([p1.id, p3.id], [p2.id, p4.id])  # the regenerated one

        BalancePredictionService.record_suggestion(
            db_session,
            method="mmr_v1",
            rank=1,
            team1_ids=first_split[0],
            team2_ids=first_split[1],
            predicted_team1_win_prob=0.55,
        )
        BalancePredictionService.record_suggestion(
            db_session,
            method="mmr_v1",
            rank=1,
            team1_ids=played_split[0],
            team2_ids=played_split[1],
            predicted_team1_win_prob=0.60,
        )
        db_session.commit()

        match = _make_match(
            db_session, played_split[0], played_split[1], team1_won=False,
            started_at=starts_shortly_after,
        )
        resolved = BalancePredictionService.resolve_for_match(db_session, match)
        assert resolved == 1

        calibration = BalancePredictionService.get_calibration(
            db_session, method="mmr_v1"
        )
        assert calibration["mmr_v1"]["count"] == 1
        assert calibration["mmr_v1"]["bins"][0]["avg_predicted"] == pytest.approx(
            0.60
        )


class TestResolutionTiming:
    def _suggest(self, db_session, player_factory, prefix, method="mmr_v2"):
        players = [player_factory(name=f"{prefix}{i}") for i in range(1, 5)]
        team1_ids, team2_ids = [players[0].id, players[1].id], [players[2].id, players[3].id]
        prediction = BalancePredictionService.record_suggestion(
            db_session, method=method, rank=1, team1_ids=team1_ids,
            team2_ids=team2_ids, predicted_team1_win_prob=0.5,
        )
        db_session.commit()
        return prediction, team1_ids, team2_ids

    def test_current_capture_method_resolves_against_the_game_it_started(
        self, db_session, player_factory
    ):
        prediction, team1_ids, team2_ids = self._suggest(db_session, player_factory, "D")
        match = _make_match(db_session, team1_ids, team2_ids, team1_won=True,
                            started_at=prediction.created_at + timedelta(minutes=3))

        assert BalancePredictionService.resolve_for_match(db_session, match) == 1
        assert prediction.match_id == match.id
        assert prediction.team1_won == 1

    def test_earlier_game_uploaded_late_cannot_claim_a_newer_suggestion(
        self, db_session, player_factory
    ):
        prediction, team1_ids, team2_ids = self._suggest(db_session, player_factory, "E")
        earlier_game = _make_match(db_session, team1_ids, team2_ids, team1_won=True,
                                   started_at=prediction.created_at - GAME_LENGTH)

        assert BalancePredictionService.resolve_for_match(db_session, earlier_game) == 0
        assert not prediction.resolved

    def test_rematch_after_the_suggested_game_is_not_attributed_to_it(
        self, db_session, player_factory
    ):
        prediction, team1_ids, team2_ids = self._suggest(db_session, player_factory, "F")
        rematch = _make_match(db_session, team1_ids, team2_ids, team1_won=False,
                              started_at=prediction.created_at + GAME_LENGTH + timedelta(minutes=3))

        assert BalancePredictionService.resolve_for_match(db_session, rematch) == 0
        assert not prediction.resolved

    def test_game_without_a_duration_is_never_attributed(self, db_session, player_factory):
        prediction, team1_ids, team2_ids = self._suggest(db_session, player_factory, "G")
        match = _make_match(db_session, team1_ids, team2_ids, team1_won=True,
                            started_at=prediction.created_at + timedelta(minutes=3))
        match.duration_seconds = 0
        db_session.commit()

        assert BalancePredictionService.resolve_for_match(db_session, match) == 0
        assert not prediction.resolved
