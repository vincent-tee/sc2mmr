/**
 * Achievement Type Definitions for SC2 MMR Tracker
 *
 * These types match the backend Pydantic models in:
 * - backend/app/api/achievements.py
 * - backend/app/models/achievements.py
 */

// =============================================================================
// Achievement Enums
// =============================================================================

export type AchievementRarity =
  | 'common'
  | 'uncommon'
  | 'rare'
  | 'epic'
  | 'legendary'
  | 'mythic';

export type AchievementCategory =
  | 'milestone'
  | 'streak'
  | 'combat'
  | 'economic'
  | 'teamwork'
  | 'variety'
  | 'special'
  | 'meme'
  | 'esports';

// =============================================================================
// Achievement Types
// =============================================================================

/** Base achievement definition */
export interface Achievement {
  code: string;
  name: string;
  description: string;
  flavor_text?: string;
  category: AchievementCategory;
  rarity: AchievementRarity;
  icon?: string;       // Emoji like "🔥" or "👑"
  color?: string;      // Hex color for custom styling
  points: number;
  is_hidden: boolean;
}

/** Achievement with earned status (for player's achievement list) */
export interface PlayerAchievement extends Achievement {
  earned_at?: string;
  trigger_value?: number;
  is_featured: boolean;
}

/** Player's complete achievement summary */
export interface PlayerAchievementsResponse {
  player_id: number;
  player_name: string;
  total_achievements: number;
  total_points: number;
  // NOTE: matches backend PlayerAchievementsResponse.awarded
  // (backend/app/api/achievements.py) - this field was previously misnamed
  // "achievements" here, which didn't match the actual API response; fixed
  // since PlayerDetail.tsx already reads `.awarded` at runtime.
  awarded: PlayerAchievement[];
  available_achievements?: Achievement[];
}

/** Leaderboard entry for achievement rankings */
export interface AchievementLeaderboardEntry {
  rank: number;
  player_id: number;
  name: string;
  total_achievements: number;
  total_points: number;
}

/** Recent achievement feed entry */
export interface RecentAchievementEntry {
  player_name: string;
  player_id: number;
  achievement_code: string;
  achievement_name: string;
  achievement_icon?: string;
  rarity: AchievementRarity;
  earned_at: string;
}

/** Rarest achievement entry */
export interface RarestAchievementEntry {
  code: string;
  name: string;
  description: string;
  icon?: string;
  rarity: AchievementRarity;
  points: number;
  earned_count: number;
  earned_by: Array<{
    player_id: number;
    player_name: string;
    earned_at: string;
  }>;
}

/** Achievement initialization response */
export interface AchievementInitResponse {
  success: boolean;
  created: number;
  message: string;
}

/** Achievement check response */
export interface AchievementCheckResponse {
  player_id: number;
  player_name: string;
  newly_awarded: string[];
  count: number;
}

// =============================================================================
// Rarity Color Configuration
// =============================================================================

/** Rarity visual configuration for badge styling */
export interface RarityColors {
  bg: string;
  border: string;
  glow: string;
  text?: string;
}

export const RARITY_COLORS: Record<AchievementRarity, RarityColors> = {
  common: {
    bg: '#374151',
    border: '#6B7280',
    glow: 'none',
    text: '#9CA3AF',
  },
  uncommon: {
    bg: '#065F46',
    border: '#10B981',
    glow: '0 0 10px rgba(16, 185, 129, 0.5)',
    text: '#10B981',
  },
  rare: {
    bg: '#1E40AF',
    border: '#3B82F6',
    glow: '0 0 15px rgba(59, 130, 246, 0.5)',
    text: '#60A5FA',
  },
  epic: {
    bg: '#5B21B6',
    border: '#8B5CF6',
    glow: '0 0 20px rgba(139, 92, 246, 0.5)',
    text: '#A78BFA',
  },
  legendary: {
    bg: '#92400E',
    border: '#F59E0B',
    glow: '0 0 25px rgba(245, 158, 11, 0.6)',
    text: '#FBBF24',
  },
  mythic: {
    bg: '#831843',
    border: '#EC4899',
    glow: '0 0 30px rgba(236, 72, 153, 0.6), 0 0 60px rgba(236, 72, 153, 0.3)',
    text: '#F472B6',
  },
};

/** Get rarity color configuration */
export function getRarityColors(rarity: AchievementRarity): RarityColors {
  return RARITY_COLORS[rarity] || RARITY_COLORS.common;
}

/** Get rarity display name with proper casing */
export function getRarityLabel(rarity: AchievementRarity): string {
  return rarity.charAt(0).toUpperCase() + rarity.slice(1);
}

/** Get points multiplier hint based on rarity */
export function getRarityPointsHint(rarity: AchievementRarity): string {
  const hints: Record<AchievementRarity, string> = {
    common: '5-10 pts',
    uncommon: '15-25 pts',
    rare: '30-50 pts',
    epic: '60-80 pts',
    legendary: '100-150 pts',
    mythic: '200+ pts',
  };
  return hints[rarity];
}

// =============================================================================
// Category Configuration
// =============================================================================

export interface CategoryInfo {
  name: string;
  icon: string;
  description: string;
}

export const CATEGORY_INFO: Record<AchievementCategory, CategoryInfo> = {
  milestone: {
    name: 'Milestones',
    icon: '🏁',
    description: 'Progress-based achievements',
  },
  streak: {
    name: 'Streaks',
    icon: '🔥',
    description: 'Win streak achievements',
  },
  combat: {
    name: 'Combat',
    icon: '⚡',
    description: 'Battle performance achievements',
  },
  economic: {
    name: 'Economic',
    icon: '💰',
    description: 'Resource management achievements',
  },
  teamwork: {
    name: 'Teamwork',
    icon: '🤝',
    description: 'Team synergy achievements',
  },
  variety: {
    name: 'Variety',
    icon: '🎲',
    description: 'Diversity and exploration achievements',
  },
  special: {
    name: 'Special',
    icon: '⭐',
    description: 'Unique accomplishments',
  },
  meme: {
    name: 'Meme',
    icon: '🤡',
    description: 'Fun and silly achievements',
  },
  esports: {
    name: 'Esports',
    icon: '🏆',
    description: 'Competitive excellence achievements',
  },
};

/** Get category info */
export function getCategoryInfo(category: AchievementCategory): CategoryInfo {
  return CATEGORY_INFO[category] || CATEGORY_INFO.special;
}
