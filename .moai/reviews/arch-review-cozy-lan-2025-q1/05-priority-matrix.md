# Phase 4.2: Consolidated Priority Matrix

## SC2 MMR Tracker - All Phases Combined

**Review Date:** December 26, 2025  
**Reviewer:** Mr.Alfred (MoAI-ADK)  
**Status:** Complete

---

## Executive Summary

This document consolidates all priority items from Phases 1-4 into a single actionable matrix, organized by priority level and estimated effort.

### Priority Level Definitions

| Priority | Definition | Timeline |
|----------|------------|----------|
| **P0 - Critical** | Blocks core functionality or creates significant risk | This week |
| **P1 - High** | Important for quality/UX, should be addressed soon | Next 2 weeks |
| **P2 - Medium** | Improvements that add value | Next month |
| **P3 - Low** | Nice-to-have enhancements | Backlog |

---

## P0 - Critical Items

### Backend (Phase 1)

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Add integration tests for replay upload chain | `backend/tests/` | 4h | Prevents regression in core flow |
| Fix SQLAlchemy type annotations | `backend/app/models.py`, `api/*.py` | 2h | Type safety, IDE support |
| Add database migration rollback tests | `backend/migrations/` | 2h | Safe schema evolution |

### Frontend (Phase 2)

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Fix 4 `any` type usages | `FailedUploads.tsx`, `WinProbabilityDisplay.tsx` | 30m | Type safety |
| Add keyboard support to interactive cards | `PlayerCard.tsx`, `TacticalCard.tsx`, `MatchHistory.tsx` | 2h | Accessibility |
| Add semantic landmarks (`<main>`, `<nav>`) | `App.tsx`, `Navigation.tsx` | 15m | Accessibility |

### Integration (Phase 3)

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Add `hybrid_mmr`, `avg_pim` to Player type | `frontend/src/types/api.ts` | 15m | Type alignment |
| Add E2E test for upload → rating update | `backend/tests/` | 3h | Critical path validation |

---

## P1 - High Priority Items

### Backend

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Complete service layer extraction | `backend/app/services/` | 8h | Code organization |
| Add API endpoint tests with TestClient | `backend/tests/test_api_integration.py` | 4h | API contract validation |
| Standardize error response contract | `backend/app/api/*.py` | 2h | Consistent error handling |
| Add replay parsing edge case tests | `backend/tests/` | 3h | Parser robustness |

### Frontend

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Add `React.memo` to list components | `PlayerCard.tsx`, `MatchCard` | 1h | Performance |
| Implement route-based code splitting | `App.tsx` | 2h | Bundle size |
| Add axios timeout configuration | `frontend/src/api/client.ts` | 30m | Reliability |

### Cozy UI Transformation

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Update fonts (Poppins/Inter) | `theme/index.ts`, `index.html` | 1h | Visual identity |
| Update color tokens to cozy palette | `theme/tokens.ts` | 2h | Visual identity |
| Transform TacticalCard → Card | `components/TacticalCard.tsx` | 2h | Component library |

### Integration

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Add cache invalidation to upload mutation | Upload page | 1h | Data freshness |
| Add `['players']` invalidation to setWinner | `FailedUploads.tsx` | 15m | Data consistency |

---

## P2 - Medium Priority Items

### Backend

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Add query performance tests | `backend/tests/` | 2h | Performance monitoring |
| Add achievement trigger tests | `backend/tests/` | 2h | Feature coverage |
| Consider async/await for I/O operations | `backend/app/` | 8h | Concurrency |
| Add soft delete (deleted_at) | `backend/app/models.py` | 2h | Data recovery |

### Frontend

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Lazy load recharts/html2canvas | Import statements | 1h | Initial load time |
| Add form labels (visually hidden) | `Players.tsx` | 5m | Accessibility |
| Add `aria-live` to LoadingState | `LoadingState.tsx` | 5m | Screen reader support |

### Cozy UI Transformation

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Update Navigation styling | `Navigation.tsx` | 2h | Visual consistency |
| Transform HexagonalStat → StatCard | `HexagonalStat.tsx` | 2h | Component library |
| Replace terminology (military → casual) | Multiple pages | 2h | Language shift |
| Remove/soften TacticalBackground | `TacticalBackground.tsx` | 1h | Visual cleanup |
| Update animation presets | `theme/animations.ts` | 2h | Gentle interactions |

### Integration

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Add smart retry logic (skip 4xx) | `frontend/src/main.tsx` | 30m | Better error handling |
| Add optimistic updates for mark reviewed | `FailedUploads.tsx` | 1h | UX responsiveness |

---

## P3 - Low Priority Items

### Backend

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Consider PostgreSQL for production | Infrastructure | 16h | Scalability |
| Add API versioning (/api/v1/) | `backend/app/main.py` | 4h | Future-proofing |
| Implement cursor-based pagination | `backend/app/api/*.py` | 4h | Large dataset support |
| Add rate limiting | `backend/app/main.py` | 2h | Protection |
| Add Redis caching for leaderboards | Infrastructure | 8h | Performance |

### Frontend

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Add keyboard shortcuts | Global | 4h | Power users |
| Add skip-to-content link | `App.tsx` | 10m | Accessibility |
| Mobile touch target fixes | Various | 2h | Mobile UX |

### Cozy UI Transformation

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| Update all page headings | `Home.tsx`, `TeamGenerator/*`, etc. | 2h | Visual polish |
| Remove uppercase text transforms | Global search/replace | 1h | Typography |
| Add celebration animations | `TeamGenerator/` | 2h | Delight |
| Update PlayerCard design | `PlayerCard.tsx` | 2h | Visual polish |
| Update empty/loading states | `EmptyState.tsx`, `LoadingState.tsx` | 1h | Friendly messaging |

### Integration

| Item | Location | Effort | Impact |
|------|----------|--------|--------|
| WebSocket for live leaderboard updates | New feature | 16h | Real-time |
| Offline support (PWA) | Infrastructure | 8h | Resilience |

---

## Implementation Roadmap

### Sprint 1: Critical Fixes (Week 1)

**Goal:** Address all P0 items

| Day | Focus | Items |
|-----|-------|-------|
| Mon | Backend Tests | Integration tests, type annotations |
| Tue | Frontend Types | Fix `any` usages, add Player type fields |
| Wed | Accessibility | Keyboard support, semantic landmarks |
| Thu | E2E Testing | Upload → rating update test |
| Fri | Review & Buffer | Address any blockers |

**Deliverables:**
- [ ] All P0 items complete
- [ ] CI/CD passes with new tests
- [ ] Type checker clean (no errors)

### Sprint 2: High Priority (Week 2-3)

**Goal:** Complete P1 items, begin Cozy UI foundation

| Week | Focus | Items |
|------|-------|-------|
| Week 2 | Backend Quality | Service layer, API tests, error contracts |
| Week 3 | Frontend + Cozy Start | Performance, fonts, colors |

**Deliverables:**
- [ ] All P1 items complete
- [ ] Cozy theme foundation in place
- [ ] Performance baseline established

### Sprint 3: Cozy UI Core (Week 4-5)

**Goal:** Complete core Cozy transformation

| Week | Focus | Items |
|------|-------|-------|
| Week 4 | Components | Card, Navigation, PlayerCard |
| Week 5 | Pages | Home, TeamGenerator, terminology |

**Deliverables:**
- [ ] Core components transformed
- [ ] Main pages updated
- [ ] Visual review with MCP tools

### Sprint 4: Polish (Week 6)

**Goal:** Complete P2 items, final polish

| Day | Focus | Items |
|-----|-------|-------|
| Mon-Tue | Remaining Components | StatCard, badges, loading states |
| Wed-Thu | Animations & Interactions | Gentle transitions, micro-interactions |
| Fri | Final Review | Accessibility audit, user testing |

**Deliverables:**
- [ ] All P2 items complete
- [ ] Cozy UI transformation complete
- [ ] User validation positive

---

## Effort Summary

| Priority | Items | Total Effort |
|----------|-------|--------------|
| P0 - Critical | 9 | ~14 hours |
| P1 - High | 12 | ~25 hours |
| P2 - Medium | 14 | ~22 hours |
| P3 - Low | 12 | ~55 hours |
| **Total** | **47** | **~116 hours** |

### By Category

| Category | Effort | Notes |
|----------|--------|-------|
| Backend Testing | 15h | Critical for reliability |
| Type Safety | 5h | Quick wins |
| Accessibility | 5h | Quick wins with high impact |
| Performance | 5h | Route splitting, memoization |
| Cozy UI | 25h | Main transformation |
| Integration | 5h | Cache, error handling |
| Future/Infra | 56h | PostgreSQL, WebSocket, etc. |

---

## Quick Reference: Top 10 Items

For immediate action, focus on these high-impact items:

| # | Item | Effort | Category |
|---|------|--------|----------|
| 1 | Fix 4 `any` type usages | 30m | P0 |
| 2 | Add semantic landmarks | 15m | P0 |
| 3 | Add `hybrid_mmr` to Player type | 15m | P0 |
| 4 | Add keyboard support to cards | 2h | P0 |
| 5 | Update fonts to Poppins/Inter | 1h | P1 |
| 6 | Add axios timeout | 30m | P1 |
| 7 | Add `React.memo` to list components | 1h | P1 |
| 8 | Update color tokens | 2h | P1 |
| 9 | Transform TacticalCard | 2h | P1 |
| 10 | Add cache invalidation to upload | 1h | P1 |

**Total for Top 10:** ~11 hours

---

## Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                      DEPENDENCY GRAPH                        │
└─────────────────────────────────────────────────────────────┘

[Theme Foundation]
      │
      ├──→ [Update Fonts] ──→ [Update Pages]
      │
      └──→ [Update Colors] ──→ [Transform Components]
                                      │
                                      ├──→ [TacticalCard → Card]
                                      │
                                      ├──→ [Navigation]
                                      │
                                      └──→ [PlayerCard]
                                              │
                                              └──→ [Page Updates]

[Backend Tests]
      │
      ├──→ [Integration Tests] (independent)
      │
      └──→ [Type Fixes] ──→ [Service Layer] (dependent)

[Accessibility]
      │
      ├──→ [Semantic Landmarks] (independent)
      │
      └──→ [Keyboard Support] (independent, can parallelize)
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Cozy UI breaks existing functionality | Low | High | Feature branch, visual regression tests |
| Theme changes cascade unexpectedly | Medium | Medium | Incremental commits, MCP screenshot review |
| Backend type fixes cause runtime issues | Low | High | Comprehensive test coverage first |
| Font loading affects performance | Low | Low | Preconnect, font-display: swap |
| User resistance to visual change | Medium | Medium | Gradual rollout, user feedback loop |

---

**Document Version:** 1.0  
**Status:** Complete  
**Related:** `04-cozy-ui-roadmap.md`, `06-mcp-integration-guide.md`
