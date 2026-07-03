/**
 * Head-to-Head API Client
 * API calls for H2H/rivalry-related endpoints
 */
import { AxiosResponse } from 'axios';
import apiClient from './client';
import type {
  HeadToHeadResponse,
  RivalryResponse,
} from '@/types/headtohead';

// =============================================================================
// Head-to-Head API Interface
// =============================================================================

export interface HeadToHeadApi {
  /** Get detailed comparison between two players */
  getComparison: (
    player1Id: number,
    player2Id: number
  ) => Promise<AxiosResponse<HeadToHeadResponse>>;

  /** Get top rivals for a specific player */
  getPlayerRivals: (
    playerId: number,
    limit?: number
  ) => Promise<AxiosResponse<RivalryResponse[]>>;

  /** Get the biggest rivalries server-wide */
  getBiggestRivalries: (
    limit?: number
  ) => Promise<AxiosResponse<RivalryResponse[]>>;
}

// =============================================================================
// API Implementation
// =============================================================================

export const headToHeadApi: HeadToHeadApi = {
  // Get H2H comparison
  getComparison: (player1Id: number, player2Id: number) => {
    return apiClient.get<HeadToHeadResponse>(
      `/h2h/${player1Id}/${player2Id}`
    );
  },

  // Get player's top rivals
  getPlayerRivals: (playerId: number, limit = 10) => {
    return apiClient.get<RivalryResponse[]>(
      `/h2h/${playerId}/rivals`,
      { params: { limit } }
    );
  },

  // Get biggest rivalries
  getBiggestRivalries: (limit = 20) => {
    return apiClient.get<RivalryResponse[]>(
      '/h2h/biggest-rivalries',
      { params: { limit } }
    );
  },
};

export default headToHeadApi;
