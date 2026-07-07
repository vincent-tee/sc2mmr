/**
 * API Endpoints
 * All backend API calls organized by resource
 */
import { AxiosResponse, AxiosProgressEvent } from 'axios';
import apiClient, { API_BASE_URL } from './client';
import type {
  Player,
  PlayerDetail,
  PlayerHistoryResponse,
  PlayerRanking,
  TeamSuggestion,
  MatchDetail,
  MatchListResponse,
  MatchListWithPlayersResponse,
  ReplayUploadResponse,
  PlayerImpact,
  MatchPlayerMetrics,
  PlayerSynergy,
  HealthCheckResponse,
  MatchPredictionResponse,
} from '@/types/api';

// =============================================================================
// Players API
// =============================================================================

export interface PlayersApi {
  getAll: (coreOnly?: boolean) => Promise<AxiosResponse<Player[]>>;
  getRankings: (minGames?: number, coreOnly?: boolean) => Promise<AxiosResponse<PlayerRanking[]>>;
  getById: (
    playerId: number,
    recentMatchesLimit?: number,
    recentMatchesOffset?: number
  ) => Promise<AxiosResponse<PlayerDetail>>;
  getHistory: (playerId: number, limit?: number) => Promise<AxiosResponse<PlayerHistoryResponse>>;
  getCoaching: (playerId: number) => Promise<AxiosResponse<any>>;
  create: (name: string, isCorePlayer?: boolean) => Promise<AxiosResponse<Player>>;
  calibrate: (name: string, similarToPlayerId: number) => Promise<AxiosResponse<Player>>;
}

export const playersApi: PlayersApi = {
  getAll: (coreOnly = false) => {
    return apiClient.get<Player[]>('/players/', {
      params: { core_only: coreOnly }
    });
  },

  getRankings: (minGames = 5, coreOnly = false) => {
    return apiClient.get<PlayerRanking[]>('/players/rankings', {
      params: { min_games: minGames, core_only: coreOnly }
    });
  },

  getById: (playerId: number, recentMatchesLimit = 10, recentMatchesOffset = 0) => {
    return apiClient.get<PlayerDetail>(`/players/${playerId}`, {
      params: {
        recent_matches_limit: recentMatchesLimit,
        recent_matches_offset: recentMatchesOffset
      }
    });
  },

  getHistory: (playerId: number, limit = 50) => {
    return apiClient.get<PlayerHistoryResponse>(`/players/${playerId}/history`, {
      params: { limit }
    });
  },

  getCoaching: (playerId: number) => {
    return apiClient.get(`/players/${playerId}/coaching`);
  },

  create: (name: string, isCorePlayer = true) => {
    return apiClient.post<Player>('/players/', {
      name,
      is_core_player: isCorePlayer
    });
  },

  calibrate: (name: string, similarToPlayerId: number) => {
    return apiClient.post<Player>('/players/calibrate', {
      name,
      similar_to_player_id: similarToPlayerId
    });
  }
};

// =============================================================================
// Teams API
// =============================================================================

export interface TeamsApi {
  balance: (playerIds: number[], topN?: number, mapName?: string) => Promise<AxiosResponse<TeamSuggestion[]>>;
  quickBalance: (playerIds: number[]) => Promise<AxiosResponse<TeamSuggestion[]>>;
  balanceWithModel: (playerIds: number[], model?: string) => Promise<AxiosResponse<TeamSuggestion[]>>;
  compareModels: (playerIds: number[]) => Promise<AxiosResponse<Record<string, TeamSuggestion[]>>>;
  getModels: () => Promise<AxiosResponse<string[]>>;
  getAIDifficulties: () => Promise<AxiosResponse<{ difficulties: Record<string, number>, config_path: string }>>;
  predict: (team1Ids: number[], team2Ids: number[]) => Promise<AxiosResponse<MatchPredictionResponse>>;
}

export const teamsApi: TeamsApi = {
  // Balance teams (primary feature!)
  balance: (playerIds: number[], topN = 10, mapName?: string) => {
    return apiClient.post<TeamSuggestion[]>('/teams/balance', {
      player_ids: playerIds,
      top_n: topN,
      map_name: mapName
    });
  },

  // Quick balance (single best result)
  quickBalance: (playerIds: number[]) => {
    return apiClient.post<TeamSuggestion[]>('/teams/quick-balance', {
      player_ids: playerIds,
      top_n: 1
    });
  },

  // Balance with specific model
  balanceWithModel: (playerIds: number[], model = 'trueskill') => {
    return apiClient.post<TeamSuggestion[]>('/teams/balance-with-model', {
      player_ids: playerIds,
      model
    });
  },

  // Compare all models
  compareModels: (playerIds: number[]) => {
    return apiClient.post<Record<string, TeamSuggestion[]>>('/teams/compare-models', {
      player_ids: playerIds
    });
  },

  // Get available models
  getModels: () => {
    return apiClient.get<string[]>('/teams/models');
  },
  // Get AI difficulties
  getAIDifficulties: () => {
    return apiClient.get<{ difficulties: Record<string, number>, config_path: string }>('/teams/ai-difficulties');
  },
  // Predict match outcome with detailed analysis

  predict: (team1Ids: number[], team2Ids: number[]) => {
    return apiClient.post<MatchPredictionResponse>('/teams/predict', {
      team_1_ids: team1Ids,
      team_2_ids: team2Ids
    });
  }
};

// =============================================================================
// Replays API
// =============================================================================

export interface FailedUpload {
  id: number;
  filename: string;
  file_size_bytes?: number;
  error_type: string;
  error_message: string;
  uploaded_at: string;
  reviewed: boolean;
  review_notes: string | null;
  map_name?: string;
  game_mode?: string;
}

export interface ReplaysApi {
  upload: (file: File, onUploadProgress?: (event: AxiosProgressEvent) => void) => Promise<AxiosResponse<ReplayUploadResponse>>;
  uploadAdvanced: (file: File, onUploadProgress?: (event: AxiosProgressEvent) => void) => Promise<AxiosResponse<ReplayUploadResponse>>;
  getMatches: (limit?: number, offset?: number) => Promise<AxiosResponse<MatchListResponse>>;
  getMatchesWithPlayers: (
    limit?: number,
    offset?: number,
    filters?: { search?: string; game_mode?: string }
  ) => Promise<AxiosResponse<MatchListWithPlayersResponse>>;
  getMatchById: (matchId: number | string) => Promise<AxiosResponse<MatchDetail>>;
  getMatchCommentary: (matchId: number | string) => Promise<AxiosResponse<{ commentary: string }>>;
  getMatchDownloadUrl: (matchId: number | string) => string;
  getFailedUploads: (limit?: number, offset?: number, errorType?: string | null, reviewed?: boolean | null) => Promise<AxiosResponse<FailedUpload[]>>;
  markUploadReviewed: (uploadId: number, reviewNotes?: string | null) => Promise<AxiosResponse<FailedUpload>>;
  setManualWinner: (uploadId: number, winnerTeam: number) => Promise<AxiosResponse<ReplayUploadResponse>>;
}

// Extended timeout for upload operations (120 seconds)
const UPLOAD_TIMEOUT = 120000;

export const replaysApi: ReplaysApi = {
  // Upload single replay
  upload: (file: File, onUploadProgress?: (event: AxiosProgressEvent) => void) => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post<ReplayUploadResponse>('/replays/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: UPLOAD_TIMEOUT,
      onUploadProgress
    });
  },

  // Upload with advanced metrics
  uploadAdvanced: (file: File, onUploadProgress?: (event: AxiosProgressEvent) => void) => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post<ReplayUploadResponse>('/replays/upload-advanced', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: UPLOAD_TIMEOUT,
      onUploadProgress
    });
  },

  // Get matches
  getMatches: (limit = 50, offset = 0) => {
    return apiClient.get<MatchListResponse>('/replays/matches', {
      params: { limit, offset }
    });
  },

  // Get matches with player summaries (for match history page).
  // Optional search (map name or player name) and game_mode filters are applied
  // server-side; omitting them preserves the original limit/offset behavior.
  getMatchesWithPlayers: (
    limit = 20,
    offset = 0,
    filters?: { search?: string; game_mode?: string }
  ) => {
    const params: Record<string, string | number> = { limit, offset };
    if (filters?.search) params.search = filters.search;
    if (filters?.game_mode) params.game_mode = filters.game_mode;
    return apiClient.get<MatchListWithPlayersResponse>('/replays/matches-with-players', {
      params
    });
  },

  // Get match details
  getMatchById: (matchId: number | string) => {
    return apiClient.get<MatchDetail>(`/replays/matches/${matchId}`);
  },

  // Get AI-generated match commentary
  getMatchCommentary: (matchId: number | string) => {
    return apiClient.get<{ commentary: string }>(`/replays/matches/${matchId}/commentary`);
  },

  // Direct download URL for the .SC2Replay file (used as an <a href>, not fetched via axios)
  getMatchDownloadUrl: (matchId: number | string) => {
    return `${API_BASE_URL}/replays/matches/${matchId}/download`;
  },

  // Get failed uploads
  getFailedUploads: (limit = 50, offset = 0, errorType: string | null = null, reviewed: boolean | null = null) => {
    return apiClient.get<FailedUpload[]>('/replays/failed-uploads', {
      params: {
        limit,
        offset,
        error_type: errorType,
        reviewed
      }
    });
  },

  // Mark failed upload as reviewed
  markUploadReviewed: (uploadId: number, reviewNotes: string | null = null) => {
    return apiClient.patch<FailedUpload>(`/replays/failed-uploads/${uploadId}/reviewed`, {
      review_notes: reviewNotes
    });
  },

  // Manually set winner for failed replay
  setManualWinner: (uploadId: number, winnerTeam: number) => {
    return apiClient.post<ReplayUploadResponse>(`/replays/failed-uploads/${uploadId}/set-winner`, {
      winner_team: winnerTeam
    });
  }
};

// =============================================================================
// Impact & Metrics API
// =============================================================================

export interface LeaderboardEntry {
  id: number;
  name: string;
  total_games: number;
  value: number;
}

export interface ImpactApi {
  getPlayersByImpact: (sortBy?: string, minGames?: number) => Promise<AxiosResponse<PlayerImpact[]>>;
  getPlayerMatchMetrics: (playerId: number, limit?: number) => Promise<AxiosResponse<MatchPlayerMetrics[]>>;
  getMatchDamageTimeline: (playerId: number, matchId: number | string) => Promise<AxiosResponse<Record<string, number>>>;
  getMatchCoordination: (matchId: number) => Promise<AxiosResponse<unknown>>;
  getPlayerSynergies: (playerId: number, minGames?: number) => Promise<AxiosResponse<PlayerSynergy[]>>;
  getTopSynergies: (minGames?: number, limit?: number) => Promise<AxiosResponse<PlayerSynergy[]>>;
  getLeaderboard: (category: string, minGames?: number, limit?: number) => Promise<AxiosResponse<LeaderboardEntry[]>>;
  getPlayerAttackPatterns: (playerId: number, limit?: number) => Promise<AxiosResponse<unknown>>;
}

export const impactApi: ImpactApi = {
  // Get players by impact scores
  getPlayersByImpact: (sortBy = 'overall', minGames = 5) => {
    return apiClient.get<PlayerImpact[]>('/impact/players', {
      params: { sort_by: sortBy, min_games: minGames }
    });
  },

  // Get detailed match metrics for a player
  getPlayerMatchMetrics: (playerId: number, limit = 20) => {
    return apiClient.get<MatchPlayerMetrics[]>(`/impact/players/${playerId}/matches`, {
      params: { limit }
    });
  },

  // Get damage timeline for a specific match
  getMatchDamageTimeline: (playerId: number, matchId: number | string) => {
    return apiClient.get<Record<string, number>>(`/impact/players/${playerId}/matches/${matchId}/timeline`);
  },

  // Get team coordination analysis for a match
  getMatchCoordination: (matchId: number) => {
    return apiClient.get(`/impact/matches/${matchId}/coordination`);
  },

  // Get player synergies
  getPlayerSynergies: (playerId: number, minGames = 3) => {
    return apiClient.get<PlayerSynergy[]>(`/impact/players/${playerId}/synergies`, {
      params: { min_games: minGames }
    });
  },

  // Get top synergies
  getTopSynergies: (minGames = 5, limit = 10) => {
    return apiClient.get<PlayerSynergy[]>('/impact/synergies/top', {
      params: { min_games: minGames, limit }
    });
  },

  // Get impact leaderboard
  getLeaderboard: (category: string, minGames = 5, limit = 10) => {
    return apiClient.get<LeaderboardEntry[]>(`/impact/leaderboard/${category}`, {
      params: { min_games: minGames, limit }
    });
  },

  // Get player attack patterns
  getPlayerAttackPatterns: (playerId: number, limit = 20) => {
    return apiClient.get(`/impact/players/${playerId}/attack-patterns`, {
      params: { limit }
    });
  }
};

// =============================================================================
// Health check
// =============================================================================

export interface HealthApi {
  check: () => Promise<AxiosResponse<HealthCheckResponse>>;
}

export const healthApi: HealthApi = {
  check: () => {
    return apiClient.get<HealthCheckResponse>('/health');
  }
};
