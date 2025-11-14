"""
API endpoints for replay upload and management.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import tempfile
import time

from ..database import get_db
from ..models import Match, MatchPlayer, Player, FailedUpload, UploadErrorType
from ..replay_parser import parse_replay, validate_replay_data, ReplayParseError
from ..rating_system import RatingSystem
from ..advanced_parser import parse_replay_advanced
from ..impact_service import ImpactService
from ..performance_rating import PerformanceRatingAdjuster
from ..match_commentary import MatchCommentaryGenerator
from pydantic import BaseModel
import traceback


router = APIRouter(prefix="/replays", tags=["replays"])


# Helper functions
def _log_failed_upload(
    db: Session,
    filename: str,
    file_size: int,
    error_type: UploadErrorType,
    error_message: str,
    error_detail: str,
    replay_hash: str = None,
    map_name: str = None,
    game_mode: str = None,
    duration_seconds: int = None,
    num_players: int = None,
    replay_file_path: str = None
):
    """Log a failed replay upload to the database."""
    try:
        failed_upload = FailedUpload(
            filename=filename,
            file_size_bytes=file_size,
            replay_hash=replay_hash,
            replay_file_path=replay_file_path,
            error_type=error_type,
            error_message=error_message[:500],  # Limit length
            error_detail=error_detail[:2000] if error_detail else None,
            map_name=map_name,
            game_mode=game_mode,
            duration_seconds=duration_seconds,
            num_players=num_players
        )
        db.add(failed_upload)
        db.commit()
    except Exception:
        # Don't let logging failures break the main flow
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


class MatchResponse(BaseModel):
    """Response model for match details."""
    id: int
    played_at: datetime
    game_mode: str
    map_name: str
    duration_seconds: int
    replay_hash: str

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
async def upload_replay(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a SC2 replay file.

    Args:
        file: .SC2Replay file
        db: Database session

    Returns:
        ReplayUploadResponse with match details

    Raises:
        HTTPException: If replay parsing fails or is duplicate
    """
    # Validate file extension
    if not file.filename.endswith('.SC2Replay'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .SC2Replay files are accepted."
        )

    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.SC2Replay') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        start_time = time.time()

        # Parse the replay
        parse_start = time.time()
        replay_data = parse_replay(tmp_file_path)
        parse_time_ms = (time.time() - parse_start) * 1000

        # Validate replay data
        validation_start = time.time()
        is_valid, error_msg = validate_replay_data(replay_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Validation failed: {error_msg}")
        validation_time_ms = (time.time() - validation_start) * 1000

        # Check for duplicate
        duplicate_start = time.time()
        existing_match = db.query(Match).filter(
            Match.replay_hash == replay_data.replay_hash
        ).first()

        if existing_match:
            raise HTTPException(
                status_code=409,
                detail=f"Replay already uploaded. Match ID: {existing_match.id}"
            )
        duplicate_check_time_ms = (time.time() - duplicate_start) * 1000

        # Create match record
        match = Match(
            played_at=replay_data.played_at,
            game_mode=replay_data.game_mode,
            map_name=replay_data.map_name,
            duration_seconds=replay_data.duration_seconds,
            replay_file_path=None,  # We're not storing the file for now
            replay_hash=replay_data.replay_hash
        )
        db.add(match)
        db.flush()  # Get match.id

        # Update ratings and create match_players
        rating_start = time.time()
        RatingSystem.update_ratings_from_match(db, replay_data, match)
        rating_time_ms = (time.time() - rating_start) * 1000

        total_time_ms = (time.time() - start_time) * 1000

        return ReplayUploadResponse(
            match_id=match.id,
            map_name=match.map_name,
            game_mode=match.game_mode.value,
            played_at=match.played_at,
            duration_seconds=match.duration_seconds,
            num_players=len(replay_data.players),
            message="Replay processed successfully",
            processing_stats=ProcessingStats(
                parse_time_ms=round(parse_time_ms, 2),
                validation_time_ms=round(validation_time_ms, 2),
                duplicate_check_time_ms=round(duplicate_check_time_ms, 2),
                rating_update_time_ms=round(rating_time_ms, 2),
                total_time_ms=round(total_time_ms, 2)
            )
        )

    except ReplayParseError as e:
        # Log failed upload
        _log_failed_upload(
            db=db,
            filename=file.filename,
            file_size=len(content),
            error_type=UploadErrorType.PARSE_ERROR,
            error_message=str(e),
            error_detail=traceback.format_exc()
        )
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")
    except HTTPException as http_ex:
        # Log validation and other HTTP errors (except duplicates and already-logged winner determination)
        if http_ex.status_code != 409:
            # Skip logging if this is a winner determination error (already logged above)
            if "Unable to determine" in str(http_ex.detail):
                raise

            error_type = UploadErrorType.VALIDATION_ERROR
            if "Invalid game mode" in str(http_ex.detail) or "Invalid number of players" in str(http_ex.detail):
                error_type = UploadErrorType.UNSUPPORTED_MODE

            # Include metadata if replay_data was parsed
            extra_kwargs = {}
            if replay_data:
                extra_kwargs.update({
                    'replay_hash': replay_data.replay_hash,
                    'map_name': replay_data.map_name,
                    'game_mode': replay_data.game_mode.value if hasattr(replay_data.game_mode, 'value') else str(replay_data.game_mode),
                    'duration_seconds': replay_data.duration_seconds,
                    'num_players': len(replay_data.players)
                })

            _log_failed_upload(
                db=db,
                filename=file.filename,
                file_size=len(content),
                error_type=error_type,
                error_message=str(http_ex.detail),
                error_detail=traceback.format_exc(),
                **extra_kwargs
            )
        raise
    except Exception as e:
        # Log unexpected errors
        extra_kwargs = {}
        if replay_data:
            extra_kwargs.update({
                'replay_hash': replay_data.replay_hash,
                'map_name': replay_data.map_name,
                'game_mode': replay_data.game_mode.value if hasattr(replay_data.game_mode, 'value') else str(replay_data.game_mode),
                'duration_seconds': replay_data.duration_seconds,
                'num_players': len(replay_data.players)
            })

        _log_failed_upload(
            db=db,
            filename=file.filename,
            file_size=len(content),
            error_type=UploadErrorType.OTHER,
            error_message=str(e),
            error_detail=traceback.format_exc(),
            **extra_kwargs
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


@router.get("/matches", response_model=List[MatchResponse])
def get_matches(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get list of matches.

    Args:
        limit: Maximum number of matches to return
        offset: Number of matches to skip
        db: Database session

    Returns:
        List of MatchResponse objects
    """
    matches = db.query(Match).order_by(
        Match.played_at.desc()
    ).limit(limit).offset(offset).all()

    return [
        MatchResponse(
            id=m.id,
            played_at=m.played_at,
            game_mode=m.game_mode.value,
            map_name=m.map_name,
            duration_seconds=m.duration_seconds,
            replay_hash=m.replay_hash or ""
        )
        for m in matches
    ]


@router.get("/matches/{match_id}", response_model=MatchDetailResponse)
def get_match_details(
    match_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific match.

    Args:
        match_id: Match ID
        db: Database session

    Returns:
        MatchDetailResponse with full match details

    Raises:
        HTTPException: If match not found
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Get all participants
    match_players = db.query(MatchPlayer).filter(
        MatchPlayer.match_id == match_id
    ).all()

    players_data = []
    for mp in match_players:
        player = db.query(Player).filter(Player.id == mp.player_id).first()
        mmr_before = mp.mu_before - (3 * mp.sigma_before)
        mmr_after = mp.mu_after - (3 * mp.sigma_after)

        players_data.append(MatchPlayerResponse(
            player_name=player.name,
            team_number=mp.team_number,
            race=mp.race.value,
            won=bool(mp.won),
            mmr_before=mmr_before,
            mmr_after=mmr_after,
            mmr_change=mmr_after - mmr_before
        ))

    return MatchDetailResponse(
        match=MatchResponse(
            id=match.id,
            played_at=match.played_at,
            game_mode=match.game_mode.value,
            map_name=match.map_name,
            duration_seconds=match.duration_seconds,
            replay_hash=match.replay_hash or ""
        ),
        players=players_data
    )


@router.post("/upload-advanced", response_model=ReplayUploadResponse)
async def upload_replay_advanced(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a SC2 replay file with advanced metrics.

    This endpoint extracts detailed performance data including:
    - Economic metrics (resources, workers, spending)
    - Combat metrics (damage, kills, army value)
    - Impact scores (economic, combat, efficiency)
    - Player synergies

    Args:
        file: .SC2Replay file
        db: Database session

    Returns:
        ReplayUploadResponse with match details

    Raises:
        HTTPException: If replay parsing fails or is duplicate
    """
    # Validate file extension
    if not file.filename.endswith('.SC2Replay'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .SC2Replay files are accepted."
        )

    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.SC2Replay') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    replay_data = None  # Track for error handling

    try:
        start_time = time.time()

        # Parse the replay with advanced metrics
        parse_start = time.time()
        advanced_data = parse_replay_advanced(tmp_file_path)
        replay_data = advanced_data.basic_data
        parse_time_ms = (time.time() - parse_start) * 1000

        # Validate replay data
        validation_start = time.time()
        is_valid, error_msg = validate_replay_data(replay_data)
        if not is_valid:
            # Check if this is a winner determination error
            if "Unable to determine" in error_msg:
                # Save the replay file for manual review
                saved_path = _save_failed_replay_file(content, file.filename, replay_data.replay_hash)
                _log_failed_upload(
                    db=db,
                    filename=file.filename,
                    file_size=len(content),
                    error_type=UploadErrorType.WINNER_DETERMINATION,
                    error_message=error_msg,
                    error_detail=traceback.format_exc(),
                    replay_hash=replay_data.replay_hash,
                    map_name=replay_data.map_name,
                    game_mode=replay_data.game_mode.value if hasattr(replay_data.game_mode, 'value') else str(replay_data.game_mode),
                    duration_seconds=replay_data.duration_seconds,
                    num_players=len(replay_data.players),
                    replay_file_path=saved_path
                )
            raise HTTPException(status_code=400, detail=f"Validation failed: {error_msg}")
        validation_time_ms = (time.time() - validation_start) * 1000

        # Check for duplicate
        duplicate_start = time.time()
        existing_match = db.query(Match).filter(
            Match.replay_hash == replay_data.replay_hash
        ).first()

        if existing_match:
            raise HTTPException(
                status_code=409,
                detail=f"Replay already uploaded. Match ID: {existing_match.id}"
            )
        duplicate_check_time_ms = (time.time() - duplicate_start) * 1000

        # Create match record
        match = Match(
            played_at=replay_data.played_at,
            game_mode=replay_data.game_mode,
            map_name=replay_data.map_name,
            duration_seconds=replay_data.duration_seconds,
            replay_file_path=None,
            replay_hash=replay_data.replay_hash
        )
        db.add(match)
        db.flush()  # Get match.id

        # Update ratings and create match_players
        rating_start = time.time()
        RatingSystem.update_ratings_from_match(db, replay_data, match)

        # Save advanced metrics for each player
        for player_metrics in advanced_data.player_metrics:
            # Find the corresponding MatchPlayer
            player = db.query(Player).filter(Player.name == player_metrics.player_name).first()
            if player:
                match_player = db.query(MatchPlayer).filter(
                    MatchPlayer.match_id == match.id,
                    MatchPlayer.player_id == player.id
                ).first()

                if match_player:
                    # Save detailed metrics
                    ImpactService.save_match_metrics(db, match_player.id, player_metrics)

                    # Update player averages
                    ImpactService.update_player_averages(db, player.id)

        # Update synergies
        ImpactService.update_synergies(db, match.id)

        # Apply performance-based rating adjustments
        # This modifies TrueSkill ratings based on individual performance
        PerformanceRatingAdjuster.adjust_ratings_for_match(db, match.id)

        rating_time_ms = (time.time() - rating_start) * 1000

        total_time_ms = (time.time() - start_time) * 1000

        return ReplayUploadResponse(
            match_id=match.id,
            map_name=match.map_name,
            game_mode=match.game_mode.value,
            played_at=match.played_at,
            duration_seconds=match.duration_seconds,
            num_players=len(replay_data.players),
            message="Replay processed successfully with advanced metrics",
            processing_stats=ProcessingStats(
                parse_time_ms=round(parse_time_ms, 2),
                validation_time_ms=round(validation_time_ms, 2),
                duplicate_check_time_ms=round(duplicate_check_time_ms, 2),
                rating_update_time_ms=round(rating_time_ms, 2),
                total_time_ms=round(total_time_ms, 2)
            )
        )

    except ReplayParseError as e:
        # Log failed upload
        _log_failed_upload(
            db=db,
            filename=file.filename,
            file_size=len(content),
            error_type=UploadErrorType.PARSE_ERROR,
            error_message=str(e),
            error_detail=traceback.format_exc()
        )
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")
    except HTTPException as http_ex:
        # Log validation and other HTTP errors (except duplicates and already-logged winner determination)
        if http_ex.status_code != 409:
            # Skip logging if this is a winner determination error (already logged above)
            if "Unable to determine" in str(http_ex.detail):
                raise

            error_type = UploadErrorType.VALIDATION_ERROR
            if "Invalid game mode" in str(http_ex.detail) or "Invalid number of players" in str(http_ex.detail):
                error_type = UploadErrorType.UNSUPPORTED_MODE

            # Include metadata if replay_data was parsed
            extra_kwargs = {}
            if replay_data:
                extra_kwargs.update({
                    'replay_hash': replay_data.replay_hash,
                    'map_name': replay_data.map_name,
                    'game_mode': replay_data.game_mode.value if hasattr(replay_data.game_mode, 'value') else str(replay_data.game_mode),
                    'duration_seconds': replay_data.duration_seconds,
                    'num_players': len(replay_data.players)
                })

            _log_failed_upload(
                db=db,
                filename=file.filename,
                file_size=len(content),
                error_type=error_type,
                error_message=str(http_ex.detail),
                error_detail=traceback.format_exc(),
                **extra_kwargs
            )
        raise
    except Exception as e:
        # Log unexpected errors
        extra_kwargs = {}
        if replay_data:
            extra_kwargs.update({
                'replay_hash': replay_data.replay_hash,
                'map_name': replay_data.map_name,
                'game_mode': replay_data.game_mode.value if hasattr(replay_data.game_mode, 'value') else str(replay_data.game_mode),
                'duration_seconds': replay_data.duration_seconds,
                'num_players': len(replay_data.players)
            })

        _log_failed_upload(
            db=db,
            filename=file.filename,
            file_size=len(content),
            error_type=UploadErrorType.OTHER,
            error_message=str(e),
            error_detail=traceback.format_exc(),
            **extra_kwargs
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


@router.get("/matches/{match_id}/commentary")
def get_match_commentary(
    match_id: int,
    db: Session = Depends(get_db)
):
    """
    Get AI-generated commentary for a specific match.

    Analyzes match data and generates natural language insights including:
    - Match overview and key moments
    - Individual player performance analysis
    - MVP identification and reasoning
    - Team synergy analysis
    - Final match summary

    Args:
        match_id: Match ID
        db: Database session

    Returns:
        Dictionary with commentary sections

    Raises:
        HTTPException: If match not found or commentary generation fails
    """
    commentary = MatchCommentaryGenerator.generate_match_summary(db, match_id)

    if 'error' in commentary:
        raise HTTPException(status_code=404, detail=commentary['error'])

    return commentary


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
    db: Session = Depends(get_db)
):
    """
    Get list of failed replay uploads for manual review.

    Args:
        limit: Maximum number of results to return
        offset: Number of results to skip
        error_type: Filter by error type (parse_error, validation_error, winner_determination, etc.)
        reviewed: Filter by review status (true/false)
        db: Database session

    Returns:
        List of FailedUploadResponse objects
    """
    query = db.query(FailedUpload).order_by(FailedUpload.uploaded_at.desc())

    # Apply filters
    if error_type:
        try:
            error_enum = UploadErrorType(error_type)
            query = query.filter(FailedUpload.error_type == error_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid error_type: {error_type}")

    if reviewed is not None:
        query = query.filter(FailedUpload.reviewed == (1 if reviewed else 0))

    failed_uploads = query.limit(limit).offset(offset).all()

    return [
        FailedUploadResponse(
            id=fu.id,
            filename=fu.filename,
            file_size_bytes=fu.file_size_bytes,
            error_type=fu.error_type.value,
            error_message=fu.error_message,
            map_name=fu.map_name,
            game_mode=fu.game_mode,
            duration_seconds=fu.duration_seconds,
            num_players=fu.num_players,
            uploaded_at=fu.uploaded_at,
            reviewed=bool(fu.reviewed)
        )
        for fu in failed_uploads
    ]


class MarkReviewedRequest(BaseModel):
    """Request to mark failed upload as reviewed."""
    review_notes: Optional[str] = None


@router.patch("/failed-uploads/{upload_id}/reviewed")
def mark_upload_reviewed(
    upload_id: int,
    request: MarkReviewedRequest,
    db: Session = Depends(get_db)
):
    """
    Mark a failed upload as reviewed.

    Args:
        upload_id: Failed upload ID
        request: Optional review notes
        db: Database session

    Returns:
        Updated failed upload

    Raises:
        HTTPException: If upload not found
    """
    failed_upload = db.query(FailedUpload).filter(FailedUpload.id == upload_id).first()

    if not failed_upload:
        raise HTTPException(status_code=404, detail="Failed upload not found")

    failed_upload.reviewed = 1
    if request.review_notes:
        failed_upload.review_notes = request.review_notes

    db.commit()

    return FailedUploadResponse(
        id=failed_upload.id,
        filename=failed_upload.filename,
        file_size_bytes=failed_upload.file_size_bytes,
        error_type=failed_upload.error_type.value,
        error_message=failed_upload.error_message,
        map_name=failed_upload.map_name,
        game_mode=failed_upload.game_mode,
        duration_seconds=failed_upload.duration_seconds,
        num_players=failed_upload.num_players,
        uploaded_at=failed_upload.uploaded_at,
        reviewed=bool(failed_upload.reviewed)
    )


def _save_failed_replay_file(content: bytes, filename: str, replay_hash: str) -> str:
    """
    Save a failed replay file to persistent storage for manual review.

    Args:
        content: Raw replay file bytes
        filename: Original filename
        replay_hash: Replay hash for unique identification

    Returns:
        Path to saved file
    """
    # Create failed_replays directory if it doesn't exist
    failed_replays_dir = os.path.join(os.getcwd(), "failed_replays")
    os.makedirs(failed_replays_dir, exist_ok=True)

    # Use replay hash for unique filename
    safe_filename = f"{replay_hash}_{filename}"
    file_path = os.path.join(failed_replays_dir, safe_filename)

    with open(file_path, 'wb') as f:
        f.write(content)

    return file_path


class ManualWinnerRequest(BaseModel):
    """Request to manually specify winner for failed replay."""
    winner_team: int  # 1 or 2


@router.post("/failed-uploads/{upload_id}/set-winner", response_model=ReplayUploadResponse)
def set_manual_winner(
    upload_id: int,
    request: ManualWinnerRequest,
    db: Session = Depends(get_db)
):
    """
    Manually specify the winner for a failed replay and reprocess it.

    This endpoint is used when automatic winner determination fails but
    the user can manually determine the winner from the game stats.

    Args:
        upload_id: Failed upload ID
        request: Winner team number (1 or 2)
        db: Database session

    Returns:
        ReplayUploadResponse with processed match details

    Raises:
        HTTPException: If upload not found, file missing, or processing fails
    """
    # Validate winner_team
    if request.winner_team not in [1, 2]:
        raise HTTPException(
            status_code=400,
            detail="winner_team must be 1 or 2"
        )

    # Get the failed upload
    failed_upload = db.query(FailedUpload).filter(FailedUpload.id == upload_id).first()

    if not failed_upload:
        raise HTTPException(status_code=404, detail="Failed upload not found")

    # Check if replay file was saved
    if not failed_upload.replay_file_path or not os.path.exists(failed_upload.replay_file_path):
        raise HTTPException(
            status_code=404,
            detail="Replay file not found. Original file may not have been saved."
        )

    try:
        start_time = time.time()

        # Parse the replay with advanced metrics
        parse_start = time.time()
        advanced_data = parse_replay_advanced(failed_upload.replay_file_path)
        replay_data = advanced_data.basic_data
        parse_time_ms = (time.time() - parse_start) * 1000

        # Override the winner with manual determination
        replay_data.winner_team = request.winner_team

        # Validate replay data
        validation_start = time.time()
        is_valid, error_msg = validate_replay_data(replay_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Validation failed: {error_msg}")
        validation_time_ms = (time.time() - validation_start) * 1000

        # Check for duplicate
        duplicate_start = time.time()
        existing_match = db.query(Match).filter(
            Match.replay_hash == replay_data.replay_hash
        ).first()

        if existing_match:
            # Delete the failed upload record since we're reprocessing
            db.delete(failed_upload)
            db.commit()
            raise HTTPException(
                status_code=409,
                detail=f"Replay already processed. Match ID: {existing_match.id}"
            )
        duplicate_check_time_ms = (time.time() - duplicate_start) * 1000

        # Create match record
        match = Match(
            played_at=replay_data.played_at,
            game_mode=replay_data.game_mode,
            map_name=replay_data.map_name,
            duration_seconds=replay_data.duration_seconds,
            replay_file_path=failed_upload.replay_file_path,  # Keep the saved file
            replay_hash=replay_data.replay_hash
        )
        db.add(match)
        db.flush()  # Get match.id

        # Update ratings and create match_players
        rating_start = time.time()
        RatingSystem.update_ratings_from_match(db, replay_data, match)

        # Save advanced metrics for each player
        for player_metrics in advanced_data.player_metrics:
            # Find the corresponding MatchPlayer
            player = db.query(Player).filter(Player.name == player_metrics.player_name).first()
            if player:
                match_player = db.query(MatchPlayer).filter(
                    MatchPlayer.match_id == match.id,
                    MatchPlayer.player_id == player.id
                ).first()

                if match_player:
                    # Save detailed metrics
                    ImpactService.save_match_metrics(db, match_player.id, player_metrics)

                    # Update player averages
                    ImpactService.update_player_averages(db, player.id)

        # Update synergies
        ImpactService.update_synergies(db, match.id)

        # Apply performance-based rating adjustments
        PerformanceRatingAdjuster.adjust_ratings_for_match(db, match.id)

        rating_time_ms = (time.time() - rating_start) * 1000

        # Delete the failed upload record since processing succeeded
        db.delete(failed_upload)
        db.commit()

        total_time_ms = (time.time() - start_time) * 1000

        return ReplayUploadResponse(
            match_id=match.id,
            map_name=match.map_name,
            game_mode=match.game_mode.value,
            played_at=match.played_at,
            duration_seconds=match.duration_seconds,
            num_players=len(replay_data.players),
            message="Replay processed successfully with manual winner determination",
            processing_stats=ProcessingStats(
                parse_time_ms=round(parse_time_ms, 2),
                validation_time_ms=round(validation_time_ms, 2),
                duplicate_check_time_ms=round(duplicate_check_time_ms, 2),
                rating_update_time_ms=round(rating_time_ms, 2),
                total_time_ms=round(total_time_ms, 2)
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log the error but don't delete the failed upload
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reprocess replay: {str(e)}"
        )
