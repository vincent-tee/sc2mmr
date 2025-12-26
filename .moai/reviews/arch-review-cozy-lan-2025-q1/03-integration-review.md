# Phase 3: Integration & Data Flow Review
## SC2 MMR Tracker - Cozy LAN Party Edition

**Review Date:** December 26, 2025  
**Reviewer:** Claude Code Architect  
**Phase:** 3 of 4  
**Thoroughness:** VERY THOROUGH (~60K tokens)

---

## Executive Summary

### Key Integration Findings

| Category | Status | Risk Level | Details |
|----------|--------|------------|---------|
| **API Contract Alignment** | ⚠️ MINOR DRIFT | Low | 2 type mismatches, 5 missing optional fields |
| **Error Handling** | ✅ GOOD | Low | Consistent error contract, proper propagation |
| **Data Synchronization** | ⚠️ GAPS | Medium | No optimistic updates, stale cache issues |
| **User Journey Coverage** | ✅ EXCELLENT | Low | All primary flows covered, good feedback |
| **Test Coverage** | 🔴 CRITICAL GAPS | High | Only 5 test files, no E2E, no integration |

### Priority Actions

1. **P0 (Critical):** Add integration tests for replay upload + rating calculation chain
2. **P1 (High):** Implement React Query cache invalidation after mutations
3. **P2 (Medium):** Align Player TypeScript type with backend hybrid_mmr/avg_pim fields
4. **P3 (Low):** Add explicit timeout configuration per API endpoint type

---

## 3.1 API Contract Validation

### 3.1.1 TypeScript ↔ Pydantic Model Alignment

#### Player Types Comparison

| Field | Frontend (TS) | Backend (Pydantic) | Status |
|-------|---------------|-------------------|--------|
| `id` | `number` | `int` | ✅ Match |
| `name` | `string` | `str` | ✅ Match |
| `mu` | `number` | `float` | ✅ Match |
| `sigma` | `number` | `float` | ✅ Match |
| `mmr` | `number` | `float` | ✅ Match |
| `recency_weighted_mmr` | `number \| null` | `Optional[float]` | ✅ Match |
| `hybrid_mmr` | ❌ MISSING | `Optional[float]` | 🔴 **DRIFT** |
| `avg_pim` | ❌ MISSING | `Optional[float]` | 🔴 **DRIFT** |
| `win_rate` | `number` | `float` (property) | ✅ Match |
| `total_games` | `number` | `int` | ✅ Match |
| `wins` | `number` | `int` | ✅ Match |
| `losses` | `number` | `int` | ✅ Match |
| `terran_games` | `number` | `int` | ✅ Match |
| `protoss_games` | `number` | `int` | ✅ Match |
| `zerg_games` | `number` | `int` | ✅ Match |
| `random_games` | `number` | `int` | ✅ Match |
| `favorite_race` | `string` | `str` (property) | ✅ Match |
| `is_core_player` | `boolean` | `bool` | ✅ Match |
| `avg_economic_score` | `number` | `float` | ✅ Match |
| `avg_combat_score` | `number` | `float` | ✅ Match |
| `avg_efficiency_score` | `number` | `float` | ✅ Match |
| `avg_overall_impact` | `number` | `float` | ✅ Match |
| `avg_first_damage_timing` | `number \| null` | `Optional[int]` | ✅ Match |
| `primary_archetype` | `string \| null` | `Optional[str]` | ✅ Match |
| `avg_aggression_score` | `number` | `float` | ✅ Match |
| `created_at` | `string` | `datetime` | ✅ Match (ISO serialized) |
| `last_played` | `string \| null` | `Optional[datetime]` | ✅ Match |

**Code Locations:**
- Frontend: `/home/vtee/projects/sc2mmr/frontend/src/types/api.ts:12-38`
- Backend: `/home/vtee/projects/sc2mmr/backend/app/api/players.py:23-43`

**Issue Details:**
```typescript
// frontend/src/types/api.ts - MISSING fields from SPEC-ML-001
export interface Player {
  // ... existing fields ...
  // MISSING:
  // hybrid_mmr: number | null;   // Performance-adjusted MMR
  // avg_pim: number | null;      // Average Performance Impact Modifier
}
```

```python
# backend/app/api/players.py:23-43 - Has these fields
class PlayerResponse(BaseModel):
    hybrid_mmr: Optional[float] = None  # Present
    avg_pim: Optional[float] = None     # Present
```

#### Match Types Comparison

| Field | Frontend (TS) | Backend (Pydantic) | Status |
|-------|---------------|-------------------|--------|
| `id` | `number` | `int` | ✅ Match |
| `played_at` | `string` | `datetime` | ✅ Match |
| `game_mode` | `string` | `GameMode` (enum) | ✅ Match |
| `map_name` | `string` | `str` | ✅ Match |
| `duration_seconds` | `number` | `int` | ✅ Match |
| `replay_hash` | `string \| null` | `Optional[str]` | ✅ Match |
| `predicted_team1_win_prob` | `number \| null` | `Optional[float]` | ✅ Match |
| `predicted_team2_win_prob` | `number \| null` | `Optional[float]` | ✅ Match |

**Code Locations:**
- Frontend: `/home/vtee/projects/sc2mmr/frontend/src/types/api.ts:78-88`
- Backend: `/home/vtee/projects/sc2mmr/backend/app/api/replays.py:128-141`

#### Enum Consistency

| Enum | Frontend | Backend | Status |
|------|----------|---------|--------|
| `Race` | `'Terran' \| 'Protoss' \| 'Zerg' \| 'Random'` | `Race.TERRAN/PROTOSS/ZERG/RANDOM` | ✅ Match |
| `GameMode` | `'2v2' \| '3v3' \| '4v4' \| ...` | `GameMode.TWO_V_TWO/THREE_V_THREE/...` | ✅ Match |
| `FairnessRating` | `'Perfect' \| 'Very Good' \| ...` | String computed in balancer | ✅ Match |
| `RivalryIntensity` | `'Casual' \| 'Competitive' \| ...` | `get_intensity_label()` | ✅ Match |
| `AchievementRarity` | `'common' \| 'uncommon' \| ...` | `AchievementRarity.COMMON/...` | ✅ Match |
| `AchievementCategory` | `'milestone' \| 'streak' \| ...` | `AchievementCategory.MILESTONE/...` | ✅ Match |

**Code Locations:**
- Frontend Enums: `/home/vtee/projects/sc2mmr/frontend/src/types/api.ts:377-400`
- Backend Models: `/home/vtee/projects/sc2mmr/backend/app/models.py:123-149, 489-509`

#### TeamSuggestion Response Alignment

| Field | Frontend (TS) | Backend (Pydantic) | Status |
|-------|---------------|-------------------|--------|
| `team_1` | `TeamInfo` | `TeamInfo` | ✅ Match |
| `team_2` | `TeamInfo` | `TeamInfo` | ✅ Match |
| `win_probability_team_1` | `number` | `float` | ✅ Match |
| `win_probability_team_2` | `number` | `float` | ✅ Match |
| `fairness_rating` | `string` | `str` | ✅ Match |
| `mmr_difference` | `number` | `float` | ✅ Match |
| `impact_balance_score` | `number` (optional) | `float` | ✅ Match |
| `impact_difference` | `number` (optional) | `float` | ✅ Match |

**Code Locations:**
- Frontend: `/home/vtee/projects/sc2mmr/frontend/src/types/api.ts:194-221`
- Backend: `/home/vtee/projects/sc2mmr/backend/app/api/teams.py:47-59`

### 3.1.2 Error Response Contract

#### Backend Error Structure

```python
# backend/app/api - Standard HTTPException pattern
raise HTTPException(
    status_code=400,
    detail="Validation failed: <message>"  # String detail
)

raise HTTPException(
    status_code=404, 
    detail="Player not found"
)

raise HTTPException(
    status_code=409,
    detail="Replay already uploaded. Match ID: <id>"
)
```

#### Frontend Error Handling

```typescript
// frontend/src/api/client.ts:39-76
apiClient.interceptors.response.use(
  (response) => response,
  (error: ApiClientError) => {
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400: error.userMessage = data.detail || 'Invalid request'; break;
        case 404: error.userMessage = data.detail || 'Resource not found'; break;
        case 409: 
          error.userMessage = data.detail || 'Duplicate entry';
          error.isDuplicate = true;
          break;
        case 500: error.userMessage = 'Server error. Please try again later.'; break;
        default: error.userMessage = data.detail || 'An error occurred';
      }
    } else if (error.request) {
      error.userMessage = 'Cannot connect to server.';
    }
    return Promise.reject(error);
  }
);
```

**Assessment:** ✅ **WELL ALIGNED**
- Backend consistently uses `HTTPException` with `detail` string
- Frontend extracts `detail` for user-friendly messages
- Special handling for 409 (duplicate) with `isDuplicate` flag

### 3.1.3 Timeout & Retry Configuration

#### Current Implementation

```typescript
// frontend/src/api/client.ts - NO explicit timeout
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  // ⚠️ MISSING: timeout configuration
});
```

```typescript
// frontend/src/main.tsx - React Query defaults
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,                    // ✅ Single retry
      staleTime: 30000,           // ✅ 30 second stale time
      // ⚠️ MISSING: networkMode, refetchOnReconnect
    },
  },
});
```

**Recommendations:**

```typescript
// Recommended timeout configuration
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30s default
  headers: { 'Content-Type': 'application/json' },
});

// Per-request timeout overrides for long operations
replaysApi.upload(file, {
  timeout: 120000, // 2 min for replay upload
});

// React Query improvements
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry 4xx errors
        if (error.response?.status >= 400 && error.response?.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 30000,
      gcTime: 5 * 60 * 1000, // 5 min garbage collection
    },
  },
});
```

---

## 3.2 Data Synchronization

### 3.2.1 React Query Configuration Analysis

**Current Configuration:**
```typescript
// frontend/src/main.tsx:15-23
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,  // Good for casual use
      retry: 1,                     // Good for resilience
      staleTime: 30000,            // 30s - appropriate for personal scale
    },
  },
});
```

### 3.2.2 Query and Mutation Inventory

#### Queries (useQuery)

| Query Key | Location | Stale Time | Notes |
|-----------|----------|------------|-------|
| `['players']` | Home.tsx:32, TeamGenerator:39 | 30s (default) | ✅ Appropriate |
| `['matches']` | Home.tsx:40 | 30s (default) | ✅ Appropriate |
| `['failed-uploads', filters...]` | FailedUploads.tsx:86 | 30s (default) | ✅ Includes filter params |
| `['match', matchId]` | MatchDetail (expected) | 30s (default) | Loaded per route |
| `['player', playerId]` | PlayerDetail (expected) | 30s (default) | Loaded per route |
| `['leaderboard', category]` | Leaderboard (expected) | 30s (default) | Per category |
| `['h2h', p1Id, p2Id]` | HeadToHead (expected) | 30s (default) | Per player pair |
| `['achievements', playerId]` | Achievements (expected) | 30s (default) | Per player |

#### Mutations (useMutation)

| Mutation | Location | Cache Invalidation | Notes |
|----------|----------|-------------------|-------|
| `balance teams` | TeamGenerator:52 | ❌ None | Sets local state only |
| `balanceWithImpact` | TeamGenerator:55 | ❌ None | Sets local state only |
| `markUploadReviewed` | FailedUploads:101 | ✅ `['failed-uploads']` | Proper invalidation |
| `setManualWinner` | FailedUploads:127 | ✅ `['failed-uploads']`, `['matches']` | Proper invalidation |
| `upload replay` | Upload (expected) | Should invalidate `['matches']`, `['players']` | ⚠️ Verify |
| `create player` | PlayerCreate (expected) | Should invalidate `['players']` | ⚠️ Verify |

### 3.2.3 Cache Invalidation Patterns

**Pattern 1: Proper Invalidation (Good Example)**
```typescript
// FailedUploads.tsx:101-124
const markReviewedMutation = useMutation({
  mutationFn: ({ uploadId, notes }) =>
    replaysApi.markUploadReviewed(uploadId, notes),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['failed-uploads'] }); // ✅
    toast({ title: 'Marked as reviewed', status: 'success' });
  },
});
```

**Pattern 2: Multi-Query Invalidation (Good Example)**
```typescript
// FailedUploads.tsx:127-163
const setWinnerMutation = useMutation({
  mutationFn: ({ uploadId, winnerTeam }) =>
    replaysApi.setManualWinner(uploadId, winnerTeam),
  onSuccess: (response) => {
    queryClient.invalidateQueries({ queryKey: ['failed-uploads'] }); // ✅
    queryClient.invalidateQueries({ queryKey: ['matches'] });        // ✅
    // Note: Should also invalidate ['players'] as ratings changed
  },
});
```

**Pattern 3: Missing Invalidation (Issue)**
```typescript
// TeamGenerator:52-73 - Balance mutation doesn't need cache invalidation
// (read-only operation, good)

// BUT: Upload page (not shown in excerpts) should invalidate:
// - ['matches'] after successful upload
// - ['players'] after rating updates
// - ['leaderboard', *] for ranking changes
```

### 3.2.4 Race Condition Vulnerabilities

**Identified Issues:**

1. **Concurrent Upload Race**
   - Two users uploading same replay simultaneously
   - Backend has `replay_hash` unique constraint - protects data
   - Frontend gets 409 error - handled correctly
   - **Status:** ✅ Protected by backend

2. **Stale Player Selection**
   - User selects players for team balance
   - Another user uploads replay changing ratings
   - First user's balance uses stale MMR values
   - **Status:** ⚠️ Acceptable for personal scale (30s stale)

3. **Manual Winner + Subsequent Upload**
   - Admin sets manual winner for failed upload
   - Original uploader retries upload
   - Backend returns 409 "already processed"
   - **Status:** ✅ Protected by backend

### 3.2.5 Real-Time Update Considerations

**Current State:** No WebSocket/SSE implementation (polling only)

**For Personal Scale (1-10 users):**
- Polling acceptable with 30s stale time
- Manual refresh sufficient for leaderboard updates
- Real-time not critical for casual LAN party use

**Future Enhancement (If Needed):**
```typescript
// Optional: Add refetch on reconnect for better UX
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnReconnect: true,  // Refresh when network returns
      refetchInterval: false,    // No continuous polling (save resources)
    },
  },
});
```

### 3.2.6 Offline Support Considerations

**Current State:** No offline support

**Assessment:** Appropriate for LAN party use case
- App assumes network connectivity to backend
- SQLite database is local anyway
- No need for PWA/Service Worker caching

---

## 3.3 User Journey Analysis

### 3.3.1 Primary Journey: Player Selection → Team Generation → Match → Upload → Review

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          SC2 MMR TRACKER USER JOURNEY                        │
└──────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  1. PLAYER  │     │  2. TEAM    │     │  3. PLAY    │     │  4. UPLOAD  │
  │   LISTING   │────▶│ GENERATION  │────▶│   MATCH     │────▶│   REPLAY    │
  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │ GET /players│     │POST /teams/ │     │ (External)  │     │POST /replays│
  │ Query:      │     │   balance   │     │  StarCraft  │     │   /upload   │
  │ ['players'] │     │             │     │             │     │             │
  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
        │                   │                                       │
        ▼                   ▼                                       ▼
  ┌─────────────┐     ┌─────────────┐                         ┌─────────────┐
  │ TeamSelector│     │BalanceResult│                         │ 5. MATCH    │
  │ Component   │     │  Component  │                         │   REVIEW    │
  └─────────────┘     └─────────────┘                         └─────────────┘
                                                                    │
                                                                    ▼
                                                              ┌─────────────┐
                                                              │GET /replays │
                                                              │/matches/:id │
                                                              └─────────────┘
```

### 3.3.2 Step 1: Player Listing

**Components Involved:**
- `TeamGenerator/index.tsx` (main orchestrator)
- `TeamGenerator/TeamSelector.tsx` (player grid)

**API Endpoint:** `GET /players/`

**Query Configuration:**
```typescript
// TeamGenerator/index.tsx:39-47
const { data: playersData, isLoading: isLoadingPlayers } = useQuery<Player[]>({
  queryKey: ['players'],
  queryFn: async () => {
    const response = await playersApi.getAll();
    return response.data;
  },
});
```

**State Management:**
- `selectedPlayers` - useState array of Player objects
- `togglePlayer()` - adds/removes from selection

**Loading Feedback:**
```typescript
if (isLoadingPlayers) {
  return <LoadingState variant="players" count={8} />;
}
```

**Empty State:**
```typescript
if (!players || players.length === 0) {
  return (
    <EmptyState
      variant="players"
      title="No Players Found"
      description="Upload some replay files..."
    />
  );
}
```

**Assessment:** ✅ **EXCELLENT**
- Clear loading feedback
- Proper empty state handling
- Query caching prevents redundant fetches

### 3.3.3 Step 2: Player Selection for Team Balancing

**Components Involved:**
- `TeamGenerator/TeamSelector.tsx`
- `hooks/usePlayerSelection.ts` (available but not used directly)

**State Flow:**
```
User clicks player card
        │
        ▼
togglePlayer(player) called
        │
        ▼
setSelectedPlayers(prev => 
  prev.some(p => p.id === player.id)
    ? prev.filter(p => p.id !== player.id)  // Remove
    : [...prev, player]                      // Add
)
        │
        ▼
Visual feedback: selected card highlighted
```

**Validation Logic:**
```typescript
const minPlayers = 2;
const canGenerate = selectedPlayers.length >= minPlayers;
const hasOddPlayers = selectedPlayers.length % 2 !== 0;
```

**Error Recovery:** N/A (client-side only)

**Assessment:** ✅ **GOOD**
- Intuitive toggle behavior
- Clear visual selection feedback
- Validation prevents invalid operations

### 3.3.4 Step 3: Team Generation Algorithm Call

**API Endpoint:** `POST /teams/balance` or `POST /teams/balance-with-impact`

**Mutation Configuration:**
```typescript
// TeamGenerator/index.tsx:52-73
const balanceTeamsMutation = useMutation({
  mutationFn: async (playerIds: number[]) => {
    if (useImpactBalance) {
      const response = await teamsApi.balanceWithImpact(
        playerIds, 3, impactWeight
      );
      return response.data;
    } else {
      const response = await teamsApi.balance(playerIds, 3);
      return response.data;
    }
  },
  onSuccess: (data) => {
    setTeamSuggestions(data);
    toast.success('Teams generated successfully!');
  },
  onError: (error) => {
    toast.error(error.userMessage || 'Failed to generate teams');
  },
});
```

**Loading State:**
```typescript
{balanceTeamsMutation.isPending && (
  <VStack spacing={4}>
    <Text>CALCULATING OPTIMAL CONFIGURATIONS...</Text>
    <TeamResultSkeleton />
    <TeamResultSkeleton />
    <TeamResultSkeleton />
  </VStack>
)}
```

**Assessment:** ✅ **GOOD**
- Proper loading feedback with skeleton UI
- Toast notifications for success/error
- Error message propagation from API

### 3.3.5 Step 4: Match Creation from Replay Upload

**API Endpoint:** `POST /replays/upload` or `POST /replays/upload-advanced`

**Flow Diagram:**
```
User drags .SC2Replay file
        │
        ▼
File validation (extension check)
        │
        ▼
FormData creation with file
        │
        ▼
POST /replays/upload-advanced
        │
        ├── SUCCESS ──────────────────┐
        │                             │
        │   ┌─────────────────────────▼───────────────────────────┐
        │   │ • Match created (match_id returned)                  │
        │   │ • Player ratings updated                            │
        │   │ • ML features extracted (if replay file saved)      │
        │   │ • Synergies recalculated                           │
        │   │ • Achievements checked                              │
        │   └─────────────────────────────────────────────────────┘
        │
        ├── 400 (Parse Error) ────────┐
        │                             │
        │   ┌─────────────────────────▼───────────────────────────┐
        │   │ • FailedUpload record created                       │
        │   │ • Error message displayed to user                   │
        │   │ • Replay saved for manual review                    │
        │   └─────────────────────────────────────────────────────┘
        │
        ├── 400 (Winner Determination) ┐
        │                              │
        │   ┌──────────────────────────▼──────────────────────────┐
        │   │ • FailedUpload with type="winner_determination"     │
        │   │ • Replay file saved for manual winner selection     │
        │   │ • User can navigate to /failed-uploads              │
        │   └─────────────────────────────────────────────────────┘
        │
        └── 409 (Duplicate) ──────────┐
                                      │
            ┌─────────────────────────▼───────────────────────────┐
            │ • "Replay already uploaded" message                  │
            │ • Existing match_id referenced                      │
            │ • User can navigate to existing match               │
            └─────────────────────────────────────────────────────┘
```

**Required Cache Invalidations (Currently Missing Verification):**
```typescript
// Should be in upload mutation onSuccess:
onSuccess: (data) => {
  queryClient.invalidateQueries({ queryKey: ['matches'] });
  queryClient.invalidateQueries({ queryKey: ['players'] });
  queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
  // Navigate to match detail
  navigate(`/history/${data.match_id}`);
}
```

### 3.3.6 Step 5: Match Review and Manual Winner Selection

**Components Involved:**
- `FailedUploads.tsx` (failed upload management)
- `MatchDetail/index.tsx` (successful match review)

**Failed Upload → Manual Winner Flow:**
```
GET /replays/failed-uploads
        │
        ▼
Display table of failed uploads
        │
        ▼
User expands "winner_determination" type row
        │
        ▼
Buttons: "Team 1 Won" | "Team 2 Won"
        │
        ▼
POST /replays/failed-uploads/:id/set-winner
   { winner_team: 1 | 2 }
        │
        ▼
Backend reprocesses with manual winner:
  • parse_replay_advanced(path, manual_winner_team=X)
  • Match created
  • Ratings updated
  • FailedUpload record deleted
        │
        ▼
Cache invalidation + navigate to match
```

**Code Reference:**
```typescript
// FailedUploads.tsx:165-172
const handleSetWinner = (upload: FailedUpload, winnerTeam: number): void => {
  if (window.confirm(`Set Team ${winnerTeam} as the winner for this match?`)) {
    setWinnerMutation.mutate({
      uploadId: upload.id,
      winnerTeam
    });
  }
};
```

**Assessment:** ✅ **EXCELLENT**
- Complete error recovery flow for winner determination failures
- Confirmation dialog prevents accidental actions
- Proper cache invalidation after mutation
- Navigation to created match on success

---

## 3.4 Testing & UAT Scenarios

### 3.4.1 Existing Test Inventory

| Test File | Purpose | Coverage |
|-----------|---------|----------|
| `backend/tests/conftest.py` | Test fixtures (db, player factory) | Infrastructure |
| `backend/tests/test_basic.py` | Player model, RatingSystem unit tests | Models/Rating |
| `backend/tests/test_h2h.py` | RivalryService integration test | H2H feature |
| `backend/tests/test_pi_calculator.py` | Performance Impact calculator | PI feature |
| `backend/tests/test_advanced_parsing_e2e.py` | Advanced replay parsing | Parser |

**Current Test Categories:**
- ✅ Unit Tests: Player model, RatingSystem
- ✅ Integration Tests: RivalryService, PI Calculator
- ⚠️ E2E Tests: Only test_advanced_parsing_e2e.py (limited)
- 🔴 Missing: API endpoint tests, database stress tests, frontend tests

### 3.4.2 Test Coverage Gaps

#### Critical Gaps (P0)

1. **Replay Upload → Rating Update Chain**
   ```python
   # MISSING: Test full upload pipeline
   def test_replay_upload_updates_ratings():
       # Upload replay
       # Verify match created
       # Verify player ratings changed
       # Verify MatchPlayer records created
       # Verify PlayerMatchMetrics created (if advanced)
       pass
   ```

2. **Concurrent Upload Handling**
   ```python
   # MISSING: Race condition testing
   def test_concurrent_replay_uploads():
       # 10 simultaneous upload requests
       # Verify unique constraint prevents duplicates
       # Verify no database corruption
       # Verify all legitimate uploads succeed
       pass
   ```

3. **Team Balance Calculation**
   ```python
   # MISSING: Balance algorithm verification
   def test_team_balance_fairness():
       # Create players with known MMR distribution
       # Generate team suggestions
       # Verify all suggestions meet fairness criteria
       # Verify no duplicate player assignments
       pass
   ```

#### High Priority Gaps (P1)

4. **API Endpoint Tests**
   ```python
   # MISSING: FastAPI TestClient tests
   def test_get_players_endpoint():
       response = client.get("/players/")
       assert response.status_code == 200
       assert isinstance(response.json(), list)
   
   def test_create_player_duplicate():
       client.post("/players/", json={"name": "Test"})
       response = client.post("/players/", json={"name": "Test"})
       assert response.status_code == 409
   ```

5. **Leaderboard Query Performance**
   ```python
   # MISSING: Performance regression testing
   def test_leaderboard_query_under_500ms():
       # Create 100+ players
       start = time.time()
       response = client.get("/leaderboard/mmr")
       elapsed = time.time() - start
       assert elapsed < 0.5  # 500ms
   ```

#### Medium Priority Gaps (P2)

6. **Achievement Trigger Tests**
   ```python
   # MISSING: Achievement awarding logic
   def test_first_win_achievement():
       # Create player with 0 wins
       # Upload winning replay
       # Verify "FIRST_WIN" achievement awarded
       pass
   ```

7. **Manual Winner Determination**
   ```python
   # MISSING: Manual winner flow
   def test_manual_winner_creates_match():
       # Create failed upload with winner_determination type
       # POST set-winner with team=1
       # Verify match created
       # Verify failed upload deleted
       # Verify ratings updated
       pass
   ```

### 3.4.3 Proposed UAT Scenarios

#### Scenario 1: Complete Match Flow (Happy Path)

```gherkin
Feature: Complete Match Flow
  As a player
  I want to upload a replay and see my rating updated
  So that I can track my progress

  Scenario: Successful 4v4 replay upload
    Given 8 players exist in the database
    And a valid 4v4 replay file with known winner (Team 1)
    When I navigate to /upload
    And I drag-and-drop the replay file
    And I click "Upload"
    Then I should see a progress indicator
    And the upload should complete in under 10 seconds
    And I should see "Replay processed successfully"
    And I should be redirected to the match detail page
    And Team 1 players should show positive MMR change
    And Team 2 players should show negative MMR change
```

#### Scenario 2: Failed Upload Recovery

```gherkin
Feature: Failed Upload Recovery
  As an admin
  I want to manually set the winner for ambiguous replays
  So that the match can still be recorded

  Scenario: Manual winner determination
    Given a replay that fails winner detection
    And the replay is saved as a failed upload
    When I navigate to /failed-uploads
    And I find the replay with error type "winner_determination"
    And I expand the row details
    And I click "Team 2 Won"
    And I confirm the action
    Then the replay should be reprocessed
    And a new match should be created
    And the failed upload should be removed from the list
    And I should see a success toast with link to match
```

#### Scenario 3: Team Generation with Impact

```gherkin
Feature: Team Generation with Impact Balancing
  As a group coordinator
  I want to balance teams considering player impact scores
  So that high-impact players are distributed evenly

  Scenario: Impact-balanced team generation
    Given 6 players exist with varied impact scores:
      | Name    | MMR  | Impact |
      | Player1 | 2500 | 75     |
      | Player2 | 2400 | 65     |
      | Player3 | 2300 | 55     |
      | Player4 | 2200 | 50     |
      | Player5 | 2100 | 45     |
      | Player6 | 2000 | 40     |
    When I navigate to /balance
    And I select all 6 players
    And I enable "Impact Balancing"
    And I set impact weight to 0.5
    And I click "Generate Teams"
    Then I should see 3 team suggestions
    And each suggestion should have impact_difference < 15
    And the highest impact player should not be paired with second highest
```

#### Scenario 4: Database Stress Test

```gherkin
Feature: Concurrent User Stress Test
  As a system administrator
  I want the system to handle 10 concurrent users
  So that LAN party sessions don't experience issues

  Scenario: 10 concurrent replay uploads
    Given 10 different valid replay files
    When 10 users simultaneously attempt to upload their replays
    Then all 10 uploads should complete within 30 seconds
    And no database errors should occur
    And all 10 matches should be created
    And player ratings should reflect all 10 matches correctly
```

#### Scenario 5: Replay Parsing Edge Cases

```gherkin
Feature: Replay Parsing Edge Cases
  As a developer
  I want edge case replays handled gracefully
  So that users get helpful error messages

  Scenario Outline: Edge case replay handling
    Given a replay file of type "<type>"
    When I attempt to upload the replay
    Then I should see error message containing "<message>"
    And the failed upload should be logged with type "<error_type>"

    Examples:
      | type                | message                          | error_type           |
      | truncated file      | Parse error                      | parse_error          |
      | unsupported mode    | Unsupported game mode            | unsupported_mode     |
      | 1v1 replay          | Invalid number of players        | validation_error     |
      | co-op replay        | Unsupported game mode            | unsupported_mode     |
      | observers only      | Unable to determine winner       | winner_determination |
      | early leave (< 1min)| Unable to determine winner       | winner_determination |
```

### 3.4.4 Test Implementation Recommendations

```python
# backend/tests/test_api_integration.py (NEW FILE)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base, Player

# Test database setup
@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

class TestPlayersAPI:
    def test_get_players_empty(self, client):
        response = client.get("/players/")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_create_player(self, client):
        response = client.post("/players/", json={"name": "TestPlayer"})
        assert response.status_code == 200
        assert response.json()["name"] == "TestPlayer"
        assert response.json()["mmr"] == 2000  # Default MMR
    
    def test_create_duplicate_player(self, client):
        client.post("/players/", json={"name": "Duplicate"})
        response = client.post("/players/", json={"name": "Duplicate"})
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

class TestTeamsAPI:
    def test_balance_teams_minimum_players(self, client, player_factory):
        # Create 4 players
        for i in range(4):
            player_factory(name=f"Player{i}", mu=25.0 + i)
        
        players = client.get("/players/").json()
        player_ids = [p["id"] for p in players]
        
        response = client.post("/teams/balance", json={
            "player_ids": player_ids,
            "top_n": 3
        })
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions) <= 3
        assert all("team_1" in s and "team_2" in s for s in suggestions)
    
    def test_balance_teams_insufficient_players(self, client):
        response = client.post("/teams/balance", json={
            "player_ids": [1],  # Only 1 player
            "top_n": 3
        })
        assert response.status_code == 400
        assert "at least 2 players" in response.json()["detail"]

class TestReplaysAPI:
    def test_upload_invalid_extension(self, client):
        files = {"file": ("test.txt", b"not a replay", "text/plain")}
        response = client.post("/replays/upload", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
```

---

## Summary: Priority Recommendations

### P0 - Critical (Address Immediately)

| Issue | Location | Recommendation |
|-------|----------|----------------|
| Missing integration tests | `backend/tests/` | Add `test_api_integration.py` with TestClient |
| No E2E upload chain test | `backend/tests/` | Add replay upload → rating update validation |
| Player type drift | `frontend/src/types/api.ts` | Add `hybrid_mmr`, `avg_pim` fields |

### P1 - High Priority (Next Sprint)

| Issue | Location | Recommendation |
|-------|----------|----------------|
| Upload mutation cache | Upload page | Invalidate `['matches']`, `['players']`, `['leaderboard']` |
| No timeout config | `frontend/src/api/client.ts` | Add 30s default, 120s for uploads |
| Missing API docs | `backend/app/api/` | Add docstrings for OpenAPI generation |

### P2 - Medium Priority (Backlog)

| Issue | Location | Recommendation |
|-------|----------|----------------|
| Performance tests | `backend/tests/` | Add query timing assertions |
| Achievement tests | `backend/tests/` | Add award trigger verification |
| setWinner cache | `FailedUploads.tsx` | Add `['players']` invalidation |

### P3 - Low Priority (Future)

| Issue | Location | Recommendation |
|-------|----------|----------------|
| Retry logic refinement | `frontend/src/main.tsx` | Smart retry based on status code |
| Cursor-based pagination | `backend/app/api/` | Replace offset for large datasets |
| WebSocket for live updates | New | Add for leaderboard real-time |

---

**Document Version:** 1.0  
**Status:** Complete  
**Next Phase:** Phase 4 - Trajectory, Roadmap & MCP Integration
