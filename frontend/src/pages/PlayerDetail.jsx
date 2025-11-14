/**
 * Player Detail Page
 * Shows comprehensive player information including stats and match history
 */
import { useState } from 'react';
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
  StatGroup,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  useColorModeValue,
  Alert,
  AlertIcon,
  Icon,
  Grid,
  GridItem,
  Progress,
  Flex,
  ButtonGroup,
} from '@chakra-ui/react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiTrendingUp, FiActivity, FiAward, FiTarget } from 'react-icons/fi';
import { playersApi } from '../api/endpoints';
import LoadingState from '../components/LoadingState';
import { formatDuration, formatWinRate } from '../utils/formatting';

const PlayerDetail = () => {
  const { playerId } = useParams();
  const navigate = useNavigate();
  const [matchesLimit, setMatchesLimit] = useState(10);

  const cardBg = useColorModeValue('white', 'gray.800');
  const teamBg = useColorModeValue('gray.50', 'gray.700');
  const winBg = useColorModeValue('green.50', 'green.900');
  const lossBg = useColorModeValue('red.50', 'red.900');

  // Fetch player details
  const { data: playerData, isLoading } = useQuery({
    queryKey: ['player', playerId, matchesLimit],
    queryFn: async () => {
      const response = await playersApi.getById(playerId, matchesLimit);
      return response.data;
    },
  });

  if (isLoading) {
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

  const getRaceColor = (race) => {
    switch (race) {
      case 'Terran': return 'red';
      case 'Protoss': return 'yellow';
      case 'Zerg': return 'purple';
      default: return 'gray';
    }
  };

  const getFavoriteRace = () => {
    const races = playerData.race_stats;
    const maxGames = Math.max(...Object.values(races));
    if (maxGames === 0) return 'Unknown';
    return Object.keys(races).find(race => races[race] === maxGames);
  };

  const favoriteRace = getFavoriteRace();

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Back Button */}
        <Button
          leftIcon={<FiArrowLeft />}
          variant="ghost"
          alignSelf="flex-start"
          onClick={() => navigate('/players')}
        >
          Back to Players
        </Button>

        {/* Player Header */}
        <Card bg={cardBg}>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <HStack justify="space-between" align="start">
                <VStack align="start" spacing={2}>
                  <HStack spacing={3}>
                    <Heading size="lg">{playerData.name}</Heading>
                    <Badge colorScheme={getRaceColor(favoriteRace)} fontSize="md">
                      {favoriteRace}
                    </Badge>
                    {playerData.is_core_player && (
                      <Badge colorScheme="blue" fontSize="md">
                        Core Player
                      </Badge>
                    )}
                  </HStack>
                  {playerData.last_played && (
                    <Text color="gray.500" fontSize="sm">
                      Last played: {new Date(playerData.last_played).toLocaleDateString()}
                    </Text>
                  )}
                </VStack>

                <StatGroup>
                  <Stat textAlign="right">
                    <StatLabel>MMR</StatLabel>
                    <StatNumber fontSize="3xl">
                      {Math.round(playerData.mmr)}
                    </StatNumber>
                    {playerData.recency_weighted_mmr && (
                      <StatHelpText>
                        Recent: {Math.round(playerData.recency_weighted_mmr)}
                      </StatHelpText>
                    )}
                  </Stat>
                </StatGroup>
              </HStack>
            </VStack>
          </CardBody>
        </Card>

        {/* Statistics Grid */}
        <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }} gap={6}>
          <GridItem>
            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>
                    <Icon as={FiActivity} mr={2} />
                    Total Games
                  </StatLabel>
                  <StatNumber>{playerData.total_games}</StatNumber>
                </Stat>
              </CardBody>
            </Card>
          </GridItem>

          <GridItem>
            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>
                    <Icon as={FiAward} mr={2} />
                    Win Rate
                  </StatLabel>
                  <StatNumber color={playerData.win_rate >= 0.5 ? 'green.500' : 'red.500'}>
                    {formatWinRate(playerData.win_rate)}
                  </StatNumber>
                  <StatHelpText>
                    {playerData.wins}W - {playerData.losses}L
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </GridItem>

          <GridItem>
            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>
                    <Icon as={FiTarget} mr={2} />
                    Skill (μ)
                  </StatLabel>
                  <StatNumber>{playerData.mu.toFixed(2)}</StatNumber>
                </Stat>
              </CardBody>
            </Card>
          </GridItem>

          <GridItem>
            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>
                    <Icon as={FiTrendingUp} mr={2} />
                    Uncertainty (σ)
                  </StatLabel>
                  <StatNumber>{playerData.sigma.toFixed(2)}</StatNumber>
                  <StatHelpText fontSize="xs">
                    Lower = More certain
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </GridItem>
        </Grid>

        {/* Race Statistics */}
        <Card bg={cardBg}>
          <CardBody>
            <Heading size="md" mb={4}>Race Statistics</Heading>
            <Grid templateColumns={{ base: '1fr', md: 'repeat(4, 1fr)' }} gap={4}>
              {Object.entries(playerData.race_stats).map(([race, games]) => (
                <GridItem key={race}>
                  <VStack align="stretch">
                    <HStack justify="space-between">
                      <Badge colorScheme={getRaceColor(race)}>{race}</Badge>
                      <Text fontWeight="bold">{games} games</Text>
                    </HStack>
                    <Progress
                      value={playerData.total_games > 0 ? (games / playerData.total_games) * 100 : 0}
                      colorScheme={getRaceColor(race)}
                      size="sm"
                      borderRadius="md"
                    />
                  </VStack>
                </GridItem>
              ))}
            </Grid>
          </CardBody>
        </Card>

        {/* Recent Matches */}
        <Card bg={cardBg}>
          <CardBody>
            <HStack justify="space-between" align="center" mb={4}>
              <Heading size="md">
                Recent Matches
                {playerData.recent_matches && playerData.recent_matches.length > 0 && (
                  <Badge ml={2} colorScheme="blue">
                    Showing {playerData.recent_matches.length}{playerData.total_games > matchesLimit ? ` of ${playerData.total_games}` : ''}
                  </Badge>
                )}
              </Heading>
              {playerData.total_games > 10 && (
                <ButtonGroup size="sm" variant="outline">
                  <Button
                    onClick={() => setMatchesLimit(10)}
                    isActive={matchesLimit === 10}
                  >
                    10
                  </Button>
                  <Button
                    onClick={() => setMatchesLimit(25)}
                    isActive={matchesLimit === 25}
                  >
                    25
                  </Button>
                  <Button
                    onClick={() => setMatchesLimit(50)}
                    isActive={matchesLimit === 50}
                  >
                    50
                  </Button>
                  {playerData.total_games > 50 && (
                    <Button
                      onClick={() => setMatchesLimit(playerData.total_games)}
                      isActive={matchesLimit === playerData.total_games}
                    >
                      All ({playerData.total_games})
                    </Button>
                  )}
                </ButtonGroup>
              )}
            </HStack>
            {playerData.recent_matches && playerData.recent_matches.length > 0 ? (
              <TableContainer>
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Date</Th>
                      <Th>Map</Th>
                      <Th>Mode</Th>
                      <Th>Race</Th>
                      <Th>Result</Th>
                      <Th isNumeric>MMR Before</Th>
                      <Th isNumeric>MMR After</Th>
                      <Th isNumeric>Change</Th>
                      <Th></Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {playerData.recent_matches.map((match) => (
                      <Tr
                        key={match.match_id}
                        bg={match.won ? winBg : lossBg}
                        _hover={{ opacity: 0.8, cursor: 'pointer' }}
                        onClick={() => navigate(`/history/${match.match_id}`)}
                      >
                        <Td>
                          <Text fontSize="xs">
                            {new Date(match.played_at).toLocaleDateString()}
                          </Text>
                        </Td>
                        <Td>{match.map_name}</Td>
                        <Td>
                          <Badge size="sm">{match.game_mode}</Badge>
                        </Td>
                        <Td>
                          <Badge colorScheme={getRaceColor(match.race)}>
                            {match.race}
                          </Badge>
                        </Td>
                        <Td>
                          <Badge colorScheme={match.won ? 'green' : 'red'}>
                            {match.won ? 'Win' : 'Loss'}
                          </Badge>
                        </Td>
                        <Td isNumeric>{Math.round(match.mmr_before)}</Td>
                        <Td isNumeric>{Math.round(match.mmr_after)}</Td>
                        <Td isNumeric>
                          <Text
                            color={match.mmr_change >= 0 ? 'green.500' : 'red.500'}
                            fontWeight="bold"
                          >
                            {match.mmr_change >= 0 ? '+' : ''}
                            {Math.round(match.mmr_change)}
                          </Text>
                        </Td>
                        <Td>
                          <Button size="xs" variant="ghost">
                            View
                          </Button>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </TableContainer>
            ) : (
              <Alert status="info">
                <AlertIcon />
                No recent matches found
              </Alert>
            )}
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};

export default PlayerDetail;
