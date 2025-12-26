/**
 * Leaderboard Type Definitions for SC2 MMR Tracker
 *
 * These types match the backend Pydantic models in:
 * - backend/app/api/leaderboard.py
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
}

/** Duo leaderboard entry for partnership rankings */
export interface DuoLeaderboardEntry {
  rank: number;
  player1_id: number;
  player1_name: string;
  player2_id: number;
  player2_name: string;
  wins_together: number;
  games_together: number;
  win_rate: number;
  synergy_score: number;
}

// =============================================================================
// Leaderboard Category Types
// =============================================================================

export type LeaderboardCategoryKey =
  | 'mmr'
  | 'winrate'
  | 'games'
  | 'achievements'
  | 'damage'
  | 'kills'
  | 'winstreak'
  | 'duos';

export interface LeaderboardCategory {
  key: LeaderboardCategoryKey;
  name: string;
  description: string;
  unit: string;
  icon: string;
}

/** All available leaderboard categories */
export const LEADERBOARD_CATEGORIES: LeaderboardCategory[] = [
  {
    key: 'mmr',
    name: 'MMR Rankings',
    description: 'Overall skill rating',
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
  {
    key: 'games',
    name: 'Most Games',
    description: 'Total matches played',
    unit: 'games',
    icon: '🎮',
  },
  {
    key: 'achievements',
    name: 'Achievement Points',
    description: 'Total achievement score',
    unit: 'pts',
    icon: '🎖️',
  },
  {
    key: 'damage',
    name: 'Damage Kings',
    description: 'Highest average damage per game',
    unit: 'dmg',
    icon: '⚔️',
  },
  {
    key: 'kills',
    name: 'Unit Slayers',
    description: 'Most units killed on average',
    unit: 'kills',
    icon: '💀',
  },
  {
    key: 'winstreak',
    name: 'Best Win Streak',
    description: 'Longest winning streak ever',
    unit: 'games',
    icon: '🔥',
  },
  {
    key: 'duos',
    name: 'Best Duos',
    description: 'Most successful partner combinations',
    unit: 'wins',
    icon: '🤝',
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
  switch (category) {
    case 'mmr':
      return Math.round(value).toLocaleString();
    case 'winrate':
      return `${value.toFixed(1)}%`;
    case 'games':
    case 'winstreak':
      return value.toLocaleString();
    case 'achievements':
      return `${value.toLocaleString()} pts`;
    case 'damage':
      return value >= 1000
        ? `${(value / 1000).toFixed(1)}k`
        : Math.round(value).toString();
    case 'kills':
      return Math.round(value).toLocaleString();
    case 'duos':
      return value.toLocaleString();
    default:
      return value.toString();
  }
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

/** Check if category uses duo format */
export function isDuoCategory(category: LeaderboardCategoryKey): boolean {
  return category === 'duos';
}
