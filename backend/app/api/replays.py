"""
API endpoints for replay upload and management.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import tempfile
import time

from ..database import get_db
from ..models import Match, MatchPlayer, Player
from ..replay_parser import parse_replay, validate_replay_data, ReplayParseError
from ..rating_system import RatingSystem
from ..advanced_parser import parse_replay_advanced
from ..impact_service import ImpactService
from ..performance_rating import PerformanceRatingAdjuster
from ..match_commentary import MatchCommentaryGenerator
from pydantic import BaseModel


router = APIRouter(prefix="/replays", tags=["replays"])


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
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
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
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
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
