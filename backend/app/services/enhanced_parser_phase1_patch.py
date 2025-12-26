"""
Phase 1 Integration Patch for Dynamic Ability Discovery (Option B)

This file provides clean integration of ability_discovery.py into enhanced_parser.py
with instant rollback capability.

Add this code to enhanced_parser.py:
1. Update imports (lines ~18-30)
2. Update __init__ method (lines ~349-371)
3. Update _extract_ability_usage method (lines ~587-630)
4. Add new method get_discovered_abilities (add after parse method)
"""

# ============================================================================
# 1. Add to imports section (after line 29)
# ============================================================================

# Add these lines:
import os

# Dynamic ability discovery (Option B integration)
try:
    from ability_discovery import get_discovery_engine

    DYNAMIC_DISCOVERY_AVAILABLE = True
except ImportError:
    DYNAMIC_DISCOVERY_AVAILABLE = False
    get_discovery_engine = None


# ============================================================================
# 2. Replace __init__ method completely (lines ~349-371)
# ============================================================================


class EnhancedReplayParser:
    """
    Extract ML-ready features from SC2 replays.

    This parser extends existing advanced_parser to capture:
    - Build order sequences for classification
    - Upgrade timelines for tech analysis
    - Ability usage for micro skill assessment
    - Resource checkpoints for macro analysis
    """

    def __init__(self, replay_path: str):
        """
        Initialize parser with replay file.

        Args:
            replay_path: Path to .SC2Replay file
        """
        self.replay_path = replay_path
        self.replay = None
        self._player_features: Dict[int, EnhancedPlayerFeatures] = {}

        # Option B: Dynamic ability discovery (feature flag for instant rollback)
        self.use_dynamic_discovery = (
            os.getenv("USE_DYNAMIC_DISCOVERY", "false").lower() == "true"
        )

        if self.use_dynamic_discovery and DYNAMIC_DISCOVERY_AVAILABLE:
            try:
                self.ability_discovery = get_discovery_engine()
                logger.info("✅ Dynamic ability discovery ENABLED (Option B)")
            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to initialize dynamic discovery: {e}, using fallback"
                )
                self.use_dynamic_discovery = False
                self.ability_discovery = None
        else:
            self.ability_discovery = None
            if self.use_dynamic_discovery and not DYNAMIC_DISCOVERY_AVAILABLE:
                logger.warning(
                    "⚠️ Dynamic discovery requested but module not available, using hardcoded"
                )
            else:
                logger.info(
                    "⚠️ Dynamic ability discovery DISABLED (using hardcoded TRACKED_ABILITIES)"
                )

    # ... rest of the class methods remain unchanged ...

    # ============================================================================
    # 3. Replace _extract_ability_usage method (lines ~587-630)
    # ============================================================================

    def _extract_ability_usage(self):
        """Extract ability usage counts for micro skill assessment."""

        # Path 1: Original hardcoded tracking (if disabled)
        if not self.use_dynamic_discovery:
            if not hasattr(self.replay, "game_events"):
                logger.warning("No game events available for ability extraction")
                return

            for event in self.replay.game_events:
                if hasattr(event, "ability") and hasattr(event, "player"):
                    self._process_ability_event(event)
            return

        # Path 2: Dynamic discovery with filtering (Option B)
        if not hasattr(self.replay, "game_events"):
            logger.warning("No game events available for ability extraction")
            return

        # Discover all abilities from replay
        try:
            discovered_abilities = self.ability_discovery.discover_from_replay(
                self.replay, getattr(self.replay, "release_string", "unknown")
            )
            logger.info(f"✅ Discovered {len(discovered_abilities)} unique abilities")
        except Exception as e:
            logger.error(
                f"❌ Ability discovery failed: {e}, falling back to no ability tracking"
            )
            return

        # Track only abilities that should be tracked (per filters)
        for event in self.replay.game_events:
            if hasattr(event, "ability") and hasattr(event, "player"):
                ability_name = getattr(event.ability, "name", None) or str(
                    event.ability
                )

                # Use dynamic discovery's filter logic
                if self.ability_discovery.should_track_ability(ability_name):
                    self._process_ability_event(event)

        logger.info(f"✅ Tracked abilities using dynamic discovery filters")

    # ============================================================================
    # 4. Add new method after parse() method (around line ~400)
    # ============================================================================

    def get_discovered_abilities(self) -> Dict[str, Dict]:
        """
        Export discovered ability metadata for ML features.

        Returns:
            Dict mapping ability_name to metadata (category, priority, usage_count)
            Returns empty dict if dynamic discovery not enabled.
        """
        if not self.use_dynamic_discovery or self.ability_discovery is None:
            logger.info("⚠️ Dynamic discovery not enabled, returning empty abilities")
            return {}

        return {
            ability_name: {
                "category": metadata.category,
                "priority": metadata.priority,
                "usage_count": metadata.usage_count,
                "patches_seen": metadata.patches_seen,
                "first_seen_date": metadata.first_seen_date,
            }
            for ability_name, metadata in self.ability_discovery.discovered_abilities.items()
        }


# ============================================================================
# 5. Rollback Instructions (Instant)
# ============================================================================

"""
To rollback instantly without code changes:

# Method 1: Environment Variable (Recommended)
export USE_DYNAMIC_DISCOVERY=false
# Then restart application - it will use hardcoded TRACKED_ABILITIES immediately

# Method 2: Code Comment
# Comment out these lines in __init__:
# self.use_dynamic_discovery = os.getenv("USE_DYNAMIC_DISCOVERY", "false").lower() == "true"
# Replace with:
# self.use_dynamic_discovery = False
"""
