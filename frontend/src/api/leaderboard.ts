/**
 * Leaderboard API Client
 * API calls for leaderboard-related endpoints
 */
import { AxiosResponse } from 'axios';
import apiClient from './client';
import type {
  LeaderboardEntry,
  DuoLeaderboardEntry,
  LeaderboardCategory,
  LeaderboardCategoryKey,
} from '@/types/leaderboard';

// =============================================================================
// Leaderboard API Interface
// =============================================================================

export interface LeaderboardApi {
  /** Get available leaderboard categories */
  getCategories: () => Promise<AxiosResponse<LeaderboardCategory[]>>;

  /** Get MMR leaderboard */
  getMMR: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get TrueSkill leaderboard */
  getTrueSkill: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get Hybrid MMR leaderboard */
  getHybrid: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get win rate leaderboard */
  getWinRate: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get games played leaderboard */
  getGames: (
    limit?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get achievement points leaderboard */
  getAchievements: (
    limit?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get damage leaderboard */
  getDamage: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get kills leaderboard */
  getKills: (
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get win streak leaderboard */
  getWinStreak: (
    limit?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Get best duos leaderboard */
  getDuos: (
    limit?: number,
    minGames?: number,
    sortBy?: 'wins' | 'winrate' | 'synergy'
  ) => Promise<AxiosResponse<DuoLeaderboardEntry[]>>;

  /** Get race-specific leaderboard */
  getRace: (
    race: 'terran' | 'protoss' | 'zerg',
    limit?: number,
    minGames?: number
  ) => Promise<AxiosResponse<LeaderboardEntry[]>>;

  /** Generic getter by category key */
  getByCategory: (
    category: LeaderboardCategoryKey,
    options?: { limit?: number; minGames?: number; sortBy?: string }
  ) => Promise<AxiosResponse<LeaderboardEntry[] | DuoLeaderboardEntry[]>>;
}

// =============================================================================
// API Implementation
// =============================================================================

export const leaderboardApi: LeaderboardApi = {
  // Get categories
  getCategories: () => {
    return apiClient.get<LeaderboardCategory[]>('/leaderboard/categories');
  },

  // Get MMR leaderboard
  getMMR: (limit = 20, minGames = 5) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/mmr', {
      params: { limit, min_games: minGames },
    });
  },

  // Get TrueSkill leaderboard
  getTrueSkill: (limit = 20, minGames = 5) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/trueskill', {
      params: { limit, min_games: minGames },
    });
  },

  // Get Hybrid leaderboard
  getHybrid: (limit = 20, minGames = 5) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/hybrid', {
      params: { limit, min_games: minGames },
    });
  },

  // Get win rate leaderboard
  getWinRate: (limit = 20, minGames = 20) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/winrate', {
      params: { limit, min_games: minGames },
    });
  },

  // Get games leaderboard
  getGames: (limit = 20) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/games', {
      params: { limit },
    });
  },

  // Get achievements leaderboard
  getAchievements: (limit = 20) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/achievements', {
      params: { limit },
    });
  },

  // Get damage leaderboard
  getDamage: (limit = 20, minGames = 10) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/damage', {
      params: { limit, min_games: minGames },
    });
  },

  // Get kills leaderboard
  getKills: (limit = 20, minGames = 10) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/kills', {
      params: { limit, min_games: minGames },
    });
  },

  // Get win streak leaderboard
  getWinStreak: (limit = 20) => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard/winstreak', {
      params: { limit },
    });
  },

  // Get duos leaderboard
  getDuos: (limit = 20, minGames = 10, sortBy = 'wins') => {
    return apiClient.get<DuoLeaderboardEntry[]>('/leaderboard/duos', {
      params: { limit, min_games: minGames, sort_by: sortBy },
    });
  },

  // Get race leaderboard
  getRace: (race, limit = 20, minGames = 10) => {
    return apiClient.get<LeaderboardEntry[]>(`/leaderboard/race/${race}`, {
      params: { limit, min_games: minGames },
    });
  },

  // Generic getter by category
  getByCategory: (category, options = {}) => {
    const { limit = 20, minGames, sortBy } = options;

    switch (category) {
      case 'mmr':
        return leaderboardApi.getMMR(limit, minGames);
      case 'trueskill':
        return leaderboardApi.getTrueSkill(limit, minGames);
      case 'hybrid':
        return leaderboardApi.getHybrid(limit, minGames);
      case 'winrate':
        return leaderboardApi.getWinRate(limit, minGames || 20);
      case 'games':
        return leaderboardApi.getGames(limit);
      case 'achievements':
        return leaderboardApi.getAchievements(limit);
      case 'damage':
        return leaderboardApi.getDamage(limit, minGames);
      case 'kills':
        return leaderboardApi.getKills(limit, minGames);
      case 'winstreak':
        return leaderboardApi.getWinStreak(limit);
      case 'duos':
        return leaderboardApi.getDuos(
          limit,
          minGames,
          (sortBy as 'wins' | 'winrate' | 'synergy') || 'wins'
        );
      default:
        return leaderboardApi.getMMR(limit, minGames);
    }
  },
};

export default leaderboardApi;
