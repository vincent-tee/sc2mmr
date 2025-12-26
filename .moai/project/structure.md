# SC2 MMR Tracker - Structure Documentation

## ARCHITECTURE OVERVIEW

**Architecture Type**: Modular Monolith (Dual-Service)
**Pattern**: Frontend SPA + Backend REST API
**Communication**: HTTP/REST with JSON payloads

```
+-------------------+     HTTP/REST     +-------------------+
|                   |    (Port 3000)    |                   |
|   React Frontend  | <---------------> |   FastAPI Backend |
|   (Vite + Chakra) |    Proxy to 8000  |   (Python + SQL)  |
|                   |                   |                   |
+-------------------+                   +-------------------+
                                               |
                                               v
                                        +-------------+
                                        |   SQLite    |
                                        |   Database  |
                                        +-------------+
```

---

## DIRECTORY STRUCTURE

```
sc2mmr/
+-- backend/                    # Python FastAPI backend
|   +-- app/                    # Main application package
|   |   +-- __init__.py
|   |   +-- main.py             # FastAPI app entry point
|   |   +-- database.py         # SQLAlchemy database setup
|   |   +-- models.py           # Database models (Player, Match, etc.)
|   |   +-- api/                # API route handlers
|   |   |   +-- __init__.py
|   |   |   +-- players.py      # Player endpoints
|   |   |   +-- replays.py      # Replay upload endpoints
|   |   |   +-- teams.py        # Team balancing endpoints
|   |   |   +-- impact.py       # Impact score endpoints
|   |   |   +-- adaptive.py     # Adaptive model endpoints
|   |   +-- rating_system.py    # TrueSkill integration
|   |   +-- balancer.py         # Team balancing algorithm
|   |   +-- replay_parser.py    # SC2Replay file parsing
|   |   +-- advanced_parser.py  # Extended replay metrics
|   |   +-- impact_service.py   # Player impact calculations
|   |   +-- playstyle_analyzer.py
|   |   +-- timing_analyzer.py
|   |   +-- damage_timeline.py
|   |   +-- match_commentary.py
|   |   +-- blended_rating.py
|   |   +-- online_learning.py
|   |   +-- auto_adaptive.py
|   |   +-- adaptive_model.py
|   |   +-- performance_rating.py
|   |   +-- rating_models.py
|   +-- migrations/             # Database migrations
|   +-- tests/                  # Backend tests
|   +-- batch_process_replays.py  # Bulk replay processor
|   +-- recalculate_ratings.py
|   +-- reset_database.py
|   +-- merge_players.py
|   +-- RECENCY_WEIGHTING.md    # Feature documentation
|
+-- frontend/                   # React frontend
|   +-- src/
|   |   +-- main.jsx            # App entry point
|   |   +-- App.jsx             # Root component with routing
|   |   +-- api/                # API client layer
|   |   |   +-- client.js       # Axios instance
|   |   |   +-- endpoints.js    # Backend API calls
|   |   +-- components/         # Reusable UI components
|   |   |   +-- Navigation.jsx
|   |   |   +-- PlayerCard.jsx
|   |   |   +-- TacticalCard.jsx
|   |   |   +-- HexagonalStat.jsx
|   |   |   +-- EmptyState.jsx
|   |   |   +-- LoadingState.jsx
|   |   |   +-- ErrorBoundary.jsx
|   |   |   +-- charts/         # Data visualization
|   |   |       +-- DamageTimelineChart.jsx
|   |   |       +-- DamageDistributionChart.jsx
|   |   |       +-- ImpactScoreRadar.jsx
|   |   |       +-- PlayerMetricsComparison.jsx
|   |   +-- pages/              # Route page components
|   |   |   +-- Home.jsx
|   |   |   +-- TeamGenerator.jsx     # PRIMARY feature
|   |   |   +-- UploadReplays.jsx
|   |   |   +-- Players.jsx
|   |   |   +-- PlayerDetail.jsx
|   |   |   +-- MatchHistory.jsx
|   |   |   +-- MatchDetail.jsx
|   |   |   +-- LineupPredictor.jsx
|   |   |   +-- AdaptiveModel.jsx
|   |   |   +-- RatingSystem.jsx
|   |   |   +-- FailedUploads.jsx
|   |   +-- hooks/              # Custom React hooks
|   |   |   +-- useToast.js
|   |   +-- theme/              # Chakra UI theme
|   +-- public/                 # Static assets
|   +-- vite.config.js          # Vite build configuration
|   +-- package.json
|   +-- eslint.config.js
|
+-- .moai/                      # MoAI-ADK configuration
|   +-- config/
|   |   +-- config.json
|   +-- project/
|       +-- product.md
|       +-- structure.md
|       +-- tech.md
|
+-- .git/                       # Git repository
+-- .github/                    # GitHub workflows (if present)
```

---

## CORE MODULES

### Backend Modules

| Module | Responsibility | Dependencies |
|--------|----------------|--------------|
| `main.py` | FastAPI app initialization, CORS, routers | All API modules |
| `models.py` | SQLAlchemy ORM models | database.py |
| `database.py` | Database connection and session management | SQLAlchemy |
| `rating_system.py` | TrueSkill rating calculations | trueskill, models |
| `balancer.py` | Team composition optimization | rating_system, models |
| `replay_parser.py` | SC2Replay file parsing | sc2reader |
| `advanced_parser.py` | Extended metrics extraction | replay_parser |
| `impact_service.py` | Player impact score calculation | models |

### Frontend Modules

| Module | Responsibility | Dependencies |
|--------|----------------|--------------|
| `App.jsx` | Root component, routing | React Router |
| `api/client.js` | HTTP client configuration | Axios |
| `api/endpoints.js` | Backend API integration | client.js |
| `pages/TeamGenerator.jsx` | Primary team balancing UI | API, Chakra UI |
| `pages/UploadReplays.jsx` | Replay upload interface | React Dropzone |
| `components/charts/*` | Data visualization | Recharts |

---

## DATA FLOW

### Replay Upload Flow

```
User uploads .SC2Replay
         |
         v
+------------------+     +------------------+     +------------------+
| Frontend         | --> | /replays/upload  | --> | replay_parser.py |
| (React Dropzone) |     | (FastAPI)        |     | (sc2reader)      |
+------------------+     +------------------+     +------------------+
                                                          |
                              +----------------------------+
                              |
                              v
                    +------------------+
                    | rating_system.py |
                    | (TrueSkill)      |
                    +------------------+
                              |
                              v
                    +------------------+
                    | models.py        |
                    | (SQLAlchemy)     |
                    +------------------+
                              |
                              v
                    +------------------+
                    | SQLite Database  |
                    +------------------+
```

### Team Balancing Flow

```
User selects players
         |
         v
+------------------+     +------------------+     +------------------+
| TeamGenerator    | --> | /teams/balance   | --> | balancer.py      |
| (Frontend)       |     | (FastAPI)        |     | (Algorithm)      |
+------------------+     +------------------+     +------------------+
                                                          |
                              +----------------------------+
                              |
                              v
                    +------------------+
                    | TrueSkill match  |
                    | quality calc     |
                    +------------------+
                              |
                              v
                    +------------------+
                    | Top N suggestions|
                    | returned to UI   |
                    +------------------+
```

---

## DATABASE SCHEMA

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `players` | Player profiles and ratings | id, name, mu, sigma, mmr, recency_weighted_mmr |
| `matches` | Match records | id, played_at, game_mode, map_name, replay_hash |
| `match_players` | Player-match relationships | match_id, player_id, team_number, won |
| `player_match_metrics` | Detailed performance data | match_player_id, damage_dealt, economic_score |
| `player_synergies` | Player pair statistics | player1_id, player2_id, games_together, synergy_score |
| `failed_uploads` | Error tracking for replays | filename, error_type, error_message |

### Key Relationships

```
Player (1) ---< (N) MatchPlayer (N) >--- (1) Match
                        |
                        v
               PlayerMatchMetrics (1:1)

Player (1) ---< (N) PlayerSynergy (N) >--- (1) Player
```

---

## INTEGRATION POINTS

### External Services

| Service | Purpose | Protocol |
|---------|---------|----------|
| None | Application is self-contained | N/A |

### Internal APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/players/` | GET | List all players |
| `/players/{id}` | GET | Get player details |
| `/players/rankings` | GET | Player leaderboard |
| `/replays/upload` | POST | Upload replay file |
| `/replays/matches` | GET | List all matches |
| `/replays/matches/{id}` | GET | Match details |
| `/teams/balance` | POST | Generate team suggestions |
| `/impact/player/{id}` | GET | Player impact metrics |

---

## NON-FUNCTIONAL REQUIREMENTS

### Performance
- **Target**: Team generation <5 seconds for 10 players
- **Current**: Achieves target through combinatorial optimization

### Reliability
- **Target**: 99% uptime for local deployment
- **Current**: Stateless backend, SQLite for persistence

### Scalability
- **Scope**: Single-instance deployment for casual groups
- **Capacity**: Supports 50+ players, 1000+ matches

### Security
- **CORS**: Configured for localhost development
- **Auth**: None (trusted local network assumed)
- **Data**: Local SQLite database

---

## OBSERVABILITY

### Logging
- Backend: Python logging to stdout
- Frontend: Browser console

### Monitoring
- Health check endpoint: `/health`
- Version check endpoint: `/version`

### Error Tracking
- Failed uploads tracked in `failed_uploads` table
- Error types categorized for analysis

---

## HISTORY

| Date | Change | Author |
|------|--------|--------|
| 2025-12-05 | Initial structure documentation created | project-manager |

---

*Document generated by MoAI-ADK Project Manager*
