/**
 * Achievements API Client
 * API calls for achievement-related endpoints
 */
import { AxiosResponse } from 'axios';
import apiClient from './client';
import type {
  Achievement,
  PlayerAchievementsResponse,
  AchievementLeaderboardEntry,
  RecentAchievementEntry,
  RarestAchievementEntry,
  AchievementInitResponse,
  AchievementCheckResponse,
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
  getLeaderboard: (
    limit?: number
  ) => Promise<AxiosResponse<AchievementLeaderboardEntry[]>>;

  /** Get most recently earned achievements */
  getRecent: (
    limit?: number
  ) => Promise<AxiosResponse<RecentAchievementEntry[]>>;

  /** Get rarest achievements */
  getRarest: (
    limit?: number
  ) => Promise<AxiosResponse<RarestAchievementEntry[]>>;

  /** Get all achievement definitions */
  getAll: (
    includeHidden?: boolean
  ) => Promise<AxiosResponse<Achievement[]>>;

  /** Initialize achievement definitions */
  init: () => Promise<AxiosResponse<AchievementInitResponse>>;

  /** Check and award achievements for a player */
  checkPlayer: (
    playerId: number,
    matchId?: number
  ) => Promise<AxiosResponse<AchievementCheckResponse>>;

  /** Check and award achievements for all players */
  checkAll: () => Promise<AxiosResponse<{
    players_checked: number;
    players_with_new_achievements: number;
    results: AchievementCheckResponse[];
  }>>;

  /** Set a player's featured achievement */
  setFeatured: (
    playerId: number,
    achievementCode: string
  ) => Promise<AxiosResponse<{ success: boolean; featured_achievement: string }>>;
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

  // Get achievement leaderboard
  getLeaderboard: (limit = 20) => {
    return apiClient.get<AchievementLeaderboardEntry[]>(
      '/achievements/leaderboard',
      { params: { limit } }
    );
  },

  // Get recent achievements
  getRecent: (limit = 20) => {
    return apiClient.get<RecentAchievementEntry[]>(
      '/achievements/recent',
      { params: { limit } }
    );
  },

  // Get rarest achievements
  getRarest: (limit = 10) => {
    return apiClient.get<RarestAchievementEntry[]>(
      '/achievements/rarest',
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

  // Initialize achievements
  init: () => {
    return apiClient.post<AchievementInitResponse>('/achievements/init');
  },

  // Check player achievements
  checkPlayer: (playerId: number, matchId?: number) => {
    return apiClient.post<AchievementCheckResponse>(
      `/achievements/check/${playerId}`,
      null,
      { params: matchId ? { match_id: matchId } : undefined }
    );
  },

  // Check all players
  checkAll: () => {
    return apiClient.post('/achievements/check-all');
  },

  // Set featured achievement
  setFeatured: (playerId: number, achievementCode: string) => {
    return apiClient.post(
      `/achievements/player/${playerId}/feature/${achievementCode}`
    );
  },
};

export default achievementsApi;
