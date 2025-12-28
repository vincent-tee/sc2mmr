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
  Tooltip,
  SimpleGrid,
  Flex,
  Circle,
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
  FiClock
} from 'react-icons/fi';
import { playersApi } from '../api/endpoints';
import { achievementsApi } from '../api/achievements';
import LoadingState from '../components/LoadingState';
import RankBadge from '../components/RankBadge';
import RaceBackground from '../components/RaceBackground';
import { formatWinRate, formatDateOnly } from '../utils/formatting';
import type { RecentMatch, PlayerDetail as PlayerDetailType } from '@/types/api';
import { RARITY_COLORS, getRarityLabel } from '../types/achievements';

// Design tokens
const cardBg = 'space.800';
const borderColor = 'space.900';
const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';

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
    <RaceBackground
      race={favoriteRace.toLowerCase()}
      intensity="subtle"
      showRaceIcon={true}
      iconPosition="center"
      iconSize={200}
      iconOpacity={0.05}
      hoverGlow={false}
      borderStyle="none"
      showPattern={true}
      minH="100vh"
    >
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
                    <Badge bg="brand.500" color="white" fontSize="sm" px={2} py={1} borderRadius="md">
                      Core
                    </Badge>
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
                  mmr={playerData.recency_weighted_mmr || playerData.mmr}
                  size="lg"
                  showMMR={true}
                  showIcon={true}
                />
                {playerData.recency_weighted_mmr && playerData.mmr !== playerData.recency_weighted_mmr && (
                  <Text fontSize="sm" color="gray.500">
                    Base MMR: {Math.round(playerData.mmr)}
                  </Text>
                )}
              </VStack>
            </HStack>
          </Box>

          {/* Statistics Grid */}
          <Box>
            <Heading size="md" fontFamily="heading" color="gray.300" mb={4}>
              <Text as="span" className="emoji-font">📊</Text> Player Stats
            </Heading>
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
                      Skill (mu)
                    </StatLabel>
                    <StatNumber fontSize="3xl" color="shield.400" fontWeight="bold">
                      {playerData.mu.toFixed(1)}
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
                      <Icon as={FiTrendingUp} mr={2} color="purple.400" />
                      Uncertainty
                    </StatLabel>
                    <StatNumber fontSize="3xl" color="purple.400" fontWeight="bold">
                      {playerData.sigma.toFixed(2)}
                    </StatNumber>
                    <StatHelpText color="gray.500" fontSize="xs">
                      Lower = More certain
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
              <Text as="span" className="emoji-font">📊</Text> Performance & Career
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
                          />
                        </VStack>
                      </GridItem>
                    ))}
                  </Grid>
                </TabPanel>
                
                <TabPanel p={0} pt={2}>
                  {!achievementData || achievementData.awarded.length === 0 ? (
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
                           <StatNumber fontSize="xl" color="accent.400">{achievementData.awarded.length}</StatNumber>
                         </Stat>
                      </HStack>
                      
                      <SimpleGrid columns={{ base: 2, sm: 3, md: 4, lg: 6 }} spacing={4}>
                        {achievementData.awarded.map((awarded: any) => {
                          const rarityColors = RARITY_COLORS[awarded.rarity as keyof typeof RARITY_COLORS] || RARITY_COLORS.common;
                          return (
                            <Tooltip 
                              key={awarded.code} 
                              label={
                                <Box p={1}>
                                  <Text fontWeight="bold">{awarded.name}</Text>
                                  <Text fontSize="xs">{awarded.description}</Text>
                                  <Text fontSize="10px" color="gray.400" mt={1}>Earned: {formatDateOnly(awarded.earned_at)}</Text>
                                </Box>
                              }
                              hasArrow
                            >
                              <VStack 
                                bg="space.900" 
                                p={3} 
                                borderRadius="xl" 
                                border="2px solid" 
                                borderColor={rarityColors.border}
                                transition="all 0.2s"
                                _hover={{ transform: 'scale(1.05)', boxShadow: '0 0 15px ' + rarityColors.border }}
                              >
                                <Circle size="10" bg={rarityColors.bg} boxShadow={rarityColors.glow}>
                                  <Text fontSize="xl">{awarded.icon || '🎖️'}</Text>
                                </Circle>
                                <Text fontSize="10px" fontWeight="bold" textAlign="center" noOfLines={1} color={rarityColors.text}>
                                  {awarded.name}
                                </Text>
                              </VStack>
                            </Tooltip>
                          );
                        })}
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
                  <Text as="span" className="emoji-font">🕐</Text> Recent Matches
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
                                {formatDateOnly(match.played_at)}
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
                  <Text fontSize="2xl" mb={2} className="emoji-font">🎮</Text>
                  <Text color="gray.500">No matches found for this page</Text>
                </Box>
              )}
            </VStack>
          </Box>
        </VStack>
      </Container>
    </RaceBackground>
  );
};

export default PlayerDetail;
