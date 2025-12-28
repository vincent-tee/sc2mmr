"""
Dynamic Ability Discovery System - Option B Implementation

This module provides future-proof ability tracking for SC2 replays.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
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
    """

    def __init__(self, config_path: Optional[str] = None):
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
        self._load_learned_abilities()

    def _load_config(self) -> dict:
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    return json.load(f)
            return self._get_default_config()
        except Exception:
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        return {
            "version": "5.0.15",
            "last_updated": "2025-01-27",
            "manual_overrides": {},
            "filter_patterns": {
                "exclude_prefixes": ["Train", "Build", "Research", "Upgrade"],
                "include_suffixes": ["Execute", "Mode", "Boost"],
                "min_priority": 1,
                "max_priority": 10,
            },
            "ability_categories": {
                "high_micro": ["Storm", "EMP", "Fungal", "Blink", "Stim"],
            },
            "learned_abilities": {},
        }

    def _load_learned_abilities(self):
        learned = self.config.get("learned_abilities", {})
        for name, meta in learned.items():
            if isinstance(meta, dict):
                self.discovered_abilities[name] = AbilityMetadata(
                    ability_name=name,
                    category=meta.get("category", "unknown"),
                    priority=meta.get("priority", 5),
                    first_seen_date=meta.get("first_seen_date", ""),
                    usage_count=meta.get("usage_count", 0),
                    patches_seen=meta.get("patches_seen", []),
                )

    def discover_from_replay(
        self, replay: Any, patch_version: Optional[str] = None
    ) -> Set[str]:
        discovered: Set[str] = set()
        if not hasattr(replay, "game_events"):
            return discovered

        for event in replay.game_events:
            if hasattr(event, "ability") and hasattr(event.ability, "name"):
                ability_name = event.ability.name
                if self._should_skip_ability(ability_name):
                    continue
                discovered.add(ability_name)
                self._update_ability_metadata(ability_name, patch_version)
        return discovered

    def _should_skip_ability(self, ability_name: str) -> bool:
        if ability_name in self.manual_overrides:
            return False
        exclude_prefixes = self.filter_patterns.get("exclude_prefixes", [])
        for prefix in exclude_prefixes:
            if ability_name.startswith(prefix):
                return True
        return False

    def _update_ability_metadata(self, ability_name: str, patch_version: Optional[str]):
        if ability_name in self.discovered_abilities:
            metadata = self.discovered_abilities[ability_name]
            metadata.usage_count += 1
            if patch_version and patch_version not in metadata.patches_seen:
                metadata.patches_seen.append(patch_version)
        else:
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

    def _classify_ability(self, ability_name: str) -> str:
        for category, keywords in self.patterns.items():
            for keyword in keywords:
                if keyword in ability_name:
                    return category
        return "unknown"

    def _infer_priority(self, ability_name: str, category: str) -> int:
        if ability_name in self.manual_overrides:
            return int(self.manual_overrides[ability_name])
        return 5

    def _get_current_date(self) -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d")

    def should_track_ability(self, ability_name: str) -> bool:
        if ability_name in self.manual_overrides:
            return True
        return not self._should_skip_ability(ability_name)

    def get_priority(self, ability_name: str) -> int:
        """Get the priority for an ability (public API)."""
        if ability_name in self.discovered_abilities:
            return self.discovered_abilities[ability_name].priority
        category = self._classify_ability(ability_name)
        return self._infer_priority(ability_name, category)

    def get_category(self, ability_name: str) -> str:
        """Get the category for an ability (public API)."""
        if ability_name in self.discovered_abilities:
            return self.discovered_abilities[ability_name].category
        return self._classify_ability(ability_name)

    def get_statistics(self) -> Dict[str, Any]:
        if not self.discovered_abilities:
            return {"total_discovered": 0}
        return {"total_discovered": len(self.discovered_abilities)}

    def save_config(self):
        try:
            learned_dict = {}
            for name, meta in self.discovered_abilities.items():
                learned_dict[name] = {
                    "category": meta.category,
                    "priority": meta.priority,
                    "first_seen_date": meta.first_seen_date,
                    "usage_count": meta.usage_count,
                    "patches_seen": meta.patches_seen,
                }
            self.config["learned_abilities"] = learned_dict
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            raise


def get_discovery_engine(config_path: Optional[str] = None) -> DynamicAbilityDiscovery:
    return DynamicAbilityDiscovery(config_path)
