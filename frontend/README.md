# SC2 MMR Tracker - Frontend

Modern React frontend for the SC2 MMR Tracker application. Built with Vite, React 18, and Chakra UI.

## Features

### Core Features
- **🎮 Team Generator (PRIMARY)**: Quick, intuitive interface for generating balanced team compositions
- **📤 Drag & Drop Upload**: Bulk upload SC2 replay files with real-time progress tracking
- **👥 Player Management**: View player statistics, rankings, and detailed profiles
- **📊 Match History**: Browse past games with detailed statistics
- **🎨 Dark Mode**: Gaming-inspired dark theme with blue/cyan primary and orange/gold accents

### Technical Highlights
- Built with React 18 and Vite for fast development
- Chakra UI v2 for accessible, themeable components
- React Query for efficient API state management
- React Router v6 for client-side routing
- React Dropzone for file uploads
- Responsive design (mobile-first approach)

## Prerequisites

- Node.js 16+ and npm
- Backend API running on `http://localhost:8000`

## Installation

```bash
# Install dependencies
npm install

# Set up environment variables (optional, defaults to localhost:8000)
# Create .env.local if you need to override the default API URL
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
```

## Development

```bash
# Start development server (runs on http://localhost:3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Quick Start

1. **Start the backend** (from project root):
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Start the frontend** (from frontend directory):
   ```bash
   npm run dev
   ```

3. **Open browser**: Navigate to `http://localhost:3000`

4. **Upload replays**: Click "Upload Replays" and drag your `.SC2Replay` files

5. **Generate teams**: Go to "Generate Teams" and select players

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client and endpoint definitions
│   │   ├── client.js     # Axios instance with interceptors
│   │   └── endpoints.js  # All backend API calls
│   ├── components/       # Reusable components
│   │   ├── PlayerCard.jsx
│   │   ├── EmptyState.jsx
│   │   ├── LoadingState.jsx
│   │   └── Navigation.jsx
│   ├── pages/            # Route components
│   │   ├── Home.jsx      # Dashboard/landing page
│   │   ├── TeamGenerator.jsx  # PRIMARY feature
│   │   ├── UploadReplays.jsx
│   │   ├── Players.jsx
│   │   └── MatchHistory.jsx
│   ├── hooks/            # Custom React hooks
│   │   └── useToast.js
│   ├── utils/            # Helper functions
│   │   └── formatting.js
│   ├── theme/            # Chakra UI theme configuration
│   │   └── index.js
│   ├── App.jsx           # Main app with routing
│   └── main.jsx          # Entry point with providers
├── public/               # Static assets
├── .env                  # Environment variables
├── vite.config.js        # Vite configuration with proxy
└── package.json
```

## Key Pages

### Home (`/`)
Dashboard with quick stats and action buttons for main features.

### Team Generator (`/balance`) - PRIMARY FEATURE
- Grid-based player selection with visual feedback
- Generate multiple balanced team suggestions
- View win probabilities and fairness ratings
- Export team compositions as text or files
- Optimized for quick interaction (<30 seconds to generate teams)

### Upload Replays (`/upload`)
- Drag-and-drop interface for `.SC2Replay` files
- Supports folders and bulk uploads
- Real-time progress tracking per file
- Duplicate detection with friendly messages
- Batch processing (5 files at a time)
- Retry failed uploads

### Players (`/players`)
- Grid view of all players
- Search and sort functionality
- Player cards with MMR, race, and statistics
- Click to view detailed player profiles

### Match History (`/history`)
- List of all recorded matches
- Filter and sort options
- Click to view detailed match results

## API Integration

The frontend communicates with the backend via:

```javascript
// Proxy configured in vite.config.js
// All /api/* requests are proxied to http://localhost:8000

// Main endpoints:
GET    /players/              - List all players
GET    /players/:id           - Get player details
POST   /teams/balance         - Generate balanced teams (PRIMARY)
POST   /replays/upload        - Upload replay file
GET    /replays/matches       - List matches
```

## Environment Variables

```bash
# .env (default values)
VITE_API_BASE_URL=http://localhost:8000
```

## Theming

The app uses a gaming-inspired dark theme:

- **Primary**: Blue/Cyan (`brand.500`: #1890FF)
- **Accent**: Orange/Gold (`accent.500`: #FA8C16)
- **Background**: Dark gray (`gray.900`)
- **Cards**: `gray.800`
- **Success**: Green, Warning: Yellow, Error: Red

Customize in `src/theme/index.js`.

## Troubleshooting

**CORS errors:**
- Ensure backend has CORS enabled for `http://localhost:3000`
- Check Vite proxy configuration in `vite.config.js`

**API connection failed:**
- Verify backend is running on `http://localhost:8000`
- Check `VITE_API_BASE_URL` in `.env`

**Build errors:**
- Clear node_modules: `rm -rf node_modules && npm install`
- Clear cache: `rm -rf dist .vite`

**Empty pages/No data:**
- Upload some replay files first
- Check browser console for errors
- Verify backend API at `http://localhost:8000/docs`

## Technology Stack

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Chakra UI v2**: Component library
- **React Query (TanStack Query)**: API state management
- **React Router v6**: Client-side routing
- **React Dropzone**: File upload handling
- **Axios**: HTTP client
- **React Icons**: Icon library
- **Framer Motion**: Animation library (via Chakra UI)

## License

Same as parent project.
