# SPEC-PHASE2-001: Implementation Context

**This document provides existing code references and working examples for the implementing agent.**

---

## 1. Completed Backend Code Locations

### 1.1 Achievement System (Complete)

```
backend/app/models.py                    # Lines 478-1036: Achievement, PlayerAchievement, PlayerRivalry models + ACHIEVEMENT_DEFINITIONS
backend/app/api/achievements.py          # All achievement endpoints
backend/app/services/achievement_service.py  # Achievement calculation logic
```

### 1.2 Leaderboard System (Complete)

```
backend/app/api/leaderboard.py           # All leaderboard endpoints (already wired in main.py)
```

### 1.3 Main App Wiring

```python
# backend/app/main.py - Lines 13, 63-64
from .api import replays, players, teams, impact, adaptive, achievements, leaderboard
# ...
app.include_router(achievements.router)
app.include_router(leaderboard.router)
```

---

## 2. Database Tables (Already Created)

```sql
-- Tables exist in backend/data/sc2mmr.db
achievements           -- 33 rows (achievement definitions)
player_achievements    -- 180 rows (earned achievements)
player_rivalries       -- 0 rows (schema ready, needs data population)
```

---

## 3. Frontend Existing Components to Reuse

### 3.1 VSScreen Component
**File**: `frontend/src/components/VSScreen.tsx`
- Already handles player vs player display
- Extend for H2H stats

### 3.2 RankBadge Component
**File**: `frontend/src/components/RankBadge.tsx`
- Shows rank badges with animations
- Reference for achievement badge styling

### 3.3 HexagonalStat Component
**File**: `frontend/src/components/HexagonalStat.tsx`
- Hexagonal shape implementation
- Use as base for achievement badge shape

### 3.4 Design Tokens
**File**: `frontend/src/theme/tokens.ts`
- All color, spacing, typography tokens
- Race-specific colors (terran, protoss, zerg)

### 3.5 API Client Pattern
**File**: `frontend/src/api/client.ts` and `frontend/src/api/endpoints.ts`
- Existing API fetching pattern
- Follow same structure for new endpoints

---

## 4. Achievement Definitions (33 Total)

### Categories & Counts
| Category | Count | Examples |
|----------|-------|----------|
| milestone | 10 | First Blood, Centurion, Victory Tastes Sweet |
| streak | 6 | Getting Warm, On Fire, The Tilt Lord |
| combat | 5 | Damage Dealer, Nuke Launcher, Unit Slayer |
| teamwork | 4 | Dynamic Duo, Power Couple, Soulmates |
| variety | 4 | Terran Commander, Swarm Lord, One Trick Pony |
| meme | 2 | No Life, Glass Cannon |
| esports | 2 | Unstoppable, God Mode Activated |

### Rarities & Point Values
| Rarity | Point Range | Count |
|--------|-------------|-------|
| common | 5-15 | 8 |
| uncommon | 20-25 | 11 |
| rare | 40-50 | 9 |
| epic | 75-100 | 4 |
| legendary | 150 | 1 |

---

## 5. Test Commands

### Backend Health Check
```bash
cd backend
uvicorn app.main:app --reload --port 8000

# Test achievements
curl http://localhost:8000/achievements/leaderboard
curl http://localhost:8000/achievements/player/4

# Test leaderboard
curl http://localhost:8000/leaderboard/mmr
curl http://localhost:8000/leaderboard/duos
```

### Frontend Dev Server
```bash
cd frontend
npm run dev
# Opens at http://localhost:5173
```

---

## 6. Player Data Reference

### Top Players (by ID for testing)
| ID | Name | Games | MMR | Achievements |
|----|------|-------|-----|--------------|
| 4 | Stephan | 139 | 3455 | 24 badges |
| 6 | shunmanFan | 144 | 2365 | 21 badges |
| 1 | ChrisO | 141 | 2074 | 22 badges |
| 12 | DemonSlayer | 126 | 2072 | 20 badges |
| 5 | Tingmore | 106 | 2787 | 18 badges |

### Best Duos (for H2H testing)
| Player 1 | Player 2 | Wins Together | Games |
|----------|----------|---------------|-------|
| Stephan | shunmanFan | 47 | 72 |
| ChrisO | Tingmore | 32 | 53 |
| Tingmore | shunmanFan | 29 | 39 |

---

## 7. Route Configuration

### Add to `frontend/src/App.tsx`
```tsx
<Route path="/leaderboard" element={<Leaderboard />} />
<Route path="/achievements" element={<Achievements />} />
<Route path="/h2h" element={<HeadToHead />} />
<Route path="/h2h/:player1Id/:player2Id" element={<HeadToHead />} />
```

### Add to `frontend/src/components/Navigation.tsx`
```tsx
// Add nav items:
{ path: '/leaderboard', label: 'Leaderboard', icon: '🏆' },
{ path: '/achievements', label: 'Achievements', icon: '🎖️' },
{ path: '/h2h', label: 'Head to Head', icon: '⚔️' },
```

---

## 8. API Response Examples

### GET /achievements/player/4
```json
{
  "player_id": 4,
  "player_name": "Stephan",
  "total_achievements": 24,
  "total_points": 870,
  "achievements": [
    {
      "code": "HOT_STREAK_15",
      "name": "God Mode Activated",
      "description": "Win 15+ matches in a row",
      "flavor_text": "Is this legal? Someone check if they're smurfing!",
      "category": "esports",
      "rarity": "legendary",
      "icon": "👑",
      "points": 150,
      "earned_at": "2025-12-11T12:05:23"
    }
  ]
}
```

### GET /leaderboard/mmr
```json
[
  {
    "rank": 1,
    "player_id": 4,
    "name": "Stephan",
    "value": 3455.3,
    "secondary_value": 139,
    "extra_info": "78W 61L"
  },
  {
    "rank": 2,
    "player_id": 5,
    "name": "Tingmore",
    "value": 2786.9,
    "secondary_value": 106,
    "extra_info": "64W 42L"
  }
]
```

---

## 9. Head-to-Head Implementation Details

### Rivalry Calculation (implement in rivalry_service.py)

```python
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models import Player, Match, MatchPlayer, PlayerRivalry

class RivalryService:
    @staticmethod
    def calculate_all_rivalries(db: Session) -> int:
        """
        Scan all matches and populate player_rivalries table.
        Returns count of rivalries created/updated.
        """
        # Get all matches
        matches = db.query(Match).all()

        rivalry_data = {}  # (p1_id, p2_id) -> stats

        for match in matches:
            participants = match.participants
            team1 = [p for p in participants if p.team_number == 1]
            team2 = [p for p in participants if p.team_number == 2]

            # Each player on team1 vs each player on team2
            for p1 in team1:
                for p2 in team2:
                    # Ensure consistent ordering
                    pid1, pid2 = min(p1.player_id, p2.player_id), max(p1.player_id, p2.player_id)
                    key = (pid1, pid2)

                    if key not in rivalry_data:
                        rivalry_data[key] = {
                            'games': 0,
                            'p1_wins': 0,
                            'p2_wins': 0,
                            'last_match': match,
                            'mmr_swings': []
                        }

                    rivalry_data[key]['games'] += 1

                    # Determine winner
                    if p1.won:
                        if p1.player_id == pid1:
                            rivalry_data[key]['p1_wins'] += 1
                        else:
                            rivalry_data[key]['p2_wins'] += 1
                    else:
                        if p1.player_id == pid1:
                            rivalry_data[key]['p2_wins'] += 1
                        else:
                            rivalry_data[key]['p1_wins'] += 1

                    # Track MMR swing
                    swing = abs(p1.mu_after - p1.mu_before) * 40
                    rivalry_data[key]['mmr_swings'].append(swing)

                    if match.played_at > rivalry_data[key]['last_match'].played_at:
                        rivalry_data[key]['last_match'] = match

        # Save to database
        count = 0
        for (pid1, pid2), data in rivalry_data.items():
            rivalry = db.query(PlayerRivalry).filter(
                and_(PlayerRivalry.player1_id == pid1, PlayerRivalry.player2_id == pid2)
            ).first()

            if not rivalry:
                rivalry = PlayerRivalry(player1_id=pid1, player2_id=pid2)
                db.add(rivalry)

            rivalry.games_against = data['games']
            rivalry.player1_wins = data['p1_wins']
            rivalry.player2_wins = data['p2_wins']
            rivalry.avg_mmr_swing = sum(data['mmr_swings']) / len(data['mmr_swings']) if data['mmr_swings'] else 0
            rivalry.biggest_upset_mmr = max(data['mmr_swings']) if data['mmr_swings'] else 0
            rivalry.last_match_id = data['last_match'].id
            rivalry.last_match_at = data['last_match'].played_at
            rivalry.rivalry_score = RivalryService.calculate_score(
                data['games'], data['p1_wins'], data['p2_wins'],
                (datetime.utcnow() - data['last_match'].played_at).days
            )
            rivalry.updated_at = datetime.utcnow()
            count += 1

        db.commit()
        return count

    @staticmethod
    def calculate_score(games, p1_wins, p2_wins, recency_days):
        if games < 3:
            return 0.0
        volume = min(games * 2, 40)
        if p1_wins + p2_wins > 0:
            closeness = (min(p1_wins, p2_wins) / max(p1_wins, p2_wins)) * 40
        else:
            closeness = 0
        recency = 20 if recency_days <= 7 else (15 if recency_days <= 30 else (10 if recency_days <= 90 else 5))
        return volume + closeness + recency
```

---

## 10. Quick Implementation Checklist

### Backend (H2H only - ~1 hour)
- [ ] Create `backend/app/services/rivalry_service.py`
- [ ] Create `backend/app/api/headtohead.py`
- [ ] Add router to `backend/app/main.py`
- [ ] Run `POST /h2h/calculate-all` to populate
- [ ] Test all 4 endpoints

### Frontend (~3-4 hours)
- [ ] Create TypeScript types in `frontend/src/types/`
- [ ] Create API clients in `frontend/src/api/`
- [ ] `AchievementBadge.tsx` component
- [ ] `AchievementGrid.tsx` component
- [ ] `Achievements.tsx` page
- [ ] `LeaderboardTable.tsx` component
- [ ] `Leaderboard.tsx` page
- [ ] `RivalryMeter.tsx` component
- [ ] `HeadToHead.tsx` page
- [ ] Add routes to `App.tsx`
- [ ] Add nav items to `Navigation.tsx`
- [ ] Add achievements section to `PlayerDetail.tsx`

---

**End of CONTEXT.md**
