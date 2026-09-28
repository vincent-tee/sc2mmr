"""Shared rules for turning replay events into per-player stats."""

from typing import Dict, Iterable, List, Optional, Tuple


def supply_blocked_seconds(snapshots: List[tuple]) -> int:
    """Seconds spent supply blocked, from (real_second, blocked) stats snapshots.

    Each blocked snapshot counts until the player's next snapshot, so the
    real sampling interval is used once and a short final (departure)
    interval only adds what actually elapsed.
    """
    ordered = sorted(snapshots)
    return round(sum(later[0] - earlier[0] for earlier, later in zip(ordered, ordered[1:]) if earlier[1]))


def is_opponent_kill(killer_team: Optional[int], victim_team: Optional[int]) -> bool:
    return killer_team is not None and victim_team is not None and killer_team != victim_team


class CutoffReason:
    LEFT = "left"  # the player left before the recording ended
    RECORDING_END = "recording_end"  # still in the game when the recording stopped


def stats_cutoffs(leave_events: Iterable[Tuple[int, Optional[int]]], participant_pids: Iterable[int],
                  last_frame: int) -> Dict[int, Tuple[int, str]]:
    """Each participant's (cutoff frame, reason): stats count up to this frame.

    `leave_events` are (frame, pid) with the pid already resolved to the
    player's own id (sc2reader's `event.player`), since raw game-event ids
    differ from tracker ids. Observers are not participants, and leaving on
    the recording's final frame is the recording ending, not a departure.
    """
    cutoffs = {pid: (last_frame, CutoffReason.RECORDING_END) for pid in participant_pids}
    for frame, pid in leave_events:
        if pid in cutoffs and frame < last_frame and frame < cutoffs[pid][0]:
            cutoffs[pid] = (frame, CutoffReason.LEFT)
    return cutoffs


def replay_stats_cutoffs(replay) -> Dict[int, Tuple[int, str]]:
    leaves = [(e.frame, getattr(getattr(e, "player", None), "pid", None))
              for e in getattr(replay, "game_events", []) if e.name == "PlayerLeaveEvent"]
    return stats_cutoffs(leaves, [p.pid for p in replay.players], int(getattr(replay, "frames", 0) or 0))


def counts_for(pid: Optional[int], frame: int, cutoffs: Dict[int, Tuple[int, str]]) -> bool:
    """Whether an event at `frame` still counts toward `pid`'s own stats."""
    return pid not in cutoffs or frame <= cutoffs[pid][0]
