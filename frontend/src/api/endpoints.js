/**
 * API Endpoints
 * All backend API calls organized by resource
 */
import apiClient from './client';

/**
 * Players API
 */
export const playersApi = {
  // Get all players
  getAll: (coreOnly = false) => {
    return apiClient.get('/players/', {
      params: { core_only: coreOnly }
    });
  },

  // Get player rankings
  getRankings: (minGames = 5, coreOnly = false) => {
    return apiClient.get('/players/rankings', {
      params: { min_games: minGames, core_only: coreOnly }
    });
  },

  // Get player details
  getById: (playerId, recentMatchesLimit = 10) => {
    return apiClient.get(`/players/${playerId}`, {
      params: { recent_matches_limit: recentMatchesLimit }
    });
  },

  // Create new player
  create: (name, isCorePlayer = true) => {
    return apiClient.post('/players/', {
      name,
      is_core_player: isCorePlayer
    });
  },

  // Calibrate new player
  calibrate: (name, similarToPlayerId) => {
    return apiClient.post('/players/calibrate', {
      name,
      similar_to_player_id: similarToPlayerId
    });
  }
};

/**
 * Teams API
 */
export const teamsApi = {
  // Balance teams (primary feature!)
  balance: (playerIds, topN = 10) => {
    return apiClient.post('/teams/balance', {
      player_ids: playerIds,
      top_n: topN
    });
  },

  // Quick balance (single best result)
  quickBalance: (playerIds) => {
    return apiClient.post('/teams/quick-balance', {
      player_ids: playerIds,
      top_n: 1
    });
  },

  // Balance with impact consideration
  balanceWithImpact: (playerIds, topN = 10, impactWeight = 0.5) => {
    return apiClient.post('/teams/balance-with-impact', {
      player_ids: playerIds,
      top_n: topN,
      impact_weight: impactWeight
    });
  },

  // Balance with specific model
  balanceWithModel: (playerIds, model = 'trueskill') => {
    return apiClient.post('/teams/balance-with-model', {
      player_ids: playerIds,
      model
    });
  },

  // Compare all models
  compareModels: (playerIds) => {
    return apiClient.post('/teams/compare-models', {
      player_ids: playerIds
    });
  },

  // Get available models
  getModels: () => {
    return apiClient.get('/teams/models');
  }
};

/**
 * Replays API
 */
export const replaysApi = {
  // Upload single replay
  upload: (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post('/replays/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress
    });
  },

  // Upload with advanced metrics
  uploadAdvanced: (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post('/replays/upload-advanced', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress
    });
  },

  // Get matches
  getMatches: (limit = 50, offset = 0) => {
    return apiClient.get('/replays/matches', {
      params: { limit, offset }
    });
  },

  // Get match details
  getMatchById: (matchId) => {
    return apiClient.get(`/replays/matches/${matchId}`);
  },

  // Get AI-generated match commentary
  getMatchCommentary: (matchId) => {
    return apiClient.get(`/replays/matches/${matchId}/commentary`);
  },

  // Get failed uploads
  getFailedUploads: (limit = 50, offset = 0, errorType = null, reviewed = null) => {
    return apiClient.get('/replays/failed-uploads', {
      params: {
        limit,
        offset,
        error_type: errorType,
        reviewed
      }
    });
  },

  // Mark failed upload as reviewed
  markUploadReviewed: (uploadId, reviewNotes = null) => {
    return apiClient.patch(`/replays/failed-uploads/${uploadId}/reviewed`, {
      review_notes: reviewNotes
    });
  },

  // Manually set winner for failed replay
  setManualWinner: (uploadId, winnerTeam) => {
    return apiClient.post(`/replays/failed-uploads/${uploadId}/set-winner`, {
      winner_team: winnerTeam
    });
  }
};

/**
 * Health check
 */
export const healthApi = {
  check: () => {
    return apiClient.get('/health');
  }
};
