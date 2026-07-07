/**
 * Match History Page - Match Archive
 * Browse past games with team rosters, results, and per-player stats.
 */
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Badge,
  Button,
  Icon,
  Grid,
  IconButton,
  ButtonGroup,
  Collapse,
  Avatar,
  AvatarGroup,
  Tooltip,
  Divider,
  Select,
  Input,
  InputGroup,
  InputLeftElement,
} from '@chakra-ui/react';
import { useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import {
  FiTarget,
  FiZap,
  FiActivity,
  FiChevronLeft,
  FiChevronRight,
  FiChevronsLeft,
  FiChevronsRight,
  FiChevronDown,
  FiChevronUp,
  FiAward,
  FiClock,
  FiSearch,
  FiFilter,
} from 'react-icons/fi';
import { LuCrown } from 'react-icons/lu';
import { replaysApi } from '../api/endpoints';
import PageHeader from '../components/PageHeader';
import EmptyState from '../components/EmptyState';
import { MatchCardSkeleton } from '../components/LoadingState';
import {
  formatDuration,
  formatDateTime,
  getRaceColor,
  getPlayerAvatarUrl,
} from '../utils/formatting';
import type { MatchWithPlayers, MatchPlayerSummary, MatchListWithPlayersResponse } from '../types/api';

// Player highlight card component (expanded per-player stats)
const PlayerHighlightCard: React.FC<{
  player: MatchPlayerSummary;
  isMVP: boolean;
}> = ({ player, isMVP }) => {
  const borderColor = player.won ? 'green.400' : 'red.400';
  const highlightBg = player.won ? 'rgba(72, 187, 120, 0.1)' : 'rgba(245, 101, 101, 0.1)';

  return (
    <Box
      bg={highlightBg}
      p={3}
      borderRadius="xl"
      border="2px solid"
      borderColor={borderColor}
      position="relative"
      transition="all 0.2s"
      _hover={{ transform: 'scale(1.02)' }}
    >
      {isMVP && (
        <Badge
          position="absolute"
          top={-2}
          right={2}
          colorScheme="yellow"
          fontSize="xs"
          px={2}
        >
          <Icon as={FiAward} mr={1} />
          MVP
        </Badge>
      )}

      <HStack spacing={3} mb={2}>
        <Avatar
          size="sm"
          name={player.player_name}
          src={getPlayerAvatarUrl(player.player_name, player.race)}
          bg={`${getRaceColor(player.race)}.500`}
        />
        <VStack align="start" spacing={0} flex={1}>
          <HStack>
            <Text fontWeight="bold" fontSize="sm">
              {player.player_name}
            </Text>
            <Badge
              colorScheme={getRaceColor(player.race)}
              fontSize="xs"
            >
              {player.race.charAt(0)}
            </Badge>
          </HStack>
          <Text fontSize="xs" fontFamily="mono" color={player.mmr_change >= 0 ? 'green.400' : 'red.400'}>
            {player.mmr_change >= 0 ? '+' : ''}{Math.round(player.mmr_change)} MMR
          </Text>
        </VStack>
      </HStack>

      {/* Stats row */}
      {player.damage_dealt && (
        <HStack spacing={4} fontSize="xs" color="gray.500" fontFamily="mono">
          <Tooltip label="Damage Dealt">
            <HStack>
              <Icon as={FiZap} />
              <Text>{player.damage_dealt.toLocaleString()}</Text>
            </HStack>
          </Tooltip>
          {player.damage_ratio && player.damage_ratio > 0 && (
            <Tooltip label="Damage Ratio">
              <HStack>
                <Icon as={FiTarget} />
                <Text>
                  {player.damage_ratio >= 100 ? '∞' : player.damage_ratio.toFixed(1)}:1
                </Text>
              </HStack>
            </Tooltip>
          )}
          {player.impact_score && (
            <Tooltip label="Impact Score">
              <HStack>
                <Icon as={FiActivity} />
                <Text>{player.impact_score.toFixed(0)}/100</Text>
              </HStack>
            </Tooltip>
          )}
        </HStack>
      )}
    </Box>
  );
};

// Compact always-visible roster for one team
const TeamRoster: React.FC<{
  label: string;
  players: MatchPlayerSummary[];
  isWinner: boolean;
  accent: string;
  align: 'start' | 'end';
}> = ({ label, players, isWinner, accent, align }) => (
  <VStack align={align} spacing={2} flex={1} minW={0}>
    <HStack spacing={2}>
      {isWinner && <Icon as={LuCrown} color={accent} boxSize="14px" />}
      <Text
        fontFamily="heading"
        fontSize="10px"
        fontWeight="black"
        letterSpacing="widest"
        textTransform="uppercase"
        color={isWinner ? accent : 'gray.500'}
      >
        {label}
      </Text>
      {isWinner && (
        <Badge bg={`${accent === 'shield.400' ? 'shield' : 'accent'}.400`} color="space.900" fontSize="9px" px={1.5} fontFamily="heading">
          WIN
        </Badge>
      )}
    </HStack>
    <AvatarGroup size="sm" max={5} flexDirection={align === 'end' ? 'row-reverse' : 'row'}>
      {players.map((p) => (
        <Avatar
          key={p.player_id}
          size="sm"
          name={p.player_name}
          src={getPlayerAvatarUrl(p.player_name, p.race)}
          bg={`${getRaceColor(p.race)}.500`}
          opacity={isWinner ? 1 : 0.75}
        />
      ))}
    </AvatarGroup>
    <Text
      fontSize="xs"
      color={isWinner ? 'gray.200' : 'gray.500'}
      fontWeight={isWinner ? 'semibold' : 'normal'}
      textAlign={align === 'end' ? 'right' : 'left'}
      noOfLines={2}
      w="100%"
    >
      {players.map((p) => p.player_name).join(', ')}
    </Text>
  </VStack>
);

// Match card component with always-visible rosters and expandable player details
const MatchCard: React.FC<{
  match: MatchWithPlayers;
  onNavigate: (id: number) => void;
}> = ({ match, onNavigate }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const team1Players = match.players.filter((p) => p.team_number === 1);
  const team2Players = match.players.filter((p) => p.team_number === 2);

  return (
    <Box
      bg="space.800"
      borderRadius="xl"
      border="1px solid"
      borderColor="whiteAlpha.100"
      position="relative"
      overflow="hidden"
      transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
      _hover={{
        borderColor: 'brand.500',
        transform: 'translateY(-2px)',
      }}
    >
      <Box p={5}>
        {/* Header: map, mode, meta, actions - clickable to expand */}
        <Box cursor="pointer" onClick={() => setIsExpanded(!isExpanded)}>
          <Grid
            templateColumns={{ base: '1fr', md: '1fr auto' }}
            gap={4}
            alignItems="center"
          >
            <VStack align="start" spacing={2} minW={0}>
              <HStack spacing={3} flexWrap="wrap">
                <Heading size="md" fontFamily="heading" letterSpacing="wide" color="gray.100">
                  {match.map_name}
                </Heading>
                <Badge
                  bg="space.900"
                  color="brand.400"
                  fontSize="xs"
                  px={2}
                  py={1}
                  borderRadius="md"
                  fontFamily="heading"
                >
                  {match.game_mode}
                </Badge>
              </HStack>

              <HStack spacing={4} fontSize="xs" color="gray.500" fontFamily="mono" flexWrap="wrap">
                <HStack spacing={1}>
                  <Icon as={FiClock} />
                  <Text>{formatDateTime(match.played_at)}</Text>
                </HStack>
                <Text>•</Text>
                <HStack spacing={1}>
                  <Icon as={FiActivity} />
                  <Text>{formatDuration(match.duration_seconds)}</Text>
                </HStack>
                {match.total_damage && (
                  <>
                    <Text>•</Text>
                    <HStack spacing={1}>
                      <Icon as={FiTarget} />
                      <Text>{match.total_damage.toLocaleString()} DMG</Text>
                    </HStack>
                  </>
                )}
              </HStack>
            </VStack>

            <HStack spacing={3}>
              <Button
                size="sm"
                variant="outline"
                colorScheme="brand"
                rightIcon={<Icon as={FiChevronRight} />}
                fontFamily="heading"
                onClick={(e) => {
                  e.stopPropagation();
                  onNavigate(match.id);
                }}
                borderRadius="lg"
                _hover={{ bg: 'brand.500', color: 'gray.900' }}
              >
                Details
              </Button>
              <IconButton
                aria-label={isExpanded ? 'Collapse' : 'Expand'}
                icon={isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                size="sm"
                variant="ghost"
                color="gray.500"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsExpanded(!isExpanded);
                }}
              />
            </HStack>
          </Grid>

          {/* Always-visible rosters */}
          <Grid
            templateColumns={{ base: '1fr auto 1fr' }}
            gap={{ base: 3, md: 6 }}
            alignItems="center"
            mt={4}
            pt={4}
            borderTop="1px solid"
            borderColor="whiteAlpha.100"
          >
            <TeamRoster
              label="Team 1"
              players={team1Players}
              isWinner={match.winner_team === 1}
              accent="shield.400"
              align="start"
            />
            <Text
              fontFamily="heading"
              fontSize="xs"
              fontWeight="black"
              color="whiteAlpha.400"
              letterSpacing="widest"
            >
              VS
            </Text>
            <TeamRoster
              label="Team 2"
              players={team2Players}
              isWinner={match.winner_team === 2}
              accent="accent.400"
              align="end"
            />
          </Grid>
        </Box>

        {/* Expandable per-player stats */}
        <Collapse in={isExpanded} animateOpacity>
          <Divider my={5} borderColor="whiteAlpha.100" />
          <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
            <Box>
              <Text
                fontFamily="heading"
                fontSize="xs"
                fontWeight="black"
                letterSpacing="widest"
                textTransform="uppercase"
                color={match.winner_team === 1 ? 'shield.400' : 'gray.500'}
                mb={3}
              >
                Team 1 Squad
              </Text>
              <VStack spacing={3} align="stretch">
                {team1Players.map((player) => (
                  <PlayerHighlightCard
                    key={player.player_id}
                    player={player}
                    isMVP={player.player_id === match.mvp_player_id}
                  />
                ))}
              </VStack>
            </Box>
            <Box>
              <Text
                fontFamily="heading"
                fontSize="xs"
                fontWeight="black"
                letterSpacing="widest"
                textTransform="uppercase"
                color={match.winner_team === 2 ? 'accent.400' : 'gray.500'}
                mb={3}
              >
                Team 2 Squad
              </Text>
              <VStack spacing={3} align="stretch">
                {team2Players.map((player) => (
                  <PlayerHighlightCard
                    key={player.player_id}
                    player={player}
                    isMVP={player.player_id === match.mvp_player_id}
                  />
                ))}
              </VStack>
            </Box>
          </Grid>
        </Collapse>
      </Box>
    </Box>
  );
};

const MATCHES_PER_PAGE = 15;

// Game modes offered in the filter dropdown (mirrors the backend GameMode enum).
// Static list keeps the dropdown stable without fetching the whole archive.
const GAME_MODES = [
  '1v1',
  '2v2',
  '3v3',
  '4v4',
  '5v5',
  '2v1',
  '3v1',
  '3v2',
  '4v1',
  '4v2',
  '4v3',
  '5v1',
  '5v2',
  '5v3',
  '5v4',
];

const MatchHistory: React.FC = () => {
  const navigate = useNavigate();

  // The URL is the source of truth for filters + page, so searches are
  // deep-linkable and survive back/forward navigation.
  const [searchParams, setSearchParams] = useSearchParams();
  const urlSearch = searchParams.get('q') ?? '';
  const modeFilter = searchParams.get('mode') ?? '';
  const currentPage = Math.max(1, parseInt(searchParams.get('page') ?? '1', 10) || 1);

  const updateParams = (updates: Record<string, string>, replace = false): void => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setSearchParams(next, { replace });
  };

  // Local input state so typing is instant; debounced into the URL (~300ms),
  // which resets to page 1 and triggers the query.
  const [searchText, setSearchText] = useState<string>(urlSearch);
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchText !== urlSearch) updateParams({ q: searchText, page: '' }, true);
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText]);
  // Keep the input in sync when the URL changes underneath us (back button).
  useEffect(() => {
    setSearchText(urlSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSearch]);

  const hasFilters = Boolean(urlSearch || modeFilter);
  const availableModes = GAME_MODES;

  // Server-side pagination + filtering: fetch only the current page for the
  // active filters instead of pulling the whole archive down at once.
  const { data: matchesData, isLoading } = useQuery<MatchListWithPlayersResponse>({
    queryKey: ['matches-with-players', currentPage, urlSearch, modeFilter],
    queryFn: async () => {
      const response = await replaysApi.getMatchesWithPlayers(
        MATCHES_PER_PAGE,
        (currentPage - 1) * MATCHES_PER_PAGE,
        { search: urlSearch, game_mode: modeFilter }
      );
      return response.data;
    },
    placeholderData: keepPreviousData,
  });

  const pageMatches = useMemo(() => matchesData?.matches || [], [matchesData]);

  // total_count is the count for the active filters (drives pagination);
  // grand_total is the whole archive (drives the header stat).
  const filteredTotal = matchesData?.total_count || 0;
  const totalMatches = matchesData?.grand_total ?? filteredTotal;
  const totalPages = Math.ceil(filteredTotal / MATCHES_PER_PAGE) || 1;
  const safePage = Math.min(currentPage, totalPages);

  const handlePageChange = (newPage: number): void => {
    updateParams({ page: newPage > 1 ? String(newPage) : '' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setSearchText(e.target.value);
  };

  const handleModeChange = (e: ChangeEvent<HTMLSelectElement>): void => {
    updateParams({ mode: e.target.value, page: '' });
  };

  const clearFilters = (): void => {
    setSearchText('');
    updateParams({ q: '', mode: '', page: '' });
  };

  const handleNavigate = (matchId: number): void => {
    navigate(`/history/${matchId}`);
  };

  const header = (
    <PageHeader
      kicker="Battle Log"
      title="Match [Archive]"
      description="Every game the squad has played, with the receipts to prove it."
      stats={[
        { label: 'Battles recorded', value: totalMatches },
        { label: hasFilters ? 'matches shown' : `of ${totalPages} pages`, value: hasFilters ? filteredTotal : safePage },
      ]}
    />
  );

  if (isLoading) {
    return (
      <Box minH="100vh" pb={16}>
        {header}
        <Container maxW="container.xl" pt={8}>
          <VStack spacing={4}>
            {Array.from({ length: 10 }).map((_, idx) => (
              <MatchCardSkeleton key={idx} />
            ))}
          </VStack>
        </Container>
      </Box>
    );
  }

  if (!hasFilters && filteredTotal === 0) {
    return (
      <Box minH="100vh" pb={16}>
        {header}
        <Container maxW="container.xl" pt={8}>
          <EmptyState
            variant="stats"
            title="No Matches Yet"
            description="Upload some replay files to start tracking your game history."
            onAction={() => navigate('/upload')}
          />
        </Container>
      </Box>
    );
  }

  return (
    <Box position="relative" minH="100vh" pb={16}>
      {header}
      <Container maxW="container.xl" pt={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Filters */}
          <Box
            bg="space.800"
            borderRadius="xl"
            border="1px solid"
            borderColor="whiteAlpha.100"
            p={4}
          >
            <HStack spacing={4} justify="space-between" flexWrap="wrap">
              <HStack spacing={4} flex={1} minW={0} flexWrap="wrap">
                <InputGroup maxW="360px">
                  <InputLeftElement pointerEvents="none">
                    <Icon as={FiSearch} color="gray.500" />
                  </InputLeftElement>
                  <Input
                    placeholder="Search map or player…"
                    value={searchText}
                    onChange={handleSearchChange}
                    bg="space.900"
                    borderColor="whiteAlpha.200"
                  />
                </InputGroup>

                <HStack spacing={2}>
                  <Icon as={FiFilter} color="gray.500" />
                  <Select
                    placeholder="All Modes"
                    value={modeFilter}
                    onChange={handleModeChange}
                    maxW="180px"
                    bg="space.900"
                    borderColor="whiteAlpha.200"
                  >
                    {availableModes.map((mode) => (
                      <option key={mode} value={mode}>
                        {mode}
                      </option>
                    ))}
                  </Select>
                </HStack>
              </HStack>

              {hasFilters && (
                <Button size="sm" variant="ghost" onClick={clearFilters}>
                  Clear Filters
                </Button>
              )}
            </HStack>
          </Box>

          {/* Match List */}
          {pageMatches.length === 0 ? (
            <EmptyState
              variant="stats"
              title="No Matches Found"
              description="No matches match your search or filter. Try adjusting them."
            />
          ) : (
            <VStack spacing={4} align="stretch">
              {pageMatches.map((match) => (
                <MatchCard key={match.id} match={match} onNavigate={handleNavigate} />
              ))}
            </VStack>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <Box mt={8}>
              <VStack spacing={4}>
                <Text
                  color="gray.500"
                  fontFamily="heading"
                  fontSize="sm"
                  letterSpacing="wide"
                >
                  Page {safePage} of {totalPages} • Showing {pageMatches.length} of {filteredTotal} matches
                </Text>

                <HStack spacing={2}>
                  <IconButton
                    icon={<FiChevronsLeft />}
                    onClick={() => handlePageChange(1)}
                    isDisabled={safePage === 1}
                    aria-label="First page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />
                  <IconButton
                    icon={<FiChevronLeft />}
                    onClick={() => handlePageChange(safePage - 1)}
                    isDisabled={safePage === 1}
                    aria-label="Previous page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />

                  <ButtonGroup spacing={2}>
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum: number;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (safePage <= 3) {
                        pageNum = i + 1;
                      } else if (safePage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = safePage - 2 + i;
                      }

                      return (
                        <Button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          variant={safePage === pageNum ? 'solid' : 'ghost'}
                          colorScheme="cyan"
                          size="lg"
                          fontFamily="heading"
                          minW="50px"
                          bg={safePage === pageNum ? 'brand.500' : undefined}
                          color={safePage === pageNum ? 'gray.900' : undefined}
                          _hover={{
                            bg: safePage === pageNum ? 'brand.400' : 'whiteAlpha.200',
                          }}
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                  </ButtonGroup>

                  <IconButton
                    icon={<FiChevronRight />}
                    onClick={() => handlePageChange(safePage + 1)}
                    isDisabled={safePage === totalPages}
                    aria-label="Next page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />
                  <IconButton
                    icon={<FiChevronsRight />}
                    onClick={() => handlePageChange(totalPages)}
                    isDisabled={safePage === totalPages}
                    aria-label="Last page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />
                </HStack>
              </VStack>
            </Box>
          )}
        </VStack>
      </Container>
    </Box>
  );
};

export default MatchHistory;
