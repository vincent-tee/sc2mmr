/**
 * Leaderboard Type Definitions for SC2 MMR Tracker
 *
 * Streamlined to 5 core categories:
 * - MMR (display MMR, the rating of record: 1000 + 100*mu - 200*sigma)
 * - Combat (in-game contribution)
 * - Win Rate (fundamental stat)
 * - Win Streak (engagement/fun)
 * - Duos (partnership rankings)
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
  | 'recent-form'
  | 'combat'
  | 'winrate'
  | 'winstreak'
  | 'duos'
  | 'trios';

export interface TrioLeaderboardEntry {
  rank: number;
  player_ids: number[];
  player_names: string[];
  wins_together: number;
  games_together: number;
  win_rate: number;
  synergy_score: number;
}

export interface LeaderboardCategory {
  key: LeaderboardCategoryKey;
  name: string;
  description: string;
  unit: string;
  icon: string;
}

/** Streamlined leaderboard categories - 6 core boards */
export const LEADERBOARD_CATEGORIES: LeaderboardCategory[] = [
  {
    key: 'mmr',
    name: 'MMR',
    description: 'Overall skill rating (TrueSkill-based MMR)',
    unit: 'MMR',
    icon: '🏆',
  },
  {
    key: 'recent-form',
    name: 'Recent Form',
    description: 'Performance weighted by last 30 matches',
    unit: 'MMR',
    icon: '📊',
  },
  {
    key: 'combat',
    name: 'Combat',
    description: 'Damage dealers and unit killers',
    unit: 'score',
    icon: '⚔️',
  },
  {
    key: 'winrate',
    name: 'Win Rate',
    description: 'Highest win percentage (min 20 games)',
    unit: '%',
    icon: '📈',
  },
  {
    key: 'winstreak',
    name: 'Hot Streak',
    description: 'Longest winning streak',
    unit: 'wins',
    icon: '🔥',
  },
  {
    key: 'duos',
    name: 'Best Duos',
    description: 'Most successful partnerships',
    unit: 'wins',
    icon: '👥',
  },
  {
    key: 'trios',
    name: 'Best Trios',
    description: 'Most successful trios',
    unit: 'wins',
    icon: '👨‍👩‍👦',
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
    case 'recent-form':
      return Math.round(value).toLocaleString();
    case 'winrate':
      return `${value.toFixed(1)}%`;
    case 'winstreak':
      return value.toLocaleString();
    case 'combat':
      return value.toFixed(1);
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
