# Architectural Review Branch - Cozy LAN Party 2025 Q1

## Branch Purpose

Comprehensive systematic architectural review of SC2 MMR Tracker focusing on:

1. **Database Robustness & Extensibility** - UAT and stress testing
2. **Replay Parsing Reliability** - Full validation & error handling
3. **Architectural Improvements** - Backend/Frontend structural gaps
4. **Cozy UI Trajectory** - Shift from military tactical to LAN party aesthetic
5. **MCP Integration** - Screenshot/UI review capabilities
6. **Testing Strategy** - Comprehensive test coverage

## Review Commit

Base commit: `0481c3a` - "feat: TypeScript migration + service layer refactoring + ML features"

This commit represents significant progress:
- Frontend: Complete JSX → TSX migration
- Backend: Service layer extraction (SPEC-REFACTOR-001)
- Backend: New features (Achievements, H2H, Leaderboard)
- Backend: ML architecture (AI MMR, build orders, predictions)
- Tests: Advanced parsing, H2H, PI calculator

## Review Phases

| Phase | Focus | Token Budget | Status |
|--------|---------|---------------|----------|
| 1 | Backend Architecture (DB, API, Parsing) | 60K | Pending |
| 2 | Frontend Architecture (Components, UX, Styling) | 60K | Pending |
| 3 | Integration (API contract, Data flow, UAT) | 60K | Pending |
| 4 | Trajectory (Cozy UI, MCP, Roadmap) | 70K | Pending |

**Total:** ~250K tokens (within budget)

## Deliverables

### Core Review Documents
- `00-review-plan.md` - Comprehensive review plan (✅ Created)
- `01-backend-review.md` - Backend architecture analysis
- `02-frontend-review.md` - Frontend architecture analysis
- `03-integration-review.md` - Integration & data flow review
- `04-cozy-ui-roadmap.md` - UI aesthetic transformation guide
- `05-priority-matrix.md` - Ranked implementation priorities
- `06-mcp-integration-guide.md` - MCP server setup & workflow

### Testing Artifacts
- `07-database-tests.md` - Database robustness test suite
- `08-parsing-tests.md` - Replay parsing edge cases
- `09-uat-scenarios.md` - End-to-end user workflows

## Cozy UI Transformation

**Goal:** Shift from "Cold Military Tactical" to "Warm LAN Party Gathering"

### Key Changes

1. **Typography**
   - Remove: Rajdhani, Orbitron (sci-fi military)
   - Add: Poppins, Inter (friendly, approachable)

2. **Color Palette**
   - Warm pastels instead of neon glow
   - Cream/beige backgrounds instead of dark military
   - Softer race color variants

3. **Shapes**
   - Rounded corners (12-16px radius)
   - Remove angular/clipped corners
   - Soft shadows, no harsh borders

4. **Animations**
   - Remove scanline effects
   - Add gentle pulse/breathing
   - Smooth transitions (300-500ms)

5. **Language**
   - "Command Center" → "Game Hub"
   - "Operatives" → "Players" / "Friends"
   - "Missions" → "Matches"
   - Title case instead of UPPERCASE

## Scale Considerations

**Personal / Small Group (1-10 concurrent users):**

- ✅ SQLite adequate for current scale
- ⚠️ Consider PostgreSQL if >10 concurrent users
- ✅ Single-threaded async sufficient
- ⚠️ Add caching for leaderboards if >5 seconds load time
- ✅ No authentication needed (trusted environment)

## MCP Integration

### Planned MCP Servers

1. **Frontend Review MCP** (@zueai/frontend-review-mcp)
   - Visual comparison of UI changes
   - Validate against cozy UI requirements

2. **Screenshot MCP Server** (@m-mcp/screenshot-server)
   - Capture desktop screenshots
   - Real-time UI review during development

3. **Playwright MCP** (already configured)
   - Automated browser screenshots
   - Cross-browser visual testing

### Workflow

```bash
# 1. Make UI change
vim frontend/src/components/PlayerCard.tsx

# 2. Capture screenshot via MCP
# Use screenshot MCP to capture current state

# 3. Request visual feedback
# AI compares before/against cozy UI requirements

# 4. Iterate
# Apply feedback until approved
```

## Known Issues (Pre-Review)

### TypeScript Errors
Multiple SQLAlchemy type annotation issues in:
- `backend/app/exceptions.py`
- `backend/app/api/replays.py`
- `backend/app/api/players.py`
- `backend/app/services/rating_service.py`
- `backend/app/services/replay_service.py`

**Root Cause:** mypy confusion between `Column[T]` type and actual values

**Impact:** Static type checking fails, but runtime works fine

**Status:** Will be addressed in Phase 1 backend review

### Service Layer Incomplete
- API routes still contain some business logic
- SPEC-REFACTOR-001 in progress (~60% complete)

**Impact:** Mixed concerns in API layer

**Status:** Will be tracked in Phase 1 backend review

## Success Criteria

Post-review, the application should:

### Database Robustness
- ✅ 99% replay parsing success rate
- ✅ <2s query response for all endpoints
- ✅ Zero data corruption in stress tests (10 concurrent users)
- ✅ Migration rollback success in <30s

### Replay Parsing
- ✅ 95%+ winner determination accuracy
- ✅ All edge cases handled with user-friendly errors
- ✅ Corrupt file detection before parsing

### Cozy UI
- ✅ Validated by 5+ users as "warm and inviting"
- ✅ No military terminology
- ✅ Rounded corners throughout
- ✅ Gentle animations only

### Extensibility
- ✅ New feature schema changes <1 day implementation
- ✅ API v1 → v2 migration <2 weeks
- ✅ Database migration success rate 100%

## Next Steps

1. Execute `/clear` to reset context
2. Run Phase 1: Backend Architecture Review
3. Create `01-backend-review.md` with findings
4. Execute `/clear` between each phase
5. Complete all 4 phases
6. Create prioritized implementation roadmap
7. Merge to `main` if approved

## Notes

- **Timeframe:** Long-term (3-6 months for major changes)
- **Budget:** 250K tokens across all phases
- **Review Type:** Thorough (deep code analysis, not surface-level)
- **Token Efficiency:** Execute `/clear` between phases

---

**Branch:** `arch-review-cozy-lan-2025-q1`
**Created:** December 26, 2025
**Base Commit:** 0481c3a
**Status:** Review Planning Complete
