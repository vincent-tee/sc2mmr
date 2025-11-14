/**
 * Main App Component
 * Sets up routing and layout
 */
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box } from '@chakra-ui/react';
import Navigation from './components/Navigation';
import Home from './pages/Home';
import TeamGenerator from './pages/TeamGenerator';
import UploadReplays from './pages/UploadReplays';
import FailedUploads from './pages/FailedUploads';
import Players from './pages/Players';
import PlayerDetail from './pages/PlayerDetail';
import MatchHistory from './pages/MatchHistory';
import MatchDetail from './pages/MatchDetail';
import RatingSystem from './pages/RatingSystem';
import AdaptiveModel from './pages/AdaptiveModel';

function App() {
  return (
    <Router>
      <Box minH="100vh" position="relative" zIndex={1}>
        <Navigation />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/balance" element={<TeamGenerator />} />
          <Route path="/upload" element={<UploadReplays />} />
          <Route path="/failed-uploads" element={<FailedUploads />} />
          <Route path="/players" element={<Players />} />
          <Route path="/players/:playerId" element={<PlayerDetail />} />
          <Route path="/history" element={<MatchHistory />} />
          <Route path="/history/:matchId" element={<MatchDetail />} />
          <Route path="/rating-system" element={<RatingSystem />} />
          <Route path="/adaptive-model" element={<AdaptiveModel />} />
        </Routes>
      </Box>
    </Router>
  );
}

export default App;
