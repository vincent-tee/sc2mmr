from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..services.derived_data import (
    ABANDONED_REBUILD_AFTER, derived_data_state, rebuild_derived_data, rebuild_if_due,
)
from ..services.game_cleanup import plan_cleanup, remove_matches
from ..services.metrics_backfill import apply_metrics_rows

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class DerivedDataStatus(BaseModel):
    stale: bool
    stale_since: Optional[datetime]
    stale_reason: Optional[str]
    rebuild_due_at: Optional[datetime]
    rebuilding: bool
    last_rebuilt_at: Optional[datetime]
    last_rebuild_seconds: Optional[float]
    last_error: Optional[str]


def current_status(db: Session) -> DerivedDataStatus:
    state = derived_data_state(db)
    db.commit()
    rebuilding = (state.rebuilding_started_at is not None
                  and datetime.utcnow() - state.rebuilding_started_at < ABANDONED_REBUILD_AFTER)
    return DerivedDataStatus(
        stale=state.stale_since is not None, stale_since=state.stale_since,
        stale_reason=state.stale_reason, rebuild_due_at=state.rebuild_due_at,
        rebuilding=rebuilding, last_rebuilt_at=state.last_rebuilt_at,
        last_rebuild_seconds=state.last_rebuild_seconds, last_error=state.last_error,
    )


@router.get("/derived-data", response_model=DerivedDataStatus)
def derived_data_status(db: Session = Depends(get_db)):
    return current_status(db)


@router.post("/derived-data/rebuild-if-due", response_model=DerivedDataStatus)
def rebuild_derived_data_if_due(db: Session = Depends(get_db)):
    try:
        rebuild_if_due(db)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {error}")
    return current_status(db)


@router.post("/derived-data/rebuild", response_model=DerivedDataStatus,
             dependencies=[Depends(require_admin)])
def force_rebuild_derived_data(db: Session = Depends(get_db)):
    try:
        stats = rebuild_derived_data(db)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {error}")
    if stats is None:
        raise HTTPException(status_code=409, detail="A rebuild is already running")
    return current_status(db)


class DuplicateCopyResponse(BaseModel):
    kept_match_id: int
    removed_match_id: int
    winners_agree: bool


class GameCleanupRequest(BaseModel):
    apply: bool = False
    expected_removed_match_ids: List[int] = []


class GameCleanupResponse(BaseModel):
    applied: bool
    aborted_match_ids: List[int]
    duplicate_copies: List[DuplicateCopyResponse]
    removed_match_ids: List[int]


@router.post("/duplicate-games", response_model=GameCleanupResponse,
             dependencies=[Depends(require_admin)])
def clean_up_duplicate_and_aborted_games(request: GameCleanupRequest, db: Session = Depends(get_db)):
    plan = plan_cleanup(db)
    to_remove = sorted(plan.match_ids_to_remove)
    if request.apply and to_remove != sorted(request.expected_removed_match_ids):
        raise HTTPException(
            status_code=409,
            detail="The games to remove changed since the dry run; review the new plan first",
        )
    if request.apply and to_remove:
        remove_matches(db, to_remove)
    return GameCleanupResponse(
        applied=request.apply,
        aborted_match_ids=plan.aborted_match_ids,
        duplicate_copies=[DuplicateCopyResponse(**vars(copy)) for copy in plan.duplicate_copies],
        removed_match_ids=to_remove,
    )


class MetricsBackfillRequest(BaseModel):
    rows: List[dict]


class MetricsBackfillResponse(BaseModel):
    updated: int
    created: int
    unmatched: int
    players_reaveraged: int


@router.post("/metrics-backfill", response_model=MetricsBackfillResponse,
             dependencies=[Depends(require_admin)])
def apply_metrics_backfill(request: MetricsBackfillRequest, db: Session = Depends(get_db)):
    return MetricsBackfillResponse(**vars(apply_metrics_rows(db, request.rows)))
