/**
 * Leaderboard Type Definitions for SC2 MMR Tracker
 *
 * Two boards:
 * - MMR (display MMR, the rating of record: 1000 + 100*mu - 200*sigma)
 * - Win Rate
 */

// =============================================================================
// Leaderboard Entry Types
// =============================================================================

/** Generic leaderboard entry for most categories */
export interface LeaderboardEntry {
  rank: number;
  player_id: number;
  name: string;
  value: number;
  secondary_value?: number;
  extra_info?: string;
  is_new?: boolean;
  is_active?: boolean;
  days_since_played?: number | null;
}

// =============================================================================
// Leaderboard Category Types
// =============================================================================

export type LeaderboardCategoryKey = 'mmr' | 'winrate';

/** Squad-wide meta report: race win rates and the archetypes that win most */
export interface MetaReportResponse {
  squad_win_rate_by_race: Record<string, number>;
  top_compositions: Record<string, unknown>[];
  most_effective_archetypes: Array<{
    type: string;
    win_rate: number;
    games: number;
  }>;
}

export interface LeaderboardCategory {
  key: LeaderboardCategoryKey;
  name: string;
  description: string;
  unit: string;
  icon: string;
}

export const LEADERBOARD_CATEGORIES: LeaderboardCategory[] = [
  {
    key: 'mmr',
    name: 'MMR',
    description: 'Overall skill rating (TrueSkill-based MMR)',
    unit: 'MMR',
    icon: '🏆',
  },
  {
    key: 'winrate',
    name: 'Win Rate',
    description: 'Highest win percentage (min 20 games)',
    unit: '%',
    icon: '📈',
  },
];

/** Get category by key */
export function getLeaderboardCategory(key: LeaderboardCategoryKey): LeaderboardCategory | undefined {
  return LEADERBOARD_CATEGORIES.find(cat => cat.key === key);
}

// =============================================================================
// Utility Functions
// =============================================================================

/** Format leaderboard value based on category */
export function formatLeaderboardValue(value: number, category: LeaderboardCategoryKey): string {
  return category === 'winrate' ? `${value.toFixed(1)}%` : Math.round(value).toLocaleString();
}

/** Get medal emoji for top 3 ranks */
export function getRankMedal(rank: number): string {
  switch (rank) {
    case 1: return '🥇';
    case 2: return '🥈';
    case 3: return '🥉';
    default: return '';
  }
}

