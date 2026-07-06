/**
 * Player Detail Page - Friend Squad Edition
 * Shows comprehensive player information with comic-book styling
 */
import { useState } from 'react';
import {
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Box,
  Badge,
  Button,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Alert,
  AlertIcon,
  Icon,
  Grid,
  GridItem,
  Progress,
  ButtonGroup,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  SimpleGrid,
  Flex,
  Tooltip,
  Link,
} from '@chakra-ui/react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { 
  FiArrowLeft, 
  FiTrendingUp, 
  FiActivity, 
  FiAward, 
  FiTarget, 
  FiStar,
  FiZap,
  FiClock,
  FiTrendingDown
} from 'react-icons/fi';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { playersApi } from '../api/endpoints';
import { achievementsApi } from '../api/achievements';
import LoadingState from '../components/LoadingState';
import RankBadge from '../components/RankBadge';
import AchievementBadge from '../components/AchievementBadge';
import { formatWinRate, formatDateOnly, formatDateTime } from '../utils/formatting';
import type { RecentMatch, PlayerDetail as PlayerDetailType } from '@/types/api';

// Design tokens
const cardBg = 'space.800';
const borderColor = 'space.900';
const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';

/**
 * Compact "D MMM" label for the trajectory chart x-axis. Mirrors the AEST
 * handling in utils/formatting (API timestamps are naive UTC), kept local
 * to avoid widening the shared util surface for a chart-only format.
 */
const formatAxisDate = (value: string): string => {
  if (!value) return '';
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(value);
  const date = new Date(hasTz ? value : `${value}Z`);
  return date.toLocaleDateString('en-AU', {
    timeZone: 'Australia/Sydney',
    month: 'short',
    day: 'numeric',
  });
};

// Extended player detail type with optional race_stats
interface PlayerDetailWithRaceStats extends Omit<PlayerDetailType, 'recent_matches'> {
  recent_matches: RecentMatch[];
  race_stats?: Record<string, number>;
}

const PlayerDetail: React.FC = () => {
  const { playerId } = useParams<{ playerId: string }>();
  const navigate = useNavigate();
  const [matchesLimit, setMatchesLimit] = useState<number>(10);
  const [matchesOffset, setMatchesOffset] = useState<number>(0);

  // Fetch player details
  const { data: playerData, isLoading, isFetching } = useQuery<PlayerDetailWithRaceStats>({
    queryKey: ['player', playerId, matchesLimit, matchesOffset],
    queryFn: async () => {
      const response = await playersApi.getById(parseInt(playerId!, 10), matchesLimit, matchesOffset);
      return response.data as PlayerDetailWithRaceStats;
    },
    placeholderData: keepPreviousData,
  });

  // Fetch player achievements
  const { data: achievementData } = useQuery({
    queryKey: ['player-achievements', playerId],
    queryFn: async () => {
      const response = await achievementsApi.getPlayerAchievements(parseInt(playerId!, 10), true);
      return response.data;
    },
    enabled: !!playerId,
  });

  // Fetch player MMR history
  const { data: historyData } = useQuery({
    queryKey: ['player-history', playerId],
    queryFn: async () => {
      const response = await playersApi.getHistory(parseInt(playerId!, 10));
      return response.data;
    },
    enabled: !!playerId,
  });

  // Only show full loading state on initial load, not pagination
  if (isLoading && !playerData) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading player details..." />
      </Container>
    );
  }

  if (!playerData) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert status="error">
          <AlertIcon />
          Player not found
        </Alert>
      </Container>
    );
  }

  const totalGames = playerData.total_games;
  const currentPage = Math.floor(matchesOffset / matchesLimit) + 1;
  const totalPages = Math.ceil(totalGames / matchesLimit);

  const handlePageChange = (newOffset: number) => {
    setMatchesOffset(Math.max(0, Math.min(newOffset, (totalPages - 1) * matchesLimit)));
  };

  const handleLimitChange = (newLimit: number) => {
    setMatchesLimit(newLimit);
    setMatchesOffset(0);
  };

  const getRaceColor = (race: string): string => {
    switch (race) {
      case 'Terran': return 'terran';
      case 'Protoss': return 'protoss';
      case 'Zerg': return 'zerg';
      default: return 'gray';
    }
  };

  const getFavoriteRace = (): string => {
    const races = playerData.race_stats ?? {};
    const values = Object.values(races);
    if (values.length === 0) return 'Unknown';
    const maxGames = Math.max(...values);
    if (maxGames === 0) return 'Unknown';
    return Object.keys(races).find(race => races[race] === maxGames) || 'Unknown';
  };

  const favoriteRace = getFavoriteRace();

  return (
    <Box minH="100vh">
      <Container maxW="container.xl" py={8}>
        <VStack spacing={6} align="stretch">
          {/* Back Button */}
          <Button
            leftIcon={<FiArrowLeft />}
            variant="ghost"
            alignSelf="flex-start"
            onClick={() => navigate('/players')}
            fontFamily="heading"
            color="gray.400"
            _hover={{ color: 'brand.400' }}
          >
            Back to Players
          </Button>

          {/* Player Header Card */}
          <Box
            bg={cardBg}
            borderRadius="xl"
            border="3px solid"
            borderColor={borderColor}
            boxShadow={brandShadow}
            p={6}
          >
            <HStack justify="space-between" align="start">
              <VStack align="start" spacing={2}>
                <HStack spacing={3}>
                  <Heading size="xl" fontFamily="heading" letterSpacing="wide" color="gray.100">
                    {playerData.name}
                  </Heading>
                  <Badge
                    bg={`${getRaceColor(favoriteRace)}.500`}
                    color="white"
                    fontSize="md"
                    px={3}
                    py={1}
                    borderRadius="md"
                  >
                    {favoriteRace}
                  </Badge>
                  {playerData.is_core_player && (
                    <Tooltip
                      label="A regular member of the clubhouse ladder — counts toward rankings, the champion, and team balancing (as opposed to a one-off guest)."
                      hasArrow
                      placement="top"
                    >
                      <Badge bg="brand.500" color="white" fontSize="sm" px={2} py={1} borderRadius="md" cursor="help">
                        Core
                      </Badge>
                    </Tooltip>
                  )}
                  {playerData.is_ai && (
                    <Badge bg="purple.500" color="white" fontSize="sm" px={2} py={1} borderRadius="md">
                      AI
                    </Badge>
                  )}
                </HStack>
                {playerData.last_played && (
                  <Text color="gray.500" fontSize="sm">
                    Last played: {formatDateOnly(playerData.last_played)}
                  </Text>
                )}
              </VStack>

              <VStack align="end" spacing={3}>
                <RankBadge
                  mmr={playerData.mmr}
                  size="lg"
                  showMMR={true}
                  showIcon={true}
                />
              </VStack>
            </HStack>
          </Box>

          {/* MMR History Chart */}
          <Box bg={cardBg} p={6} borderRadius="2xl" border="3px solid" borderColor={borderColor} boxShadow={brandShadow} w="100%">
            <HStack justify="space-between" mb={6}>
              <VStack align="start" spacing={0}>
                <Heading size="md" fontFamily="heading" color="gray.100" textTransform="uppercase" letterSpacing="widest">
                  Performance Trajectory
                </Heading>
                <Text fontSize="xs" color="gray.500">MMR over last 50 matches — same rating as the rank badge</Text>
              </VStack>
              {historyData?.history && historyData.history.length >= 2 && (
                <Badge colorScheme={(historyData.history[historyData.history.length-1].mmr >= historyData.history[0].mmr) ? 'green' : 'red'} fontSize="xs" px={3} py={1}>
                  {(historyData.history[historyData.history.length-1].mmr - historyData.history[0].mmr) >= 0 ? '+' : ''}
                  {Math.round(historyData.history[historyData.history.length-1].mmr - historyData.history[0].mmr)} Total Swing
                </Badge>
              )}
            </HStack>
            
            <Box h="300px" w="100%">
              {historyData?.history && historyData.history.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historyData.history}>
                    <defs>
                      <linearGradient id="colorMmr" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00FF88" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#00FF88" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" vertical={false} />
                    <XAxis
                      dataKey="played_at"
                      tickFormatter={formatAxisDate}
                      stroke="#718096"
                      fontSize={11}
                      minTickGap={48}
                      interval="preserveStartEnd"
                      tickLine={false}
                      axisLine={false}
                      dy={6}
                    />
                    <YAxis
                      domain={['dataMin - 20', 'dataMax + 20']}
                      stroke="#718096"
                      fontSize={12}
                      tickFormatter={(value) => `${value}`}
                    />
                    <RechartsTooltip 
                      contentStyle={{ backgroundColor: '#1A202C', borderColor: '#2D3748', borderRadius: '8px' }}
                      itemStyle={{ color: '#00FF88' }}
                      labelStyle={{ color: '#A0AEC0' }}
                      formatter={(value: any) => [Math.round(value), 'MMR']}
                      labelFormatter={(label, payload) => {
                        if (payload && payload[0]) {
                          return `Match #${payload[0].payload.match_id} on ${payload[0].payload.map_name}`;
                        }
                        return label;
                      }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="mmr" 
                      stroke="#00FF88" 
                      strokeWidth={3}
                      fillOpacity={1} 
                      fill="url(#colorMmr)" 
                      animationDuration={1500}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <Flex h="100%" align="center" justify="center" direction="column">
                  <Icon as={FiActivity} boxSize={8} color="gray.700" mb={2} />
                  <Text color="gray.600">Insufficient data for trajectory mapping</Text>
                </Flex>
              )}
            </Box>
          </Box>


          {/* Statistics Grid */}

          <Box>
            <Flex justify="space-between" align="center" mb={4} gap={3} flexWrap="wrap">
              <Heading size="md" fontFamily="heading" color="gray.300">
                Player Stats
              </Heading>
              <Link
                onClick={() => navigate('/rating-system')}
                fontSize="sm"
                fontFamily="heading"
                fontWeight="700"
                color="accent.400"
                _hover={{ color: 'accent.300', textDecoration: 'none' }}
              >
                How the rating works →
              </Link>
            </Flex>
            <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }} gap={4}>
              <GridItem>
                <Box
                  bg={cardBg}
                  borderRadius="xl"
                  border="3px solid"
                  borderColor={borderColor}
                  boxShadow={brandShadow}
                  p={5}
                  h="100%"
                >
                  <Stat>
                    <StatLabel color="gray.400" fontFamily="heading" letterSpacing="wide">
                      <Icon as={FiActivity} mr={2} color="brand.400" />
                      Total Games
                    </StatLabel>
                    <StatNumber fontSize="3xl" color="brand.400" fontWeight="bold">
                      {playerData.total_games}
                    </StatNumber>
                    <StatHelpText color="gray.500">&nbsp;</StatHelpText>
                  </Stat>
                </Box>
              </GridItem>

              <GridItem>
                <Box
                  bg={cardBg}
                  borderRadius="xl"
                  border="3px solid"
                  borderColor={borderColor}
                  boxShadow={brandShadow}
                  p={5}
                  h="100%"
                >
                  <Stat>
                    <StatLabel color="gray.400" fontFamily="heading" letterSpacing="wide">
                      <Icon as={FiAward} mr={2} color="accent.400" />
                      Win Rate
                    </StatLabel>
                    <StatNumber fontSize="3xl" color={playerData.win_rate >= 0.5 ? 'green.400' : 'red.400'} fontWeight="bold">
                      {formatWinRate(playerData.win_rate)}
                    </StatNumber>
                    <StatHelpText color="gray.500">
                      {playerData.wins}W - {playerData.losses}L
                    </StatHelpText>
                  </Stat>
                </Box>
              </GridItem>

              <GridItem>
                <Box
                  bg={cardBg}
                  borderRadius="xl"
                  border="3px solid"
                  borderColor={borderColor}
                  boxShadow={brandShadow}
                  p={5}
                  h="100%"
                >
                  <Stat>
                    <StatLabel color="gray.400" fontFamily="heading" letterSpacing="wide">
                      <Icon as={FiTarget} mr={2} color="shield.400" />
                      Skill estimate
                    </StatLabel>
                    <StatNumber fontSize="3xl" color="shield.400" fontWeight="bold">
                      {playerData.mu.toFixed(1)}
                    </StatNumber>
                    <StatHelpText color="gray.500" fontSize="xs">
                      The system's best guess at true skill
                    </StatHelpText>
                  </Stat>
                </Box>
              </GridItem>

              <GridItem>
                <Box
                  bg={cardBg}
                  borderRadius="xl"
                  border="3px solid"
                  borderColor={borderColor}
                  boxShadow={brandShadow}
                  p={5}
                  h="100%"
                >
                  <Stat>
                    <StatLabel color="gray.400" fontFamily="heading" letterSpacing="wide">
                      <Icon as={FiTrendingUp} mr={2} color="purple.400" />
                      Rating confidence
                    </StatLabel>
                    <StatNumber fontSize="3xl" color="purple.400" fontWeight="bold">
                      {playerData.sigma.toFixed(2)}
                    </StatNumber>
                    <StatHelpText color="gray.500" fontSize="xs">
                      How settled this rating is — lower means more certain
                    </StatHelpText>
                  </Stat>
                </Box>
              </GridItem>
            </Grid>
          </Box>

          {/* Race Statistics */}
          <Box
            bg={cardBg}
            borderRadius="xl"
            border="3px solid"
            borderColor={borderColor}
            boxShadow={brandShadow}
            p={6}
          >
            <Heading size="md" fontFamily="heading" color="gray.300" mb={6}>
              Performance &amp; Career
            </Heading>
            
            <Tabs variant="unstyled">
              <TabList mb={4} gap={2}>
                <Tab 
                  bg="space.900" 
                  color="gray.500" 
                  borderRadius="lg" 
                  px={6} 
                  py={2}
                  fontFamily="heading"
                  _selected={{ bg: 'brand.500', color: 'white', boxShadow: '3px 3px 0 var(--chakra-colors-space-900)' }}
                  _hover={{ bg: 'space.700' }}
                >
                  <Icon as={FiZap} mr={2} /> Race Stats
                </Tab>
                <Tab 
                  bg="space.900" 
                  color="gray.500" 
                  borderRadius="lg" 
                  px={6} 
                  py={2}
                  fontFamily="heading"
                  _selected={{ bg: 'brand.500', color: 'white', boxShadow: '3px 3px 0 var(--chakra-colors-space-900)' }}
                  _hover={{ bg: 'space.700' }}
                >
                  <Icon as={FiAward} mr={2} /> Trophy Case
                </Tab>
              </TabList>
              
              <TabPanels>
                <TabPanel p={0} pt={2}>
                  <Grid templateColumns={{ base: '1fr', md: 'repeat(4, 1fr)' }} gap={4}>
                    {Object.entries(playerData.race_stats ?? {}).map(([race, games]) => (
                      <GridItem key={race}>
                        <VStack align="stretch" spacing={2}>
                          <HStack justify="space-between">
                            <Badge
                              bg={`${getRaceColor(race)}.500`}
                              color="white"
                              px={2}
                              py={1}
                              borderRadius="md"
                            >
                              {race}
                            </Badge>
                            <Text fontWeight="bold" color="gray.300" fontFamily="mono">
                              {games} games
                            </Text>
                          </HStack>
                          <Progress
                            value={playerData.total_games > 0 ? (games / playerData.total_games) * 100 : 0}
                            colorScheme={getRaceColor(race)}
                            size="sm"
                            borderRadius="full"
                            bg="space.900"
                            sx={{ '& > div': { bg: `${getRaceColor(race)}.500` } }}
                          />
                        </VStack>
                      </GridItem>
                    ))}
                  </Grid>
                </TabPanel>
                
                <TabPanel p={0} pt={2}>
                  {!achievementData?.awarded?.length ? (
                    <Box py={8} textAlign="center" bg="space.900" borderRadius="xl" border="2px dashed" borderColor="space.700">
                      <Icon as={FiAward} boxSize={10} color="gray.700" mb={2} />
                      <Text color="gray.600">No trophies earned yet. Start playing to unlock achievements!</Text>
                    </Box>
                  ) : (
                    <VStack align="stretch" spacing={6}>
                      <HStack spacing={4}>
                         <Stat bg="space.900" p={3} borderRadius="lg" border="1px solid" borderColor="whiteAlpha.100">
                           <StatLabel fontSize="xs" color="gray.500">Points</StatLabel>
                           <StatNumber fontSize="xl" color="brand.400">{achievementData.total_points}</StatNumber>
                         </Stat>
                         <Stat bg="space.900" p={3} borderRadius="lg" border="1px solid" borderColor="whiteAlpha.100">
                           <StatLabel fontSize="xs" color="gray.500">Unlocked</StatLabel>
                           <StatNumber fontSize="xl" color="accent.400">{achievementData?.awarded?.length || 0}</StatNumber>
                         </Stat>
                      </HStack>
                      
                      <SimpleGrid columns={{ base: 2, sm: 3, md: 4, lg: 6 }} spacing={4}>
                        {achievementData.awarded.map((awarded) => (
                          <Box key={awarded.code} display="flex" justifyContent="center">
                            <AchievementBadge
                              code={awarded.code}
                              name={awarded.name}
                              description={awarded.description}
                              flavor_text={awarded.flavor_text}
                              icon={awarded.icon || '🎖️'}
                              rarity={awarded.rarity}
                              category={awarded.category}
                              points={awarded.points}
                              earned
                              earned_at={awarded.earned_at}
                              size="sm"
                            />
                          </Box>
                        ))}
                      </SimpleGrid>
                    </VStack>
                  )}
                </TabPanel>
              </TabPanels>
            </Tabs>
          </Box>

          {/* Recent Matches */}
          <Box
            bg={cardBg}
            borderRadius="xl"
            border="3px solid"
            borderColor={borderColor}
            boxShadow={brandShadow}
            p={6}
          >
            <VStack align="stretch" spacing={4}>
              <HStack justify="space-between" align="center">
                <Heading size="md" fontFamily="heading" color="gray.300">
                  Recent Matches
                  {playerData.recent_matches && playerData.recent_matches.length > 0 && (
                    <Badge ml={3} bg="space.700" color="brand.400" fontSize="sm" px={2} py={1} borderRadius="md">
                      {matchesOffset + 1}-{matchesOffset + playerData.recent_matches.length} of {totalGames}
                    </Badge>
                  )}
                </Heading>
                <HStack spacing={4}>
                  <Text fontSize="sm" color="gray.500">Page Size:</Text>
                  <ButtonGroup size="sm" variant="outline" isAttached>
                    {[10, 25, 50].map(limit => (
                      <Button
                        key={limit}
                        onClick={() => handleLimitChange(limit)}
                        bg={matchesLimit === limit ? 'brand.500' : 'transparent'}
                        color={matchesLimit === limit ? 'white' : 'gray.400'}
                        borderColor="space.600"
                        _hover={{ bg: matchesLimit === limit ? 'brand.600' : 'space.700' }}
                      >
                        {limit}
                      </Button>
                    ))}
                  </ButtonGroup>
                </HStack>
              </HStack>

              {playerData.recent_matches && playerData.recent_matches.length > 0 ? (
                <>
                  <TableContainer>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th color="gray.500" borderColor="space.700">Date</Th>
                          <Th color="gray.500" borderColor="space.700">Map</Th>
                          <Th color="gray.500" borderColor="space.700">Mode</Th>
                          <Th color="gray.500" borderColor="space.700">Race</Th>
                          <Th color="gray.500" borderColor="space.700">Result</Th>
                          <Th color="gray.500" borderColor="space.700" isNumeric>Before</Th>
                          <Th color="gray.500" borderColor="space.700" isNumeric>After</Th>
                          <Th color="gray.500" borderColor="space.700" isNumeric>Change</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {playerData.recent_matches.map((match: RecentMatch) => (
                          <Tr
                            key={match.match_id}
                            bg={match.won ? 'rgba(72, 187, 120, 0.1)' : 'rgba(245, 101, 101, 0.1)'}
                            _hover={{ bg: match.won ? 'rgba(72, 187, 120, 0.2)' : 'rgba(245, 101, 101, 0.2)', cursor: 'pointer' }}
                            onClick={() => navigate(`/history/${match.match_id}`)}
                            transition="all 0.2s"
                          >
                            <Td borderColor="space.700">
                              <Text fontSize="xs" color="gray.400">
                                {formatDateTime(match.played_at)}
                              </Text>
                            </Td>
                            <Td borderColor="space.700" color="gray.300">{match.map_name}</Td>
                            <Td borderColor="space.700">
                              <Badge size="sm" bg="space.700" color="gray.300">{match.game_mode}</Badge>
                            </Td>
                            <Td borderColor="space.700">
                              <Badge bg={`${getRaceColor(match.race)}.500`} color="white">
                                {match.race}
                              </Badge>
                            </Td>
                            <Td borderColor="space.700">
                              <Badge bg={match.won ? 'green.500' : 'red.500'} color="white">
                                {match.won ? 'Win' : 'Loss'}
                              </Badge>
                            </Td>
                            <Td borderColor="space.700" isNumeric color="gray.400">{Math.round(match.mmr_before)}</Td>
                            <Td borderColor="space.700" isNumeric color="gray.400">{Math.round(match.mmr_after)}</Td>
                            <Td borderColor="space.700" isNumeric>
                              <Text
                                color={match.mmr_change >= 0 ? 'green.400' : 'red.400'}
                                fontWeight="bold"
                                fontFamily="mono"
                              >
                                {match.mmr_change >= 0 ? '+' : ''}
                                {Math.round(match.mmr_change)}
                              </Text>
                            </Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </TableContainer>

                  {/* Pagination Controls */}
                  <HStack justify="center" pt={4}>
                    <ButtonGroup size="sm" variant="outline">
                      <Button
                        onClick={() => handlePageChange(0)}
                        isDisabled={matchesOffset === 0}
                        borderColor="space.600"
                        color="gray.400"
                        _hover={{ bg: 'space.700' }}
                      >
                        First
                      </Button>
                      <Button
                        onClick={() => handlePageChange(matchesOffset - matchesLimit)}
                        isDisabled={matchesOffset === 0}
                        borderColor="space.600"
                        color="gray.400"
                        _hover={{ bg: 'space.700' }}
                      >
                        Previous
                      </Button>
                      <Button variant="ghost" isDisabled color="gray.500">
                        Page {currentPage} of {totalPages}
                      </Button>
                      <Button
                        onClick={() => handlePageChange(matchesOffset + matchesLimit)}
                        isDisabled={currentPage >= totalPages}
                        borderColor="space.600"
                        color="gray.400"
                        _hover={{ bg: 'space.700' }}
                      >
                        Next
                      </Button>
                      <Button
                        onClick={() => handlePageChange((totalPages - 1) * matchesLimit)}
                        isDisabled={currentPage >= totalPages}
                        borderColor="space.600"
                        color="gray.400"
                        _hover={{ bg: 'space.700' }}
                      >
                        Last
                      </Button>
                    </ButtonGroup>
                  </HStack>
                </>
              ) : (
                <Box
                  bg="space.900"
                  borderRadius="lg"
                  p={6}
                  textAlign="center"
                >
                  <Text color="gray.500">No matches found for this page</Text>
                </Box>
              )}
            </VStack>
          </Box>
        </VStack>
      </Container>
    </Box>
  );
};

export default PlayerDetail;
