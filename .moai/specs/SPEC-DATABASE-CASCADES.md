# SPEC-DATABASE-CASCADES: Database Cascade Deletes & Standardized Result Interface

**Version**: 1.0.0
**Status**: Draft
**Priority**: High
**Estimated Effort**: 1-2 hours

---

## 1. Overview

### 1.1 Problem Statement
Currently, deleting a match or a player might fail or leave orphaned records because foreign key constraints do not automatically cascade. This makes database maintenance and testing difficult. Additionally, there is no standardized interface for match results between the parser and various services, leading to type narrowing issues.

### 1.2 Proposed Solution
1. Implement `ON DELETE CASCADE` for all relevant foreign keys in the SQLAlchemy models.
2. Recreate the SQLite database with these new constraints.
3. Define a `ProcessedMatchResult` dataclass to serve as a standard interface.

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-1: Cascade Deletes in Models
Update `backend/app/models.py` to include `ondelete="CASCADE"` in `ForeignKey` definitions for:
- `MatchPlayer` (match_id, player_id)
- `PlayerMatchMetrics` (match_player_id)
- `PerformanceFeatures` (match_player_id)
- `PlayerAchievement` (player_id, achievement_id, trigger_match_id)
- `PlayerSynergy` (player1_id, player2_id)
- `PlayerRivalry` (player1_id, player2_id, last_match_id)

#### FR-2: Database Migration
A Python script to:
1. Enable foreign keys in SQLite.
2. Create a temporary schema or drop and recreate tables (since SQLite's `ALTER TABLE` is limited for foreign keys).
3. Verify the new schema.

#### FR-3: Standardized Result Interface
Create `backend/app/types/results.py` with `ProcessedMatchResult` dataclass following type narrowing guidelines.

---

## 3. Implementation Details

### 3.1 Model Changes
```python
# Example for MatchPlayer
match_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
)
```

### 3.2 Dataclass Definition
```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class ProcessedMatchResult:
    # Match metadata
    played_at: datetime
    game_mode: str
    map_name: str
    duration_seconds: int
    # ... other fields
```

---

## 4. Verification Plan

### 4.1 Migration Verification
1. Run the migration script.
2. Inspect schema using `PRAGMA foreign_key_list(table_name)`.

### 4.2 Functional Verification
1. Insert a test match with participants, metrics, and features.
2. Delete the match.
3. Verify that `match_players`, `player_match_metrics`, and `performance_features` for that match are gone.

---

**End of SPEC-DATABASE-CASCADES**
