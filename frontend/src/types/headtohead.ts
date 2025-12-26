/**
 * Head-to-Head Type Definitions for SC2 MMR Tracker
 *
 * These types match the backend Pydantic models in:
 * - backend/app/api/headtohead.py
 */

// =============================================================================
// Head-to-Head Response Types
// =============================================================================

/** Player summary in H2H context */
export interface H2HPlayerSummary {
  id: number;
  name: string;
  mmr: number;
  wins: number;
  favorite_race: string;
}

/** Head-to-head statistics */
export interface HeadToHeadStats {
  total_games: number;
  player1_wins: number;
  player2_wins: number;
  win_rate_player1: number;
  last_match_date: string | null;
  avg_mmr_swing: number;
  rivalry_score: number;
  rivalry_intensity: RivalryIntensity;
}

/** Match summary in H2H context */
export interface H2HMatchSummary {
  match_id: number;
  date: string;
  winner_id: number;
  map_name: string;
  duration_seconds: number;
}

/** Complete H2H response */
export interface HeadToHeadResponse {
  player1: H2HPlayerSummary;
  player2: H2HPlayerSummary;
  head_to_head: HeadToHeadStats;
  recent_matches: H2HMatchSummary[];
}

// =============================================================================
// Rivalry Types
// =============================================================================

export type RivalryIntensity = 'Casual' | 'Competitive' | 'Fierce' | 'Epic';

/** Rivalry entry for lists */
export interface RivalryResponse {
  player1_id: number;
  player1_name: string;
  player2_id: number;
  player2_name: string;
  games: number;
  score: number;
  intensity: RivalryIntensity;
}

// =============================================================================
// Rivalry Intensity Configuration
// =============================================================================

export interface IntensityConfig {
  label: string;
  color: string;
  bgColor: string;
  glowColor: string;
  description: string;
  minScore: number;
}

export const INTENSITY_CONFIG: Record<RivalryIntensity, IntensityConfig> = {
  Casual: {
    label: 'Casual',
    color: '#9CA3AF',
    bgColor: 'rgba(156, 163, 175, 0.2)',
    glowColor: 'rgba(156, 163, 175, 0.3)',
    description: 'Few encounters',
    minScore: 0,
  },
  Competitive: {
    label: 'Competitive',
    color: '#60A5FA',
    bgColor: 'rgba(96, 165, 250, 0.2)',
    glowColor: 'rgba(96, 165, 250, 0.4)',
    description: 'Regular opponents',
    minScore: 40,
  },
  Fierce: {
    label: 'Fierce',
    color: '#F59E0B',
    bgColor: 'rgba(245, 158, 11, 0.2)',
    glowColor: 'rgba(245, 158, 11, 0.5)',
    description: 'Intense rivalry',
    minScore: 60,
  },
  Epic: {
    label: 'Epic',
    color: '#EF4444',
    bgColor: 'rgba(239, 68, 68, 0.2)',
    glowColor: 'rgba(239, 68, 68, 0.6)',
    description: 'Legendary showdowns',
    minScore: 80,
  },
};

/** Get intensity configuration */
export function getIntensityConfig(intensity: RivalryIntensity): IntensityConfig {
  return INTENSITY_CONFIG[intensity] || INTENSITY_CONFIG.Casual;
}

/** Calculate intensity from score */
export function getIntensityFromScore(score: number): RivalryIntensity {
  if (score >= 80) return 'Epic';
  if (score >= 60) return 'Fierce';
  if (score >= 40) return 'Competitive';
  return 'Casual';
}

// =============================================================================
// Utility Functions
// =============================================================================

/** Format rivalry score for display */
export function formatRivalryScore(score: number): string {
  return Math.round(score).toString();
}

/** Get win rate display for a player in H2H */
export function getH2HWinRate(wins: number, totalGames: number): string {
  if (totalGames === 0) return '0%';
  return `${((wins / totalGames) * 100).toFixed(0)}%`;
}

/** Get the other player in a rivalry */
export function getOpponentFromRivalry(
  rivalry: RivalryResponse,
  playerId: number
): { id: number; name: string } {
  if (rivalry.player1_id === playerId) {
    return { id: rivalry.player2_id, name: rivalry.player2_name };
  }
  return { id: rivalry.player1_id, name: rivalry.player1_name };
}

/** Format match duration */
export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/** Check if a match was an upset based on predictions */
export function wasUpset(
  winnerId: number,
  player1Id: number,
  player1WinRate: number
): boolean {
  const expectedWinner = player1WinRate >= 0.5 ? player1Id : -1;
  return winnerId !== expectedWinner;
}
