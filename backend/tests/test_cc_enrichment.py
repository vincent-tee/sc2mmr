"""
Tests for CommandCenter enrichment: gating, pid mapping, and the hard-timeout
isolation that protects against a hung SC2 engine process.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models import GameMode, Match, MatchPlayer, PlayerMatchMetrics, Race
from app.services import cc_enrichment


class TestEnrichmentGating:
    def test_disabled_by_default_returns_zero(self, db_session, player_factory):
        # settings.upload_cc_enrichment_enabled defaults to False
        players = [player_factory(name=f"gate{i}") for i in range(4)]
        match = Match(
            played_at=datetime.utcnow(),
            game_mode=GameMode.TWO_V_TWO,
            map_name="Test",
            duration_seconds=600,
            replay_file_path="/fake/path.SC2Replay",
        )
        db_session.add(match)
        db_session.flush()
        for i, p in enumerate(players):
            db_session.add(
                MatchPlayer(
                    match_id=match.id, player_id=p.id,
                    team_number=1 if i < 2 else 2, race=Race.TERRAN,
                    won=1, mu_before=25, sigma_before=8, mu_after=25, sigma_after=8,
                )
            )
        db_session.commit()

        assert cc_enrichment.enrich_match_with_cc_metrics(db_session, match.id) == 0

    def test_no_replay_file_path_returns_zero(self, db_session):
        with patch("app.services.cc_enrichment.settings") as mock_settings:
            mock_settings.upload_cc_enrichment_enabled = True
            match = Match(
                played_at=datetime.utcnow(), game_mode=GameMode.TWO_V_TWO,
                map_name="Test", duration_seconds=600, replay_file_path=None,
            )
            db_session.add(match)
            db_session.commit()
            assert cc_enrichment.enrich_match_with_cc_metrics(db_session, match.id) == 0

    def test_unavailable_engine_returns_zero(self, db_session):
        with patch("app.services.cc_enrichment.settings") as mock_settings, \
             patch("app.services.cc_enrichment.is_commandcenter_available", return_value=False):
            mock_settings.upload_cc_enrichment_enabled = True
            match = Match(
                played_at=datetime.utcnow(), game_mode=GameMode.TWO_V_TWO,
                map_name="Test", duration_seconds=600,
                replay_file_path="/fake/path.SC2Replay",
            )
            db_session.add(match)
            db_session.commit()
            assert cc_enrichment.enrich_match_with_cc_metrics(db_session, match.id) == 0


class TestPidMapping:
    def test_maps_by_name_not_row_order(self, db_session, player_factory):
        """
        Regression: the pid->player mapping must come from re-parsing the
        replay's authoritative player order, not from assuming MatchPlayer
        DB row order matches the engine's internal pid order (the latter is
        what the older backfill script assumed and is not guaranteed).
        """
        # DB insertion order is deliberately reversed relative to "replay" pid order
        p_a = player_factory(name="Alice")
        p_b = player_factory(name="Bob")
        match = Match(
            played_at=datetime.utcnow(), game_mode=GameMode.TWO_V_TWO,
            map_name="Test", duration_seconds=600,
            replay_file_path="/fake/path.SC2Replay",
        )
        db_session.add(match)
        db_session.flush()
        # Insert Bob's MatchPlayer row before Alice's (reversed vs. replay pid 1=Alice, 2=Bob)
        db_session.add(
            MatchPlayer(
                match_id=match.id, player_id=p_b.id, team_number=2,
                race=Race.ZERG, won=0, mu_before=25, sigma_before=8,
                mu_after=25, sigma_after=8,
            )
        )
        db_session.add(
            MatchPlayer(
                match_id=match.id, player_id=p_a.id, team_number=1,
                race=Race.TERRAN, won=1, mu_before=25, sigma_before=8,
                mu_after=25, sigma_after=8,
            )
        )
        db_session.commit()

        with patch("app.services.cc_enrichment.settings") as mock_settings, \
             patch("app.services.cc_enrichment.is_commandcenter_available", return_value=True), \
             patch.object(cc_enrichment, "_sc2_pid_to_name", return_value={1: "Alice", 2: "Bob"}), \
             patch.object(cc_enrichment, "parse_replay_isolated") as mock_parse:
            mock_settings.upload_cc_enrichment_enabled = True
            mock_parse.return_value = {
                1: {"collected_minerals": 1000, "total_damage_dealt": 500,
                    "total_damage_taken": 100},
                2: {"collected_minerals": 2000, "total_damage_dealt": 900,
                    "total_damage_taken": 300},
            }
            updated = cc_enrichment.enrich_match_with_cc_metrics(db_session, match.id)

        assert updated == 2
        alice_mp = (
            db_session.query(MatchPlayer)
            .filter(MatchPlayer.match_id == match.id, MatchPlayer.player_id == p_a.id)
            .one()
        )
        bob_mp = (
            db_session.query(MatchPlayer)
            .filter(MatchPlayer.match_id == match.id, MatchPlayer.player_id == p_b.id)
            .one()
        )
        alice_metrics = (
            db_session.query(PlayerMatchMetrics)
            .filter(PlayerMatchMetrics.match_player_id == alice_mp.id)
            .one()
        )
        bob_metrics = (
            db_session.query(PlayerMatchMetrics)
            .filter(PlayerMatchMetrics.match_player_id == bob_mp.id)
            .one()
        )
        # pid 1 (Alice) -> 1000 minerals, regardless of DB row insertion order
        assert alice_metrics.minerals_collected == 1000
        assert bob_metrics.minerals_collected == 2000


class TestIsolatedParseHardTimeout:
    def test_hung_subprocess_is_killed_and_returns_none(self):
        """
        The SC2 engine can hang indefinitely inside a single coordinator
        update() call instead of returning (observed directly against a
        real replay: process printed "Waiting for connection..." forever
        after the engine itself had already fatally crashed). The soft
        between-call timeout inside CommandCenterParser can't catch that,
        so parse_replay_isolated must kill the child process from outside
        when join() times out while it's still alive.

        A real spawned subprocess won't pick up parent-process patches (it
        re-imports the module fresh), so this simulates the hang at the
        multiprocessing.Process level instead of relying on a real hung
        SC2 engine being present in the test environment.
        """
        from app.services import commandcenter_parser as ccp

        fake_proc = MagicMock()
        # alive after the hard-timeout join, still alive after terminate()
        # (escalation path), dead after kill()
        fake_proc.is_alive.side_effect = [True, True, False]
        fake_ctx = MagicMock()
        fake_ctx.Queue.return_value = MagicMock(empty=lambda: True)
        fake_ctx.Process.return_value = fake_proc

        with patch.object(ccp, "HAS_CC", True), \
             patch("multiprocessing.get_context", return_value=fake_ctx):
            result = ccp.parse_replay_isolated(
                "/fake/path.SC2Replay", num_players=2, hard_timeout=3
            )

        assert result is None
        fake_proc.terminate.assert_called_once()
        fake_proc.kill.assert_called_once()

    def test_unavailable_returns_none_immediately(self):
        from app.services import commandcenter_parser as ccp

        with patch.object(ccp, "HAS_CC", False):
            assert ccp.parse_replay_isolated("/fake/path.SC2Replay", num_players=2) is None
