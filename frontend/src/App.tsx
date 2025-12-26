/**
 * Main App Component
 *
 * Sets up routing and layout with individual error boundaries per page.
 * Each route is wrapped in an ErrorBoundary to prevent cascading failures.
 * Uses React.lazy for route-based code splitting to improve initial load time.
 */
import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box, Spinner, Center, Link } from '@chakra-ui/react';
import Navigation from './components/Navigation';
import ErrorBoundary from './components/ErrorBoundary';

/**
 * Skip-to-content link for keyboard/screen reader accessibility
 */
const SkipToContent: React.FC = () => (
  <Link
    href="#main-content"
    position="absolute"
    top="-40px"
    left="0"
    bg="brand.500"
    color="white"
    px={4}
    py={2}
    zIndex={100}
    _focus={{
      top: "0",
    }}
  >
    Skip to main content
  </Link>
);

// Lazy load all pages for code splitting
// Critical path pages (Home) are loaded eagerly for better perceived performance
import Home from './pages/Home';

// Lazy-loaded pages
const TeamGenerator = lazy(() => import('./pages/TeamGenerator'));
const LineupPredictor = lazy(() => import('./pages/LineupPredictor'));
const UploadReplays = lazy(() => import('./pages/UploadReplays'));
const FailedUploads = lazy(() => import('./pages/FailedUploads'));
const Players = lazy(() => import('./pages/Players'));
const PlayerDetail = lazy(() => import('./pages/PlayerDetail'));
const MatchHistory = lazy(() => import('./pages/MatchHistory'));
const MatchDetail = lazy(() => import('./pages/MatchDetail'));
const RatingSystem = lazy(() => import('./pages/RatingSystem'));
const AdaptiveModel = lazy(() => import('./pages/AdaptiveModel'));
const Leaderboard = lazy(() => import('./pages/Leaderboard'));
const Achievements = lazy(() => import('./pages/Achievements'));
const HeadToHead = lazy(() => import('./pages/HeadToHead'));

/**
 * Loading fallback component for Suspense boundaries
 */
const PageLoader: React.FC = () => (
  <Center minH="50vh">
    <Spinner
      size="xl"
      color="brand.500"
      thickness="4px"
      speed="0.65s"
      emptyColor="gray.700"
    />
  </Center>
);

/**
 * Root application component that provides routing structure.
 *
 * @returns The main application with navigation and routed pages
 */
function App(): React.ReactElement {
  return (
    <Router>
      <SkipToContent />
      <Box minH="100vh" position="relative" zIndex={1}>
        <Navigation />
        <Box as="main" role="main" id="main-content">
          <Suspense fallback={<PageLoader />}>
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
              <Route
                path="/leaderboard"
                element={
                  <ErrorBoundary>
                    <Leaderboard />
                  </ErrorBoundary>
                }
              />
              <Route
                path="/achievements"
                element={
                  <ErrorBoundary>
                    <Achievements />
                  </ErrorBoundary>
                }
              />
              <Route
                path="/h2h"
                element={
                  <ErrorBoundary>
                    <HeadToHead />
                  </ErrorBoundary>
                }
              />
              <Route
                path="/h2h/:player1Id/:player2Id"
                element={
                  <ErrorBoundary>
                    <HeadToHead />
                  </ErrorBoundary>
                }
              />
            </Routes>
          </Suspense>
        </Box>
      </Box>
    </Router>
  );
}

export default App;
