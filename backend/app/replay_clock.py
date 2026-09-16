"""Correct game-loop-to-real-second conversion for replay events.

sc2reader's own `event.second` is computed internally as `frame >> 4`
(hardcoded 16 loops/second) and does not account for the replay's actual
game speed. Modern "Faster"-speed replays run at ~22.4 loops/second, so
`event.second` reads roughly 40% short (see
docs/reviews/2026-09-15-replay-metrics-review.md for the empirical
confirmation on two real replay files: frame counts of 17529/25744 against
real durations of 782/1149 seconds).

Rather than hardcoding a speed-to-loops table (values differ by client
version and the review found sc2reader's own expansion detection unreliable
for very new build numbers), this self-calibrates per replay from two
values sc2reader already gets right: total frame count and real duration.
"""


def frame_to_real_second(frame: int, duration_seconds: int, total_frames: int) -> float:
    """Core conversion: given a replay's own known total frames and real
    duration, convert any raw frame number to real elapsed seconds."""
    if not total_frames or not duration_seconds:
        return frame / 16.0  # no reliable duration; fall back to the old (known-imperfect) rate
    loops_per_second = total_frames / duration_seconds
    return frame / loops_per_second


def real_second(frame: int, replay) -> float:
    """Convert a raw game-loop frame count to real elapsed seconds, using
    this specific replay's own frame-count/duration ratio."""
    total_frames = getattr(replay, "frames", None)
    duration = getattr(replay, "game_length", None) or getattr(replay, "real_length", None)
    duration_seconds = getattr(duration, "seconds", None)
    return frame_to_real_second(frame, duration_seconds, total_frames)


def event_real_second(event, replay) -> float:
    """Same as real_second, reading the frame off an sc2reader event."""
    return real_second(event.frame, replay)
