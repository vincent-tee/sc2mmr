"""
API endpoints for replay upload and management.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Any
from datetime import datetime
import os
import tempfile
import time
import logging

import trueskill

from ..database import get_db
from ..config import settings
from ..models import (
    Match,
    MatchPlayer,
    Player,
    FailedUpload,
    UploadErrorType,
    PerformanceFeatures,
    PlayerMatchMetrics,
    GameMode,
)
from ..replay_parser import (
    parse_replay,
    validate_replay_data,
    ReplayParseError,
    WinnerDeterminationError,
)
from ..rating_system import RatingSystem
from ..advanced_parser import parse_replay_advanced
from ..services import replay_storage
from ..services.ingestion import find_existing_match, ingest_match, save_advanced_metrics, post_process_match
from ..exceptions import ValidationError
from ..match_commentary import MatchCommentaryGenerator
from pydantic import BaseModel
import traceback

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/replays", tags=["replays"])


# Helper functions
def _reject_oversized_upload(content: bytes) -> None:
    """Enforce settings.max_replay_size_mb (real SC2 replays are ~1-5 MB)."""
    limit_bytes = settings.max_replay_size_mb * 1024 * 1024
    if len(content) > limit_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large ({len(content) / (1024 * 1024):.1f} MB). "
                f"Maximum replay size is {settings.max_replay_size_mb} MB."
            ),
        )


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
    # False when the replay was already tracked (exact re-upload or the same
    # game from another player) and the existing match was refreshed instead
    # of a new one being created. Ratings only change when this is True.
    created: bool = True
    message: str
    processing_stats: ProcessingStats

    class Config:
        from_attributes = True


class MatchPlayerSummary(BaseModel):
    """Simplified player info for match lists."""

    player_id: int
    player_name: str
    team_number: int
    race: str
    won: bool
    mmr_change: float
    mmr_before: Optional[float] = None
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
    # total_count is the count for the ACTIVE filters (drives pagination);
    # grand_total is the unfiltered archive size (drives header stats).
    total_count: int
    grand_total: int
    limit: int
    offset: int

    class Config:
        from_attributes = True


class MatchPlayerResponse(BaseModel):
    """Response model for match player details."""

    player_id: int
    player_name: str
    team_number: int
    race: str
    won: bool
    mmr_before: float
    mmr_after: float
    mmr_change: float

    # Score-screen stats (from PlayerMatchMetrics; None if never parsed/voided match)
    apm: Optional[float] = None
    minerals_collected: Optional[int] = None
    vespene_collected: Optional[int] = None
    total_resources_collected: Optional[int] = None
    resources_spent: Optional[int] = None
    spending_efficiency: Optional[float] = None
    workers_created: Optional[int] = None
    army_value_built: Optional[int] = None
    army_value_killed: Optional[int] = None
    army_value_lost: Optional[int] = None
    units_killed: Optional[int] = None
    units_lost: Optional[int] = None
    damage_dealt: Optional[int] = None
    damage_taken: Optional[int] = None
    kill_death_ratio: Optional[float] = None
    supply_block_seconds: Optional[int] = None

    class Config:
        from_attributes = True


class MatchDetailResponse(BaseModel):
    """Detailed match response with players."""

    match: MatchResponse
    players: List[MatchPlayerResponse]

    class Config:
        from_attributes = True


@router.post("/upload", response_model=ReplayUploadResponse)
def upload_replay(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
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

    content = file.file.read(settings.max_replay_size_mb * 1024 * 1024 + 1)
    _reject_oversized_upload(content)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".SC2Replay") as tmp_file:
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

        # If this is the same game already recorded under a different
        # uploader's file (same game_fingerprint, different replay_hash),
        # don't save a second copy of the replay on disk - just reuse the
        # match that's already there.
        duplicate = find_existing_match(db, replay_data)
        replay_file_path = None
        if (duplicate is None or duplicate.replay_hash == replay_data.replay_hash
                or replay_data.duration_seconds > duplicate.duration_seconds):
            replay_file_path = _save_replay_file(content, fn, replay_data.replay_hash)

        match, created = ingest_match(db, replay_data, replay_file_path)

        post_process_match(db, int(match.id), created, replay_file_path)

        if settings.upload_cc_enrichment_enabled:
            from ..services.cc_enrichment import enrich_match_with_cc_metrics_background

            # Runs after this response is sent, in its own DB session — a
            # slow or hung SC2 engine must never add latency to the upload.
            background_tasks.add_task(
                enrich_match_with_cc_metrics_background, int(match.id)
            )

        total_time_ms = (time.time() - start_time) * 1000

        return ReplayUploadResponse(
            match_id=int(match.id),
            map_name=str(match.map_name),
            game_mode=str(match.game_mode.value),
            played_at=match.played_at,
            duration_seconds=int(match.duration_seconds),
            num_players=len(replay_data.players),
            created=created,
            message=(
                "Replay processed successfully"
                if created
                else f"Already on the ladder - existing Match #{match.id} was refreshed"
            ),
            processing_stats=ProcessingStats(
                parse_time_ms=0.0,
                validation_time_ms=0.0,
                duplicate_check_time_ms=0.0,
                rating_update_time_ms=0.0,
                total_time_ms=round(total_time_ms, 2),
            ),
        )

    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    game_mode: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # Build a filtered base query. With no filters this is identical to
    # `db.query(Match)`, so behavior stays backward compatible.
    base_query = db.query(Match)

    # Optional game-mode filter (e.g. "3v3", "4v4"). Unknown modes are a
    # client bug (stale dropdown, typo'd URL) — fail loudly rather than
    # silently returning an empty archive.
    if game_mode:
        try:
            base_query = base_query.filter(Match.game_mode == GameMode(game_mode))
        except ValueError:
            valid = ", ".join(m.value for m in GameMode)
            raise HTTPException(
                status_code=422,
                detail=f"Unknown game_mode '{game_mode}'. Valid modes: {valid}",
            )

    # Optional search across the map name OR any participating player's name.
    # LIKE metacharacters in the term are escaped so "Data_Disruptor" or
    # "100%" search literally instead of acting as wildcards.
    if search and search.strip():
        term = (
            search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern = f"%{term}%"
        player_match_ids = (
            db.query(MatchPlayer.match_id)
            .join(Player, MatchPlayer.player_id == Player.id)
            .filter(Player.name.ilike(pattern, escape="\\"))
        )
        base_query = base_query.filter(
            or_(
                Match.map_name.ilike(pattern, escape="\\"),
                Match.id.in_(player_match_ids),
            )
        )

    # total_count reflects the FILTERED total so the frontend paginates
    # correctly; grand_total is the whole archive for header stats.
    grand_total = db.query(func.count(Match.id)).scalar() or 0
    total_count = base_query.count() if (game_mode or (search and search.strip())) else grand_total
    matches = (
        base_query.order_by(Match.played_at.desc())
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

            mmr_diff = round(float((mp.mmr_after or 0) - (mp.mmr_before or 0)), 1)
            if mp.won:
                winner_team = int(mp.team_number)

            summary = MatchPlayerSummary(
                player_id=int(p.id),
                player_name=str(p.name),
                team_number=int(mp.team_number),
                race=str(mp.race.value),
                won=bool(mp.won == 1),
                mmr_change=mmr_diff,
                mmr_before=float(mp.mmr_before or 0),
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
        grand_total=int(grand_total),
        limit=limit,
        offset=offset,
    )


@router.get("/matches/{match_id}", response_model=MatchDetailResponse)
def get_match_details(match_id: int, db: Session = Depends(get_db)):
    match: Any = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match_players = (
        db.query(MatchPlayer, Player, PlayerMatchMetrics)
        .join(Player, MatchPlayer.player_id == Player.id)
        .outerjoin(
            PlayerMatchMetrics, PlayerMatchMetrics.match_player_id == MatchPlayer.id
        )
        .filter(MatchPlayer.match_id == match_id)
        .all()
    )

    players_data = []
    for mp_obj, p_obj, metrics_obj in match_players:
        mp: Any = mp_obj
        p: Any = p_obj
        metrics: Any = metrics_obj
        mmr_b = float(mp.mmr_before or 0)
        mmr_a = float(mp.mmr_after or 0)
        players_data.append(
            MatchPlayerResponse(
                player_id=int(p.id),
                player_name=str(p.name),
                team_number=int(mp.team_number),
                race=str(mp.race.value),
                won=bool(mp.won == 1),
                mmr_before=mmr_b,
                mmr_after=mmr_a,
                mmr_change=mmr_a - mmr_b,
                apm=metrics.apm if metrics else None,
                minerals_collected=metrics.minerals_collected if metrics else None,
                vespene_collected=metrics.vespene_collected if metrics else None,
                total_resources_collected=(
                    metrics.total_resources_collected if metrics else None
                ),
                resources_spent=metrics.resources_spent if metrics else None,
                spending_efficiency=(
                    metrics.spending_efficiency if metrics else None
                ),
                workers_created=metrics.workers_created if metrics else None,
                army_value_built=metrics.army_value_built if metrics else None,
                army_value_killed=metrics.army_value_killed if metrics else None,
                army_value_lost=metrics.army_value_lost if metrics else None,
                units_killed=metrics.units_killed if metrics else None,
                units_lost=metrics.units_lost if metrics else None,
                damage_dealt=metrics.damage_dealt if metrics else None,
                damage_taken=metrics.damage_taken if metrics else None,
                kill_death_ratio=metrics.kill_death_ratio if metrics else None,
                supply_block_seconds=(
                    metrics.supply_block_seconds if metrics else None
                ),
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

    # Pre-match win probability. Most matches have this persisted from upload
    # time, but a handful of historical rows were never populated and would
    # otherwise render as a meaningless 50/50. For those, recompute the odds
    # from each team's stored pre-match TrueSkill ratings (mu/sigma before the
    # game) using the same function the balancer/predictor uses - a pure
    # function of the two teams' ratings, no ML model involved. The result is
    # not persisted (read-only endpoint); it's recomputed per request for the
    # few historical rows affected.
    team1_prob = match.predicted_team1_win_prob
    team2_prob = match.predicted_team2_win_prob
    if team1_prob is None or team2_prob is None:
        team1_ratings = [
            trueskill.Rating(mu=float(mp.mu_before), sigma=float(mp.sigma_before))
            for mp, _, _ in match_players
            if int(mp.team_number) == 1
        ]
        team2_ratings = [
            trueskill.Rating(mu=float(mp.mu_before), sigma=float(mp.sigma_before))
            for mp, _, _ in match_players
            if int(mp.team_number) == 2
        ]
        if team1_ratings and team2_ratings:
            team1_prob, team2_prob = RatingSystem.calculate_win_probability(
                team1_ratings, team2_ratings
            )

    return MatchDetailResponse(
        match=MatchResponse(
            id=int(match.id),
            played_at=match.played_at,
            game_mode=str(match.game_mode.value),
            map_name=str(match.map_name),
            duration_seconds=int(match.duration_seconds),
            replay_hash=str(match.replay_hash or ""),
            predicted_team1_win_prob=team1_prob,
            predicted_team2_win_prob=team2_prob,
            ml_predicted_win_prob=ml_win_prob,
        ),
        players=players_data,
    )


@router.get("/matches/{match_id}/download")
def download_replay(match_id: int, db: Session = Depends(get_db)):
    """
    Download the original .SC2Replay file for a match, for opening in the
    StarCraft II client. Not every match has a stored file (replay storage
    can be disabled, or it may predate the storage feature).
    """
    match: Any = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if not match.replay_hash:
        raise HTTPException(
            status_code=404, detail="No replay file was recorded for this match"
        )

    replay_bytes = replay_storage.fetch_replay_by_hash(str(match.replay_hash))
    if replay_bytes is None:
        raise HTTPException(
            status_code=404, detail="Replay file is no longer available"
        )

    download_name = f"{match.map_name}_{match.played_at.strftime('%Y-%m-%d')}.SC2Replay"
    return Response(
        content=replay_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@router.get("/matches/{match_id}/commentary")
def get_match_commentary(match_id: int, db: Session = Depends(get_db)):
    """
    Get AI-generated commentary for a match.
    """
    return MatchCommentaryGenerator.generate_match_summary(db, match_id)


def _save_failed_replay_file(content: bytes, filename: str, replay_hash: str) -> str:
    return replay_storage.save_failed_replay(content, filename, replay_hash)


def _save_replay_file(content: bytes, filename: str, replay_hash: str) -> Optional[str]:
    return replay_storage.save_replay(content, replay_hash)


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
            # Check if replay file exists (downloads a temp copy in GCS mode)
            local_path = replay_storage.materialize_local_copy(
                str(match.replay_file_path or "")
            )
            if not local_path:
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
                db, local_path, int(match.id)
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


class RetryFailedUploadResponse(BaseModel):
    """Response for a failed-upload retry attempt."""

    upload_id: int
    status: str  # "recovered" | "still_failing" | "file_missing"
    match_id: Optional[int] = None
    detail: Optional[str] = None


@router.post(
    "/failed-uploads/{upload_id}/retry", response_model=RetryFailedUploadResponse
)
def retry_failed_upload(upload_id: int, db: Session = Depends(get_db)):
    """
    Re-parse a previously failed replay against the current parser and, if it
    now succeeds, ingest it as a real match (same pipeline as /upload).

    Several historical failures (map_name=None crashing calculate_game_fingerprint,
    stale winner-determination edge cases) are now fixed in the parser but the
    original replay files were never re-processed. This recovers that data
    instead of leaving it stranded in failed_uploads/failed_replays.
    """
    failed_upload = db.query(FailedUpload).filter(FailedUpload.id == upload_id).first()
    if not failed_upload:
        raise HTTPException(status_code=404, detail="Failed upload not found")

    file_path = replay_storage.materialize_local_copy(
        str(failed_upload.replay_file_path or "")
    )
    if not file_path:
        return RetryFailedUploadResponse(
            upload_id=upload_id,
            status="file_missing",
            detail="Original replay file is no longer available",
        )

    try:
        replay_data = parse_replay(file_path)
    except Exception as e:
        return RetryFailedUploadResponse(
            upload_id=upload_id, status="still_failing", detail=str(e)
        )

    is_valid, error_msg = validate_replay_data(replay_data)
    if not is_valid:
        return RetryFailedUploadResponse(
            upload_id=upload_id, status="still_failing", detail=error_msg
        )

    try:
        match, created = ingest_match(
            db, replay_data, failed_upload.replay_file_path,
            failed_upload_id=upload_id,
        )
    except ValidationError as exc:
        return RetryFailedUploadResponse(
            upload_id=upload_id, status="still_failing", detail=str(exc)
        )

    post_process_match(db, int(match.id), created, file_path)

    logger.info(f"Recovered failed upload {upload_id} as match {match.id}")
    return RetryFailedUploadResponse(
        upload_id=upload_id, status="recovered", match_id=int(match.id)
    )


@router.post("/failed-uploads/retry-all", response_model=List[RetryFailedUploadResponse])
def retry_all_failed_uploads(
    limit: int = 200, db: Session = Depends(get_db)
):
    """
    Retry every unreviewed failed upload against the current parser.

    Intended as a one-off/periodic sweep after a parser bug fix (see
    /failed-uploads/{id}/retry for the per-file semantics).
    """
    ids = [
        row.id
        for row in db.query(FailedUpload.id)
        .filter(FailedUpload.reviewed == 0)
        .limit(limit)
        .all()
    ]
    results = []
    for upload_id in ids:
        try:
            results.append(retry_failed_upload(upload_id, db))
        except HTTPException:
            continue
    recovered = sum(1 for r in results if r.status == "recovered")
    logger.info(f"Retry sweep: {recovered}/{len(results)} failed uploads recovered")
    return results


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

    # Check if replay file was saved; parsers need a real local file, so a
    # gs:// stored path is downloaded to a temp file first.
    local_replay_path = replay_storage.materialize_local_copy(
        str(failed_upload.replay_file_path or "")
    )
    if not local_replay_path:
        raise HTTPException(
            status_code=404,
            detail="Replay file not found. Original file may not have been saved.",
        )

    replay_data = None
    try:
        start_time = time.time()

        # Parse the replay with advanced metrics
        advanced_data = parse_replay_advanced(
            local_replay_path, manual_winner_team=request.winner_team
        )
        replay_data = advanced_data.basic_data

        # Validate replay data
        is_valid, error_msg = validate_replay_data(replay_data)
        if not is_valid:
            raise HTTPException(
                status_code=400, detail=f"Validation failed: {error_msg}"
            )

        match, created = ingest_match(
            db, replay_data, failed_upload.replay_file_path,
            save_metrics=lambda work, recorded: save_advanced_metrics(work, recorded, advanced_data),
            require_experience=False, failed_upload_id=upload_id,
        )

        post_process_match(db, int(match.id), created, local_replay_path)

        return ReplayUploadResponse(
            match_id=int(match.id),
            map_name=str(match.map_name),
            game_mode=str(match.game_mode.value),
            played_at=match.played_at,
            duration_seconds=int(match.duration_seconds),
            num_players=len(replay_data.players),
            created=created,
            message="Replay processed successfully with manual winner determination",
            processing_stats=ProcessingStats(
                parse_time_ms=0,
                validation_time_ms=0,
                duplicate_check_time_ms=0,
                rating_update_time_ms=0,
                total_time_ms=round((time.time() - start_time) * 1000, 2),
            ),
        )

    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
def upload_replay_advanced(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """
    Upload and process a SC2 replay file with advanced metrics.
    """
    fn: str = str(file.filename) if file.filename else "unknown.SC2Replay"
    logger.info(f"[UPLOAD-ADV] Starting upload: {fn}")

    if not fn.endswith(".SC2Replay"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .SC2Replay files are accepted.",
        )

    content = file.file.read(settings.max_replay_size_mb * 1024 * 1024 + 1)
    _reject_oversized_upload(content)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".SC2Replay") as tmp_file:
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
        logger.info(f"[UPLOAD-ADV] {fn}: File saved to temp ({len(content)} bytes)")

    replay_data = None
    try:
        start_time = time.time()
        step_times: dict = {}

        # Parse with advanced metrics
        step_start = time.time()
        advanced_data = parse_replay_advanced(tmp_file_path)
        replay_data = advanced_data.basic_data
        step_times["parse"] = (time.time() - step_start) * 1000
        logger.info(f"[UPLOAD-ADV] {fn}: Parse complete ({step_times['parse']:.0f}ms)")

        # Validate
        step_start = time.time()
        is_valid, error_msg = validate_replay_data(replay_data)
        step_times["validate"] = (time.time() - step_start) * 1000
        logger.info(f"[UPLOAD-ADV] {fn}: Validation complete ({step_times['validate']:.0f}ms)")
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

        # Same game already recorded under a different uploader's file?
        # Don't save a second copy of the replay on disk.
        step_start = time.time()
        duplicate = find_existing_match(db, replay_data)
        replay_file_path = None
        if (duplicate is None or duplicate.replay_hash == replay_data.replay_hash
                or replay_data.duration_seconds > duplicate.duration_seconds):
            replay_file_path = _save_replay_file(content, fn, replay_data.replay_hash)
        step_times["save_file"] = (time.time() - step_start) * 1000
        logger.info(f"[UPLOAD-ADV] {fn}: File saved ({step_times['save_file']:.0f}ms)")

        step_start = time.time()
        match, created = ingest_match(
            db, replay_data, replay_file_path,
            save_metrics=lambda work, recorded: save_advanced_metrics(work, recorded, advanced_data),
        )
        step_times["rating_update"] = (time.time() - step_start) * 1000

        post_process_match(db, int(match.id), created, replay_file_path, optimize=True)

        total_time_ms = (time.time() - start_time) * 1000

        # Log summary with all step timings
        timing_summary = ", ".join([f"{k}={v:.0f}ms" for k, v in step_times.items()])
        logger.info(f"[UPLOAD-ADV] {fn}: COMPLETE in {total_time_ms:.0f}ms | {timing_summary}")

        return ReplayUploadResponse(
            match_id=int(match.id),
            map_name=str(match.map_name),
            game_mode=str(match.game_mode.value),
            played_at=match.played_at,
            duration_seconds=int(match.duration_seconds),
            num_players=len(replay_data.players),
            created=created,
            message=(
                "Replay processed successfully with advanced metrics"
                if created
                else f"Already on the ladder - existing Match #{match.id} was refreshed"
            ),
            processing_stats=ProcessingStats(
                parse_time_ms=round(step_times.get("parse", 0), 2),
                validation_time_ms=round(step_times.get("validate", 0), 2),
                duplicate_check_time_ms=round(step_times.get("upsert", 0), 2),
                rating_update_time_ms=round(step_times.get("rating_update", 0), 2),
                total_time_ms=round(total_time_ms, 2),
            ),
        )

    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except ReplayParseError as e:
        logger.error(f"[UPLOAD-ADV] {fn}: PARSE ERROR - {str(e)}")
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
        logger.warning(f"[UPLOAD-ADV] {fn}: HTTP EXCEPTION - {http_ex.detail}")
        raise
    except Exception as e:
        logger.error(f"[UPLOAD-ADV] {fn}: UNEXPECTED ERROR - {str(e)}", exc_info=True)
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
