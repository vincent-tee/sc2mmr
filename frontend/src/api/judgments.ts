/** Private organizer judgments and selected-game capture; uses the shared API client. */
import { AxiosResponse } from 'axios';
import apiClient from './client';

// =============================================================================
// Shared enums (mirrors backend/app/models.py)
// =============================================================================

export type HumanEstimate = 'even' | 'team1_favored' | 'team2_favored';
export type JudgmentConfidence = 'low' | 'medium' | 'high';
export type JudgmentReason =
  | 'off_race'
  | 'returning_player'
  | 'current_form'
  | 'communication'
  | 'map'
  | 'known_synergy'
  | 'other';
export type PostgameFeedbackType = 'felt_balanced' | 'one_sided' | 'snowballed_early' | 'disconnect' | 'other';

export interface PlayerRaceContext {
  player_id: number;
  race: string;
}

// =============================================================================
// Pre-game judgment types
// =============================================================================

export interface CreateJudgmentRequest {
  team1_player_ids: number[];
  team2_player_ids: number[];

  map_name?: string | null;
  team1_context?: PlayerRaceContext[] | null;
  team2_context?: PlayerRaceContext[] | null;

  model_version?: string | null;
  model_predicted_team1_win_prob?: number | null;
  balance_prediction_id?: number | null;
  match_id?: number | null;

  human_estimate: HumanEstimate;
  human_win_prob?: number | null;
  confidence: JudgmentConfidence;
  reason: JudgmentReason;
  reason_note?: string | null;

  author: string;
}

export interface UpdateJudgmentRequest {
  human_estimate?: HumanEstimate;
  human_win_prob?: number | null;
  confidence?: JudgmentConfidence;
  reason?: JudgmentReason;
  reason_note?: string | null;
}

export interface JudgmentResponse {
  id: number;
  selection_id: number | null;
  created_at: string;
  balance_prediction_id: number | null;
  match_id: number | null;
  team1_player_ids_key: string;
  team2_player_ids_key: string;
  map_name: string | null;
  team1_context: PlayerRaceContext[] | null;
  team2_context: PlayerRaceContext[] | null;
  model_version: string | null;
  model_predicted_team1_win_prob: number | null;
  human_estimate: HumanEstimate;
  human_win_prob: number | null;
  confidence: JudgmentConfidence;
  reason: JudgmentReason;
  reason_note: string | null;
  author: string;
  is_locked: boolean;
  locked_at: string | null;
}

// =============================================================================
// Post-game feedback types
// =============================================================================

export interface CreateFeedbackRequest {
  judgment_id?: number | null;
  match_id?: number | null;
  feedback: PostgameFeedbackType;
  note?: string | null;
  author: string;
}

export interface FeedbackResponse {
  id: number;
  created_at: string;
  judgment_id: number | null;
  match_id: number | null;
  feedback: PostgameFeedbackType;
  note: string | null;
  author: string;
}

// =============================================================================
// API
// =============================================================================

export interface JudgmentsApi {
  create: (request: CreateJudgmentRequest) => Promise<AxiosResponse<JudgmentResponse>>;
  list: (filters?: { matchId?: number; balancePredictionId?: number }) => Promise<AxiosResponse<JudgmentResponse[]>>;
  getById: (judgmentId: number) => Promise<AxiosResponse<JudgmentResponse>>;
  update: (judgmentId: number, request: UpdateJudgmentRequest) => Promise<AxiosResponse<JudgmentResponse>>;
  lock: (judgmentId: number) => Promise<AxiosResponse<JudgmentResponse>>;
  createFeedback: (request: CreateFeedbackRequest) => Promise<AxiosResponse<FeedbackResponse>>;
  listFeedback: (filters?: { matchId?: number; judgmentId?: number }) => Promise<AxiosResponse<FeedbackResponse[]>>;
}

export const judgmentsApi: JudgmentsApi = {
  create: (request: CreateJudgmentRequest) => {
    return apiClient.post<JudgmentResponse>('/judgments', request);
  },

  list: (filters?: { matchId?: number; balancePredictionId?: number }) => {
    return apiClient.get<JudgmentResponse[]>('/judgments', {
      params: {
        match_id: filters?.matchId,
        balance_prediction_id: filters?.balancePredictionId,
      },
    });
  },

  getById: (judgmentId: number) => {
    return apiClient.get<JudgmentResponse>(`/judgments/${judgmentId}`);
  },

  update: (judgmentId: number, request: UpdateJudgmentRequest) => {
    return apiClient.patch<JudgmentResponse>(`/judgments/${judgmentId}`, request);
  },

  lock: (judgmentId: number) => {
    return apiClient.post<JudgmentResponse>(`/judgments/${judgmentId}/lock`);
  },

  createFeedback: (request: CreateFeedbackRequest) => {
    return apiClient.post<FeedbackResponse>('/judgments/feedback', request);
  },

  listFeedback: (filters?: { matchId?: number; judgmentId?: number }) => {
    return apiClient.get<FeedbackResponse[]>('/judgments/feedback/list', {
      params: {
        match_id: filters?.matchId,
        judgment_id: filters?.judgmentId,
      },
    });
  },
};

export default judgmentsApi;

export interface BalanceSelection {
  id: number;
  started_at: string;
  team1_ids_key: string;
  team2_ids_key: string;
  map_name: string | null;
  match_id: number | null;
}

export const selectionsApi = {
  candidates: (matchId: number) => apiClient.get<BalanceSelection[]>(`/judgments/selections/candidates/${matchId}`),
  attach: (selectionId: number, matchId: number) => apiClient.post(`/judgments/selections/${selectionId}/match/${matchId}`),
};
