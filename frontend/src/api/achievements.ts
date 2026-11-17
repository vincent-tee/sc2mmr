/**
 * Achievements API Client
 * API calls for achievement-related endpoints
 */
import { AxiosResponse } from 'axios';
import apiClient from './client';
import type {
  Achievement,
  PlayerAchievementsResponse,
  RecentAchievementEntry,
} from '@/types/achievements';

// =============================================================================
// Achievements API Interface
// =============================================================================

export interface AchievementsApi {
  /** Get all achievements for a specific player */
  getPlayerAchievements: (
    playerId: number,
    includeAvailable?: boolean
  ) => Promise<AxiosResponse<PlayerAchievementsResponse>>;

  /** Get achievement points leaderboard */

  /** Get most recently earned achievements */
  getRecent: (
    limit?: number
  ) => Promise<AxiosResponse<RecentAchievementEntry[]>>;

  /** Get rarest achievements */

  /** Get all achievement definitions */
  getAll: (
    includeHidden?: boolean
  ) => Promise<AxiosResponse<Achievement[]>>;

  /** Initialize achievement definitions */

  /** Check and award achievements for a player */

  /** Check and award achievements for all players */

  /** Set a player's featured achievement */
}

// =============================================================================
// API Implementation
// =============================================================================

export const achievementsApi: AchievementsApi = {
  // Get player achievements
  getPlayerAchievements: (playerId: number, includeAvailable = false) => {
    return apiClient.get<PlayerAchievementsResponse>(
      `/achievements/player/${playerId}`,
      { params: { include_available: includeAvailable } }
    );
  },

  // Get recent achievements
  getRecent: (limit = 20) => {
    return apiClient.get<RecentAchievementEntry[]>(
      '/achievements/recent',
      { params: { limit } }
    );
  },

  // Get all achievement definitions
  getAll: (includeHidden = false) => {
    return apiClient.get<Achievement[]>(
      '/achievements/all',
      { params: { include_hidden: includeHidden } }
    );
  },
};

export default achievementsApi;
