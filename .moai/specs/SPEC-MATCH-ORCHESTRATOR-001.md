# SPEC-MATCH-ORCHESTRATOR-001: Match Orchestrator Implementation

## Status
- **Type**: Refactoring / Architecture
- **Status**: Proposed
- **Owner**: @user
- **Created**: 2025-12-27

## Context
The current match processing logic is scattered across `ReplayService` and `MatchService`. This duplication leads to inconsistencies, especially in handling manual winner resolution and ensuring all pipelines (ML extraction, rating updates, etc.) are executed correctly. We need a Single Source of Truth for the match lifecycle.

## Requirements
1. Implement `backend/app/services/match_orchestrator.py`.
2. The orchestrator must handle: Duplicate Detection -> Parsing -> DB Creation -> Rating Pipeline -> ML Extraction -> Advanced Metrics -> Online Learning.
3. Refactor `ReplayService` and `MatchService` to delegate their core logic to the orchestrator.
4. Ensure manual winner resolution uses the same orchestration pipeline.
5. Verify that rating recalculations are triggered correctly when matches are deleted.

## Design

### MatchOrchestrator
The `MatchOrchestrator` will provide a unified interface for processing matches from replay files, whether they are new uploads or manual resolutions of failed uploads.

```python
class MatchOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.ml_service = MLFeaturesService
        self.rating_service = RatingService(db)
        # ... other services

    def process_replay(
        self,
        file_path: str,
        filename: str,
        manual_winner_team: Optional[int] = None,
        use_advanced_parser: bool = True
    ) -> MatchProcessingResult:
        # 1. Parsing
        # 2. Duplicate Detection (by hash)
        # 3. Match Record Creation
        # 4. Rating Pipeline (TrueSkill + Performance)
        # 5. ML Extraction
        # 6. Advanced Metrics
        # 7. Online Learning Trigger
        # 8. Auto-optimization Trigger
        pass
```

### Refactoring ReplayService
- Remove `_execute_replay_processing` and related private methods that handle the pipeline.
- Delegate `process_replay` and `process_replay_with_manual_winner` to `MatchOrchestrator`.

### Refactoring MatchService
- Delegate `set_manual_winner` to `MatchOrchestrator`.
- Ensure `delete_match` properly triggers `RatingService.recalculate_all_ratings()`.

## Implementation Plan

### Phase 1: MatchOrchestrator Implementation
- [ ] Create `backend/app/services/match_orchestrator.py`.
- [ ] Move pipeline logic from `ReplayService` to `MatchOrchestrator`.
- [ ] Support manual winner override in the orchestrator.

### Phase 2: ReplayService Refactoring
- [ ] Update `ReplayService` to use `MatchOrchestrator`.
- [ ] Clean up redundant methods in `ReplayService`.

### Phase 3: MatchService Refactoring
- [ ] Update `MatchService.set_manual_winner` to use `MatchOrchestrator`.
- [ ] Ensure `MatchService.delete_match` remains robust.

### Phase 4: Verification
- [ ] Run existing tests: `test_ml_pipeline_e2e.py`, `test_advanced_parsing_e2e.py`.
- [ ] Create a new test for the orchestrator if needed.

## Acceptance Criteria
- [ ] `MatchOrchestrator` handles the full match lifecycle.
- [ ] `ReplayService` and `MatchService` are significantly simplified.
- [ ] Manual winner resolution follows the exact same pipeline as normal uploads.
- [ ] All tests pass.
