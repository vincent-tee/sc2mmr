# SPEC-PHASE2-FRONTEND-HANDOVER: SC2 MMR Phase 2 - Frontend

## 1. Overview

This document serves as the specification for the **Frontend Implementation** of Phase 2 (Achievements, Leaderboard, Head-to-Head). The backend implementation is complete and verified.

## 2. API Reference (Backend Ready)

The following endpoints are fully implemented and tested in `backend/`:

### 2.1 Head-to-Head (HTH)
Base URL: `/h2h`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/{player1_id}/{player2_id}` | Detailed comparison between two players. |
| GET | `/{player_id}/rivals` | Top rivals for a specific player. |
| GET | `/biggest-rivalries` | Server-wide most intense rivalries. |
| POST | `/calculate-all` | Trigger manual recalculation of all rivalries. |

### 2.2 Achievements (Existing)
Base URL: `/achievements`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/player/{id}` | Get player's achievements. |
| GET | `/all` | Get definitions of all achievements. |

### 2.3 Leaderboard (Existing)
Base URL: `/leaderboard`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mmr`, `/winrate`, `/games` | Various leaderboard categories. |

## 3. Frontend Requirements

### 3.1 Types
Create TypeScript interfaces matching the backend response models. Code locations:
- `backend/app/api/headtohead.py` (H2H models)
- `backend/app/models.py` (Achievement/Rivalry models)

Suggested file structure:
- `frontend/src/types/achievements.ts`
- `frontend/src/types/leaderboard.ts`
- `frontend/src/types/headtohead.ts`

### 3.2 Pages & Components

#### Head-to-Head Page (`/h2h`)
- **Route**: `/h2h` (selector) and `/h2h/:p1/:p2` (comparison)
- **Components**:
    - `RivalryMeter`: Visual gauge for rivalry score (0-100+) and intensity label (Casual/Competitive/Fierce/Epic).
    - `VSHeader`: Large avatars/names with VS graphic.
    - `StatComparison`: Side-by-side stats (Win Rate, MMR Swing, etc.).
    - `MatchHistory`: List of recent games between them.

#### Leaderboard Page (`/leaderboard`)
- **Route**: `/leaderboard`
- **Features**:
    - Tabbed navigation (MMR, Win Rate, Activity, Achievements).
    - `LeaderboardTable`: Reusable table component.
    - Highlight current user if logged in (optional).

#### Achievements Page (`/achievements`)
- **Route**: `/achievements`
- **Features**:
    - Grid of all possible achievements.
    - Filter by category (Milestone, Combat, Meme, etc.).
    - `AchievementBadge`: Hexagonal badge with icon, rarity color, and tooltip.

### 3.3 Design System
Use existing tokens in `frontend/src/theme/tokens.ts`.
- **Rarity Colors**: Define specific colors for Common, Rare, Epic, Legendary.
- **Race Colors**: Use standard Terran (Blue), Zerg (Purple), Protoss (Gold).

## 4. Implementation Steps

1.  **Generate Types**: Map Python Pydantic models to TypeScript interfaces.
2.  **API Client**: Create `headtohead.ts` using the existing `apiClient`.
3.  **Components**: Build atomic components (`AchievementBadge`, `RivalryMeter`).
4.  **Pages**: Assemble pages and wire up data fetching.
5.  **Navigation**: Add links to the main nav bar.

## 5. Testing
- Verify H2H page loads correctly with IDs `4` (Stephan) and `1` (ChrisO).
- Verify "Biggest Rivalries" list renders.
- Check responsive design on mobile.
