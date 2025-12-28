/**
 * Leaderboard Page
 * Multi-category leaderboard with tabbed navigation
 */
import React, { useState, useMemo, useCallback } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Flex,
  useColorModeValue,
  Skeleton,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { keyframes } from '@emotion/react';
import { leaderboardApi } from '../api/leaderboard';
import RankBadge from '../components/RankBadge';
import {
  LEADERBOARD_CATEGORIES,
  LeaderboardCategoryKey,
  LeaderboardEntry,
  DuoLeaderboardEntry,
  formatLeaderboardValue,
  getRankMedal,
  isDuoCategory,
} from '../types/leaderboard';
import { colors, shadows } from '../theme/tokens';

// =============================================================================
// Animations
// =============================================================================

// Shimmer animation - available for future use
// const shimmer = keyframes`
//   0% { background-position: -200% center; }
//   100% { background-position: 200% center; }
// `;

const pulseGlow = keyframes`
  0%, 100% { box-shadow: 0 0 10px rgba(255, 140, 26, 0.3); }
  50% { box-shadow: 0 0 20px rgba(255, 140, 26, 0.5); }
`;

// =============================================================================
// Helper Components
// =============================================================================

interface CategoryTabProps {
  category: typeof LEADERBOARD_CATEGORIES[number];
  isActive: boolean;
  onClick: () => void;
}

const CategoryTab: React.FC<CategoryTabProps> = React.memo(({ category, isActive, onClick }) => {
  const activeBg = useColorModeValue('brand.500', 'brand.500');
  const inactiveBg = useColorModeValue('gray.700', 'space.700');
  const activeColor = useColorModeValue('gray.900', 'gray.900');
  const inactiveColor = useColorModeValue('gray.300', 'gray.300');

  return (
    <Button
      onClick={onClick}
      bg={isActive ? activeBg : inactiveBg}
      color={isActive ? activeColor : inactiveColor}
      size="sm"
      px={4}
      py={2}
      borderRadius="lg"
      fontWeight="bold"
      fontFamily="heading"
      letterSpacing="wide"
      transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
      _hover={{
        bg: isActive ? activeBg : 'gray.600',
        transform: 'translateY(-2px)',
      }}
      sx={isActive ? {
        boxShadow: '3px 3px 0 space.900',
      } : {}}
    >
      <HStack spacing={2}>
        <Text fontSize="lg">{category.icon}</Text>
        <Text display={{ base: 'none', md: 'block' }}>{category.name}</Text>
      </HStack>
    </Button>
  );
});

CategoryTab.displayName = 'CategoryTab';

interface RankCellProps {
  rank: number;
}

const RankCell: React.FC<RankCellProps> = React.memo(({ rank }) => {
  const medal = getRankMedal(rank);
  const isTopThree = rank <= 3;

  return (
    <HStack spacing={1}>
      {medal && <Text fontSize="xl">{medal}</Text>}
      <Text
        fontWeight={isTopThree ? 'bold' : 'normal'}
        color={isTopThree ? 'shield.400' : 'gray.400'}
        fontFamily="mono"
      >
        #{rank}
      </Text>
    </HStack>
  );
});

RankCell.displayName = 'RankCell';

// =============================================================================
// Table Components
// =============================================================================

interface StandardTableProps {
  entries: LeaderboardEntry[];
  category: LeaderboardCategoryKey;
  onPlayerClick: (playerId: number) => void;
}

const StandardTable: React.FC<StandardTableProps> = React.memo(({ entries, category, onPlayerClick }) => {
  const hoverBg = useColorModeValue('whiteAlpha.100', 'whiteAlpha.100');
  const categoryInfo = LEADERBOARD_CATEGORIES.find(c => c.key === category);

  return (
    <Table variant="simple" size="md">
      <Thead>
        <Tr>
          <Th color="gray.500" width="80px">Rank</Th>
          <Th color="gray.500">Player</Th>
          <Th color="gray.500" isNumeric>{categoryInfo?.unit || 'Value'}</Th>
          <Th color="gray.500" display={{ base: 'none', md: 'table-cell' }}>Info</Th>
        </Tr>
      </Thead>
      <Tbody>
        {entries.map((entry) => (
          <Tr
            key={entry.player_id}
            cursor="pointer"
            transition="all 0.2s"
            _hover={{
              bg: hoverBg,
              transform: 'translateX(4px)',
            }}
            onClick={() => onPlayerClick(entry.player_id)}
          >
            <Td>
              <RankCell rank={entry.rank} />
            </Td>
            <Td>
              <HStack spacing={3}>
                <Text fontWeight="semibold" color="gray.100" fontFamily="heading">
                  {entry.name}
                </Text>
                {['mmr', 'trueskill', 'hybrid'].includes(category) && (
                  <RankBadge mmr={entry.value} size="xs" showMMR={false} />
                )}
              </HStack>
            </Td>
            <Td isNumeric>
              <Text
                fontWeight="bold"
                color={entry.rank <= 3 ? 'shield.400' : 'brand.400'}
                fontFamily="mono"
                fontSize="lg"
              >
                {formatLeaderboardValue(entry.value, category)}
              </Text>
            </Td>
            <Td display={{ base: 'none', md: 'table-cell' }}>
              <Text color="gray.500" fontSize="sm">
                {entry.extra_info || '-'}
              </Text>
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
});

StandardTable.displayName = 'StandardTable';

interface DuoTableProps {
  entries: DuoLeaderboardEntry[];
  onPlayerClick: (playerId: number) => void;
}

const DuoTable: React.FC<DuoTableProps> = React.memo(({ entries, onPlayerClick }) => {
  const hoverBg = useColorModeValue('whiteAlpha.100', 'whiteAlpha.100');

  return (
    <Table variant="simple" size="md">
      <Thead>
        <Tr>
          <Th color="gray.500" width="80px">Rank</Th>
          <Th color="gray.500">Partnership</Th>
          <Th color="gray.500" isNumeric>Wins</Th>
          <Th color="gray.500" isNumeric display={{ base: 'none', md: 'table-cell' }}>Win Rate</Th>
          <Th color="gray.500" isNumeric display={{ base: 'none', lg: 'table-cell' }}>Synergy</Th>
        </Tr>
      </Thead>
      <Tbody>
        {entries.map((entry) => (
          <Tr
            key={`${entry.player1_id}-${entry.player2_id}`}
            transition="all 0.2s"
            _hover={{
              bg: hoverBg,
              transform: 'translateX(4px)',
            }}
          >
            <Td>
              <RankCell rank={entry.rank} />
            </Td>
            <Td>
              <HStack spacing={2}>
                <Text
                  fontWeight="semibold"
                  color="gray.100"
                  cursor="pointer"
                  _hover={{ color: 'brand.400' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onPlayerClick(entry.player1_id);
                  }}
                >
                  {entry.player1_name}
                </Text>
                <Text color="gray.500">&</Text>
                <Text
                  fontWeight="semibold"
                  color="gray.100"
                  cursor="pointer"
                  _hover={{ color: 'brand.400' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onPlayerClick(entry.player2_id);
                  }}
                >
                  {entry.player2_name}
                </Text>
              </HStack>
            </Td>
            <Td isNumeric>
              <Text
                fontWeight="bold"
                color={entry.rank <= 3 ? 'shield.400' : 'brand.400'}
                fontFamily="mono"
              >
                {entry.wins_together}
              </Text>
            </Td>
            <Td isNumeric display={{ base: 'none', md: 'table-cell' }}>
              <Badge
                colorScheme={entry.win_rate >= 60 ? 'green' : entry.win_rate >= 50 ? 'yellow' : 'red'}
              >
                {entry.win_rate.toFixed(1)}%
              </Badge>
            </Td>
            <Td isNumeric display={{ base: 'none', lg: 'table-cell' }}>
              <Text color="gray.400" fontFamily="mono">
                {entry.synergy_score.toFixed(1)}
              </Text>
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
});

DuoTable.displayName = 'DuoTable';

// =============================================================================
// Main Component
// =============================================================================

const Leaderboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState<LeaderboardCategoryKey>('mmr');

  const bgColor = useColorModeValue('gray.900', 'space.900');
  const cardBg = useColorModeValue('gray.800', 'space.800');

  // Fetch leaderboard data
  const { data, isLoading, error } = useQuery({
    queryKey: ['leaderboard', activeCategory],
    queryFn: async () => {
      const response = await leaderboardApi.getByCategory(activeCategory, {
        limit: 20,
        minGames: activeCategory === 'winrate' ? 20 : 10,
      });
      return response.data;
    },
    staleTime: 60000, // 1 minute
  });

  const handlePlayerClick = useCallback((playerId: number) => {
    navigate(`/players/${playerId}`);
  }, [navigate]);

  const categoryInfo = useMemo(() =>
    LEADERBOARD_CATEGORIES.find(c => c.key === activeCategory),
    [activeCategory]
  );

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
              🏆 Leaderboards
            </Heading>
            <Text color="gray.500" mt={2}>
              Rankings across all categories
            </Text>
          </Box>

          {/* Category Tabs */}
          <Box
            overflowX="auto"
            py={2}
            css={{
              '&::-webkit-scrollbar': { height: '4px' },
              '&::-webkit-scrollbar-thumb': { background: colors.brand[500], borderRadius: '2px' },
            }}
          >
            <Flex gap={2} minW="max-content" justify="center">
              {LEADERBOARD_CATEGORIES.map((category) => (
                <CategoryTab
                  key={category.key}
                  category={category}
                  isActive={activeCategory === category.key}
                  onClick={() => setActiveCategory(category.key)}
                />
              ))}
            </Flex>
          </Box>

          {/* Category Header */}
          {categoryInfo && (
            <Box
              textAlign="center"
              py={6}
              bg="rgba(0, 0, 0, 0.2)"
              borderRadius="xl"
              border="1px solid"
              borderColor="whiteAlpha.100"
              position="relative"
              overflow="hidden"
            >
              <VStack spacing={2} position="relative" zIndex={1}>
                <HStack justify="center" spacing={4}>
                  <Text fontSize="4xl" className="emoji-font">{categoryInfo.icon}</Text>
                  <Heading size="xl" color="gray.100" fontFamily="heading" letterSpacing="widest" textTransform="uppercase">
                    {categoryInfo.name}
                  </Heading>
                </HStack>
                <Text color="gray.400" fontSize="lg" maxW="container.md" mx="auto" fontWeight="medium">
                  {categoryInfo.description}
                </Text>
              </VStack>
              {/* Background Icon Watermark */}
              <Icon
                as={FiTarget}
                position="absolute"
                right="-20px"
                bottom="-20px"
                boxSize={32}
                color="whiteAlpha.05"
                transform="rotate(-15deg)"
              />
            </Box>
          )}

          {/* Leaderboard Table */}
          <Box
            bg="space.800"
            borderRadius="xl"
            border="3px solid"
            borderColor="space.700"
            boxShadow="3px 3px 0 space.900"
            overflow="hidden"
          >
            {isLoading ? (
              <VStack spacing={4} p={8}>
                {[...Array(10)].map((_, i) => (
                  <Skeleton key={i} height="50px" width="100%" borderRadius="md" />
                ))}
              </VStack>
            ) : error ? (
              <Alert status="error" bg="transparent">
                <AlertIcon />
                Failed to load leaderboard data
              </Alert>
            ) : data && data.length > 0 ? (
              isDuoCategory(activeCategory) ? (
                <DuoTable
                  entries={data as DuoLeaderboardEntry[]}
                  onPlayerClick={handlePlayerClick}
                />
              ) : (
                <StandardTable
                  entries={data as LeaderboardEntry[]}
                  category={activeCategory}
                  onPlayerClick={handlePlayerClick}
                />
              )
            ) : (
              <Box p={8} textAlign="center">
                <Text color="gray.500">No data available for this category</Text>
              </Box>
            )}
          </Box>
        </VStack>
      </Container>
    </Box>
  );
};

export default Leaderboard;
