import apiClient from './client';
import type { ResultSource } from '../types/api';

export interface ResultReviewItem {
  match_id: number;
  played_at: string;
  map_name: string;
  duration_seconds: number;
  result_source: ResultSource | null;
  winner_team: number | null;
  supply_frame: number | null;
  team_supply: Record<string, number>;
  supply_favourite_team: number | null;
  supply_ratio: number | null;
  other_recordings: { replay_hash: string; winner_team: number }[];
  conflicts: boolean;
  rosters: { team: number; players: string[] }[];
}

export interface ResultReviewQueue {
  total: number;
  conflicts: number;
  unchecked: number;
  items: ResultReviewItem[];
}

export interface ConfirmResultResponse {
  changed: boolean;
  item: ResultReviewItem;
}

export const matchResultsApi = {
  reviewQueue: () => apiClient.get<ResultReviewQueue>('/match-results/review'),
  confirm: (matchId: number, winnerTeam: number, confirmedBy: string) =>
    apiClient.post<ConfirmResultResponse>(`/match-results/${matchId}/confirm`, {
      winner_team: winnerTeam,
      confirmed_by: confirmedBy,
    }),
};
