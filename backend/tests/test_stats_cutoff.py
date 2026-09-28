import os
from pathlib import Path

import pytest

from app.metric_accounting import CutoffReason, counts_for, stats_cutoffs

FIXTURE_REPLAYS = Path(os.environ.get("SC2MMR_FIXTURE_REPLAYS", Path(__file__).resolve().parents[1] / "replays"))
MATCH_1168 = FIXTURE_REPLAYS / "361e31e8c6c844196005748299fc210a9f7740e66b877dff265ee049c6cf8da4.SC2Replay"
MATCH_1167 = FIXTURE_REPLAYS / "55a9525aac4d5dbd634d8c2beba24db2035ef487ef35e5caf069d6645f68d613.SC2Replay"
NORMAL_FINISH = FIXTURE_REPLAYS / "0064f1e60fb95eb7041b04ceae6bd3249339f987f540046a3a636692fea74586.SC2Replay"


def test_leaving_before_the_end_sets_a_cutoff_and_the_last_frame_does_not():
    cutoffs = stats_cutoffs([(35999, 4), (38542, 7), (38792, 1), (500, 99), (10, None)], [1, 4, 7], 38792)
    assert cutoffs == {
        1: (38792, CutoffReason.RECORDING_END),
        4: (35999, CutoffReason.LEFT),
        7: (38542, CutoffReason.LEFT),
    }


def test_events_count_up_to_and_including_the_cutoff_frame():
    cutoffs = {4: (35999, CutoffReason.LEFT)}
    assert counts_for(4, 35999, cutoffs)
    assert not counts_for(4, 36000, cutoffs)
    assert counts_for(9, 99999, cutoffs)


def parsed_players(path):
    if not path.exists():
        pytest.skip(f"replay fixture not available: {path.name}")
    from app.advanced_parser import parse_replay_advanced
    return {m.player_name: m for m in parse_replay_advanced(str(path), manual_winner_team=1).player_metrics}


def bank(metrics):
    return metrics.total_resources_collected - metrics.resources_spent


@pytest.mark.local_data
def test_players_who_left_are_frozen_at_their_departure():
    players = parsed_players(MATCH_1168)
    shadow, sirhc, chriso = players["ShadowDragon"], players["Sirhc"], players["ChrisO"]
    assert (shadow.stats_cutoff_reason, shadow.stats_cutoff_second) == (CutoffReason.LEFT, 1606)
    assert bank(shadow) == 2814
    assert shadow.army_value_killed == 12300
    assert (sirhc.stats_cutoff_reason, bank(sirhc)) == (CutoffReason.LEFT, 366)
    assert chriso.stats_cutoff_reason == CutoffReason.RECORDING_END
    assert bank(chriso) == 14776
    assert all(m.supply_block_seconds <= m.stats_cutoff_second for m in players.values())


@pytest.mark.local_data
def test_observers_leaving_do_not_create_player_departures():
    players = parsed_players(MATCH_1167)
    assert "shunmanFan" not in players
    assert all(m.stats_cutoff_reason is not None for m in players.values())


@pytest.mark.local_data
def test_a_normal_finish_only_trims_the_last_seconds():
    players = parsed_players(NORMAL_FINISH)
    assert {name: m.stats_cutoff_reason for name, m in players.items()} == {
        "ChrisO": CutoffReason.RECORDING_END, "shunmanFan": CutoffReason.LEFT,
        "Redevilz": CutoffReason.LEFT, "HahaLolo": CutoffReason.LEFT,
    }
    assert min(m.stats_cutoff_second for m in players.values()) >= 760
