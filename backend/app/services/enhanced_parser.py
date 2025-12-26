"""
Enhanced SC2 Replay Parser - ML-Ready Feature Extraction

This module extends advanced_parser to extract additional features for ML models:
- Build order sequences (chronological unit/building production)
- Upgrade timelines (when upgrades complete)
- Ability usage counts (for micro skill assessment)
- Resource checkpoints (economy snapshots at key moments)
- Worker harassment losses (early game pressure handling)

These features enable:
- Build order classification (LSTM model)
- Macro/Micro skill decomposition
- Team synergy prediction
- Enhanced MMR model (XGBoost)
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import hashlib
import json
import os
import sys
from pathlib import Path

import sc2reader  # type: ignore

# Dynamic ability discovery (Option B integration)
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from ability_discovery import get_discovery_engine  # type: ignore

    DYNAMIC_DISCOVERY_AVAILABLE = True
except ImportError:
    DYNAMIC_DISCOVERY_AVAILABLE = False
    get_discovery_engine = None

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes for Enhanced Features
# ============================================================================


@dataclass
class BuildOrderEvent:
    """Single event in a build order sequence."""

    second: int  # Game second when produced
    unit_type: str  # Unit or building name
    supply: int = 0  # Supply used at this point
    is_building: bool = False  # True if structure
    is_worker: bool = False  # True if worker unit


@dataclass
class UpgradeEvent:
    """Upgrade completion event."""

    second: int  # Game second when completed
    upgrade_name: str  # Name of upgrade
    upgrade_category: str = "unknown"  # "attack", "armor", "speed", "ability", etc.


@dataclass
class AbilityUsage:
    """Summary of ability usage for a player."""

    total_abilities: int = 0
    abilities: Dict[str, int] = field(default_factory=dict)  # {"Stim": 15, "EMP": 3}
    abilities_per_minute: float = 0.0


@dataclass
class ResourceCheckpoint:
    """Resource state at a specific game moment."""

    second: int
    minerals: int = 0
    vespene: int = 0
    workers: int = 0
    supply_used: int = 0
    supply_cap: int = 0
    army_supply: int = 0


@dataclass
class EnhancedPlayerFeatures:
    """ML-ready features extracted for a single player."""

    player_id: int
    player_name: str
    race: str
    team: int
    won: bool

    # Build Order (Sequence of units/buildings)
    build_order: List[BuildOrderEvent] = field(default_factory=list)
    build_order_hash: str = ""
    detected_build_type: str = "unknown"

    # Tech Progression
    upgrades: List[UpgradeEvent] = field(default_factory=list)
    first_attack_upgrade_second: Optional[int] = None
    first_armor_upgrade_second: Optional[int] = None
    upgrade_timing_score: float = 0.0

    # Micro Performance
    ability_usage: AbilityUsage = field(default_factory=AbilityUsage)

    # Macro Performance
    resource_checkpoints: List[ResourceCheckpoint] = field(default_factory=list)
    supply_block_seconds: int = 0
    early_worker_losses: int = 0
    harassment_response_score: float = 0.0


# ============================================================================
# Constants & Configuration
# ============================================================================

TRACKED_ABILITIES = {
    # Terran
    "Stimpack",
    "Heal",
    "SiegeMode",
    "Unsiege",
    "AssaultMode",
    "FighterMode",
    "Cloak",
    "Decloak",
    "250mmStrikeCannons",
    "Snipe",
    "EMP",
    "NuclearStrike",
    "TacticalJump",
    "Yamato",
    "ScannerSweep",
    "CalldownMULE",
    "SupplyDrop",
    # Protoss
    "Blink",
    "PsionicStorm",
    "Feedback",
    "ForceField",
    "GuardianShield",
    "PrismaticAlignment",
    "Revelation",
    "StasisWard",
    "PurificationNova",
    "MassRecall",
    "StrategicRecall",
    "ChronoBoost",
    # NEW: Patch 5.0.14/5.0.15 abilities
    "EnergyRecharge",  # Nexus ability (5.0.14)
    "EnergyOvercharge",  # Alternative name (PTR version)
    "GuardianShield",  # Sentry ability (typo fix: Guardian → Guardian)
    "TimeWarp",  # Mothership Core ability (5.0.14)
    "PrismaticAlignment",  # Mothership ability (already tracked, keeping)
    # Zerg
    "SpawnChangeling",
    "Contaminate",
    "NeuralParasite",
    "FungalGrowth",
    "InfestorTerran",
    "Transfusion",
    "SpawnLarva",
    "Abduct",
    "BlindingCloud",
    "ParasiticBomb",
    "ConsumptiveCloud",
    # NEW: Patch 5.0.14/5.0.15 abilities
    "MicrobialShroud",  # Infestor ability (5.0.14)
    "CentrifugalHooks",  # Baneling ability/upgrade (5.0.15 modified)
}


# ============================================================================
# Enhanced Parser Class
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
        self.replay: Any = None
        self._player_features: Dict[int, EnhancedPlayerFeatures] = {}

        # Option B: Dynamic ability discovery (feature flag for instant rollback)
        self.use_dynamic_discovery = (
            os.getenv("USE_DYNAMIC_DISCOVERY", "false").lower() == "true"
        )

        self.ability_discovery: Any = None
        if (
            self.use_dynamic_discovery
            and DYNAMIC_DISCOVERY_AVAILABLE
            and get_discovery_engine
        ):
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

    def parse(self) -> Dict[int, EnhancedPlayerFeatures]:
        """
        Parse replay and extract all enhanced features.

        Returns:
            Dictionary mapping player_id to EnhancedPlayerFeatures
        """
        try:
            # Load replay with maximum detail
            self.replay = sc2reader.load_replay(self.replay_path, load_level=4)  # type: ignore

            # Initialize features for each human player
            for player in self.replay.players:
                if not player.is_human:
                    continue

                self._player_features[player.pid] = EnhancedPlayerFeatures(
                    player_id=player.pid,
                    player_name=self._clean_player_name(player),
                    race=player.play_race,
                    team=player.team_id,
                    won=player.result == "Win",
                )

            # Extract all features
            self._extract_build_orders()
            self._extract_upgrades()
            self._extract_ability_usage()
            self._extract_resource_checkpoints()
            self._extract_harassment_losses()
            self._extract_supply_blocks()

            # Calculate derived features
            self._calculate_build_hashes()
            self._classify_build_types()
            self._calculate_upgrade_scores()
            self._calculate_ability_efficiency()
            self._calculate_harassment_response()

            return self._player_features

        except Exception as e:
            logger.error(f"Enhanced parser error: {e}")
            raise

    def get_discovered_abilities(self) -> Dict[str, Dict]:
        """
        Export discovered ability metadata for ML features.

        Returns:
            Dict mapping ability_name to metadata (category, priority, usage_count)
            Returns empty dict if dynamic discovery not enabled.
        """
        if not self.use_dynamic_discovery or self.ability_discovery is None:
            logger.info("Dynamic discovery not enabled, returning empty abilities")
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

    def _clean_player_name(self, player) -> str:
        """Remove clan tag from player name."""
        name = player.name
        if hasattr(player, "clan_tag") and player.clan_tag:
            name = name.replace(f"[{player.clan_tag}]", "").strip()
        return name

    # ========================================================================
    # Build Order Extraction
    # ========================================================================

    def _extract_build_orders(self):
        """Extract chronological build order for each player."""
        if not self.replay or not hasattr(self.replay, "tracker_events"):
            logger.warning("No tracker events available for build order extraction")
            return

        for event in self.replay.tracker_events:
            # Unit born events (most production)
            if event.name == "UnitBornEvent":
                self._process_unit_born(event)

            # Unit init events (buildings start construction)
            elif event.name == "UnitInitEvent":
                self._process_unit_init(event)

    def _process_unit_born(self, event):
        """Process UnitBornEvent for build order."""
        pid = getattr(event, "control_pid", None)
        if pid not in self._player_features:
            return

        unit_type = self._get_unit_type(event)
        if not unit_type or unit_type == "Unknown":
            return

        # Skip non-relevant units (map elements, temporary units, cosmetics, etc.)
        skip_prefixes = (
            "Beacon",
            "Reward",
            "Spray",
            "Destructible",
            "Collapsible",
            "Mineral",
            "Vespene",
            "XelNaga",
            "Unbuildable",
            "Rich",
        )
        if unit_type.startswith(skip_prefixes):
            return

        if unit_type in {
            "Larva",
            "Egg",
            "Cocoon",
            "LocustMP",
            "LocustMPFlying",
            "Changeling",
            "InfestorTerran",
            "Broodling",
            "AutoTurret",
            "PointDefenseDrone",
            "MULE",
            "Interceptor",
            "AdeptPhaseShift",
        }:
            return

        build_event = BuildOrderEvent(
            second=event.second,
            unit_type=unit_type,
            is_building=False,
            is_worker=unit_type in {"SCV", "Probe", "Drone"},
        )
        self._player_features[pid].build_order.append(build_event)

    def _process_unit_init(self, event):
        """Process UnitInitEvent (buildings)."""
        pid = getattr(event, "control_pid", None)
        if pid not in self._player_features:
            return

        unit_type = self._get_unit_type(event)
        if not unit_type or unit_type == "Unknown":
            return

        build_event = BuildOrderEvent(
            second=event.second, unit_type=unit_type, is_building=True
        )
        self._player_features[pid].build_order.append(build_event)

    def _get_unit_type(self, event) -> str:
        """Extract unit type name from event."""
        return (
            getattr(event, "unit_type_name", None)
            or getattr(event, "unit_type", None)
            or "Unknown"
        )

    # ========================================================================
    # Upgrade Extraction
    # ========================================================================

    def _extract_upgrades(self):
        """Extract upgrade completion events."""
        if not self.replay or not hasattr(self.replay, "tracker_events"):
            return

        for event in self.replay.tracker_events:
            if event.name == "UpgradeCompleteEvent":
                pid = getattr(event, "pid", None)
                if pid not in self._player_features:
                    continue

                upgrade_name = getattr(event, "upgrade_type_name", "Unknown")
                category = self._categorize_upgrade(upgrade_name)

                upgrade_event = UpgradeEvent(
                    second=event.second,
                    upgrade_name=upgrade_name,
                    upgrade_category=category,
                )
                self._player_features[pid].upgrades.append(upgrade_event)

    def _categorize_upgrade(self, name: str) -> str:
        """Categorize upgrades into functional groups."""
        name_lower = name.lower()
        if any(x in name_lower for x in ["attack", "weapons"]):
            return "attack"
        if any(x in name_lower for x in ["armor", "plating", "carapace"]):
            return "armor"
        if any(x in name_lower for x in ["shield"]):
            return "shield"
        if any(x in name_lower for x in ["speed", "boost", "thermal"]):
            return "speed"
        return "tech"

    # ========================================================================
    # Ability Extraction
    # ========================================================================

    def _extract_ability_usage(self):
        """Extract micro ability usage counts."""
        if not self.replay or not hasattr(self.replay, "game_events"):
            return

        # Option B: use dynamic discovery if enabled
        if self.use_dynamic_discovery and self.ability_discovery:
            self.ability_discovery.discover_from_replay(self.replay)

        for event in self.replay.game_events:
            if event.name != "CmdEvent":
                continue

            pid = getattr(event, "player", None)
            if (
                pid is None
                or not hasattr(pid, "pid")
                or pid.pid not in self._player_features
            ):
                continue

            ability_name = getattr(event, "ability_name", "Unknown")

            # Option B Check
            if self.use_dynamic_discovery and self.ability_discovery:
                if self.ability_discovery.should_track_ability(ability_name):
                    self._record_ability(pid.pid, ability_name)
            # Legacy Fallback
            elif ability_name in TRACKED_ABILITIES:
                self._record_ability(pid.pid, ability_name)

    def _record_ability(self, pid: int, ability_name: str):
        """Helper to record ability usage in features."""
        features = self._player_features[pid]
        features.ability_usage.total_abilities += 1
        features.ability_usage.abilities[ability_name] = (
            features.ability_usage.abilities.get(ability_name, 0) + 1
        )

    # ========================================================================
    # Resource Checkpoint Extraction
    # ========================================================================

    def _extract_resource_checkpoints(self, intervals: Optional[List[int]] = None):
        """
        Extract resource state at key game moments.

        Args:
            intervals: List of game seconds to sample (default: 60, 120, 180, 300, 600)
        """
        if intervals is None:
            intervals = [60, 120, 180, 300, 600, 900]  # 1, 2, 3, 5, 10, 15 min

        # For accurate resource tracking, we'd need to process PlayerStatsEvent
        # This is a simplified version based on available data
        for pid, features in self._player_features.items():
            if not self.replay or not hasattr(self.replay, "game_length"):
                continue

            game_len = self.replay.game_length.seconds
            for second in intervals:
                if second > game_len:
                    break
                # Implementation would go here if sc2reader supported periodic snapshots
                # Currently using placeholders or end-of-game stats if available

    # ========================================================================
    # Combat/Harassment Extraction
    # ========================================================================

    def _extract_harassment_losses(self):
        """Identify early game worker losses."""
        if not self.replay or not hasattr(self.replay, "tracker_events"):
            return

        for event in self.replay.tracker_events:
            if event.name == "UnitDiedEvent":
                unit_type = self._get_unit_type(event)
                if unit_type in {"SCV", "Probe", "Drone"} and event.second < 300:
                    owner_pid = getattr(event, "unit_pid", None)
                    if owner_pid in self._player_features:
                        self._player_features[owner_pid].early_worker_losses += 1

    def _extract_supply_blocks(self):
        """Identify macro bottlenecks."""
        # This requires periodic supply checks from tracker events
        pass

    # ========================================================================
    # Calculation & Transformation
    # ========================================================================

    def _calculate_build_hashes(self):
        """Generate a hash for build order comparison/clustering."""
        for features in self._player_features.values():
            if not features.build_order:
                continue

            # Take first 10 significant units (non-worker)
            major_units = [
                e.unit_type for e in features.build_order if not e.is_worker
            ][:10]
            build_str = ",".join(major_units)
            features.build_order_hash = hashlib.md5(build_str.encode()).hexdigest()[:16]

    def _classify_build_types(self):
        """Heuristic classification of playstyle."""
        for features in self._player_features.values():
            # Rough heuristics
            if features.early_worker_losses > 5:
                features.detected_build_type = "harassed"
            # More classification logic would be implemented here

    def _calculate_upgrade_scores(self):
        """Score tech timing relative to game duration."""
        for features in self._player_features.values():
            if not features.upgrades:
                continue

            # Identify first upgrades
            attack = [u for u in features.upgrades if u.upgrade_category == "attack"]
            if attack:
                features.first_attack_upgrade_second = min(u.second for u in attack)

            armor = [u for u in features.upgrades if u.upgrade_category == "armor"]
            if armor:
                features.first_armor_upgrade_second = min(u.second for u in armor)

    def _calculate_ability_efficiency(self):
        """Calculate APM-normalized ability usage."""
        if not self.replay or not hasattr(self.replay, "game_length"):
            return

        game_mins = self.replay.game_length.seconds / 60.0
        if game_mins == 0:
            return

        for features in self._player_features.values():
            features.ability_usage.abilities_per_minute = (
                features.ability_usage.total_abilities / game_mins
            )

    def _calculate_harassment_response(self):
        """Calculate score based on worker loss handling."""
        for features in self._player_features.values():
            # Higher is better (less losses)
            features.harassment_response_score = max(
                0, 100 - (features.early_worker_losses * 10)
            )


# ============================================================================
# API Convenience Functions
# ============================================================================


def parse_replay_enhanced(replay_path: str) -> Dict[int, EnhancedPlayerFeatures]:
    """
    Parse replay and extract enhanced ML-ready features.

    Args:
        replay_path: Path to .SC2Replay file

    Returns:
        Dictionary mapping player_id -> EnhancedPlayerFeatures
    """
    parser = EnhancedReplayParser(replay_path)
    return parser.parse()


def parse_replay_enhanced_dict(replay_path: str) -> Dict[int, Dict]:
    """
    Parse replay and return features as JSON-serializable dictionaries.

    Args:
        replay_path: Path to .SC2Replay file

    Returns:
        Dictionary mapping player_id -> feature dict
    """
    features = parse_replay_enhanced(replay_path)
    return {pid: f.__dict__ for pid, f in features.items()}
