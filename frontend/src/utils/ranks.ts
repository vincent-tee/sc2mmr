/**
 * Rank Badge Utility Functions
 * StarCraft 2 rank thresholds - ADJUSTED for friend group play
 */

/**
 * SC2 rank name and their MMR thresholds
 * Tuned for display MMR, the rating of record (1000 + 100*mu - 200*sigma).
 * New players start around 1833 (Silver) and climb as uncertainty drops;
 * the current player pool spans roughly 1800-3900.
 */
export const RANK_THRESHOLDS = {
  Bronze: { min: 0, max: 1500 },
  Silver: { min: 1500, max: 1900 },
  Gold: { min: 1900, max: 2300 },
  Platinum: { min: 2300, max: 2800 },
  Diamond: { min: 2800, max: 3300 },
  Master: { min: 3300, max: 3800 },
  Grandmaster: { min: 3800, max: Infinity },
} as const;

export type RankName = keyof typeof RANK_THRESHOLDS;

/**
 * Rank color mapping using Chakra UI color names
 * Warm color palette optimized for SC2 tactical theme
 */
export const RANK_COLORS: Record<RankName, { bg: string; color: string; icon: string; border?: string }> = {
  Bronze: {
    bg: 'orange.600',
    color: 'white',
    icon: '',
  },
  Silver: {
    bg: 'gray.400',
    color: 'gray.900',
    icon: '',
  },
  Gold: {
    bg: 'yellow.500',
    color: 'gray.900',
    icon: '',
  },
  Platinum: {
    bg: 'cyan.400',
    color: 'gray.900',
    icon: '',
  },
  Diamond: {
    bg: 'blue.400',
    color: 'white',
    icon: '',
  },
  Master: {
    bg: 'purple.500',
    color: 'white',
    icon: '',
  },
  Grandmaster: {
    bg: 'red.500',
    color: 'white',
    icon: '',
    border: 'gold',
  },
} as const;

/**
 * Get rank information from MMR value
 * @param mmr - Player's MMR value
 * @returns Rank info including name, colors, and icon
 */
export function getRankFromMMR(mmr: number): {
  name: RankName;
  bg: string;
  color: string;
  icon: string;
  border?: string;
} {
  const rank = Object.entries(RANK_THRESHOLDS).find(
    ([_, threshold]) => mmr >= threshold.min && mmr < threshold.max
  )?.[0] as RankName | undefined;

  if (!rank) {
    // Fallback to Grandmaster for extremely high MMR
    const rankName: RankName = 'Grandmaster';
    const colors = RANK_COLORS[rankName];
    return {
      name: rankName,
      bg: colors.bg,
      color: colors.color,
      icon: colors.icon,
      border: colors.border,
    };
  }

  const colors = RANK_COLORS[rank];
  return {
    name: rank,
    bg: colors.bg,
    color: colors.color,
    icon: colors.icon,
    border: colors.border,
  };
}

/**
 * Get Chakra Badge component props based on MMR
 * @param mmr - Player's MMR value
 * @returns Props object for Chakra Badge component
 */
export function getRankBadgeProps(mmr: number): {
  bg: string;
  color: string;
  textTransform: 'uppercase';
  fontWeight: string;
  letterSpacing: string;
  borderWidth?: string;
  borderColor?: string;
  boxShadow?: string;
} {
  const rankInfo = getRankFromMMR(mmr);
  const baseProps = {
    bg: rankInfo.bg,
    color: rankInfo.color,
    textTransform: 'uppercase' as const,
    fontWeight: 'bold',
    letterSpacing: '0.05em',
  };

  // Add special styling for Grandmaster
  if (rankInfo.name === 'Grandmaster') {
    return {
      ...baseProps,
      borderWidth: '2px',
      borderColor: 'yellow.300',
      boxShadow: '0 0 15px rgba(255, 193, 7, 0.5)',
    };
  }

  return baseProps;
}

/**
 * Get rank tier description for tooltips
 * @param mmr - Player's MMR value
 * @returns Human-readable rank tier string
 */
export function getRankTierDescription(mmr: number): string {
  const rankInfo = getRankFromMMR(mmr);
  const threshold = RANK_THRESHOLDS[rankInfo.name];
  const percentInRank = (
    ((mmr - threshold.min) / (threshold.max - threshold.min)) * 100
  ).toFixed(0);

  if (rankInfo.name === 'Grandmaster') {
    return `${rankInfo.name} (${percentInRank}% through tier)`;
  }

  const nextRank = Object.keys(RANK_THRESHOLDS)[
    Object.keys(RANK_THRESHOLDS).indexOf(rankInfo.name) + 1
  ] as RankName | undefined;
  const mmrToNextRank = nextRank
    ? Math.round(RANK_THRESHOLDS[nextRank].min - mmr)
    : 0;

  return `${rankInfo.name} - ${percentInRank}% progress (${mmrToNextRank} MMR to next rank)`;
}
