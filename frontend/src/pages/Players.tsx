/**
 * Players Page - Clubhouse Edition
 * One home for the squad: top-3 podium, then a searchable ranking table
 * with races, activity and recent form. Other boards (Combat, Win Rate, ...)
 * are alternate views behind the category switcher.
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
  Skeleton,
  Alert,
  AlertIcon,
  Icon,
  Avatar,
  Input,
  InputGroup,
  InputLeftElement,
  Link,
  Tooltip,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { keyframes } from '@emotion/react';
import { FiActivity, FiTrendingUp, FiSearch } from 'react-icons/fi';
import type { IconType } from 'react-icons';
import { LuTrophy, LuSwords, LuFlame, LuCrown, LuSnowflake } from 'react-icons/lu';
import { leaderboardApi } from '../api/leaderboard';
import { playersApi } from '../api/endpoints';
import RankBadge from '../components/RankBadge';
import PageHeader from '../components/PageHeader';
import EmptyState from '../components/EmptyState';
import { formatDate, formatWinRate, getPlayerAvatarUrl, getPlayerRaces } from '../utils/formatting';
import type { Player } from '../types/api';
import {
  LEADERBOARD_CATEGORIES,
  LeaderboardCategoryKey,
  LeaderboardEntry,
  formatLeaderboardValue,
} from '../types/leaderboard';
import LapsedToggle from '@/components/LapsedToggle';

// Parse a "383W 325L" record string into a win-rate percentage.
// Returns null when the extra_info isn't a W/L record (e.g. "Current: 1").
const winRateFromRecord = (info?: string): string | null => {
  if (!info) return null;
  const match = info.match(/(\d+)\s*W\s*(\d+)\s*L/i);
  if (!match) return null;
  const wins = parseInt(match[1], 10);
  const losses = parseInt(match[2], 10);
  const total = wins + losses;
  if (total === 0) return null;
  return `${((wins / total) * 100).toFixed(1)}%`;
};

const CATEGORY_ICONS: Record<string, IconType> = {
  mmr: LuTrophy,
  'recent-form': FiActivity,
  combat: LuSwords,
  winrate: FiTrendingUp,
  winstreak: LuFlame,
};

const HOT_TONE = { icon: LuFlame, color: 'orange.400', label: 'Hot' };
const COLD_TONE = { icon: LuSnowflake, color: 'blue.400', label: 'Cold' };

// Same hot/cold thresholds PlayerCard uses; recentForm is last-5 win rate (0.0-1.0)
const toneFromRecentForm = (recentForm: number | null | undefined) => {
  if (recentForm == null) return null;
  if (recentForm >= 0.7) return HOT_TONE;
  if (recentForm <= 0.3) return COLD_TONE;
  return null;
};

// The recent-form board sends its hot/cold flag as an emoji
const toneFromFormIcon = (formIcon: string | null | undefined) => {
  if (formIcon === '🔥') return HOT_TONE;
  if (formIcon?.startsWith('❄')) return COLD_TONE;
  return null;
};

const toEntry = (player: Player, rank: number): LeaderboardEntry => ({
  rank,
  player_id: player.id,
  name: player.name,
  value: player.mmr,
  extra_info: `${player.wins}W ${player.losses}L`,
  is_new: player.is_new,
  is_active: player.is_active,
});

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
      <Text>{category.name}</Text>
    </HStack>
  </Button>
));

CategoryTab.displayName = 'CategoryTab';

// =============================================================================
// Podium (top 3)
// =============================================================================

interface PodiumProps {
  entries: LeaderboardEntry[];
  category: LeaderboardCategoryKey;
  onPlayerClick: (playerId: number) => void;
  raceById: Map<number, string>;
}

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
    step: '56px',
    avatar: '72px',
    order: { base: 0, md: 1 },
  },
  {
    hex: '#CBD5E1',
    soft: 'rgba(203, 213, 225, 0.10)',
    border: 'rgba(203, 213, 225, 0.35)',
    text: 'gray.300',
    step: '36px',
    avatar: '52px',
    order: { base: 1, md: 0 },
  },
  {
    hex: '#D97706',
    soft: 'rgba(217, 119, 6, 0.12)',
    border: 'rgba(217, 119, 6, 0.45)',
    text: 'orange.400',
    step: '22px',
    avatar: '52px',
    order: { base: 2, md: 2 },
  },
];

const Podium: React.FC<PodiumProps> = React.memo(({ entries, category, onPlayerClick, raceById }) => {
  const top3 = entries.slice(0, 3);
  if (top3.length < 3) return null;

  return (
    <Flex
      gap={{ base: 2, md: 4 }}
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
            _hover={{ transform: 'translateY(-4px)' }}
            onClick={() => onPlayerClick(entry.player_id)}
          >
            <Box
              position="relative"
              overflow="hidden"
              bg={isChampion ? `linear-gradient(180deg, ${medal.soft}, var(--chakra-colors-space-800) 55%)` : 'space.800'}
              borderRadius={{ base: 'xl', md: '2xl 2xl 0 0' }}
              border="1px solid"
              borderBottom={{ base: '1px solid', md: 'none' }}
              borderColor={medal.border}
              boxShadow={isChampion ? '0 0 60px rgba(251, 191, 36, 0.10)' : 'none'}
              textAlign={{ base: 'left', md: 'center' }}
              display={{ base: 'flex', md: 'block' }}
              alignItems="center"
              gap={3}
              px={{ base: 3, md: 5 }}
              pt={{ base: 2.5, md: isChampion ? 7 : 5 }}
              pb={{ base: 2.5, md: 4 }}
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
              <Text display={{ base: 'block', md: 'none' }} fontFamily="heading" fontWeight="800" fontSize="xl" color={medal.text} w="20px">
                {idx + 1}
              </Text>
              <Box position="relative" display="inline-block" mb={{ base: 0, md: 2 }} flexShrink={0}>
                {isChampion && (
                  <Icon
                    as={LuCrown}
                    color="shield.400"
                    boxSize={{ base: '18px', md: '24px' }}
                    position="absolute"
                    top={{ base: '-13px', md: '-18px' }}
                    left="50%"
                    transform="translateX(-50%) rotate(-8deg)"
                    filter="drop-shadow(0 0 6px rgba(251, 191, 36, 0.6))"
                    zIndex={1}
                  />
                )}
                <Avatar
                  boxSize={{ base: '40px', md: medal.avatar }}
                  src={getPlayerAvatarUrl(entry.name, raceById.get(entry.player_id))}
                  name={entry.name}
                  border="3px solid"
                  borderColor={medal.hex}
                  boxShadow={`0 0 0 4px ${medal.soft}`}
                />
              </Box>
              <Box minW={0} flex={{ base: 1, md: 'none' }}>
                <Heading fontSize={{ base: 'md', md: isChampion ? '2xl' : 'lg' }} color="gray.50" noOfLines={1}>
                  {entry.name}
                </Heading>
                {entry.extra_info && (
                  <Text fontSize="xs" color="gray.500" mt={{ base: 0, md: 1 }} noOfLines={1} fontFamily="mono">
                    {entry.extra_info}
                  </Text>
                )}
              </Box>
              <Box textAlign={{ base: 'right', md: 'center' }} flexShrink={0} mt={{ base: 0, md: 2 }}>
                <Text
                  fontFamily="mono"
                  fontWeight="700"
                  fontSize={{ base: 'lg', md: isChampion ? '3xl' : 'xl' }}
                  lineHeight="1.1"
                  color={medal.text}
                >
                  {formatLeaderboardValue(entry.value, category)}
                </Text>
                {category === 'mmr' && (
                  <HStack justify={{ base: 'flex-end', md: 'center' }} mt={1}>
                    <RankBadge mmr={entry.value} size="xs" showMMR={false} />
                  </HStack>
                )}
              </Box>
            </Box>

            <Flex
              h={medal.step}
              display={{ base: 'none', md: 'flex' }}
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
                fontSize={isChampion ? '3xl' : 'xl'}
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
// Table building blocks
// =============================================================================

const RankCell: React.FC<{ rank: number }> = React.memo(({ rank }) => (
  <Text
    fontFamily="heading"
    fontWeight="800"
    fontSize={{ base: 'lg', md: 'xl' }}
    color={rank <= 3 ? 'brand.400' : 'whiteAlpha.400'}
    whiteSpace="nowrap"
  >
    {rank}
  </Text>
));

RankCell.displayName = 'RankCell';

interface PlayerCellProps {
  playerId: number;
  name: string;
  race?: string;
  isAi?: boolean;
  isNew?: boolean;
  isLapsed?: boolean;
}

const PlayerCell: React.FC<PlayerCellProps> = ({ playerId, name, race, isAi, isNew, isLapsed }) => (
  <HStack spacing={{ base: 2, md: 3 }} minW={0}>
    <Avatar size="xs" src={getPlayerAvatarUrl(name, race, isAi)} name={name} flexShrink={0} />
    <Link
      as={RouterLink}
      to={`/players/${playerId}`}
      onClick={(e) => e.stopPropagation()}
      fontWeight="700"
      color="gray.100"
      fontFamily="heading"
      noOfLines={1}
      minW={0}
      _hover={{ color: 'brand.400' }}
    >
      {name}
    </Link>
    {isAi && (
      <Badge colorScheme="purple" variant="solid" fontSize="9px" px={1.5}>
        AI
      </Badge>
    )}
    {isNew && (
      <Badge colorScheme="teal" fontSize="9px" px={1.5} display={{ base: 'none', sm: 'inline-block' }}>
        NEW
      </Badge>
    )}
    {isLapsed && (
      <Badge colorScheme="gray" fontSize="9px" px={1.5}>
        LAPSED
      </Badge>
    )}
  </HStack>
);

const FormPips: React.FC<{ recentForm: number | null | undefined }> = ({ recentForm }) => {
  if (recentForm == null) {
    return <Text color="gray.600" fontFamily="mono" fontSize="sm">-</Text>;
  }
  const filled = Math.round(recentForm * 5);
  const tone = toneFromRecentForm(recentForm);
  return (
    <Tooltip label={`${Math.round(recentForm * 100)}% win rate over last 5 games`} hasArrow fontSize="xs">
      <HStack spacing={1} justify="flex-end">
        {tone && <Icon as={tone.icon} color={tone.color} boxSize={3.5} filter="drop-shadow(0 0 3px currentColor)" />}
        {[0, 1, 2, 3, 4].map((i) => (
          <Box key={i} w="6px" h="6px" borderRadius="full" bg={i < filled ? 'green.400' : 'whiteAlpha.300'} />
        ))}
      </HStack>
    </Tooltip>
  );
};

const thProps = { color: 'gray.500', borderColor: 'whiteAlpha.100' } as const;
const tdProps = { borderColor: 'whiteAlpha.100' } as const;
const tableSx = { 'th, td': { px: [2, null, 4], py: [3, null, 3.5] } };
const fromSm = { base: 'none', sm: 'table-cell' } as const;
const fromMd = { base: 'none', md: 'table-cell' } as const;
const fromLg = { base: 'none', lg: 'table-cell' } as const;

// =============================================================================
// MMR ranking table (players API: has races, activity and form)
// =============================================================================

interface RankedPlayer {
  rank: number;
  player: Player;
}

interface RankingTableProps {
  rows: RankedPlayer[];
  onPlayerClick: (playerId: number) => void;
}

const RankingTable: React.FC<RankingTableProps> = React.memo(({ rows, onPlayerClick }) => (
  <Table variant="simple" size="md" sx={tableSx}>
    <Thead>
      <Tr>
        <Th {...thProps} w={{ base: '32px', md: '64px' }}>Rank</Th>
        <Th {...thProps}>Player</Th>
        <Th {...thProps} isNumeric>MMR</Th>
        <Th {...thProps} display={fromMd}>Record</Th>
        <Th {...thProps} isNumeric display={fromMd}>Win rate</Th>
        <Th {...thProps} display={fromLg}>Races</Th>
        <Th {...thProps} display={fromLg}>Last seen</Th>
        <Th {...thProps} isNumeric display={fromSm}>Form</Th>
      </Tr>
    </Thead>
    <Tbody>
      {rows.map(({ rank, player }) => (
        <Tr
          key={player.id}
          cursor="pointer"
          transition="all 0.15s ease"
          _hover={{ bg: 'whiteAlpha.100' }}
          onClick={() => onPlayerClick(player.id)}
        >
          <Td {...tdProps}>
            <RankCell rank={rank} />
          </Td>
          <Td {...tdProps} maxW={{ base: '170px', md: 'none' }}>
            <PlayerCell
              playerId={player.id}
              name={player.name}
              race={player.favorite_race}
              isAi={player.is_ai}
              isNew={player.is_new}
              isLapsed={player.is_active === false}
            />
          </Td>
          <Td {...tdProps} isNumeric>
            <HStack justify="flex-end" spacing={3}>
              <Box display={{ base: 'none', md: 'block' }}>
                <RankBadge mmr={player.mmr} size="xs" showMMR={false} />
              </Box>
              <Text fontWeight="700" color={rank <= 3 ? 'shield.400' : 'brand.400'} fontFamily="mono" fontSize="md">
                {formatLeaderboardValue(player.mmr, 'mmr')}
              </Text>
            </HStack>
          </Td>
          <Td {...tdProps} display={fromMd}>
            <Text color="gray.400" fontFamily="mono" fontSize="sm" whiteSpace="nowrap">
              {player.wins}W {player.losses}L
            </Text>
          </Td>
          <Td {...tdProps} isNumeric display={fromMd}>
            <Text color="gray.300" fontFamily="mono" fontSize="sm" fontWeight="600">
              {formatWinRate(player.win_rate)}
            </Text>
          </Td>
          <Td {...tdProps} display={fromLg}>
            <HStack spacing={1}>
              {getPlayerRaces(player).map((race) => (
                <Tooltip key={race.name} label={`${race.name} · ${race.games} games`} hasArrow fontSize="xs">
                  <Badge variant={`race-${race.name.toLowerCase()}`} fontSize="10px" px={1.5} fontFamily="mono">
                    {race.emoji}
                  </Badge>
                </Tooltip>
              ))}
            </HStack>
          </Td>
          <Td {...tdProps} display={fromLg}>
            <Text color="gray.400" fontSize="sm" whiteSpace="nowrap">
              {formatDate(player.last_played)}
            </Text>
          </Td>
          <Td {...tdProps} isNumeric display={fromSm}>
            <FormPips recentForm={player.recent_form} />
          </Td>
        </Tr>
      ))}
    </Tbody>
  </Table>
));

RankingTable.displayName = 'RankingTable';

// =============================================================================
// Other categories (leaderboard API)
// =============================================================================

interface CategoryTableProps {
  entries: LeaderboardEntry[];
  category: LeaderboardCategoryKey;
  onPlayerClick: (playerId: number) => void;
  raceById: Map<number, string>;
}

const CategoryTable: React.FC<CategoryTableProps> = React.memo(({ entries, category, onPlayerClick, raceById }) => {
  const categoryInfo = LEADERBOARD_CATEGORIES.find((c) => c.key === category);
  const isRecentForm = category === 'recent-form';
  const showRecordCols = category === 'winrate';

  return (
    <Table variant="simple" size="md" sx={tableSx}>
      <Thead>
        <Tr>
          <Th {...thProps} w={{ base: '32px', md: '64px' }}>Rank</Th>
          <Th {...thProps}>Player</Th>
          <Th {...thProps} isNumeric>{categoryInfo?.unit || 'Value'}</Th>
          {isRecentForm ? (
            <>
              <Th {...thProps} isNumeric display={fromMd}>Games</Th>
              <Th {...thProps} isNumeric display={fromMd}>WR</Th>
            </>
          ) : showRecordCols ? (
            <>
              <Th {...thProps} display={fromMd}>Record</Th>
              <Th {...thProps} isNumeric display={fromMd}>Win rate</Th>
            </>
          ) : (
            <Th {...thProps} display={fromMd}>Info</Th>
          )}
        </Tr>
      </Thead>
      <Tbody>
        {entries.map((entry) => {
          const tone = toneFromFormIcon(entry.form_icon);
          return (
            <Tr
              key={entry.player_id}
              cursor="pointer"
              transition="all 0.15s ease"
              _hover={{ bg: 'whiteAlpha.100' }}
              onClick={() => onPlayerClick(entry.player_id)}
            >
              <Td {...tdProps}>
                <RankCell rank={entry.rank} />
              </Td>
              <Td {...tdProps} maxW={{ base: '170px', md: 'none' }}>
                <PlayerCell
                  playerId={entry.player_id}
                  name={entry.name}
                  race={raceById.get(entry.player_id)}
                  isNew={entry.is_new}
                  isLapsed={entry.is_active === false}
                />
              </Td>
              <Td {...tdProps} isNumeric>
                <Text fontWeight="700" color={entry.rank <= 3 ? 'shield.400' : 'brand.400'} fontFamily="mono" fontSize="md">
                  {formatLeaderboardValue(entry.value, category)}
                </Text>
              </Td>
              {isRecentForm ? (
                <>
                  <Td {...tdProps} isNumeric display={fromMd}>
                    <Text color="gray.400" fontFamily="mono" fontSize="sm">
                      {entry.games_played ?? '-'}/30
                    </Text>
                  </Td>
                  <Td {...tdProps} isNumeric display={fromMd}>
                    <HStack justify="flex-end" spacing={1.5}>
                      {tone && <Icon as={tone.icon} color={tone.color} boxSize={3.5} aria-label={tone.label} />}
                      <Text color="gray.300" fontFamily="mono" fontSize="sm" fontWeight="600">
                        {entry.secondary_value != null ? `${entry.secondary_value}%` : '-'}
                      </Text>
                    </HStack>
                  </Td>
                </>
              ) : showRecordCols ? (
                <>
                  <Td {...tdProps} display={fromMd}>
                    <Text color="gray.400" fontFamily="mono" fontSize="sm">
                      {entry.extra_info || '-'}
                    </Text>
                  </Td>
                  <Td {...tdProps} isNumeric display={fromMd}>
                    <Text color="gray.300" fontFamily="mono" fontSize="sm" fontWeight="600">
                      {winRateFromRecord(entry.extra_info) ?? '-'}
                    </Text>
                  </Td>
                </>
              ) : (
                <Td {...tdProps} display={fromMd}>
                  <Text color="gray.500" fontSize="sm">
                    {entry.extra_info || '-'}
                  </Text>
                </Td>
              )}
            </Tr>
          );
        })}
      </Tbody>
    </Table>
  );
});

CategoryTable.displayName = 'CategoryTable';

// =============================================================================
// Main Component
// =============================================================================

const Players: React.FC = () => {
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState<LeaderboardCategoryKey>('mmr');
  const [showLapsed, setShowLapsed] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const isMmrView = activeCategory === 'mmr';

  const {
    data: playersData,
    isLoading: loadingPlayers,
    error: playersError,
  } = useQuery<Player[]>({
    queryKey: ['players'],
    queryFn: async () => (await playersApi.getAll()).data,
    staleTime: 60000,
  });

  const {
    data: categoryData,
    isLoading: loadingCategory,
    error: categoryError,
  } = useQuery({
    queryKey: ['leaderboard', activeCategory],
    queryFn: async () =>
      (
        await leaderboardApi.getByCategory(activeCategory, {
          limit: 20,
          minGames: activeCategory === 'winrate' ? 20 : 10,
        })
      ).data as LeaderboardEntry[],
    enabled: !isMmrView,
    staleTime: 60000,
  });

  const raceById = useMemo(() => {
    const map = new Map<number, string>();
    (playersData || []).forEach((p) => {
      if (p.favorite_race) map.set(p.id, p.favorite_race);
    });
    return map;
  }, [playersData]);

  const rankedPlayers = useMemo<RankedPlayer[]>(
    () =>
      (playersData || [])
        // A missing is_active flag counts as active so older backends still list everyone
        .filter((p) => p.total_games > 0 && (showLapsed || (p.is_active ?? true)))
        .sort((a, b) => b.mmr - a.mmr)
        .map((player, i) => ({ rank: i + 1, player })),
    [playersData, showLapsed]
  );

  const handlePlayerClick = useCallback((playerId: number) => navigate(`/players/${playerId}`), [navigate]);

  const query = searchTerm.trim().toLowerCase();
  const isSearching = query !== '';
  const matchesSearch = (name: string) => name.toLowerCase().includes(query);

  const podiumEntries = isMmrView
    ? rankedPlayers.slice(0, 3).map(({ rank, player }) => toEntry(player, rank))
    : (categoryData || []).slice(0, 3);
  const showPodium = !isSearching && podiumEntries.length >= 3;
  const tableStart = showPodium ? 3 : 0;

  const rankingRows = rankedPlayers.slice(tableStart).filter(({ player }) => matchesSearch(player.name));
  const categoryRows = (categoryData || []).slice(tableStart).filter((entry) => matchesSearch(entry.name));
  const visibleRowCount = isMmrView ? rankingRows.length : categoryRows.length;

  const isLoading = isMmrView ? loadingPlayers : loadingCategory;
  const error = isMmrView ? playersError : categoryError;
  const hasNoPlayers = !loadingPlayers && !playersError && rankedPlayers.length === 0 && !showLapsed;

  const categoryInfo = LEADERBOARD_CATEGORIES.find((c) => c.key === activeCategory);

  return (
    <Box minH="100vh" pb={16}>
      <PageHeader
        kicker="Squad Records"
        title="The [Players]"
        description={
          isMmrView
            ? 'Everyone in the squad, ranked by MMR — with races, recent form and who has been playing lately.'
            : categoryInfo?.description
        }
        stats={isMmrView ? [{ label: showLapsed ? 'Players incl. lapsed' : 'Current players', value: rankedPlayers.length }] : undefined}
      />

      <Container maxW="container.xl" pt={6}>
        {hasNoPlayers ? (
          <EmptyState variant="players" onAction={() => navigate('/upload')} />
        ) : (
          <VStack spacing={6} align="stretch">
            <Box overflowX="auto" pb={1} mx={{ base: -4, md: 0 }} px={{ base: 4, md: 0 }} sx={{ WebkitOverflowScrolling: 'touch' }}>
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

            {isLoading ? (
              <VStack spacing={4}>
                <Skeleton height="180px" width="100%" borderRadius="2xl" />
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} height="48px" width="100%" borderRadius="md" />
                ))}
              </VStack>
            ) : error ? (
              <Alert status="error" bg="space.800" borderRadius="xl">
                <AlertIcon />
                Failed to load player rankings
              </Alert>
            ) : (
              <>
                {showPodium && (
                  <Podium
                    entries={podiumEntries}
                    category={activeCategory}
                    onPlayerClick={handlePlayerClick}
                    raceById={raceById}
                  />
                )}

                <Box>
                  <Flex justify="space-between" align="center" gap={3} wrap="wrap" mb={3}>
                    <InputGroup size="sm" w={{ base: '100%', sm: '260px' }}>
                      <InputLeftElement pointerEvents="none">
                        <Icon as={FiSearch} color="gray.500" />
                      </InputLeftElement>
                      <Input
                        aria-label="Search players"
                        placeholder="Search players..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        borderRadius="full"
                        bg="whiteAlpha.100"
                        border="1px solid"
                        borderColor="whiteAlpha.200"
                        _placeholder={{ color: 'gray.500' }}
                        _focus={{ borderColor: 'brand.500', boxShadow: '0 0 0 2px rgba(255, 107, 53, 0.3)' }}
                      />
                    </InputGroup>
                    {isMmrView && <LapsedToggle id="show-lapsed" isChecked={showLapsed} onChange={setShowLapsed} />}
                  </Flex>

                  {visibleRowCount > 0 ? (
                    <Box bg="space.800" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100" overflowX="auto">
                      {isMmrView ? (
                        <RankingTable rows={rankingRows} onPlayerClick={handlePlayerClick} />
                      ) : (
                        <CategoryTable
                          entries={categoryRows}
                          category={activeCategory}
                          onPlayerClick={handlePlayerClick}
                          raceById={raceById}
                        />
                      )}
                    </Box>
                  ) : (
                    <Box p={8} textAlign="center" bg="space.800" borderRadius="xl" border="1px dashed" borderColor="whiteAlpha.300">
                      <Text color="gray.500">
                        {isSearching ? `No players matching "${searchTerm}"` : showPodium ? 'Only three players on this board' : 'No data available for this category'}
                      </Text>
                    </Box>
                  )}
                </Box>
              </>
            )}
          </VStack>
        )}
      </Container>
    </Box>
  );
};

export default Players;
