"""
ReplayService - Business logic for replay upload and processing.

This service extracts the core business logic from the replay API routes,
providing a clean separation between HTTP handling and domain logic.

Usage:
    from app.services.replay_service import ReplayService

    service = ReplayService(db)
    result = service.process_replay(file_content, filename)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
import hashlib
import logging
import os
import tempfile
import time
import traceback

from sqlalchemy.orm import Session

from ..config import settings
from ..exceptions import (
    ReplayParseError,
    WinnerDeterminationError,
    DuplicateReplayError,
    ValidationError,
)
from ..models import (
    Match,
    MatchPlayer,
    Player,
    FailedUpload,
    UploadErrorType,
)
from ..replay_parser import (
    parse_replay,
    validate_replay_data,
    ReplayData,
    calculate_replay_hash,
    determine_game_mode,
    ReplayParseError as ParserReplayParseError,
    WinnerDeterminationError as ParserWinnerDeterminationError,
)
from ..advanced_parser import parse_replay_advanced, AdvancedReplayData
from ..rating_system import RatingSystem
from ..impact_service import ImpactService
from ..performance_rating import PerformanceRatingAdjuster
from ..auto_adaptive import trigger_auto_optimization
from .ml_features_service import MLFeaturesService

logger = logging.getLogger(__name__)


@dataclass
class FailedUploadData:
    """Data for a failed upload record."""

    filename: str
    file_size: int
    error_type: UploadErrorType
    error_message: str
    error_detail: str
    replay_hash: Optional[str] = None
    map_name: Optional[str] = None
    game_mode: Optional[str] = None
    duration_seconds: Optional[int] = None
    num_players: Optional[int] = None
    replay_file_path: Optional[str] = None


@dataclass
class ProcessingStats:
    """Statistics about the processing stages."""

    parse_time_ms: float
    validation_time_ms: float
    duplicate_check_time_ms: float
    rating_update_time_ms: float
    total_time_ms: float


@dataclass
class ReplayProcessingResult:
    """Result of successful replay processing."""

    match: Match
    num_players: int
    processing_stats: ProcessingStats
    message: str


class ReplayService:
    """
    Service for processing SC2 replay files.

    Handles the complete replay processing pipeline:
    1. Parsing replay files
    2. Validating replay data
    3. Checking for duplicates
    4. Creating match records
    5. Updating player ratings
    6. Saving advanced metrics (optional)

    Attributes:
        db: SQLAlchemy database session
    """

    # File extension for SC2 replays
    REPLAY_EXTENSION = ".SC2Replay"

    def __init__(self, db: Session):
        """
        Initialize the ReplayService.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def process_replay(
        self,
        file_content: bytes,
        filename: str,
        use_advanced_parser: bool = True,
    ) -> ReplayProcessingResult:
        """
        Process a replay file and update ratings.

        This is the main entry point for replay processing. It handles:
        - File validation
        - Parsing (basic or advanced)
        - Duplicate detection
        - Match creation
        - Rating updates

        Args:
            file_content: Raw bytes of the replay file
            filename: Original filename
            use_advanced_parser: Whether to use advanced metrics extraction

        Returns:
            ReplayProcessingResult with match details and stats

        Raises:
            ValidationError: If file type is invalid
            ReplayParseError: If parsing fails
            WinnerDeterminationError: If winner cannot be determined
            DuplicateReplayError: If replay already exists
        """
        self._validate_file_extension(filename)

        tmp_file_path = self._save_to_temp_file(file_content)

        try:
            return self._process_replay_file(
                tmp_file_path,
                file_content,
                filename,
                use_advanced_parser,
            )
        finally:
            self._cleanup_temp_file(tmp_file_path)

    def process_replay_with_manual_winner(
        self,
        file_content: bytes,
        filename: str,
        winner_team: int,
        use_advanced_parser: bool = True,
    ) -> ReplayProcessingResult:
        """
        Process a replay file with manually specified winner.

        Used when automatic winner determination fails but the user
        can manually determine the winner from game stats.

        Args:
            file_content: Raw bytes of the replay file
            filename: Original filename
            winner_team: Winning team number (1 or 2)
            use_advanced_parser: Whether to use advanced metrics extraction

        Returns:
            ReplayProcessingResult with match details and stats

        Raises:
            ValidationError: If winner_team is invalid or file type is wrong
            ReplayParseError: If parsing fails
            DuplicateReplayError: If replay already exists
        """
        if winner_team not in (1, 2):
            raise ValidationError(f"winner_team must be 1 or 2, got: {winner_team}")

        self._validate_file_extension(filename)

        tmp_file_path = self._save_to_temp_file(file_content)

        try:
            return self._process_replay_file(
                tmp_file_path,
                file_content,
                filename,
                use_advanced_parser,
                manual_winner_team=winner_team,
            )
        finally:
            self._cleanup_temp_file(tmp_file_path)

    def _validate_file_extension(self, filename: str) -> None:
        """
        Validate that the file has the correct extension.

        Args:
            filename: Name of the file to validate

        Raises:
            ValidationError: If file extension is invalid
        """
        if not filename.endswith(self.REPLAY_EXTENSION):
            raise ValidationError(
                f"Invalid file type. Only {self.REPLAY_EXTENSION} files are accepted."
            )

    def _save_to_temp_file(self, content: bytes) -> str:
        """
        Save content to a temporary file.

        Args:
            content: File content as bytes

        Returns:
            Path to the temporary file
        """
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=self.REPLAY_EXTENSION
        ) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name

    def _cleanup_temp_file(self, file_path: str) -> None:
        """
        Remove a temporary file if it exists.

        Args:
            file_path: Path to the file to remove
        """
        if os.path.exists(file_path):
            os.remove(file_path)

    def _process_replay_file(
        self,
        file_path: str,
        file_content: bytes,
        filename: str,
        use_advanced_parser: bool,
        manual_winner_team: Optional[int] = None,
    ) -> ReplayProcessingResult:
        """
        Core replay processing logic with error handling.

        Args:
            file_path: Path to the temporary replay file
            file_content: Original file content (for error handling)
            filename: Original filename
            use_advanced_parser: Whether to use advanced metrics
            manual_winner_team: Optional manual winner (1 or 2)

        Returns:
            ReplayProcessingResult with match details

        Raises:
            ReplayParseError: If parsing fails
            WinnerDeterminationError: If winner cannot be determined
            DuplicateReplayError: If replay already exists
        """
        replay_data = None

        try:
            return self._execute_replay_processing(
                file_path, use_advanced_parser, manual_winner_team
            )

        except (ParserWinnerDeterminationError, WinnerDeterminationError) as e:
            self._handle_winner_determination_error(
                e, file_content, filename, file_path, replay_data
            )
            raise WinnerDeterminationError(str(e))

        except (ParserReplayParseError, ReplayParseError) as e:
            self._handle_parse_error(e, file_content, filename)
            raise ReplayParseError(str(e))

        except DuplicateReplayError:
            raise

        except Exception as e:
            self._handle_unexpected_error(e, file_content, filename, replay_data)
            raise ReplayParseError(f"Unexpected error: {str(e)}")

    def _execute_replay_processing(
        self,
        file_path: str,
        use_advanced_parser: bool,
        manual_winner_team: Optional[int] = None,
    ) -> ReplayProcessingResult:
        """
        Execute the replay processing pipeline.

        Args:
            file_path: Path to the replay file
            use_advanced_parser: Whether to use advanced metrics
            manual_winner_team: Optional manual winner (1 or 2)

        Returns:
            ReplayProcessingResult with match details
        """
        start_time = time.time()

        # Parse replay
        parse_start = time.time()
        replay_data, advanced_data = self._parse_replay(
            file_path, use_advanced_parser, manual_winner_team
        )
        parse_time_ms = (time.time() - parse_start) * 1000

        # Validate and check duplicate
        validation_time_ms, duplicate_check_time_ms = self._validate_and_check(
            replay_data
        )

        # Create match and update ratings
        match = self._create_match(replay_data)
        rating_start = time.time()
        self._update_player_ratings(match, replay_data)

        # Extract and save ML-ready features (SPEC-ML-001)
        self._extract_ml_features(file_path, match.id)

        if advanced_data:
            self._save_advanced_metrics(match, advanced_data)

        # Trigger Online Learning Engine (Self-Improving Model)
        self._trigger_online_learning(match, replay_data)

        rating_time_ms = (time.time() - rating_start) * 1000
        total_time_ms = (time.time() - start_time) * 1000

        return self._build_result(
            match,
            replay_data,
            advanced_data,
            parse_time_ms,
            validation_time_ms,
            duplicate_check_time_ms,
            rating_time_ms,
            total_time_ms,
        )

    def _validate_and_check(self, replay_data: ReplayData) -> Tuple[float, float]:
        """
        Validate replay and check for duplicates.

        Returns:
            Tuple of (validation_time_ms, duplicate_check_time_ms)
        """
        validation_start = time.time()
        self._validate_replay(replay_data)
        validation_time_ms = (time.time() - validation_start) * 1000

        duplicate_start = time.time()
        self._check_duplicate(replay_data.replay_hash)
        duplicate_check_time_ms = (time.time() - duplicate_start) * 1000

        return validation_time_ms, duplicate_check_time_ms

    def _build_result(
        self,
        match: Match,
        replay_data: ReplayData,
        advanced_data: Optional[AdvancedReplayData],
        parse_time_ms: float,
        validation_time_ms: float,
        duplicate_check_time_ms: float,
        rating_time_ms: float,
        total_time_ms: float,
    ) -> ReplayProcessingResult:
        """Build the processing result with stats."""
        message = "Replay processed successfully"
        if advanced_data:
            message += " with advanced metrics"

        return ReplayProcessingResult(
            match=match,
            num_players=len(replay_data.players),
            processing_stats=ProcessingStats(
                parse_time_ms=round(parse_time_ms, 2),
                validation_time_ms=round(validation_time_ms, 2),
                duplicate_check_time_ms=round(duplicate_check_time_ms, 2),
                rating_update_time_ms=round(rating_time_ms, 2),
                total_time_ms=round(total_time_ms, 2),
            ),
            message=message,
        )

    def _parse_replay(
        self,
        file_path: str,
        use_advanced_parser: bool,
        manual_winner_team: Optional[int] = None,
    ) -> Tuple[ReplayData, Optional[AdvancedReplayData]]:
        """
        Parse the replay file.

        Args:
            file_path: Path to the replay file
            use_advanced_parser: Whether to extract advanced metrics
            manual_winner_team: Optional manual winner override

        Returns:
            Tuple of (basic_data, advanced_data or None)
        """
        if use_advanced_parser:
            advanced_data = parse_replay_advanced(
                file_path, manual_winner_team=manual_winner_team
            )
            return advanced_data.basic_data, advanced_data
        else:
            basic_data = parse_replay(file_path, manual_winner_team=manual_winner_team)
            return basic_data, None

    def _validate_replay(self, replay_data: ReplayData) -> None:
        """
        Validate parsed replay data.

        Args:
            replay_data: Parsed replay data to validate

        Raises:
            ValidationError: If validation fails
        """
        is_valid, error_msg = validate_replay_data(replay_data)
        if not is_valid:
            raise ValidationError(f"Validation failed: {error_msg}")

    def _check_duplicate(self, replay_hash: str) -> None:
        """
        Check if a replay with the same hash already exists.

        Args:
            replay_hash: Hash of the replay file

        Raises:
            DuplicateReplayError: If replay already exists
        """
        existing_match = (
            self.db.query(Match).filter(Match.replay_hash == replay_hash).first()
        )

        if existing_match:
            raise DuplicateReplayError(replay_hash, existing_match.id)

    def _create_match(self, replay_data: ReplayData) -> Match:
        """
        Create a match record in the database.

        Args:
            replay_data: Parsed replay data

        Returns:
            Created Match object with ID assigned
        """
        match = Match(
            played_at=replay_data.played_at,
            game_mode=replay_data.game_mode,
            map_name=replay_data.map_name,
            duration_seconds=replay_data.duration_seconds,
            replay_file_path=None,
            replay_hash=replay_data.replay_hash,
        )
        self.db.add(match)
        self.db.flush()  # Get match.id
        return match

    def _update_player_ratings(self, match: Match, replay_data: ReplayData) -> None:
        """
        Update player ratings based on match results.

        Args:
            match: The match record
            replay_data: Parsed replay data with player info
        """
        RatingSystem.update_ratings_from_match(self.db, replay_data, match)

    def _extract_ml_features(self, replay_path: str, match_id: int) -> None:
        """
        Extract ML-ready features from replay and save to database.

        This extracts build orders, upgrades, abilities, and macro metrics
        from the replay file and stores them in the performance_features table.

        Features are extracted even if parsing fails - continues gracefully.

        Args:
            replay_path: Path to the replay file
            match_id: ID of the created match
        """
        try:
            logger.info(f"Extracting ML features for match_id={match_id}")
            results = MLFeaturesService.extract_and_save_ml_features(
                self.db, replay_path, match_id
            )

            if results:
                success_count = sum(1 for v in results.values() if v)
                logger.info(
                    f"ML features extraction complete: "
                    f"{success_count}/{len(results)} players succeeded"
                )
            else:
                logger.warning(
                    f"ML features extraction returned no results for match_id={match_id}"
                )

        except Exception as e:
            logger.warning(
                f"Failed to extract ML features for match_id={match_id}: {e}",
                exc_info=True,
            )
            # Continue - don't fail replay upload if ML extraction fails

    def _save_advanced_metrics(
        self, match: Match, advanced_data: AdvancedReplayData
    ) -> None:
        """
        Save advanced performance metrics for each player.

        This includes:
        - Detailed match metrics (damage, resources, etc.)
        - Player average updates
        - Synergy calculations
        - Performance-based rating adjustments
        - Auto-optimization trigger

        Args:
            match: The match record
            advanced_data: Advanced replay data with player metrics
        """
        try:
            self._save_player_metrics(match.id, advanced_data)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save impact metrics: {e}", exc_info=True)
            self.db.rollback()

        self._update_synergies(match.id)
        self._apply_performance_adjustments(match.id)
        self._trigger_optimization()

    def _save_player_metrics(
        self, match_id: int, advanced_data: AdvancedReplayData
    ) -> None:
        """
        Save metrics for each player in the match.

        Args:
            match_id: The match ID
            advanced_data: Advanced replay data with player metrics
        """
        for player_metrics in advanced_data.player_metrics:
            player = (
                self.db.query(Player)
                .filter(Player.name == player_metrics.player_name)
                .first()
            )
            if not player:
                continue

            match_player = (
                self.db.query(MatchPlayer)
                .filter(
                    MatchPlayer.match_id == match_id,
                    MatchPlayer.player_id == player.id,
                )
                .first()
            )

            if match_player:
                ImpactService.save_match_metrics(
                    self.db, match_player.id, player_metrics
                )
                ImpactService.update_player_averages(self.db, player.id)

    def _update_synergies(self, match_id: int) -> None:
        """
        Update player synergy scores for the match.

        Args:
            match_id: The match ID
        """
        try:
            ImpactService.update_synergies(self.db, match_id)
        except Exception as e:
            logger.error(f"Failed to update synergies: {e}", exc_info=True)

    def _apply_performance_adjustments(self, match_id: int) -> None:
        """
        Apply performance-based rating adjustments.

        Args:
            match_id: The match ID
        """
        try:
            PerformanceRatingAdjuster.adjust_ratings_for_match(self.db, match_id)
        except Exception as e:
            logger.error(
                f"Failed to apply performance-based adjustments: {e}",
                exc_info=True,
            )

    def _trigger_online_learning(self, match: Match, replay_data: ReplayData) -> None:
        """
        Trigger the Online Learning Engine to record match outcome and improve models.

        Args:
            match: The created match record
            replay_data: Parsed replay data
        """
        try:
            from ..online_learning import OnlineLearningEngine

            # Determine if team 1 won
            team1_won = any(p.won for p in replay_data.players if p.team == 1)

            logger.info(f"Triggering OnlineLearningEngine for match_id={match.id}")
            engine = OnlineLearningEngine(self.db)
            engine.record_outcome(match.id, team1_won)

        except Exception as e:
            logger.warning(
                f"Failed to trigger OnlineLearningEngine for match_id={match.id}: {e}",
                exc_info=True,
            )

    def _trigger_optimization(self) -> None:
        """Trigger auto-optimization if threshold reached."""
        try:
            optimization_result = trigger_auto_optimization(self.db)
            if optimization_result:
                logger.info(
                    f"Auto-optimization triggered: {optimization_result.get('suggestion')} "
                    f"(confidence: {optimization_result.get('confidence', 0):.2f})"
                )
        except Exception as e:
            logger.warning(f"Auto-optimization failed: {e}", exc_info=False)

    def _handle_winner_determination_error(
        self,
        error: Exception,
        file_content: bytes,
        filename: str,
        file_path: str,
        replay_data: Optional[ReplayData],
    ) -> None:
        """
        Handle winner determination errors by logging and saving replay.

        Args:
            error: The error that occurred
            file_content: Original file content
            filename: Original filename
            file_path: Path to temp file (for extracting metadata)
            replay_data: Parsed replay data (if available)
        """
        logger.warning(
            f"WinnerDeterminationError for file '{filename}': {str(error)[:200]}...",
            exc_info=False,
        )

        # Extract metadata for failed upload record
        metadata = self._extract_replay_metadata(file_path, replay_data)

        # Save replay file for manual review
        saved_path = None
        if metadata.get("replay_hash"):
            saved_path = self._save_failed_replay_file(
                file_content, filename, metadata["replay_hash"]
            )

        self._log_failed_upload(
            filename=filename,
            file_size=len(file_content),
            error_type=UploadErrorType.WINNER_DETERMINATION,
            error_message=str(error),
            error_detail=traceback.format_exc(),
            replay_file_path=saved_path,
            replay_hash=metadata.get("replay_hash"),
            map_name=metadata.get("map_name"),
            game_mode=metadata.get("game_mode"),
            duration_seconds=metadata.get("duration_seconds"),
            num_players=metadata.get("num_players"),
        )

    def _handle_parse_error(
        self,
        error: Exception,
        file_content: bytes,
        filename: str,
    ) -> None:
        """
        Handle parse errors by logging the failure.

        Args:
            error: The error that occurred
            file_content: Original file content
            filename: Original filename
        """
        logger.error(
            f"ReplayParseError for file '{filename}': {str(error)[:200]}...",
            exc_info=False,
        )

        self._log_failed_upload(
            filename=filename,
            file_size=len(file_content),
            error_type=UploadErrorType.PARSE_ERROR,
            error_message=str(error),
            error_detail=traceback.format_exc(),
        )

    def _handle_unexpected_error(
        self,
        error: Exception,
        file_content: bytes,
        filename: str,
        replay_data: Optional[ReplayData],
    ) -> None:
        """
        Handle unexpected errors by logging with metadata.

        Args:
            error: The error that occurred
            file_content: Original file content
            filename: Original filename
            replay_data: Parsed replay data (if available)
        """
        logger.error(
            f"Unexpected error processing replay '{filename}': {str(error)}",
            exc_info=True,
        )

        extra_kwargs: Dict[str, Any] = {}
        if replay_data:
            extra_kwargs = self._extract_metadata_from_replay_data(replay_data)

        self._log_failed_upload(
            filename=filename,
            file_size=len(file_content),
            error_type=UploadErrorType.OTHER,
            error_message=str(error),
            error_detail=traceback.format_exc(),
            **extra_kwargs,
        )

    def _extract_replay_metadata(
        self, file_path: str, replay_data: Optional[ReplayData]
    ) -> Dict[str, Any]:
        """
        Extract metadata from replay file or parsed data.

        Args:
            file_path: Path to the replay file
            replay_data: Already parsed replay data (if available)

        Returns:
            Dictionary with metadata fields
        """
        if replay_data:
            return self._extract_metadata_from_replay_data(replay_data)

        # Try to extract minimal metadata from file
        try:
            import sc2reader  # type: ignore

            replay = sc2reader.load_replay(file_path, load_level=2)  # type: ignore
            replay_hash = calculate_replay_hash(file_path)
            human_players = [p for p in replay.players if p.is_human]
            num_players = len(human_players)
            game_mode_enum = determine_game_mode(num_players)

            return {
                "replay_hash": replay_hash,
                "map_name": replay.map_name,
                "game_mode": game_mode_enum.value if game_mode_enum else None,
                "duration_seconds": (
                    replay.game_length.seconds
                    if hasattr(replay, "game_length")
                    else None
                ),
                "num_players": num_players,
            }
        except Exception:
            return {}

    def _extract_metadata_from_replay_data(
        self, replay_data: ReplayData
    ) -> Dict[str, Any]:
        """
        Extract metadata from parsed replay data.

        Args:
            replay_data: Parsed replay data

        Returns:
            Dictionary with metadata fields
        """
        return {
            "replay_hash": replay_data.replay_hash,
            "map_name": replay_data.map_name,
            "game_mode": (
                replay_data.game_mode.value
                if hasattr(replay_data.game_mode, "value")
                else str(replay_data.game_mode)
            ),
            "duration_seconds": replay_data.duration_seconds,
            "num_players": len(replay_data.players),
        }

    def _save_failed_replay_file(
        self, content: bytes, filename: str, replay_hash: str
    ) -> str:
        """
        Save a failed replay file for manual review.

        Args:
            content: Raw replay file bytes
            filename: Original filename
            replay_hash: Replay hash for unique identification

        Returns:
            Path to saved file
        """
        failed_replays_dir = os.path.join(os.getcwd(), settings.failed_replays_dir)
        os.makedirs(failed_replays_dir, exist_ok=True)

        safe_filename = f"{replay_hash}_{filename}"
        file_path = os.path.join(failed_replays_dir, safe_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        return file_path

    def _log_failed_upload(
        self,
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
    ) -> None:
        """
        Log a failed replay upload to the database.

        If a failed upload with the same replay_hash already exists,
        it updates the existing record instead of creating a duplicate.
        """
        data = FailedUploadData(
            filename=filename,
            file_size=file_size,
            error_type=error_type,
            error_message=error_message,
            error_detail=error_detail,
            replay_hash=replay_hash,
            map_name=map_name,
            game_mode=game_mode,
            duration_seconds=duration_seconds,
            num_players=num_players,
            replay_file_path=replay_file_path,
        )
        self._save_failed_upload(data)

    def _save_failed_upload(self, data: FailedUploadData) -> None:
        """Save or update a failed upload record in the database."""
        try:
            existing = self._find_existing_failed_upload(data.replay_hash)

            if existing:
                self._update_failed_upload_record(existing, data)
            else:
                self._create_failed_upload_record(data)

            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log failed upload: {e}", exc_info=True)
            self.db.rollback()

    def _find_existing_failed_upload(
        self, replay_hash: Optional[str]
    ) -> Optional[FailedUpload]:
        """Find an existing failed upload by replay hash."""
        if not replay_hash:
            return None
        return (
            self.db.query(FailedUpload)
            .filter(FailedUpload.replay_hash == replay_hash)
            .first()
        )

    def _update_failed_upload_record(
        self, existing: FailedUpload, data: FailedUploadData
    ) -> None:
        """Update an existing failed upload record."""
        existing.filename = data.filename
        existing.uploaded_at = datetime.utcnow()
        existing.file_size_bytes = data.file_size
        existing.error_type = data.error_type
        existing.error_message = data.error_message[:500]
        existing.error_detail = data.error_detail[:2000] if data.error_detail else None

        if data.map_name:
            existing.map_name = data.map_name
        if data.game_mode:
            existing.game_mode = data.game_mode
        if data.duration_seconds:
            existing.duration_seconds = data.duration_seconds
        if data.num_players:
            existing.num_players = data.num_players
        if data.replay_file_path:
            existing.replay_file_path = data.replay_file_path

    def _create_failed_upload_record(self, data: FailedUploadData) -> None:
        """Create a new failed upload record."""
        failed_upload = FailedUpload(
            filename=data.filename,
            file_size_bytes=data.file_size,
            replay_hash=data.replay_hash,
            replay_file_path=data.replay_file_path,
            error_type=data.error_type,
            error_message=data.error_message[:500],
            error_detail=data.error_detail[:2000] if data.error_detail else None,
            map_name=data.map_name,
            game_mode=data.game_mode,
            duration_seconds=data.duration_seconds,
            num_players=data.num_players,
        )
        self.db.add(failed_upload)

    def get_existing_match_by_hash(self, replay_hash: str) -> Optional[Match]:
        """
        Get an existing match by its replay hash.

        Args:
            replay_hash: The replay file hash

        Returns:
            Match object if found, None otherwise
        """
        return self.db.query(Match).filter(Match.replay_hash == replay_hash).first()

    def delete_failed_upload(self, upload_id: int) -> bool:
        """
        Delete a failed upload record.

        Args:
            upload_id: The failed upload ID to delete

        Returns:
            True if deleted, False if not found
        """
        failed_upload = (
            self.db.query(FailedUpload).filter(FailedUpload.id == upload_id).first()
        )

        if not failed_upload:
            return False

        self.db.delete(failed_upload)
        self.db.commit()
        return True
