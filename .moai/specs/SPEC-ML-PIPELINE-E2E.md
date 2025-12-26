# SPEC-ML-PIPELINE-E2E: End-to-End ML Pipeline Verification

**Version**: 1.0.0
**Status**: Draft
**Priority**: High
**Estimated Effort**: 1-2 hours

---

## 1. Overview

### 1.1 Problem Statement
The ML pipeline involves multiple stages: replay parsing, feature extraction, build order classification, and SHAP-based outcome explanation. Currently, these components are tested individually, but there is no single E2E test that verifies the integration of the entire pipeline from replay upload to API-retrievable explanations.

### 1.2 Proposed Solution
Implement an E2E test that uses a real SC2Replay file to exercise the full pipeline:
1. Upload a replay via API.
2. Verify feature extraction into `performance_features` table.
3. Verify XGBoost prediction generation.
4. Verify SHAP explanation generation and retrieval via the commentary API.
5. Verify build order category assignment.

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-1: Replay Upload Integration
The test must use the `TestClient` to upload a replay to `/replays/upload` and ensure it is processed without errors.

#### FR-2: Feature Extraction Verification
Verify that `PerformanceFeatures` records are created for all players in the match with populated build orders, abilities, and upgrades.

#### FR-3: XGBoost Prediction & SHAP Verification
Verify that the match commentary API returns SHAP impact values, indicating that the XGBoost model (or fallback) successfully processed the extracted features.

#### FR-4: Build Order Classification
Verify that `detected_build_type` is correctly assigned to at least one player based on the replay content.

---

## 3. Implementation Plan

### 3.1 Test Setup
- Use `backend/replays/f3522e58a5296a9bb9be3cece3a2679690f4dcf2e69c32cddb0e32d642d11d1a.SC2Replay` as the test replay.
- Ensure the database is clean for the test match.
- Mock external AI services if any, but keep the internal ML pipeline real.

### 3.2 Verification Steps
1. **API Upload**: `POST /replays/upload`
2. **DB Check**: Query `Match`, `MatchPlayer`, `PerformanceFeatures`.
3. **Commentary API**: `GET /replays/matches/{match_id}/commentary`
4. **Assertions**:
   - Response status codes are 200.
   - `shap_impacts` is a non-empty list in the commentary response.
   - `detected_build_type` is not null.

---

## 4. Verification Plan

### 4.1 Automated Tests
- Run `pytest backend/tests/test_ml_pipeline_e2e.py`.

---

**End of SPEC-ML-PIPELINE-E2E**
