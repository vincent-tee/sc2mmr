# SC2 MMR Tracker

A web application to track StarCraft 2 replays for a casual gaming group, maintain player ratings using TrueSkill, and balance teams for fair matches.

## Features

### Core Functionality
- **Replay Upload & Processing**: Parse SC2 replay files to extract match data
- **Player Tracking**: Unified TrueSkill MMR ratings across all game modes
- **Team Balancing**: Generate balanced team compositions based on MMR (PRIMARY FEATURE)
- **Player Rankings**: View leaderboards and detailed player statistics
- **Outsider Calibration**: Quick setup for guest players

### Key Highlights
- Supports 3v3, 4v4, and 5v5 game modes
- TrueSkill rating system handles team-based games naturally
- Skill decay modeling for irregular play patterns
- **Duplicate replay detection** (SHA256 hashing prevents double-counting)
- **Recency weighting** (recent matches weighted more heavily for current skill estimate)
- Race statistics tracking (Terran, Protoss, Zerg)
- Multiple rating models (TrueSkill, Impact, Hybrid, Ensemble)

## Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sc2mmr
   ```

2. **Install backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   cd backend
   python -m app.main
   ```

   Or using uvicorn directly:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## API Documentation

### Main Endpoints

#### Replays
- `POST /replays/upload` - Upload and process a .SC2Replay file
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

### Example Usage

#### 1. Upload a Replay
```bash
curl -X POST "http://localhost:8000/replays/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/replay.SC2Replay"
```

#### 2. View Player Rankings
```bash
curl -X GET "http://localhost:8000/players/rankings?min_games=5"
```

#### 3. Balance Teams (Most Important)
```bash
curl -X POST "http://localhost:8000/teams/balance" \
  -H "Content-Type: application/json" \
  -d '{
    "player_ids": [1, 2, 3, 4, 5, 6],
    "top_n": 5
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

#### 4. Calibrate New Outsider
```bash
curl -X POST "http://localhost:8000/players/calibrate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NewPlayer",
    "similar_to_player_id": 3
  }'
```

## How It Works

### TrueSkill Rating System

The application uses Microsoft's TrueSkill algorithm to rate players:

- **mu (μ)**: Skill estimate (default: 25.0)
- **sigma (σ)**: Uncertainty (default: 8.333, decreases with games played)
- **MMR**: Conservative rating = μ - 3σ (used for balancing)

#### Why TrueSkill?
- Designed for team-based games
- Handles rating uncertainty (important for irregular play)
- Better than Elo for multi-player team scenarios
- Unified rating across all game modes (3v3, 4v4, 5v5)

#### Skill Decay
- Sigma (uncertainty) increases over time without games
- Models skill deterioration from inactivity
- Default: 0.0833 increase per day inactive

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

## Project Structure

```
sc2mmr/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── models.py            # Database models
│   │   ├── database.py          # DB connection
│   │   ├── replay_parser.py     # SC2 replay parsing (sc2reader)
│   │   ├── rating_system.py     # TrueSkill integration
│   │   ├── balancer.py          # Team balancing logic
│   │   └── api/
│   │       ├── replays.py       # Replay endpoints
│   │       ├── players.py       # Player endpoints
│   │       └── teams.py         # Team balancing endpoints
│   ├── data/                    # SQLite database (auto-created)
│   ├── tests/                   # Unit tests (future)
│   └── requirements.txt         # Python dependencies
├── frontend/                    # Web frontend (future)
└── README.md
```

## Database Schema

### Player
- ID, Name
- TrueSkill: mu, sigma
- Statistics: total_games, wins, losses
- Race stats: terran_games, protoss_games, zerg_games, random_games
- Metadata: created_at, last_played, is_core_player

### Match
- ID, played_at, game_mode, map_name, duration_seconds
- replay_file_path, replay_hash (for duplicate detection)

### MatchPlayer
- Links players to matches
- team_number, race, won
- Rating snapshots: mu_before, sigma_before, mu_after, sigma_after

## Development Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Project structure
- [x] SC2 replay parser
- [x] Database models
- [x] TrueSkill integration
- [x] FastAPI backend
- [x] Team balancing algorithm

### Phase 2: API Endpoints ✅
- [x] Replay upload
- [x] Player statistics
- [x] Team balancing
- [x] Outsider calibration

### Phase 3: Frontend (Future)
- [ ] React-based web UI
- [ ] Replay upload interface
- [ ] Player dashboard
- [ ] Team balancer UI
- [ ] Match history visualization

### Phase 4: Enhancements (Future)
- [ ] Auto-scan replay folder
- [ ] Advanced analytics
- [ ] Race matchup considerations
- [ ] Performance trends graphs
- [ ] Export/import functionality

## Technical Details

### Dependencies
- **FastAPI**: Modern web framework
- **SQLAlchemy**: ORM for database operations
- **sc2reader**: SC2 replay file parsing
- **trueskill**: TrueSkill rating algorithm
- **uvicorn**: ASGI server

### Database
- SQLite for simplicity (suitable for casual group)
- Auto-creates on first run
- Located at `backend/data/sc2mmr.db`

### Replay Parsing
- Uses sc2reader library
- Extracts: players, races, teams, results, map, duration
- Validates team sizes and game results
- SHA256 hash prevents duplicate uploads

## Usage Tips

1. **Initial Setup**
   - Create core players manually or let them be auto-created from first replay
   - Upload historical replays to establish baseline ratings

2. **Regular Sessions**
   - Upload replays after each session
   - View updated rankings
   - Use team balancer before next session

3. **Balancing Teams**
   - Select all available players for the session
   - Review top 3-5 suggestions
   - Consider match quality score (aim for 0.75+)
   - Pick teams with ~50% win probability for both sides

4. **Handling Outsiders**
   - Use `/players/calibrate` endpoint
   - Select a core player with similar skill
   - Outsider gets similar rating with higher uncertainty
   - Rating adjusts quickly with first few games

## API Interactive Documentation

Visit `http://localhost:8000/docs` for interactive API documentation where you can:
- Explore all endpoints
- Try API calls directly in browser
- View request/response schemas
- See example payloads

## Contributing

This is a personal project for a casual gaming group, but suggestions and improvements are welcome!

## License

MIT License - feel free to use and modify for your own gaming groups.

## Acknowledgments

- Microsoft Research for the TrueSkill algorithm
- sc2reader library maintainers
- FastAPI framework
