# SPEC-PHASE4-BUILD-CLASSIFICATION: Build Order Clustering

## Overview
Phase 4 implements automated build order classification using unsupervised learning (K-Means Clustering). This allows the system to identify player strategies (e.g., Cheese, Rush, Macro) without manual labeling.

## Objectives
- Extract tactical features from build order sequences.
- Cluster build orders into meaningful archetypes.
- Provide human-readable labels for identified clusters.
- Enable automatic strategy detection for future match analysis.

## Implementation Details

### Feature Extraction
The `BuildFeatureExtractor` captures:
1. **Timing**: First army unit, first expansion, first tech building.
2. **Composition**: Count of workers, army units, and buildings in the first 5 minutes.
3. **Identity**: Player race and name.

### Clustering Logic
- **Algorithm**: K-Means (scikit-learn).
- **Fallback**: Rule-based heuristic classification for small datasets (< 20 samples).
- **Normalization**: Features are normalized to a 0-1 range based on game time (600s) and typical unit counts.

### Integration
- Triggered during the ML feature extraction pipeline in `ReplayService`.
- Results stored in `performance_features.detected_build_type`.
- Exposed via `/adaptive/build-order/retrain` for model updates.

## Success Metrics
- 90% agreement between clustering archetypes and manual rule-based heuristics.
- Successful classification of at least 5 distinct archetypes on a balanced dataset.
- System stability during training with varying dataset sizes.
