"""
Dynamic Ability Discovery System - Option B Implementation

This module provides future-proof ability tracking for SC2 replays:
- Auto-discovers all abilities from replays (no hardcoded lists)
- Classifies abilities into categories (micro, macro, utility)
- Assigns priority scores for ML feature weighting
- Learns new abilities over time (no manual updates per patch)

Benefits over hardcoded approach:
- 100% ability coverage (vs 0-50% currently)
- Future-proof: automatically adapts to new patches
- Better ML features: ability categories, diversity metrics
- Maintainable: external config, no code changes needed
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AbilityMetadata:
    """Metadata for a discovered ability."""

    ability_name: str
    category: str  # high_micro, medium_micro, macro, movement, utility, unknown
    priority: int  # 1-10 for ML feature weighting
    first_seen_date: str  # When this ability was first discovered
    usage_count: int = 0  # Total times seen across all parsed replays
    patches_seen: List[str] = field(
        default_factory=list
    )  # SC2 patches where this ability appears


class DynamicAbilityDiscovery:
    """
    Auto-discovery engine for SC2 replay abilities.

    Replaces hardcoded TRACKED_ABILITIES dictionary with dynamic learning.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize discovery engine.

        Args:
            config_path: Path to abilities_config.json (default: ./config/abilities_config.json)
        """
        self.config_path = (
            Path(config_path)
            if config_path
            else Path(__file__).parent.parent / "config" / "abilities_config.json"
        )
        self.config = self._load_config()
        self.discovered_abilities: Dict[str, AbilityMetadata] = {}
        self.patterns = self.config.get("ability_categories", {})
        self.manual_overrides = self.config.get("manual_overrides", {})
        self.filter_patterns = self.config.get("filter_patterns", {})

        # Load previously learned abilities
        self._load_learned_abilities()

    def _load_config(self) -> dict:
        """Load abilities configuration from JSON file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    logger.info(f"✅ Loaded abilities config from {self.config_path}")
                    return config
            else:
                logger.warning(
                    f"⚠️ Config not found at {self.config_path}, using defaults"
                )
                return self._get_default_config()
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """Return default configuration if file doesn't exist."""
        return {
            "version": "5.0.15",
            "last_updated": "2025-01-27",
            "manual_overrides": {
                "PsionicStorm": 10,
                "Blink": 10,
                "Stimpack": 10,
            },
            "filter_patterns": {
                "exclude_prefixes": [
                    "Train",
                    "Build",
                    "Research",
                    "Upgrade",
                    "RightClick",
                    "Hold",
                    "Patrol",
                    "SetRally",
                    "Cancel",
                ],
                "include_suffixes": [
                    "Execute",
                    "Mode",
                    "Boost",
                    "Warp",
                    "Shift",
                    "Storm",
                ],
                "min_priority": 1,
                "max_priority": 10,
            },
            "ability_categories": {
                "high_micro": ["Storm", "EMP", "Fungal", "Blink", "Stim", "Feedback"],
                "medium_micro": ["Recharge", "ForceField", "Transfusion", "Abduct"],
                "macro": ["Chrono", "ChronoBoost", "SpawnLarva", "MULE", "Warp"],
                "movement": [
                    "Blink",
                    "Charge",
                    "Speed",
                    "Jump",
                    "Recall",
                    "PhaseShift",
                ],
                "utility": ["Scan", "Shield", "Cloak", "Decloak", "SupplyDrop"],
            },
            "learned_abilities": {},
        }

    def _load_learned_abilities(self):
        """Load previously discovered abilities from config."""
        learned = self.config.get("learned_abilities", {})
        for ability_name, metadata in learned.items():
            if isinstance(metadata, dict):
                # Convert dict to AbilityMetadata
                self.discovered_abilities[ability_name] = AbilityMetadata(
                    ability_name=ability_name,
                    category=metadata.get("category", "unknown"),
                    priority=metadata.get("priority", 5),
                    first_seen_date=metadata.get("first_seen_date", ""),
                    usage_count=metadata.get("usage_count", 0),
                    patches_seen=metadata.get("patches_seen", []),
                )
        logger.info(
            f"✅ Loaded {len(self.discovered_abilities)} learned abilities from config"
        )

    def discover_from_replay(
        self, replay, patch_version: Optional[str] = None
    ) -> Set[str]:
        """
        Discover ALL unique abilities from a parsed replay.

        Args:
            replay: sc2reader Replay object
            patch_version: Optional SC2 version string

        Returns:
            Set of discovered ability names
        """
        discovered = set()

        if not hasattr(replay, "game_events"):
            logger.warning("⚠️ No game_events in replay, cannot discover abilities")
            return discovered

        for event in replay.game_events:
            if hasattr(event, "ability") and hasattr(event.ability, "name"):
                ability_name = event.ability.name

                # Skip based on filter patterns
                if self._should_skip_ability(ability_name):
                    continue

                discovered.add(ability_name)

                # Update metadata
                self._update_ability_metadata(ability_name, patch_version)

        logger.info(f"✅ Discovered {len(discovered)} abilities from replay")
        return discovered

    def _should_skip_ability(self, ability_name: str) -> bool:
        """
        Determine if ability should be skipped based on filter patterns.

        Args:
            ability_name: Name of the ability

        Returns:
            True if should skip, False otherwise
        """
        # Manual overrides always included
        if ability_name in self.manual_overrides:
            return False

        exclude_prefixes = self.filter_patterns.get("exclude_prefixes", [])
        include_suffixes = self.filter_patterns.get("include_suffixes", [])

        # Check if ability starts with excluded prefix
        for prefix in exclude_prefixes:
            if ability_name.startswith(prefix):
                return True

        # Check if ability ends with included suffix (more specific)
        for suffix in include_suffixes:
            if ability_name.endswith(suffix):
                return False

        # Default: include if not explicitly excluded
        return False

    def _update_ability_metadata(self, ability_name: str, patch_version: Optional[str]):
        """Update metadata for a discovered ability."""
        # Get existing or create new
        if ability_name in self.discovered_abilities:
            metadata = self.discovered_abilities[ability_name]
            metadata.usage_count += 1

            if patch_version and patch_version not in metadata.patches_seen:
                metadata.patches_seen.append(patch_version)
        else:
            # New ability discovery
            category = self._classify_ability(ability_name)
            priority = self._infer_priority(ability_name, category)

            metadata = AbilityMetadata(
                ability_name=ability_name,
                category=category,
                priority=priority,
                first_seen_date=self._get_current_date(),
                usage_count=1,
                patches_seen=[patch_version] if patch_version else [],
            )

            self.discovered_abilities[ability_name] = metadata
            logger.info(
                f"🆕 New ability discovered: {ability_name} (category: {category}, priority: {priority})"
            )

    def _classify_ability(self, ability_name: str) -> str:
        """
        Classify ability into category based on pattern matching.

        Args:
            ability_name: Name of the ability

        Returns:
            Category string: high_micro, medium_micro, macro, movement, utility, unknown
        """
        for category, keywords in self.patterns.items():
            for keyword in keywords:
                if keyword in ability_name:
                    return category

        return "unknown"

    def _infer_priority(self, ability_name: str, category: str) -> int:
        """
        Infer priority score for ML feature weighting.

        Args:
            ability_name: Name of the ability
            category: Classified category

        Returns:
            Priority score (1-10)
        """
        # Manual override takes precedence
        if ability_name in self.manual_overrides:
            return self.manual_overrides[ability_name]

        min_priority = self.filter_patterns.get("min_priority", 1)
        max_priority = self.filter_patterns.get("max_priority", 10)

        # Category-based inference
        category_priorities = {
            "high_micro": max_priority,
            "medium_micro": max_priority - 2,
            "macro": max_priority - 5,
            "movement": max_priority - 3,
            "utility": max_priority - 4,
            "unknown": min_priority,
        }

        return category_priorities.get(category, min_priority)

    def _get_current_date(self) -> str:
        """Get current date in ISO format."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d")

    def get_priority(self, ability_name: str) -> int:
        """
        Get priority for an ability.

        Args:
            ability_name: Name of the ability

        Returns:
            Priority score (1-10)
        """
        if ability_name in self.discovered_abilities:
            return self.discovered_abilities[ability_name].priority
        elif ability_name in self.manual_overrides:
            return self.manual_overrides[ability_name]
        else:
            # Fallback for unknown abilities
            return 5

    def should_track_ability(self, ability_name: str) -> bool:
        """
        Determine if ability should be tracked for ML features.

        Args:
            ability_name: Name of the ability

        Returns:
            True if should track, False otherwise
        """
        # Manual overrides always tracked
        if ability_name in self.manual_overrides:
            return True

        # Check if ability passes filter
        if self._should_skip_ability(ability_name):
            return False

        return True

    def get_category(self, ability_name: str) -> str:
        """
        Get category for an ability.

        Args:
            ability_name: Name of the ability

        Returns:
            Category string
        """
        if ability_name in self.discovered_abilities:
            return self.discovered_abilities[ability_name].category
        else:
            return self._classify_ability(ability_name)

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about discovered abilities.

        Returns:
            Dictionary with statistics
        """
        if not self.discovered_abilities:
            return {
                "total_discovered": 0,
                "by_category": {},
                "most_common": None,
                "newest_ability": None,
            }

        # Count by category
        by_category: Dict[str, int] = {}
        for metadata in self.discovered_abilities.values():
            by_category[metadata.category] = by_category.get(metadata.category, 0) + 1

        # Most common ability
        most_common = (
            max(
                self.discovered_abilities.keys(),
                key=lambda k: self.discovered_abilities[k].usage_count,
            )
            if self.discovered_abilities
            else None
        )

        # Newest ability
        newest = (
            max(
                self.discovered_abilities.keys(),
                key=lambda k: self.discovered_abilities[k].first_seen_date,
                default=None,
            )
            if self.discovered_abilities
            else None
        )

        return {
            "total_discovered": len(self.discovered_abilities),
            "by_category": by_category,
            "most_common": most_common,
            "most_common_count": self.discovered_abilities[most_common].usage_count
            if most_common
            else 0,
            "newest_ability": newest,
            "config_version": self.config.get("version", "unknown"),
        }

    def save_config(self):
        """Save updated configuration with learned abilities."""
        try:
            # Prepare learned abilities for saving
            learned_dict = {}
            for ability_name, metadata in self.discovered_abilities.items():
                learned_dict[ability_name] = {
                    "category": metadata.category,
                    "priority": metadata.priority,
                    "first_seen_date": metadata.first_seen_date,
                    "usage_count": metadata.usage_count,
                    "patches_seen": metadata.patches_seen,
                }

            self.config["learned_abilities"] = learned_dict
            self.config["last_updated"] = self._get_current_date()

            # Create directory if needed
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Save
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)

            logger.info(f"✅ Saved {len(learned_dict)} abilities to {self.config_path}")

        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
            raise


# Convenience function for backward compatibility
def get_discovery_engine(config_path: Optional[str] = None) -> DynamicAbilityDiscovery:
    """
    Get or create a discovery engine instance.

    Args:
        config_path: Optional path to config file

    Returns:
        DynamicAbilityDiscovery instance
    """
    return DynamicAbilityDiscovery(config_path)
