/**
 * Match Detail Page - TACTICAL MISSION ANALYSIS
 * Comprehensive match information with win probability analysis
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
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useColorModeValue,
  Alert,
  AlertIcon,
  Icon,
  Flex,
  Grid,
  GridItem,
  Progress,
  Divider,
} from '@chakra-ui/react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  FiArrowLeft,
  FiTarget,
  FiTrendingUp,
  FiUsers,
  FiZap,
  FiAward,
  FiArrowUp,
  FiArrowDown,
  FiAlertTriangle,
  FiActivity,
} from 'react-icons/fi';
import { replaysApi, impactApi } from '../api/endpoints';
import LoadingState from '../components/LoadingState';
import DamageTimelineChart from '../components/charts/DamageTimelineChart';
import ImpactScoreRadar from '../components/charts/ImpactScoreRadar';
import DamageDistributionChart from '../components/charts/DamageDistributionChart';
import PlayerMetricsComparison from '../components/charts/PlayerMetricsComparison';
import {
  formatDuration,
  formatDateTime,
  formatWinProbability,
  getUpsetIndicator,
  isUpset,
} from '../utils/formatting';

const MatchDetail = () => {
  const { matchId } = useParams();
  const navigate = useNavigate();

  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');
  const teamBg = useColorModeValue('gray.50', 'rgba(30, 41, 59, 0.5)');
  const winnerBg = useColorModeValue('green.50', 'rgba(0, 255, 136, 0.1)');
  const loserBg = useColorModeValue('red.50', 'rgba(239, 68, 68, 0.1)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');

  // Fetch match details
  const { data: matchData, isLoading: matchLoading } = useQuery({
    queryKey: ['match', matchId],
    queryFn: async () => {
      const response = await replaysApi.getMatchById(matchId);
      return response.data;
    },
  });

  // Fetch match commentary
  const { data: commentary, isLoading: commentaryLoading } = useQuery({
    queryKey: ['match-commentary', matchId],
    queryFn: async () => {
      const response = await replaysApi.getMatchCommentary(matchId);
      return response.data;
    },
    enabled: !!matchData,
  });

  // Fetch metrics data for all players in the match
  const { data: playerMetrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['match-metrics', matchId],
    queryFn: async () => {
      if (!matchData || !matchData.players) return null;

      const metricsPromises = matchData.players.map(async (player) => {
        try {
          const response = await impactApi.getPlayerMatchMetrics(player.player_id, 100);
          // Find the metrics for this specific match
          const matchMetric = response.data.find((m) => m.match_id === parseInt(matchId));
          return {
            player_id: player.player_id,
            player_name: player.player_name,
            metrics: matchMetric,
          };
        } catch (error) {
          console.error(`Error fetching metrics for player ${player.player_id}:`, error);
          return null;
        }
      });

      const results = await Promise.all(metricsPromises);

      // Convert to object keyed by player_id for easy lookup
      const metricsMap = {};
      results.forEach((result) => {
        if (result && result.metrics) {
          metricsMap[result.player_id] = result.metrics;
        }
      });

      return metricsMap;
    },
    enabled: !!matchData,
  });

  // Fetch damage timeline data for players
  const { data: damageTimelines, isLoading: timelinesLoading } = useQuery({
    queryKey: ['match-damage-timelines', matchId],
    queryFn: async () => {
      if (!matchData || !matchData.players) return null;

      const timelinePromises = matchData.players.map(async (player) => {
        try {
          const response = await impactApi.getMatchDamageTimeline(player.player_id, matchId);
          return {
            player_id: player.player_id,
            player_name: player.player_name,
            team_number: player.team_number,
            timeline: response.data,
          };
        } catch (error) {
          // Timeline might not be available for all players
          return null;
        }
      });

      const results = await Promise.all(timelinePromises);
      return results.filter((r) => r !== null);
    },
    enabled: !!matchData,
  });

  if (matchLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading tactical data..." />
      </Container>
    );
  }

  if (!matchData) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert status="error">
          <AlertIcon />
          Mission data not found
        </Alert>
      </Container>
    );
  }

  const { match, players } = matchData;

  // Group players by team
  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);
  const team1Won = team1Players.length > 0 && team1Players[0].won;

  // Win probability analysis
  const hasWinProb = match.predicted_team1_win_prob && match.predicted_team2_win_prob;
  const team1Prob = match.predicted_team1_win_prob || 0.5;
  const team2Prob = match.predicted_team2_win_prob || 0.5;
  const winningTeam = team1Won ? 1 : 2;
  const upsetIndicator = hasWinProb ? getUpsetIndicator(winningTeam, team1Prob, team2Prob) : null;
  const wasUpset = hasWinProb ? isUpset(winningTeam, team1Prob, team2Prob) : false;

  return (
    <Box position="relative">
      {/* Animated tactical grid background */}
      <Box
        position="fixed"
        top={0}
        left={0}
        right={0}
        bottom={0}
        opacity={0.02}
        pointerEvents="none"
        backgroundImage="linear-gradient(rgba(0, 212, 255, 0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.8) 1px, transparent 1px)"
        backgroundSize="60px 60px"
        zIndex={0}
      />

      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Back Button */}
          <Button
            leftIcon={<FiArrowLeft />}
            variant="ghost"
            alignSelf="flex-start"
            onClick={() => navigate('/history')}
            size="lg"
            fontFamily="heading"
            _hover={{
              transform: 'translateX(-4px)',
              color: 'brand.400',
            }}
            transition="all 0.2s"
          >
            RETURN TO ARCHIVE
          </Button>

          {/* Dramatic Match Header */}
          <Card
            bg={cardBg}
            border="2px solid"
            borderColor={borderColor}
            boxShadow="0 8px 32px rgba(0, 212, 255, 0.2)"
            position="relative"
            overflow="hidden"
            _before={{
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '4px',
              background: 'linear-gradient(90deg, rgba(0, 212, 255, 0.8), rgba(255, 179, 0, 0.8))',
            }}
          >
            <CardBody>
              <VStack align="stretch" spacing={6}>
                <Flex justify="space-between" align="start" flexWrap="wrap" gap={4}>
                  <VStack align="start" spacing={2}>
                    <HStack spacing={3}>
                      <Icon as={FiActivity} boxSize={6} color="brand.400" />
                      <Heading
                        size="2xl"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wider"
                      >
                        {match.map_name}
                      </Heading>
                      <Badge
                        colorScheme="blue"
                        fontSize="lg"
                        px={4}
                        py={1}
                        fontFamily="heading"
                      >
                        {match.game_mode}
                      </Badge>
                    </HStack>
                    <Text color="gray.500" fontFamily="heading" fontSize="sm">
                      {formatDateTime(match.played_at)}
                    </Text>
                  </VStack>

                  <Stat textAlign="right">
                    <StatLabel fontFamily="heading" color="brand.400">
                      MISSION DURATION
                    </StatLabel>
                    <StatNumber fontSize="3xl" fontFamily="heading">
                      {formatDuration(match.duration_seconds)}
                    </StatNumber>
                  </Stat>
                </Flex>

                {/* DRAMATIC WIN PROBABILITY SECTION */}
                {hasWinProb && (
                  <Box>
                    <Divider my={4} borderColor="whiteAlpha.200" />

                    {/* Upset Alert */}
                    {upsetIndicator && (
                      <Alert
                        status="warning"
                        variant="left-accent"
                        mb={4}
                        bg="rgba(255, 179, 0, 0.1)"
                        borderColor="accent.500"
                        borderWidth="2px"
                      >
                        <Icon as={FiAlertTriangle} boxSize={6} mr={3} color="accent.500" />
                        <Box>
                          <Text
                            fontWeight="bold"
                            fontSize="lg"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wider"
                          >
                            {upsetIndicator}
                          </Text>
                          <Text fontSize="sm" mt={1}>
                            The underdog team defied the odds and secured victory!
                          </Text>
                        </Box>
                      </Alert>
                    )}

                    <VStack spacing={4}>
                      <Heading
                        size="md"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wider"
                        color="brand.400"
                      >
                        ▸ WIN PROBABILITY ANALYSIS
                      </Heading>

                      <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={6} w="full">
                        {/* Team 1 Prediction */}
                        <Card
                          bg={team1Won ? winnerBg : loserBg}
                          border="2px solid"
                          borderColor={team1Won ? 'shield.500' : 'red.500'}
                          boxShadow={team1Won ? '0 0 20px rgba(0, 255, 136, 0.3)' : 'none'}
                        >
                          <CardBody>
                            <VStack spacing={3}>
                              <HStack>
                                <Icon as={FiTrendingUp} color="brand.400" boxSize={5} />
                                <Text
                                  fontFamily="heading"
                                  fontWeight="bold"
                                  textTransform="uppercase"
                                  color="brand.400"
                                >
                                  Team 1
                                </Text>
                                {team1Won && (
                                  <Badge colorScheme="green" ml="auto">
                                    <Icon as={FiAward} mr={1} />
                                    VICTORY
                                  </Badge>
                                )}
                              </HStack>
                              <Stat textAlign="center">
                                <StatLabel fontSize="xs" color="gray.500">
                                  PREDICTED WIN CHANCE
                                </StatLabel>
                                <StatNumber
                                  fontSize="4xl"
                                  fontFamily="heading"
                                  color={team1Prob > 0.5 ? 'shield.500' : 'gray.400'}
                                >
                                  {formatWinProbability(team1Prob)}
                                </StatNumber>
                                <StatHelpText>
                                  {team1Won ? 'Prediction: Correct' : 'Prediction: Incorrect'}
                                </StatHelpText>
                              </Stat>
                            </VStack>
                          </CardBody>
                        </Card>

                        {/* VS Divider */}
                        <Flex align="center" justify="center">
                          <Box textAlign="center">
                            <Icon as={FiZap} boxSize={12} color="accent.500" mb={2} />
                            <Text
                              fontFamily="heading"
                              fontSize="2xl"
                              fontWeight="black"
                              letterSpacing="wider"
                              color="accent.500"
                            >
                              VS
                            </Text>
                          </Box>
                        </Flex>

                        {/* Team 2 Prediction */}
                        <Card
                          bg={!team1Won ? winnerBg : loserBg}
                          border="2px solid"
                          borderColor={!team1Won ? 'shield.500' : 'red.500'}
                          boxShadow={!team1Won ? '0 0 20px rgba(0, 255, 136, 0.3)' : 'none'}
                        >
                          <CardBody>
                            <VStack spacing={3}>
                              <HStack>
                                <Icon as={FiTrendingUp} color="accent.400" boxSize={5} />
                                <Text
                                  fontFamily="heading"
                                  fontWeight="bold"
                                  textTransform="uppercase"
                                  color="accent.400"
                                >
                                  Team 2
                                </Text>
                                {!team1Won && (
                                  <Badge colorScheme="green" ml="auto">
                                    <Icon as={FiAward} mr={1} />
                                    VICTORY
                                  </Badge>
                                )}
                              </HStack>
                              <Stat textAlign="center">
                                <StatLabel fontSize="xs" color="gray.500">
                                  PREDICTED WIN CHANCE
                                </StatLabel>
                                <StatNumber
                                  fontSize="4xl"
                                  fontFamily="heading"
                                  color={team2Prob > 0.5 ? 'shield.500' : 'gray.400'}
                                >
                                  {formatWinProbability(team2Prob)}
                                </StatNumber>
                                <StatHelpText>
                                  {!team1Won ? 'Prediction: Correct' : 'Prediction: Incorrect'}
                                </StatHelpText>
                              </Stat>
                            </VStack>
                          </CardBody>
                        </Card>
                      </Grid>

                      {/* Visual probability comparison */}
                      <Box w="full">
                        <HStack spacing={1}>
                          <Box flex={team1Prob}>
                            <Progress
                              value={100}
                              size="xl"
                              colorScheme="cyan"
                              borderRadius="md"
                              bg="gray.700"
                              sx={{
                                '& > div': {
                                  background: 'linear-gradient(90deg, rgba(0, 212, 255, 0.6), rgba(0, 212, 255, 1))',
                                  boxShadow: '0 0 15px rgba(0, 212, 255, 0.6)',
                                },
                              }}
                            />
                          </Box>
                          <Box flex={team2Prob}>
                            <Progress
                              value={100}
                              size="xl"
                              colorScheme="orange"
                              borderRadius="md"
                              bg="gray.700"
                              sx={{
                                '& > div': {
                                  background: 'linear-gradient(90deg, rgba(255, 179, 0, 1), rgba(255, 179, 0, 0.6))',
                                  boxShadow: '0 0 15px rgba(255, 179, 0, 0.6)',
                                },
                              }}
                            />
                          </Box>
                        </HStack>
                      </Box>
                    </VStack>
                  </Box>
                )}
              </VStack>
            </CardBody>
          </Card>

          {/* Tabs for different views */}
          <Tabs
            colorScheme="brand"
            variant="enclosed"
            size="lg"
            sx={{
              '& .chakra-tabs__tab': {
                fontFamily: 'heading',
                textTransform: 'uppercase',
                letterSpacing: 'wider',
                _selected: {
                  bg: 'brand.500',
                  color: 'gray.900',
                  borderColor: 'brand.500',
                  boxShadow: '0 0 20px rgba(0, 212, 255, 0.4)',
                },
              },
            }}
          >
            <TabList>
              <Tab>
                <Icon as={FiUsers} mr={2} />
                OPERATIVES
              </Tab>
              <Tab>
                <Icon as={FiZap} mr={2} />
                COMMENTARY
              </Tab>
              <Tab>
                <Icon as={FiTarget} mr={2} />
                ANALYTICS
              </Tab>
            </TabList>

            <TabPanels>
              {/* Players Tab */}
              <TabPanel px={0}>
                <VStack spacing={6} align="stretch">
                  {/* Team 1 */}
                  <Box>
                    <HStack mb={4} spacing={3}>
                      <Heading
                        size="lg"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wider"
                      >
                        Team 1
                      </Heading>
                      {team1Won && (
                        <Badge
                          colorScheme="green"
                          fontSize="md"
                          px={3}
                          py={1}
                          fontFamily="heading"
                        >
                          <Icon as={FiAward} mr={1} />
                          VICTORY
                        </Badge>
                      )}
                    </HStack>
                    <Card
                      bg={team1Won ? winnerBg : loserBg}
                      border="2px solid"
                      borderColor={team1Won ? 'shield.500' : 'red.500'}
                    >
                      <CardBody>
                        <TableContainer>
                          <Table variant="simple" size="sm">
                            <Thead>
                              <Tr>
                                <Th fontFamily="heading">OPERATIVE</Th>
                                <Th fontFamily="heading">RACE</Th>
                                <Th isNumeric fontFamily="heading">
                                  MMR BEFORE
                                </Th>
                                <Th isNumeric fontFamily="heading">
                                  MMR AFTER
                                </Th>
                                <Th isNumeric fontFamily="heading">
                                  CHANGE
                                </Th>
                              </Tr>
                            </Thead>
                            <Tbody>
                              {team1Players.map((player, idx) => (
                                <Tr key={idx}>
                                  <Td fontWeight="bold" fontFamily="heading">
                                    {player.player_name}
                                  </Td>
                                  <Td>
                                    <Badge fontFamily="heading">{player.race}</Badge>
                                  </Td>
                                  <Td isNumeric>{Math.round(player.mmr_before)}</Td>
                                  <Td isNumeric>{Math.round(player.mmr_after)}</Td>
                                  <Td isNumeric>
                                    <HStack justify="flex-end" spacing={1}>
                                      <Icon
                                        as={player.mmr_change >= 0 ? FiArrowUp : FiArrowDown}
                                        color={player.mmr_change >= 0 ? 'green.500' : 'red.500'}
                                      />
                                      <Text
                                        color={player.mmr_change >= 0 ? 'green.500' : 'red.500'}
                                        fontWeight="bold"
                                      >
                                        {Math.abs(Math.round(player.mmr_change))}
                                      </Text>
                                    </HStack>
                                  </Td>
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </TableContainer>
                      </CardBody>
                    </Card>
                  </Box>

                  {/* Team 2 */}
                  <Box>
                    <HStack mb={4} spacing={3}>
                      <Heading
                        size="lg"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wider"
                      >
                        Team 2
                      </Heading>
                      {!team1Won && (
                        <Badge
                          colorScheme="green"
                          fontSize="md"
                          px={3}
                          py={1}
                          fontFamily="heading"
                        >
                          <Icon as={FiAward} mr={1} />
                          VICTORY
                        </Badge>
                      )}
                    </HStack>
                    <Card
                      bg={team1Won ? loserBg : winnerBg}
                      border="2px solid"
                      borderColor={team1Won ? 'red.500' : 'shield.500'}
                    >
                      <CardBody>
                        <TableContainer>
                          <Table variant="simple" size="sm">
                            <Thead>
                              <Tr>
                                <Th fontFamily="heading">OPERATIVE</Th>
                                <Th fontFamily="heading">RACE</Th>
                                <Th isNumeric fontFamily="heading">
                                  MMR BEFORE
                                </Th>
                                <Th isNumeric fontFamily="heading">
                                  MMR AFTER
                                </Th>
                                <Th isNumeric fontFamily="heading">
                                  CHANGE
                                </Th>
                              </Tr>
                            </Thead>
                            <Tbody>
                              {team2Players.map((player, idx) => (
                                <Tr key={idx}>
                                  <Td fontWeight="bold" fontFamily="heading">
                                    {player.player_name}
                                  </Td>
                                  <Td>
                                    <Badge fontFamily="heading">{player.race}</Badge>
                                  </Td>
                                  <Td isNumeric>{Math.round(player.mmr_before)}</Td>
                                  <Td isNumeric>{Math.round(player.mmr_after)}</Td>
                                  <Td isNumeric>
                                    <HStack justify="flex-end" spacing={1}>
                                      <Icon
                                        as={player.mmr_change >= 0 ? FiArrowUp : FiArrowDown}
                                        color={player.mmr_change >= 0 ? 'green.500' : 'red.500'}
                                      />
                                      <Text
                                        color={player.mmr_change >= 0 ? 'green.500' : 'red.500'}
                                        fontWeight="bold"
                                      >
                                        {Math.abs(Math.round(player.mmr_change))}
                                      </Text>
                                    </HStack>
                                  </Td>
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </TableContainer>
                      </CardBody>
                    </Card>
                  </Box>
                </VStack>
              </TabPanel>

              {/* Commentary Tab */}
              <TabPanel px={0}>
                {commentaryLoading ? (
                  <LoadingState message="Generating tactical analysis..." />
                ) : commentary && !commentary.error ? (
                  <VStack spacing={6} align="stretch">
                    {/* Match Overview */}
                    <Card
                      bg={cardBg}
                      border="2px solid"
                      borderColor={borderColor}
                    >
                      <CardBody>
                        <Heading
                          size="md"
                          mb={3}
                          fontFamily="heading"
                          textTransform="uppercase"
                          letterSpacing="wider"
                        >
                          Mission Overview
                        </Heading>
                        <Text lineHeight="tall">{commentary.overview}</Text>
                      </CardBody>
                    </Card>

                    {/* Key Moments */}
                    <Card
                      bg={cardBg}
                      border="2px solid"
                      borderColor={borderColor}
                    >
                      <CardBody>
                        <HStack mb={4}>
                          <Icon as={FiZap} color="yellow.500" />
                          <Heading
                            size="md"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wider"
                          >
                            Critical Moments
                          </Heading>
                        </HStack>
                        <VStack align="stretch" spacing={3}>
                          {commentary.key_moments.map((moment, idx) => (
                            <Box
                              key={idx}
                              p={3}
                              bg={teamBg}
                              borderRadius="md"
                              borderLeft="4px solid"
                              borderLeftColor="brand.500"
                            >
                              <Text>{moment}</Text>
                            </Box>
                          ))}
                        </VStack>
                      </CardBody>
                    </Card>

                    {/* MVP Analysis */}
                    {commentary.mvp_analysis &&
                      commentary.mvp_analysis.player_name !== 'Unknown' && (
                        <Card
                          bg={cardBg}
                          borderWidth="3px"
                          borderColor="yellow.400"
                          boxShadow="0 0 30px rgba(255, 215, 0, 0.3)"
                        >
                          <CardBody>
                            <HStack mb={4}>
                              <Icon as={FiAward} color="yellow.500" boxSize={6} />
                              <Heading
                                size="md"
                                fontFamily="heading"
                                textTransform="uppercase"
                                letterSpacing="wider"
                              >
                                Mission MVP
                              </Heading>
                            </HStack>
                            <VStack align="stretch" spacing={3}>
                              <HStack>
                                <Text
                                  fontWeight="bold"
                                  fontSize="xl"
                                  fontFamily="heading"
                                >
                                  {commentary.mvp_analysis.player_name}
                                </Text>
                                <Badge colorScheme="yellow" fontSize="md">
                                  Team {commentary.mvp_analysis.team}
                                </Badge>
                                {commentary.mvp_analysis.impact_score && (
                                  <Badge colorScheme="green" fontSize="md">
                                    Impact: {commentary.mvp_analysis.impact_score.toFixed(1)}
                                  </Badge>
                                )}
                              </HStack>
                              <Text lineHeight="tall">{commentary.mvp_analysis.reasoning}</Text>
                            </VStack>
                          </CardBody>
                        </Card>
                      )}

                    {/* Player Performances */}
                    <Card
                      bg={cardBg}
                      border="2px solid"
                      borderColor={borderColor}
                    >
                      <CardBody>
                        <HStack mb={4}>
                          <Icon as={FiTarget} color="blue.500" />
                          <Heading
                            size="md"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wider"
                          >
                            Operative Performance
                          </Heading>
                        </HStack>
                        <VStack align="stretch" spacing={4}>
                          {Object.entries(commentary.player_performances).map(
                            ([name, analysis]) => (
                              <Box key={name} p={4} bg={teamBg} borderRadius="md">
                                <Heading size="sm" mb={2} fontFamily="heading">
                                  {name}
                                </Heading>
                                <Text fontSize="sm" lineHeight="tall">
                                  {analysis}
                                </Text>
                              </Box>
                            )
                          )}
                        </VStack>
                      </CardBody>
                    </Card>

                    {/* Team Analysis */}
                    {commentary.team_analysis && (
                      <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={6}>
                        <GridItem>
                          <Card
                            bg={cardBg}
                            border="2px solid"
                            borderColor={borderColor}
                          >
                            <CardBody>
                              <Heading
                                size="md"
                                mb={3}
                                fontFamily="heading"
                                textTransform="uppercase"
                                letterSpacing="wider"
                              >
                                Team 1 Analysis
                              </Heading>
                              <Text fontSize="sm" lineHeight="tall">
                                {commentary.team_analysis.team_1}
                              </Text>
                            </CardBody>
                          </Card>
                        </GridItem>
                        <GridItem>
                          <Card
                            bg={cardBg}
                            border="2px solid"
                            borderColor={borderColor}
                          >
                            <CardBody>
                              <Heading
                                size="md"
                                mb={3}
                                fontFamily="heading"
                                textTransform="uppercase"
                                letterSpacing="wider"
                              >
                                Team 2 Analysis
                              </Heading>
                              <Text fontSize="sm" lineHeight="tall">
                                {commentary.team_analysis.team_2}
                              </Text>
                            </CardBody>
                          </Card>
                        </GridItem>
                      </Grid>
                    )}

                    {/* Match Summary */}
                    <Card
                      bg={cardBg}
                      border="2px solid"
                      borderColor={borderColor}
                    >
                      <CardBody>
                        <HStack mb={4}>
                          <Icon as={FiTrendingUp} color="purple.500" />
                          <Heading
                            size="md"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wider"
                          >
                            Final Assessment
                          </Heading>
                        </HStack>
                        <Text lineHeight="tall" fontSize="md">
                          {commentary.match_summary}
                        </Text>
                      </CardBody>
                    </Card>
                  </VStack>
                ) : (
                  <Alert status="info">
                    <AlertIcon />
                    Tactical commentary is only available for advanced replay uploads.
                  </Alert>
                )}
              </TabPanel>

              {/* Analytics Tab */}
              <TabPanel px={0}>
                {metricsLoading || timelinesLoading ? (
                  <LoadingState message="Loading match analytics..." />
                ) : playerMetrics && Object.keys(playerMetrics).length > 0 ? (
                  <VStack spacing={6} align="stretch">
                    {/* Player Comparison */}
                    <PlayerMetricsComparison
                      players={players}
                      metricsData={playerMetrics}
                    />

                    {/* Individual Player Analytics - Team 1 */}
                    <Box>
                      <Heading
                        size="lg"
                        mb={4}
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wider"
                      >
                        Team 1 Analytics
                      </Heading>
                      <VStack spacing={4} align="stretch">
                        {team1Players.map((player) => {
                          const metrics = playerMetrics[player.player_id];
                          const timeline = damageTimelines?.find(
                            (t) => t.player_id === player.player_id
                          );

                          if (!metrics) return null;

                          return (
                            <Box key={player.player_id}>
                              <Grid
                                templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }}
                                gap={4}
                              >
                                {/* Impact Score Radar */}
                                <GridItem>
                                  <ImpactScoreRadar
                                    metrics={metrics}
                                    playerName={player.player_name}
                                  />
                                </GridItem>

                                {/* Damage Distribution */}
                                <GridItem>
                                  {timeline && timeline.timeline.damage_distribution && (
                                    <DamageDistributionChart
                                      damageDistribution={timeline.timeline.damage_distribution}
                                      playerName={player.player_name}
                                    />
                                  )}
                                </GridItem>
                              </Grid>

                              {/* Damage Timeline */}
                              {timeline && (
                                <Box mt={4}>
                                  <DamageTimelineChart
                                    timelineData={timeline.timeline}
                                    playerName={player.player_name}
                                  />
                                </Box>
                              )}

                              <Divider my={6} borderColor="whiteAlpha.200" />
                            </Box>
                          );
                        })}
                      </VStack>
                    </Box>

                    {/* Individual Player Analytics - Team 2 */}
                    <Box>
                      <Heading
                        size="lg"
                        mb={4}
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wider"
                      >
                        Team 2 Analytics
                      </Heading>
                      <VStack spacing={4} align="stretch">
                        {team2Players.map((player) => {
                          const metrics = playerMetrics[player.player_id];
                          const timeline = damageTimelines?.find(
                            (t) => t.player_id === player.player_id
                          );

                          if (!metrics) return null;

                          return (
                            <Box key={player.player_id}>
                              <Grid
                                templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }}
                                gap={4}
                              >
                                {/* Impact Score Radar */}
                                <GridItem>
                                  <ImpactScoreRadar
                                    metrics={metrics}
                                    playerName={player.player_name}
                                  />
                                </GridItem>

                                {/* Damage Distribution */}
                                <GridItem>
                                  {timeline && timeline.timeline.damage_distribution && (
                                    <DamageDistributionChart
                                      damageDistribution={timeline.timeline.damage_distribution}
                                      playerName={player.player_name}
                                    />
                                  )}
                                </GridItem>
                              </Grid>

                              {/* Damage Timeline */}
                              {timeline && (
                                <Box mt={4}>
                                  <DamageTimelineChart
                                    timelineData={timeline.timeline}
                                    playerName={player.player_name}
                                  />
                                </Box>
                              )}

                              {player !== team2Players[team2Players.length - 1] && (
                                <Divider my={6} borderColor="whiteAlpha.200" />
                              )}
                            </Box>
                          );
                        })}
                      </VStack>
                    </Box>
                  </VStack>
                ) : (
                  <Alert status="info">
                    <AlertIcon />
                    Advanced analytics are only available for matches with detailed metrics data.
                    Upload replays using the "Advanced Upload" option to enable analytics.
                  </Alert>
                )}
              </TabPanel>
            </TabPanels>
          </Tabs>
        </VStack>
      </Container>
    </Box>
  );
};

export default MatchDetail;
