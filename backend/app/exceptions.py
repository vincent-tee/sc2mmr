"""
Custom exceptions for SC2 MMR Tracker.

This module defines specific exception types for different error scenarios,
enabling more precise error handling and better error messages.

Usage:
    from app.exceptions import ReplayParseError

    try:
        process_replay(file)
    except ReplayParseError as e:
        logger.error(f"Failed to parse replay: {e}")
        raise HTTPException(status_code=400, detail=str(e))
"""

from typing import Optional


class SC2MMRException(Exception):
    """
    Base exception for all SC2 MMR Tracker errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self, message: str = "SC2 MMR Tracker Error", detail: Optional[str] = None
    ):
        self.message = message
        self.detail = detail
        super().__init__(self.message)

    def __str__(self):
        if self.detail:
            return f"{self.message}: {self.detail}"
        return self.message


class ReplayParseError(SC2MMRException):
    """
    Raised when a replay file cannot be parsed.

    This could be due to:
    - Corrupted replay file
    - Unsupported replay version
    - Invalid file format
    """

    pass


class WinnerDeterminationError(SC2MMRException):
    """
    Raised when the winner of a match cannot be determined.

    This could occur when:
    - Match data is incomplete
    - All players appear to have left
    - Game ended in an unusual way
    """

    pass


class ValidationError(SC2MMRException):
    """
    Raised when input validation fails.
    """

    pass
