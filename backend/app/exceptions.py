"""
Custom exceptions for SC2 MMR Tracker.

This module defines specific exception types for different error scenarios,
enabling more precise error handling and better error messages.

Usage:
    from app.exceptions import ReplayParseError, PlayerNotFoundError

    try:
        process_replay(file)
    except ReplayParseError as e:
        logger.error(f"Failed to parse replay: {e}")
        raise HTTPException(status_code=400, detail=str(e))
"""


class SC2MMRException(Exception):
    """
    Base exception for all SC2 MMR Tracker errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(self, message: str, detail: str = None):
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


class RatingCalculationError(SC2MMRException):
    """
    Raised when rating calculation fails.

    This could occur when:
    - Invalid mu/sigma values
    - TrueSkill library error
    - Mathematical overflow/underflow
    """
    pass


class PlayerNotFoundError(SC2MMRException):
    """
    Raised when a requested player is not found in the database.
    """

    def __init__(self, player_id: int = None, player_name: str = None):
        if player_id:
            message = f"Player with ID {player_id} not found"
        elif player_name:
            message = f"Player '{player_name}' not found"
        else:
            message = "Player not found"
        super().__init__(message)


class MatchNotFoundError(SC2MMRException):
    """
    Raised when a requested match is not found in the database.
    """

    def __init__(self, match_id: int):
        super().__init__(f"Match with ID {match_id} not found")


class DuplicateReplayError(SC2MMRException):
    """
    Raised when attempting to upload a replay that already exists.
    """

    def __init__(self, replay_hash: str, match_id: int = None):
        message = f"Replay already exists (hash: {replay_hash[:16]}...)"
        if match_id:
            message += f" - associated with match ID {match_id}"
        super().__init__(message)


class TeamBalanceError(SC2MMRException):
    """
    Raised when team balancing fails.

    This could occur when:
    - Not enough players selected
    - Invalid player IDs
    - Balancing algorithm fails
    """
    pass


class ValidationError(SC2MMRException):
    """
    Raised when input validation fails.
    """
    pass


class DatabaseError(SC2MMRException):
    """
    Raised when a database operation fails.

    Wraps SQLAlchemy errors with more context.
    """
    pass


class ConfigurationError(SC2MMRException):
    """
    Raised when there's a configuration problem.
    """
    pass
