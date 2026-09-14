"""Private organizer judgments, immutable selected games, and separate feedback.

    Model snapshots are read from saved suggestions; these routes never mutate
    player ratings. Writes use the existing organizer/admin gate; all reads
    require a session when authentication is enabled, including public-read mode.
"""

from datetime import datetime, timedelta
import json
import trueskill
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..auth import require_admin
from ..database import get_db
from ..models import (
    BalancePrediction,
    BalanceSelection,
    Player,
    HumanEstimate,
    JudgmentConfidence,
    JudgmentReason,
    Match,
    PostgameFeedback,
    PostgameFeedbackType,
    PregameJudgment,
)

router = APIRouter(prefix="/judgments", tags=["judgments"])


def _ids_key(player_ids: List[int]) -> str:
    """Sorted comma-separated player-ID snapshot (matches BalancePrediction's
    team1_ids_key/team2_ids_key convention in app/services/balance_capture.py)."""
    return ",".join(str(i) for i in sorted(player_ids))


# =============================================================================
# Request/response models
# =============================================================================


class PlayerRaceContext(BaseModel):
    player_id: int
    race: str = Field(pattern="^(Terran|Protoss|Zerg|Random)$")


class CreateJudgmentRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    team1_player_ids: List[int] = Field(..., min_length=1, max_length=20)
    team2_player_ids: List[int] = Field(..., min_length=1, max_length=20)

    map_name: Optional[str] = Field(None, max_length=200)
    team1_context: Optional[List[PlayerRaceContext]] = Field(None, max_length=20)
    team2_context: Optional[List[PlayerRaceContext]] = Field(None, max_length=20)

    model_version: Optional[str] = Field(None, max_length=100)
    model_predicted_team1_win_prob: Optional[float] = Field(None, ge=0, le=1, allow_inf_nan=False)
    balance_prediction_id: Optional[int] = None
    match_id: Optional[int] = None

    human_estimate: HumanEstimate
    human_win_prob: Optional[float] = Field(None, ge=0, le=1, allow_inf_nan=False)
    confidence: JudgmentConfidence
    reason: JudgmentReason
    reason_note: Optional[str] = Field(None, max_length=2000)

    author: str = Field(..., min_length=1, max_length=100, pattern=r".*\S.*")


    @model_validator(mode="after")
    def validate_roster(self):
        ids = self.team1_player_ids + self.team2_player_ids
        if len(ids) != len(set(ids)) or any(i <= 0 for i in ids):
            raise ValueError("Teams must contain distinct positive player IDs")
        for team, context in ((self.team1_player_ids, self.team1_context),
                              (self.team2_player_ids, self.team2_context)):
            if context is not None:
                context_ids = [c.player_id for c in context]
                if len(context_ids) != len(set(context_ids)) or not set(context_ids) <= set(team):
                    raise ValueError("Race context must refer to distinct members of its team")
        return self


class UpdateJudgmentRequest(BaseModel):
    """All fields optional; only content editable before lock. Roster,
    match linkage, and model snapshot are immutable after creation too -
    only the human's own estimate/confidence/reason are ever revised."""

    human_estimate: Optional[HumanEstimate] = None
    human_win_prob: Optional[float] = Field(None, ge=0, le=1, allow_inf_nan=False)
    confidence: Optional[JudgmentConfidence] = None
    reason: Optional[JudgmentReason] = None
    reason_note: Optional[str] = Field(None, max_length=2000)


    @field_validator("human_estimate", "confidence", "reason")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class JudgmentResponse(BaseModel):
    id: int
    selection_id: Optional[int]
    created_at: datetime
    balance_prediction_id: Optional[int]
    match_id: Optional[int]
    team1_player_ids_key: str
    team2_player_ids_key: str
    map_name: Optional[str]
    team1_context: Optional[List[PlayerRaceContext]]
    team2_context: Optional[List[PlayerRaceContext]]
    model_version: Optional[str]
    model_predicted_team1_win_prob: Optional[float]
    human_estimate: HumanEstimate
    human_win_prob: Optional[float]
    confidence: JudgmentConfidence
    reason: JudgmentReason
    reason_note: Optional[str]
    author: str
    is_locked: bool
    locked_at: Optional[datetime]

    model_config = {"from_attributes": True, "protected_namespaces": ()}

    @classmethod
    def from_model(cls, j: PregameJudgment) -> "JudgmentResponse":
        return cls(
            id=j.id,
            selection_id=j.selection_id,
            created_at=j.created_at,
            balance_prediction_id=j.balance_prediction_id,
            match_id=j.match_id,
            team1_player_ids_key=j.team1_player_ids_key,
            team2_player_ids_key=j.team2_player_ids_key,
            map_name=j.map_name,
            team1_context=j.team1_context_json,
            team2_context=j.team2_context_json,
            model_version=j.model_version,
            model_predicted_team1_win_prob=j.model_predicted_team1_win_prob,
            human_estimate=j.human_estimate,
            human_win_prob=j.human_win_prob,
            confidence=j.confidence,
            reason=j.reason,
            reason_note=j.reason_note,
            author=j.author,
            is_locked=bool(j.is_locked),
            locked_at=j.locked_at,
        )


class CreateFeedbackRequest(BaseModel):
    judgment_id: Optional[int] = None
    match_id: Optional[int] = None
    feedback: PostgameFeedbackType
    note: Optional[str] = Field(None, max_length=2000)
    author: str = Field(..., min_length=1, max_length=100, pattern=r".*\S.*")


class FeedbackResponse(BaseModel):
    id: int
    created_at: datetime
    judgment_id: Optional[int]
    match_id: Optional[int]
    feedback: PostgameFeedbackType
    note: Optional[str]
    author: str

    model_config = {"from_attributes": True}


# =============================================================================
# Pre-game judgment endpoints
# =============================================================================


@router.post("", response_model=JudgmentResponse, dependencies=[Depends(require_admin)])
def create_judgment(request: CreateJudgmentRequest, db: Session = Depends(get_db)):
    """Record an organizer's pre-game team-balance judgment.

    Does not touch any rating column and is not used by the balancer or any
    ML training path - purely an independent, parallel signal.
    """
    if request.match_id is not None:
        if not db.query(Match.id).filter(Match.id == request.match_id).first():
            raise HTTPException(status_code=404, detail="Match not found")
        raise HTTPException(status_code=409, detail="Use post-game feedback for completed matches")
    ids = request.team1_player_ids + request.team2_player_ids
    if db.query(Player.id).filter(Player.id.in_(ids)).count() != len(ids):
        raise HTTPException(status_code=422, detail="Unknown player in roster")
    if request.balance_prediction_id is not None:
        prediction = db.get(BalancePrediction, request.balance_prediction_id)
        if prediction is None:
            raise HTTPException(status_code=404, detail="Balance prediction not found")
        if (prediction.method not in {"mmr_v2", "composite_v2"} or prediction.resolved
                or datetime.utcnow() - prediction.created_at > timedelta(hours=2)):
            raise HTTPException(status_code=409, detail="Generate fresh teams before recording a judgment")
        if _ids_key(ids) != prediction.players_key:
            raise HTTPException(status_code=422, detail="Final teams must use the suggestion's player pool")
        if db.query(BalanceSelection.id).filter(BalanceSelection.balance_prediction_id == prediction.id).first():
            raise HTTPException(status_code=409, detail="This suggestion already started a game")
        original_sizes = sorted([len(prediction.team1_ids_key.split(',')), len(prediction.team2_ids_key.split(','))])
        if sorted([len(request.team1_player_ids), len(request.team2_player_ids)]) != original_sizes:
            raise HTTPException(status_code=422, detail="Swaps must preserve the suggested team sizes")
        features = json.loads(prediction.features_json or '{}')
        original1 = prediction.team1_ids_key
        original2 = prediction.team2_ids_key
        final1 = _ids_key(request.team1_player_ids)
        final2 = _ids_key(request.team2_player_ids)
        if (final1, final2) == (original1, original2):
            probability = prediction.predicted_team1_win_prob
        elif (final1, final2) == (original2, original1):
            probability = 1 - prediction.predicted_team1_win_prob
        else:
            snapshots = features.get('ratings', {})
            if any(str(pid) not in snapshots for pid in ids):
                raise HTTPException(status_code=409, detail="Regenerate this suggestion to support swaps")
            from ..rating_policy import win_probability
            teams = [[trueskill.Rating(**snapshots[str(pid)]) for pid in team]
                     for team in (request.team1_player_ids, request.team2_player_ids)]
            probability = win_probability(*teams, variance_scale=features.get('variance_scale'))
        request.model_predicted_team1_win_prob = probability
        request.model_version = prediction.method
        request.map_name = features.get('map_name') or request.map_name

    judgment = PregameJudgment(
        created_at=datetime.utcnow(),
        balance_prediction_id=request.balance_prediction_id,
        match_id=request.match_id,
        team1_player_ids_key=_ids_key(request.team1_player_ids),
        team2_player_ids_key=_ids_key(request.team2_player_ids),
        map_name=request.map_name,
        team1_context_json=(
            [c.model_dump() for c in request.team1_context] if request.team1_context else None
        ),
        team2_context_json=(
            [c.model_dump() for c in request.team2_context] if request.team2_context else None
        ),
        model_version=request.model_version,
        model_predicted_team1_win_prob=request.model_predicted_team1_win_prob,
        human_estimate=request.human_estimate,
        human_win_prob=request.human_win_prob,
        confidence=request.confidence,
        reason=request.reason,
        reason_note=request.reason_note,
        author=request.author,
        is_locked=0,
    )
    db.add(judgment)
    db.commit()
    db.refresh(judgment)
    return JudgmentResponse.from_model(judgment)


@router.get("", response_model=List[JudgmentResponse])
def list_judgments(
    match_id: Optional[int] = None,
    balance_prediction_id: Optional[int] = None,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List judgments, optionally filtered by match or originating suggestion."""
    query = db.query(PregameJudgment)
    if match_id is not None:
        query = query.filter(PregameJudgment.match_id == match_id)
    if balance_prediction_id is not None:
        query = query.filter(PregameJudgment.balance_prediction_id == balance_prediction_id)
    judgments = query.order_by(PregameJudgment.created_at.desc(), PregameJudgment.id.desc()).offset(offset).limit(limit).all()
    return [JudgmentResponse.from_model(j) for j in judgments]


class SelectionResponse(BaseModel):
    id: int
    started_at: datetime
    team1_ids_key: str
    team2_ids_key: str
    map_name: Optional[str]
    match_id: Optional[int]
    model_config = {"from_attributes": True}


@router.get("/selections/candidates/{match_id}", response_model=List[SelectionResponse])
def selection_candidates(match_id: int, db: Session = Depends(get_db)):
    from ..services.balance_selection import match_outcome
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    candidates = db.query(BalanceSelection).filter(
        BalanceSelection.match_id.is_(None),
        BalanceSelection.started_at <= match.played_at,
        BalanceSelection.started_at >= match.played_at - timedelta(hours=2),
    ).order_by(BalanceSelection.started_at.desc()).limit(100).all()
    valid = []
    for selection in candidates:
        try:
            match_outcome(db, match, selection)
            valid.append(selection)
        except ValueError:
            continue
    return valid


@router.post("/selections/{selection_id}/match/{match_id}", dependencies=[Depends(require_admin)])
def link_selection(selection_id: int, match_id: int, db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    from ..services.balance_selection import attach_match
    match, selection = db.get(Match, match_id), db.get(BalanceSelection, selection_id)
    if match is None or selection is None:
        raise HTTPException(status_code=404, detail="Match or selection not found")
    try:
        attach_match(db, match, selection)
        db.commit()
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        detail = str(exc) if isinstance(exc, ValueError) else "Match already has a selected game"
        raise HTTPException(status_code=409, detail=detail)
    return {"selection_id": selection_id, "match_id": match_id}


@router.get("/selections/calibration")
def selected_calibration(db: Session = Depends(get_db)):
    from ..services.balance_capture import BalancePredictionService
    rows = db.query(BalanceSelection, BalancePrediction, PregameJudgment).join(
        BalancePrediction, BalanceSelection.balance_prediction_id == BalancePrediction.id
    ).join(PregameJudgment, PregameJudgment.selection_id == BalanceSelection.id).filter(
        BalanceSelection.match_id.isnot(None), BalanceSelection.team1_won.isnot(None),
        PregameJudgment.is_locked == 1,
    ).all()
    model_pairs, human_pairs = {}, []
    paired_models = []
    for selection, prediction, judgment in rows:
        pair = (selection.predicted_team1_win_prob, selection.team1_won)
        model_pairs.setdefault(prediction.method, []).append(pair)
        if judgment.human_win_prob is not None:
            human_pairs.append((judgment.human_win_prob, selection.team1_won))
            paired_models.append(pair)
    score = BalancePredictionService._calibration_from_pairs
    return {"models": {method: score(pairs) for method, pairs in model_pairs.items()},
            "human": score(human_pairs), "model_on_human_games": score(paired_models)}


@router.get("/{judgment_id}", response_model=JudgmentResponse)
def get_judgment(judgment_id: int, db: Session = Depends(get_db)):
    judgment = db.query(PregameJudgment).filter(PregameJudgment.id == judgment_id).first()
    if not judgment:
        raise HTTPException(status_code=404, detail="Judgment not found")
    return JudgmentResponse.from_model(judgment)


@router.patch(
    "/{judgment_id}", response_model=JudgmentResponse, dependencies=[Depends(require_admin)]
)
def update_judgment(
    judgment_id: int, request: UpdateJudgmentRequest, db: Session = Depends(get_db)
):
    """Revise the human estimate/confidence/reason before lock.

    Roster, match linkage, and the model snapshot are never editable through
    this endpoint (they are the immutable "what was actually judged, against
    what" record) - only the organizer's own read on it.
    """
    judgment = db.query(PregameJudgment).filter(PregameJudgment.id == judgment_id).first()
    if not judgment:
        raise HTTPException(status_code=404, detail="Judgment not found")
    if judgment.is_locked:
        raise HTTPException(status_code=409, detail="Judgment is locked and can no longer be edited")

    updates = request.model_dump(exclude_unset=True)
    if updates:
        changed = db.query(PregameJudgment).filter(
            PregameJudgment.id == judgment_id, PregameJudgment.is_locked == 0
        ).update(updates, synchronize_session=False)
        if changed != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="Judgment is locked")

    db.commit()
    db.refresh(judgment)
    return JudgmentResponse.from_model(judgment)


@router.post(
    "/{judgment_id}/lock", response_model=JudgmentResponse, dependencies=[Depends(require_admin)]
)
def lock_judgment(judgment_id: int, db: Session = Depends(get_db)):
    """Freeze a judgment's content, e.g. once the match has started.

    Locking is idempotent: locking an already-locked judgment is a no-op
    (returns the existing lock timestamp) rather than an error, since two
    organizers hitting the button at once shouldn't fail either request.
    """
    now = datetime.utcnow()
    changed = db.query(PregameJudgment).filter(
        PregameJudgment.id == judgment_id, PregameJudgment.is_locked == 0
    ).update({"is_locked": 1, "locked_at": now}, synchronize_session=False)
    judgment = db.get(PregameJudgment, judgment_id, populate_existing=True)
    if judgment is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Judgment not found")
    if changed and judgment.balance_prediction_id is not None:
        prediction = db.get(BalancePrediction, judgment.balance_prediction_id)
        if (prediction.method not in {"mmr_v2", "composite_v2"} or prediction.resolved
                or now - prediction.created_at > timedelta(hours=2)):
            db.rollback()
            raise HTTPException(status_code=409, detail="Generate fresh teams before starting a game")
        selection = BalanceSelection(
            balance_prediction_id=prediction.id, started_at=now,
            team1_ids_key=judgment.team1_player_ids_key,
            team2_ids_key=judgment.team2_player_ids_key,
            map_name=judgment.map_name,
            predicted_team1_win_prob=judgment.model_predicted_team1_win_prob,
        )
        db.add(selection)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="This suggestion already started a game; regenerate teams for another game")
        judgment.selection_id = selection.id
    db.commit()
    db.refresh(judgment)
    return JudgmentResponse.from_model(judgment)


# =============================================================================
# Post-game feedback endpoints
# =============================================================================


@router.post("/feedback", response_model=FeedbackResponse, dependencies=[Depends(require_admin)])
def create_feedback(request: CreateFeedbackRequest, db: Session = Depends(get_db)):
    if request.judgment_id is None and request.match_id is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of judgment_id or match_id is required",
        )
    if request.judgment_id is not None:
        judgment = (
            db.query(PregameJudgment).filter(PregameJudgment.id == request.judgment_id).first()
        )
        if not judgment:
            raise HTTPException(status_code=404, detail="Judgment not found")
    if request.judgment_id is not None and request.match_id is not None:
        if judgment.match_id != request.match_id:
            raise HTTPException(status_code=422, detail="Feedback links must refer to the same match")
    if request.match_id is not None:
        if not db.query(Match.id).filter(Match.id == request.match_id).first():
            raise HTTPException(status_code=404, detail="Match not found")

    feedback = PostgameFeedback(
        created_at=datetime.utcnow(),
        judgment_id=request.judgment_id,
        match_id=request.match_id,
        feedback=request.feedback,
        note=request.note,
        author=request.author,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)


@router.get("/feedback/list", response_model=List[FeedbackResponse])
def list_feedback(
    match_id: Optional[int] = None,
    judgment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(PostgameFeedback)
    if match_id is not None:
        query = query.filter(PostgameFeedback.match_id == match_id)
    if judgment_id is not None:
        query = query.filter(PostgameFeedback.judgment_id == judgment_id)
    feedback = query.order_by(PostgameFeedback.created_at.desc(), PostgameFeedback.id.desc()).offset(offset).limit(limit).all()
    return [FeedbackResponse.model_validate(f) for f in feedback]
