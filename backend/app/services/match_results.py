"""Reviewing, confirming and backfilling where each match's winner came from."""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from ..match_result import ResultSource, supply_favourite
from ..models import Match, MatchPlayer
from ..replay_parser import ReplayData, parse_replay
from . import replay_storage
from .derived_data import mark_stale

logger = logging.getLogger(__name__)


def stored_winner_team(match: Match) -> Optional[int]:
    winners = {int(mp.team_number) for mp in match.participants if mp.won}
    return winners.pop() if len(winners) == 1 else None


def disagreeing_recordings(match: Match, winner: Optional[int]) -> list[dict]:
    return [r for r in (match.result_evidence or {}).get("other_recordings", []) if r.get("winner_team") != winner]


@dataclass
class ReviewItem:
    match: Match
    winner_team: Optional[int]
    supply_favourite_team: Optional[int]
    supply_ratio: Optional[float]
    other_recordings_disagree: bool

    @property
    def conflicts(self) -> bool:
        supply_disagrees = self.supply_favourite_team is not None and self.supply_favourite_team != self.winner_team
        return self.other_recordings_disagree or supply_disagrees


def review_item(match: Match) -> ReviewItem:
    winner = stored_winner_team(match)
    favourite, ratio = supply_favourite(match.result_evidence)
    return ReviewItem(match, winner, favourite, ratio, bool(disagreeing_recordings(match, winner)))


def review_queue(db: Session) -> list[ReviewItem]:
    """Suggested results, most doubtful first.

    Another recording disagreeing comes first, then games where the team with
    more supply at the common frame was not the one awarded the win (largest
    supply gap first), then the rest from closest to clearest.
    """
    items = [review_item(m) for m in db.query(Match).filter(Match.result_source == ResultSource.SUGGESTED)]

    def order(item: ReviewItem):
        ratio = item.supply_ratio or 1.0
        return (not item.other_recordings_disagree, not item.conflicts, -ratio if item.conflicts else ratio)

    return sorted(items, key=order)


class ResultChangeError(ValueError):
    pass


def confirm_result(db: Session, match: Match, winner_team: int, confirmed_by: str,
                   now: Optional[datetime] = None) -> bool:
    """Record a person's decision on who won; returns whether the winner changed.

    A changed winner rewrites the participants' results and schedules the
    rating rebuild, which replays every rating, achievement and prediction
    that depended on it.
    """
    if winner_team not in (1, 2):
        raise ResultChangeError("Winner must be team 1 or team 2")
    if not confirmed_by.strip():
        raise ResultChangeError("Say who is confirming the result")
    changed = stored_winner_team(match) != winner_team
    if changed:
        for mp in db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id):
            mp.won = int(mp.team_number == winner_team)
        mark_stale(db, f"Match {match.id} result changed to team {winner_team} by {confirmed_by.strip()}")
    match.result_source = ResultSource.CONFIRMED
    match.result_confirmed_by = confirmed_by.strip()
    match.result_confirmed_at = now or datetime.utcnow()
    db.commit()
    return changed


@dataclass
class BackfillReport:
    checked: int = 0
    replay: int = 0
    suggested: int = 0
    disagreeing_replay: int = 0
    missing_file: int = 0
    unreadable: int = 0
    remaining: int = 0
    last_id: int = 0
    samples: list[dict] = field(default_factory=list)


def classify_from_replay(match: Match, parsed: ReplayData) -> tuple[str, Optional[dict]]:
    """Decide a stored match's result source from a fresh parse of its replay.

    The stored winner is never changed here. When the replay states a result
    that differs from the stored one, the match is left suggested with that
    recording noted, so a person decides.
    """
    evidence = dict(parsed.result_evidence or {})
    if parsed.result_source != ResultSource.REPLAY:
        return ResultSource.SUGGESTED, evidence or None
    replay_winner = next(p.team for p in parsed.players if p.won)
    if replay_winner == stored_winner_team(match):
        return ResultSource.REPLAY, evidence or None
    evidence["other_recordings"] = [{"replay_hash": parsed.replay_hash, "winner_team": replay_winner}]
    return ResultSource.SUGGESTED, evidence


def backfill_result_sources(db: Session, limit: int, dry_run: bool, after_id: int = 0,
                            parse: Callable[[str], ReplayData] = parse_replay) -> BackfillReport:
    """Label up to `limit` unchecked matches; repeat until `remaining` is 0.

    Dry runs write nothing, so page through them with `after_id`.
    """
    report = BackfillReport()
    pending = (db.query(Match).filter(Match.result_source.is_(None), Match.id > after_id)
               .order_by(Match.id))
    for match in pending.limit(limit).all():
        report.checked += 1
        report.last_id = match.id
        stored = str(match.replay_file_path or "")
        local = replay_storage.materialize_local_copy(stored)
        if not local:
            report.missing_file += 1
            if not dry_run:
                match.result_source = ResultSource.UNKNOWN
            continue
        try:
            parsed = parse(local)
        except Exception as error:
            logger.warning("Could not re-read replay for match %s: %s", match.id, error)
            report.unreadable += 1
            if not dry_run:
                match.result_source = ResultSource.UNKNOWN
            continue
        finally:
            if local != stored:
                os.unlink(local)
        source, evidence = classify_from_replay(match, parsed)
        if source == ResultSource.REPLAY:
            report.replay += 1
        elif evidence and evidence.get("other_recordings"):
            report.disagreeing_replay += 1
        else:
            report.suggested += 1
        if len(report.samples) < 20 and source == ResultSource.SUGGESTED:
            report.samples.append({"match_id": match.id, "evidence": evidence})
        if not dry_run:
            match.result_source, match.result_evidence = source, evidence
    if not dry_run:
        db.commit()
    report.remaining = db.query(Match).filter(Match.result_source.is_(None)).count()
    return report

