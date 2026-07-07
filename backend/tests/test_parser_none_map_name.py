"""
Regression tests for the map_name=None crash.

sc2reader can set replay.map_name (and Player.name) to None on partial or
corrupt replays. getattr(obj, "attr", default) only substitutes the default
when the attribute is *missing*, not when it exists and is None — so the old
code crashed with `'NoneType' object has no attribute 'lower'` inside
calculate_game_fingerprint. This accounted for a chunk of historical
failed_uploads (error_type=OTHER) that should instead have processed as
"Unknown Map".
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.replay_parser import calculate_game_fingerprint, parse_replay
from app.services.unified_parser import UnifiedParser


def make_fake_player(name="TestPlayer", team_id=1, result="Win", is_human=True):
    p = MagicMock()
    p.name = name
    p.team_id = team_id
    p.result = result
    p.is_human = is_human
    p.play_race = "Terran"
    p.pid = team_id
    p.stats = None
    p.avg_apm = 100.0
    p.clan_tag = None
    return p


def make_fake_replay(map_name, players):
    replay = MagicMock()
    replay.map_name = map_name
    replay.utc_date = datetime.utcnow()
    replay.game_length = MagicMock(seconds=600)
    replay.players = players
    replay.events = []
    replay.tracker_events = []
    replay.game_events = []
    return replay


class TestFingerprintNoneSafety:
    def test_none_map_name_does_not_crash(self):
        with pytest.raises(AttributeError):
            # Sanity check: this is the exact crash the fix prevents
            None.lower()

        # calculate_game_fingerprint itself still requires a str; the fix is
        # upstream (parse_replay/UnifiedParser resolving None -> "Unknown Map")
        fp = calculate_game_fingerprint("Unknown Map", datetime.utcnow(), ["a", "b"])
        assert len(fp) == 64


class TestParseReplayMapNameFallback:
    def test_none_map_name_resolves_to_unknown_map(self):
        players = [
            make_fake_player("P1", team_id=1),
            make_fake_player("P2", team_id=1),
            make_fake_player("P3", team_id=2),
            make_fake_player("P4", team_id=2),
        ]
        replay = make_fake_replay(map_name=None, players=players)

        with patch("app.replay_parser.sc2reader.load_replay", return_value=replay), \
             patch("app.replay_parser.calculate_replay_hash", return_value="deadbeef"):
            data = parse_replay("/fake/path.SC2Replay")

        assert data.map_name == "Unknown Map"

    def test_missing_map_name_attribute_also_resolves(self):
        players = [
            make_fake_player("P1", team_id=1),
            make_fake_player("P2", team_id=1),
            make_fake_player("P3", team_id=2),
            make_fake_player("P4", team_id=2),
        ]
        replay = make_fake_replay(map_name=None, players=players)
        del replay.map_name  # simulate attribute genuinely absent

        with patch("app.replay_parser.sc2reader.load_replay", return_value=replay), \
             patch("app.replay_parser.calculate_replay_hash", return_value="deadbeef"):
            data = parse_replay("/fake/path.SC2Replay")

        assert data.map_name == "Unknown Map"


class TestUnifiedParserMapNameFallback:
    def test_clean_name_handles_none(self):
        parser = UnifiedParser()
        player = MagicMock()
        player.name = None
        player.clan_tag = None
        assert parser._clean_name(player) == "Unknown"
