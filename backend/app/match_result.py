"""Where a match's winner came from, and the evidence behind a suggested winner.

A replay only sometimes records who won. When it doesn't, the parser suggests a
winner from team stats; that suggestion is rated like any other result but is
labelled so people can confirm or correct it.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


class ResultSource:
    REPLAY = "replay"  # the replay file itself records the result
    SUGGESTED = "suggested"  # inferred from team stats because the replay has no result
    CONFIRMED = "confirmed"  # chosen or confirmed by a person
    UNKNOWN = "unknown"  # the stored replay could not be re-read to check


@dataclass(frozen=True)
class StatsSnapshot:
    player_id: int
    team: int
    frame: int
    supply_used: float


def supply_at_common_frame(snapshots: Iterable[StatsSnapshot]) -> Optional[dict]:
    """Team supply at the latest moment every participant has a stats snapshot.

    Recordings don't end at the same frame for everyone (the recorder's last
    snapshot can be seconds after the others), so comparing each player's final
    snapshot would compare different moments.
    """
    by_player: Dict[int, List[StatsSnapshot]] = {}
    for snapshot in snapshots:
        by_player.setdefault(snapshot.player_id, []).append(snapshot)
    if not by_player:
        return None

    common_frame = min(max(s.frame for s in player) for player in by_player.values())
    team_supply: Dict[int, float] = {}
    for player in by_player.values():
        at_or_before = [s for s in player if s.frame <= common_frame]
        if not at_or_before:
            continue
        latest = max(at_or_before, key=lambda s: s.frame)
        team_supply[latest.team] = team_supply.get(latest.team, 0.0) + latest.supply_used
    return {"frame": common_frame, "team_supply": {str(team): supply for team, supply in sorted(team_supply.items())}}


def supply_favourite(evidence: Optional[dict]) -> Tuple[Optional[int], Optional[float]]:
    """The team with more supply at the common frame, and how many times more it had."""
    if not evidence or not evidence.get("team_supply"):
        return None, None
    supply = {int(team): value for team, value in evidence["team_supply"].items()}
    if len(supply) != 2:
        return None, None
    (team_a, supply_a), (team_b, supply_b) = sorted(supply.items(), key=lambda item: -item[1])
    if supply_a == supply_b:
        return None, 1.0
    return team_a, (supply_a / supply_b if supply_b > 0 else float("inf"))
