# SC2 MMR Tracker - Technical Documentation

## TECHNOLOGY STACK

### Backend Stack

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Runtime** | Python | 3.10+ | Backend runtime |
| **Framework** | FastAPI | Latest | REST API framework |
| **ORM** | SQLAlchemy | Latest | Database abstraction |
| **Database** | SQLite | 3.x | Data persistence |
| **Rating System** | TrueSkill | 0.4.5 | Bayesian skill rating |
| **Replay Parsing** | sc2reader | Latest | SC2Replay file parsing |
| **Math/Stats** | SciPy | Latest | Statistical calculations |
| **Server** | Uvicorn | Latest | ASGI server |

### Frontend Stack

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Runtime** | Node.js | 16+ | JavaScript runtime |
| **Framework** | React | 19.2.0 | UI framework |
| **Build Tool** | Vite | 7.2.2 | Development & bundling |
| **UI Library** | Chakra UI | 2.10.9 | Component library |
| **State Management** | TanStack Query | 5.90.7 | Server state management |
| **Routing** | React Router | 7.9.5 | Client-side routing |
| **HTTP Client** | Axios | 1.13.2 | API communication |
| **Charts** | Recharts | 3.4.1 | Data visualization |
| **File Upload** | React Dropzone | 14.3.8 | Drag-drop uploads |
| **Animations** | Framer Motion | 12.23.24 | UI animations |
| **Icons** | React Icons | 5.5.0 | Icon library |
| **Styling** | Emotion | 11.14.x | CSS-in-JS |

---

## FRAMEWORK DETAILS

### FastAPI Backend

```python
# Core Configuration (main.py)
app = FastAPI(
    title="SC2 MMR Tracker",
    version="2.1.0",
    lifespan=lifespan  # Database initialization
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(replays.router)
app.include_router(players.router)
app.include_router(teams.router)
app.include_router(impact.router)
app.include_router(adaptive.router)
```

### React Frontend

```javascript
// Vite Configuration (vite.config.js)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

---

## TOOLING

### Development Tools

| Tool | Purpose | Configuration |
|------|---------|---------------|
| Vite | Frontend dev server | `vite.config.js` |
| Uvicorn | Backend dev server | `--reload` flag |
| ESLint | JavaScript linting | `eslint.config.js` |
| Git | Version control | `.gitignore` |

### Build Tools

| Tool | Command | Output |
|------|---------|--------|
| Vite | `npm run build` | `frontend/dist/` |
| Python | N/A | No build step needed |

### Scripts

**Frontend (`package.json`)**:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  }
}
```

**Backend**:
```bash
# Development server
uvicorn app.main:app --reload

# Batch replay processing
python batch_process_replays.py /path/to/replays --verbose

# Database reset
python reset_database.py

# Rating recalculation
python recalculate_ratings.py
```

---

## QUALITY STANDARDS

### TRUST 5 Principles Status

| Principle | Status | Implementation |
|-----------|--------|----------------|
| **Test-First** | Partial | `tests/test_basic.py` present |
| **Readable** | Good | Clear naming, structured modules |
| **Unified** | Good | Consistent patterns across codebase |
| **Secured** | Basic | Local-only deployment assumed |
| **Trackable** | Good | Git version control, replay hashing |

### Code Quality

- **Python Style**: PEP 8 compliance
- **JavaScript Style**: ESLint with React rules
- **Documentation**: Docstrings in Python, JSDoc comments

### Testing Strategy

| Layer | Framework | Coverage Target |
|-------|-----------|-----------------|
| Backend | pytest | 85% |
| Frontend | Vitest/Jest | (Not configured) |
| Integration | Manual | Core workflows |

---

## SECURITY

### Current Security Posture

| Area | Implementation | Notes |
|------|----------------|-------|
| **Authentication** | None | Trusted local network |
| **Authorization** | None | All users have full access |
| **Input Validation** | FastAPI Pydantic | Request validation |
| **File Uploads** | Extension check | `.SC2Replay` only |
| **Duplicate Prevention** | SHA256 hashing | `replay_hash` field |
| **CORS** | Permissive (`*`) | Development configuration |

### Security Recommendations

1. Add authentication for production deployment
2. Configure specific CORS origins
3. Implement rate limiting
4. Add request logging for audit

---

## OPERATIONS

### Deployment

**Current**: Local development deployment
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

**Production Considerations**:
- Frontend: Static build served via Nginx/CDN
- Backend: Gunicorn with Uvicorn workers
- Database: PostgreSQL for scale

### Environment Variables

**Frontend (`.env`)**:
```bash
VITE_API_BASE_URL=http://localhost:8000
```

**Backend**: No environment variables required for local deployment

### Database Management

| Operation | Command | Purpose |
|-----------|---------|---------|
| Initialize | Automatic on startup | Create tables |
| Reset | `python reset_database.py` | Clear all data |
| Migrate | `python migrations/run_*.py` | Schema updates |
| Backup | Copy `*.db` file | Data backup |

---

## MONITORING & OBSERVABILITY

### Health Checks

| Endpoint | Response | Purpose |
|----------|----------|---------|
| `GET /` | API info | Root endpoint |
| `GET /health` | `{"status": "healthy"}` | Liveness check |
| `GET /version` | Version + features | Version verification |

### Logging

**Backend**:
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Frontend**: Browser console logging

### Error Tracking

- Failed uploads stored in `failed_uploads` table
- Error types: `parse_error`, `validation_error`, `winner_determination`, `unsupported_mode`, `corrupt_file`
- Review endpoint available for failed upload management

---

## INCIDENT RESPONSE

### Common Issues

| Issue | Detection | Resolution |
|-------|-----------|------------|
| CORS errors | Browser console | Verify backend CORS config |
| API connection failed | Network tab | Check backend running on :8000 |
| Duplicate replay | HTTP 409 | Already processed, skip |
| Winner determination | Error log | Manual review of replay |
| Empty data | UI shows empty state | Upload replays first |

### Recovery Procedures

1. **Database corruption**: Restore from backup or reset
2. **Rating inconsistency**: Run `recalculate_ratings.py`
3. **Player merge needed**: Use `merge_players.py`

---

## ALGORITHM DETAILS

### TrueSkill Configuration

```python
trueskill.setup(
    mu=25.0,              # Initial skill estimate
    sigma=8.333,          # Initial uncertainty
    beta=4.166,           # Skill class width
    tau=0.0833,           # Dynamics factor (per day)
    draw_probability=0.0  # No draws in SC2
)
```

### MMR Formula

```python
# Displayed MMR (scaled for user-friendliness)
MMR = 1000 + (40 * mu)

# Approximate range:
# - New players: ~1000 MMR
# - Experienced: 800-2200 MMR
```

### Recency Weighting

```python
# Exponential decay with 60-day half-life
weight = 0.5^(days_ago / 60)

# Examples:
# Today: 1.0 (100%)
# 60 days ago: 0.5 (50%)
# 120 days ago: 0.25 (25%)
```

### Team Balancing

1. Generate all possible team combinations
2. Calculate TrueSkill match quality for each
3. Sort by match quality (higher = more balanced)
4. Return top N suggestions

---

## DEPENDENCIES

### Backend (Python)

```
fastapi
uvicorn[standard]
sqlalchemy
trueskill
sc2reader
scipy
python-multipart
```

### Frontend (Node.js)

```json
{
  "dependencies": {
    "@chakra-ui/react": "^2.10.9",
    "@emotion/react": "^11.14.0",
    "@emotion/styled": "^11.14.1",
    "@tanstack/react-query": "^5.90.7",
    "axios": "^1.13.2",
    "framer-motion": "^12.23.24",
    "html2canvas": "^1.4.1",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "react-dropzone": "^14.3.8",
    "react-icons": "^5.5.0",
    "react-router-dom": "^7.9.5",
    "recharts": "^3.4.1"
  },
  "devDependencies": {
    "@eslint/js": "^9.39.1",
    "@types/react": "^19.2.2",
    "@types/react-dom": "^19.2.2",
    "@vitejs/plugin-react": "^5.1.0",
    "eslint": "^9.39.1",
    "eslint-plugin-react-hooks": "^5.2.0",
    "eslint-plugin-react-refresh": "^0.4.24",
    "globals": "^16.5.0",
    "vite": "^7.2.2"
  }
}
```

---

## HISTORY

| Date | Change | Author |
|------|--------|--------|
| 2025-12-05 | Initial technical documentation created | project-manager |

---

*Document generated by MoAI-ADK Project Manager*
