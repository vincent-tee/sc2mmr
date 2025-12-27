"""
API endpoints for replay upload and management.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Any, cast
from datetime import datetime
import os
import tempfile
import time
import logging

from ..database import get_db
from ..models import (
    Match,
    MatchPlayer,
    Player,
    FailedUpload,
    UploadErrorType,
    PerformanceFeatures,
)
from ..replay_parser import (
    parse_replay,
    validate_replay_data,
    ReplayParseError,
    WinnerDeterminationError,
)
from ..rating_system import RatingSystem
from ..advanced_parser import parse_replay_advanced
from ..impact_service import ImpactService
from ..performance_rating import PerformanceRatingAdjuster
from ..match_commentary import MatchCommentaryGenerator
from ..auto_adaptive import trigger_auto_optimization
from pydantic import BaseModel
import traceback

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/replays", tags=["replays"])


# Helper functions
def _log_failed_upload(
    db: Session,
    filename: str,
    file_size: int,
    error_type: UploadErrorType,
    error_message: str,
    error_detail: str,
    replay_hash: Optional[str] = None,
    map_name: Optional[str] = None,
    game_mode: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    num_players: Optional[int] = None,
    replay_file_path: Optional[str] = None,
):
    """
    Log a failed replay upload to the database.
    """
    try:
        # Check for existing failed upload with same hash
        existing: Any = None
        if replay_hash:
            existing = (
                db.query(FailedUpload)
                .filter(FailedUpload.replay_hash == replay_hash)
                .first()
            )

        if existing:
            # Update existing record
            existing.filename = filename
            existing.uploaded_at = datetime.utcnow()
            existing.file_size_bytes = file_size
            existing.error_type = error_type
            existing.error_message = error_message[:500]
            existing.error_detail = error_detail[:2000] if error_detail else None
            # Update optional fields if provided
            if map_name:
                existing.map_name = map_name
            if game_mode:
                existing.game_mode = game_mode
            if duration_seconds:
                existing.duration_seconds = duration_seconds
            if num_players:
                existing.num_players = num_players
            if replay_file_path:
                existing.replay_file_path = replay_file_path
            db.commit()
        else:
            # Create new record
            failed_upload = FailedUpload(
                filename=filename,
                file_size_bytes=file_size,
                replay_hash=replay_hash,
                replay_file_path=replay_file_path,
                error_type=error_type,
                error_message=error_message[:500],
                error_detail=error_detail[:2000] if error_detail else None,
                map_name=map_name,
                game_mode=game_mode,
                duration_seconds=duration_seconds,
                num_players=num_players,
            )
            db.add(failed_upload)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to log failed upload: {e}", exc_info=True)
        db.rollback()


# Request/Response models
class ProcessingStats(BaseModel):
    """Statistics about the processing stages."""

    parse_time_ms: float
    validation_time_ms: float
    duplicate_check_time_ms: float
    rating_update_time_ms: float
    total_time_ms: float


class ReplayUploadResponse(BaseModel):
    """Response for successful replay upload."""

    match_id: int
    map_name: str
    game_mode: str
    played_at: datetime
    duration_seconds: int
    num_players: int
    message: str
    processing_stats: ProcessingStats

    class Config:
        from_attributes = True


class MatchPlayerSummary(BaseModel):
    """Summary of a player's performance in a match."""

    player_id: int
    player_name: str
    team_number: int
    race: str
    won: bool
    mmr_change: float
    damage_dealt: Optional[int] = None
    impact_score: Optional[float] = None


class MatchResponse(BaseModel):
    """Response model for match details."""

    id: int
    played_at: datetime
    game_mode: str
    map_name: str
    duration_seconds: int
    replay_hash: Optional[str] = None
    predicted_team1_win_prob: Optional[float] = None
    predicted_team2_win_prob: Optional[float] = None
    ml_predicted_win_prob: Optional[float] = None

    winner_team: int = 0
    players: List[MatchPlayerSummary] = []

    # Highlight stats
    mvp_player_id: Optional[int] = None
    mvp_player_name: Optional[str] = None
    total_damage: Optional[int] = None

    class Config:
        from_attributes = True


class MatchWithPlayersResponse(MatchResponse):
    """Response model for a match including player summaries."""

    pass


class MatchListResponse(BaseModel):
    """Response model for a list of matches."""

    matches: List[MatchResponse]
    total_count: int
    limit: int
    offset: int

    class Config:
        from_attributes = True


class MatchListWithPlayersResponse(BaseModel):
    """Response model for matches with players included."""

    matches: List[MatchWithPlayersResponse]
    total_count: int
    limit: int
    offset: int

    class Config:
        from_attributes = True


class MatchPlayerResponse(BaseModel):
    """Response model for match player details."""

    player_name: str
    team_number: int
    race: str
    won: bool
    mmr_before: float
    mmr_after: float
    mmr_change: float

    class Config:
        from_attributes = True


class MatchDetailResponse(BaseModel):
    """Detailed match response with players."""

    match: MatchResponse
    players: List[MatchPlayerResponse]

    class Config:
        from_attributes = True


@router.post("/upload", response_model=ReplayUploadResponse)
async def upload_replay(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload and process a SC2 replay file.
    """
    fn: str = str(file.filename) if file.filename else "unknown.SC2Replay"
    logger.info(f"Starting replay upload: filename='{fn}'")

    if not fn.endswith(".SC2Replay"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .SC2Replay files are accepted.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".SC2Replay") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    replay_data = None
    try:
        start_time = time.time()
        replay_data = parse_replay(tmp_file_path)

        is_valid, error_msg = validate_replay_data(replay_data)
        if not is_valid:
            raise HTTPException(
                status_code=400, detail=f"Validation failed: {error_msg}"
            )

        existing_match = (
            db.query(Match).filter(Match.replay_hash == replay_data.replay_hash).first()
        )

        if existing_match:
            raise HTTPException(
                status_code=409,
                detail=f"Replay already uploaded. Match ID: {existing_match.id}",
            )

        replay_file_path = _save_replay_file(content, fn, replay_data.replay_hash)

        match = Match(
            played_at=replay_data.played_at,
            game_mode=replay_data.game_mode,
            map_name=replay_data.map_name,
            duration_seconds=replay_data.duration_seconds,
            replay_file_path=replay_file_path,
            replay_hash=replay_data.replay_hash,
        )
        db.add(match)
        db.flush()

        RatingSystem.update_ratings_from_match(db, replay_data, match)

        if replay_file_path:
            try:
                from ..services.ml_features_service import MLFeaturesService

                MLFeaturesService.extract_and_save_ml_features(
                    db, replay_file_path, int(match.id)
                )
            except Exception as e:
                logger.warning(f"ML feature extraction failed: {e}")

        try:
            from ..online_learning import OnlineLearningEngine

            team1_won = any(p.won for p in replay_data.players if p.team == 1)
            learning_engine = OnlineLearningEngine(db)
            learning_engine.record_outcome(int(match.id), team1_won)
        except Exception as e:
            logger.warning(f"Online learning record failed: {e}")

        total_time_ms = (time.time() - start_time) * 1000

        return ReplayUploadResponse(
            match_id=int(match.id),
            map_name=str(match.map_name),
            game_mode=str(match.game_mode.value),
            played_at=match.played_at,
            duration_seconds=int(match.duration_seconds),
            num_players=len(replay_data.players),
            message="Replay processed successfully",
            processing_stats=ProcessingStats(
                parse_time_ms=0.0,
                validation_time_ms=0.0,
                duplicate_check_time_ms=0.0,
                rating_update_time_ms=0.0,
                total_time_ms=round(total_time_ms, 2),
            ),
        )

    except WinnerDeterminationError as e:
        import sc2reader  # type: ignore

        replay_hash = None
        m_name = None
        g_mode = None
        dur = None
        n_p = None

        try:
            replay = sc2reader.load_replay(tmp_file_path, load_level=2)  # type: ignore
            from ..replay_parser import calculate_replay_hash, determine_game_mode

            replay_hash = calculate_replay_hash(tmp_file_path)
            m_name = str(getattr(replay, "map_name", ""))
            dur = int(getattr(getattr(replay, "game_length", None), "seconds", 0))
            n_p = len(
                [
                    p
                    for p in getattr(replay, "players", [])
                    if getattr(p, "is_human", False)
                ]
            )
            g_mode_enum = determine_game_mode(n_p)
            g_mode = g_mode_enum.value if g_mode_enum else None
        except Exception:
            pass

        saved_path = None
        if replay_hash:
            saved_path = _save_failed_replay_file(content, fn, replay_hash)

        _log_failed_upload(
            db=db,
            filename=fn,
            file_size=len(content),
            error_type=UploadErrorType.WINNER_DETERMINATION,
            error_message=str(e),
            error_detail=traceback.format_exc(),
            replay_hash=replay_hash,
            map_name=m_name,
            game_mode=g_mode,
            duration_seconds=dur,
            num_players=n_p,
            replay_file_path=saved_path,
        )
        raise HTTPException(
            status_code=400, detail=f"Winner determination failed: {str(e)}"
        )

    except ReplayParseError as e:
        _log_failed_upload(
            db=db,
            filename=fn,
            file_size=len(content),
            error_type=UploadErrorType.PARSE_ERROR,
            error_message=str(e),
            error_detail=traceback.format_exc(),
        )
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")
    except HTTPException as http_ex:
        if http_ex.status_code != 409:
            msg = str(http_ex.detail)
            if "Unable to determine" not in msg:
                error_type = UploadErrorType.VALIDATION_ERROR
                if "Invalid game mode" in msg:
                    error_type = UploadErrorType.UNSUPPORTED_MODE

                _log_failed_upload(
                    db=db,
                    filename=fn,
                    file_size=len(content),
                    error_type=error_type,
                    error_message=msg,
                    error_detail=traceback.format_exc(),
                    replay_hash=replay_data.replay_hash if replay_data else None,
                    map_name=str(replay_data.map_name) if replay_data else None,
                    game_mode=str(replay_data.game_mode.value) if replay_data else None,
                    duration_seconds=int(replay_data.duration_seconds)
                    if replay_data
                    else None,
                    num_players=len(replay_data.players) if replay_data else None,
                )
        raise
    except Exception as e:
        _log_failed_upload(
            db=db,
            filename=fn,
            file_size=len(content),
            error_type=UploadErrorType.OTHER,
            error_message=str(e),
            error_detail=traceback.format_exc(),
            replay_hash=replay_data.replay_hash if replay_data else None,
            map_name=str(replay_data.map_name) if replay_data else None,
            game_mode=str(replay_data.game_mode.value) if replay_data else None,
            duration_seconds=int(replay_data.duration_seconds) if replay_data else None,
            num_players=len(replay_data.players) if replay_data else None,
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


@router.get("/matches", response_model=MatchListResponse)
def get_matches(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    total_count = db.query(func.count(Match.id)).scalar() or 0
    matches = (
        db.query(Match)
        .order_by(Match.played_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return MatchListResponse(
        matches=[
            MatchResponse(
                id=int(m.id),
                played_at=m.played_at,
                game_mode=str(m.game_mode.value),
                map_name=str(m.map_name),
                duration_seconds=int(m.duration_seconds),
                replay_hash=str(m.replay_hash or ""),
            )
            for m in matches
        ],
        total_count=int(total_count),
        limit=limit,
        offset=offset,
    )


@router.get("/matches-with-players", response_model=MatchListWithPlayersResponse)
def get_matches_with_players(
    limit: int = 20, offset: int = 0, db: Session = Depends(get_db)
):
    from ..models import PlayerMatchMetrics

    total_count = db.query(func.count(Match.id)).scalar() or 0
    matches = (
        db.query(Match)
        .order_by(Match.played_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    match_responses = []
    for m in matches:
        match: Any = m
        match_players = (
            db.query(MatchPlayer, Player)
            .join(Player, MatchPlayer.player_id == Player.id)
            .filter(MatchPlayer.match_id == match.id)
            .all()
        )

        player_summaries = []
        winner_team = 0
        mvp_id = None
        mvp_name = None
        max_impact = -1.0

        for mp_obj, p_obj in match_players:
            mp: Any = mp_obj
            p: Any = p_obj
            metrics: Any = (
                db.query(PlayerMatchMetrics)
                .filter(PlayerMatchMetrics.match_player_id == mp.id)
                .first()
            )

            mmr_diff = round(
                float(
                    RatingSystem.calculate_display_mmr(mp.mu_after)
                    - RatingSystem.calculate_display_mmr(mp.mu_before)
                ),
                1,
            )
            if mp.won:
                winner_team = int(mp.team_number)

            summary = MatchPlayerSummary(
                player_id=int(p.id),
                player_name=str(p.name),
                team_number=int(mp.team_number),
                race=str(mp.race.value),
                won=bool(mp.won == 1),
                mmr_change=mmr_diff,
                damage_dealt=int(metrics.damage_dealt) if metrics else None,
                impact_score=float(metrics.overall_impact) if metrics else None,
            )
            player_summaries.append(summary)

            if metrics and mp.won and float(metrics.overall_impact or 0) > max_impact:
                max_impact = float(metrics.overall_impact)
                mvp_id = int(p.id)
                mvp_name = str(p.name)

        match_responses.append(
            MatchWithPlayersResponse(
                id=int(match.id),
                played_at=match.played_at,
                game_mode=str(match.game_mode.value),
                map_name=str(match.map_name),
                duration_seconds=int(match.duration_seconds),
                replay_hash=str(match.replay_hash or ""),
                winner_team=winner_team,
                players=player_summaries,
                mvp_player_id=mvp_id,
                mvp_player_name=mvp_name,
            )
        )

    return MatchListWithPlayersResponse(
        matches=match_responses,
        total_count=int(total_count),
        limit=limit,
        offset=offset,
    )


@router.get("/matches/{match_id}", response_model=MatchDetailResponse)
def get_match_details(match_id: int, db: Session = Depends(get_db)):
    match: Any = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match_players = (
        db.query(MatchPlayer, Player)
        .join(Player, MatchPlayer.player_id == Player.id)
        .filter(MatchPlayer.match_id == match_id)
        .all()
    )

    players_data = []
    for mp_obj, p_obj in match_players:
        mp: Any = mp_obj
        p: Any = p_obj
        mmr_b = float(RatingSystem.calculate_display_mmr(mp.mu_before))
        mmr_a = float(RatingSystem.calculate_display_mmr(mp.mu_after))
        players_data.append(
            MatchPlayerResponse(
                player_name=str(p.name),
                team_number=int(mp.team_number),
                race=str(mp.race.value),
                won=bool(mp.won == 1),
                mmr_before=mmr_b,
                mmr_after=mmr_a,
                mmr_change=mmr_a - mmr_b,
            )
        )

    # Get ML win probability from PerformanceFeatures if available
    ml_win_prob = None
    first_mp = match_players[0][0] if match_players else None
    if first_mp:
        from ..models import PerformanceFeatures

        perf = (
            db.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == first_mp.id)
            .first()
        )
        if perf and perf.ml_win_probability is not None:
            # ml_win_probability is stored as prob for THIS player's team
            if first_mp.team_number == 1:
                ml_win_prob = perf.ml_win_probability
            else:
                ml_win_prob = 1.0 - perf.ml_win_probability

    return MatchDetailResponse(
        match=MatchResponse(
            id=int(match.id),
            played_at=match.played_at,
            game_mode=str(match.game_mode.value),
            map_name=str(match.map_name),
            duration_seconds=int(match.duration_seconds),
            replay_hash=str(match.replay_hash or ""),
            predicted_team1_win_prob=match.predicted_team1_win_prob,
            predicted_team2_win_prob=match.predicted_team2_win_prob,
            ml_predicted_win_prob=ml_win_prob,
        ),
        players=players_data,
    )


@router.get("/matches/{match_id}/commentary")
def get_match_commentary(match_id: int, db: Session = Depends(get_db)):
    """
    Get AI-generated commentary for a match.
    """
    return MatchCommentaryGenerator.generate_match_summary(db, match_id)


def _save_failed_replay_file(content: bytes, filename: str, replay_hash: str) -> str:
    failed_replays_dir = os.path.join(os.getcwd(), "failed_replays")
    os.makedirs(failed_replays_dir, exist_ok=True)
    file_path = os.path.join(failed_replays_dir, f"{replay_hash}_{filename}")
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def _save_replay_file(content: bytes, filename: str, replay_hash: str) -> Optional[str]:
    from ..config import settings

    if not settings.replay_storage_enabled:
        return None
    replays_dir = os.path.join(os.getcwd(), settings.replay_storage_dir)
    os.makedirs(replays_dir, exist_ok=True)
    file_path = os.path.join(replays_dir, f"{replay_hash}.SC2Replay")
    if os.path.exists(file_path):
        return file_path
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


class BulkReprocessRequest(BaseModel):
    """Request for bulk reprocessing."""

    match_ids: Optional[List[int]] = None  # If None, process all
    force: bool = False  # If True, reprocess even if features exist


class BulkReprocessResponse(BaseModel):
    """Response for bulk reprocessing."""

    total: int
    processed: int
    skipped: int
    failed: int
    errors: List[dict]


@router.post("/bulk-reprocess", response_model=BulkReprocessResponse)
def bulk_reprocess_replays(
    request: BulkReprocessRequest, db: Session = Depends(get_db)
):
    """
    Bulk re-process existing matches to extract ML features.
    """
    from ..services.ml_features_service import MLFeaturesService

    # Get matches to process
    query = db.query(Match)

    if request.match_ids:
        query = query.filter(Match.id.in_(request.match_ids))

    matches = query.all()

    total = len(matches)
    processed = 0
    skipped = 0
    failed = 0
    errors = []

    for m in matches:
        match: Any = m
        try:
            # Check if replay file exists
            if not match.replay_file_path or not os.path.exists(match.replay_file_path):
                skipped += 1
                errors.append({"match_id": match.id, "error": "Replay file not found"})
                continue

            # Check if features already exist (unless force=True)
            if not request.force:
                # Check if any player has features
                match_players = (
                    db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
                )

                has_features = False
                for mp in match_players:
                    existing = (
                        db.query(PerformanceFeatures)
                        .filter(PerformanceFeatures.match_player_id == mp.id)
                        .first()
                    )
                    if existing and existing.ml_win_probability is not None:
                        has_features = True
                        break

                if has_features:
                    skipped += 1
                    continue

            # Extract and save ML features
            results = MLFeaturesService.extract_and_save_ml_features(
                db, str(match.replay_file_path), int(match.id)
            )

            if any(results.values()):
                processed += 1
            else:
                failed += 1
                errors.append(
                    {
                        "match_id": match.id,
                        "error": "Feature extraction returned no results",
                    }
                )

        except Exception as e:
            failed += 1
            errors.append({"match_id": match.id, "error": str(e)})
            logger.error(f"Failed to reprocess match {match.id}: {e}")

    return BulkReprocessResponse(
        total=total,
        processed=processed,
        skipped=skipped,
        failed=failed,
        errors=errors[:50],  # Limit error list
    )


class FailedUploadResponse(BaseModel):
    """Response model for failed uploads."""

    id: int
    filename: str
    file_size_bytes: Optional[int]
    error_type: str
    error_message: str
    map_name: Optional[str]
    game_mode: Optional[str]
    duration_seconds: Optional[int]
    num_players: Optional[int]
    uploaded_at: datetime
    reviewed: bool

    class Config:
        from_attributes = True


@router.get("/failed-uploads", response_model=List[FailedUploadResponse])
def get_failed_uploads(
    limit: int = 50,
    offset: int = 0,
    error_type: Optional[str] = None,
    reviewed: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """
    Get list of failed replay uploads for manual review.
    """
    query = db.query(FailedUpload).order_by(FailedUpload.uploaded_at.desc())

    # Apply filters
    if error_type:
        try:
            error_enum = UploadErrorType(error_type)
            query = query.filter(FailedUpload.error_type == error_enum)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid error_type: {error_type}"
            )

    if reviewed is not None:
        query = query.filter(FailedUpload.reviewed == (1 if reviewed else 0))

    failed_uploads = query.limit(limit).offset(offset).all()

    return [
        FailedUploadResponse(
            id=int(fu.id),
            filename=str(fu.filename),
            file_size_bytes=fu.file_size_bytes,
            error_type=str(fu.error_type.value),
            error_message=str(fu.error_message),
            map_name=fu.map_name,
            game_mode=fu.game_mode,
            duration_seconds=fu.duration_seconds,
            num_players=fu.num_players,
            uploaded_at=fu.uploaded_at,
            reviewed=bool(fu.reviewed),
        )
        for fu in failed_uploads
    ]


class MarkReviewedRequest(BaseModel):
    """Request to mark failed upload as reviewed."""

    review_notes: Optional[str] = None


@router.patch("/failed-uploads/{upload_id}/reviewed")
def mark_upload_reviewed(
    upload_id: int, request: MarkReviewedRequest, db: Session = Depends(get_db)
):
    """
    Mark a failed upload as reviewed.
    """
    failed_upload = db.query(FailedUpload).filter(FailedUpload.id == upload_id).first()

    if not failed_upload:
        raise HTTPException(status_code=404, detail="Failed upload not found")

    failed_upload.reviewed = 1
    if request.review_notes:
        failed_upload.review_notes = request.review_notes

    db.commit()

    return {
        "status": "success",
        "message": f"Upload {upload_id} marked as reviewed",
    }


class ManualWinnerRequest(BaseModel):
    """Request to manually specify winner for failed replay."""

    winner_team: int  # 1 or 2


@router.post(
    "/failed-uploads/{upload_id}/set-winner", response_model=ReplayUploadResponse
)
def set_manual_winner(
    upload_id: int, request: ManualWinnerRequest, db: Session = Depends(get_db)
):
    """
    Manually specify the winner for a failed replay and reprocess it.
    """
    logger.info(
        f"📌 Manual winner determination requested for upload_id={upload_id}, winner_team={request.winner_team}"
    )

    # Validate winner_team
    if request.winner_team not in [1, 2]:
        raise HTTPException(status_code=400, detail="winner_team must be 1 or 2")

    # Get the failed upload
    failed_upload = db.query(FailedUpload).filter(FailedUpload.id == upload_id).first()

    if not failed_upload:
        raise HTTPException(status_code=404, detail="Failed upload not found")

    # Check if replay file was saved
    if not failed_upload.replay_file_path or not os.path.exists(
        failed_upload.replay_file_path
    ):
        raise HTTPException(
            status_code=404,
            detail="Replay file not found. Original file may not have been saved.",
        )

    replay_data = None
    try:
        start_time = time.time()

        # Parse the replay with advanced metrics
        advanced_data = parse_replay_advanced(
            str(failed_upload.replay_file_path), manual_winner_team=request.winner_team
        )
        replay_data = advanced_data.basic_data

        # Validate replay data
        is_valid, error_msg = validate_replay_data(replay_data)
        if not is_valid:
            raise HTTPException(
                status_code=400, detail=f"Validation failed: {error_msg}"
            )

        # Check for duplicate
        existing_match = (
            db.query(Match).filter(Match.replay_hash == replay_data.replay_hash).first()
        )

        if existing_match:
            # Delete the failed upload record since it's already processed
            db.delete(failed_upload)
            db.commit()

            return ReplayUploadResponse(
                match_id=int(existing_match.id),
                map_name=str(existing_match.map_name),
                game_mode=str(existing_match.game_mode.value),
                played_at=existing_match.played_at,
                duration_seconds=int(existing_match.duration_seconds),
                num_players=len(replay_data.players),
                message=f"Replay was already successfully processed as Match #{existing_match.id}",
                processing_stats=ProcessingStats(
                    parse_time_ms=0,
                    validation_time_ms=0,
                    duplicate_check_time_ms=0,
                    rating_update_time_ms=0.0,
                    total_time_ms=round((time.time() - start_time) * 1000, 2),
                ),
            )

        # Create match record
        match = Match(
            played_at=replay_data.played_at,
            game_mode=replay_data.game_mode,
            map_name=replay_data.map_name,
            duration_seconds=replay_data.duration_seconds,
            replay_file_path=failed_upload.replay_file_path,
            replay_hash=replay_data.replay_hash,
        )
        db.add(match)
        db.flush()

        # Update ratings and create match_players
        RatingSystem.update_ratings_from_match(db, replay_data, match)

        # Save advanced metrics
        for player_metrics in advanced_data.player_metrics:
            player = (
                db.query(Player)
                .filter(Player.name == player_metrics.player_name)
                .first()
            )
            if player:
                match_player = (
                    db.query(MatchPlayer)
                    .filter(
                        MatchPlayer.match_id == match.id,
                        MatchPlayer.player_id == player.id,
                    )
                    .first()
                )

                if match_player:
                    ImpactService.save_match_metrics(
                        db, match_player.id, player_metrics
                    )
                    ImpactService.update_player_averages(db, player.id)

        # Update synergies and adjustments
        ImpactService.update_synergies(db, int(match.id))
        PerformanceRatingAdjuster.adjust_ratings_for_match(db, int(match.id))

        # Delete the failed upload record since processing succeeded
        db.delete(failed_upload)
        db.commit()

        return ReplayUploadResponse(
            match_id=int(match.id),
            map_name=str(match.map_name),
            game_mode=str(match.game_mode.value),
            played_at=match.played_at,
            duration_seconds=int(match.duration_seconds),
            num_players=len(replay_data.players),
            message="Replay processed successfully with manual winner determination",
            processing_stats=ProcessingStats(
                parse_time_ms=0,
                validation_time_ms=0,
                duplicate_check_time_ms=0,
                rating_update_time_ms=0,
                total_time_ms=round((time.time() - start_time) * 1000, 2),
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during manual reprocessing: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to reprocess replay: {str(e)}"
        )


@router.post("/upload-advanced", response_model=ReplayUploadResponse)
async def upload_replay_advanced(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """
    Upload and process a SC2 replay file with advanced metrics.
    """
    fn: str = str(file.filename) if file.filename else "unknown.SC2Replay"

    if not fn.endswith(".SC2Replay"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .SC2Replay files are accepted.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".SC2Replay") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    replay_data = None
    try:
        start_time = time.time()

        # Parse with advanced metrics
        advanced_data = parse_replay_advanced(tmp_file_path)
        replay_data = advanced_data.basic_data

        # Validate
        is_valid, error_msg = validate_replay_data(replay_data)
        if not is_valid:
            # Check for winner determination failure to log it specifically
            if error_msg and "Unable to determine" in error_msg:
                saved_path = _save_failed_replay_file(
                    content, fn, replay_data.replay_hash
                )
                _log_failed_upload(
                    db=db,
                    filename=fn,
                    file_size=len(content),
                    error_type=UploadErrorType.WINNER_DETERMINATION,
                    error_message=error_msg,
                    error_detail=traceback.format_exc(),
                    replay_hash=replay_data.replay_hash,
                    map_name=str(replay_data.map_name),
                    game_mode=str(replay_data.game_mode.value),
                    duration_seconds=int(replay_data.duration_seconds),
                    num_players=len(replay_data.players),
                    replay_file_path=saved_path,
                )
            raise HTTPException(
                status_code=400, detail=f"Validation failed: {error_msg}"
            )

        # Check duplicate
        existing_match = (
            db.query(Match).filter(Match.replay_hash == replay_data.replay_hash).first()
        )

        if existing_match:
            raise HTTPException(
                status_code=409,
                detail=f"Replay already uploaded. Match ID: {existing_match.id}",
            )

        # Save file
        replay_file_path = _save_replay_file(content, fn, replay_data.replay_hash)

        # Create match
        match = Match(
            played_at=replay_data.played_at,
            game_mode=replay_data.game_mode,
            map_name=replay_data.map_name,
            duration_seconds=replay_data.duration_seconds,
            replay_file_path=replay_file_path,
            replay_hash=replay_data.replay_hash,
        )
        db.add(match)
        db.flush()

        # Update ratings
        RatingSystem.update_ratings_from_match(db, replay_data, match)

        # Save metrics
        for player_metrics in advanced_data.player_metrics:
            player = (
                db.query(Player)
                .filter(Player.name == player_metrics.player_name)
                .first()
            )
            if player:
                match_player = (
                    db.query(MatchPlayer)
                    .filter(
                        MatchPlayer.match_id == match.id,
                        MatchPlayer.player_id == player.id,
                    )
                    .first()
                )

                if match_player:
                    ImpactService.save_match_metrics(
                        db, match_player.id, player_metrics
                    )
                    ImpactService.update_player_averages(db, player.id)

        # Update synergies and adjustments
        ImpactService.update_synergies(db, int(match.id))
        PerformanceRatingAdjuster.adjust_ratings_for_match(db, int(match.id))

        # Extract and save ML features
        if replay_file_path:
            try:
                from ..services.ml_features_service import MLFeaturesService

                MLFeaturesService.extract_and_save_ml_features(
                    db, replay_file_path, int(match.id)
                )
            except Exception as e:
                logger.warning(f"ML feature extraction failed: {e}")

        # Trigger auto optimization
        try:
            trigger_auto_optimization(db)
        except Exception as e:
            logger.warning(f"Auto-optimization failed: {e}")

        total_time_ms = (time.time() - start_time) * 1000

        return ReplayUploadResponse(
            match_id=int(match.id),
            map_name=str(match.map_name),
            game_mode=str(match.game_mode.value),
            played_at=match.played_at,
            duration_seconds=int(match.duration_seconds),
            num_players=len(replay_data.players),
            message="Replay processed successfully with advanced metrics",
            processing_stats=ProcessingStats(
                parse_time_ms=0,
                validation_time_ms=0,
                duplicate_check_time_ms=0,
                rating_update_time_ms=0,
                total_time_ms=round(total_time_ms, 2),
            ),
        )

    except ReplayParseError as e:
        _log_failed_upload(
            db=db,
            filename=fn,
            file_size=len(content),
            error_type=UploadErrorType.PARSE_ERROR,
            error_message=str(e),
            error_detail=traceback.format_exc(),
        )
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        _log_failed_upload(
            db=db,
            filename=fn,
            file_size=len(content),
            error_type=UploadErrorType.OTHER,
            error_message=str(e),
            error_detail=traceback.format_exc(),
            replay_hash=replay_data.replay_hash if replay_data else None,
            map_name=str(replay_data.map_name) if replay_data else None,
            game_mode=str(replay_data.game_mode.value) if replay_data else None,
            duration_seconds=int(replay_data.duration_seconds) if replay_data else None,
            num_players=len(replay_data.players) if replay_data else None,
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
