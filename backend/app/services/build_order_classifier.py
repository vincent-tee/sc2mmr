"""
Build Order Classifier - K-Means Clustering Approach

Classifies player build orders into archetypes (cheese, rush, macro, timing, etc.)
using K-means clustering on extracted build order features.

Features:
1. Works with small datasets (5+ matches)
2. Automatically identifies build archetypes
3. Provides confidence scores for predictions
4. Scales as more data becomes available

SPEC-ML-001 Implementation.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, cast
from collections import Counter

import numpy as np
from sqlalchemy.orm import Session

from ..models import PerformanceFeatures, MatchPlayer, Player

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class BuildFeatures:
    """Extracted features from a build order for clustering."""

    match_player_id: int
    player_name: str
    race: str

    # Timing features (normalized to game seconds)
    first_army_unit_time: float = 999  # Time to first non-worker unit
    first_expansion_time: float = 999  # Time to second base
    first_tech_time: float = 999  # Time to first tech building

    # Composition features (counts in first 5 minutes)
    early_worker_count: int = 0
    early_army_count: int = 0
    early_building_count: int = 0

    # Build order hash for exact matching
    build_hash: str = ""

    # Classification result (filled after clustering)
    archetype: str = "unknown"
    confidence: float = 0.0


@dataclass
class BuildArchetype:
    """Represents a build archetype cluster."""

    name: str
    description: str
    centroid: np.ndarray  # Cluster center
    examples: List[str] = field(default_factory=list)  # Player names with this build
    count: int = 0


# ============================================================================
# Build Archetype Definitions (Initial Seeds)
# ============================================================================

# Standard build type rules based on timing
BUILD_TYPE_RULES = {
    "cheese": {
        "first_army_time_max": 90,  # Army before 1:30
        "description": "Very early aggression (proxy, cannon rush, etc.)",
    },
    "rush": {
        "first_army_time_max": 150,  # Army before 2:30
        "first_expansion_time_min": 240,  # No expand before 4:00
        "description": "Early aggression with delayed expansion",
    },
    "timing_attack": {
        "first_expansion_time_max": 180,  # Expand before 3:00
        "first_army_time_max": 180,  # Army before 3:00
        "description": "Economic opening into timed aggression",
    },
    "macro": {
        "first_expansion_time_max": 150,  # Fast expand before 2:30
        "description": "Economy-focused opening",
    },
    "standard": {
        "description": "Balanced opening (default)",
    },
}


# ============================================================================
# Feature Extraction
# ============================================================================


class BuildFeatureExtractor:
    """Extracts ML-ready features from build order JSON."""

    # Tech buildings by race
    TECH_BUILDINGS = {
        "Terran": {"Factory", "Starport", "GhostAcademy", "Armory", "FusionCore"},
        "Protoss": {
            "CyberneticsCore",
            "TwilightCouncil",
            "RoboticsFacility",
            "Stargate",
            "TemplarArchive",
            "DarkShrine",
            "FleetBeacon",
        },
        "Zerg": {
            "RoachWarren",
            "BanelingNest",
            "HydraliskDen",
            "LurkerDen",
            "InfestationPit",
            "Spire",
            "UltraliskCavern",
        },
    }

    # Expansion buildings
    EXPANSION_BUILDINGS = {"CommandCenter", "Nexus", "Hatchery"}

    # Worker units
    WORKERS = {"SCV", "Probe", "Drone"}

    @classmethod
    def extract_features(
        cls,
        build_order_json: List[Dict[str, Any]],
        race: str,
        match_player_id: int,
        player_name: str,
        build_hash: str = "",
    ) -> BuildFeatures:
        """
        Extract clustering features from build order.
        """
        features = BuildFeatures(
            match_player_id=match_player_id,
            player_name=player_name,
            race=race,
            build_hash=build_hash,
        )

        if not build_order_json:
            return features

        # Track counts
        worker_count = 0
        army_count = 0
        building_count = 0
        base_count = 1  # Start with main base

        tech_buildings = cls.TECH_BUILDINGS.get(race, set())

        for event in build_order_json:
            unit_type = str(event.get("unit_type", ""))
            second = int(event.get("second", 0))
            is_building = bool(event.get("is_building", False))
            is_worker = bool(event.get("is_worker", False)) or unit_type in cls.WORKERS

            # First army unit timing
            if (
                not is_worker
                and not is_building
                and features.first_army_unit_time == 999
            ):
                features.first_army_unit_time = float(second)

            # First expansion timing
            if unit_type in cls.EXPANSION_BUILDINGS:
                base_count += 1
                if base_count == 2 and features.first_expansion_time == 999:
                    features.first_expansion_time = float(second)

            # First tech building timing
            if unit_type in tech_buildings and features.first_tech_time == 999:
                features.first_tech_time = float(second)

            # Early game counts (first 5 minutes = 300 seconds)
            if second <= 300:
                if is_worker:
                    worker_count += 1
                elif is_building:
                    building_count += 1
                else:
                    army_count += 1

        features.early_worker_count = worker_count
        features.early_army_count = army_count
        features.early_building_count = building_count

        return features


# ============================================================================
# Rule-Based Classification (Fallback)
# ============================================================================


def classify_by_rules(features: BuildFeatures) -> Tuple[str, float]:
    """
    Classify build using rule-based approach.
    """
    # Check each rule set
    if features.first_army_unit_time < 90:
        return "cheese", 0.85

    if features.first_army_unit_time < 150 and features.first_expansion_time > 240:
        return "rush", 0.80

    if features.first_expansion_time < 150:
        return "macro", 0.75

    if features.first_expansion_time < 180 and features.first_army_unit_time < 180:
        return "timing_attack", 0.70

    return "standard", 0.60


# ============================================================================
# K-Means Clustering (When Enough Data)
# ============================================================================


class BuildOrderClusterer:
    """
    K-Means clustering for build order classification.
    """

    def __init__(self, n_clusters: int = 5, min_samples: int = 10):
        self.n_clusters = n_clusters
        self.min_samples = min_samples
        self.centroids: Optional[np.ndarray] = None
        self.labels_: Optional[np.ndarray] = None
        self.fitted = False

    def _features_to_vector(self, features: BuildFeatures) -> np.ndarray:
        """Convert BuildFeatures to feature vector for clustering."""
        return np.array(
            [
                features.first_army_unit_time / 600,  # Normalize to 10 min
                features.first_expansion_time / 600,
                features.first_tech_time / 600,
                features.early_worker_count / 30,  # Normalize to ~30 workers
                features.early_army_count / 20,
                features.early_building_count / 10,
            ]
        )

    def fit(self, features_list: List[BuildFeatures]) -> bool:
        """
        Fit clustering model on build features.
        """
        if len(features_list) < self.min_samples:
            logger.info(
                f"Not enough samples for clustering ({len(features_list)} < {self.min_samples}), "
                "using rule-based classification"
            )
            return False

        # Convert to numpy array
        X = np.array([self._features_to_vector(f) for f in features_list])

        try:
            from sklearn.cluster import KMeans

            kmeans = KMeans(
                n_clusters=min(self.n_clusters, len(features_list)),
                random_state=42,
                n_init=10,  # type: ignore
            )
            self.labels_ = kmeans.fit_predict(X)
            self.centroids = kmeans.cluster_centers_
            self.fitted = True
            logger.info(f"K-Means clustering fitted with {self.n_clusters} clusters")
            return True

        except ImportError:
            logger.warning(
                "scikit-learn not available, using rule-based classification"
            )
            return False

    def predict(self, features: BuildFeatures) -> Tuple[int, float]:
        """
        Predict cluster for a single build.
        """
        if not self.fitted or self.centroids is None:
            return -1, 0.0

        vector = self._features_to_vector(features)

        # Find nearest centroid
        distances = np.linalg.norm(self.centroids - vector, axis=1)
        cluster_id = int(np.argmin(distances))
        min_distance = distances[cluster_id]

        # Confidence based on distance (closer = higher confidence)
        confidence = max(0.0, 1.0 - min_distance / 2.5)

        return cluster_id, confidence


# ============================================================================
# Main Classifier Service
# ============================================================================


class BuildOrderClassifier:
    """
    Main service for build order classification.
    """

    # Cluster ID to archetype name mapping (updated during training)
    CLUSTER_NAMES = {
        0: "cheese",
        1: "rush",
        2: "timing_attack",
        3: "macro",
        4: "standard",
    }

    def __init__(self):
        self.clusterer = BuildOrderClusterer(n_clusters=5, min_samples=20)
        self.use_clustering = False

    def train(self, db: Session) -> Dict[str, Any]:
        """
        Train classifier on all available build data.
        """
        # Get all performance features with build orders
        features_records = (
            db.query(PerformanceFeatures)
            .filter(PerformanceFeatures.build_order_json.isnot(None))
            .all()
        )

        if not features_records:
            logger.warning("No build order data available for training")
            return {"status": "no_data", "samples": 0}

        # Extract features
        build_features: List[BuildFeatures] = []
        for pf in features_records:
            # 1. Validate and Narrow (Recursive Type Resolution Pattern)
            if not isinstance(pf.build_order_json, list):
                continue

            mp = (
                db.query(MatchPlayer)
                .filter(MatchPlayer.id == pf.match_player_id)
                .first()
            )

            if not mp:
                continue

            player = db.query(Player).filter(Player.id == mp.player_id).first()
            if not player:
                continue

            # 2. Cast and Process
            build_data = cast(List[Dict[str, Any]], pf.build_order_json)

            features = BuildFeatureExtractor.extract_features(
                build_order_json=build_data,
                race=mp.race.value if hasattr(mp.race, "value") else str(mp.race),
                match_player_id=int(pf.match_player_id),
                player_name=str(player.name),
                build_hash=str(pf.build_order_hash or ""),
            )
            build_features.append(features)

        logger.info(f"Extracted features from {len(build_features)} build orders")

        # Try clustering
        self.use_clustering = self.clusterer.fit(build_features)

        if self.use_clustering:
            self._analyze_clusters(build_features)
            return {
                "status": "clustering",
                "samples": len(build_features),
                "clusters": self.clusterer.n_clusters,
            }
        else:
            return {
                "status": "rule_based",
                "samples": len(build_features),
                "reason": f"Not enough samples (need {self.clusterer.min_samples}+)",
            }

    def _analyze_clusters(self, features_list: List[BuildFeatures]) -> None:
        """Analyze clusters to determine archetype names."""
        if not self.clusterer.fitted or self.clusterer.labels_ is None:
            return

        # Group features by cluster
        cluster_features: Dict[int, List[BuildFeatures]] = {}
        for i, features in enumerate(features_list):
            cluster_id = int(self.clusterer.labels_[i])
            if cluster_id not in cluster_features:
                cluster_features[cluster_id] = []
            cluster_features[cluster_id].append(features)

        # Analyze each cluster's characteristics
        for cluster_id, cluster_list in cluster_features.items():
            avg_army_time = np.mean([f.first_army_unit_time for f in cluster_list])
            avg_expand_time = np.mean([f.first_expansion_time for f in cluster_list])

            # Determine archetype based on cluster averages
            if avg_army_time < 90:
                self.CLUSTER_NAMES[cluster_id] = "cheese"
            elif avg_army_time < 150 and avg_expand_time > 240:
                self.CLUSTER_NAMES[cluster_id] = "rush"
            elif avg_expand_time < 150:
                self.CLUSTER_NAMES[cluster_id] = "macro"
            elif avg_expand_time < 180:
                self.CLUSTER_NAMES[cluster_id] = "timing_attack"
            else:
                self.CLUSTER_NAMES[cluster_id] = "standard"

            logger.info(
                f"Cluster {cluster_id} ({len(cluster_list)} samples): "
                f"archetype={self.CLUSTER_NAMES[cluster_id]}, "
                f"avg_army_time={avg_army_time:.0f}s, "
                f"avg_expand_time={avg_expand_time:.0f}s"
            )

    def classify(
        self,
        build_order_json: List[Dict[str, Any]],
        race: str,
        match_player_id: int = 0,
        player_name: str = "",
    ) -> Tuple[str, float]:
        """
        Classify a build order.
        """
        features = BuildFeatureExtractor.extract_features(
            build_order_json=build_order_json,
            race=race,
            match_player_id=match_player_id,
            player_name=player_name,
        )

        if self.use_clustering:
            cluster_id, confidence = self.clusterer.predict(features)
            archetype = self.CLUSTER_NAMES.get(cluster_id, "unknown")
            return archetype, confidence
        else:
            return classify_by_rules(features)

    def classify_from_db(self, db: Session, match_player_id: int) -> Tuple[str, float]:
        """
        Classify a build from database records.
        """
        pf = (
            db.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == match_player_id)
            .first()
        )

        if not pf or not isinstance(pf.build_order_json, list):
            return "unknown", 0.0

        mp = db.query(MatchPlayer).filter(MatchPlayer.id == match_player_id).first()
        if not mp:
            return "unknown", 0.0

        player = db.query(Player).filter(Player.id == mp.player_id).first()
        race = mp.race.value if hasattr(mp.race, "value") else str(mp.race)

        # Recursive Type Resolution
        build_json = cast(List[Dict[str, Any]], pf.build_order_json)
        return self.classify(
            build_order_json=build_json,
            race=race,
            match_player_id=int(match_player_id),
            player_name=str(player.name if player else ""),
        )


# ============================================================================
# Singleton Instance
# ============================================================================

_classifier_instance: Optional[BuildOrderClassifier] = None


def get_classifier() -> BuildOrderClassifier:
    """Get or create the build order classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = BuildOrderClassifier()
    return _classifier_instance


def train_classifier(db: Session) -> Dict[str, Any]:
    """Train the build order classifier."""
    classifier = get_classifier()
    return classifier.train(db)


def classify_build(
    db: Session,
    match_player_id: int,
) -> Tuple[str, float]:
    """Classify a player's build order."""
    classifier = get_classifier()
    return classifier.classify_from_db(db, match_player_id)
