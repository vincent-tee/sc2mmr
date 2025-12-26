/**
 * AchievementGrid Component
 * Grid display of achievements with category filtering and grouping
 */
import React, { memo, useMemo, useState, useCallback } from 'react';
import {
  Box,
  SimpleGrid,
  VStack,
  HStack,
  Text,
  Select,
  Badge,
  Flex,
  useColorModeValue,
} from '@chakra-ui/react';
import AchievementBadge from './AchievementBadge';
import {
  type AchievementCategory,
  type PlayerAchievement,
  type Achievement,
  getCategoryInfo,
} from '@/types/achievements';
import { spacing, radii } from '@/theme/tokens';

// =============================================================================
// Types
// =============================================================================

export interface AchievementGridProps {
  /** List of achievements (can be earned or available) */
  achievements: (PlayerAchievement | Achievement)[];
  /** Whether to group achievements by category */
  groupByCategory?: boolean;
  /** Show locked (unearned) achievements */
  showLocked?: boolean;
  /** Default category filter */
  defaultCategory?: AchievementCategory | 'all';
  /** Achievement badge size */
  badgeSize?: 'sm' | 'md' | 'lg';
  /** Number of columns (responsive) */
  columns?: { base: number; sm?: number; md?: number; lg?: number };
  /** Click handler for achievement badges */
  onAchievementClick?: (achievement: PlayerAchievement | Achievement) => void;
  /** Empty state message */
  emptyMessage?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Check if achievement is earned (has earned_at field)
 */
function isEarnedAchievement(
  achievement: PlayerAchievement | Achievement
): achievement is PlayerAchievement {
  return 'earned_at' in achievement && achievement.earned_at !== undefined;
}

/**
 * Get all unique categories from achievements
 */
function getUniqueCategories(
  achievements: (PlayerAchievement | Achievement)[]
): AchievementCategory[] {
  const categories = new Set<AchievementCategory>();
  achievements.forEach((a) => categories.add(a.category));
  return Array.from(categories);
}

// =============================================================================
// Category Header Component
// =============================================================================

interface CategoryHeaderProps {
  category: AchievementCategory;
  earnedCount: number;
  totalCount: number;
}

const CategoryHeader: React.FC<CategoryHeaderProps> = memo(({
  category,
  earnedCount,
  totalCount,
}) => {
  const categoryInfo = getCategoryInfo(category);
  const bgColor = useColorModeValue('gray.100', 'whiteAlpha.100');

  return (
    <Flex
      align="center"
      justify="space-between"
      bg={bgColor}
      px={4}
      py={2}
      borderRadius={radii.md}
      mb={3}
    >
      <HStack spacing={2}>
        <Text fontSize="xl">{categoryInfo.icon}</Text>
        <Text
          fontWeight="bold"
          fontFamily="heading"
          letterSpacing="wide"
          textTransform="uppercase"
        >
          {categoryInfo.name}
        </Text>
      </HStack>
      <Badge
        colorScheme={earnedCount === totalCount ? 'green' : 'gray'}
        fontSize="sm"
        px={2}
        py={1}
        borderRadius="md"
      >
        {earnedCount}/{totalCount}
      </Badge>
    </Flex>
  );
});

CategoryHeader.displayName = 'CategoryHeader';

// =============================================================================
// Category Filter Component
// =============================================================================

interface CategoryFilterProps {
  categories: AchievementCategory[];
  selectedCategory: AchievementCategory | 'all';
  onChange: (category: AchievementCategory | 'all') => void;
}

const CategoryFilter: React.FC<CategoryFilterProps> = memo(({
  categories,
  selectedCategory,
  onChange,
}) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');

  return (
    <Select
      value={selectedCategory}
      onChange={(e) => onChange(e.target.value as AchievementCategory | 'all')}
      bg={bgColor}
      borderColor={borderColor}
      maxW="200px"
      size="sm"
      fontFamily="heading"
      aria-label="Filter achievements by category"
    >
      <option value="all">All Categories</option>
      {categories.map((cat) => {
        const info = getCategoryInfo(cat);
        return (
          <option key={cat} value={cat}>
            {info.icon} {info.name}
          </option>
        );
      })}
    </Select>
  );
});

CategoryFilter.displayName = 'CategoryFilter';

// =============================================================================
// Main Component
// =============================================================================

const AchievementGrid: React.FC<AchievementGridProps> = ({
  achievements,
  groupByCategory = false,
  showLocked = true,
  defaultCategory = 'all',
  badgeSize = 'md',
  columns = { base: 3, sm: 4, md: 5, lg: 6 },
  onAchievementClick,
  emptyMessage = 'No achievements to display',
}) => {
  const [selectedCategory, setSelectedCategory] = useState<AchievementCategory | 'all'>(
    defaultCategory
  );

  const emptyTextColor = useColorModeValue('gray.500', 'gray.400');

  // Get unique categories
  const allCategories = useMemo(
    () => getUniqueCategories(achievements),
    [achievements]
  );

  // Filter achievements based on category and earned status
  const filteredAchievements = useMemo(() => {
    return achievements.filter((a) => {
      // Category filter
      if (selectedCategory !== 'all' && a.category !== selectedCategory) {
        return false;
      }
      // Show locked filter
      if (!showLocked && !isEarnedAchievement(a)) {
        return false;
      }
      return true;
    });
  }, [achievements, selectedCategory, showLocked]);

  // Group achievements by category
  const groupedAchievements = useMemo(() => {
    if (!groupByCategory) return null;

    const groups: Record<AchievementCategory, (PlayerAchievement | Achievement)[]> = {
      milestone: [],
      streak: [],
      combat: [],
      economic: [],
      teamwork: [],
      variety: [],
      special: [],
      meme: [],
      esports: [],
    };

    filteredAchievements.forEach((a) => {
      groups[a.category].push(a);
    });

    // Return only non-empty groups
    return Object.entries(groups)
      .filter(([_, items]) => items.length > 0)
      .map(([category, items]) => ({
        category: category as AchievementCategory,
        achievements: items,
        earnedCount: items.filter((a) => isEarnedAchievement(a)).length,
      }));
  }, [filteredAchievements, groupByCategory]);

  // Handle category change
  const handleCategoryChange = useCallback(
    (category: AchievementCategory | 'all') => {
      setSelectedCategory(category);
    },
    []
  );

  // Handle achievement click
  const handleAchievementClick = useCallback(
    (achievement: PlayerAchievement | Achievement) => {
      onAchievementClick?.(achievement);
    },
    [onAchievementClick]
  );

  // Render achievement badge
  const renderBadge = (achievement: PlayerAchievement | Achievement) => {
    const isEarned = isEarnedAchievement(achievement);

    return (
      <Box key={achievement.code} display="flex" justifyContent="center">
        <AchievementBadge
          code={achievement.code}
          name={achievement.name}
          description={achievement.description}
          flavor_text={achievement.flavor_text}
          icon={achievement.icon || '?'}
          rarity={achievement.rarity}
          category={achievement.category}
          points={achievement.points}
          earned={isEarned}
          earned_at={isEarned ? achievement.earned_at : undefined}
          size={badgeSize}
          onClick={() => handleAchievementClick(achievement)}
          showTooltip
        />
      </Box>
    );
  };

  // Empty state
  if (filteredAchievements.length === 0) {
    return (
      <Box
        textAlign="center"
        py={spacing['3xl']}
        color={emptyTextColor}
      >
        <Text fontSize="4xl" mb={3}>
          🏆
        </Text>
        <Text fontSize="lg">{emptyMessage}</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={4} align="stretch" w="100%">
      {/* Category Filter */}
      {allCategories.length > 1 && (
        <Flex justify="flex-end">
          <CategoryFilter
            categories={allCategories}
            selectedCategory={selectedCategory}
            onChange={handleCategoryChange}
          />
        </Flex>
      )}

      {/* Grouped Display */}
      {groupByCategory && groupedAchievements ? (
        <VStack spacing={6} align="stretch">
          {groupedAchievements.map(({ category, achievements: catAchievements, earnedCount }) => (
            <Box key={category}>
              <CategoryHeader
                category={category}
                earnedCount={earnedCount}
                totalCount={catAchievements.length}
              />
              <SimpleGrid columns={columns} spacing={spacing.md}>
                {catAchievements.map(renderBadge)}
              </SimpleGrid>
            </Box>
          ))}
        </VStack>
      ) : (
        /* Flat Grid Display */
        <SimpleGrid columns={columns} spacing={spacing.md}>
          {filteredAchievements.map(renderBadge)}
        </SimpleGrid>
      )}
    </VStack>
  );
};

export default memo(AchievementGrid);
