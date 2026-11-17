# SC2MMR - Friend Squad Edition 🎮

StarCraft II replay analysis and squad rating system. Track your friends, balance teams, and analyze what actually wins games.

## 🚀 Quick Start

To start both the backend and frontend services:

```bash
chmod +x run.sh
./run.sh
```

- **Frontend**: [http://localhost:5175](http://localhost:5175)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🛠️ Key Components

### Backend (FastAPI + SQLite)
- **MMR System**: TrueSkill™ based rating (mu/sigma).
- **Replay Parser**: sc2reader-based parser with fallback winner determination.

### Frontend (React + Vite + Chakra UI)
- **Aesthetic**: "Friend Squad" (Sunset Orange, Comic Shadows, Rounded Corners).
- **Team Generator**: Balance teams with "Add Guest" support and Impact balancing.
- **Insights**: Per-player performance trends, head-to-head records and achievements.

## 📂 Project Structure

- `/backend`: Python service and replay parsing. `requirements.txt` is what the app needs; `requirements-dev.txt` adds the test tools and `requirements-research.txt` the libraries the analysis scripts in `backend/scripts` use.
- `/frontend`: React application and aesthetic theme.
- `/scripts`: Utility scripts for data maintenance and uploads.
- `/docs`: Reviews, specs and the rating consolidation log.

## 📝 Troubleshooting

- **Logs**: Check `backend.log` in the root directory for API errors.
- **Port Conflicts**: If ports are blocked, run `pkill -f uvicorn` and `pkill -f vite`.
- **Database**: The SQLite database is located at `backend/data/sc2mmr.db`.
