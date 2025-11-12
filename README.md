# SC2 MMR Tracker

A comprehensive web application to track StarCraft 2 replays for casual gaming groups, maintain player ratings using TrueSkill, analyze performance metrics, and balance teams for fair matches.

## Features

### Core Functionality
- **Team Balancing (PRIMARY FEATURE)**: Generate balanced team compositions based on MMR with match quality prediction
- **Replay Upload & Processing**: Parse SC2 replay files to extract match data and performance metrics
- **Player Tracking**: Unified TrueSkill MMR ratings across all game modes (3v3, 4v4, 5v5)
- **Performance Analytics**: Detailed economic, combat, and efficiency metrics for each player
- **Player Rankings**: View leaderboards and detailed player statistics
- **Match History**: Browse past games with full statistics
- **Outsider Calibration**: Quick setup for guest players
- **Modern Web Interface**: React-based frontend with dark gaming theme

### Key Highlights
- **Multiple Rating Models**: TrueSkill, Impact-based, Hybrid models, and Ensemble ratings
- **Recency Weighting**: Recent matches weighted more heavily (60-day half-life) for current skill estimate
- **Duplicate Detection**: SHA256 hashing prevents double-counting replays
- **Advanced Metrics**: Economic scores, combat effectiveness, timing analysis, player archetypes
- **Synergy Detection**: Identifies which players work well together
- **Skill Decay**: Models rating uncertainty for irregular play patterns
- **Race Statistics**: Track performance by race (Terran, Protoss, Zerg)
- **Drag & Drop Upload**: Bulk upload replays with real-time progress tracking

## Quick Start

### Prerequisites
- **Backend**: Python 3.9+, pip
- **Frontend**: Node.js 16+, npm

### 1. Backend Setup

```bash
# Clone the repository
git clone <repository-url>
cd sc2mmr/backend

# Install dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

### 3. Load Your Data

**Option A: Batch Process (Recommended for Initial Setup)**
```bash
cd backend
python batch_process_replays.py /path/to/your/replays --show-predictions --verbose
```

This will:
- Sort replays chronologically
- Process each replay in order
- Show predictions before each match
- Display rating evolution
- Track prediction accuracy (typically reaches 65-75% as ratings stabilize)

**Option B: Web Upload**
1. Open http://localhost:3000
2. Click "Upload Replays"
3. Drag and drop your .SC2Replay files
4. Files are processed automatically

### 4. Generate Balanced Teams

**Via Web Interface:**
1. Go to http://localhost:3000/balance
2. Select players for your session
3. Click "Generate Teams"
4. Review suggestions with match quality scores

**Via API:**
```bash
curl -X POST "http://localhost:8000/teams/balance" \
  -H "Content-Type: application/json" \
  -d '{
    "player_ids": [1, 2, 3, 4, 5, 6],
    "num_suggestions": 5
  }'
```

## Project Structure

```
sc2mmr/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── models.py          # Database models
│   │   ├── database.py        # DB connection
│   │   ├── replay_parser.py   # SC2 replay parsing
│   │   ├── advanced_parser.py # Advanced metrics extraction
│   │   ├── rating_system.py   # TrueSkill + recency weighting
│   │   ├── rating_models.py   # Multi-model rating system
│   │   ├── balancer.py        # Team balancing logic
│   │   ├── impact_service.py  # Impact scores & synergies
│   │   ├── timing_analyzer.py # Player archetype detection
│   │   └── api/               # API endpoints
│   ├── data/                  # SQLite database (auto-created)
│   ├── batch_process_replays.py
│   └── requirements.txt
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── pages/             # Main routes
│   │   │   ├── Home.jsx
│   │   │   ├── TeamGenerator.jsx  # PRIMARY feature
│   │   │   ├── UploadReplays.jsx
│   │   │   ├── Players.jsx
│   │   │   └── MatchHistory.jsx
│   │   ├── components/        # Reusable components
│   │   ├── api/              # API client
│   │   └── theme/            # Chakra UI theme
│   ├── package.json
│   └── vite.config.js
├── README.md                   # This file
├── PROJECT_OVERVIEW.md         # Detailed technical documentation
├── SETUP.md                    # Detailed setup guide
├── IMPLEMENTATION_SUMMARY.md   # Feature summary
└── ADVANCED_FEATURES.md        # Advanced metrics documentation
```

## How It Works

### TrueSkill Rating System

The application uses Microsoft's TrueSkill algorithm to rate players:

- **mu (μ)**: Skill estimate (default: 25.0)
- **sigma (σ)**: Uncertainty (default: 8.333, decreases with games played)
- **MMR**: Conservative rating = μ - 3σ (used for balancing)

#### Why TrueSkill?
- Designed specifically for team-based games
- Handles rating uncertainty (important for irregular play)
- Better than Elo for multi-player team scenarios
- Unified rating across all game modes (3v3, 4v4, 5v5)

#### Skill Decay
- Sigma (uncertainty) increases over time without games
- Models skill deterioration from inactivity
- Default: 0.0833 increase per day inactive

#### Recency Weighting
- Recent matches weighted more heavily for current skill estimate
- 60-day half-life (configurable)
- Provides more accurate current skill level

### Team Balancing Algorithm

1. **Generate Combinations**: Calculate all possible team splits
2. **Predict Match Quality**: Use TrueSkill to assess balance
3. **Rank Suggestions**: Sort by match quality and MMR difference
4. **Return Top N**: Present best balanced options

Match quality ranges from 0-1:
- 0.9+: Excellent
- 0.75-0.9: Very Good
- 0.6-0.75: Good
- 0.4-0.6: Fair
- <0.4: Poor

### Advanced Performance Metrics

#### Impact Scoring
Each player receives scores (0-100) across multiple dimensions:
- **Economic Score** (30% weight): Resource collection, worker production, spending efficiency
- **Combat Score** (50% weight): Damage dealt, kills, army value destroyed
- **Efficiency Score** (20% weight): Resource usage, damage ratios, trade efficiency
- **Overall Impact**: Weighted combination identifying high-impact players

#### Player Archetypes
Automatically identifies playstyles:
- **Rush**: Heavy early aggression (<4 min)
- **Timing Attacker**: Mid-game power spikes (4-7 min)
- **Late Game**: Patient, economy-focused (10+ min)
- **All-In**: Single massive attack
- **Balanced**: Consistent pressure
- **Defender**: Reactive play

#### Synergy Detection
Identifies which players work well together:
- Win rate together (60% weight)
- Role complementarity (20% weight)
- Performance consistency (20% weight)
- Synergy scores from 0-100

## API Documentation

### Main Endpoints

#### Replays
- `POST /replays/upload` - Upload and process a .SC2Replay file
- `POST /replays/upload-advanced` - Upload with full metrics extraction
- `GET /replays/matches` - Get list of matches
- `GET /replays/matches/{match_id}` - Get detailed match information

#### Players
- `GET /players/` - Get all players
- `GET /players/rankings` - Get player rankings by MMR
- `GET /players/{player_id}` - Get detailed player information
- `POST /players/` - Create a new player
- `POST /players/calibrate` - Calibrate a new outsider player

#### Teams (PRIMARY FEATURE)
- `POST /teams/balance` - Generate balanced team suggestions
- `POST /teams/quick-balance` - Get single best team composition
- `POST /teams/balance-with-model` - Balance using specific rating model
- `POST /teams/compare-models` - Compare all rating models

#### Impact & Synergies
- `GET /impact/players` - Rank players by impact scores
- `GET /impact/players/{id}/matches` - Detailed match history with metrics
- `GET /impact/players/{id}/synergies` - Player's best partners
- `GET /impact/synergies/top` - Top synergies across all players
- `GET /impact/leaderboard/{category}` - Category-specific rankings

### Example: Balance Teams

```bash
curl -X POST "http://localhost:8000/teams/balance" \
  -H "Content-Type: application/json" \
  -d '{
    "player_ids": [1, 2, 3, 4, 5, 6],
    "num_suggestions": 5
  }'
```

Response:
```json
[
  {
    "team_1": {
      "players": [
        {"id": 1, "name": "Player1", "mmr": 15.2},
        {"id": 3, "name": "Player3", "mmr": 12.8},
        {"id": 5, "name": "Player5", "mmr": 11.5}
      ],
      "total_mmr": 39.5,
      "avg_mmr": 13.17
    },
    "team_2": {
      "players": [
        {"id": 2, "name": "Player2", "mmr": 14.1},
        {"id": 4, "name": "Player4", "mmr": 13.0},
        {"id": 6, "name": "Player6", "mmr": 12.3}
      ],
      "total_mmr": 39.4,
      "avg_mmr": 13.13
    },
    "mmr_difference": 0.1,
    "match_quality": 0.92,
    "win_probability_team_1": 0.502,
    "win_probability_team_2": 0.498,
    "fairness_rating": "Excellent"
  }
]
```

## Frontend Features

### Team Generator (PRIMARY FEATURE)
- Quick, intuitive player selection interface
- Generate multiple balanced team suggestions
- View win probabilities and fairness ratings
- Export team compositions
- Optimized for <30 second team generation

### Upload Replays
- Drag-and-drop interface for bulk uploads
- Real-time progress tracking
- Duplicate detection with friendly messages
- Batch processing (5 files at a time)
- Retry failed uploads

### Players Dashboard
- Grid view of all players
- Search and sort functionality
- Player cards with MMR, race, and statistics
- Click to view detailed profiles

### Match History
- List of all recorded matches
- Filter and sort options
- Detailed match results

### Technology Stack
- React 18 with Vite
- Chakra UI v2 (dark gaming theme)
- React Query for API state management
- React Router v6
- React Dropzone for file uploads

## Database Schema

### Player
- Identity: ID, Name, created_at, last_played
- TrueSkill: mu, sigma, recency_weighted_mmr
- Statistics: total_games, wins, losses
- Race stats: terran_games, protoss_games, zerg_games
- Impact scores: economic, combat, efficiency, overall
- Archetype: primary_archetype, avg_aggression_score

### Match
- ID, played_at, game_mode, map_name, duration_seconds
- replay_file_path, replay_hash (for duplicate detection)

### MatchPlayer
- Links players to matches
- team_number, race, won
- Rating snapshots: mu_before, sigma_before, mu_after, sigma_after

### PlayerMatchMetrics
- Detailed per-match performance data
- Economic, combat, timing, and mechanics metrics
- Impact scores and archetype data

### PlayerSynergies
- Player pair performance tracking
- Games together, win rate, synergy scores

## Development Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Project structure
- [x] SC2 replay parser
- [x] Database models
- [x] TrueSkill integration
- [x] FastAPI backend
- [x] Team balancing algorithm

### Phase 2: API Endpoints ✅
- [x] Replay upload (basic & advanced)
- [x] Player statistics
- [x] Team balancing
- [x] Outsider calibration
- [x] Impact & synergy endpoints

### Phase 3: Frontend ✅
- [x] React-based web UI
- [x] Replay upload interface
- [x] Player dashboard
- [x] Team balancer UI
- [x] Match history visualization
- [x] Dark gaming theme

### Phase 4: Advanced Features ✅
- [x] Advanced metrics extraction
- [x] Multiple rating models
- [x] Recency weighting
- [x] Player archetype detection
- [x] Synergy detection
- [x] Batch replay processor

### Phase 5: Future Enhancements
- [ ] Auto-scan replay folder
- [ ] Performance trends graphs
- [ ] Export/import functionality
- [ ] Map-specific ratings
- [ ] Race matchup considerations
- [ ] Build order analysis
- [ ] Discord/Slack integration

## Technical Details

### Backend Dependencies
- **FastAPI**: Modern async web framework
- **SQLAlchemy**: ORM for database operations
- **sc2reader**: SC2 replay file parsing
- **trueskill**: TrueSkill rating algorithm
- **uvicorn**: ASGI server

### Frontend Dependencies
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Chakra UI v2**: Component library
- **React Query**: API state management
- **React Router v6**: Client-side routing
- **Axios**: HTTP client

### Database
- SQLite for simplicity (suitable for casual groups)
- Auto-creates on first run
- Located at `backend/data/sc2mmr.db`

### Replay Parsing
- Uses sc2reader library
- Extracts: players, races, teams, results, map, duration
- Advanced metrics: economic, combat, timing data
- Validates team sizes and game results
- SHA256 hash prevents duplicate uploads

## Usage Tips

### Initial Setup
1. Install backend and frontend dependencies
2. Start both servers
3. Batch process historical replays to establish baseline ratings
4. Upload new replays after each session

### Regular Sessions
1. Upload replays after each session (via web or batch)
2. View updated rankings
3. Use team balancer before next session
4. Track player improvement over time

### Balancing Teams
1. Select all available players for the session
2. Review top 3-5 suggestions
3. Consider match quality score (aim for 0.75+)
4. Pick teams with ~50% win probability for both sides

### Handling Outsiders
1. Use `/players/calibrate` endpoint or web interface
2. Select a core player with similar skill
3. Outsider gets similar rating with higher uncertainty
4. Rating adjusts quickly with first few games

## Performance

### Processing Speed
- Basic replay parsing: ~50-100ms per replay
- Advanced parsing: ~200-500ms per replay
- Batch of 100 replays: ~30-60 seconds

### Team Balancing
- 6 players (3v3): ~5ms (20 combinations)
- 8 players (4v4): ~20ms (70 combinations)
- 10 players (5v5): ~100ms (252 combinations)

### Storage
- Per match: ~2KB (basic) or ~5KB (advanced with metrics)
- 1000 matches: ~5MB database size

## Troubleshooting

### Backend Issues
- **Module not found**: Ensure dependencies installed in `backend/` directory
- **Database errors**: Delete `backend/data/sc2mmr.db` to reset (WARNING: loses all data)
- **Replay parsing errors**: Some replays may be corrupted or non-standard game modes

### Frontend Issues
- **CORS errors**: Ensure backend has CORS enabled for `http://localhost:3000`
- **API connection failed**: Verify backend is running on port 8000
- **Empty pages**: Upload some replay files first

### General Tips
- Need at least 5-10 games per player for ratings to stabilize
- Watch prediction accuracy - should reach 60-70% as ratings improve
- Process replays chronologically for most accurate rating evolution

## Documentation

- **README.md** (this file): Main project overview and quick start
- **PROJECT_OVERVIEW.md**: Comprehensive technical documentation
- **SETUP.md**: Detailed setup guide and troubleshooting
- **IMPLEMENTATION_SUMMARY.md**: Complete feature list and use cases
- **ADVANCED_FEATURES.md**: Deep dive into metrics and algorithms

## Contributing

This is a personal project for a casual gaming group, but suggestions and improvements are welcome!

## License

MIT License - feel free to use and modify for your own gaming groups.

## Acknowledgments

- Microsoft Research for the TrueSkill algorithm
- sc2reader library maintainers
- FastAPI framework
- React and Chakra UI communities
