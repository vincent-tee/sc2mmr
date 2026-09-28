/**
 * Leaderboard API Client
 * MMR and win rate boards
 */
import { AxiosResponse } from 'axios';
import apiClient from './client';
import type {
  LeaderboardEntry,
  LeaderboardCategoryKey,
  MetaReportResponse,
} from '@/types/leaderboard';

// =============================================================================
// Leaderboard API Interface
// =============================================================================

export interface LeaderboardApi {
  /** Get MMR leaderboard (display MMR, the rating of record) */
  getMMR: (
    limit?: number,
    minGames?: number,
    activeOnly?: boolean
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;



  /** Get win rate leaderboard */
  getWinRate: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;



  getMetaReport: () => Promise<AxiosResponse<MetaReportResponse>>;

  /** Generic getter by category key */
  getByCategory: (
    category: LeaderboardCategoryKey,
    options?: {
      limit?: number;
      minGames?: number;
      activeOnly?: boolean;
    }
  ) => Promise<
    AxiosResponse<LeaderboardEntry[]>
  >;
}

export const leaderboardApi: LeaderboardApi = {
  getMMR: (limit = 20, minGames = 5, activeOnly = false) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/mmr', {
      params: { limit, min_games: minGames, active_only: activeOnly },
    });
  },



  getWinRate: (limit = 20, minGames = 20) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/winrate', {
      params: { limit, min_games: minGames },
    });
  },



  getMetaReport: () => {
    return apiClient.get<MetaReportResponse>('/leaderboard/meta-report');
  },

  getByCategory: (category, options = {}) => {

    const { limit = 20, minGames, activeOnly } = options;

    switch (category) {
      case 'mmr':
        return leaderboardApi.getMMR(limit, minGames, activeOnly);
      case 'winrate':
        return leaderboardApi.getWinRate(limit, minGames || 20);
      default:
        return leaderboardApi.getMMR(limit, minGames);
    }
  },
};

export default leaderboardApi;
