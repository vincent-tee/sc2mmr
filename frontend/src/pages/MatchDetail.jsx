/**
 * Match Detail Page
 * Shows comprehensive match information including AI-generated commentary
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
  Divider,
  Alert,
  AlertIcon,
  Icon,
  Flex,
  Grid,
  GridItem,
} from '@chakra-ui/react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiTarget, FiTrendingUp, FiUsers, FiZap, FiAward, FiArrowUp, FiArrowDown } from 'react-icons/fi';
import { replaysApi } from '../api/endpoints';
import LoadingState from '../components/LoadingState';
import { formatDuration, formatWinRate, formatDateTime } from '../utils/formatting';

const MatchDetail = () => {
  const { matchId } = useParams();
  const navigate = useNavigate();

  const cardBg = useColorModeValue('white', 'gray.800');
  const teamBg = useColorModeValue('gray.50', 'gray.700');
  const winnerBg = useColorModeValue('green.50', 'green.900');
  const loserBg = useColorModeValue('red.50', 'red.900');

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
    enabled: !!matchData, // Only fetch commentary after match details are loaded
  });

  if (matchLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading match details..." />
      </Container>
    );
  }

  if (!matchData) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert status="error">
          <AlertIcon />
          Match not found
        </Alert>
      </Container>
    );
  }

  const { match, players } = matchData;

  // Group players by team
  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);
  const team1Won = team1Players.length > 0 && team1Players[0].won;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Back Button */}
        <Button
          leftIcon={<FiArrowLeft />}
          variant="ghost"
          alignSelf="flex-start"
          onClick={() => navigate('/history')}
        >
          Back to History
        </Button>

        {/* Match Header */}
        <Card bg={cardBg}>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <HStack justify="space-between" align="start">
                <VStack align="start" spacing={2}>
                  <HStack spacing={3}>
                    <Heading size="lg">{match.map_name}</Heading>
                    <Badge colorScheme="blue" fontSize="md">
                      {match.game_mode}
                    </Badge>
                  </HStack>
                  <Text color="gray.500">
                    {formatDateTime(match.played_at)}
                  </Text>
                </VStack>

                <Stat textAlign="right">
                  <StatLabel>Duration</StatLabel>
                  <StatNumber fontSize="2xl">
                    {formatDuration(match.duration_seconds)}
                  </StatNumber>
                </Stat>
              </HStack>
            </VStack>
          </CardBody>
        </Card>

        {/* Tabs for different views */}
        <Tabs colorScheme="brand" variant="enclosed">
          <TabList>
            <Tab>
              <Icon as={FiUsers} mr={2} />
              Players
            </Tab>
            <Tab>
              <Icon as={FiZap} mr={2} />
              Commentary
            </Tab>
          </TabList>

          <TabPanels>
            {/* Players Tab */}
            <TabPanel px={0}>
              <VStack spacing={6} align="stretch">
                {/* Team 1 */}
                <Box>
                  <HStack mb={4} spacing={3}>
                    <Heading size="md">Team 1</Heading>
                    {team1Won && (
                      <Badge colorScheme="green" fontSize="md">
                        <Icon as={FiAward} mr={1} />
                        Victory
                      </Badge>
                    )}
                  </HStack>
                  <Card bg={team1Won ? winnerBg : loserBg}>
                    <CardBody>
                      <TableContainer>
                        <Table variant="simple" size="sm">
                          <Thead>
                            <Tr>
                              <Th>Player</Th>
                              <Th>Race</Th>
                              <Th isNumeric>MMR Before</Th>
                              <Th isNumeric>MMR After</Th>
                              <Th isNumeric>Change</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {team1Players.map((player, idx) => (
                              <Tr key={idx}>
                                <Td fontWeight="bold">{player.player_name}</Td>
                                <Td>
                                  <Badge>{player.race}</Badge>
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
                    <Heading size="md">Team 2</Heading>
                    {!team1Won && (
                      <Badge colorScheme="green" fontSize="md">
                        <Icon as={FiAward} mr={1} />
                        Victory
                      </Badge>
                    )}
                  </HStack>
                  <Card bg={team1Won ? loserBg : winnerBg}>
                    <CardBody>
                      <TableContainer>
                        <Table variant="simple" size="sm">
                          <Thead>
                            <Tr>
                              <Th>Player</Th>
                              <Th>Race</Th>
                              <Th isNumeric>MMR Before</Th>
                              <Th isNumeric>MMR After</Th>
                              <Th isNumeric>Change</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {team2Players.map((player, idx) => (
                              <Tr key={idx}>
                                <Td fontWeight="bold">{player.player_name}</Td>
                                <Td>
                                  <Badge>{player.race}</Badge>
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
                <LoadingState message="Generating AI commentary..." />
              ) : commentary && !commentary.error ? (
                <VStack spacing={6} align="stretch">
                  {/* Match Overview */}
                  <Card bg={cardBg}>
                    <CardBody>
                      <Heading size="md" mb={3}>
                        Match Overview
                      </Heading>
                      <Text lineHeight="tall">{commentary.overview}</Text>
                    </CardBody>
                  </Card>

                  {/* Key Moments */}
                  <Card bg={cardBg}>
                    <CardBody>
                      <HStack mb={4}>
                        <Icon as={FiZap} color="yellow.500" />
                        <Heading size="md">Key Moments</Heading>
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
                  {commentary.mvp_analysis && commentary.mvp_analysis.player_name !== 'Unknown' && (
                    <Card bg={cardBg} borderWidth="2px" borderColor="yellow.400">
                      <CardBody>
                        <HStack mb={4}>
                          <Icon as={FiAward} color="yellow.500" boxSize={6} />
                          <Heading size="md">Match MVP</Heading>
                        </HStack>
                        <VStack align="stretch" spacing={3}>
                          <HStack>
                            <Text fontWeight="bold" fontSize="xl">
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
                  <Card bg={cardBg}>
                    <CardBody>
                      <HStack mb={4}>
                        <Icon as={FiTarget} color="blue.500" />
                        <Heading size="md">Player Performances</Heading>
                      </HStack>
                      <VStack align="stretch" spacing={4}>
                        {Object.entries(commentary.player_performances).map(([name, analysis]) => (
                          <Box key={name} p={4} bg={teamBg} borderRadius="md">
                            <Heading size="sm" mb={2}>
                              {name}
                            </Heading>
                            <Text fontSize="sm" lineHeight="tall">
                              {analysis}
                            </Text>
                          </Box>
                        ))}
                      </VStack>
                    </CardBody>
                  </Card>

                  {/* Team Analysis */}
                  {commentary.team_analysis && (
                    <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={6}>
                      <GridItem>
                        <Card bg={cardBg}>
                          <CardBody>
                            <Heading size="md" mb={3}>
                              Team 1 Analysis
                            </Heading>
                            <Text fontSize="sm" lineHeight="tall">
                              {commentary.team_analysis.team_1}
                            </Text>
                          </CardBody>
                        </Card>
                      </GridItem>
                      <GridItem>
                        <Card bg={cardBg}>
                          <CardBody>
                            <Heading size="md" mb={3}>
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
                  <Card bg={cardBg}>
                    <CardBody>
                      <HStack mb={4}>
                        <Icon as={FiTrendingUp} color="purple.500" />
                        <Heading size="md">Final Summary</Heading>
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
                  Commentary is only available for replays uploaded with advanced metrics. Upload
                  replays using the "Upload-Advanced" endpoint to enable this feature.
                </Alert>
              )}
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Container>
  );
};

export default MatchDetail;
