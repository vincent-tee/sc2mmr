/**
 * Lineup Predictor - Manually select player lineups and predict win rates
 */
import { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  Button,
  Badge,
  Icon,
  Grid,
  GridItem,
  Select,
  IconButton,
  Divider,
  useColorModeValue,
  Alert,
  AlertIcon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Progress,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import {
  FiUsers,
  FiTarget,
  FiTrendingUp,
  FiX,
  FiPlus,
  FiZap,
  FiShield,
} from 'react-icons/fi';
import { playersApi, teamsApi } from '../api/endpoints';
import LoadingState from '../components/LoadingState';

const LineupPredictor = () => {
  const [team1Players, setTeam1Players] = useState([]);
  const [team2Players, setTeam2Players] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);

  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');
  const team1Bg = useColorModeValue('cyan.50', 'rgba(0, 212, 255, 0.1)');
  const team2Bg = useColorModeValue('orange.50', 'rgba(255, 179, 0, 0.1)');

  // Fetch all players
  const { data: playersData, isLoading: playersLoading } = useQuery({
    queryKey: ['players-all'],
    queryFn: async () => {
      const response = await playersApi.getAll(false);
      return response.data;
    },
  });

  const players = playersData || [];

  // Calculate prediction when lineups change
  useEffect(() => {
    if (team1Players.length > 0 && team2Players.length > 0 &&
        team1Players.length === team2Players.length) {
      calculatePrediction();
    } else {
      setPrediction(null);
    }
  }, [team1Players, team2Players]);

  const calculatePrediction = async () => {
    setIsCalculating(true);
    try {
      const allPlayerIds = [...team1Players, ...team2Players];
      const response = await teamsApi.balance(allPlayerIds, 1);

      // Find which team configuration matches our selection
      const ourTeam1Ids = new Set(team1Players);
      const matchingBalance = response.data.balanced_teams.find(balance => {
        const configTeam1Ids = new Set(balance.team_1.map(p => p.id));
        return (
          balance.team_1.length === team1Players.length &&
          [...ourTeam1Ids].every(id => configTeam1Ids.has(id))
        );
      });

      if (matchingBalance) {
        setPrediction({
          team1_win_prob: matchingBalance.team_1_win_prob,
          team2_win_prob: matchingBalance.team_2_win_prob,
          mmr_difference: matchingBalance.mmr_difference,
          quality: matchingBalance.quality,
        });
      } else {
        // If exact match not found, estimate based on MMR
        const team1MMR = team1Players.reduce((sum, id) => {
          const player = players.find(p => p.id === id);
          return sum + (player?.mmr || 0);
        }, 0) / team1Players.length;

        const team2MMR = team2Players.reduce((sum, id) => {
          const player = players.find(p => p.id === id);
          return sum + (player?.mmr || 0);
        }, 0) / team2Players.length;

        const mmrDiff = team1MMR - team2MMR;

        // Simple logistic function for win probability based on MMR difference
        const team1WinProb = 1 / (1 + Math.exp(-mmrDiff / 200));

        setPrediction({
          team1_win_prob: team1WinProb,
          team2_win_prob: 1 - team1WinProb,
          mmr_difference: Math.abs(mmrDiff),
          quality: 1 - Math.abs(team1WinProb - 0.5) * 2,
        });
      }
    } catch (error) {
      console.error('Error calculating prediction:', error);
    } finally {
      setIsCalculating(false);
    }
  };

  const addPlayerToTeam = (teamNumber, playerId) => {
    const player = players.find(p => p.id === parseInt(playerId));
    if (!player) return;

    if (teamNumber === 1) {
      if (!team1Players.includes(player.id) && !team2Players.includes(player.id)) {
        setTeam1Players([...team1Players, player.id]);
      }
    } else {
      if (!team2Players.includes(player.id) && !team1Players.includes(player.id)) {
        setTeam2Players([...team2Players, player.id]);
      }
    }
  };

  const removePlayerFromTeam = (teamNumber, playerId) => {
    if (teamNumber === 1) {
      setTeam1Players(team1Players.filter(id => id !== playerId));
    } else {
      setTeam2Players(team2Players.filter(id => id !== playerId));
    }
  };

  const clearAll = () => {
    setTeam1Players([]);
    setTeam2Players([]);
    setPrediction(null);
  };

  const getAvailablePlayers = (teamNumber) => {
    const usedIds = new Set([...team1Players, ...team2Players]);
    return players.filter(p => !usedIds.has(p.id));
  };

  const getPlayerById = (id) => players.find(p => p.id === id);

  const formatWinProb = (prob) => `${(prob * 100).toFixed(1)}%`;

  if (playersLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading players..." />
      </Container>
    );
  }

  return (
    <Box position="relative">
      {/* Tactical grid background */}
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
          {/* Header */}
          <Box>
            <HStack mb={2}>
              <Icon as={FiTarget} boxSize={8} color="brand.400" />
              <Heading
                size="2xl"
                fontFamily="heading"
                textTransform="uppercase"
                letterSpacing="wider"
              >
                Lineup Predictor
              </Heading>
            </HStack>
            <Text color="gray.500" fontSize="lg">
              Manually select player lineups and get win rate predictions
            </Text>
          </Box>

          {/* Prediction Results */}
          {prediction && (
            <Card
              bg={cardBg}
              border="2px solid"
              borderColor={borderColor}
              boxShadow="0 8px 32px rgba(0, 212, 255, 0.2)"
            >
              <CardBody>
                <VStack spacing={6}>
                  <Heading size="md" fontFamily="heading" textTransform="uppercase" color="brand.400">
                    ▸ WIN PROBABILITY PREDICTION
                  </Heading>

                  <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={6} w="full">
                    {/* Team 1 Prediction */}
                    <Card bg={team1Bg} border="2px solid" borderColor="brand.500">
                      <CardBody>
                        <VStack spacing={3}>
                          <HStack>
                            <Icon as={FiShield} color="brand.400" boxSize={5} />
                            <Text fontFamily="heading" fontWeight="bold" textTransform="uppercase" color="brand.400">
                              Team 1
                            </Text>
                          </HStack>
                          <Stat textAlign="center">
                            <StatLabel fontSize="xs" color="gray.500">
                              PREDICTED WIN CHANCE
                            </StatLabel>
                            <StatNumber
                              fontSize="4xl"
                              fontFamily="heading"
                              color={prediction.team1_win_prob > 0.5 ? 'green.400' : 'gray.400'}
                            >
                              {formatWinProb(prediction.team1_win_prob)}
                            </StatNumber>
                            <StatHelpText>
                              {prediction.team1_win_prob > 0.5 ? 'Favored' : 'Underdog'}
                            </StatHelpText>
                          </Stat>
                        </VStack>
                      </CardBody>
                    </Card>

                    {/* VS Divider */}
                    <VStack justify="center">
                      <Icon as={FiZap} boxSize={12} color="accent.500" />
                      <Text fontFamily="heading" fontSize="2xl" fontWeight="black" color="accent.500">
                        VS
                      </Text>
                      <Badge colorScheme="purple" fontSize="sm">
                        Match Quality: {(prediction.quality * 100).toFixed(0)}%
                      </Badge>
                    </VStack>

                    {/* Team 2 Prediction */}
                    <Card bg={team2Bg} border="2px solid" borderColor="accent.500">
                      <CardBody>
                        <VStack spacing={3}>
                          <HStack>
                            <Icon as={FiShield} color="accent.400" boxSize={5} />
                            <Text fontFamily="heading" fontWeight="bold" textTransform="uppercase" color="accent.400">
                              Team 2
                            </Text>
                          </HStack>
                          <Stat textAlign="center">
                            <StatLabel fontSize="xs" color="gray.500">
                              PREDICTED WIN CHANCE
                            </StatLabel>
                            <StatNumber
                              fontSize="4xl"
                              fontFamily="heading"
                              color={prediction.team2_win_prob > 0.5 ? 'green.400' : 'gray.400'}
                            >
                              {formatWinProb(prediction.team2_win_prob)}
                            </StatNumber>
                            <StatHelpText>
                              {prediction.team2_win_prob > 0.5 ? 'Favored' : 'Underdog'}
                            </StatHelpText>
                          </Stat>
                        </VStack>
                      </CardBody>
                    </Card>
                  </Grid>

                  {/* Visual probability bar */}
                  <Box w="full">
                    <HStack spacing={1}>
                      <Box flex={prediction.team1_win_prob}>
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
                      <Box flex={prediction.team2_win_prob}>
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

                  {/* Additional Stats */}
                  <HStack spacing={6}>
                    <Stat textAlign="center" size="sm">
                      <StatLabel>MMR Difference</StatLabel>
                      <StatNumber>{Math.round(prediction.mmr_difference)}</StatNumber>
                    </Stat>
                    <Stat textAlign="center" size="sm">
                      <StatLabel>Match Quality</StatLabel>
                      <StatNumber>{(prediction.quality * 100).toFixed(1)}%</StatNumber>
                    </Stat>
                  </HStack>
                </VStack>
              </CardBody>
            </Card>
          )}

          {/* Team Selection */}
          <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
            {/* Team 1 */}
            <TeamSelector
              teamNumber={1}
              teamPlayers={team1Players}
              availablePlayers={getAvailablePlayers(1)}
              onAddPlayer={addPlayerToTeam}
              onRemovePlayer={removePlayerFromTeam}
              getPlayerById={getPlayerById}
              bg={team1Bg}
              borderColor="brand.500"
              iconColor="brand.400"
            />

            {/* Team 2 */}
            <TeamSelector
              teamNumber={2}
              teamPlayers={team2Players}
              availablePlayers={getAvailablePlayers(2)}
              onAddPlayer={addPlayerToTeam}
              onRemovePlayer={removePlayerFromTeam}
              getPlayerById={getPlayerById}
              bg={team2Bg}
              borderColor="accent.500"
              iconColor="accent.400"
            />
          </Grid>

          {/* Info and Actions */}
          <HStack justify="space-between">
            <Alert status="info" borderRadius="md">
              <AlertIcon />
              <Text fontSize="sm">
                Select players for both teams. Teams must have equal player counts to predict.
              </Text>
            </Alert>
            <Button
              leftIcon={<FiX />}
              variant="outline"
              colorScheme="red"
              onClick={clearAll}
              isDisabled={team1Players.length === 0 && team2Players.length === 0}
            >
              Clear All
            </Button>
          </HStack>
        </VStack>
      </Container>
    </Box>
  );
};

// Team Selector Component
const TeamSelector = ({
  teamNumber,
  teamPlayers,
  availablePlayers,
  onAddPlayer,
  onRemovePlayer,
  getPlayerById,
  bg,
  borderColor,
  iconColor,
}) => {
  const [selectedPlayerId, setSelectedPlayerId] = useState('');

  const handleAddPlayer = () => {
    if (selectedPlayerId) {
      onAddPlayer(teamNumber, selectedPlayerId);
      setSelectedPlayerId('');
    }
  };

  const totalMMR = teamPlayers.reduce((sum, id) => {
    const player = getPlayerById(id);
    return sum + (player?.mmr || 0);
  }, 0);

  const avgMMR = teamPlayers.length > 0 ? totalMMR / teamPlayers.length : 0;

  return (
    <Card bg={bg} border="2px solid" borderColor={borderColor}>
      <CardBody>
        <VStack align="stretch" spacing={4}>
          {/* Header */}
          <HStack justify="space-between">
            <HStack>
              <Icon as={FiUsers} color={iconColor} boxSize={6} />
              <Heading size="md" fontFamily="heading" textTransform="uppercase">
                Team {teamNumber}
              </Heading>
            </HStack>
            <Badge colorScheme={teamNumber === 1 ? 'cyan' : 'orange'} fontSize="md">
              {teamPlayers.length} Players
            </Badge>
          </HStack>

          {/* Average MMR */}
          {teamPlayers.length > 0 && (
            <Box p={3} bg="rgba(0, 0, 0, 0.2)" borderRadius="md">
              <HStack justify="space-between">
                <Text fontSize="sm" color="gray.400">
                  Average MMR
                </Text>
                <Text fontSize="lg" fontWeight="bold" color={iconColor}>
                  {Math.round(avgMMR)}
                </Text>
              </HStack>
            </Box>
          )}

          {/* Player List */}
          <VStack align="stretch" spacing={2} minH="200px">
            {teamPlayers.length === 0 ? (
              <Box p={8} textAlign="center" color="gray.500">
                <Icon as={FiPlus} boxSize={10} mb={2} />
                <Text>No players selected</Text>
              </Box>
            ) : (
              teamPlayers.map((playerId) => {
                const player = getPlayerById(playerId);
                if (!player) return null;

                return (
                  <HStack
                    key={playerId}
                    p={3}
                    bg="rgba(0, 0, 0, 0.2)"
                    borderRadius="md"
                    justify="space-between"
                  >
                    <VStack align="start" spacing={0} flex={1}>
                      <Text fontWeight="bold" fontFamily="heading">
                        {player.name}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        MMR: {Math.round(player.mmr)}
                      </Text>
                    </VStack>
                    <IconButton
                      icon={<FiX />}
                      size="sm"
                      variant="ghost"
                      colorScheme="red"
                      onClick={() => onRemovePlayer(teamNumber, playerId)}
                      aria-label="Remove player"
                    />
                  </HStack>
                );
              })
            )}
          </VStack>

          <Divider />

          {/* Add Player */}
          <VStack align="stretch" spacing={2}>
            <Text fontSize="sm" fontWeight="bold" color="gray.400">
              ADD PLAYER
            </Text>
            <HStack>
              <Select
                placeholder="Select player..."
                value={selectedPlayerId}
                onChange={(e) => setSelectedPlayerId(e.target.value)}
                size="sm"
              >
                {availablePlayers.map((player) => (
                  <option key={player.id} value={player.id}>
                    {player.name} (MMR: {Math.round(player.mmr)})
                  </option>
                ))}
              </Select>
              <Button
                leftIcon={<FiPlus />}
                size="sm"
                colorScheme={teamNumber === 1 ? 'cyan' : 'orange'}
                onClick={handleAddPlayer}
                isDisabled={!selectedPlayerId}
              >
                Add
              </Button>
            </HStack>
          </VStack>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default LineupPredictor;
