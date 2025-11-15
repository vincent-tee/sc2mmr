# SC2 MMR Tracker - Complete Guide

> **Quick Links:**
> [Setup](#setup) | [Features](#features) | [API Reference](#api-reference) | [Technical Details](#technical-details) | [Troubleshooting](#troubleshooting)

---

## Overview

A comprehensive StarCraft 2 replay analysis and team balancing system for casual gaming groups (6-12 players). The **primary feature** is generating balanced team compositions using TrueSkill ratings and advanced performance metrics.

### Tech Stack
- **Backend**: Python 3.9+, FastAPI, SQLite, sc2reader, TrueSkill
- **Frontend**: React 18, Vite, Chakra UI v2, React Query
- **Database**: SQLite (auto-created at `backend/data/sc2mmr.db`)

---

## Setup

### Prerequisites
- Python 3.9+ and pip
- Node.js 16+ and npm

### Backend Installation

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Frontend Installation

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend available at: http://localhost:3000

### Load Replay Data

**Option A: Batch Processing (Recommended)**
```bash
cd backend
python batch_process_replays.py /path/to/replays --show-predictions --verbose
```

This processes replays chronologically, showing:
- Predictions before each match
- Rating evolution over time
- Final rankings and prediction accuracy

**Option B: Web Upload**
1. Open http://localhost:3000
2. Navigate to "Upload Replays"
3. Drag and drop .SC2Replay files
4. Files process automatically

---

## Features

### Core Functionality

#### 1. **Team Balancing** (PRIMARY FEATURE)
- Generates balanced team compositions based on MMR
- Predicts win probability for both teams
- Match quality scoring (0-1, higher = more balanced)
- Multiple suggestions with fairness ratings

#### 2. **Rating System**
- **TrueSkill**: Bayesian skill rating for team games
- **Recency Weighting**: 60-day half-life weights recent matches more heavily
- **Skill Decay**: Uncertainty increases for inactive players
- **Unified MMR**: Same rating across 3v3, 4v4, 5v5

#### 3. **Performance Metrics**
- **Economic**: Resources collected, worker production, spending efficiency
- **Combat**: Damage dealt/taken, kills, army value destroyed
- **Efficiency**: Resource usage, damage ratios, trade efficiency
- **Impact Scores**: 0-100 scores combining all metrics

#### 4. **Player Analysis**
- **Archetypes**: Rush, Timing Attacker, Late Game, All-In, Balanced, Defender
- **Aggression Score**: 0-100 quantifying playstyle
- **Role Detection**: Economy specialist vs Combat specialist
- **Timing Patterns**: First damage, expansion timings, attack windows

#### 5. **Synergy Detection**
- Identifies which players work well together
- Win rate analysis (60% weight)
- Role complementarity (20% weight)
- Performance consistency (20% weight)
- Synergy scores: 0-100 (80+ = excellent)

#### 6. **Replay Processing**
- SC2 replay parsing (all expansions supported)
- Duplicate detection via SHA256 hashing
- Advanced metrics extraction from tracker events
- Failed upload tracking with manual winner selection

---

## API Reference

### Base URL
`http://localhost:8000`

### Replays

#### Upload Replay (Basic)
```http
POST /replays/upload
Content-Type: multipart/form-data

file: replay.SC2Replay
```

#### Upload Replay (Advanced - Recommended)
```http
POST /replays/upload-advanced
Content-Type: multipart/form-data

file: replay.SC2Replay
```
Extracts full performance metrics, impact scores, and synergies.

#### List Matches
```http
GET /replays/matches?limit=50&offset=0
```

#### Get Match Details
```http
GET /replays/matches/{match_id}
```

#### Get Failed Uploads
```http
GET /replays/failed-uploads?limit=50&error_type=winner_determination
```

#### Manual Winner Selection
```http
POST /replays/failed-uploads/{upload_id}/set-winner
Content-Type: application/json

{
  "winner_team": 1
}
```

### Players

#### List All Players
```http
GET /players/?core_only=true
```

#### Get Rankings
```http
GET /players/rankings?min_games=5&core_only=true
```

#### Get Player Details
```http
GET /players/{player_id}
```

#### Create Player
```http
POST /players/
Content-Type: application/json

{
  "name": "PlayerName",
  "is_core_player": true
}
```

#### Calibrate Outsider
```http
POST /players/calibrate
Content-Type: application/json

{
  "name": "GuestPlayer",
  "similar_to_player_id": 5
}
```

### Team Balancing

#### Balance Teams
```http
POST /teams/balance
Content-Type: application/json

{
  "player_ids": [1, 2, 3, 4, 5, 6],
  "num_suggestions": 5,
  "game_mode": "3v3"
}
```

Response includes:
- Multiple team compositions
- Match quality scores
- Win probabilities
- Fairness ratings

#### Quick Balance
```http
POST /teams/quick-balance
Content-Type: application/json

{
  "player_ids": [1, 2, 3, 4, 5, 6]
}
```
Returns single best team split.

#### Compare Rating Models
```http
POST /teams/compare-models
Content-Type: application/json

{
  "player_ids": [1, 2, 3, 4, 5, 6]
}
```
Shows how all 8 rating models would balance the teams.

### Impact & Synergies

#### Get Impact Rankings
```http
GET /impact/players?limit=20&sort_by=combat&min_games=5
```
Sort options: `overall`, `economic`, `combat`, `efficiency`

#### Get Player Match History
```http
GET /impact/players/{player_id}/matches?limit=20
```

#### Get Player Synergies
```http
GET /impact/players/{player_id}/synergies?min_games=3
```

#### Get Top Synergies
```http
GET /impact/synergies/top?min_games=5&limit=10
```

#### Category Leaderboards
```http
GET /impact/leaderboard/{category}?min_games=5&limit=10
```
Categories: `economic`, `combat`, `efficiency`, `overall`

---

## Technical Details

### Database Schema

#### players
- Identity: id, name, created_at, last_played, is_core_player
- TrueSkill: mu, sigma, recency_weighted_mmr
- Statistics: total_games, wins, losses
- Race stats: terran_games, protoss_games, zerg_games
- Impact scores: avg_economic_score, avg_combat_score, avg_efficiency_score, avg_overall_impact
- Archetype: primary_archetype, avg_aggression_score

#### matches
- id, played_at, game_mode, map_name, duration_seconds
- replay_file_path, replay_hash (SHA256 for duplicates)
- predicted_team1_win_prob, predicted_team2_win_prob

#### match_players
- match_id, player_id, team_number, race, won
- Rating snapshots: mu_before, sigma_before, mu_after, sigma_after

#### player_match_metrics
- Economic: total_resources_collected, avg_workers, peak_workers, avg_spending_quotient
- Combat: damage_dealt, damage_taken, units_killed, units_lost, army_value_killed/lost
- Timing: first_damage_second, peak_army_second, expansion_timings
- Impact: economic_score, combat_score, efficiency_score, overall_impact

#### player_synergies
- player_1_id, player_2_id, games_together, wins_together, synergy_score

### Rating Systems

#### TrueSkill Parameters
```python
mu = 25.0              # Initial skill estimate
sigma = 8.333          # Initial uncertainty
beta = 4.166           # Skill class width
tau = 0.0833           # Dynamics factor (skill change per day)
```

**MMR Calculation:**
```
MMR = mu - (3 * sigma)
```
This is a conservative estimate (99.7% confidence).

#### Recency Weighting
Exponential decay with 60-day half-life:
```
weight = 0.5^(days_ago / 60)
recency_weighted_mmr = Σ(MMR_i × weight_i) / Σ(weight_i)
```

#### Available Rating Models
1. **trueskill** - Pure win/loss TrueSkill
2. **impact** - 100% performance metrics
3. **hybrid_balanced** - 50% TrueSkill, 50% Impact
4. **hybrid_skill_heavy** - 70% TrueSkill, 30% Impact
5. **hybrid_impact_heavy** - 30% TrueSkill, 70% Impact
6. **impact_combat** - 100% combat score only
7. **impact_economic** - 100% economic score only
8. **ensemble** - Optimized weighted combination

### Impact Scoring

#### Formula
```python
overall_impact = (
    0.30 * economic_score +
    0.50 * combat_score +
    0.20 * efficiency_score
)
```

#### Component Calculations
- **Economic**: Resources, workers, spending (normalized 0-100)
- **Combat**: Damage dealt, kills, army value (normalized 0-100)
- **Efficiency**: Ratios and trade efficiency (normalized 0-100)

### Synergy Calculation
```python
expected_win_rate = (player1_win_rate + player2_win_rate) / 2
actual_win_rate = wins_together / games_together
synergy_score = (actual - expected) / 0.5 * 100  # Normalized 0-100
```

### Team Balancing Algorithm
1. Generate all possible team splits (combinations)
2. For each split, calculate TrueSkill match quality
3. Match quality = probability of draw (0-1, higher = more balanced)
4. Sort by quality and return top N suggestions

### Archetype Detection
```python
if avg_first_damage_timing < 240s:  # < 4 min
    archetype = "Rush"
elif avg_first_damage_timing < 420s:  # 4-7 min
    archetype = "Timing Attacker"
elif avg_first_damage_timing < 600s:  # 7-10 min
    archetype = "Mid Game"
else:
    archetype = "Late Game"
```

---

## Advanced Setup

### Self-Improving Adaptive System

For groups with 150+ replays, enable the adaptive model system that automatically optimizes metric weights.

#### Phase 1: Enable Log-Only Monitoring

1. **Add database tables** (if not exists):
```bash
cd backend
python3 - <<'EOF'
from app.database import engine
from app.online_learning import ModelVersion, PredictionLog, FeatureImportance, FeatureSuggestion
from app.models import Base

ModelVersion.__table__.create(bind=engine, checkfirst=True)
PredictionLog.__table__.create(bind=engine, checkfirst=True)
FeatureImportance.__table__.create(bind=engine, checkfirst=True)
FeatureSuggestion.__table__.create(bind=engine, checkfirst=True)
print("✓ Tables created")
EOF
```

2. **Check adaptive model suggestions**:
```bash
curl http://localhost:8000/api/adaptive/suggest-weights | jq
```

3. **Monitor online learning**:
```bash
curl http://localhost:8000/api/adaptive/model-performance | jq
```

#### Configuration
Adjust in `backend/app/auto_adaptive.py`:
```python
class AutoAdaptiveConfig:
    MATCHES_PER_OPTIMIZATION = 5  # Trigger every N matches
    MIN_MATCHES_FOR_FIRST_RUN = 50  # Minimum before first run
    ENABLED = True  # Toggle on/off
```

---

## Troubleshooting

### Backend Issues

**Module not found**
```bash
cd backend
pip install -r requirements.txt
```

**Database errors**
```bash
# Reset database (WARNING: loses all data)
rm backend/data/sc2mmr.db
# Restart server to recreate
```

**Schema migration errors** (`no such column: matches.predicted_team1_win_prob`)
```bash
# Run the migration script
cd backend
python3 migrate_predictions_simple.py
```
See [MIGRATION_PREDICTIONS.md](backend/MIGRATION_PREDICTIONS.md) for details.

**Replay parsing errors**
- Some replays may be corrupted or non-standard
- Check logs for specific error messages
- Batch processor skips invalid replays and continues

### Frontend Issues

**CORS errors**
- Ensure backend CORS is enabled for `http://localhost:3000`
- Check `backend/app/main.py` for CORS configuration

**API connection failed**
- Verify backend is running on port 8000
- Check browser console for error details

**Empty pages**
- Upload some replay files first
- Check that database has data

### Replay Upload Failures

**500 Internal Server Error**
- Check backend logs for detailed error
- Advanced features may fail but upload should still complete
- Errors are logged and don't block upload

**Winner determination failed**
- Some replays can't auto-determine winner (all players quit early)
- Check Failed Uploads page
- Use manual winner selection based on game stats

**Duplicate replay**
- Replay already processed (SHA256 match)
- Returns HTTP 409 with existing match ID
- Safe to ignore

### Performance Tips

- Need 5-10 games per player for ratings to stabilize
- Watch prediction accuracy - should reach 60-70% as ratings improve
- Process replays chronologically for most accurate rating evolution
- Use batch processor for large replay collections
- Advanced upload (`/upload-advanced`) extracts more metrics but is slower

---

## Common Operations

### Start Services
```bash
# Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev
```

### Process Replays in Batch
```bash
cd backend
python batch_process_replays.py "/path/to/replays" --show-predictions --verbose
```

### Check Rankings
```bash
curl http://localhost:8000/players/rankings?min_games=3 | python -m json.tool
```

### Balance Teams via API
```bash
curl -X POST "http://localhost:8000/teams/balance" \
  -H "Content-Type: application/json" \
  -d '{"player_ids": [1,2,3,4,5,6], "num_suggestions": 5}' \
  | python -m json.tool
```

### Production Build (Frontend)
```bash
cd frontend
npm run build    # Creates dist/
npm run preview  # Preview production build
```

---

## Project Structure

```
sc2mmr/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── models.py               # Database models
│   │   ├── database.py             # DB connection
│   │   ├── replay_parser.py        # Basic replay parsing
│   │   ├── advanced_parser.py      # Detailed metrics extraction
│   │   ├── rating_system.py        # TrueSkill + recency weighting
│   │   ├── balancer.py             # Team balancing
│   │   ├── impact_service.py       # Impact scores & synergies
│   │   └── api/                    # API endpoints
│   ├── data/                       # SQLite database
│   └── batch_process_replays.py    # Batch processor
├── frontend/
│   ├── src/
│   │   ├── pages/                  # Main routes
│   │   ├── components/             # Reusable components
│   │   ├── api/                    # API client
│   │   └── theme/                  # Chakra UI theme
│   └── package.json
└── GUIDE.md                        # This file
```

---

## License

MIT License - feel free to use and modify for your own gaming groups.

---

## Acknowledgments

- Microsoft Research for the TrueSkill algorithm
- sc2reader library maintainers
- FastAPI, React, and Chakra UI communities
