from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import Match
from ..services.match_results import (
    ResultChangeError, ReviewItem, backfill_result_sources, confirm_result, review_item, review_queue,
)

router = APIRouter(prefix="/match-results", tags=["match results"])


class TeamRoster(BaseModel):
    team: int
    players: List[str]


class ReviewItemResponse(BaseModel):
    match_id: int
    played_at: datetime
    map_name: str
    duration_seconds: int
    result_source: Optional[str]
    winner_team: Optional[int]
    supply_frame: Optional[int]
    team_supply: dict
    supply_favourite_team: Optional[int]
    supply_ratio: Optional[float]
    other_recordings: List[dict]
    conflicts: bool
    rosters: List[TeamRoster]


def to_response(item: ReviewItem) -> ReviewItemResponse:
    match = item.match
    evidence = match.result_evidence or {}
    rosters = {}
    for mp in match.participants:
        rosters.setdefault(int(mp.team_number), []).append(mp.player.name)
    return ReviewItemResponse(
        match_id=match.id, played_at=match.played_at, map_name=match.map_name,
        duration_seconds=match.duration_seconds, result_source=match.result_source,
        winner_team=item.winner_team, supply_frame=evidence.get("frame"),
        team_supply=evidence.get("team_supply", {}),
        supply_favourite_team=item.supply_favourite_team,
        supply_ratio=None if item.supply_ratio in (None, float("inf")) else round(item.supply_ratio, 2),
        other_recordings=evidence.get("other_recordings", []), conflicts=item.conflicts,
        rosters=[TeamRoster(team=team, players=sorted(names)) for team, names in sorted(rosters.items())],
    )


class ReviewQueueResponse(BaseModel):
    total: int
    conflicts: int
    unchecked: int
    items: List[ReviewItemResponse]


@router.get("/review", response_model=ReviewQueueResponse)
def get_review_queue(db: Session = Depends(get_db)):
    items = review_queue(db)
    return ReviewQueueResponse(
        total=len(items), conflicts=sum(item.conflicts for item in items),
        unchecked=db.query(Match).filter(Match.result_source.is_(None)).count(),
        items=[to_response(item) for item in items],
    )


class ConfirmResultRequest(BaseModel):
    winner_team: int
    confirmed_by: str


class ConfirmResultResponse(BaseModel):
    changed: bool
    item: ReviewItemResponse


@router.post("/{match_id}/confirm", response_model=ConfirmResultResponse,
             dependencies=[Depends(require_admin)])
def confirm_match_result(match_id: int, request: ConfirmResultRequest, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    try:
        changed = confirm_result(db, match, request.winner_team, request.confirmed_by)
    except ResultChangeError as error:
        raise HTTPException(status_code=400, detail=str(error))
    db.refresh(match)
    return ConfirmResultResponse(changed=changed, item=to_response(review_item(match)))


class BackfillResponse(BaseModel):
    dry_run: bool
    checked: int
    replay: int
    suggested: int
    disagreeing_replay: int
    missing_file: int
    unreadable: int
    remaining: int
    last_id: int
    samples: List[dict]


@router.post("/backfill", response_model=BackfillResponse, dependencies=[Depends(require_admin)])
def backfill(limit: int = Query(25, ge=1, le=200), dry_run: bool = True, after_id: int = 0,
             recheck_unknown: bool = False, db: Session = Depends(get_db)):
    report = backfill_result_sources(db, limit=limit, dry_run=dry_run, after_id=after_id,
                                     recheck_unknown=recheck_unknown)
    return BackfillResponse(dry_run=dry_run, **report.__dict__)

