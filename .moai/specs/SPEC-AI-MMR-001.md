# SPEC-AI-MMR-001: Dynamic AI MMR for Team Balancing

**Version**: 1.1.0
**Status**: Draft
**Priority**: Medium
**Estimated Effort**: 2-3 hours

---

## 1. Overview

### 1.1 Problem Statement
When players queue for a match with an odd number of participants, an AI (computer-controlled player) must fill the gap. Currently, there is no mechanism to assign a skill rating to this AI for team balancing purposes.

### 1.2 Proposed Solution
Assign a **fixed MMR** to the AI slot based on the selected difficulty. These values are calibrated to approximate SC2 ladder ranks.

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-1: Fixed AI MMR per Difficulty
Each AI difficulty maps to a fixed MMR value, calibrated against your player group:

| Difficulty | MMR   | Equivalent Player Level |
|------------|-------|-------------------------|
| Very Easy  | 1400  | Below INterprime        |
| Easy       | 1650  | ~DemonSlayer level      |
| Medium     | 1900  | ~Redevilz/wudok         |
| Hard       | 2100  | ~ChrisO/Cyrexg          |
| Very Hard  | 2350  | ~shunmanFan             |
| Elite      | 2500  | ~Sirhc (below HahaLolo) |

> **Calibration Note**: Stephan (3455 MMR) beats Elite AI easily, so Elite is placed at ~2500 (mid-pack). Adjust these values after testing real matches.

#### FR-2: Single AI Slot Only
Only **one AI** can be added per match. This simplifies the API and balancing logic.

#### FR-3: Use AI MMR in Balancing Algorithm
The existing `teams.py` balancing logic should treat the AI slot as a virtual player with the fixed MMR for the selected difficulty.

---

## 3. API Changes

### 3.1 Request Model Update

Modify the team balance request to support an optional AI:

```python
class BalanceRequest(BaseModel):
    player_ids: List[int]
    ai_difficulty: Optional[str] = None  # "easy", "medium", "hard", "very_hard", "elite"
```

### 3.2 Example Request

```json
POST /teams/balance
{
  "player_ids": [1, 4, 5, 6, 12],
  "ai_difficulty": "hard"
}
```

### 3.3 Response Model Update

The response indicates which team the AI is placed on:

```json
{
  "team1": {
    "players": [{"id": 4, "name": "Stephan"}, {"id": 12, "name": "DemonSlayer"}],
    "has_ai": true,
    "ai_mmr": 2400
  },
  "team2": {
    "players": [{"id": 1, "name": "ChrisO"}, {"id": 5, "name": "Tingmore"}, {"id": 6, "name": "shunmanFan"}],
    "has_ai": false,
    "ai_mmr": null
  },
  "win_probability": 0.52
}
```

---

## 4. Implementation Details

### 4.1 AI MMR Lookup

```python
AI_MMR_VALUES = {
    "very_easy": 1200,
    "easy": 1600,
    "medium": 2000,
    "hard": 2400,
    "very_hard": 2700,
    "elite": 3000,
}

def get_ai_mmr(difficulty: str) -> float:
    return AI_MMR_VALUES.get(difficulty, 2000)  # Default to Medium
```

### 4.2 Integrating with Team Balancer

1. If `ai_difficulty` is provided, calculate `ai_mmr = get_ai_mmr(ai_difficulty)`.
2. Create a "virtual player" with this MMR.
3. Pass all players + virtual AI to the balancer.
4. Balancer assigns AI to a team to minimize MMR difference.
5. Response includes `has_ai: true` and `ai_mmr` on the appropriate team.

---

## 5. Verification Plan

### 5.1 Unit Tests
- Test `get_ai_mmr` with all difficulty levels.
- Test balancer assigns AI to weaker team to balance.

### 5.2 Integration Test
- POST `/teams/balance` with 5 human players + `ai_difficulty: "hard"`.
- Verify response includes AI on one team.
- Verify `win_probability` accounts for AI.

---

**End of SPEC-AI-MMR-001**

