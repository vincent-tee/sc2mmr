# SPEC-REFACTOR-001: Implementation Plan

---
spec_id: SPEC-REFACTOR-001
version: 1.0.0
status: draft
created: 2025-12-06
---

## Executive Summary

This implementation plan details the step-by-step execution of the SC2 MMR Tracker comprehensive refactoring. The plan is organized into 6 phases with clear dependencies, deliverables, and validation criteria.

**Total Estimated Effort**: 5-7 development days
**Recommended Approach**: TDD (Red-Green-Refactor)

---

## Phase 1: Backend Test Fixes (BLOCKING)

**Priority**: Critical - Must complete before other phases
**Estimated Effort**: 0.5 days
**Dependencies**: None

### 1.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| P1-T01 | Fix `test_player_creation` - Update test to use proper SQLAlchemy session fixture | `tests/test_basic.py`, `tests/conftest.py` | 30 min |
| P1-T02 | Fix `test_player_mmr_calculation` - Update assertion to match `1000 + 40*mu` formula | `tests/test_basic.py` | 15 min |
| P1-T03 | Standardize `win_rate` - Update test OR property to be consistent | `tests/test_basic.py`, `app/models.py` | 30 min |
| P1-T04 | Fix `test_conservative_rating` - Align with unified MMR formula | `tests/test_basic.py`, `app/rating_system.py` | 30 min |
| P1-T05 | Create centralized MMR calculation function | `app/rating_system.py` | 30 min |
| P1-T06 | Update all MMR references to use central function | Multiple files | 1 hour |

### 1.2 Implementation Details

#### P1-T01: Fix test_player_creation

**Problem**: SQLAlchemy column defaults are not applied until session flush.

**Solution**: Create proper test fixture with session.

```python
# tests/conftest.py (NEW)
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def player_factory(db_session):
    def _create_player(**kwargs):
        from app.models import Player
        defaults = {"name": "TestPlayer", "mu": 25.0, "sigma": 8.333}
        defaults.update(kwargs)
        player = Player(**defaults)
        db_session.add(player)
        db_session.flush()
        return player
    return _create_player
```

#### P1-T02: Fix test_player_mmr_calculation

**Current Test** (incorrect):
```python
expected_mmr = 25.0 - (3 * 8.333)  # Old formula
```

**Updated Test**:
```python
expected_mmr = 1000 + (40 * 25.0)  # Current formula: 2000
```

#### P1-T05: Centralized MMR Calculation

```python
# app/rating_system.py
class RatingSystem:
    # MMR Calculation Constants
    MMR_BASE = 1000
    MMR_MU_MULTIPLIER = 40

    @staticmethod
    def calculate_display_mmr(mu: float) -> float:
        """
        Unified MMR calculation for display purposes.
        Formula: 1000 + 40*mu

        Returns approximately:
        - New players (mu=25): 2000 MMR
        - Experienced range: 800-2200 MMR
        """
        return RatingSystem.MMR_BASE + (RatingSystem.MMR_MU_MULTIPLIER * mu)
```

### 1.3 Validation

```bash
# All tests must pass
cd backend && pytest tests/test_basic.py -v

# Expected output:
# tests/test_basic.py::test_player_creation PASSED
# tests/test_basic.py::test_player_mmr_calculation PASSED
# tests/test_basic.py::test_player_win_rate PASSED
# tests/test_basic.py::test_favorite_race PASSED
# tests/test_basic.py::test_trueskill_rating_creation PASSED
# tests/test_basic.py::test_conservative_rating PASSED
```

---

## Phase 2: Backend Architecture (HIGH)

**Priority**: High
**Estimated Effort**: 1.5 days
**Dependencies**: Phase 1 complete

### 2.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| P2-T01 | Create `/backend/app/services/` directory structure | Directory creation | 5 min |
| P2-T02 | Create `ReplayService` with extracted upload logic | `services/replay_service.py` | 2 hours |
| P2-T03 | Create `RatingService` with recalculation logic | `services/rating_service.py` | 2 hours |
| P2-T04 | Create `MatchService` with match operations | `services/match_service.py` | 1 hour |
| P2-T05 | Create `config.py` with pydantic-settings | `app/config.py` | 1 hour |
| P2-T06 | Create custom exception types | `app/exceptions.py` | 30 min |
| P2-T07 | Refactor API routes to use services | `app/api/*.py` | 2 hours |
| P2-T08 | Add proper rollback handling | `app/api/*.py` | 1 hour |
| P2-T09 | Fix CORS configuration | `app/main.py` | 15 min |

### 2.2 Implementation Details

#### P2-T01: Service Directory Structure

```
backend/app/services/
├── __init__.py
├── base.py           # Base service class
├── replay_service.py # Replay upload/processing
├── rating_service.py # Rating calculations
└── match_service.py  # Match operations
```

#### P2-T02: ReplayService Extraction

**Before** (api/replays.py:upload_replay_advanced - 254 lines):
```python
@router.post("/upload-advanced")
async def upload_replay_advanced(file: UploadFile, db: Session):
    # 254 lines of mixed concerns
    pass
```

**After**:
```python
# services/replay_service.py
class ReplayService:
    def __init__(self, db: Session):
        self.db = db

    def process_replay(self, file_content: bytes, filename: str) -> Match:
        """Process uploaded replay file. Max 40 lines."""
        replay_data = self._parse_replay(file_content)
        self._validate_replay(replay_data)
        match = self._create_match(replay_data)
        self._update_player_ratings(match)
        return match

    def _parse_replay(self, content: bytes) -> dict:
        """Parse SC2 replay file. Max 30 lines."""
        pass

    def _validate_replay(self, data: dict) -> None:
        """Validate replay data. Max 20 lines."""
        pass

    def _create_match(self, data: dict) -> Match:
        """Create match record. Max 30 lines."""
        pass

    def _update_player_ratings(self, match: Match) -> None:
        """Update player ratings after match. Max 30 lines."""
        pass

# api/replays.py (thin controller)
@router.post("/upload-advanced")
async def upload_replay_advanced(file: UploadFile, db: Session):
    service = ReplayService(db)
    try:
        match = service.process_replay(await file.read(), file.filename)
        return {"match_id": match.id, "status": "success"}
    except ReplayParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
```

#### P2-T05: Centralized Configuration

```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./data/sc2mmr.db"

    # CORS
    cors_origins: List[str] = ["http://localhost:5173"]

    # TrueSkill Parameters
    trueskill_mu: float = 25.0
    trueskill_sigma: float = 8.333
    trueskill_beta: float = 4.166
    trueskill_tau: float = 0.083
    trueskill_draw_probability: float = 0.0

    # MMR Display
    mmr_base: int = 1000
    mmr_mu_multiplier: int = 40

    # Recency Weighting
    recency_half_life_days: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

#### P2-T06: Custom Exceptions

```python
# app/exceptions.py
class SC2MMRException(Exception):
    """Base exception for SC2 MMR application."""
    pass

class ReplayParseError(SC2MMRException):
    """Raised when replay parsing fails."""
    pass

class WinnerDeterminationError(SC2MMRException):
    """Raised when winner cannot be determined."""
    pass

class RatingCalculationError(SC2MMRException):
    """Raised when rating calculation fails."""
    pass

class PlayerNotFoundError(SC2MMRException):
    """Raised when player is not found."""
    pass
```

#### P2-T09: Fix CORS

```python
# app/main.py
from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # Not ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2.3 Validation

```bash
# Run all backend tests
cd backend && pytest -v --cov=app --cov-report=term-missing

# Verify no broad exception handlers
grep -r "except Exception" app/api/ | wc -l  # Should be 0

# Verify CORS not wildcard
grep "allow_origins" app/main.py  # Should show specific origins
```

---

## Phase 3: Frontend TypeScript Migration (HIGH)

**Priority**: High
**Estimated Effort**: 1.5 days
**Dependencies**: None (can run parallel to Phase 2)

### 3.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| P3-T01 | Add TypeScript configuration | `tsconfig.json`, `vite.config.ts` | 30 min |
| P3-T02 | Create type definitions directory | `src/types/` | 15 min |
| P3-T03 | Define API response types | `src/types/api.ts` | 1 hour |
| P3-T04 | Define component prop types | `src/types/components.ts` | 1 hour |
| P3-T05 | Migrate utility files | `src/utils/*.ts` | 30 min |
| P3-T06 | Migrate API client | `src/api/*.ts` | 1 hour |
| P3-T07 | Migrate hooks | `src/hooks/*.ts` | 30 min |
| P3-T08 | Migrate components | `src/components/*.tsx` | 3 hours |
| P3-T09 | Migrate pages | `src/pages/*.tsx` | 3 hours |
| P3-T10 | Update imports and fix type errors | All files | 1 hour |

### 3.2 Implementation Details

#### P3-T01: TypeScript Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@/types/*": ["src/types/*"],
      "@/components/*": ["src/components/*"],
      "@/hooks/*": ["src/hooks/*"],
      "@/api/*": ["src/api/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

#### P3-T03: API Response Types

```typescript
// src/types/api.ts
export interface Player {
  id: number;
  name: string;
  mu: number;
  sigma: number;
  mmr: number;
  win_rate: number;
  total_games: number;
  wins: number;
  losses: number;
  terran_games: number;
  protoss_games: number;
  zerg_games: number;
  random_games: number;
  favorite_race: string;
  is_core_player: boolean;
  avg_overall_impact: number;
  avg_economic_score: number;
  avg_combat_score: number;
  avg_efficiency_score: number;
  created_at: string;
  last_played: string | null;
}

export interface Match {
  id: number;
  map_name: string;
  game_mode: string;
  played_at: string;
  duration_seconds: number;
  replay_hash: string;
  winner_team: number;
  team_1_win_probability: number;
  team_2_win_probability: number;
  players: MatchPlayer[];
}

export interface MatchPlayer {
  id: number;
  player_id: number;
  player_name: string;
  team: number;
  race: string;
  won: boolean;
  mmr_before: number;
  mmr_after: number;
  mmr_change: number;
}

export interface TeamSuggestion {
  team_1: TeamInfo;
  team_2: TeamInfo;
  win_probability_team_1: number;
  win_probability_team_2: number;
  fairness_rating: string;
  mmr_difference: number;
  impact_balance_score?: number;
}

export interface TeamInfo {
  players: Player[];
  avg_mmr: number;
  avg_impact?: number;
}

export interface ApiError {
  detail: string;
  code?: string;
}
```

#### P3-T04: Component Prop Types

```typescript
// src/types/components.ts
import type { Player, Match, TeamSuggestion } from './api';

export interface PlayerCardProps {
  player: Player;
  isSelected?: boolean;
  onSelect?: (player: Player) => void;
  showStats?: boolean;
}

export interface TacticalCardProps {
  variant?: 'primary' | 'secondary' | 'accent';
  glow?: boolean;
  children: React.ReactNode;
}

export interface TeamDisplayProps {
  team: TeamInfo;
  teamNumber: 1 | 2;
  winProbability: number;
}

export interface WinProbabilityDisplayProps {
  team1Probability: number;
  team2Probability: number;
  size?: 'sm' | 'md' | 'lg';
}
```

### 3.3 Migration Order

1. **Infrastructure**: `tsconfig.json`, `vite.config.ts`
2. **Types**: `src/types/` (API types, component props)
3. **Utilities**: `src/utils/formatting.ts`
4. **API Layer**: `src/api/client.ts`, `src/api/endpoints.ts`
5. **Hooks**: `src/hooks/useToast.ts`, `src/hooks/usePlayerSelection.ts`
6. **Components** (bottom-up):
   - Leaf components: `LoadingState`, `EmptyState`, `ErrorBoundary`
   - Chart components: `ImpactScoreRadar`, `DamageDistributionChart`
   - Feature components: `PlayerCard`, `TacticalCard`
7. **Pages** (bottom-up):
   - Simple pages first: `Players`, `UploadReplays`
   - Complex pages last: `TeamGenerator`, `MatchDetail`

### 3.4 Validation

```bash
# Type check passes
cd frontend && npx tsc --noEmit

# No .jsx files remain
find src -name "*.jsx" | wc -l  # Should be 0

# Build succeeds
npm run build
```

---

## Phase 4: Frontend Component Extraction (MEDIUM)

**Priority**: Medium
**Estimated Effort**: 1 day
**Dependencies**: Phase 3 complete

### 4.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| P4-T01 | Extract `TacticalBackground` component | `components/common/TacticalBackground.tsx` | 30 min |
| P4-T02 | Extract `WinProbabilityDisplay` component | `components/common/WinProbabilityDisplay.tsx` | 30 min |
| P4-T03 | Create `usePlayerSelection` hook | `hooks/usePlayerSelection.ts` | 1 hour |
| P4-T04 | Decompose `TeamGenerator` page | `pages/team-generator/*.tsx` | 2 hours |
| P4-T05 | Decompose `MatchDetail` page | `pages/match-detail/*.tsx` | 2 hours |
| P4-T06 | Update imports in affected files | Multiple files | 1 hour |

### 4.2 Implementation Details

#### P4-T01: TacticalBackground Component

```typescript
// src/components/common/TacticalBackground.tsx
import { Box, BoxProps } from '@chakra-ui/react';

interface TacticalBackgroundProps extends BoxProps {
  variant?: 'grid' | 'scanlines' | 'both';
  opacity?: number;
}

export const TacticalBackground: React.FC<TacticalBackgroundProps> = ({
  variant = 'both',
  opacity = 0.03,
  children,
  ...props
}) => {
  return (
    <Box position="relative" {...props}>
      {(variant === 'grid' || variant === 'both') && (
        <Box
          position="absolute"
          inset={0}
          opacity={opacity}
          bgImage="linear-gradient(rgba(0, 212, 255, 0.1) 1px, transparent 1px),
                   linear-gradient(90deg, rgba(0, 212, 255, 0.1) 1px, transparent 1px)"
          bgSize="20px 20px"
          pointerEvents="none"
        />
      )}
      {(variant === 'scanlines' || variant === 'both') && (
        <Box
          position="absolute"
          inset={0}
          opacity={opacity * 2}
          bgImage="repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 212, 255, 0.03) 2px,
            rgba(0, 212, 255, 0.03) 4px
          )"
          pointerEvents="none"
        />
      )}
      <Box position="relative" zIndex={1}>
        {children}
      </Box>
    </Box>
  );
};
```

#### P4-T03: usePlayerSelection Hook

```typescript
// src/hooks/usePlayerSelection.ts
import { useState, useCallback, useMemo } from 'react';
import type { Player } from '@/types/api';

interface UsePlayerSelectionOptions {
  maxPlayers?: number;
  minPlayers?: number;
}

interface UsePlayerSelectionReturn {
  selectedPlayers: Player[];
  togglePlayer: (player: Player) => void;
  isSelected: (player: Player) => boolean;
  clearSelection: () => void;
  canSelect: boolean;
  selectionCount: number;
}

export const usePlayerSelection = (
  options: UsePlayerSelectionOptions = {}
): UsePlayerSelectionReturn => {
  const { maxPlayers = Infinity, minPlayers = 0 } = options;
  const [selectedPlayers, setSelectedPlayers] = useState<Player[]>([]);

  const togglePlayer = useCallback((player: Player) => {
    setSelectedPlayers(prev => {
      const isCurrentlySelected = prev.some(p => p.id === player.id);
      if (isCurrentlySelected) {
        return prev.filter(p => p.id !== player.id);
      }
      if (prev.length >= maxPlayers) {
        return prev;
      }
      return [...prev, player];
    });
  }, [maxPlayers]);

  const isSelected = useCallback(
    (player: Player) => selectedPlayers.some(p => p.id === player.id),
    [selectedPlayers]
  );

  const clearSelection = useCallback(() => {
    setSelectedPlayers([]);
  }, []);

  const canSelect = selectedPlayers.length < maxPlayers;
  const selectionCount = selectedPlayers.length;

  return {
    selectedPlayers,
    togglePlayer,
    isSelected,
    clearSelection,
    canSelect,
    selectionCount,
  };
};
```

#### P4-T04: TeamGenerator Decomposition

**Current Structure** (988 lines in one file):
```
TeamGenerator.jsx (988 lines)
```

**Target Structure**:
```
pages/TeamGenerator/
├── index.tsx              # Main page (~100 lines)
├── TeamSelector.tsx       # Player selection UI (~150 lines)
├── TeamDisplay.tsx        # Team display (~100 lines)
├── BalanceResults.tsx     # Balance algorithm results (~150 lines)
└── TeamGeneratorContext.tsx # Shared state (~80 lines)
```

### 4.3 Validation

```bash
# All components render correctly
npm run dev  # Manual visual verification

# No component exceeds 300 lines
find src -name "*.tsx" -exec wc -l {} \; | awk '$1 > 300 {print}'  # Should be empty

# Imports work correctly
npm run build
```

---

## Phase 5: Design System Unification (MEDIUM)

**Priority**: Medium
**Estimated Effort**: 0.5 days
**Dependencies**: Phase 4 complete

### 5.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| P5-T01 | Create design tokens file | `src/theme/tokens.ts` | 30 min |
| P5-T02 | Create animations file | `src/theme/animations.ts` | 30 min |
| P5-T03 | Update theme index | `src/theme/index.ts` | 30 min |
| P5-T04 | Replace hardcoded colors | Multiple files | 2 hours |
| P5-T05 | Remove unused App.css | `src/App.css` | 5 min |

### 5.2 Implementation Details

#### P5-T01: Design Tokens

```typescript
// src/theme/tokens.ts
export const colors = {
  // Primary palette
  brand: {
    50: '#e6f7ff',
    100: '#bae7ff',
    500: '#00d4ff',
    600: '#00a3cc',
    900: '#003d4d',
  },
  // Accent colors
  accent: {
    500: 'rgba(0, 212, 255, 0.5)',
    600: 'rgba(0, 212, 255, 0.7)',
  },
  // Race colors
  race: {
    terran: '#4a9eff',
    protoss: '#ffd700',
    zerg: '#9d4edd',
    random: '#888888',
  },
  // Status colors
  status: {
    win: '#48bb78',
    loss: '#f56565',
    draw: '#ecc94b',
  },
  // Background colors
  bg: {
    card: 'rgba(26, 32, 44, 0.9)',
    overlay: 'rgba(0, 0, 0, 0.7)',
    tactical: 'rgba(0, 212, 255, 0.03)',
  },
};

export const spacing = {
  card: 4,
  section: 8,
  page: 12,
};

export const radii = {
  card: 'lg',
  button: 'md',
};
```

#### P5-T02: Animations

```typescript
// src/theme/animations.ts
import { keyframes } from '@chakra-ui/react';

export const scanlineAnimation = keyframes`
  0% { transform: translateY(0); }
  100% { transform: translateY(100%); }
`;

export const pulseGlow = keyframes`
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
`;

export const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
`;

export const animations = {
  scanline: `${scanlineAnimation} 8s linear infinite`,
  pulse: `${pulseGlow} 2s ease-in-out infinite`,
  fadeIn: `${fadeIn} 0.3s ease-out`,
};
```

### 5.3 Validation

```bash
# No hardcoded colors
grep -r "rgba(" src/components/ src/pages/ | grep -v "theme" | wc -l  # Should be 0
grep -r "#[0-9a-fA-F]" src/components/ src/pages/ | wc -l  # Should be 0

# App.css removed
ls src/App.css  # Should not exist
```

---

## Phase 6: Test Coverage (HIGH)

**Priority**: High
**Estimated Effort**: 1 day
**Dependencies**: Phases 1-5 complete

### 6.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| P6-T01 | Setup Vitest for frontend | `vitest.config.ts`, `package.json` | 30 min |
| P6-T02 | Add backend API endpoint tests | `tests/test_api/*.py` | 2 hours |
| P6-T03 | Add backend service tests | `tests/test_services/*.py` | 2 hours |
| P6-T04 | Add frontend component tests | `src/**/*.test.tsx` | 2 hours |
| P6-T05 | Add frontend hook tests | `src/hooks/*.test.ts` | 1 hour |
| P6-T06 | Verify coverage targets | Coverage reports | 30 min |

### 6.2 Implementation Details

#### P6-T01: Vitest Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/'],
      thresholds: {
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

#### P6-T02: Backend API Tests Example

```python
# tests/test_api/test_players.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestPlayersAPI:
    def test_get_players_returns_list(self):
        response = client.get("/players/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_player_not_found(self):
        response = client.get("/players/99999")
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_create_player_success(self):
        response = client.post("/players/", json={"name": "NewPlayer"})
        assert response.status_code == 201
        assert response.json()["name"] == "NewPlayer"

    def test_create_player_duplicate_name(self):
        client.post("/players/", json={"name": "DuplicateTest"})
        response = client.post("/players/", json={"name": "DuplicateTest"})
        assert response.status_code == 409
```

#### P6-T04: Frontend Component Test Example

```typescript
// src/components/PlayerCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { PlayerCard } from './PlayerCard';
import { theme } from '@/theme';

const mockPlayer = {
  id: 1,
  name: 'TestPlayer',
  mmr: 2000,
  win_rate: 0.65,
  total_games: 100,
  favorite_race: 'Terran',
  // ... other fields
};

const renderWithChakra = (component: React.ReactNode) => {
  return render(
    <ChakraProvider theme={theme}>
      {component}
    </ChakraProvider>
  );
};

describe('PlayerCard', () => {
  it('renders player name', () => {
    renderWithChakra(<PlayerCard player={mockPlayer} />);
    expect(screen.getByText('TestPlayer')).toBeInTheDocument();
  });

  it('shows MMR value', () => {
    renderWithChakra(<PlayerCard player={mockPlayer} />);
    expect(screen.getByText('2000')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const onSelect = vi.fn();
    renderWithChakra(<PlayerCard player={mockPlayer} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onSelect).toHaveBeenCalledWith(mockPlayer);
  });

  it('shows selected state', () => {
    renderWithChakra(<PlayerCard player={mockPlayer} isSelected />);
    expect(screen.getByRole('button')).toHaveAttribute('data-selected', 'true');
  });
});
```

### 6.3 Validation

```bash
# Backend coverage
cd backend && pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Frontend coverage
cd frontend && npm run test:coverage
# Verify: Coverage >= 80%
```

---

## Execution Checklist

### Phase 1 Checklist
- [ ] Create `tests/conftest.py` with fixtures
- [ ] Fix `test_player_creation`
- [ ] Fix `test_player_mmr_calculation`
- [ ] Fix `test_player_win_rate`
- [ ] Fix `test_conservative_rating`
- [ ] Create centralized MMR function
- [ ] Update all MMR references
- [ ] All 6 tests pass

### Phase 2 Checklist
- [ ] Create services directory
- [ ] Implement `ReplayService`
- [ ] Implement `RatingService`
- [ ] Implement `MatchService`
- [ ] Create `config.py`
- [ ] Create `exceptions.py`
- [ ] Refactor API routes
- [ ] Add rollback handling
- [ ] Fix CORS configuration

### Phase 3 Checklist
- [ ] Add `tsconfig.json`
- [ ] Create type definitions
- [ ] Migrate utilities
- [ ] Migrate API client
- [ ] Migrate hooks
- [ ] Migrate components
- [ ] Migrate pages
- [ ] Fix all type errors
- [ ] Build succeeds

### Phase 4 Checklist
- [ ] Extract `TacticalBackground`
- [ ] Extract `WinProbabilityDisplay`
- [ ] Create `usePlayerSelection`
- [ ] Decompose `TeamGenerator`
- [ ] Decompose `MatchDetail`
- [ ] Update all imports

### Phase 5 Checklist
- [ ] Create design tokens
- [ ] Create animations module
- [ ] Update theme index
- [ ] Replace all hardcoded colors
- [ ] Remove `App.css`

### Phase 6 Checklist
- [ ] Setup Vitest
- [ ] Add API endpoint tests
- [ ] Add service layer tests
- [ ] Add component tests
- [ ] Add hook tests
- [ ] Backend coverage >= 80%
- [ ] Frontend coverage >= 80%

---

## Risk Mitigation Actions

| Risk | Mitigation |
|------|------------|
| MMR formula change | Backup database, test with sample data first |
| TypeScript errors | Start with `strict: false`, enable incrementally |
| Component extraction bugs | Extract with identical render output first |
| Service extraction | Write tests before refactoring |

---

## Success Criteria Summary

| Metric | Target |
|--------|--------|
| Backend tests | 100% passing |
| Backend coverage | >= 80% |
| Frontend coverage | >= 80% |
| TypeScript files | 100% |
| Hardcoded colors | 0 |
| Functions >50 lines | 0 |
| Components >300 lines | 0 |
| Build status | Passing |
