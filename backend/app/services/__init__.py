"""
Services package for SC2 MMR Tracker.

This module contains business logic services extracted from API routes.
Each service encapsulates a specific domain of functionality.
"""

from .pi_calculator import PICalculator, MatchAverages, PIMBreakdown  # type: ignore
from .match_orchestrator import (  # type: ignore
    MatchOrchestrator,
    MatchOrchestrationResult,
    OrchestrationStats,
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
