/**
 * Leaderboard API Client
 * Streamlined to 5 core categories
 */
import { AxiosResponse } from 'axios';
import apiClient from './client';
import type {
  LeaderboardEntry,
  DuoLeaderboardEntry,
  LeaderboardCategoryKey,
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

  /** Get recent form leaderboard (14-day half-life weighted) */
  getRecentForm: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get combat leaderboard */
  getCombat: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get win rate leaderboard */
  getWinRate: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get win streak leaderboard */
  getWinStreak: (
    limit?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get longest matches leaderboard (each player's own longest game) */
  getLongestMatches: (
    limit?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get best duos leaderboard */
  getDuos: (
    limit?: number,
    minGames?: number,
    sortBy?: 'wins' | 'winrate' | 'synergy'
  ) => Promise<AxiosResponse<DuoLeaderboardEntry[]>>;

  /** Get best trios leaderboard */
  getTrios: (
    limit?: number,
    minGames?: number,
    sortBy?: 'wins' | 'winrate' | 'synergy'
  ) => Promise<AxiosResponse<TrioLeaderboardEntry[]>>;

  /** Generic getter by category key */
  getMetaReport: () => Promise<AxiosResponse<any>>;
}

export const leaderboardApi: LeaderboardApi = {
  getMMR: (limit = 20, minGames = 5, activeOnly = false) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/mmr', {
      params: { limit, min_games: minGames, active_only: activeOnly },
    });
  },

  getRecentForm: (limit = 20, minGames = 10) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/recent-form', {
      params: { limit, min_games: minGames },
    });
  },

  getCombat: (limit = 20, minGames = 5) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/specialists', {
      params: { category: 'combat', limit, min_games: minGames },
    });
  },

  getWinRate: (limit = 20, minGames = 20) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/winrate', {
      params: { limit, min_games: minGames },
    });
  },

  getWinStreak: (limit = 20) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/winstreak', {
      params: { limit },
    });
  },

  getLongestMatches: (limit = 20) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/longest-matches', {
      params: { limit },
    });
  },

  getDuos: (limit = 20, minGames = 5, sortBy = 'wins') => {
    return apiClient.get<DuoLeaderboardEntry[]>('/leaderboard/duos', {
      params: { limit, min_games: minGames, sort_by: sortBy },
    });
  },

  getTrios: (limit = 20, minGames = 5, sortBy = 'wins') => {
    return apiClient.get<TrioLeaderboardEntry[]>('/leaderboard/trios', {
      params: { limit, min_games: minGames, sort_by: sortBy },
    });
  },

  getMetaReport: () => {
    return apiClient.get('/leaderboard/meta-report');
  },

  getByCategory: (category, options = {}) => {

    const { limit = 20, minGames, sortBy, activeOnly } = options;

    switch (category) {
      case 'mmr':
        return leaderboardApi.getMMR(limit, minGames, activeOnly);
      case 'recent-form':
        return leaderboardApi.getRecentForm(limit, minGames || 10);
      case 'combat':
        return leaderboardApi.getCombat(limit, minGames);
      case 'winrate':
        return leaderboardApi.getWinRate(limit, minGames || 20);
      case 'winstreak':
        return leaderboardApi.getWinStreak(limit);
      case 'longest-matches':
        return leaderboardApi.getLongestMatches(limit);
      case 'duos':
        return leaderboardApi.getDuos(
          limit,
          minGames || 5,
          (sortBy as 'wins' | 'winrate' | 'synergy') || 'wins'
        );
      case 'trios':
        return leaderboardApi.getTrios(
          limit,
          minGames || 5,
          (sortBy as 'wins' | 'winrate' | 'synergy') || 'wins'
        );
      default:
        return leaderboardApi.getMMR(limit, minGames);
    }
  },
};

export default leaderboardApi;
