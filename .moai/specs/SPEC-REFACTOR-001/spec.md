# SPEC-REFACTOR-001: SC2 MMR Tracker Comprehensive Refactoring

---
id: SPEC-REFACTOR-001
version: 1.0.0
status: draft
created: 2025-12-06
updated: 2025-12-06
author: R2-D2
priority: high
---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-06 | R2-D2 | Initial SPEC creation |

---

## 1. Overview

### 1.1 Purpose

This SPEC defines a comprehensive refactoring of the SC2 MMR Tracker application to:
- Fix all failing backend tests
- Unify inconsistent MMR formula calculations
- Simplify backend architecture for extensibility
- Modernize frontend with TypeScript and unified design system
- Improve error handling and reduce error-prone code patterns

### 1.2 Scope

| Area | In Scope | Out of Scope |
|------|----------|--------------|
| Backend Tests | Fix 4 failing tests, add API tests | Full E2E testing |
| MMR Formula | Unify to single formula, recalculate ratings | Algorithm changes |
| Backend Architecture | Service layer extraction, error handling | Database schema changes |
| Frontend | TypeScript migration, component extraction | New features |
| Styling | Theme token unification, design system | Visual redesign |
| Testing | 80% coverage target | Performance testing |

### 1.3 Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Backend Test Pass Rate | 33% (2/6) | 100% |
| Backend Test Coverage | <5% | 80% |
| Frontend Test Coverage | 0% | 80% |
| TypeScript Coverage | 0% | 100% |
| Hardcoded Colors | 50+ | 0 |
| Functions >100 lines | 5+ | 0 |

---

## 2. Functional Requirements (MUST)

### 2.1 Backend Test Fixes

| ID | Requirement |
|----|-------------|
| FR-001 | The system MUST fix `test_player_creation` by ensuring SQLAlchemy model defaults are applied correctly in test fixtures |
| FR-002 | The system MUST fix `test_player_mmr_calculation` by updating test assertions to match current MMR formula: `1000 + 40*mu` |
| FR-003 | The system MUST fix `test_player_win_rate` by standardizing `win_rate` property to return percentage (0-100) OR updating test to expect decimal (0-1) |
| FR-004 | The system MUST fix `test_conservative_rating` by aligning `RatingSystem.get_conservative_rating()` with display MMR formula |
| FR-005 | The system MUST unify MMR calculation to a single source of truth in `rating_system.py` |

### 2.2 Backend Architecture

| ID | Requirement |
|----|-------------|
| FR-010 | The system MUST extract `upload_replay_advanced()` (254 lines) into a dedicated `ReplayService` class with methods <50 lines each |
| FR-011 | The system MUST extract `recalculate_all_ratings()` (267 lines) into `RatingService` with decomposed methods |
| FR-012 | The system MUST extract `set_manual_winner()` (212 lines) into `MatchService` |
| FR-013 | The system MUST create `/backend/app/services/` directory with service layer architecture |
| FR-014 | The system MUST create `/backend/app/config.py` using `pydantic-settings` for centralized configuration |
| FR-015 | The system MUST add proper `db.rollback()` calls to all database transaction error handlers |

### 2.3 Frontend TypeScript Migration

| ID | Requirement |
|----|-------------|
| FR-020 | The system MUST migrate all 25+ `.jsx` files to `.tsx` TypeScript files |
| FR-021 | The system MUST create type definitions for all API response shapes in `/frontend/src/types/` |
| FR-022 | The system MUST add `tsconfig.json` with strict mode enabled |
| FR-023 | The system MUST add type annotations to all component props |

### 2.4 Frontend Component Extraction

| ID | Requirement |
|----|-------------|
| FR-030 | The system MUST decompose `TeamGenerator.jsx` (988 lines) into `TeamSelector`, `TeamDisplay`, and `BalanceResults` components |
| FR-031 | The system MUST decompose `MatchDetail.jsx` (1,063 lines) into `MatchHeader`, `AnalyticsTab`, `TimelineTab` components |
| FR-032 | The system MUST extract duplicated tactical background pattern into `TacticalBackground` component |
| FR-033 | The system MUST create `usePlayerSelection` custom hook for shared player selection logic |
| FR-034 | The system MUST extract `WinProbabilityDisplay` component from duplicated patterns |

### 2.5 Design System Unification

| ID | Requirement |
|----|-------------|
| FR-040 | The system MUST replace all hardcoded `rgba()` color values (50+ instances) with Chakra theme tokens |
| FR-041 | The system MUST move all inline keyframe animations to `/frontend/src/theme/animations.ts` |
| FR-042 | The system MUST remove unused `App.css` file |
| FR-043 | The system MUST create `/frontend/src/theme/tokens.ts` for design token definitions |

---

## 3. Non-Functional Requirements (SHOULD)

### 3.1 Code Quality

| ID | Requirement |
|----|-------------|
| NFR-001 | Backend test coverage SHOULD reach 80% as measured by pytest-cov |
| NFR-002 | Frontend test coverage SHOULD reach 80% as measured by Vitest |
| NFR-003 | No function SHOULD exceed 50 lines of logic (excluding imports, comments) |
| NFR-004 | No component file SHOULD exceed 300 lines |
| NFR-005 | Cyclomatic complexity SHOULD not exceed 10 per function |

### 3.2 Performance

| ID | Requirement |
|----|-------------|
| NFR-010 | TypeScript migration SHOULD NOT increase bundle size by more than 10% |
| NFR-011 | Component extraction SHOULD maintain current render performance |

### 3.3 Maintainability

| ID | Requirement |
|----|-------------|
| NFR-020 | All extracted services SHOULD follow single responsibility principle |
| NFR-021 | All new components SHOULD have JSDoc/TSDoc comments |
| NFR-022 | Configuration changes SHOULD be loadable from environment variables |

---

## 4. Interface Requirements (SHALL)

### 4.1 API Contracts

| ID | Requirement |
|----|-------------|
| IR-001 | Existing API response shapes SHALL remain unchanged (backward compatible) |
| IR-002 | MMR values returned by API SHALL use unified formula consistently |
| IR-003 | Error responses SHALL follow consistent format: `{ detail: string, code?: string }` |

### 4.2 Component Interfaces

| ID | Requirement |
|----|-------------|
| IR-010 | Extracted components SHALL maintain existing prop interfaces |
| IR-011 | Custom hooks SHALL return typed objects with clear interfaces |
| IR-012 | Theme tokens SHALL be accessible via Chakra's `useTheme` hook |

---

## 5. Design Constraints (MUST)

### 5.1 Technology Constraints

| ID | Constraint |
|----|------------|
| DC-001 | Backend MUST remain Python 3.10+ with FastAPI |
| DC-002 | Frontend MUST remain React 19 with Vite |
| DC-003 | TypeScript version MUST be 5.0+ |
| DC-004 | Database schema MUST NOT change (SQLite with current tables) |
| DC-005 | Chakra UI MUST remain the styling framework |

### 5.2 Backward Compatibility

| ID | Constraint |
|----|------------|
| DC-010 | All existing API endpoints MUST continue to work without changes |
| DC-011 | Existing replay files MUST remain processable |
| DC-012 | User-facing MMR display MUST NOT change visually (same formula already displayed) |

### 5.3 Security Constraints

| ID | Constraint |
|----|------------|
| DC-020 | CORS MUST be configured with specific origins, not wildcard `*` |
| DC-021 | Exception details MUST NOT leak internal stack traces in production |

---

## 6. Acceptance Criteria

### 6.1 Backend Test Criteria

```gherkin
GIVEN the backend test suite
WHEN pytest is executed on tests/test_basic.py
THEN all 6 tests SHALL pass with 0 failures

GIVEN a Player model instance created in test
WHEN default values are accessed before session commit
THEN mu SHALL equal 25.0 AND sigma SHALL equal 8.333

GIVEN a Player with 10 games, 7 wins, 3 losses
WHEN win_rate property is accessed
THEN it SHALL return 70.0 as a percentage
```

### 6.2 Architecture Criteria

```gherkin
GIVEN the refactored backend codebase
WHEN analyzing function lengths in app/api/ directory
THEN no function SHALL exceed 50 lines of business logic

GIVEN a database error during replay upload
WHEN the exception is caught
THEN db.rollback() SHALL be called AND specific error message returned

GIVEN the services directory
WHEN inspecting service classes
THEN ReplayService, RatingService, and MatchService SHALL exist
```

### 6.3 Frontend Criteria

```gherkin
GIVEN the frontend source directory
WHEN searching for .jsx files
THEN 0 files SHALL be found (all converted to .tsx)

GIVEN the TeamGenerator component
WHEN analyzing the file structure
THEN TeamSelector, TeamDisplay, and BalanceResults SHALL be separate files

GIVEN any component file
WHEN searching for hardcoded rgba values
THEN 0 hardcoded color values SHALL be found
```

### 6.4 Test Coverage Criteria

```gherkin
GIVEN the backend test suite
WHEN pytest --cov is executed
THEN coverage SHALL be >= 80%

GIVEN the frontend test suite
WHEN vitest --coverage is executed
THEN coverage SHALL be >= 80%
```

---

## 7. Technical Context

### 7.1 Current Architecture

```
Backend:
/backend
├── app/
│   ├── api/           # Routes + business logic (mixed)
│   │   ├── players.py   (856 lines, 267-line function)
│   │   ├── replays.py   (1,172 lines, 254-line function)
│   │   ├── teams.py     (600 lines)
│   │   └── impact.py    (660 lines)
│   ├── models.py        (344 lines)
│   ├── rating_system.py (433 lines)
│   └── balancer.py      (447 lines)
└── tests/
    └── test_basic.py    (71 lines, 4 failing)

Frontend:
/frontend/src
├── api/               # API client (2 files)
├── components/        # Reusable components (11 files)
├── pages/             # Page components (11 files, 2 >1000 lines)
├── theme/             # Chakra theme (1 file)
└── utils/             # Utilities (1 file)
```

### 7.2 Target Architecture

```
Backend:
/backend
├── app/
│   ├── api/           # HTTP layer only (thin controllers)
│   ├── services/      # Business logic (NEW)
│   │   ├── replay_service.py
│   │   ├── rating_service.py
│   │   └── match_service.py
│   ├── config.py      # Centralized configuration (NEW)
│   ├── exceptions.py  # Custom exception types (NEW)
│   ├── models.py
│   └── rating_system.py
└── tests/
    ├── test_basic.py
    ├── test_api/      # API endpoint tests (NEW)
    └── test_services/ # Service layer tests (NEW)

Frontend:
/frontend/src
├── api/
├── components/
│   ├── common/        # Shared components (NEW)
│   │   ├── TacticalBackground.tsx
│   │   └── WinProbabilityDisplay.tsx
│   ├── team/          # Team-related components (NEW)
│   └── match/         # Match-related components (NEW)
├── hooks/             # Custom hooks (EXPANDED)
│   └── usePlayerSelection.ts
├── pages/
├── theme/
│   ├── index.ts
│   ├── tokens.ts      # Design tokens (NEW)
│   └── animations.ts  # Keyframe animations (NEW)
├── types/             # TypeScript definitions (NEW)
└── utils/
```

### 7.3 MMR Formula Unification

**Current State (3 formulas)**:
- Display MMR: `1000 + 40*mu`
- Historical MMR: `1000 + 40*mu - 120*sigma`
- Conservative rating: `mu - 3*sigma`

**Target State (1 formula)**:
```python
# rating_system.py
class RatingSystem:
    @staticmethod
    def calculate_display_mmr(mu: float, sigma: float = None) -> float:
        """
        Unified MMR calculation for display purposes.
        Sigma is kept internal for matchmaking quality.
        """
        return 1000 + (40 * mu)
```

---

## 8. Dependencies

### 8.1 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| typescript | ^5.0.0 | TypeScript compiler |
| @types/react | ^19.0.0 | React type definitions |
| vitest | ^2.0.0 | Frontend testing |
| @testing-library/react | ^16.0.0 | React testing utilities |
| pydantic-settings | ^2.0.0 | Backend configuration |
| pytest-cov | ^4.0.0 | Backend coverage |

### 8.2 Internal Dependencies

| Component | Depends On |
|-----------|------------|
| API Routes | Services |
| Services | Models, RatingSystem |
| Frontend Components | Types, Theme Tokens |
| Custom Hooks | Types |

---

## 9. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MMR recalculation affects existing ratings | Medium | High | Backup database before migration, verify with test data |
| TypeScript migration breaks runtime | Low | Medium | Incremental migration, keep `strict: false` initially |
| Large component refactor introduces bugs | Medium | Medium | Visual regression testing, extract with identical UI first |
| Service extraction breaks existing functionality | Low | High | Comprehensive API tests before and after extraction |

---

## 10. Implementation Phases

### Phase 1: Backend Test Fixes (Priority: BLOCKING)
- Fix 4 failing tests
- Unify MMR formula
- Add test fixtures

### Phase 2: Backend Architecture (Priority: HIGH)
- Create service layer
- Extract business logic
- Centralize configuration
- Improve error handling

### Phase 3: Frontend TypeScript (Priority: HIGH)
- Setup TypeScript configuration
- Create type definitions
- Migrate components incrementally

### Phase 4: Frontend Components (Priority: MEDIUM)
- Extract shared components
- Decompose large pages
- Create custom hooks

### Phase 5: Design System (Priority: MEDIUM)
- Unify theme tokens
- Extract animations
- Remove hardcoded colors

### Phase 6: Test Coverage (Priority: HIGH)
- Add backend API tests
- Add frontend component tests
- Verify coverage targets

---

## 11. Glossary

| Term | Definition |
|------|------------|
| MMR | Matchmaking Rating - skill-based rating for player matching |
| TrueSkill | Microsoft's Bayesian skill rating system |
| mu (μ) | TrueSkill skill estimate (default 25.0) |
| sigma (σ) | TrueSkill uncertainty (default 8.333) |
| EARS | Easy Approach to Requirements Syntax |
| Service Layer | Business logic abstraction between API and data |

---

## 12. References

- [TrueSkill Documentation](https://trueskill.org/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Chakra UI Theme](https://chakra-ui.com/docs/styled-system/theme)
