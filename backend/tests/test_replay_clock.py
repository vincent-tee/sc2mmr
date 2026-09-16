"""Tests for the game-loop-to-real-second conversion fix.

sc2reader's event.second assumes a fixed 16 loops/second, which reads wrong
on faster-than-default replays -- confirmed empirically on real replay files
in docs/reviews/2026-09-15-replay-metrics-review.md (frame/duration ratios
of ~22.4 loops/second, not 16).
"""
from types import SimpleNamespace

from app.replay_clock import frame_to_real_second, real_second, event_real_second


def test_frame_to_real_second_uses_replays_own_ratio():
    # 17529 frames over a 782-second replay (one of the review's real
    # samples) -- confirms this is NOT the same as frame/16.
    result = frame_to_real_second(17529, duration_seconds=782, total_frames=17529)
    assert result == 782  # by construction: end-of-replay frame maps to end-of-replay second
    # A frame at the midpoint should map to roughly the midpoint in real time,
    # not to (frame/16), which would overshoot the real duration.
    midpoint = frame_to_real_second(17529 // 2, duration_seconds=782, total_frames=17529)
    assert abs(midpoint - 391) < 1
    naive_wrong_value = (17529 // 2) / 16.0
    assert naive_wrong_value > 391 + 100  # the old bug overshoots by a large margin


def test_frame_to_real_second_falls_back_without_duration_data():
    # No total_frames/duration available -- fall back to the old (known
    # imperfect) rate rather than crashing or dividing by zero.
    assert frame_to_real_second(160, duration_seconds=0, total_frames=None) == 10.0
    assert frame_to_real_second(160, duration_seconds=100, total_frames=0) == 10.0


def test_real_second_reads_replay_attributes():
    replay = SimpleNamespace(frames=17529, game_length=SimpleNamespace(seconds=782))
    assert abs(real_second(17529, replay) - 782) < 1e-9


def test_event_real_second_reads_frame_off_event():
    replay = SimpleNamespace(frames=17529, game_length=SimpleNamespace(seconds=782))
    event = SimpleNamespace(frame=17529)
    assert abs(event_real_second(event, replay) - 782) < 1e-9
