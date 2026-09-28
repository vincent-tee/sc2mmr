"""Reviewing, confirming and backfilling where each match's winner came from."""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from ..match_result import ResultSource, supply_favourite, supply_winner
from ..models import Match, MatchPlayer
from ..replay_parser import ReplayData, WinnerDeterminationError, parse_replay
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
    """Games that need a person to say who won, most doubtful first.

    That is every unknown result, plus any suggested one that another
    recording of the same game contradicts. A suggested result from a clear
    supply lead is not listed: it already has a winner.
    """
    reviewable = Match.result_source.in_([ResultSource.UNKNOWN, ResultSource.SUGGESTED])
    items = [review_item(m) for m in db.query(Match).filter(reviewable)]
    needs_person = [item for item in items
                    if item.match.result_source == ResultSource.UNKNOWN or item.other_recordings_disagree]

    def order(item: ReviewItem):
        return (not item.other_recordings_disagree, -(item.supply_ratio or 1.0), item.match.played_at)

    return sorted(needs_person, key=order)


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
    changed = set_winner(db, match, winner_team,
                         f"Match {match.id} result changed to team {winner_team} by {confirmed_by.strip()}")
    match.result_source = ResultSource.CONFIRMED
    match.result_confirmed_by = confirmed_by.strip()
    match.result_confirmed_at = now or datetime.utcnow()
    db.commit()
    return changed


def set_winner(db: Session, match: Match, winner_team: Optional[int], reason: str) -> bool:
    """Rewrite the participants' results; returns whether they changed.

    No winner marks every participant as not having won, which leaves the game
    unrated. A change schedules the rating rebuild.
    """
    if stored_winner_team(match) == winner_team:
        return False
    for mp in db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id):
        mp.won = int(winner_team is not None and mp.team_number == winner_team)
    mark_stale(db, reason)
    return True


def settled_result(evidence: Optional[dict]) -> tuple[str, Optional[int]]:
    """Result source and winner for a game whose replay records no result.

    Another recording that states the result settles it; otherwise a clear
    supply lead does; otherwise nobody knows.
    """
    recorded = {r.get("winner_team") for r in (evidence or {}).get("other_recordings", [])}
    if len(recorded) == 1 and None not in recorded:
        return ResultSource.REPLAY, recorded.pop()
    winner = supply_winner(evidence)
    return (ResultSource.SUGGESTED, winner) if winner is not None else (ResultSource.UNKNOWN, None)


@dataclass
class SettleReport:
    checked: int = 0
    changed: list[dict] = field(default_factory=list)


def settle_unrecorded_results(db: Session, dry_run: bool) -> SettleReport:
    """Apply the winner rule to every stored game whose replay records no result."""
    report = SettleReport()
    reviewable = Match.result_source.in_([ResultSource.UNKNOWN, ResultSource.SUGGESTED])
    for match in db.query(Match).filter(reviewable).order_by(Match.id):
        report.checked += 1
        source, winner = settled_result(match.result_evidence)
        before = (match.result_source, stored_winner_team(match))
        if before == (source, winner):
            continue
        report.changed.append({"match_id": match.id, "from": {"source": before[0], "winner_team": before[1]},
                               "to": {"source": source, "winner_team": winner}})
        if not dry_run:
            set_winner(db, match, winner, f"Match {match.id} result settled by the winner rule")
            match.result_source = source
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return report


@dataclass
class BackfillReport:
    checked: int = 0
    replay: int = 0
    suggested: int = 0
    unknown: int = 0
    winner_changes: int = 0
    missing_file: int = 0
    unreadable: int = 0
    remaining: int = 0
    last_id: int = 0
    samples: list[dict] = field(default_factory=list)


def result_from_replay(parsed: ReplayData) -> tuple[str, Optional[int]]:
    """Result source and winner from a fresh parse of a stored game's replay."""
    return parsed.result_source, next(p.team for p in parsed.players if p.won)


def backfill_result_sources(db: Session, limit: int, dry_run: bool, after_id: int = 0,
                            parse: Callable[[str], ReplayData] = parse_replay,
                            recheck_unknown: bool = False) -> BackfillReport:
    """Label up to `limit` unchecked matches; repeat until `remaining` is 0.

    Dry runs write nothing, so page through them with `after_id`.
    """
    report = BackfillReport()
    unchecked = Match.result_source.is_(None)
    if recheck_unknown:
        unchecked = unchecked | (Match.result_source == ResultSource.UNKNOWN)
    pending = db.query(Match).filter(unchecked, Match.id > after_id).order_by(Match.id)
    for match in pending.limit(limit).all():
        report.checked += 1
        report.last_id = match.id
        stored = str(match.replay_file_path or "")
        local = replay_storage.materialize_match_replay(stored, match.replay_hash)
        if not local:
            report.missing_file += 1
            continue
        try:
            parsed = parse(local)
            evidence = parsed.result_evidence
            source, winner = result_from_replay(parsed)
        except WinnerDeterminationError as no_clear_winner:
            evidence = no_clear_winner.team_stats or None
            source, winner = ResultSource.UNKNOWN, None
        except Exception as error:
            logger.warning("Could not re-read replay for match %s: %s", match.id, error)
            report.unreadable += 1
            continue
        finally:
            if local != stored:
                os.unlink(local)
        if source == ResultSource.REPLAY:
            report.replay += 1
        elif source == ResultSource.SUGGESTED:
            report.suggested += 1
        else:
            report.unknown += 1
        changes_winner = winner != stored_winner_team(match)
        report.winner_changes += changes_winner
        if len(report.samples) < 20 and (changes_winner or source == ResultSource.UNKNOWN):
            report.samples.append({"match_id": match.id, "source": source, "winner_team": winner,
                                   "stored_winner_team": stored_winner_team(match), "evidence": evidence})
        if not dry_run:
            set_winner(db, match, winner, f"Match {match.id} result re-read from its replay")
            match.result_source, match.result_evidence = source, evidence
    if not dry_run:
        db.commit()
    report.remaining = db.query(Match).filter(unchecked).count()
    return report

