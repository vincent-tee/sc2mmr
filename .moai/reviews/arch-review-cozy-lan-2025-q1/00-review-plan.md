# Architectural Review: SC2 MMR Tracker - Cozy LAN Party Edition
## Systematic Review Plan with Database Testing & Cozy UI Trajectory

**Review Date:** December 26, 2025
**Review Type:** Comprehensive (Thorough - 60K tokens/phase)
**Trajectory:** Tactical Military → Cozy LAN Party / Homey Gaming Environment
**Scale:** Personal / Small Group (1-10 concurrent users)
**Timeframe:** Long-term (3-6 months for major changes)

---

## Executive Summary

This systematic architectural review addresses:

1. **Database Robustness & Extensibility** - Comprehensive UAT/testing
2. **Replay Parsing Reliability** - Full parsing validation & error handling
3. **Architectural Gaps** - Backend/Frontend structural improvements
4. **UI Trajectory Shift** - Military tactical → Cozy LAN party aesthetic
5. **MCP Server Integration** - Screenshot/UI review capabilities
6. **Testing Strategy** - Database stress tests, parsing edge cases, UAT scenarios

---

## Review Structure (4 Phases)

### Phase 1: Backend Architecture Review
**Focus:** Data layer, service layer, API design, robustness testing
**Token Budget:** ~60K tokens
**Deliverable:** `01-backend-review.md`

#### 1.1 Database Robustness Testing
- Schema extensibility analysis
- Migration strategy validation
- Connection pooling requirements (personal group scale)
- Query performance audit
- Data integrity constraints

#### 1.2 Service Layer Completion
- SPEC-REFACTOR-001 progress review
- Business logic extraction completeness
- Service interface standardization
- Error handling patterns

#### 1.3 API Design Validation
- Pydantic model coverage
- Request/response consistency
- Error contract alignment
- Documentation completeness

#### 1.4 Replay Parsing Robustness
- sc2reader integration patterns
- Error handling edge cases
- Corrupt file detection
- Winner determination reliability
- Parser test coverage (existing + gaps)

#### 1.5 ML Integration Review
- AI MMR service architecture
- Build order classifier integration
- Prediction accuracy tracking
- Online learning pipeline

---

### Phase 2: Frontend Architecture Review
**Focus:** Component architecture, state management, UX, styling trajectory
**Token Budget:** ~60K tokens
**Deliverable:** `02-frontend-review.md`

#### 2.1 Component Architecture
- TypeScript type safety audit
- Component reusability patterns
- Props interface design
- Error boundary strategy
- Co-location effectiveness

#### 2.2 State Management
- React Query cache strategy
- Data synchronization patterns
- Loading state handling
- Error recovery flows
- Optimistic updates

#### 2.3 Performance
- Bundle size analysis
- Render optimization
- Image lazy loading
- Code splitting
- Memoization opportunities

#### 2.4 Styling & Theme System
- **Tactical → Cozy Transformation:**
  - Replace angular shapes with rounded corners
  - Swap sci-fi fonts (Rajdhani/Orbitron) for friendly sans-serif (Poppins/Inter)
  - Change military terminology to casual gaming language
  - Replace neon glow with warm pastels
  - Remove scanlines, add gentle transitions
  - Corner brackets → Soft borders/gradients

- Design tokens migration plan
- Component styling consistency
- Responsive design review
- Accessibility audit

#### 2.5 UX & User Journey
- Team balance flow optimization
- Replay upload feedback
- Error messaging clarity
- Empty states & loading states
- Micro-interactions

---

### Phase 3: Integration & Data Flow Review
**Focus:** API-Frontend contract, state sync, user journeys
**Token Budget:** ~60K tokens
**Deliverable:** `03-integration-review.md`

#### 3.1 API Contract Validation
- TypeScript ↔ Pydantic alignment
- Type safety across boundary
- Error propagation patterns
- Timeout handling
- Retry logic

#### 3.2 Data Synchronization
- React Query cache invalidation
- Real-time update needs
- Race condition prevention
- Offline support consideration

#### 3.3 User Journey Analysis
- **Primary Journey:** Player selection → Team generation → Match → Upload → Review
- Error recovery flows
- Loading feedback
- Success confirmation

#### 3.4 Testing & UAT Scenarios
- End-to-end user workflows
- Database stress tests (10 concurrent users)
- Replay parsing edge cases (corrupt, unsupported, duplicate)
- Network failure simulation

---

### Phase 4: Trajectory, Roadmap & MCP Integration
**Focus:** Cozy UI roadmap, MCP servers, implementation priorities
**Token Budget:** ~70K tokens
**Deliverables:**
- `04-cozy-ui-roadmap.md`
- `05-priority-matrix.md`
- `06-mcp-integration-guide.md`

#### 4.1 Cozy LAN Party Aesthetic Roadmap

**Visual Language Shift:**

| Current (Tactical) | Cozy LAN Party (Target) |
|---------------------|------------------------|
| Angular/clipped shapes | Rounded corners, soft curves |
| Rajdhani/Orbitron fonts | Poppins/Inter (friendly) |
| UPPERCASE military text | Title case, casual language |
| Warm orange/gold glow | Pastel gradients (cozy) |
| Scanline animations | Gentle pulse/breathing |
| Corner brackets | Soft borders, card shadows |
| Dark military backgrounds | Warm beige/cream/soft gray |
| Blue/red/gold race colors | Softer palette variants |
| "COMMAND CENTER" | "Game Hub" / "Lounge" |
| "OPERATIVES" | "Players" / "Friends" |
| "MISSIONS" | "Matches" / "Games" |

**Color Palette Evolution:**

```typescript
// Current Tactical Palette
brand: { 500: '#FF8C1A' },  // Warm orange
accent: { 500: '#EF4444' },   // Deep red
space: { 900: '#2A241F' },   // Dark brown

// Cozy LAN Party Palette
brand: { 500: '#FFB347' },  // Pastel orange
accent: { 500: '#FFA07A' },  // Light salmon
space: { 50: '#FDF6F0',      // Warm cream
       900: '#D4C5A9' },    // Warm lavender-gray

// Softer Race Colors
terran:  { 500: '#64B5F6' },  // Soft blue
protoss: { 500: '#FFE082' },  // Light gold
zerg:    { 500: '#CE93D8' },  // Soft purple
```

**Component Redesign Priorities:**
1. Navigation → "Game Lounge" (warm, inviting)
2. PlayerCard → Rounder avatars, friendly badges
3. TacticalCard → Soft "Game Card" with subtle gradients
4. RankBadge → "Skill Badge" with softer edges
5. LoadingState → Gentle spinner with cozy animation

**Typography Shift:**
```css
/* Current */
font-family: 'Rajdhani', 'Orbitron', sans-serif;
text-transform: uppercase;

/* Cozy LAN Party */
font-family: 'Poppins', 'Inter', sans-serif;
text-transform: none; /* Title case for headings */
```

**Language Shift:**
- "Command Center" → "Game Hub"
- "Operatives" → "Players"
- "Missions" → "Matches"
- "System Status" → "Game Status"
- "Tactical Analysis" → "Game Insights"

#### 4.2 MCP Server Integration

**Recommended MCP Servers for UI Review:**

1. **Frontend Review MCP** (@zueai/frontend-review-mcp)
   - Compare before/after screenshots
   - Validate UI changes against requirements
   - Automated visual regression testing

2. **Screenshot MCP Server** (@m-mcp/screenshot-server)
   - Capture desktop screenshots on demand
   - Review UI in real-time during development
   - Integration with development workflow

3. **Playwright MCP** (already configured)
   - Automated browser screenshots
   - Cross-browser UI testing
   - End-to-end visual validation

**Setup Guide:**
```bash
# Update .mcp.json with screenshot server
{
  "mcpServers": {
    "screenshot-review": {
      "command": "npx",
      "args": ["-y", "@zueai/frontend-review-mcp@latest"]
    },
    "browser-screenshot": {
      "command": "npx",
      "args": ["-y", "@m-mcp/screenshot-server@latest"]
    }
  }
}
```

**Workflow:**
1. Make UI changes locally
2. Use MCP server to capture screenshot
3. Request visual feedback from AI
4. Validate against cozy UI requirements
5. Iterate until approved

#### 4.3 Priority Matrix

| Priority | Impact | Effort | Item | Phase |
|----------|---------|---------|-------|--------|
| **P0 - Critical** | | | | |
| Database robustness tests | High | Medium | Schema validation, migration rollback tests | Phase 1 |
| Replay parsing edge cases | High | Medium | Corrupt files, unsupported modes | Phase 1 |
| API error contract | High | Low | Standardize error responses | Phase 1 |
| **P1 - High** | | | | |
| Service layer completion | High | High | Extract remaining business logic | Phase 1 |
| Cozy UI color tokens | High | Low | Update design tokens | Phase 2 |
| Font migration | Medium | Medium | Replace sci-fi fonts | Phase 2 |
| MCP screenshot integration | High | Medium | Configure UI review tools | Phase 4 |
| **P2 - Medium** | | | | |
| Component roundness | Medium | Medium | Rounded corners, soft borders | Phase 2 |
| Language shift | Medium | Low | Casual terminology | Phase 2 |
| Animation gentle-ization | Low | Medium | Remove scanlines, add pulse | Phase 2 |
| **P3 - Low** | | | | |
| Cozy illustrations | Low | High | Custom artwork | Phase 4 |
| Ambient sounds | Low | High | Audio enhancements | Phase 4 |
| Mobile responsiveness | Medium | High | Tablet/phone support | Phase 4 |

---

## Testing & UAT Strategy

### Database Testing

**Unit Tests:**
```python
# Test database models
def test_player_model_constraints():
    # Unique name constraint
    # MMR bounds (0-5000)
    # Valid race values
    pass

def test_match_cascade_deletion():
    # Delete match → MatchPlayers deleted
    # Player ratings preserved (with history)
    pass
```

**Integration Tests:**
```python
def test_concurrent_replay_upload():
    # Simulate 10 users uploading simultaneously
    # Verify no data corruption
    # Verify performance < 2s per upload
    pass

def test_migration_rollback():
    # Apply migration → Verify schema
    # Rollback → Verify original schema
    # Re-apply → Verify idempotency
    pass
```

**Performance Tests:**
```python
def test_query_performance():
    # Leaderboard query < 500ms (100 players)
    # Player detail < 100ms
    # Team generation < 3s (10 players)
    pass
```

### Replay Parsing UAT

**Test Scenarios:**
1. **Valid Replays:**
   - Standard 1v1, 2v2, 3v3, 4v4
   - Different map sizes
   - All race combinations
   - Various game lengths (5min - 60min)

2. **Edge Cases:**
   - Corrupt replay file (truncated)
   - Unsupported game modes (Archon mode, Co-op)
   - Observers/AFK players
   - Early game leaves
   - Rematch scenarios

3. **Error Recovery:**
   - Duplicate upload detection
   - Parser failure → FailedUpload logging
   - Replay file path preservation
   - Manual winner determination fallback

**Validation:**
```python
def test_winner_determination_accuracy():
    # Upload 100 replays with known winners
    # Verify > 95% accuracy
    # Log false positives/negatives
    pass
```

### End-to-End User Tests

**Scenario 1: Team Balance Flow**
```
1. Login as player
2. Navigate to /balance
3. Select 8 players from roster
4. Click "Generate Teams"
5. Verify loading state < 3s
6. Verify team suggestions displayed
7. Verify fairness rating calculated
8. Select team suggestion
9. Verify visual feedback
```

**Scenario 2: Replay Upload Flow**
```
1. Navigate to /upload
2. Drag-and-drop replay file
3. Verify file validation (.SC2Replay)
4. Click upload
5. Verify progress indicator
6. Verify success message
7. Verify match created
8. Verify player ratings updated
9. Navigate to /history
10. Verify match appears
```

**Scenario 3: Database Stress Test**
```
1. Create 20 concurrent upload requests
2. Verify all succeed
3. Verify no database locks
4. Verify response time < 2s each
5. Verify data integrity (no duplicates)
```

---

## Extensibility Assessment

### Database Schema Extensibility

**Current Strengths:**
- ✅ SQL-based migrations (flexible)
- ✅ Additive schema evolution (no destructive changes)
- ✅ Feature flags in config (gradual rollout)
- ✅ Separate ML features table (isolates experimental fields)

**Extensibility Improvements:**
- ⚠️ Add JSON columns for flexible metadata (Player.extra_data, Match.extra_data)
- ⚠️ Consider PostgreSQL for production (JSONB support, better indexing)
- ⚠️ Implement soft delete (deleted_at timestamp)
- ⚠️ Add audit logging (created_at, updated_at tracking)

### API Extensibility

**Current Strengths:**
- ✅ FastAPI auto-generates OpenAPI docs
- ✅ Pydantic models enable easy schema evolution
- ✅ Modular router structure

**Extensibility Improvements:**
- ⚠️ Add API versioning (/api/v1/, /api/v2/)
- ⚠️ Implement pagination with cursor-based (for large datasets)
- ⚠️ Add filtering/sorting options to list endpoints
- ⚠️ Implement rate limiting (for production scale)

---

## Current Challenges (Identified)

### Backend
1. **Incomplete Service Layer** - Some business logic remains in API routes
2. **No Async/Await** - Blocking operations limit concurrency
3. **SQLite Production Concerns** - Single connection, no connection pooling
4. **Migration Tooling** - Manual SQL files instead of Alembic
5. **Caching** - No Redis/in-memory cache for leaderboards

### Frontend
1. **Tactical Aesthetic** - Not aligned with "cozy LAN party" goal
2. **Per-Route ErrorBoundaries** - Over-engineering (app-level sufficient)
3. **Utility Organization** - Multiple files scattered across directories
4. **No Bundle Analysis** - Can't identify optimization opportunities
5. **Accessibility** - Missing ARIA labels, keyboard navigation

### Integration
1. **Type Drift** - TypeScript ↔ Pydantic alignment needs validation
2. **No Real-Time Updates** - Leaderboards require manual refresh
3. **Error Propagation** - API errors not always user-friendly

---

## Success Metrics (Post-Review)

### Database Robustness
- ✅ 99% replay parsing success rate
- ✅ < 2s query response for all endpoints
- ✅ Zero data corruption in stress tests (10 concurrent users)
- ✅ Migration rollback success in < 30s

### Replay Parsing
- ✅ 95%+ winner determination accuracy
- ✅ All edge cases handled with user-friendly errors
- ✅ Corrupt file detection before parsing

### UI/UX
- ✅ Cozy aesthetic validated by 5+ users
- ✅ Navigation flow completion time < 10s
- ✅ User satisfaction survey > 4.5/5.0

### Extensibility
- ✅ New feature schema changes < 1 day implementation
- ✅ API version v1 → v2 migration < 2 weeks
- ✅ Database migration success rate 100%

---

## Next Steps

1. **Phase 1 Execution** (Backend Review + Database Testing)
2. **Phase 2 Execution** (Frontend Review + Cozy UI Planning)
3. **Phase 3 Execution** (Integration Review + UAT Scenarios)
4. **Phase 4 Execution** (Trajectory Roadmap + MCP Integration)
5. **Implementation** (Based on priority matrix)
6. **Validation** (User testing, performance monitoring)

---

**Document Version:** 1.0
**Status:** Planning Complete
**Next:** Execute Phase 1 (Backend Architecture Review)
