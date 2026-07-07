/**
 * Leaderboard Page - Clubhouse Edition
 * Editorial header, icon category tabs, asymmetric top-3 podium,
 * then a dense table with oversized rank numerals.
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
  Icon,
  Avatar,
  Switch,
  FormControl,
  FormLabel,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { keyframes } from '@emotion/react';
import { FiActivity, FiTrendingUp, FiUsers } from 'react-icons/fi';
import type { IconType } from 'react-icons';
import { LuTrophy, LuSwords, LuFlame, LuUsersRound, LuCrown } from 'react-icons/lu';
import { leaderboardApi } from '../api/leaderboard';
import { playersApi } from '../api/endpoints';
import RankBadge from '../components/RankBadge';
import PageHeader from '../components/PageHeader';
import { getPlayerAvatarUrl } from '../utils/formatting';
import type { Player } from '../types/api';
import {
  LEADERBOARD_CATEGORIES,
  LeaderboardCategoryKey,
  LeaderboardEntry,
  DuoLeaderboardEntry,
  TrioLeaderboardEntry,
  formatLeaderboardValue,
} from '../types/leaderboard';

// Icon per category (replaces the old emoji icons)
const CATEGORY_ICONS: Record<string, IconType> = {
  mmr: LuTrophy,
  'recent-form': FiActivity,
  combat: LuSwords,
  winrate: FiTrendingUp,
  winstreak: LuFlame,
  duos: FiUsers,
  trios: LuUsersRound,
};

// =============================================================================
// Category Tabs
// =============================================================================

interface CategoryTabProps {
  category: (typeof LEADERBOARD_CATEGORIES)[number];
  isActive: boolean;
  onClick: () => void;
}

const CategoryTab: React.FC<CategoryTabProps> = React.memo(({ category, isActive, onClick }) => (
  <Button
    onClick={onClick}
    size="sm"
    px={4}
    h="36px"
    borderRadius="full"
    fontWeight={isActive ? '800' : '600'}
    fontFamily="heading"
    bg={isActive ? 'brand.500' : 'whiteAlpha.100'}
    color={isActive ? 'white' : 'gray.400'}
    border="1px solid"
    borderColor={isActive ? 'brand.500' : 'transparent'}
    transition="all 0.18s ease"
    _hover={{
      bg: isActive ? 'brand.400' : 'whiteAlpha.200',
      color: isActive ? 'white' : 'gray.200',
    }}
  >
    <HStack spacing={2}>
      <Icon as={CATEGORY_ICONS[category.key] || LuTrophy} boxSize="14px" />
      <Text display={{ base: 'none', md: 'block' }}>{category.name}</Text>
    </HStack>
  </Button>
));

CategoryTab.displayName = 'CategoryTab';

// =============================================================================
// Podium (top 3, standard categories)
// =============================================================================

interface PodiumProps {
  entries: LeaderboardEntry[];
  category: LeaderboardCategoryKey;
  onPlayerClick: (playerId: number) => void;
  raceById: Map<number, string>;
}

// Slow shine sweep across the champion card
const championShine = keyframes`
  0% { transform: translateX(-140%) skewX(-18deg); }
  55%, 100% { transform: translateX(240%) skewX(-18deg); }
`;

// Medal styling per rank (index = rank - 1)
const MEDALS = [
  {
    hex: '#FBBF24',
    soft: 'rgba(251, 191, 36, 0.14)',
    border: 'rgba(251, 191, 36, 0.55)',
    text: 'shield.400',
    step: { base: '52px', md: '92px' },
    avatar: '92px',
    order: { base: 0, md: 1 },
  },
  {
    hex: '#CBD5E1',
    soft: 'rgba(203, 213, 225, 0.10)',
    border: 'rgba(203, 213, 225, 0.35)',
    text: 'gray.300',
    step: { base: '44px', md: '56px' },
    avatar: '64px',
    order: { base: 1, md: 0 },
  },
  {
    hex: '#D97706',
    soft: 'rgba(217, 119, 6, 0.12)',
    border: 'rgba(217, 119, 6, 0.45)',
    text: 'orange.400',
    step: { base: '38px', md: '34px' },
    avatar: '64px',
    order: { base: 2, md: 2 },
  },
];

const Podium: React.FC<PodiumProps> = React.memo(({ entries, category, onPlayerClick, raceById }) => {
  const top3 = entries.slice(0, 3);
  if (top3.length < 3) return null;

  return (
    <Flex
      gap={{ base: 3, md: 4 }}
      align={{ base: 'stretch', md: 'flex-end' }}
      direction={{ base: 'column', md: 'row' }}
    >
      {top3.map((entry, idx) => {
        const medal = MEDALS[idx];
        const isChampion = idx === 0;
        return (
          <Flex
            key={entry.player_id}
            direction="column"
            flex={{ md: isChampion ? 1.25 : 1 }}
            order={medal.order}
            cursor="pointer"
            role="group"
            transition="transform 0.2s ease"
            _hover={{ transform: 'translateY(-6px)' }}
            onClick={() => onPlayerClick(entry.player_id)}
          >
            {/* Card */}
            <Box
              position="relative"
              overflow="hidden"
              bg={isChampion ? `linear-gradient(180deg, ${medal.soft}, var(--chakra-colors-space-800) 55%)` : 'space.800'}
              borderRadius="2xl 2xl 0 0"
              borderTopRadius="2xl"
              border="1px solid"
              borderBottom="none"
              borderColor={medal.border}
              boxShadow={isChampion ? '0 0 60px rgba(251, 191, 36, 0.10)' : 'none'}
              textAlign="center"
              px={5}
              pt={isChampion ? 8 : 6}
              pb={5}
              _groupHover={{ borderColor: medal.hex }}
            >
              {isChampion && (
                <Box
                  aria-hidden
                  position="absolute"
                  top={0}
                  bottom={0}
                  w="45%"
                  bg="linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent)"
                  animation={`${championShine} 4.5s ease-in-out infinite`}
                  pointerEvents="none"
                />
              )}
              {/* Avatar with crown perched on the champion */}
              <Box position="relative" display="inline-block" mb={3}>
                {isChampion && (
                  <Icon
                    as={LuCrown}
                    color="shield.400"
                    boxSize="26px"
                    position="absolute"
                    top="-20px"
                    left="50%"
                    transform="translateX(-50%) rotate(-8deg)"
                    filter="drop-shadow(0 0 6px rgba(251, 191, 36, 0.6))"
                    zIndex={1}
                  />
                )}
                <Avatar
                  boxSize={medal.avatar}
                  src={getPlayerAvatarUrl(entry.name, raceById.get(entry.player_id))}
                  name={entry.name}
                  border="3px solid"
                  borderColor={medal.hex}
                  boxShadow={`0 0 0 4px ${medal.soft}`}
                />
              </Box>
              <Heading fontSize={isChampion ? '2xl' : 'lg'} color="gray.50" mb={1} noOfLines={1}>
                {entry.name}
              </Heading>
              <Text
                fontFamily="mono"
                fontWeight="700"
                fontSize={isChampion ? '3xl' : 'xl'}
                lineHeight="1.1"
                color={medal.text}
              >
                {formatLeaderboardValue(entry.value, category)}
              </Text>
              {entry.extra_info && (
                <Text fontSize="xs" color="gray.500" mt={1.5} noOfLines={1}>
                  {entry.extra_info}
                </Text>
              )}
            </Box>

            {/* Podium step — numeral only; heights and medal colors carry the rest */}
            <Flex
              h={medal.step}
              align="center"
              justify="center"
              bg={`linear-gradient(180deg, ${medal.soft}, rgba(0, 0, 0, 0.25))`}
              borderTop="3px solid"
              borderBottomRadius="xl"
              sx={{ borderTopColor: medal.hex }}
            >
              <Text
                fontFamily="heading"
                fontWeight="800"
                fontSize={isChampion ? '4xl' : '2xl'}
                lineHeight="1"
                color={medal.text}
              >
                {idx + 1}
              </Text>
            </Flex>
          </Flex>
        );
      })}
    </Flex>
  );
});

Podium.displayName = 'Podium';

// =============================================================================
// Rank numeral cell
// =============================================================================

const RankCell: React.FC<{ rank: number }> = React.memo(({ rank }) => (
  <Text
    fontFamily="heading"
    fontWeight="800"
    fontSize="xl"
    color={rank <= 3 ? 'brand.400' : 'whiteAlpha.400'}
    w="40px"
  >
    {rank}
  </Text>
));

RankCell.displayName = 'RankCell';

// =============================================================================
// Tables
// =============================================================================

interface StandardTableProps {
  entries: LeaderboardEntry[];
  category: LeaderboardCategoryKey;
  onPlayerClick: (playerId: number) => void;
  raceById: Map<number, string>;
}

const StandardTable: React.FC<StandardTableProps> = React.memo(
  ({ entries, category, onPlayerClick, raceById }) => {
    const hoverBg = useColorModeValue('whiteAlpha.100', 'whiteAlpha.100');
    const categoryInfo = LEADERBOARD_CATEGORIES.find((c) => c.key === category);

    const isRecentForm = category === 'recent-form';

    return (
      <Table variant="simple" size="md">
        <Thead>
          <Tr>
            <Th color="gray.500" width="70px" borderColor="whiteAlpha.100">Rank</Th>
            <Th color="gray.500" borderColor="whiteAlpha.100">Player</Th>
            <Th color="gray.500" isNumeric borderColor="whiteAlpha.100">{categoryInfo?.unit || 'Value'}</Th>
            {isRecentForm ? (
              <>
                <Th color="gray.500" isNumeric display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
                  Games
                </Th>
                <Th color="gray.500" isNumeric display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
                  WR
                </Th>
              </>
            ) : (
              <Th color="gray.500" display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
                Info
              </Th>
            )}
          </Tr>
        </Thead>
        <Tbody>
          {entries.map((entry) => (
            <Tr
              key={entry.player_id}
              cursor="pointer"
              transition="all 0.15s ease"
              _hover={{ bg: hoverBg }}
              onClick={() => onPlayerClick(entry.player_id)}
            >
              <Td borderColor="whiteAlpha.100">
                <RankCell rank={entry.rank} />
              </Td>
              <Td borderColor="whiteAlpha.100">
                <HStack spacing={3}>
                  <Avatar size="xs" src={getPlayerAvatarUrl(entry.name, raceById.get(entry.player_id))} name={entry.name} />
                  <Text fontWeight="700" color="gray.100" fontFamily="heading">
                    {entry.name}
                  </Text>
                  {category === 'mmr' && <RankBadge mmr={entry.value} size="xs" showMMR={false} />}
                  {entry.is_new && (
                    <Badge colorScheme="teal" fontSize="9px" px={1.5}>
                      NEW
                    </Badge>
                  )}
                  {entry.is_active === false && (
                    <Badge colorScheme="gray" fontSize="9px" px={1.5}>
                      LEGACY
                    </Badge>
                  )}
                </HStack>
              </Td>
              <Td isNumeric borderColor="whiteAlpha.100">
                <Text
                  fontWeight="700"
                  color={entry.rank <= 3 ? 'shield.400' : 'brand.400'}
                  fontFamily="mono"
                  fontSize="md"
                >
                  {formatLeaderboardValue(entry.value, category)}
                </Text>
              </Td>
              {isRecentForm ? (
                <>
                  <Td isNumeric display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
                    <Text color="gray.400" fontFamily="mono" fontSize="sm">
                      {entry.games_played ?? '-'}/30
                    </Text>
                  </Td>
                  <Td isNumeric display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
                    <HStack justify="flex-end" spacing={1.5}>
                      {entry.form_icon && <Text fontSize="sm">{entry.form_icon}</Text>}
                      <Text color="gray.300" fontFamily="mono" fontSize="sm" fontWeight="600">
                        {entry.secondary_value != null ? `${entry.secondary_value}%` : '-'}
                      </Text>
                    </HStack>
                  </Td>
                </>
              ) : (
                <Td display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
                  <Text color="gray.500" fontSize="sm">
                    {entry.extra_info || '-'}
                  </Text>
                </Td>
              )}
            </Tr>
          ))}
        </Tbody>
      </Table>
    );
  }
);

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
          <Th color="gray.500" width="70px" borderColor="whiteAlpha.100">Rank</Th>
          <Th color="gray.500" borderColor="whiteAlpha.100">Partnership</Th>
          <Th color="gray.500" isNumeric borderColor="whiteAlpha.100">Wins</Th>
          <Th color="gray.500" isNumeric display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
            Win Rate
          </Th>
          <Th color="gray.500" isNumeric display={{ base: 'none', lg: 'table-cell' }} borderColor="whiteAlpha.100">
            Synergy
          </Th>
        </Tr>
      </Thead>
      <Tbody>
        {entries.map((entry) => (
          <Tr
            key={`${entry.player1_id}-${entry.player2_id}`}
            transition="all 0.15s ease"
            _hover={{ bg: hoverBg }}
          >
            <Td borderColor="whiteAlpha.100">
              <RankCell rank={entry.rank} />
            </Td>
            <Td borderColor="whiteAlpha.100">
              <HStack spacing={2}>
                <Text
                  fontWeight="700"
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
                  fontWeight="700"
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
            <Td isNumeric borderColor="whiteAlpha.100">
              <Text fontWeight="700" color={entry.rank <= 3 ? 'shield.400' : 'brand.400'} fontFamily="mono">
                {entry.wins_together}
              </Text>
            </Td>
            <Td isNumeric display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
              <Badge colorScheme={entry.win_rate >= 60 ? 'green' : entry.win_rate >= 50 ? 'yellow' : 'red'}>
                {entry.win_rate.toFixed(1)}%
              </Badge>
            </Td>
            <Td isNumeric display={{ base: 'none', lg: 'table-cell' }} borderColor="whiteAlpha.100">
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

interface TrioTableProps {
  entries: TrioLeaderboardEntry[];
  onPlayerClick: (playerId: number) => void;
}

const TrioTable: React.FC<TrioTableProps> = React.memo(({ entries, onPlayerClick }) => {
  const hoverBg = useColorModeValue('whiteAlpha.100', 'whiteAlpha.100');

  return (
    <Table variant="simple" size="md">
      <Thead>
        <Tr>
          <Th color="gray.500" width="70px" borderColor="whiteAlpha.100">Rank</Th>
          <Th color="gray.500" borderColor="whiteAlpha.100">Trio Partnership</Th>
          <Th color="gray.500" isNumeric borderColor="whiteAlpha.100">Wins</Th>
          <Th color="gray.500" isNumeric display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
            Win Rate
          </Th>
          <Th color="gray.500" isNumeric display={{ base: 'none', lg: 'table-cell' }} borderColor="whiteAlpha.100">
            Synergy
          </Th>
        </Tr>
      </Thead>
      <Tbody>
        {entries.map((entry) => (
          <Tr key={entry.player_ids.join('-')} transition="all 0.15s ease" _hover={{ bg: hoverBg }}>
            <Td borderColor="whiteAlpha.100">
              <RankCell rank={entry.rank} />
            </Td>
            <Td borderColor="whiteAlpha.100">
              <HStack spacing={2} flexWrap="wrap">
                {entry.player_names.map((name, idx) => (
                  <React.Fragment key={idx}>
                    <Text
                      fontWeight="700"
                      color="gray.100"
                      cursor="pointer"
                      _hover={{ color: 'brand.400' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onPlayerClick(entry.player_ids[idx]);
                      }}
                    >
                      {name}
                    </Text>
                    {idx < entry.player_names.length - 1 && <Text color="gray.500">&</Text>}
                  </React.Fragment>
                ))}
              </HStack>
            </Td>
            <Td isNumeric borderColor="whiteAlpha.100">
              <Text fontWeight="700" color={entry.rank <= 3 ? 'shield.400' : 'brand.400'} fontFamily="mono">
                {entry.wins_together}
              </Text>
            </Td>
            <Td isNumeric display={{ base: 'none', md: 'table-cell' }} borderColor="whiteAlpha.100">
              <Badge colorScheme={entry.win_rate >= 60 ? 'green' : entry.win_rate >= 50 ? 'yellow' : 'red'}>
                {entry.win_rate.toFixed(1)}%
              </Badge>
            </Td>
            <Td isNumeric display={{ base: 'none', lg: 'table-cell' }} borderColor="whiteAlpha.100">
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

TrioTable.displayName = 'TrioTable';

// =============================================================================
// Main Component
// =============================================================================

const Leaderboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState<LeaderboardCategoryKey>('mmr');
  const [showLegacy, setShowLegacy] = useState(false);

  // Shared with Home's players query; used to keep avatar styles race-consistent
  const { data: playersData } = useQuery<Player[]>({
    queryKey: ['players'],
    queryFn: async () => {
      const response = await playersApi.getAll();
      return response.data;
    },
    staleTime: 60000,
  });

  const raceById = useMemo(() => {
    const map = new Map<number, string>();
    (playersData || []).forEach((p) => {
      if (p.favorite_race) map.set(p.id, p.favorite_race);
    });
    return map;
  }, [playersData]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['leaderboard', activeCategory, showLegacy],
    queryFn: async () => {
      const response = await leaderboardApi.getByCategory(activeCategory, {
        limit: 20,
        minGames: activeCategory === 'winrate' ? 20 : 10,
        activeOnly: activeCategory === 'mmr' ? !showLegacy : undefined,
      });
      return response.data;
    },
    staleTime: 60000, // 1 minute
  });

  const handlePlayerClick = useCallback(
    (playerId: number) => {
      navigate(`/players/${playerId}`);
    },
    [navigate]
  );

  const categoryInfo = useMemo(
    () => LEADERBOARD_CATEGORIES.find((c) => c.key === activeCategory),
    [activeCategory]
  );

  const isTeamCategory = activeCategory === 'duos' || activeCategory === 'trios';
  const standardEntries = !isTeamCategory && data ? (data as LeaderboardEntry[]) : [];
  const showPodium = !isTeamCategory && standardEntries.length >= 3;

  return (
    <Box minH="100vh" pb={16}>
      <PageHeader
        kicker="Squad Records"
        title="The [Ladder]"
        description={categoryInfo?.description}
      />

      <Container maxW="container.xl" pt={6}>
        <VStack spacing={8} align="stretch">
          {/* Category Tabs */}
          <Flex justify="space-between" align="center" gap={3} wrap="wrap">
            <Box overflowX="auto" pb={1}>
              <Flex gap={2} minW="max-content">
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
            {activeCategory === 'mmr' && (
              <FormControl w="auto" display="flex" alignItems="center" gap={2}>
                <FormLabel htmlFor="show-legacy" mb={0} fontSize="sm" color="gray.400" cursor="pointer">
                  Show legacy players
                </FormLabel>
                <Switch
                  id="show-legacy"
                  size="sm"
                  colorScheme="orange"
                  isChecked={showLegacy}
                  onChange={(e) => setShowLegacy(e.target.checked)}
                />
              </FormControl>
            )}
          </Flex>

          {isLoading ? (
            <VStack spacing={4}>
              <Skeleton height="220px" width="100%" borderRadius="2xl" />
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} height="48px" width="100%" borderRadius="md" />
              ))}
            </VStack>
          ) : error ? (
            <Alert status="error" bg="space.800" borderRadius="xl">
              <AlertIcon />
              Failed to load leaderboard data
            </Alert>
          ) : data && data.length > 0 ? (
            <>
              {showPodium && (
                <Podium
                  entries={standardEntries}
                  category={activeCategory}
                  onPlayerClick={handlePlayerClick}
                  raceById={raceById}
                />
              )}
              <Box
                bg="space.800"
                borderRadius="xl"
                border="1px solid"
                borderColor="whiteAlpha.100"
                overflow="hidden"
              >
                {activeCategory === 'duos' ? (
                  <DuoTable entries={data as DuoLeaderboardEntry[]} onPlayerClick={handlePlayerClick} />
                ) : activeCategory === 'trios' ? (
                  <TrioTable entries={data as TrioLeaderboardEntry[]} onPlayerClick={handlePlayerClick} />
                ) : (
                  <StandardTable
                    entries={showPodium ? standardEntries.slice(3) : standardEntries}
                    category={activeCategory}
                    onPlayerClick={handlePlayerClick}
                    raceById={raceById}
                  />
                )}
              </Box>
            </>
          ) : (
            <Box p={8} textAlign="center" bg="space.800" borderRadius="xl">
              <Text color="gray.500">No data available for this category</Text>
            </Box>
          )}
        </VStack>
      </Container>
    </Box>
  );
};

export default Leaderboard;
