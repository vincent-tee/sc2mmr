"""
Enhanced SC2 Replay Parser - ML-Ready Feature Extraction

This module extends the advanced_parser to extract additional features for ML models:
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

import sc2reader
from sc2reader.events import (
    TrackerEvent,
)

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

    # Build Order Features
    build_order: List[BuildOrderEvent] = field(default_factory=list)
    build_order_hash: str = ""  # For clustering similar builds
    detected_build_type: str = "unknown"  # "rush", "macro", "timing", "cheese"

    # Upgrade Features
    upgrades: List[UpgradeEvent] = field(default_factory=list)
    upgrade_timing_score: float = 0.0  # Z-score vs average timings
    first_attack_upgrade_second: Optional[int] = None
    first_armor_upgrade_second: Optional[int] = None

    # Ability Features
    ability_usage: AbilityUsage = field(default_factory=AbilityUsage)
    ability_efficiency: float = 0.0  # Abilities per damage dealt

    # Resource Checkpoints
    resource_checkpoints: List[ResourceCheckpoint] = field(default_factory=list)
    resource_float_avg: float = 0.0  # Average unspent resources (lower = better macro)

    # Harassment Response
    early_worker_losses: int = 0  # Workers lost in first 5 minutes
    early_worker_loss_rate: float = 0.0  # % of starting workers lost
    harassment_response_score: float = 0.0  # 0-100, higher = better defense

    # Supply Management
    supply_block_seconds: int = 0  # Time spent supply blocked
    supply_efficiency: float = 0.0  # 0-1, higher = less time blocked


# ============================================================================
# Worker and Building Definitions
# ============================================================================

WORKER_UNITS = {"SCV", "Probe", "Drone"}

BUILDING_TYPES = {
    # Terran
    "CommandCenter", "CommandCenterFlying", "OrbitalCommand", "PlanetaryFortress",
    "SupplyDepot", "Refinery", "Barracks", "BarracksFlying",
    "EngineeringBay", "GhostAcademy", "Factory", "FactoryFlying",
    "Starport", "StarportFlying", "FusionCore", "TechLab", "Reactor",
    "Bunker", "MissileTurret", "SensorTower", "Armory",

    # Protoss
    "Nexus", "Pylon", "Assimilator", "Gateway", "WarpGate",
    "Forge", "CyberneticsCore", "PhotonCannon", "ShieldBattery",
    "RoboticsFacility", "RoboticsBay", "Stargate", "FleetBeacon",
    "TwilightCouncil", "TemplarArchive", "DarkShrine",

    # Zerg
    "Hatchery", "Lair", "Hive", "SpawningPool", "EvolutionChamber",
    "Extractor", "RoachWarren", "BanelingNest", "HydraliskDen",
    "LurkerDen", "InfestationPit", "Spire", "GreaterSpire",
    "UltraliskCavern", "NydusNetwork", "NydusCanal",
    "SpineCrawler", "SporeCrawler", "CreepTumor",
}

UPGRADE_CATEGORIES = {
    # Terran Attack
    "TerranInfantryWeaponsLevel1": "attack",
    "TerranInfantryWeaponsLevel2": "attack",
    "TerranInfantryWeaponsLevel3": "attack",
    "TerranVehicleWeaponsLevel1": "attack",
    "TerranVehicleWeaponsLevel2": "attack",
    "TerranVehicleWeaponsLevel3": "attack",
    "TerranShipWeaponsLevel1": "attack",
    "TerranShipWeaponsLevel2": "attack",
    "TerranShipWeaponsLevel3": "attack",

    # Terran Armor
    "TerranInfantryArmorsLevel1": "armor",
    "TerranInfantryArmorsLevel2": "armor",
    "TerranInfantryArmorsLevel3": "armor",
    "TerranVehicleArmorsLevel1": "armor",
    "TerranVehicleArmorsLevel2": "armor",
    "TerranVehicleArmorsLevel3": "armor",
    "TerranShipArmorsLevel1": "armor",
    "TerranShipArmorsLevel2": "armor",
    "TerranShipArmorsLevel3": "armor",

    # Terran Abilities
    "Stimpack": "ability",
    "CombatShield": "ability",
    "ConcussiveShells": "ability",
    "InfernalPreIgniter": "ability",
    "DrillingClaws": "ability",
    "TransformationServos": "ability",
    "PersonalCloaking": "ability",
    "EnhancedShockwaves": "ability",
    "CorvidReactor": "ability",
    "BehemothReactor": "ability",
    "HighCapacityFuelTanks": "ability",
    "RavenCorvidReactor": "ability",

    # Protoss Attack
    "ProtossGroundWeaponsLevel1": "attack",
    "ProtossGroundWeaponsLevel2": "attack",
    "ProtossGroundWeaponsLevel3": "attack",
    "ProtossAirWeaponsLevel1": "attack",
    "ProtossAirWeaponsLevel2": "attack",
    "ProtossAirWeaponsLevel3": "attack",

    # Protoss Armor
    "ProtossGroundArmorsLevel1": "armor",
    "ProtossGroundArmorsLevel2": "armor",
    "ProtossGroundArmorsLevel3": "armor",
    "ProtossAirArmorsLevel1": "armor",
    "ProtossAirArmorsLevel2": "armor",
    "ProtossAirArmorsLevel3": "armor",
    "ProtossShieldsLevel1": "armor",
    "ProtossShieldsLevel2": "armor",
    "ProtossShieldsLevel3": "armor",

    # Protoss Abilities
    "WarpGateResearch": "ability",
    "Blink": "ability",
    "Charge": "ability",
    "ResonatingGlaives": "ability",
    "PsionicStorm": "ability",
    "GraviticBoosters": "ability",
    "GraviticDrive": "ability",
    "ExtendedThermalLance": "ability",
    "FluxVanes": "ability",
    "AnionPulseCrystals": "ability",
    "ShadowStride": "ability",

    # Zerg Attack
    "ZergMeleeWeaponsLevel1": "attack",
    "ZergMeleeWeaponsLevel2": "attack",
    "ZergMeleeWeaponsLevel3": "attack",
    "ZergMissileWeaponsLevel1": "attack",
    "ZergMissileWeaponsLevel2": "attack",
    "ZergMissileWeaponsLevel3": "attack",
    "ZergFlyerWeaponsLevel1": "attack",
    "ZergFlyerWeaponsLevel2": "attack",
    "ZergFlyerWeaponsLevel3": "attack",

    # Zerg Armor
    "ZergGroundArmorsLevel1": "armor",
    "ZergGroundArmorsLevel2": "armor",
    "ZergGroundArmorsLevel3": "armor",
    "ZergFlyerArmorsLevel1": "armor",
    "ZergFlyerArmorsLevel2": "armor",
    "ZergFlyerArmorsLevel3": "armor",

    # Zerg Abilities
    "ZerglingMetabolicBoost": "speed",
    "ZerglingAdrenalGlands": "ability",
    "CentrifugalHooks": "ability",
    "GlialReconstitution": "speed",
    "TunnelingClaws": "ability",
    "MuscularAugments": "speed",
    "GroovedSpines": "ability",
    "AdaptiveTalons": "ability",
    "SeismicSpines": "ability",
    "PathogenGlands": "ability",
    "NeuralParasite": "ability",
    "ChitinousPlating": "armor",
    "AnabolicSynthesis": "speed",
}

# Important abilities for micro skill assessment
TRACKED_ABILITIES = {
    # Terran
    "Stimpack", "250mmStrikeCannons", "Snipe", "EMP", "NuclearStrike",
    "TacticalJump", "Yamato", "ScannerSweep", "CalldownMULE", "SupplyDrop",

    # Protoss
    "Blink", "PsionicStorm", "Feedback", "ForceField", "GuardianShield",
    "PrismaticAlignment", "Revelation", "StasisWard", "PurificationNova",
    "MassRecall", "StrategicRecall", "ChronoBoost",

    # Zerg
    "SpawnChangeling", "Contaminate", "NeuralParasite", "FungalGrowth",
    "InfestorTerran", "Transfusion", "SpawnLarva", "Abduct", "BlindingCloud",
    "ParasiticBomb", "ConsumptiveCloud",
}


# ============================================================================
# Enhanced Parser Class
# ============================================================================

class EnhancedReplayParser:
    """
    Extract ML-ready features from SC2 replays.

    This parser extends the existing advanced_parser to capture:
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

    def parse(self) -> Dict[int, EnhancedPlayerFeatures]:
        """
        Parse replay and extract all enhanced features.

        Returns:
            Dictionary mapping player_id to EnhancedPlayerFeatures
        """
        try:
            # Load replay with maximum detail
            self.replay = sc2reader.load_replay(self.replay_path, load_level=4)

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

    def _clean_player_name(self, player) -> str:
        """Remove clan tag from player name."""
        name = player.name
        if hasattr(player, 'clan_tag') and player.clan_tag:
            name = name.replace(f"[{player.clan_tag}]", "").strip()
        return name

    # ========================================================================
    # Build Order Extraction
    # ========================================================================

    def _extract_build_orders(self):
        """Extract chronological build order for each player."""
        if not hasattr(self.replay, 'tracker_events'):
            logger.warning("No tracker events available for build order extraction")
            return

        for event in self.replay.tracker_events:
            # Unit born events (most production)
            if event.name == 'UnitBornEvent':
                self._process_unit_born(event)

            # Unit init events (buildings start construction)
            elif event.name == 'UnitInitEvent':
                self._process_unit_init(event)

    def _process_unit_born(self, event):
        """Process UnitBornEvent for build order."""
        pid = getattr(event, 'control_pid', None)
        if pid not in self._player_features:
            return

        unit_type = self._get_unit_type(event)
        if not unit_type or unit_type == "Unknown":
            return

        # Skip non-relevant units (map elements, temporary units, cosmetics, etc.)
        skip_prefixes = ("Beacon", "Reward", "Spray", "Destructible", "Collapsible",
                        "Mineral", "Vespene", "XelNaga", "Unbuildable", "Rich")
        if unit_type.startswith(skip_prefixes):
            return

        if unit_type in {"Larva", "Egg", "Cocoon", "LocustMP", "LocustMPFlying",
                          "Changeling", "InfestorTerran", "Broodling",
                          "AutoTurret", "PointDefenseDrone", "MULE",
                          "Interceptor", "AdeptPhaseShift"}:
            return

        build_event = BuildOrderEvent(
            second=event.second,
            unit_type=unit_type,
            supply=self._get_supply_at(pid, event.second),
            is_building=unit_type in BUILDING_TYPES,
            is_worker=unit_type in WORKER_UNITS,
        )

        self._player_features[pid].build_order.append(build_event)

    def _process_unit_init(self, event):
        """Process UnitInitEvent for building construction start."""
        pid = getattr(event, 'control_pid', None)
        if pid not in self._player_features:
            return

        unit_type = self._get_unit_type(event)
        if not unit_type or unit_type not in BUILDING_TYPES:
            return

        build_event = BuildOrderEvent(
            second=event.second,
            unit_type=unit_type,
            supply=self._get_supply_at(pid, event.second),
            is_building=True,
            is_worker=False,
        )

        self._player_features[pid].build_order.append(build_event)

    def _get_unit_type(self, event) -> Optional[str]:
        """Extract unit type from event with fallbacks."""
        try:
            return (
                getattr(event, 'unit_type_name', None) or
                getattr(event, 'unit_type', None) or
                getattr(getattr(event, 'unit', None), 'name', None) or
                None
            )
        except AttributeError:
            return None

    def _get_supply_at(self, player_id: int, second: int) -> int:
        """Get approximate supply at a given game second."""
        # Simplified - would need state tracking for accuracy
        # For now, estimate based on build order up to this point
        features = self._player_features.get(player_id)
        if not features:
            return 0

        supply = 12  # Starting supply
        for event in features.build_order:
            if event.second > second:
                break
            if event.is_worker:
                supply += 1
            elif not event.is_building:
                supply += 2  # Rough estimate
        return min(supply, 200)

    # ========================================================================
    # Upgrade Extraction
    # ========================================================================

    def _extract_upgrades(self):
        """Extract upgrade completion events for each player."""
        if not hasattr(self.replay, 'tracker_events'):
            return

        for event in self.replay.tracker_events:
            if event.name == 'UpgradeCompleteEvent':
                self._process_upgrade(event)

    def _process_upgrade(self, event):
        """Process upgrade completion event."""
        # Get player ID - different attribute names in different sc2reader versions
        pid = getattr(event, 'pid', None) or getattr(event, 'player_id', None)

        # Try to get from player object
        if pid is None and hasattr(event, 'player'):
            pid = getattr(event.player, 'pid', None)

        if pid not in self._player_features:
            return

        upgrade_name = getattr(event, 'upgrade_type_name', None) or str(event)

        # Skip cosmetic/reward upgrades
        skip_prefixes = ("Reward", "Spray", "Dance", "Skin", "Portrait", "Decal")
        if any(upgrade_name.startswith(prefix) for prefix in skip_prefixes):
            return

        category = UPGRADE_CATEGORIES.get(upgrade_name, "unknown")

        upgrade_event = UpgradeEvent(
            second=event.second,
            upgrade_name=upgrade_name,
            upgrade_category=category,
        )

        features = self._player_features[pid]
        features.upgrades.append(upgrade_event)

        # Track first attack/armor upgrades
        if category == "attack" and features.first_attack_upgrade_second is None:
            features.first_attack_upgrade_second = event.second
        elif category == "armor" and features.first_armor_upgrade_second is None:
            features.first_armor_upgrade_second = event.second

    # ========================================================================
    # Ability Usage Extraction
    # ========================================================================

    def _extract_ability_usage(self):
        """Extract ability usage counts for micro skill assessment."""
        if not hasattr(self.replay, 'game_events'):
            logger.warning("No game events available for ability extraction")
            return

        for event in self.replay.game_events:
            if hasattr(event, 'ability') and hasattr(event, 'player'):
                self._process_ability_event(event)

    def _process_ability_event(self, event):
        """Process ability usage event."""
        player = event.player
        if not player or not hasattr(player, 'pid'):
            return

        pid = player.pid
        if pid not in self._player_features:
            return

        ability_name = getattr(event.ability, 'name', None) or str(event.ability)

        # Only track significant abilities
        if ability_name not in TRACKED_ABILITIES:
            return

        features = self._player_features[pid]
        features.ability_usage.total_abilities += 1
        features.ability_usage.abilities[ability_name] = (
            features.ability_usage.abilities.get(ability_name, 0) + 1
        )

    # ========================================================================
    # Resource Checkpoint Extraction
    # ========================================================================

    def _extract_resource_checkpoints(self, intervals: List[int] = None):
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
            for second in intervals:
                if second > self.replay.game_length.seconds:
                    break

                checkpoint = ResourceCheckpoint(
                    second=second,
                    workers=self._estimate_workers_at(pid, second),
                    supply_used=self._get_supply_at(pid, second),
                )
                features.resource_checkpoints.append(checkpoint)

    def _estimate_workers_at(self, player_id: int, second: int) -> int:
        """Estimate worker count at a given second."""
        features = self._player_features.get(player_id)
        if not features:
            return 0

        workers = 12  # Starting workers
        for event in features.build_order:
            if event.second > second:
                break
            if event.is_worker:
                workers += 1

        # Account for early worker losses
        if second <= 300:  # First 5 minutes
            workers -= features.early_worker_losses

        return max(0, workers)

    # ========================================================================
    # Harassment Loss Extraction
    # ========================================================================

    def _extract_harassment_losses(self, cutoff_seconds: int = 300):
        """
        Extract early worker losses (first 5 minutes).

        Args:
            cutoff_seconds: Only count losses before this time (default: 300 = 5 min)
        """
        if not hasattr(self.replay, 'tracker_events'):
            return

        for event in self.replay.tracker_events:
            if event.name == 'UnitDiedEvent' and event.second <= cutoff_seconds:
                self._process_early_death(event)

    def _process_early_death(self, event):
        """Process early unit death for harassment tracking."""
        # Get owner of dead unit
        owner_pid = getattr(event, 'unit_upkeeper_id', None) or \
                    getattr(event, 'unit_pid', None) or \
                    getattr(getattr(event, 'unit', None), 'owner_id', None)

        if owner_pid not in self._player_features:
            return

        unit_type = self._get_unit_type(event)
        if unit_type in WORKER_UNITS:
            self._player_features[owner_pid].early_worker_losses += 1

    # ========================================================================
    # Supply Block Extraction
    # ========================================================================

    def _extract_supply_blocks(self):
        """
        Estimate time spent supply blocked.

        Note: This is an approximation. True supply block detection
        would require analyzing production queues.
        """
        # Simplified: check for gaps in unit production during high-activity periods
        for pid, features in self._player_features.items():
            if len(features.build_order) < 10:
                continue

            # Look for production gaps > 20 seconds (potential supply block)
            last_unit_time = 0
            supply_block_time = 0

            for event in features.build_order:
                if not event.is_worker and not event.is_building:
                    gap = event.second - last_unit_time
                    if gap > 20 and last_unit_time > 60:  # After first minute
                        # Likely supply blocked for part of this gap
                        supply_block_time += min(gap - 10, 30)  # Cap at 30 sec
                    last_unit_time = event.second

            features.supply_block_seconds = supply_block_time

    # ========================================================================
    # Derived Feature Calculations
    # ========================================================================

    def _calculate_build_hashes(self):
        """Calculate hash of build order for clustering similar builds."""
        for features in self._player_features.values():
            # Create hash from first 20 non-worker units
            key_units = [
                e.unit_type for e in features.build_order
                if not e.is_worker
            ][:20]

            hash_input = "-".join(key_units)
            features.build_order_hash = hashlib.md5(
                hash_input.encode()
            ).hexdigest()[:16]

    def _classify_build_types(self):
        """Classify build type based on build order patterns."""
        for features in self._player_features.values():
            features.detected_build_type = self._classify_single_build(features)

    def _classify_single_build(self, features: EnhancedPlayerFeatures) -> str:
        """Classify a single player's build."""
        build_order = features.build_order

        if len(build_order) < 5:
            return "unknown"

        # Get timing of first non-worker army unit
        first_army_time = None
        for event in build_order:
            if not event.is_worker and not event.is_building:
                first_army_time = event.second
                break

        # Get expansion timing
        expansion_time = None
        base_count = 0
        for event in build_order:
            if event.unit_type in {"CommandCenter", "Nexus", "Hatchery"}:
                base_count += 1
                if base_count == 2 and expansion_time is None:
                    expansion_time = event.second

        # Classification rules
        if first_army_time and first_army_time < 120:  # Army before 2 min
            return "cheese"
        elif first_army_time and first_army_time < 180:  # Army before 3 min
            return "rush"
        elif expansion_time and expansion_time < 180:  # Fast expand before 3 min
            return "macro"
        elif expansion_time and expansion_time > 300:  # Late expand after 5 min
            return "timing_attack"
        else:
            return "standard"

    def _calculate_upgrade_scores(self):
        """Calculate upgrade timing scores relative to averages."""
        # Average upgrade timings (in seconds) - rough estimates
        AVERAGE_FIRST_ATTACK = 420  # 7 minutes
        AVERAGE_FIRST_ARMOR = 480   # 8 minutes

        for features in self._player_features.values():
            score = 0.0
            count = 0

            if features.first_attack_upgrade_second:
                diff = AVERAGE_FIRST_ATTACK - features.first_attack_upgrade_second
                score += diff / 60  # Normalize to minutes
                count += 1

            if features.first_armor_upgrade_second:
                diff = AVERAGE_FIRST_ARMOR - features.first_armor_upgrade_second
                score += diff / 60
                count += 1

            if count > 0:
                features.upgrade_timing_score = score / count

    def _calculate_ability_efficiency(self):
        """Calculate ability usage per minute."""
        game_minutes = self.replay.game_length.seconds / 60

        for features in self._player_features.values():
            if game_minutes > 0:
                features.ability_usage.abilities_per_minute = (
                    features.ability_usage.total_abilities / game_minutes
                )

    def _calculate_harassment_response(self):
        """Calculate harassment response score (0-100)."""
        for features in self._player_features.values():
            # Score based on early worker losses
            # 0 losses = 100, each loss reduces by 10
            base_score = 100 - (features.early_worker_losses * 10)
            features.harassment_response_score = max(0, min(100, base_score))

            # Calculate loss rate (assuming 12 starting workers)
            features.early_worker_loss_rate = features.early_worker_losses / 12.0

    # ========================================================================
    # Export Functions
    # ========================================================================

    def to_dict(self) -> Dict[int, Dict]:
        """Export features as dictionary for database storage."""
        result = {}
        for pid, features in self._player_features.items():
            result[pid] = {
                "player_id": features.player_id,
                "player_name": features.player_name,
                "race": features.race,
                "team": features.team,
                "won": features.won,

                # Build order (as JSON-serializable list)
                "build_order": [
                    {
                        "second": e.second,
                        "unit_type": e.unit_type,
                        "supply": e.supply,
                        "is_building": e.is_building,
                    }
                    for e in features.build_order
                ],
                "build_order_hash": features.build_order_hash,
                "detected_build_type": features.detected_build_type,

                # Upgrades
                "upgrades": [
                    {
                        "second": u.second,
                        "upgrade_name": u.upgrade_name,
                        "category": u.upgrade_category,
                    }
                    for u in features.upgrades
                ],
                "upgrade_timing_score": features.upgrade_timing_score,
                "first_attack_upgrade_second": features.first_attack_upgrade_second,
                "first_armor_upgrade_second": features.first_armor_upgrade_second,

                # Abilities
                "ability_usage": features.ability_usage.abilities,
                "total_abilities": features.ability_usage.total_abilities,
                "abilities_per_minute": features.ability_usage.abilities_per_minute,

                # Resource checkpoints
                "resource_checkpoints": [
                    {
                        "second": c.second,
                        "workers": c.workers,
                        "supply_used": c.supply_used,
                    }
                    for c in features.resource_checkpoints
                ],

                # Harassment & Macro
                "early_worker_losses": features.early_worker_losses,
                "early_worker_loss_rate": features.early_worker_loss_rate,
                "harassment_response_score": features.harassment_response_score,
                "supply_block_seconds": features.supply_block_seconds,
            }
        return result


# ============================================================================
# Convenience Function
# ============================================================================

def parse_replay_enhanced(replay_path: str) -> Dict[int, EnhancedPlayerFeatures]:
    """
    Parse replay and extract enhanced ML-ready features.

    Args:
        replay_path: Path to .SC2Replay file

    Returns:
        Dictionary mapping player_id to EnhancedPlayerFeatures
    """
    parser = EnhancedReplayParser(replay_path)
    return parser.parse()


def parse_replay_enhanced_dict(replay_path: str) -> Dict[int, Dict]:
    """
    Parse replay and return features as JSON-serializable dictionaries.

    Args:
        replay_path: Path to .SC2Replay file

    Returns:
        Dictionary mapping player_id to feature dictionaries
    """
    parser = EnhancedReplayParser(replay_path)
    parser.parse()
    return parser.to_dict()
