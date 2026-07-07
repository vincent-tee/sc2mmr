"""
Services package for SC2 MMR Tracker.

This module contains business logic services extracted from API routes.
Each service encapsulates a specific domain of functionality.

Services:
- PICalculator: Performance Impact Modifier calculation (SPEC-ML-001)
- ReplayService: Replay upload and processing (SPEC-REFACTOR-001)
- RatingService: Rating calculation and recalculation (SPEC-REFACTOR-001)
- MatchService: Match CRUD and winner determination (SPEC-REFACTOR-001)
- AchievementService: Achievement tracking and awarding (Phase 2)
"""

from .pi_calculator import PICalculator, MatchAverages, PIMBreakdown  # type: ignore
from .match_orchestrator import (  # type: ignore
    MatchOrchestrator,
    MatchOrchestrationResult,
    OrchestrationStats,
)
from .replay_service import (  # type: ignore
    ReplayService,
    ReplayProcessingResult,
    ProcessingStats,
    FailedUploadData,
)
from .rating_service import (  # type: ignore
    RatingService,
    RecalculationStats,
    MatchProcessingContext,
)
from .match_service import (  # type: ignore
    MatchService,
    MatchDetails,
    MatchPlayerData,
    MatchStatistics,
    ManualWinnerResult,
)
from .achievement_service import AchievementService  # type: ignore
from .adaptive_balancer import (  # type: ignore
    MLMetricsBalancer,
    MLPlayerRating,
    MLTeamSuggestion,
    SynergyCalculator,
    ComponentAccuracyTracker,
)
from .session_weighted_ratings import SessionWeightedRatings  # type: ignore

__all__ = [
    # PI Calculator
    "PICalculator",
    "MatchAverages",
    "PIMBreakdown",
    # Match Orchestrator
    "MatchOrchestrator",
    "MatchOrchestrationResult",
    "OrchestrationStats",
    # Replay Service
    "ReplayService",
    "ReplayProcessingResult",
    "ProcessingStats",
    "FailedUploadData",
    # Rating Service
    "RatingService",
    "RecalculationStats",
    "MatchProcessingContext",
    # Match Service
    "MatchService",
    "MatchDetails",
    "MatchPlayerData",
    "MatchStatistics",
    "ManualWinnerResult",
    # Achievement Service
    "AchievementService",
    # Adaptive Balancer (ML Metrics)
    "MLMetricsBalancer",
    "MLPlayerRating",
    "MLTeamSuggestion",
    "SynergyCalculator",
    "ComponentAccuracyTracker",
    # Session Weighted Ratings
    "SessionWeightedRatings",
]
