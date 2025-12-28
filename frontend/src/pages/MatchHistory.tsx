/**
 * Match History Page - Match Archive
 * Browse past games with esports commentary and player highlights
 */
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  Badge,
  Button,
  useColorModeValue,
  Icon,
  Progress,
  Grid,
  IconButton,
  ButtonGroup,
  Collapse,
  Avatar,
  Tooltip,
  Divider,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import {
  FiTarget,
  FiTrendingUp,
  FiZap,
  FiActivity,
  FiChevronLeft,
  FiChevronRight,
  FiChevronsLeft,
  FiChevronsRight,
  FiChevronDown,
  FiChevronUp,
  FiAward,
  FiUsers,
} from 'react-icons/fi';
import { replaysApi } from '../api/endpoints';
import EmptyState from '../components/EmptyState';
import { MatchCardSkeleton } from '../components/LoadingState';
import { formatDuration, formatDateTime, getRaceColor } from '../utils/formatting';
import {
  generateMatchOverview,
  generateMVPCommentary,
  generatePlayerHighlight,
  generateUpsetCommentary,
} from '../utils/esportsCommentary';
import type { MatchWithPlayers, MatchPlayerSummary, MatchListWithPlayersResponse } from '../types/api';

// Player highlight card component
const PlayerHighlightCard: React.FC<{
  player: MatchPlayerSummary;
  matchId: number;
  isMVP: boolean;
}> = ({ player, matchId, isMVP }) => {
  const bgColor = useColorModeValue(
    player.won ? 'green.50' : 'red.50',
    player.won ? 'rgba(72, 187, 120, 0.1)' : 'rgba(245, 101, 101, 0.1)'
  );
  const borderColor = player.won ? 'green.400' : 'red.400';

  // Generate unique commentary for this player
  const commentary = generatePlayerHighlight(
    {
      name: player.player_name,
      won: player.won,
      damageDealt: player.damage_dealt || 0,
      damageRatio: player.damage_ratio || 1,
      impactScore: player.impact_score || undefined,
    },
    matchId
  );

  return (
    <Box
      bg={bgColor}
      p={3}
      borderRadius="md"
      border="1px solid"
      borderColor={borderColor}
      position="relative"
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
          <Text fontSize="xs" color={player.mmr_change >= 0 ? 'green.400' : 'red.400'}>
            {player.mmr_change >= 0 ? '+' : ''}{Math.round(player.mmr_change)} MMR
          </Text>
        </VStack>
      </HStack>

      {/* Stats row */}
      {player.damage_dealt && (
        <HStack spacing={4} mb={2} fontSize="xs" color="gray.500">
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

      {/* Commentary */}
      <Text fontSize="xs" fontStyle="italic" color="gray.400" noOfLines={2}>
        {commentary}
      </Text>
    </Box>
  );
};

// Match card component with expandable player details
const MatchCard: React.FC<{
  match: MatchWithPlayers;
  onNavigate: (id: number) => void;
}> = ({ match, onNavigate }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const team1Players = match.players.filter((p) => p.team_number === 1);
  const team2Players = match.players.filter((p) => p.team_number === 2);

  const hasWinProb = match.predicted_team1_win_prob && match.predicted_team2_win_prob;
  const team1Prob = match.predicted_team1_win_prob || 0.5;
  const team2Prob = match.predicted_team2_win_prob || 0.5;

  // Generate unique match commentary
  const matchOverview = generateMatchOverview(
    match.duration_seconds,
    match.map_name,
    match.game_mode,
    match.id
  );

  // Check for upset
  const winnerProb = match.winner_team === 1 ? team1Prob : team2Prob;
  const upsetCommentary = generateUpsetCommentary(winnerProb, match.id);

  // MVP commentary
  const mvpCommentary = match.mvp_player_name && match.total_damage
    ? generateMVPCommentary(match.mvp_player_name, 75, match.id)
    : null;

  return (
    <Card
      bg="space.800"
      border="3px solid"
      borderColor="space.700"
      boxShadow="3px 3px 0 space.900"
      position="relative"
      overflow="hidden"
      transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
      _hover={{
        borderColor: 'brand.500',
        transform: 'translateY(-2px)',
      }}
    >
      <CardBody>
        {/* Main match info - clickable */}
        <Box
          cursor="pointer"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <Grid
            templateColumns={{ base: '1fr', md: 'auto 1fr auto' }}
            gap={4}
            alignItems="center"
          >
            {/* Left: Match icon with winner indicator */}
            <Box
              bg={`linear-gradient(135deg, ${match.winner_team === 1 ? 'rgba(72, 187, 120, 0.3)' : 'rgba(0, 212, 255, 0.2)'}, ${match.winner_team === 2 ? 'rgba(255, 179, 0, 0.3)' : 'rgba(255, 179, 0, 0.1)'})`}
              p={3}
              borderRadius="lg"
              border="2px solid"
              borderColor={match.winner_team === 1 ? 'green.400' : 'orange.400'}
              textAlign="center"
            >
              <Text fontSize="xs" color="gray.400" fontFamily="heading">
                Winner
              </Text>
              <Text fontSize="lg" fontWeight="bold" color={match.winner_team === 1 ? 'green.400' : 'orange.400'}>
                Team {match.winner_team}
              </Text>
            </Box>

            {/* Middle: Match details + commentary */}
            <VStack align="start" spacing={2} flex={1}>
              <HStack spacing={3} flexWrap="wrap">
                <Heading
                  size="md"
                  fontFamily="heading"
                  letterSpacing="wide"
                >
                  {match.map_name}
                </Heading>
                <Badge
                  colorScheme="blue"
                  fontSize="sm"
                  px={2}
                  fontFamily="heading"
                >
                  {match.game_mode}
                </Badge>
                {upsetCommentary && (
                  <Badge colorScheme="purple" fontSize="sm" px={2}>
                    🤯 UPSET
                  </Badge>
                )}
              </HStack>

              {/* Esports Commentary */}
              <Text
                fontSize="sm"
                fontWeight="medium"
                color="brand.300"
                fontFamily="heading"
              >
                {matchOverview}
              </Text>

              <HStack spacing={4} fontSize="xs" color="gray.500" fontFamily="heading">
                <Text>{formatDateTime(match.played_at)}</Text>
                <Text>•</Text>
                <HStack>
                  <Icon as={FiZap} />
                  <Text>{formatDuration(match.duration_seconds)}</Text>
                </HStack>
                {match.total_damage && (
                  <>
                    <Text>•</Text>
                    <HStack>
                      <Icon as={FiTarget} />
                      <Text>{match.total_damage.toLocaleString()} total damage</Text>
                    </HStack>
                  </>
                )}
              </HStack>

              {/* Win Probability Bar */}
              {hasWinProb && (
                <Box w="full" mt={1}>
                  <HStack justify="space-between" mb={1} fontSize="xs" fontFamily="heading">
                    <HStack>
                      <Badge
                        bg={match.winner_team === 1 ? 'green.500' : 'gray.600'}
                        color="white"
                        fontSize="xs"
                      >
                        T1: {(team1Prob * 100).toFixed(0)}%
                      </Badge>
                    </HStack>
                    <HStack>
                      <Badge
                        bg={match.winner_team === 2 ? 'green.500' : 'gray.600'}
                        color="white"
                        fontSize="xs"
                      >
                        T2: {(team2Prob * 100).toFixed(0)}%
                      </Badge>
                    </HStack>
                  </HStack>
                  <HStack spacing={1}>
                    <Box flex={team1Prob}>
                      <Progress
                        value={100}
                        size="sm"
                        colorScheme={match.winner_team === 1 ? 'green' : 'cyan'}
                        borderRadius="md"
                        bg="gray.700"
                      />
                    </Box>
                    <Box flex={team2Prob}>
                      <Progress
                        value={100}
                        size="sm"
                        colorScheme={match.winner_team === 2 ? 'green' : 'orange'}
                        borderRadius="md"
                        bg="gray.700"
                      />
                    </Box>
                  </HStack>
                </Box>
              )}
            </VStack>

            {/* Right: Expand/Action buttons */}
            <VStack spacing={2}>
              <Button
                size="sm"
                variant="primary"
                rightIcon={<Icon as={FiTarget} />}
                fontFamily="heading"
                onClick={(e) => {
                  e.stopPropagation();
                  onNavigate(match.id);
                }}
              >
                Details
              </Button>
              <IconButton
                aria-label={isExpanded ? 'Collapse' : 'Expand'}
                icon={isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                size="sm"
                variant="ghost"
                colorScheme="cyan"
              />
            </VStack>
          </Grid>
        </Box>

        {/* Expandable player highlights */}
        <Collapse in={isExpanded} animateOpacity>
          <Divider my={4} borderColor="whiteAlpha.200" />

          {/* MVP Highlight */}
          {mvpCommentary && (
            <Box
              bg="rgba(255, 215, 0, 0.1)"
              p={3}
              borderRadius="md"
              border="1px solid"
              borderColor="yellow.500"
              mb={4}
            >
              <Text fontSize="sm" fontWeight="bold" color="yellow.400">
                {mvpCommentary}
              </Text>
            </Box>
          )}

          <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={4}>
            {/* Team 1 */}
            <Box>
              <HStack mb={2}>
                <Icon as={FiUsers} color="cyan.400" />
                <Text
                  fontFamily="heading"
                  fontSize="sm"
                  color={match.winner_team === 1 ? 'green.400' : 'gray.400'}
                >
                  Team 1 {match.winner_team === 1 && '🏆'}
                </Text>
              </HStack>
              <VStack spacing={2} align="stretch">
                {team1Players.map((player) => (
                  <PlayerHighlightCard
                    key={player.player_id}
                    player={player}
                    matchId={match.id}
                    isMVP={player.player_id === match.mvp_player_id}
                  />
                ))}
              </VStack>
            </Box>

            {/* Team 2 */}
            <Box>
              <HStack mb={2}>
                <Icon as={FiUsers} color="orange.400" />
                <Text
                  fontFamily="heading"
                  fontSize="sm"
                  color={match.winner_team === 2 ? 'green.400' : 'gray.400'}
                >
                  Team 2 {match.winner_team === 2 && '🏆'}
                </Text>
              </HStack>
              <VStack spacing={2} align="stretch">
                {team2Players.map((player) => (
                  <PlayerHighlightCard
                    key={player.player_id}
                    player={player}
                    matchId={match.id}
                    isMVP={player.player_id === match.mvp_player_id}
                  />
                ))}
              </VStack>
            </Box>
          </Grid>
        </Collapse>
      </CardBody>
    </Card>
  );
};

const MatchHistory: React.FC = () => {
  const navigate = useNavigate();

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const matchesPerPage = 15;

  // Fetch matches with player data using keepPreviousData for smooth pagination
  const { data: matchesData, isLoading, isFetching } = useQuery<MatchListWithPlayersResponse>({
    queryKey: ['matches-with-players', currentPage],
    queryFn: async () => {
      const offset = (currentPage - 1) * matchesPerPage;
      const response = await replaysApi.getMatchesWithPlayers(matchesPerPage, offset);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });

  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_count || 0;
  const totalPages = Math.ceil(totalMatches / matchesPerPage);

  const handlePageChange = (newPage: number): void => {
    setCurrentPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigate = (matchId: number): void => {
    navigate(`/history/${matchId}`);
  };

  if (isLoading) {
    return (
      <Box bg="space.900">
        <Container maxW="container.xl" py={8}>
          <VStack spacing={8} align="stretch">
            <Heading>Match History</Heading>
            <VStack spacing={4}>
              {Array.from({ length: 10 }).map((_, idx) => (
                <MatchCardSkeleton key={idx} />
              ))}
            </VStack>
          </VStack>
        </Container>
      </Box>
    );
  }

  if (matches.length === 0) {
    return (
      <Box bg="space.900">
        <Container maxW="container.xl" py={8}>
          <VStack spacing={8} align="stretch">
            <Heading>Match History</Heading>
            <EmptyState
              variant="stats"
              title="No Matches Yet"
              description="Upload some replay files to start tracking your game history."
              onAction={() => navigate('/upload')}
            />
          </VStack>
        </Container>
      </Box>
    );
  }

  return (
    <Box position="relative" bg="space.900">
      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Header Section */}
          <Box position="relative">
            <HStack justify="space-between" align="start" mb={2}>
              <VStack align="start" spacing={1}>
                <HStack spacing={3}>
                  <Icon as={FiActivity} boxSize={8} color="brand.400" />
                  <Heading
                    size="2xl"
                    fontFamily="heading"
                    letterSpacing="wider"
                    color="brand.400"
                  >
                    Match History
                  </Heading>
                </HStack>
                <Text
                  color="gray.500"
                  fontFamily="heading"
                  letterSpacing="wide"
                  fontSize="sm"
                >
                  {totalMatches} matches recorded{totalPages > 1 ? ` • Page ${currentPage}/${totalPages}` : ''}
                  {isFetching && !isLoading && ' • Updating...'}
                </Text>
              </VStack>

              {/* Stats badges */}
              <HStack spacing={3}>
                <Badge
                  bg="brand.500"
                  color="gray.900"
                  px={4}
                  py={2}
                  borderRadius="lg"
                  fontSize="lg"
                  fontFamily="heading"
                  boxShadow="3px 3px 0 space.900"
                >
<Icon as={FiTrendingUp} mr={2} />
                    Active
                  </Badge>
              </HStack>
            </HStack>
          </Box>

          {/* Match List */}
          <VStack spacing={4} align="stretch">
            {matches.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                onNavigate={handleNavigate}
              />
            ))}
          </VStack>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <Box mt={8}>
              <VStack spacing={4}>
                {/* Page info */}
                <Text
                  color="gray.500"
                  fontFamily="heading"
                  fontSize="sm"
                  letterSpacing="wide"
                >
                  Page {currentPage} of {totalPages} • Showing {matches.length} of {totalMatches} matches
                </Text>

                {/* Pagination buttons */}
                <HStack spacing={2}>
                  <IconButton
                    icon={<FiChevronsLeft />}
                    onClick={() => handlePageChange(1)}
                    isDisabled={currentPage === 1}
                    aria-label="First page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />
                  <IconButton
                    icon={<FiChevronLeft />}
                    onClick={() => handlePageChange(currentPage - 1)}
                    isDisabled={currentPage === 1}
                    aria-label="Previous page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />

                  {/* Page number buttons */}
                  <ButtonGroup spacing={2}>
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      // Show pages around current page
                      let pageNum: number;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }

                      return (
                        <Button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          variant={currentPage === pageNum ? 'solid' : 'ghost'}
                          colorScheme="cyan"
                          size="lg"
                          fontFamily="heading"
                          minW="50px"
                          bg={currentPage === pageNum ? 'brand.500' : undefined}
                          color={currentPage === pageNum ? 'gray.900' : undefined}
                          _hover={{
                            bg: currentPage === pageNum ? 'brand.400' : 'whiteAlpha.200',
                          }}
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                  </ButtonGroup>

                  <IconButton
                    icon={<FiChevronRight />}
                    onClick={() => handlePageChange(currentPage + 1)}
                    isDisabled={currentPage === totalPages}
                    aria-label="Next page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />
                  <IconButton
                    icon={<FiChevronsRight />}
                    onClick={() => handlePageChange(totalPages)}
                    isDisabled={currentPage === totalPages}
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
