# SPEC-PHASE2-001: SC2 MMR Phase 2 - Achievements, Leaderboard & Head-to-Head

**Version**: 1.0.0
**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 4-6 hours

---

## 1. Overview

### 1.1 Purpose
Complete Phase 2 of the SC2 MMR tracking system by implementing the Head-to-Head rivalry system and all frontend components for Achievements, Leaderboard, and Head-to-Head features.

### 1.2 Background
Phase 1 delivered match prediction. Phase 2 backend for Achievements and Leaderboard is **complete and tested**. This SPEC covers the remaining work:
- Head-to-Head API (backend)
- All frontend components (3 major features)

### 1.3 Current State
| Component | Backend | Frontend |
|-----------|---------|----------|
| Achievements | ✅ Complete (10 endpoints) | ❌ Not started |
| Leaderboard | ✅ Complete (10 endpoints) | ❌ Not started |
| Head-to-Head | ❌ Not started | ❌ Not started |

---

## 2. Requirements

### 2.1 Head-to-Head Backend API

#### 2.1.1 Endpoints Required

```
GET /h2h/{player1_id}/{player2_id}    # Compare two specific players
GET /h2h/{player_id}/rivals           # Get player's top rivals
GET /h2h/biggest-rivalries            # Global most intense matchups
POST /h2h/calculate-all               # Backfill rivalry data from match history
```

#### 2.1.2 Data Model (Already Created)

```python
# In backend/app/models.py - PlayerRivalry class exists
class PlayerRivalry(Base):
    __tablename__ = "player_rivalries"

    player1_id: int          # Always smaller ID
    player2_id: int          # Always larger ID
    games_against: int       # Times on opposite teams
    player1_wins: int
    player2_wins: int
    avg_mmr_swing: float     # Average MMR change in their games
    biggest_upset_mmr: float # Largest upset between them
    last_match_id: int
    last_match_at: datetime
    rivalry_score: float     # Calculated intensity score
```

#### 2.1.3 Rivalry Score Formula

```python
def calculate_rivalry_score(games_against, player1_wins, player2_wins, recency_days):
    """
    Higher score = more intense rivalry

    Components:
    - Volume: More games = more rivalry
    - Closeness: 50-50 records are more intense than one-sided
    - Recency: Recent games boost the score
    """
    if games_against < 3:
        return 0.0

    # Volume component (0-40 points)
    volume_score = min(games_against * 2, 40)

    # Closeness component (0-40 points)
    # Perfect 50-50 = 40 points, one-sided = 0 points
    total = player1_wins + player2_wins
    if total > 0:
        win_ratio = min(player1_wins, player2_wins) / max(player1_wins, player2_wins)
        closeness_score = win_ratio * 40
    else:
        closeness_score = 0

    # Recency component (0-20 points)
    if recency_days <= 7:
        recency_score = 20
    elif recency_days <= 30:
        recency_score = 15
    elif recency_days <= 90:
        recency_score = 10
    else:
        recency_score = 5

    return volume_score + closeness_score + recency_score
```

#### 2.1.4 Response Schema

```typescript
// GET /h2h/{player1_id}/{player2_id}
interface HeadToHeadResponse {
  player1: {
    id: number;
    name: string;
    mmr: number;
    wins: number;
    favorite_race: string;
  };
  player2: {
    id: number;
    name: string;
    mmr: number;
    wins: number;
    favorite_race: string;
  };
  head_to_head: {
    total_games: number;
    player1_wins: number;
    player2_wins: number;
    win_rate_player1: number;
    last_match_date: string;
    avg_mmr_swing: number;
    rivalry_score: number;
    rivalry_intensity: "Casual" | "Competitive" | "Fierce" | "Epic";
  };
  recent_matches: Array<{
    match_id: number;
    date: string;
    winner_id: number;
    map_name: string;
    duration_seconds: number;
  }>;
}
```

---

### 2.2 Frontend: Achievement Components

#### 2.2.1 AchievementBadge Component

**File**: `frontend/src/components/AchievementBadge.tsx`

```typescript
interface AchievementBadgeProps {
  code: string;
  name: string;
  description: string;
  flavor_text?: string;
  icon: string;        // Emoji like "🔥" or "👑"
  rarity: AchievementRarity;
  category: AchievementCategory;
  points: number;
  earned?: boolean;
  earned_at?: string;
  showTooltip?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

type AchievementRarity = 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary' | 'mythic';
type AchievementCategory = 'milestone' | 'streak' | 'combat' | 'economic' | 'teamwork' | 'variety' | 'special' | 'meme' | 'esports';
```

**Rarity Color Scheme** (use design tokens):
```typescript
const RARITY_COLORS = {
  common: { bg: '#374151', border: '#6B7280', glow: 'none' },
  uncommon: { bg: '#065F46', border: '#10B981', glow: '0 0 10px #10B981' },
  rare: { bg: '#1E40AF', border: '#3B82F6', glow: '0 0 15px #3B82F6' },
  epic: { bg: '#5B21B6', border: '#8B5CF6', glow: '0 0 20px #8B5CF6' },
  legendary: { bg: '#92400E', border: '#F59E0B', glow: '0 0 25px #F59E0B' },
  mythic: { bg: '#831843', border: '#EC4899', glow: '0 0 30px #EC4899, 0 0 60px #EC4899' },
};
```

**Visual Requirements**:
- Hexagonal badge shape (like existing HexagonalStat)
- Icon (emoji) centered
- Glow effect based on rarity
- Grayscale + locked icon if not earned
- Hover tooltip with name, description, flavor text

#### 2.2.2 AchievementGrid Component

**File**: `frontend/src/components/AchievementGrid.tsx`

```typescript
interface AchievementGridProps {
  achievements: Achievement[];
  earnedIds: Set<string>;  // Set of earned achievement codes
  onBadgeClick?: (achievement: Achievement) => void;
  showLocked?: boolean;    // Show unearned achievements grayed out
  groupByCategory?: boolean;
}
```

#### 2.2.3 PlayerAchievements Section

**Add to**: `frontend/src/pages/PlayerDetail.tsx`

```typescript
// New section in player detail page
<section className="player-achievements">
  <h2>🎖️ Achievements ({earned.length}/{total})</h2>
  <div className="achievement-points">
    Total Points: {totalPoints}
  </div>
  <div className="featured-badge">
    {featuredAchievement && <AchievementBadge {...featuredAchievement} size="lg" />}
  </div>
  <AchievementGrid
    achievements={allAchievements}
    earnedIds={earnedCodes}
    groupByCategory={true}
  />
</section>
```

---

### 2.3 Frontend: Leaderboard Page

#### 2.3.1 Page Structure

**File**: `frontend/src/pages/Leaderboard.tsx`

```typescript
const LEADERBOARD_CATEGORIES = [
  { key: 'mmr', name: 'MMR Rankings', icon: '🏆' },
  { key: 'winrate', name: 'Win Rate', icon: '📈' },
  { key: 'games', name: 'Most Games', icon: '🎮' },
  { key: 'achievements', name: 'Achievement Points', icon: '🎖️' },
  { key: 'damage', name: 'Damage Kings', icon: '⚔️' },
  { key: 'kills', name: 'Unit Slayers', icon: '💀' },
  { key: 'winstreak', name: 'Best Win Streak', icon: '🔥' },
  { key: 'duos', name: 'Best Duos', icon: '🤝' },
];
```

#### 2.3.2 Components Needed

```typescript
// LeaderboardTable.tsx
interface LeaderboardTableProps {
  entries: LeaderboardEntry[];
  columns: ColumnConfig[];
  highlightPlayerId?: number;  // Highlight current user
}

// LeaderboardEntry type
interface LeaderboardEntry {
  rank: number;
  player_id: number;
  name: string;
  value: number;
  secondary_value?: number;
  extra_info?: string;
}

// DuoLeaderboardTable.tsx (special case for duos)
interface DuoLeaderboardEntry {
  rank: number;
  player1_id: number;
  player1_name: string;
  player2_id: number;
  player2_name: string;
  wins_together: number;
  games_together: number;
  win_rate: number;
  synergy_score: number;
}
```

#### 2.3.3 Visual Requirements

- Tab navigation for categories
- Animated rank changes (optional)
- Race icon next to player name
- Medal icons for top 3 (🥇🥈🥉)
- Click row to go to player detail
- Mobile responsive

---

### 2.4 Frontend: Head-to-Head Page

#### 2.4.1 Page Structure

**File**: `frontend/src/pages/HeadToHead.tsx`

**Route**: `/h2h/:player1Id/:player2Id` or `/h2h` (with player selector)

#### 2.4.2 Components

```typescript
// VSScreen.tsx (already exists - enhance it)
interface VSScreenProps {
  player1: PlayerSummary;
  player2: PlayerSummary;
  headToHead: HeadToHeadStats;
  showAnimation?: boolean;
}

// RivalryMeter.tsx (new)
interface RivalryMeterProps {
  score: number;           // 0-100
  intensity: string;       // "Casual" | "Competitive" | "Fierce" | "Epic"
  gamesPlayed: number;
}

// MatchHistoryList.tsx (new)
interface MatchHistoryListProps {
  matches: RecentMatch[];
  player1Id: number;
  player2Id: number;
}
```

#### 2.4.3 Player Selector

When navigating to `/h2h` without IDs:
- Show two dropdown selects
- "Compare" button
- Quick links to "Biggest Rivalries"

---

## 3. API Reference

### 3.1 Existing Endpoints (Backend Complete)

#### Achievements API
```
GET  /achievements/player/{player_id}?include_available=false
GET  /achievements/leaderboard?limit=20
GET  /achievements/recent?limit=20
GET  /achievements/rarest?limit=10
GET  /achievements/all?include_hidden=false
POST /achievements/init
POST /achievements/check/{player_id}?match_id=optional
POST /achievements/check-all
POST /achievements/player/{player_id}/feature/{achievement_code}
```

#### Leaderboard API
```
GET /leaderboard/categories
GET /leaderboard/mmr?limit=20&min_games=5
GET /leaderboard/winrate?limit=20&min_games=20
GET /leaderboard/games?limit=20
GET /leaderboard/achievements?limit=20
GET /leaderboard/damage?limit=20&min_games=10
GET /leaderboard/kills?limit=20&min_games=10
GET /leaderboard/winstreak?limit=20
GET /leaderboard/duos?limit=20&min_games=10&sort_by=wins
GET /leaderboard/race/{race}?limit=20&min_games=10
```

### 3.2 To Implement (Head-to-Head)

```
GET  /h2h/{player1_id}/{player2_id}
GET  /h2h/{player_id}/rivals?limit=10
GET  /h2h/biggest-rivalries?limit=20
POST /h2h/calculate-all
```

---

## 4. File Structure

### 4.1 Backend Files to Create

```
backend/app/api/headtohead.py           # H2H API endpoints
backend/app/services/rivalry_service.py # Rivalry calculation logic
```

### 4.2 Frontend Files to Create

```
frontend/src/pages/Leaderboard.tsx
frontend/src/pages/HeadToHead.tsx
frontend/src/pages/Achievements.tsx          # Full achievements catalog

frontend/src/components/AchievementBadge.tsx
frontend/src/components/AchievementGrid.tsx
frontend/src/components/LeaderboardTable.tsx
frontend/src/components/DuoLeaderboardTable.tsx
frontend/src/components/RivalryMeter.tsx
frontend/src/components/PlayerSelector.tsx

frontend/src/api/achievements.ts             # API client functions
frontend/src/api/leaderboard.ts
frontend/src/api/headtohead.ts

frontend/src/types/achievements.ts           # TypeScript types
frontend/src/types/leaderboard.ts
frontend/src/types/headtohead.ts
```

### 4.3 Frontend Files to Modify

```
frontend/src/App.tsx                    # Add routes
frontend/src/components/Navigation.tsx  # Add nav links
frontend/src/pages/PlayerDetail.tsx     # Add achievements section
```

---

## 5. Implementation Order

### Phase 2A: Head-to-Head Backend (1 hour)
1. Create `rivalry_service.py` with calculation logic
2. Create `headtohead.py` API endpoints
3. Wire router in `main.py`
4. Run `POST /h2h/calculate-all` to populate data
5. Test all endpoints

### Phase 2B: TypeScript Types & API Clients (30 min)
1. Create all type definitions
2. Create API client functions
3. Test with existing backend

### Phase 2C: Achievement Frontend (1.5 hours)
1. `AchievementBadge` component with rarity styling
2. `AchievementGrid` component
3. Add achievements section to `PlayerDetail.tsx`
4. Create standalone `Achievements.tsx` catalog page

### Phase 2D: Leaderboard Frontend (1.5 hours)
1. `LeaderboardTable` component
2. `DuoLeaderboardTable` component
3. `Leaderboard.tsx` page with tabs
4. Add to navigation

### Phase 2E: Head-to-Head Frontend (1.5 hours)
1. `RivalryMeter` component
2. `PlayerSelector` component
3. Enhance existing `VSScreen` component
4. `HeadToHead.tsx` page
5. Add to navigation

---

## 6. Testing Checklist

### Backend
- [ ] `GET /h2h/4/1` returns comparison (Stephan vs first player)
- [ ] `GET /h2h/4/rivals` returns Stephan's top rivals
- [ ] `GET /h2h/biggest-rivalries` returns sorted list
- [ ] Rivalry scores calculated correctly

### Frontend
- [ ] Achievement badges render with correct rarity colors
- [ ] Locked achievements show grayed out
- [ ] Leaderboard tabs switch correctly
- [ ] Player rows link to player detail
- [ ] H2H page loads with two players
- [ ] VS screen animates on load
- [ ] Mobile responsive on all pages

---

## 7. Sample Data Reference

### Current Achievement Leaders
| Rank | Player | Points | Badges |
|------|--------|--------|--------|
| 1 | Stephan | 870 | 24 |
| 2 | shunmanFan | 675 | 21 |
| 3 | ChrisO | 660 | 22 |

### Expected Top Rivalries
Based on synergy data, likely intense rivalries:
- Stephan vs shunmanFan (72 games together = many against too)
- ChrisO vs Tingmore (53 games together)
- ChrisO vs DemonSlayer (37 games together)

---

## 8. Design Tokens Reference

Use existing tokens from `frontend/src/theme/tokens.ts`:

```typescript
// Colors
colors.primary      // Main accent
colors.background   // Page background
colors.surface      // Card backgrounds

// Race colors (for badges)
colors.terran       // Blue
colors.protoss      // Gold
colors.zerg         // Purple

// Spacing
spacing.sm, spacing.md, spacing.lg

// Typography
fontSize.sm, fontSize.md, fontSize.lg
```

---

## 9. Notes for Implementation

1. **Reuse existing components**: `VSScreen`, `RankBadge`, `HexagonalStat` already exist
2. **Follow existing patterns**: Check `PlayerDetail.tsx` for API fetching patterns
3. **Use React Query or similar**: For data fetching if already in use
4. **Animation library**: Check if Framer Motion is available for badge animations
5. **Error handling**: Show loading states and error boundaries

---

**End of SPEC-PHASE2-001**
