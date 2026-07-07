"""
Tests for the s2protocol patch-resilience fallback: triggers only when
sc2reader fails to load a replay, and produces data equivalent to what
sc2reader would have for the same file.

Uses a real local replay file so the field-mapping (name cleaning, team
indexing, race, win/loss, duration) is checked against ground truth from
sc2reader's own parse of the identical file, not just mocked structures.
"""
import glob
import os
from unittest.mock import patch

import pytest

from app.models import GameMode, Race
from app.replay_parser import ReplayParseError, parse_replay
from app.s2protocol_fallback import (
    _clean_name,
    _decode_race,
    _determine_game_mode,
    parse_replay_s2protocol,
)
from app.replay_parser import PlayerData

REPLAYS_DIR = os.path.join(os.path.dirname(__file__), "..", "replays")


def _first_real_replay():
    files = sorted(glob.glob(os.path.join(REPLAYS_DIR, "*.SC2Replay")))
    if not files:
        pytest.skip("No local replay files available for s2protocol fallback test")
    return files[0]


class TestFieldDecoding:
    def test_clean_name_strips_clan_tag_and_space_marker(self):
        raw = b"&lt;FGAM&gt;<sp/>ChrisO"
        assert _clean_name(raw) == "ChrisO"

    def test_clean_name_handles_no_clan_tag(self):
        assert _clean_name(b"PlainName") == "PlainName"

    def test_clean_name_handles_none(self):
        assert _clean_name(None) == "Unknown"

    def test_decode_race(self):
        assert _decode_race(b"Terran") == Race.TERRAN
        assert _decode_race(b"Protoss") == Race.PROTOSS
        assert _decode_race(b"Zerg") == Race.ZERG
        assert _decode_race(b"") == Race.RANDOM
        assert _decode_race(None) == Race.RANDOM

    def test_determine_game_mode_from_player_data(self):
        players = [
            PlayerData(name="a", race=Race.TERRAN, team=1, won=True),
            PlayerData(name="b", race=Race.TERRAN, team=1, won=True),
            PlayerData(name="c", race=Race.ZERG, team=2, won=False),
            PlayerData(name="d", race=Race.ZERG, team=2, won=False),
        ]
        assert _determine_game_mode(players) == GameMode.TWO_V_TWO


class TestFallbackAgainstRealReplay:
    """Cross-checks the fallback's output against sc2reader parsing the same file."""

    def test_matches_sc2reader_ground_truth(self):
        sc2reader = pytest.importorskip("sc2reader")
        f = _first_real_replay()

        replay = sc2reader.load_replay(f, load_level=2)
        expected_duration = replay.game_length.seconds
        expected_players = {
            p.name: (p.team_id, str(p.play_race), p.result == "Win")
            for p in replay.players
            if getattr(p, "is_human", False)
        }

        data = parse_replay_s2protocol(f)

        # Duration from game-loop-rate conversion should be within a couple
        # seconds of sc2reader's own duration for the same file.
        assert abs(data.duration_seconds - expected_duration) <= 2

        assert len(data.players) == len(expected_players)
        for p in data.players:
            assert p.name in expected_players
            expected_team, expected_race, expected_won = expected_players[p.name]
            assert p.team == expected_team
            assert expected_race.startswith(str(p.race.value)[:4])
            assert p.won == expected_won

    def test_manual_winner_override(self):
        f = _first_real_replay()
        data = parse_replay_s2protocol(f, manual_winner_team=2)
        team1_players = [p for p in data.players if p.team == 1]
        team2_players = [p for p in data.players if p.team == 2]
        assert all(not p.won for p in team1_players)
        assert all(p.won for p in team2_players)


class TestParseReplayFallbackTrigger:
    def test_falls_back_when_sc2reader_fails(self):
        f = _first_real_replay()
        with patch(
            "app.replay_parser.sc2reader.load_replay",
            side_effect=RuntimeError("unrecognized protocol version"),
        ):
            data = parse_replay(f)
        assert len(data.players) >= 2
        assert data.map_name != "Unknown Map"

    def test_raises_original_error_when_both_fail(self):
        f = _first_real_replay()
        with patch(
            "app.replay_parser.sc2reader.load_replay",
            side_effect=RuntimeError("sc2reader boom"),
        ), patch(
            "app.s2protocol_fallback.parse_replay_s2protocol",
            side_effect=RuntimeError("s2protocol also boom"),
        ):
            with pytest.raises(ReplayParseError, match="sc2reader boom"):
                parse_replay(f)

    def test_does_not_trigger_when_sc2reader_succeeds(self):
        f = _first_real_replay()
        with patch("app.s2protocol_fallback.parse_replay_s2protocol") as mock_fallback:
            parse_replay(f)
        mock_fallback.assert_not_called()
