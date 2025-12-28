/**
 * Achievements Page
 * Achievement catalog with filtering and player lookup
 */
import React, { useState, useMemo } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  SimpleGrid,
  Badge,
  Flex,
  Select,
  Input,
  InputGroup,
  InputLeftElement,
  Skeleton,
  Tooltip,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { keyframes } from '@emotion/react';
import { FiSearch, FiClock, FiAward, FiStar, FiActivity } from 'react-icons/fi';
import { achievementsApi } from '../api/achievements';
import {
  Achievement,
  AchievementRarity,
  AchievementCategory,
  RARITY_COLORS,
  CATEGORY_INFO,
  getRarityLabel,
  getCategoryInfo,
  RecentAchievementEntry,
} from '../types/achievements';

// Design tokens
const cardBg = 'space.800';
const borderColor = 'space.900';
const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';

// =============================================================================
// Animations
// =============================================================================

const rarityGlow = keyframes`
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
`;

const slideIn = keyframes`
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
`;

// =============================================================================
// Helper Components
// =============================================================================

interface AchievementCardProps {
  achievement: Achievement;
  index: number;
}

const AchievementCard: React.FC<AchievementCardProps> = React.memo(({ achievement, index }) => {
  const rarityColors = RARITY_COLORS[achievement.rarity];
  const categoryInfo = getCategoryInfo(achievement.category);

  return (
    <Tooltip
      label={
        <Box p={2}>
          <Text fontWeight="bold" fontFamily="heading">{achievement.name}</Text>
          <Text fontSize="sm" color="gray.300">{achievement.description}</Text>
          {achievement.flavor_text && (
            <Text fontSize="xs" color="gray.400" fontStyle="italic" mt={1}>
              "{achievement.flavor_text}"
            </Text>
          )}
          <HStack mt={2} spacing={2}>
            <Badge colorScheme="purple">{getRarityLabel(achievement.rarity)}</Badge>
            <Badge colorScheme="blue">{achievement.points} pts</Badge>
          </HStack>
        </Box>
      }
      placement="top"
      hasArrow
      bg="space.700"
      borderRadius="md"
    >
      <Box
        bg="space.800"
        borderRadius="xl"
        border="3px solid"
        borderColor={rarityColors.border}
        p={4}
        position="relative"
        overflow="hidden"
        cursor="pointer"
        transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
        animation={`${slideIn} 0.3s ease-out ${index * 0.05}s both`}
        _hover={{
          transform: 'translateY(-4px)',
          boxShadow: brandShadow,
        }}
      >
        {/* Icon */}
        <Flex
          justify="center"
          align="center"
          w="60px"
          h="60px"
          mx="auto"
          mb={3}
          bg={rarityColors.bg}
          borderRadius="xl"
          boxShadow={rarityColors.glow}
        >
          <Text fontSize="2xl">{achievement.icon || '🎖️'}</Text>
        </Flex>

        {/* Name */}
        <Text
          fontWeight="bold"
          fontSize="sm"
          color={rarityColors.text}
          textAlign="center"
          noOfLines={2}
          fontFamily="heading"
        >
          {achievement.name}
        </Text>

        {/* Category & Points */}
        <HStack justify="center" mt={2} spacing={1}>
          <Text fontSize="xs">{categoryInfo.icon}</Text>
          <Text fontSize="xs" color="gray.500">
            {achievement.points} pts
          </Text>
        </HStack>
      </Box>
    </Tooltip>
  );
});

AchievementCard.displayName = 'AchievementCard';

interface RecentAchievementItemProps {
  entry: RecentAchievementEntry;
}

const RecentAchievementItem: React.FC<RecentAchievementItemProps> = React.memo(({ entry }) => {
  const rarityColors = RARITY_COLORS[entry.rarity];

  const timeAgo = useMemo(() => {
    const date = new Date(entry.earned_at);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  }, [entry.earned_at]);

  return (
    <HStack
      bg="space.800"
      p={3}
      borderRadius="xl"
      border="2px solid"
      borderColor="space.700"
      spacing={3}
      transition="all 0.2s"
      _hover={{ borderColor: rarityColors.border, transform: 'translateX(4px)' }}
    >
      <Box
        w="40px"
        h="40px"
        bg={rarityColors.bg}
        borderRadius="md"
        display="flex"
        alignItems="center"
        justifyContent="center"
        boxShadow={rarityColors.glow}
      >
        <Text fontSize="lg">{entry.achievement_icon || '🎖️'}</Text>
      </Box>
      <VStack align="start" spacing={0} flex={1}>
        <Text fontWeight="bold" color="gray.100" fontSize="sm">
          {entry.player_name}
        </Text>
        <Text color={rarityColors.text} fontSize="xs">
          {entry.achievement_name}
        </Text>
      </VStack>
      <Text color="gray.500" fontSize="xs">
        {timeAgo}
      </Text>
    </HStack>
  );
});

RecentAchievementItem.displayName = 'RecentAchievementItem';

// =============================================================================
// Main Component
// =============================================================================

const Achievements: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<AchievementCategory | 'all'>('all');
  const [selectedRarity, setSelectedRarity] = useState<AchievementRarity | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const bgColor = useColorModeValue('gray.900', 'space.900');
  const cardBg = useColorModeValue('gray.800', 'space.800');

  // Fetch all achievements
  const { data: achievements, isLoading: achievementsLoading } = useQuery({
    queryKey: ['achievements', 'all'],
    queryFn: async () => {
      const response = await achievementsApi.getAll(false);
      return response.data;
    },
    staleTime: 300000, // 5 minutes
  });

  // Fetch recent achievements
  const { data: recentAchievements, isLoading: recentLoading } = useQuery({
    queryKey: ['achievements', 'recent'],
    queryFn: async () => {
      const response = await achievementsApi.getRecent(10);
      return response.data;
    },
    staleTime: 60000, // 1 minute
  });

  // Filter achievements
  const filteredAchievements = useMemo(() => {
    if (!achievements) return [];

    return achievements.filter((a) => {
      if (selectedCategory !== 'all' && a.category !== selectedCategory) return false;
      if (selectedRarity !== 'all' && a.rarity !== selectedRarity) return false;
      if (searchTerm && !a.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    });
  }, [achievements, selectedCategory, selectedRarity, searchTerm]);

  // Group by category
  const groupedAchievements = useMemo(() => {
    const groups: Record<string, Achievement[]> = {};

    filteredAchievements.forEach((a) => {
      if (!groups[a.category]) {
        groups[a.category] = [];
      }
      groups[a.category].push(a);
    });

    return groups;
  }, [filteredAchievements]);

  const categories = Object.keys(CATEGORY_INFO) as AchievementCategory[];
  const rarities: AchievementRarity[] = ['common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic'];

  return (
    <Box bg="space.900" minH="100vh" py={8}>
      <Container maxW="container.xl">
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <Box textAlign="center">
            <Heading
              size="2xl"
              fontFamily="heading"
              color="brand.400"
              letterSpacing="wider"
            >
              🎖️ Achievements
            </Heading>
            <Text color="gray.500" mt={2}>
              {achievements?.length || 0} achievements to earn
            </Text>
          </Box>

          <Tabs variant="soft-rounded" colorScheme="brand">
            <TabList justifyContent="center">
              <Tab>All Achievements</Tab>
              <Tab>Recent Activity</Tab>
            </TabList>

            <TabPanels>
              {/* All Achievements Tab */}
              <TabPanel px={0}>
                {/* Filters */}
                <Flex
                  gap={4}
                  mb={6}
                  direction={{ base: 'column', md: 'row' }}
                  align={{ base: 'stretch', md: 'center' }}
                >
                  <InputGroup maxW={{ base: '100%', md: '300px' }}>
                    <InputLeftElement pointerEvents="none">
                      <FiSearch color="gray" />
                    </InputLeftElement>
                    <Input
                      placeholder="Search achievements..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      bg="space.800"
                      border="2px solid"
                      borderColor="space.700"
                      fontFamily="heading"
                      _hover={{ borderColor: 'brand.500' }}
                      _focus={{ borderColor: 'brand.500' }}
                    />
                  </InputGroup>

                  <Select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value as AchievementCategory | 'all')}
                    maxW={{ base: '100%', md: '200px' }}
                    bg="space.800"
                    border="2px solid"
                    borderColor="space.700"
                    fontFamily="heading"
                    _hover={{ borderColor: 'brand.500' }}
                  >
                    <option value="all">All Categories</option>
                    {categories.map((cat) => (
                      <option key={cat} value={cat}>
                        {CATEGORY_INFO[cat].icon} {CATEGORY_INFO[cat].name}
                      </option>
                    ))}
                  </Select>

                  <Select
                    value={selectedRarity}
                    onChange={(e) => setSelectedRarity(e.target.value as AchievementRarity | 'all')}
                    maxW={{ base: '100%', md: '200px' }}
                    bg="space.800"
                    border="2px solid"
                    borderColor="space.700"
                    fontFamily="heading"
                    _hover={{ borderColor: 'brand.500' }}
                  >
                    <option value="all">All Rarities</option>
                    {rarities.map((rarity) => (
                      <option key={rarity} value={rarity}>
                        {getRarityLabel(rarity)}
                      </option>
                    ))}
                  </Select>
                </Flex>

                {/* Achievement Grid */}
                {achievementsLoading ? (
                  <SimpleGrid columns={{ base: 2, sm: 3, md: 4, lg: 5 }} spacing={4}>
                    {[...Array(15)].map((_, i) => (
                      <Skeleton key={i} height="180px" borderRadius="lg" />
                    ))}
                  </SimpleGrid>
                ) : filteredAchievements.length > 0 ? (
                  selectedCategory === 'all' ? (
                    // Grouped view
                    <VStack spacing={8} align="stretch">
                      {Object.entries(groupedAchievements).map(([category, achievements]) => (
                        <Box key={category}>
                          <HStack mb={4}>
                            <Text fontSize="xl">
                              {CATEGORY_INFO[category as AchievementCategory]?.icon || '📦'}
                            </Text>
                            <Heading size="md" color="gray.200" fontFamily="heading">
                              {CATEGORY_INFO[category as AchievementCategory]?.name || category}
                            </Heading>
                            <Badge colorScheme="brand">{achievements.length}</Badge>
                          </HStack>
                          <SimpleGrid columns={{ base: 2, sm: 3, md: 4, lg: 5 }} spacing={4}>
                            {achievements.map((achievement, index) => (
                              <AchievementCard
                                key={achievement.code}
                                achievement={achievement}
                                index={index}
                              />
                            ))}
                          </SimpleGrid>
                        </Box>
                      ))}
                    </VStack>
                  ) : (
                    // Flat view
                    <SimpleGrid columns={{ base: 2, sm: 3, md: 4, lg: 5 }} spacing={4}>
                      {filteredAchievements.map((achievement, index) => (
                        <AchievementCard
                          key={achievement.code}
                          achievement={achievement}
                          index={index}
                        />
                      ))}
                    </SimpleGrid>
                  )
                ) : (
                  <Box textAlign="center" py={8}>
                    <Text color="gray.500">No achievements found</Text>
                  </Box>
                )}
              </TabPanel>

              {/* Recent Activity Tab */}
              <TabPanel px={0}>
                <VStack spacing={4} align="stretch">
                  <Heading size="md" color="gray.200" fontFamily="heading">
                    <HStack>
                      <FiClock />
                      <Text>Recent Unlocks</Text>
                    </HStack>
                  </Heading>

                  {recentLoading ? (
                    <VStack spacing={2}>
                      {[...Array(5)].map((_, i) => (
                        <Skeleton key={i} height="60px" width="100%" borderRadius="md" />
                      ))}
                    </VStack>
                  ) : recentAchievements && recentAchievements.length > 0 ? (
                    <VStack spacing={2} align="stretch">
                      {recentAchievements.map((entry, index) => (
                        <RecentAchievementItem key={`${entry.player_id}-${entry.achievement_code}-${index}`} entry={entry} />
                      ))}
                    </VStack>
                  ) : (
                    <Box textAlign="center" py={8}>
                      <Text color="gray.500">No recent achievements</Text>
                    </Box>
                  )}
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </VStack>
      </Container>
    </Box>
  );
};

export default Achievements;
