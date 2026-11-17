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
  TeamSuggestion,
  MatchDetail,
  MatchListWithPlayersResponse,
  ReplayUploadResponse,
  MatchPlayerMetrics,
  MatchPredictionResponse,
} from '@/types/api';

// =============================================================================
// Players API
// =============================================================================

export interface PlayersApi {
  getAll: (coreOnly?: boolean) => Promise<AxiosResponse<Player[]>>;
  getById: (
    playerId: number,
    recentMatchesLimit?: number,
    recentMatchesOffset?: number
  ) => Promise<AxiosResponse<PlayerDetail>>;
  getHistory: (playerId: number, limit?: number) => Promise<AxiosResponse<PlayerHistoryResponse>>;
}

export const playersApi: PlayersApi = {
  getAll: (coreOnly = false) => {
    return apiClient.get<Player[]>('/players/', {
      params: { core_only: coreOnly }
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
};

// =============================================================================
// Teams API
// =============================================================================

export interface TeamsApi {
  balance: (playerIds: number[], topN?: number) => Promise<AxiosResponse<TeamSuggestion[]>>;
  getAIDifficulties: () => Promise<AxiosResponse<{ difficulties: Record<string, number>, config_path: string }>>;
  predict: (team1Ids: number[], team2Ids: number[]) => Promise<AxiosResponse<MatchPredictionResponse>>;
}

export const teamsApi: TeamsApi = {
  // Balance teams (primary feature!)
  balance: (playerIds: number[], topN = 10) => {
    return apiClient.post<TeamSuggestion[]>('/teams/balance', {
      player_ids: playerIds,
      top_n: topN,
    });
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
  uploadAdvanced: (file: File, onUploadProgress?: (event: AxiosProgressEvent) => void) => Promise<AxiosResponse<ReplayUploadResponse>>;
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
  getPlayerMatchMetrics: (playerId: number, limit?: number) => Promise<AxiosResponse<MatchPlayerMetrics[]>>;
}

export const impactApi: ImpactApi = {
  // Get detailed match metrics for a player
  getPlayerMatchMetrics: (playerId: number, limit = 20) => {
    return apiClient.get<MatchPlayerMetrics[]>(`/impact/players/${playerId}/matches`, {
      params: { limit }
    });
  },
};
