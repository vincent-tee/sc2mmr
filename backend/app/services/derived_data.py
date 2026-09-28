import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import trueskill
from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from ..impact_service import ImpactService
from ..models import DerivedDataState, Match, MatchPlayer, Player
from ..rating_policy import win_probability

REBUILD_DEBOUNCE = timedelta(minutes=2)
ABANDONED_REBUILD_AFTER = timedelta(minutes=10)

logger = logging.getLogger(__name__)


@dataclass
class RatedMatch:
    match: Match
    teams: dict[int, list[MatchPlayer]]
    winning_team: int


def rated_matches(db: Session) -> list[RatedMatch]:
    rated = []
    for match in db.query(Match).order_by(Match.played_at.asc(), Match.id.asc()).all():
        participants = db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        teams = {1: [mp for mp in participants if mp.team_number == 1],
                 2: [mp for mp in participants if mp.team_number == 2]}
        winners = {mp.team_number for mp in participants if mp.won}
        if teams[1] and teams[2] and len(winners) == 1:
            rated.append(RatedMatch(match, teams, winners.pop()))
    return rated


def rebuild_match_win_probabilities(matches: list[RatedMatch]) -> None:
    for rated in matches:
        team1, team2 = ([trueskill.Rating(mu=mp.mu_before, sigma=mp.sigma_before) for mp in rated.teams[t]]
                        for t in (1, 2))
        team1_win_probability = win_probability(team1, team2)
        rated.match.predicted_team1_win_prob = team1_win_probability
        rated.match.predicted_team2_win_prob = 1.0 - team1_win_probability


def rebuild_metric_averages(db: Session) -> None:
    for (player_id,) in db.query(Player.id).all():
        ImpactService.update_player_averages(db, player_id)


def rebuild_achievements(db: Session) -> None:
    from .achievement_service import AchievementService

    for (player_id,) in db.query(Player.id).filter(Player.total_games > 0).all():
        AchievementService.check_and_award_all(db, player_id)


def reresolve_balance_predictions(db: Session, matches: list[RatedMatch]) -> None:
    from .balance_capture import BalancePredictionService

    for rated in matches:
        BalancePredictionService.resolve_for_match(db, rated.match)


def rebuild_all(db: Session) -> dict:
    from .rating_recalculation import recalculate_ratings_in_place
    from .rivalry_service import RivalryService

    rating_stats = recalculate_ratings_in_place(db)
    matches = rated_matches(db)
    rebuild_match_win_probabilities(matches)
    rebuild_metric_averages(db)
    RivalryService.calculate_all_rivalries(db)
    rebuild_achievements(db)
    reresolve_balance_predictions(db, matches)
    return rating_stats


def derived_data_state(db: Session) -> DerivedDataState:
    state = db.get(DerivedDataState, 1)
    if state is None:
        state = DerivedDataState(id=1)
        db.add(state)
        db.flush()
    return state


def mark_stale(db: Session, reason: str, now: Optional[datetime] = None) -> None:
    now = now or datetime.utcnow()
    state = derived_data_state(db)
    if state.stale_since is None:
        state.stale_since = now
    state.stale_reason = reason
    state.rebuild_due_at = now + REBUILD_DEBOUNCE
    db.flush()


def claim_rebuild(db: Session, now: datetime, only_when_due: bool) -> bool:
    derived_data_state(db)
    claim = (
        update(DerivedDataState)
        .where(DerivedDataState.id == 1)
        .where(or_(DerivedDataState.rebuilding_started_at.is_(None),
                   DerivedDataState.rebuilding_started_at < now - ABANDONED_REBUILD_AFTER))
    )
    if only_when_due:
        claim = claim.where(DerivedDataState.stale_since.isnot(None),
                            DerivedDataState.rebuild_due_at <= now)
    claimed = db.execute(claim.values(rebuilding_started_at=now)).rowcount == 1
    db.commit()
    return claimed


def rebuild_derived_data(db: Session, now: Optional[datetime] = None,
                         only_when_due: bool = False) -> Optional[dict]:
    from .ingestion import ingestion_transaction

    now = now or datetime.utcnow()
    if not claim_rebuild(db, now, only_when_due):
        return None
    started = time.monotonic()
    try:
        with ingestion_transaction(db) as work:
            stats = rebuild_all(work)
            state = derived_data_state(work)
            state.stale_since = None
            state.stale_reason = None
            state.rebuild_due_at = None
            state.rebuilding_started_at = None
            state.last_rebuilt_at = datetime.utcnow()
            state.last_rebuild_seconds = round(time.monotonic() - started, 2)
            state.last_error = None
        return stats
    except Exception as error:
        logger.exception("Derived data rebuild failed")
        state = derived_data_state(db)
        state.rebuilding_started_at = None
        state.last_error = f"{type(error).__name__}: {error}"[:500]
        if state.stale_since is not None:
            state.rebuild_due_at = datetime.utcnow() + REBUILD_DEBOUNCE
        db.commit()
        raise


def rebuild_if_due(db: Session, now: Optional[datetime] = None) -> Optional[dict]:
    return rebuild_derived_data(db, now, only_when_due=True)
