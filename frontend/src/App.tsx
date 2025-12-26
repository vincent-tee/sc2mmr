/**
 * Main App Component
 *
 * Sets up routing and layout with individual error boundaries per page.
 * Each route is wrapped in an ErrorBoundary to prevent cascading failures.
 */
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box } from '@chakra-ui/react';
import Navigation from './components/Navigation';
import ErrorBoundary from './components/ErrorBoundary';
import Home from './pages/Home';
import TeamGenerator from './pages/TeamGenerator';
import LineupPredictor from './pages/LineupPredictor';
import UploadReplays from './pages/UploadReplays';
import FailedUploads from './pages/FailedUploads';
import Players from './pages/Players';
import PlayerDetail from './pages/PlayerDetail';
import MatchHistory from './pages/MatchHistory';
import MatchDetail from './pages/MatchDetail';
import RatingSystem from './pages/RatingSystem';
import AdaptiveModel from './pages/AdaptiveModel';
import Leaderboard from './pages/Leaderboard';
import Achievements from './pages/Achievements';
import HeadToHead from './pages/HeadToHead';

/**
 * Root application component that provides routing structure.
 *
 * @returns The main application with navigation and routed pages
 */
function App(): React.ReactElement {
  return (
    <Router>
      <Box minH="100vh" position="relative" zIndex={1}>
        <Navigation />
        <Routes>
          <Route
            path="/"
            element={
              <ErrorBoundary>
                <Home />
              </ErrorBoundary>
            }
          />
          <Route
            path="/balance"
            element={
              <ErrorBoundary>
                <TeamGenerator />
              </ErrorBoundary>
            }
          />
          <Route
            path="/predictor"
            element={
              <ErrorBoundary>
                <LineupPredictor />
              </ErrorBoundary>
            }
          />
          <Route
            path="/upload"
            element={
              <ErrorBoundary>
                <UploadReplays />
              </ErrorBoundary>
            }
          />
          <Route
            path="/failed-uploads"
            element={
              <ErrorBoundary>
                <FailedUploads />
              </ErrorBoundary>
            }
          />
          <Route
            path="/players"
            element={
              <ErrorBoundary>
                <Players />
              </ErrorBoundary>
            }
          />
          <Route
            path="/players/:playerId"
            element={
              <ErrorBoundary>
                <PlayerDetail />
              </ErrorBoundary>
            }
          />
          <Route
            path="/history"
            element={
              <ErrorBoundary>
                <MatchHistory />
              </ErrorBoundary>
            }
          />
          <Route
            path="/history/:matchId"
            element={
              <ErrorBoundary>
                <MatchDetail />
              </ErrorBoundary>
            }
          />
          <Route
            path="/rating-system"
            element={
              <ErrorBoundary>
                <RatingSystem />
              </ErrorBoundary>
            }
          />
          <Route
            path="/adaptive-model"
            element={
              <ErrorBoundary>
                <AdaptiveModel />
              </ErrorBoundary>
            }
          />
        </Routes>
      </Box>
    </Router>
  );
}

export default App;
