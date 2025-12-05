# SPEC-REFACTOR-001: Acceptance Criteria

---
spec_id: SPEC-REFACTOR-001
version: 1.0.0
status: draft
created: 2025-12-06
---

## Overview

This document defines the acceptance criteria for the SC2 MMR Tracker Comprehensive Refactoring. All scenarios must pass before the SPEC can be marked as complete.

---

## 1. Backend Test Fixes

### Scenario 1.1: All Basic Tests Pass

```gherkin
Feature: Backend Basic Tests
  As a developer
  I want all basic tests to pass
  So that the codebase has a reliable foundation

  Scenario: Execute test suite
    Given the backend test suite exists at tests/test_basic.py
    When I run pytest tests/test_basic.py -v
    Then all 6 tests should pass
    And the output should show "6 passed, 0 failed"

  Scenario: Player creation with defaults
    Given a new Player model is instantiated
    When I access the mu property
    Then it should equal 25.0
    And sigma should equal 8.333

  Scenario: MMR calculation accuracy
    Given a Player with mu=30.0
    When I access the mmr property
    Then it should equal 2200 (1000 + 40*30)

  Scenario: Win rate returns percentage
    Given a Player with 10 total_games, 7 wins, 3 losses
    When I access the win_rate property
    Then it should return 0.7 (decimal format)
    Or it should return 70.0 (percentage format) - decision required
```

### Scenario 1.2: MMR Formula Consistency

```gherkin
Feature: Unified MMR Formula
  As a user
  I want consistent MMR values across the application
  So that I'm not confused by different numbers

  Scenario: MMR formula is centralized
    Given the RatingSystem class in rating_system.py
    When I search for MMR calculation
    Then there should be exactly one calculate_display_mmr method
    And all other files should reference this method

  Scenario: Historical MMR uses same formula
    Given a MatchPlayer record with mu_before=25.0
    When I calculate mmr_before
    Then it should use the same formula as Player.mmr
    And the value should be 2000 (1000 + 40*25)
```

---

## 2. Backend Architecture

### Scenario 2.1: Service Layer Exists

```gherkin
Feature: Service Layer Architecture
  As a developer
  I want business logic separated from API routes
  So that the code is testable and maintainable

  Scenario: Services directory structure
    Given the backend app directory
    When I check app/services/
    Then the following files should exist:
      | File                  |
      | __init__.py           |
      | replay_service.py     |
      | rating_service.py     |
      | match_service.py      |

  Scenario: ReplayService implementation
    Given the ReplayService class
    When I inspect its methods
    Then no method should exceed 50 lines
    And it should have methods for:
      | Method               | Purpose                    |
      | process_replay       | Main entry point           |
      | _parse_replay        | Parse SC2 replay file      |
      | _validate_replay     | Validate replay data       |
      | _create_match        | Create match record        |
      | _update_player_ratings | Update ratings after match |
```

### Scenario 2.2: Error Handling Improvement

```gherkin
Feature: Proper Error Handling
  As a developer
  I want specific exception types
  So that errors are properly identified and handled

  Scenario: No broad exception handlers
    Given the app/api/ directory
    When I search for "except Exception:"
    Then zero matches should be found
    And specific exceptions should be used instead

  Scenario: Database rollback on error
    Given an API endpoint that modifies the database
    When an error occurs during the transaction
    Then db.rollback() should be called
    And a specific error message should be returned

  Scenario: Custom exceptions exist
    Given the app/exceptions.py file
    Then the following exceptions should be defined:
      | Exception               | Purpose                        |
      | SC2MMRException         | Base exception                 |
      | ReplayParseError        | Replay parsing failures        |
      | WinnerDeterminationError | Winner cannot be determined   |
      | RatingCalculationError  | Rating calculation failures    |
      | PlayerNotFoundError     | Player not found               |
```

### Scenario 2.3: Centralized Configuration

```gherkin
Feature: Configuration Management
  As a developer
  I want configuration centralized
  So that settings are easy to manage and override

  Scenario: Config file exists
    Given the app/ directory
    When I check for config.py
    Then it should exist with pydantic-settings

  Scenario: Configuration values
    Given the Settings class in config.py
    Then the following settings should be configurable:
      | Setting              | Default Value              |
      | database_url         | sqlite:///./data/sc2mmr.db |
      | cors_origins         | ["http://localhost:5173"]  |
      | trueskill_mu         | 25.0                       |
      | trueskill_sigma      | 8.333                      |
      | mmr_base             | 1000                       |
      | mmr_mu_multiplier    | 40                         |

  Scenario: CORS not wildcard
    Given the main.py file
    When I check the CORS middleware configuration
    Then allow_origins should NOT be ["*"]
    And it should use settings.cors_origins
```

---

## 3. Frontend TypeScript Migration

### Scenario 3.1: Full TypeScript Coverage

```gherkin
Feature: TypeScript Migration
  As a developer
  I want type-safe frontend code
  So that runtime errors are caught at compile time

  Scenario: No JSX files remain
    Given the frontend/src directory
    When I search for .jsx files
    Then zero files should be found
    And all React files should be .tsx

  Scenario: TypeScript configuration
    Given the frontend directory
    Then tsconfig.json should exist
    And strict mode should be enabled

  Scenario: Type check passes
    Given the frontend codebase
    When I run npx tsc --noEmit
    Then zero type errors should be reported
```

### Scenario 3.2: Type Definitions

```gherkin
Feature: API Type Definitions
  As a developer
  I want typed API responses
  So that I have autocomplete and type safety

  Scenario: Types directory exists
    Given the frontend/src directory
    When I check for types/
    Then the following files should exist:
      | File           | Purpose                   |
      | api.ts         | API response types        |
      | components.ts  | Component prop types      |
      | index.ts       | Re-exports                |

  Scenario: Player type is complete
    Given the Player interface in types/api.ts
    Then it should include all fields:
      | Field             | Type    |
      | id                | number  |
      | name              | string  |
      | mu                | number  |
      | sigma             | number  |
      | mmr               | number  |
      | win_rate          | number  |
      | total_games       | number  |
      | wins              | number  |
      | losses            | number  |
      | favorite_race     | string  |
      | is_core_player    | boolean |
```

---

## 4. Frontend Component Extraction

### Scenario 4.1: Shared Components

```gherkin
Feature: Extracted Shared Components
  As a developer
  I want reusable components
  So that code is not duplicated

  Scenario: TacticalBackground component exists
    Given the components/common directory
    When I check for TacticalBackground.tsx
    Then it should exist
    And it should accept variant and opacity props

  Scenario: TacticalBackground replaces duplicates
    Given the following files:
      | File                          |
      | pages/Players.tsx             |
      | pages/TeamGenerator/index.tsx |
      | pages/MatchDetail/index.tsx   |
      | pages/LineupPredictor.tsx     |
    When I search for tactical grid background code
    Then each file should import TacticalBackground
    And no inline tactical background CSS should exist

  Scenario: WinProbabilityDisplay component
    Given the components/common directory
    Then WinProbabilityDisplay.tsx should exist
    And it should accept team1Probability and team2Probability props
```

### Scenario 4.2: Custom Hooks

```gherkin
Feature: Player Selection Hook
  As a developer
  I want shared selection logic
  So that TeamGenerator and LineupPredictor work consistently

  Scenario: usePlayerSelection hook exists
    Given the hooks directory
    When I check for usePlayerSelection.ts
    Then it should exist
    And it should export usePlayerSelection function

  Scenario: Hook interface
    Given the usePlayerSelection hook
    Then it should return:
      | Property         | Type                     |
      | selectedPlayers  | Player[]                 |
      | togglePlayer     | (player: Player) => void |
      | isSelected       | (player: Player) => boolean |
      | clearSelection   | () => void               |
      | canSelect        | boolean                  |
      | selectionCount   | number                   |
```

### Scenario 4.3: Component Size Limits

```gherkin
Feature: Component Size Limits
  As a developer
  I want small focused components
  So that code is readable and maintainable

  Scenario: No component exceeds 300 lines
    Given all .tsx files in src/
    When I count lines per file
    Then no file should exceed 300 lines

  Scenario: TeamGenerator is decomposed
    Given the pages/TeamGenerator directory
    Then the following files should exist:
      | File                      | Max Lines |
      | index.tsx                 | 150       |
      | TeamSelector.tsx          | 200       |
      | TeamDisplay.tsx           | 150       |
      | BalanceResults.tsx        | 200       |

  Scenario: MatchDetail is decomposed
    Given the pages/MatchDetail directory
    Then the following files should exist:
      | File               | Max Lines |
      | index.tsx          | 150       |
      | MatchHeader.tsx    | 150       |
      | AnalyticsTab.tsx   | 250       |
      | TimelineTab.tsx    | 200       |
```

---

## 5. Design System Unification

### Scenario 5.1: Theme Tokens

```gherkin
Feature: Design Tokens
  As a developer
  I want centralized design tokens
  So that styling is consistent

  Scenario: Tokens file exists
    Given the theme directory
    When I check for tokens.ts
    Then it should exist
    And it should export colors, spacing, and radii

  Scenario: Color tokens are complete
    Given the colors object in tokens.ts
    Then it should include:
      | Category | Tokens                           |
      | brand    | 50, 100, 500, 600, 900           |
      | accent   | 500, 600                         |
      | race     | terran, protoss, zerg, random    |
      | status   | win, loss, draw                  |
      | bg       | card, overlay, tactical          |
```

### Scenario 5.2: No Hardcoded Colors

```gherkin
Feature: Theme Token Usage
  As a developer
  I want all colors to use theme tokens
  So that styling is maintainable

  Scenario: No rgba in components
    Given all files in src/components/ and src/pages/
    When I search for rgba\(
    Then zero matches should be found outside theme files

  Scenario: No hex colors in components
    Given all files in src/components/ and src/pages/
    When I search for #[0-9a-fA-F]{3,6}
    Then zero matches should be found outside theme files
```

### Scenario 5.3: Animations Centralized

```gherkin
Feature: Centralized Animations
  As a developer
  I want animations in one place
  So that they're consistent and reusable

  Scenario: Animations file exists
    Given the theme directory
    When I check for animations.ts
    Then it should exist
    And it should export keyframes and animation strings

  Scenario: No inline keyframes
    Given all files in src/components/ and src/pages/
    When I search for @keyframes
    Then zero matches should be found
    And animations should be imported from theme/animations
```

### Scenario 5.4: Unused Files Removed

```gherkin
Feature: Clean Codebase
  As a developer
  I want no unused files
  So that the codebase is clean

  Scenario: App.css is removed
    Given the src directory
    When I check for App.css
    Then it should NOT exist
```

---

## 6. Test Coverage

### Scenario 6.1: Backend Coverage

```gherkin
Feature: Backend Test Coverage
  As a developer
  I want high test coverage
  So that changes are safe

  Scenario: Coverage meets target
    Given the backend test suite
    When I run pytest --cov=app --cov-fail-under=80
    Then the command should succeed
    And coverage should be >= 80%

  Scenario: API endpoints are tested
    Given the tests/test_api directory
    Then tests should exist for:
      | Endpoint Category | Test File          |
      | /players/*        | test_players.py    |
      | /replays/*        | test_replays.py    |
      | /teams/*          | test_teams.py      |
      | /impact/*         | test_impact.py     |

  Scenario: Services are tested
    Given the tests/test_services directory
    Then tests should exist for:
      | Service        | Test File               |
      | ReplayService  | test_replay_service.py  |
      | RatingService  | test_rating_service.py  |
      | MatchService   | test_match_service.py   |
```

### Scenario 6.2: Frontend Coverage

```gherkin
Feature: Frontend Test Coverage
  As a developer
  I want high frontend test coverage
  So that UI changes are safe

  Scenario: Vitest is configured
    Given the frontend directory
    Then vitest.config.ts should exist
    And package.json should have test scripts

  Scenario: Coverage meets target
    Given the frontend test suite
    When I run npm run test:coverage
    Then coverage should be >= 80%

  Scenario: Components are tested
    Given the src/components directory
    Then test files should exist for:
      | Component           | Test File                   |
      | PlayerCard          | PlayerCard.test.tsx         |
      | TacticalCard        | TacticalCard.test.tsx       |
      | TacticalBackground  | TacticalBackground.test.tsx |
      | ErrorBoundary       | ErrorBoundary.test.tsx      |

  Scenario: Hooks are tested
    Given the src/hooks directory
    Then test files should exist for:
      | Hook               | Test File                    |
      | usePlayerSelection | usePlayerSelection.test.ts   |
      | useToast           | useToast.test.ts             |
```

---

## 7. Integration Criteria

### Scenario 7.1: Build Success

```gherkin
Feature: Successful Build
  As a developer
  I want the application to build
  So that it can be deployed

  Scenario: Backend starts successfully
    Given the backend directory
    When I run uvicorn app.main:app
    Then the server should start without errors
    And /health endpoint should return 200

  Scenario: Frontend builds successfully
    Given the frontend directory
    When I run npm run build
    Then the build should complete without errors
    And dist/ directory should be created

  Scenario: Frontend dev server works
    Given the frontend directory
    When I run npm run dev
    Then the development server should start
    And the application should be accessible at localhost:5173
```

### Scenario 7.2: API Backward Compatibility

```gherkin
Feature: API Backward Compatibility
  As a user
  I want existing API calls to work
  So that my workflow is not disrupted

  Scenario: Existing endpoints unchanged
    Given the refactored backend
    When I call GET /players/
    Then the response format should be unchanged

  Scenario: MMR values consistent
    Given a player with known mu value
    When I retrieve the player via API
    Then the MMR should match the unified formula
    And historical match MMR values should be consistent
```

---

## 8. Final Acceptance Checklist

### Pre-Merge Checklist

- [ ] All 6 backend basic tests pass
- [ ] Backend coverage >= 80%
- [ ] Frontend coverage >= 80%
- [ ] Zero .jsx files remain
- [ ] TypeScript build passes with no errors
- [ ] Zero hardcoded rgba() values in components/pages
- [ ] Zero broad `except Exception` handlers
- [ ] All services created and used
- [ ] Configuration centralized
- [ ] CORS properly configured
- [ ] App.css removed
- [ ] TacticalBackground component created and used
- [ ] usePlayerSelection hook created and used
- [ ] No component exceeds 300 lines
- [ ] No function exceeds 50 lines
- [ ] Both backend and frontend build successfully
- [ ] All API endpoints return expected responses

### Sign-Off Requirements

| Role | Requirement | Status |
|------|-------------|--------|
| Developer | All tests pass | [ ] |
| Developer | Coverage targets met | [ ] |
| Developer | Build succeeds | [ ] |
| Reviewer | Code review complete | [ ] |
| QA | Manual testing complete | [ ] |

---

## Validation Commands

```bash
# Backend Tests
cd backend && pytest -v --cov=app --cov-report=term-missing

# Frontend Type Check
cd frontend && npx tsc --noEmit

# Frontend Build
cd frontend && npm run build

# Frontend Tests
cd frontend && npm run test:coverage

# Search for issues
grep -r "except Exception:" backend/app/api/  # Should be 0
find frontend/src -name "*.jsx" | wc -l       # Should be 0
grep -r "rgba(" frontend/src/components/ frontend/src/pages/ | wc -l  # Should be 0
```
