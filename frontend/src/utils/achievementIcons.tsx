/**
 * Achievement Icon Mapping
 *
 * The backend stores an emoji string on each achievement (`icon`), but emoji
 * do not render reliably cross-platform (they show as tofu boxes on many
 * systems - see HOUSE RULE: no emoji as UI iconography). This module maps
 * achievement `code` (and category as a fallback) to a react-icons component
 * from the Lucide (lu) set so badges, category headers and the recent feed all
 * render crisp vector icons instead.
 *
 * Lookup order: exact code -> category -> generic award icon. Because every
 * known code is mapped below, the category/generic fallbacks only ever trigger
 * for codes added on the backend that haven't been mapped here yet - they must
 * never fall back to a raw emoji.
 */
import type { IconType } from 'react-icons';
import {
  LuRadiation,
  LuBomb,
  LuSwords,
  LuSword,
  LuZap,
  LuSkull,
  LuCrown,
  LuMoon,
  LuGem,
  LuGamepad2,
  LuSprout,
  LuTrophy,
  LuMedal,
  LuShield,
  LuBot,
  LuSparkles,
  LuStar,
  LuTrendingUp,
  LuCalendarDays,
  LuHeart,
  LuFlame,
  LuUsers,
  LuFlaskConical,
  LuHandshake,
  LuRepeat,
  LuCog,
  LuSun,
  LuBug,
  LuFlag,
  LuCoins,
  LuDices,
  LuSmile,
  LuAward,
} from 'react-icons/lu';
import type { AchievementCategory } from '@/types/achievements';

// =============================================================================
// Per-achievement icons (keyed by backend `code`)
// =============================================================================

const ACHIEVEMENT_ICONS: Record<string, IconType> = {
  // Combat
  NUKE_LAUNCHER: LuRadiation,
  MASS_MURDERER: LuBomb,
  DAMAGE_DEALER: LuSwords,
  UNIT_SLAYER_500: LuSword,
  // Esports
  HOT_STREAK_10: LuZap,
  WALKING_APOCALYPSE: LuSkull,
  HOT_STREAK_15: LuCrown,
  // Meme
  NO_LIFE: LuMoon,
  GLASS_CANNON: LuGem,
  // Milestone
  FIRST_BLOOD: LuGamepad2,
  GETTING_STARTED: LuSprout,
  FIRST_WIN: LuTrophy,
  DOUBLE_DIGITS: LuMedal,
  MMR_3500: LuCrown,
  CENTURION: LuShield,
  WINNING_MACHINE: LuBot,
  MMR_3000: LuSparkles,
  VETERAN: LuStar,
  MMR_2500: LuTrendingUp,
  DEDICATED_WARRIOR: LuCalendarDays,
  // Special
  SOULMATES: LuHeart,
  // Streak
  HOT_STREAK_3: LuFlame,
  HOT_STREAK_5: LuFlame,
  // Teamwork
  POWER_COUPLE: LuUsers,
  HIGH_SYNERGY: LuFlaskConical,
  DYNAMIC_DUO: LuHandshake,
  // Variety
  ONE_TRICK_PONY: LuRepeat,
  RACE_MASTER_T: LuCog,
  RACE_MASTER_P: LuSun,
  RACE_MASTER_Z: LuBug,
};

// =============================================================================
// Per-category icons (fallback + section headers / filters)
// =============================================================================

const CATEGORY_ICONS: Record<AchievementCategory, IconType> = {
  milestone: LuFlag,
  streak: LuFlame,
  combat: LuSwords,
  economic: LuCoins,
  teamwork: LuHandshake,
  variety: LuDices,
  special: LuStar,
  meme: LuSmile,
  esports: LuTrophy,
};

/** Generic fallback when neither code nor category resolves. */
const DEFAULT_ICON: IconType = LuAward;

/**
 * Resolve the icon component for an achievement. Prefers the code-specific
 * icon, then the category icon, then a generic award icon. Never returns an
 * emoji.
 */
export function getAchievementIcon(
  code: string,
  category?: AchievementCategory
): IconType {
  return (
    ACHIEVEMENT_ICONS[code] ||
    (category ? CATEGORY_ICONS[category] : undefined) ||
    DEFAULT_ICON
  );
}

/** Resolve the icon component for a category (section headers, filters). */
export function getCategoryIcon(category: AchievementCategory): IconType {
  return CATEGORY_ICONS[category] || DEFAULT_ICON;
}
