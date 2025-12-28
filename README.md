# SC2MMR - Friend Squad Edition 🎮

StarCraft II replay analysis and squad rating system. Track your friends, balance teams, and analyze what actually wins games.

## 🚀 Quick Start

To start both the backend and frontend services:

```bash
chmod +x run.sh
./run.sh
```

- **Frontend**: [http://localhost:3002](http://localhost:3002)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🛠️ Key Components

### Backend (FastAPI + SQLite)
- **MMR System**: TrueSkill™ based rating (mu/sigma).
- **ML Intelligence**: XGBoost model analyzing 14+ gameplay factors (Macro, Micro, Momentum).
- **Replay Parser**: sc2reader-based parser with fallback winner determination.

### Frontend (React + Vite + Chakra UI)
- **Aesthetic**: "Friend Squad" (Sunset Orange, Comic Shadows, Rounded Corners).
- **Team Generator**: Balance teams with "Add Guest" support and Impact balancing.
- **Insights**: Performance trends and feature importance monitoring.

## 📂 Project Structure

- `/backend`: Python service, replay parsing, and ML models.
- `/frontend`: React application and aesthetic theme.
- `/scripts`: Utility scripts for data maintenance and uploads.
- `/docs/archive`: Legacy documentation and phase reports.

## 📝 Troubleshooting

- **Logs**: Check `backend.log` in the root directory for API errors.
- **Port Conflicts**: If ports are blocked, run `pkill -f uvicorn` and `pkill -f vite`.
- **Database**: The SQLite database is located at `backend/data/sc2mmr.db`.
