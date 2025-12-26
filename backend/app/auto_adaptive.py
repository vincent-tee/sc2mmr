"""
Auto-Adaptive Model System

Automatically triggers weight optimization after every N matches.
For small datasets (200-300 matches/year), this provides continuous
improvement without excessive computation.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from .models import Match, PlayerMatchMetrics
from .adaptive_model import AdaptiveModelTuner, PerformanceWeights

logger = logging.getLogger(__name__)


class AutoAdaptiveConfig:
    """Configuration for auto-adaptive system."""

    # Trigger optimization after every N matches
    MATCHES_PER_OPTIMIZATION: int = 5

    # Minimum matches before first optimization
    MIN_MATCHES_FOR_FIRST_RUN: int = 50

    # Enable/disable auto-optimization
    ENABLED: bool = True


class AutoAdaptiveTracker:
    """
    Tracks when to trigger adaptive model optimization.
    """

    _last_optimization_count: int = 0
    _current_weights: Optional[PerformanceWeights] = None

    @classmethod
    def should_optimize(cls, db: Session) -> bool:
        """
        Check if we should trigger optimization.
        """
        if not AutoAdaptiveConfig.ENABLED:
            return False

        # Get total match count
        total_matches = db.query(func.count(Match.id)).scalar() or 0

        # Need minimum matches before first run
        if total_matches < AutoAdaptiveConfig.MIN_MATCHES_FOR_FIRST_RUN:
            return False

        # Check if we've crossed a threshold
        matches_since_last = total_matches - cls._last_optimization_count

        if matches_since_last >= AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION:
            logger.info(
                f"Auto-adaptive trigger: {matches_since_last} matches since last "
                f"optimization (threshold: {AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION})"
            )
            return True

        return False

    @classmethod
    def optimize_if_needed(cls, db: Session) -> Optional[Dict[str, Any]]:
        """
        Optimize weights if threshold reached.
        """
        if not cls.should_optimize(db):
            return None

        try:
            logger.info("Running auto-adaptive optimization...")

            # Get current match count
            total_matches = db.query(func.count(Match.id)).scalar() or 0

            # Run optimization
            suggestion = AdaptiveModelTuner.suggest_weight_update(db)

            if suggestion:
                # Update tracking
                cls._last_optimization_count = total_matches

                # Cache weights if suggested
                if "suggested_weights" in suggestion:
                    cls._current_weights = suggestion["suggested_weights"]
                    logger.info(
                        f"Auto-adaptive optimization complete: {suggestion['suggestion']}"
                    )
                    logger.info(f"New weights: {cls._current_weights}")
                else:
                    logger.info(
                        f"Auto-adaptive optimization complete: {suggestion['suggestion']} "
                        f"(no changes recommended)"
                    )

                return suggestion
            else:
                logger.warning("Auto-adaptive optimization returned no suggestion")
                return None

        except Exception as e:
            logger.error(f"Auto-adaptive optimization failed: {e}", exc_info=True)
            return None

    @classmethod
    def get_current_weights(cls) -> PerformanceWeights:
        """
        Get current optimized weights or defaults.
        """
        return cls._current_weights or PerformanceWeights()

    @classmethod
    def force_optimization(cls, db: Session) -> Dict[str, Any]:
        """
        Force optimization regardless of threshold.
        """
        logger.info("Forcing auto-adaptive optimization...")
        total_matches = db.query(func.count(Match.id)).scalar() or 0

        suggestion = AdaptiveModelTuner.suggest_weight_update(db)

        if suggestion:
            cls._last_optimization_count = total_matches
            if "suggested_weights" in suggestion:
                cls._current_weights = suggestion["suggested_weights"]

        return suggestion or {}

    @classmethod
    def reset(cls):
        """Reset tracking (useful after database reset)."""
        cls._last_optimization_count = 0
        cls._current_weights = None
        logger.info("Auto-adaptive tracker reset")


# Convenience function to call from upload endpoint
def trigger_auto_optimization(db: Session) -> Optional[Dict[str, Any]]:
    """
    Convenience function to trigger auto-optimization.
    """
    return AutoAdaptiveTracker.optimize_if_needed(db)
