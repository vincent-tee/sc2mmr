# SC2 MMR Tracker

A comprehensive web application to track StarCraft 2 replays for casual gaming groups, maintain player ratings using TrueSkill, analyze performance metrics, and balance teams for fair matches.

> **📖 [Read the Complete Guide](GUIDE.md)** for full documentation including setup, features, API reference, and troubleshooting.

## Features

- **Team Balancing** (PRIMARY): Generate balanced team compositions based on MMR with match quality prediction
- **Replay Processing**: Parse SC2 replay files to extract match data and performance metrics
- **Player Tracking**: Unified TrueSkill MMR ratings across all game modes (3v3, 4v4, 5v5)
- **Performance Analytics**: Economic, combat, and efficiency metrics for each player
- **Synergy Detection**: Identifies which players work well together
- **Player Archetypes**: Rush, Timing Attacker, Late Game, All-In, Balanced, Defender
- **Modern Web Interface**: React-based frontend with dark gaming theme

## Quick Start

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

### 3. Load Replay Data

**Batch Processing (Recommended)**
```bash
cd backend
python batch_process_replays.py /path/to/replays --show-predictions --verbose
```

**Web Upload**
1. Open http://localhost:3000
2. Navigate to "Upload Replays"
3. Drag and drop your .SC2Replay files

### 4. Balance Teams

**Web Interface:**
1. Go to http://localhost:3000/balance
2. Select players for your session
3. Click "Generate Teams"
4. Review suggestions with match quality scores

**API:**
```bash
curl -X POST "http://localhost:8000/teams/balance" \
  -H "Content-Type: application/json" \
  -d '{"player_ids": [1,2,3,4,5,6], "num_suggestions": 5}'
```

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, SQLite, sc2reader, TrueSkill
- **Frontend**: React 18, Vite, Chakra UI v2, React Query
- **Database**: SQLite (auto-created, no configuration needed)

## Project Structure

```
sc2mmr/
├── backend/           # FastAPI backend
│   ├── app/          # Application code
│   │   ├── api/      # API endpoints
│   │   ├── models.py # Database models
│   │   └── ...       # Services and utilities
│   └── data/         # SQLite database
├── frontend/         # React frontend
│   ├── src/
│   │   ├── pages/    # Main routes
│   │   ├── components/
│   │   └── api/      # API client
│   └── package.json
└── GUIDE.md          # Complete documentation
```

## Documentation

- **[GUIDE.md](GUIDE.md)** - Complete guide with setup, features, API reference, and troubleshooting
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Stats extraction fix deployment
- **[DEPLOYMENT_TESTING_GUIDE.md](DEPLOYMENT_TESTING_GUIDE.md)** - Testing procedures
- **API Docs** - Interactive documentation at http://localhost:8000/docs

## Key Features Explained

### TrueSkill Rating System
- **mu (μ)**: Skill estimate (default: 25.0)
- **sigma (σ)**: Uncertainty (default: 8.333, decreases with games played)
- **MMR**: Conservative rating = μ - 3σ (used for balancing)
- **Recency Weighting**: 60-day half-life weights recent matches more heavily

### Impact Scoring
Each player receives scores (0-100) across:
- **Economic Score** (30% weight): Resources, workers, spending efficiency
- **Combat Score** (50% weight): Damage dealt, kills, army value destroyed
- **Efficiency Score** (20% weight): Resource usage, damage ratios

### Team Balancing
1. Generate all possible team splits
2. Predict match quality using TrueSkill
3. Rank suggestions by match quality and MMR difference
4. Return top N balanced options

Match quality ranges:
- 0.9+: Excellent
- 0.75-0.9: Very Good
- 0.6-0.75: Good
- 0.4-0.6: Fair
- <0.4: Poor

## Common Operations

### Process Historical Replays
```bash
cd backend
python batch_process_replays.py /path/to/replays --show-predictions
```

This shows:
- Predictions before each match
- Rating evolution over time
- Final rankings and prediction accuracy (typically 65-75%)

### Check Player Rankings
```bash
curl http://localhost:8000/players/rankings?min_games=5 | python -m json.tool
```

### Upload Replay via API
```bash
curl -X POST "http://localhost:8000/replays/upload-advanced" \
  -F "file=@replay.SC2Replay"
```

### View Player Synergies
```bash
curl http://localhost:8000/impact/players/1/synergies | python -m json.tool
```

## Troubleshooting

**Module not found errors**
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

**CORS errors**
- Ensure backend is running on port 8000
- Frontend proxy configuration handles CORS in development

**Empty frontend pages**
- Upload some replay files first
- Check backend is running and accessible

See **[GUIDE.md](GUIDE.md)** for complete troubleshooting information.

## Performance

- **Replay parsing**: 50-100ms (basic), 200-500ms (advanced)
- **Batch processing**: ~30-60 seconds for 100 replays
- **Team balancing**:
  - 6 players (3v3): ~5ms (20 combinations)
  - 8 players (4v4): ~20ms (70 combinations)
  - 10 players (5v5): ~100ms (252 combinations)

## License

MIT License - feel free to use and modify for your own gaming groups.

## Contributing

This is a personal project for a casual gaming group, but suggestions and improvements are welcome!

## Acknowledgments

- Microsoft Research for the TrueSkill algorithm
- sc2reader library maintainers
- FastAPI, React, and Chakra UI communities
