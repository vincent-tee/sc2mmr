"""
ReplayService - Business logic for replay upload and processing.

Type Issues:
- sc2reader lacks type stubs.
"""

import logging
import os
import tempfile
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings  # type: ignore
from app.exceptions import (  # type: ignore
    DuplicateReplayError,
    ReplayParseError,
    ValidationError,
    WinnerDeterminationError,
)
from app.models import (  # type: ignore
    FailedUpload,
    Match,
    MatchPlayer,
    Player,
    UploadErrorType,
)
from app.replay_parser import (  # type: ignore
    calculate_replay_hash,
    determine_game_mode,
    validate_replay_data,
    ReplayData,
)
from app.services.match_orchestrator import MatchOrchestrator, MatchOrchestrationResult  # type: ignore

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
    """

    REPLAY_EXTENSION = ".SC2Replay"

    def __init__(self, db: Session):
        self.db = db

    def process_replay(
        self,
        file_content: bytes,
        filename: str,
        use_advanced_parser: bool = True,
        use_cc_parser: bool = False,
    ) -> ReplayProcessingResult:
        self._validate_file_extension(filename)
        tmp_file_path = self._save_to_temp_file(file_content)

        try:
            return self._process_replay_file(
                tmp_file_path,
                file_content,
                filename,
                use_advanced_parser,
                use_cc_parser=use_cc_parser,
            )
        finally:
            self._cleanup_temp_file(tmp_file_path)

    def process_replay_with_manual_winner(
        self,
        file_content: bytes,
        filename: str,
        winner_team: int,
        use_advanced_parser: bool = True,
        use_cc_parser: bool = False,
    ) -> ReplayProcessingResult:
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
                use_cc_parser=use_cc_parser,
            )
        finally:
            self._cleanup_temp_file(tmp_file_path)

    def _process_replay_file(
        self,
        file_path: str,
        file_content: bytes,
        filename: str,
        use_advanced_parser: bool,
        manual_winner_team: Optional[int] = None,
        use_cc_parser: bool = False,
    ) -> ReplayProcessingResult:
        orchestrator = MatchOrchestrator(self.db)

        try:
            result = orchestrator.orchestrate_match(
                file_path=file_path,
                filename=filename,
                manual_winner_team=manual_winner_team,
                use_advanced_parser=use_advanced_parser,
                use_cc_parser=use_cc_parser,
            )

            return ReplayProcessingResult(
                match=result.match,
                num_players=result.num_players,
                processing_stats=ProcessingStats(
                    parse_time_ms=result.stats.parse_time_ms,
                    validation_time_ms=result.stats.validation_time_ms,
                    duplicate_check_time_ms=result.stats.duplicate_check_time_ms,
                    rating_update_time_ms=result.stats.rating_update_time_ms,
                    total_time_ms=result.stats.total_time_ms,
                ),
                message=result.message,
            )

        except WinnerDeterminationError as e:
            self._handle_winner_determination_error(
                e, file_content, filename, file_path, None
            )
            raise
        except ReplayParseError as e:
            self._handle_parse_error(e, file_content, filename)
            raise
        except DuplicateReplayError:
            raise
        except Exception as e:
            self._handle_unexpected_error(e, file_content, filename, None)
            raise ReplayParseError(f"Unexpected error: {str(e)}")

    def _validate_file_extension(self, filename: str) -> None:
        if not filename.endswith(self.REPLAY_EXTENSION):
            raise ValidationError(
                f"Invalid file type. Only {self.REPLAY_EXTENSION} files are accepted."
            )

    def _save_to_temp_file(self, content: bytes) -> str:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=self.REPLAY_EXTENSION
        ) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name

    def _cleanup_temp_file(self, file_path: str) -> None:
        if os.path.exists(file_path):
            os.remove(file_path)

    def _handle_winner_determination_error(
        self,
        error: Exception,
        file_content: bytes,
        filename: str,
        file_path: str,
        replay_data: Optional[ReplayData],
    ) -> None:
        logger.warning(
            f"WinnerDeterminationError for file '{filename}': {str(error)[:200]}..."
        )
        metadata = self._extract_replay_metadata(file_path, replay_data)
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
        self, error: Exception, file_content: bytes, filename: str
    ) -> None:
        logger.error(f"ReplayParseError for file '{filename}': {str(error)[:200]}...")
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
        if replay_data:
            return self._extract_metadata_from_replay_data(replay_data)
        try:
            import sc2reader  # type: ignore

            replay = sc2reader.load_replay(file_path, load_level=2)  # type: ignore
            replay_hash = calculate_replay_hash(file_path)
            human_players = [p for p in replay.players if p.is_human]
            num_players = len(human_players)
            game_mode_enum = determine_game_mode(num_players)
            game_length = getattr(replay, "game_length", None)
            duration_seconds = game_length.seconds if game_length else None
            return {
                "replay_hash": replay_hash,
                "map_name": getattr(replay, "map_name", "Unknown"),
                "game_mode": game_mode_enum.value if game_mode_enum else None,
                "duration_seconds": duration_seconds,
                "num_players": num_players,
            }

        except Exception:
            return {}

    def _extract_metadata_from_replay_data(
        self, replay_data: ReplayData
    ) -> Dict[str, Any]:
        return {
            "replay_hash": replay_data.replay_hash,
            "map_name": replay_data.map_name,
            "game_mode": replay_data.game_mode.value
            if hasattr(replay_data.game_mode, "value")
            else str(replay_data.game_mode),
            "duration_seconds": replay_data.duration_seconds,
            "num_players": len(replay_data.players),
        }

    def _save_failed_replay_file(
        self, content: bytes, filename: str, replay_hash: str
    ) -> str:
        failed_replays_dir = os.path.join(os.getcwd(), settings.failed_replays_dir)
        os.makedirs(failed_replays_dir, exist_ok=True)
        safe_filename = f"{replay_hash}_{filename}"
        file_path = os.path.join(failed_replays_dir, safe_filename)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    def _log_failed_upload(self, **kwargs) -> None:
        data = FailedUploadData(**kwargs)
        self._save_failed_upload(data)

    def _save_failed_upload(self, data: FailedUploadData) -> None:
        try:
            existing = (
                self.db.query(FailedUpload)
                .filter(FailedUpload.replay_hash == data.replay_hash)
                .first()
                if data.replay_hash
                else None
            )
            if existing:
                existing.filename = data.filename
                existing.uploaded_at = datetime.utcnow()
                existing.file_size_bytes = data.file_size
                existing.error_type = data.error_type
                existing.error_message = data.error_message[:500]
                existing.error_detail = (
                    data.error_detail[:2000] if data.error_detail else None
                )
            else:
                failed_upload = FailedUpload(
                    filename=data.filename,
                    file_size_bytes=data.file_size,
                    replay_hash=data.replay_hash,
                    replay_file_path=data.replay_file_path,
                    error_type=data.error_type,
                    error_message=data.error_message[:500],
                    error_detail=data.error_detail[:2000]
                    if data.error_detail
                    else None,
                    map_name=data.map_name,
                    game_mode=data.game_mode,
                    duration_seconds=data.duration_seconds,
                    num_players=data.num_players,
                )
                self.db.add(failed_upload)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log failed upload: {e}")
            self.db.rollback()

    def get_existing_match_by_hash(self, replay_hash: str) -> Optional[Match]:
        return self.db.query(Match).filter(Match.replay_hash == replay_hash).first()

    def reprocess_match_metrics(
        self, file_path: str, match: Match, use_cc_parser: bool = False
    ) -> bool:
        """Reprocess only metrics and features for an existing match."""
        orchestrator = MatchOrchestrator(self.db)
        try:
            # Parse the replay (unified)
            result = orchestrator.parser.parse(file_path)

            # Augmented Parsing (CommandCenter based)
            if use_cc_parser and orchestrator.cc_parser:
                try:
                    cc_metrics = orchestrator.cc_parser.parse_replay(file_path)
                    orchestrator._augment_with_cc_metrics(result, cc_metrics)
                except Exception as e:
                    logger.error(
                        f"CommandCenter parsing failed for Match #{match.id}: {e}"
                    )

            # Save only metrics
            orchestrator.save_metrics_only(match, result)
            return True
        except Exception as e:
            logger.error(f"Failed to reprocess metrics for Match #{match.id}: {e}")
            return False

    def delete_failed_upload(self, upload_id: int) -> bool:
        failed_upload = (
            self.db.query(FailedUpload).filter(FailedUpload.id == upload_id).first()
        )
        if not failed_upload:
            return False
        self.db.delete(failed_upload)
        self.db.commit()
        return True
