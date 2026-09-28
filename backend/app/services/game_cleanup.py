from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..models import Match
from .derived_data import mark_stale
from .ingestion import MIN_GAME_SECONDS, game_started_at


@dataclass
class DuplicateCopy:
    kept_match_id: int
    removed_match_id: int
    winners_agree: bool


@dataclass
class CleanupPlan:
    aborted_match_ids: list[int] = field(default_factory=list)
    duplicate_copies: list[DuplicateCopy] = field(default_factory=list)

    @property
    def match_ids_to_remove(self) -> list[int]:
        return self.aborted_match_ids + [c.removed_match_id for c in self.duplicate_copies]


def winning_player_ids(match: Match) -> set[int]:
    return {mp.player_id for mp in match.participants if mp.won}


def more_complete_copy_first(a: Match, b: Match) -> tuple[Match, Match]:
    return (a, b) if (a.duration_seconds or 0, -a.id) >= (b.duration_seconds or 0, -b.id) else (b, a)


def plan_cleanup(db: Session) -> CleanupPlan:
    plan = CleanupPlan()
    played = db.query(Match).filter(Match.played_at.isnot(None)).all()
    plan.aborted_match_ids = sorted(m.id for m in played if (m.duration_seconds or 0) < MIN_GAME_SECONDS)
    aborted = set(plan.aborted_match_ids)
    games = sorted((m for m in played if m.id not in aborted),
                   key=lambda m: (game_started_at(m.played_at, m.duration_seconds), m.id))
    rosters = {m.id: {mp.player_id for mp in m.participants} for m in games}
    removed: set[int] = set()
    for i, first in enumerate(games):
        if first.id in removed:
            continue
        for second in games[i + 1:]:
            if game_started_at(second.played_at, second.duration_seconds) >= first.played_at:
                break
            if second.id in removed or second.map_name != first.map_name or rosters[second.id] != rosters[first.id]:
                continue
            kept, dropped = more_complete_copy_first(first, second)
            plan.duplicate_copies.append(DuplicateCopy(
                kept_match_id=kept.id, removed_match_id=dropped.id,
                winners_agree=winning_player_ids(kept) == winning_player_ids(dropped),
            ))
            removed.add(dropped.id)
            if dropped is first:
                break
    return plan


def remove_matches(db: Session, match_ids: list[int]) -> int:
    removed = db.query(Match).filter(Match.id.in_(match_ids)).delete(synchronize_session=False)
    if removed:
        mark_stale(db, f"Removed {removed} duplicate or aborted games")
    db.commit()
    db.expire_all()
    return removed
