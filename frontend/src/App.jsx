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
import Players from './pages/Players';
import MatchHistory from './pages/MatchHistory';
import RatingSystem from './pages/RatingSystem';

function App() {
  return (
    <Router>
      <Box minH="100vh">
        <Navigation />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/balance" element={<TeamGenerator />} />
          <Route path="/upload" element={<UploadReplays />} />
          <Route path="/players" element={<Players />} />
          <Route path="/history" element={<MatchHistory />} />
          <Route path="/rating-system" element={<RatingSystem />} />
        </Routes>
      </Box>
    </Router>
  );
}

export default App;
