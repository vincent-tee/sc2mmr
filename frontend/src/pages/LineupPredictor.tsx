/**
 * Lineup Predictor - Enhanced match prediction with synergy analysis
 *
 * Features:
 * - Team selection with player search
 * - Win probability prediction via TrueSkill
 * - Team synergy and chemistry analysis
 * - Confidence indicators with visual feedback
 * - Upset potential alerts
 * - Match quality scoring
 */
import { useState, useEffect, type ChangeEvent, useCallback } from 'react';
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
  Select,
  IconButton,
  Divider,
  useColorModeValue,
  Alert,
  AlertIcon,
  Stat,
  StatNumber,
  StatHelpText,
  Progress,
  Spinner,
  Tooltip,
  Flex,
  SimpleGrid,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  FiUsers,
  FiTarget,
  FiX,
  FiPlus,
  FiZap,
  FiShield,
  FiTrendingUp,
  FiAlertTriangle,
  FiCheckCircle,
  FiActivity,
  FiHeart,
  FiAward,
} from 'react-icons/fi';
import { playersApi, teamsApi } from '../api/endpoints';
import LoadingState from '../components/LoadingState';
import TacticalBackground from '../components/common/TacticalBackground';
import type { Player, MatchPredictionResponse, SynergyInfo, TeamChemistry } from '@/types/api';
import { colors, shadows } from '../theme/tokens';

// Animation keyframes
const pulseGlow = keyframes`
  0%, 100% { box-shadow: 0 0 20px rgba(0, 212, 255, 0.4); }
  50% { box-shadow: 0 0 40px rgba(0, 212, 255, 0.8); }
`;

const upsetPulse = keyframes`
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 20px rgba(255, 179, 0, 0.4);
  }
  50% {
    transform: scale(1.02);
    box-shadow: 0 0 40px rgba(255, 179, 0, 0.8);
  }
`;

const slideInUp = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

const confidencePulse = keyframes`
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
`;

// Chemistry badge colors
const getChemistryConfig = (chemistry: TeamChemistry) => {
  switch (chemistry) {
    case 'Strong':
      return { colorScheme: 'green', icon: FiHeart, label: 'Strong Chemistry' };
    case 'Average':
      return { colorScheme: 'blue', icon: FiActivity, label: 'Average Chemistry' };
    case 'Weak':
      return { colorScheme: 'red', icon: FiAlertTriangle, label: 'Weak Chemistry' };
    default:
      return { colorScheme: 'gray', icon: FiActivity, label: 'Unknown' };
  }
};

// Confidence badge config
const getConfidenceConfig = (confidence: string) => {
  switch (confidence) {
    case 'High':
      return { colorScheme: 'green', icon: FiCheckCircle };
    case 'Medium':
      return { colorScheme: 'yellow', icon: FiActivity };
    case 'Low':
      return { colorScheme: 'orange', icon: FiAlertTriangle };
    default:
      return { colorScheme: 'gray', icon: FiActivity };
  }
};

const LineupPredictor: React.FC = () => {
  const [team1Players, setTeam1Players] = useState<number[]>([]);
  const [team2Players, setTeam2Players] = useState<number[]>([]);
  const [prediction, setPrediction] = useState<MatchPredictionResponse | null>(null);

  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.9)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');
  const team1Bg = useColorModeValue('cyan.50', 'rgba(0, 212, 255, 0.08)');
  const team2Bg = useColorModeValue('orange.50', 'rgba(255, 140, 26, 0.08)');
  const overlayBg = useColorModeValue('gray.50', 'rgba(0, 0, 0, 0.3)');

  // Fetch all players
  const { data: playersData, isLoading: playersLoading } = useQuery<Player[]>({
    queryKey: ['players-all'],
    queryFn: async () => {
      const response = await playersApi.getAll(false);
      return response.data;
    },
  });

  const players = playersData || [];

  // Prediction mutation
  const predictionMutation = useMutation({
    mutationFn: async ({ team1Ids, team2Ids }: { team1Ids: number[]; team2Ids: number[] }) => {
      const response = await teamsApi.predict(team1Ids, team2Ids);
      return response.data;
    },
    onSuccess: (data) => {
      setPrediction(data);
    },
    onError: (error) => {
      console.error('Prediction error:', error);
      setPrediction(null);
    },
  });

  // Calculate prediction when lineups change
  const calculatePrediction = useCallback(() => {
    if (team1Players.length > 0 && team2Players.length > 0) {
      predictionMutation.mutate({ team1Ids: team1Players, team2Ids: team2Players });
    } else {
      setPrediction(null);
    }
  }, [team1Players, team2Players]);

  useEffect(() => {
    const timer = setTimeout(() => {
      calculatePrediction();
    }, 300); // Debounce

    return () => clearTimeout(timer);
  }, [team1Players, team2Players, calculatePrediction]);

  const addPlayerToTeam = (teamNumber: number, playerId: string): void => {
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

  const removePlayerFromTeam = (teamNumber: number, playerId: number): void => {
    if (teamNumber === 1) {
      setTeam1Players(team1Players.filter(id => id !== playerId));
    } else {
      setTeam2Players(team2Players.filter(id => id !== playerId));
    }
  };

  const clearAll = (): void => {
    setTeam1Players([]);
    setTeam2Players([]);
    setPrediction(null);
  };

  const getAvailablePlayers = (): Player[] => {
    const usedIds = new Set([...team1Players, ...team2Players]);
    return players.filter(p => !usedIds.has(p.id)).sort((a, b) => b.mmr - a.mmr);
  };

  const getPlayerById = (id: number): Player | undefined => players.find(p => p.id === id);

  if (playersLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading players..." />
      </Container>
    );
  }

  return (
    <Box position="relative" minH="100vh">
      <TacticalBackground opacity={0.02} gridSize={60} />

      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <Box animation={`${slideInUp} 0.5s ease-out`}>
            <HStack mb={2}>
              <Icon as={FiTarget} boxSize={8} color="brand.400" />
              <Heading
                size="2xl"
                fontFamily="heading"
                textTransform="uppercase"
                letterSpacing="wider"
                bgGradient="linear(to-r, brand.400, accent.400)"
                bgClip="text"
              >
                Match Predictor
              </Heading>
            </HStack>
            <Text color="gray.500" fontSize="lg">
              Select teams and get AI-powered win predictions with synergy analysis
            </Text>
          </Box>

          {/* Prediction Results */}
          {(prediction || predictionMutation.isPending) && (
            <PredictionDisplay
              prediction={prediction}
              isLoading={predictionMutation.isPending}
              cardBg={cardBg}
              borderColor={borderColor}
              team1Bg={team1Bg}
              team2Bg={team2Bg}
            />
          )}

          {/* Team Selection */}
          <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
            <TeamSelector
              teamNumber={1}
              teamPlayers={team1Players}
              availablePlayers={getAvailablePlayers()}
              onAddPlayer={addPlayerToTeam}
              onRemovePlayer={removePlayerFromTeam}
              getPlayerById={getPlayerById}
              bg={team1Bg}
              borderColor="brand.500"
              iconColor="brand.400"
              prediction={prediction?.team_1}
            />

            <TeamSelector
              teamNumber={2}
              teamPlayers={team2Players}
              availablePlayers={getAvailablePlayers()}
              onAddPlayer={addPlayerToTeam}
              onRemovePlayer={removePlayerFromTeam}
              getPlayerById={getPlayerById}
              bg={team2Bg}
              borderColor="accent.500"
              iconColor="accent.400"
              prediction={prediction?.team_2}
            />
          </Grid>

          {/* Info and Actions */}
          <HStack justify="space-between" flexWrap="wrap" gap={4}>
            <Alert status="info" borderRadius="md" maxW="600px" bg={overlayBg}>
              <AlertIcon />
              <Text fontSize="sm">
                Select players for both teams. Predictions include win probability, team synergy, and upset potential.
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

// Prediction Display Component
interface PredictionDisplayProps {
  prediction: MatchPredictionResponse | null;
  isLoading: boolean;
  cardBg: string;
  borderColor: string;
  team1Bg: string;
  team2Bg: string;
}

const PredictionDisplay: React.FC<PredictionDisplayProps> = ({
  prediction,
  isLoading,
  cardBg,
  borderColor,
  team1Bg,
  team2Bg,
}) => {
  if (isLoading) {
    return (
      <Card
        bg={cardBg}
        border="2px solid"
        borderColor={borderColor}
        animation={`${pulseGlow} 2s ease-in-out infinite`}
      >
        <CardBody>
          <VStack spacing={4} py={8}>
            <Spinner size="xl" color="brand.400" thickness="4px" />
            <Text color="gray.400" fontFamily="heading" textTransform="uppercase" letterSpacing="wide">
              Calculating prediction...
            </Text>
          </VStack>
        </CardBody>
      </Card>
    );
  }

  if (!prediction) return null;

  const team1WinProb = prediction.team_1.win_probability;
  const team2WinProb = prediction.team_2.win_probability;
  const confidenceConfig = getConfidenceConfig(prediction.confidence);

  return (
    <Card
      bg={cardBg}
      border="2px solid"
      borderColor={prediction.upset_potential ? colors.shield[500] : borderColor}
      boxShadow={prediction.upset_potential ? shadows.accentGlow : shadows.brandGlow}
      animation={prediction.upset_potential ? `${upsetPulse} 2s ease-in-out infinite` : `${slideInUp} 0.5s ease-out`}
    >
      <CardBody>
        <VStack spacing={6}>
          {/* Header with confidence and upset alert */}
          <Flex justify="space-between" align="center" w="full" flexWrap="wrap" gap={2}>
            <HStack>
              <Icon as={FiTarget} color="brand.400" boxSize={6} />
              <Heading size="md" fontFamily="heading" textTransform="uppercase" color="brand.400">
                Match Prediction
              </Heading>
            </HStack>

            <HStack spacing={3}>
              <Tooltip label={`Prediction confidence: ${prediction.confidence}`}>
                <Badge
                  colorScheme={confidenceConfig.colorScheme}
                  fontSize="sm"
                  px={3}
                  py={1}
                  borderRadius="full"
                  animation={`${confidencePulse} 2s ease-in-out infinite`}
                >
                  <HStack spacing={1}>
                    <Icon as={confidenceConfig.icon} />
                    <Text>{prediction.confidence} Confidence</Text>
                  </HStack>
                </Badge>
              </Tooltip>

              {prediction.upset_potential && (
                <Badge
                  colorScheme="yellow"
                  fontSize="sm"
                  px={3}
                  py={1}
                  borderRadius="full"
                  animation={`${upsetPulse} 1s ease-in-out infinite`}
                >
                  <HStack spacing={1}>
                    <Icon as={FiZap} />
                    <Text>UPSET ALERT!</Text>
                  </HStack>
                </Badge>
              )}
            </HStack>
          </Flex>

          {/* Win Probability Cards */}
          <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={6} w="full">
            {/* Team 1 */}
            <Card bg={team1Bg} border="2px solid" borderColor={prediction.predicted_winner === 1 ? 'green.400' : 'brand.500'}>
              <CardBody>
                <VStack spacing={3}>
                  <HStack>
                    <Icon as={FiShield} color="brand.400" boxSize={5} />
                    <Text fontFamily="heading" fontWeight="bold" textTransform="uppercase" color="brand.400">
                      Team 1
                    </Text>
                    {prediction.predicted_winner === 1 && (
                      <Badge colorScheme="green" ml={2}>
                        <HStack spacing={1}>
                          <Icon as={FiAward} />
                          <Text>FAVORED</Text>
                        </HStack>
                      </Badge>
                    )}
                  </HStack>
                  <Stat textAlign="center">
                    <StatNumber
                      fontSize="4xl"
                      fontFamily="heading"
                      color={team1WinProb > 50 ? 'green.400' : team1WinProb < 50 ? 'red.400' : 'gray.400'}
                    >
                      {team1WinProb.toFixed(1)}%
                    </StatNumber>
                    <StatHelpText>
                      Avg MMR: {prediction.team_1.avg_mmr.toFixed(0)}
                    </StatHelpText>
                  </Stat>

                  {/* Chemistry Badge */}
                  <ChemistryBadge chemistry={prediction.team_1.team_chemistry} />
                </VStack>
              </CardBody>
            </Card>

            {/* VS Divider with Match Quality */}
            <VStack justify="center" spacing={4}>
              <Icon as={FiZap} boxSize={12} color="accent.500" />
              <Text fontFamily="heading" fontSize="2xl" fontWeight="black" color="accent.500">
                VS
              </Text>
              <VStack spacing={2}>
                <Tooltip label="How competitive this match should be (higher = more even)">
                  <Badge colorScheme="purple" fontSize="md" px={3} py={1}>
                    <HStack>
                      <Icon as={FiActivity} />
                      <Text>Quality: {(prediction.match_quality * 100).toFixed(0)}%</Text>
                    </HStack>
                  </Badge>
                </Tooltip>
              </VStack>
            </VStack>

            {/* Team 2 */}
            <Card bg={team2Bg} border="2px solid" borderColor={prediction.predicted_winner === 2 ? 'green.400' : 'accent.500'}>
              <CardBody>
                <VStack spacing={3}>
                  <HStack>
                    <Icon as={FiShield} color="accent.400" boxSize={5} />
                    <Text fontFamily="heading" fontWeight="bold" textTransform="uppercase" color="accent.400">
                      Team 2
                    </Text>
                    {prediction.predicted_winner === 2 && (
                      <Badge colorScheme="green" ml={2}>
                        <HStack spacing={1}>
                          <Icon as={FiAward} />
                          <Text>FAVORED</Text>
                        </HStack>
                      </Badge>
                    )}
                  </HStack>
                  <Stat textAlign="center">
                    <StatNumber
                      fontSize="4xl"
                      fontFamily="heading"
                      color={team2WinProb > 50 ? 'green.400' : team2WinProb < 50 ? 'red.400' : 'gray.400'}
                    >
                      {team2WinProb.toFixed(1)}%
                    </StatNumber>
                    <StatHelpText>
                      Avg MMR: {prediction.team_2.avg_mmr.toFixed(0)}
                    </StatHelpText>
                  </Stat>

                  <ChemistryBadge chemistry={prediction.team_2.team_chemistry} />
                </VStack>
              </CardBody>
            </Card>
          </Grid>

          {/* Visual probability bar */}
          <Box w="full">
            <HStack spacing={1}>
              <Box flex={team1WinProb}>
                <Progress
                  value={100}
                  size="lg"
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
              <Box flex={team2WinProb}>
                <Progress
                  value={100}
                  size="lg"
                  colorScheme="orange"
                  borderRadius="md"
                  bg="gray.700"
                  sx={{
                    '& > div': {
                      background: 'linear-gradient(90deg, rgba(255, 140, 26, 1), rgba(255, 140, 26, 0.6))',
                      boxShadow: '0 0 15px rgba(255, 140, 26, 0.6)',
                    },
                  }}
                />
              </Box>
            </HStack>
            <HStack justify="space-between" mt={1}>
              <Text fontSize="xs" color="brand.400">{team1WinProb.toFixed(1)}%</Text>
              <Text fontSize="xs" color="accent.400">{team2WinProb.toFixed(1)}%</Text>
            </HStack>
          </Box>

          {/* Prediction Factors */}
          {prediction.factors.length > 0 && (
            <Box w="full" p={4} bg="rgba(0, 0, 0, 0.2)" borderRadius="md">
              <Text fontSize="sm" fontWeight="bold" color="gray.400" mb={2} textTransform="uppercase">
                Analysis Factors
              </Text>
              <VStack align="start" spacing={1}>
                {prediction.factors.map((factor, idx) => (
                  <HStack key={idx} spacing={2}>
                    <Icon
                      as={factor.includes('⚡') ? FiZap : FiTrendingUp}
                      color={factor.includes('⚡') ? 'yellow.400' : 'gray.500'}
                      boxSize={4}
                    />
                    <Text fontSize="sm" color="gray.300">{factor}</Text>
                  </HStack>
                ))}
              </VStack>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

// Chemistry Badge Component
interface ChemistryBadgeProps {
  chemistry: TeamChemistry;
}

const ChemistryBadge: React.FC<ChemistryBadgeProps> = ({ chemistry }) => {
  const config = getChemistryConfig(chemistry);

  return (
    <Tooltip label={`Team chemistry based on historical performance together`}>
      <Badge colorScheme={config.colorScheme} fontSize="xs" px={2} py={1}>
        <HStack spacing={1}>
          <Icon as={config.icon} />
          <Text>{config.label}</Text>
        </HStack>
      </Badge>
    </Tooltip>
  );
};

// Synergy Display Component
interface SynergyDisplayProps {
  synergies: SynergyInfo[];
}

const SynergyDisplay: React.FC<SynergyDisplayProps> = ({ synergies }) => {
  if (synergies.length === 0) {
    return (
      <Text fontSize="xs" color="gray.500" fontStyle="italic">
        No synergy data available
      </Text>
    );
  }

  return (
    <VStack align="stretch" spacing={2}>
      {synergies.slice(0, 3).map((syn, idx) => (
        <HStack key={idx} justify="space-between" p={2} bg="rgba(0, 0, 0, 0.2)" borderRadius="sm">
          <Text fontSize="xs" color="gray.300">
            {syn.player1_name} + {syn.player2_name}
          </Text>
          <HStack spacing={2}>
            <Badge colorScheme={syn.win_rate >= 50 ? 'green' : 'red'} fontSize="xs">
              {syn.win_rate.toFixed(0)}% WR
            </Badge>
            <Text fontSize="xs" color="gray.500">
              ({syn.games_together} games)
            </Text>
          </HStack>
        </HStack>
      ))}
    </VStack>
  );
};

// Team Selector Component
interface TeamSelectorProps {
  teamNumber: number;
  teamPlayers: number[];
  availablePlayers: Player[];
  onAddPlayer: (teamNumber: number, playerId: string) => void;
  onRemovePlayer: (teamNumber: number, playerId: number) => void;
  getPlayerById: (id: number) => Player | undefined;
  bg: string;
  borderColor: string;
  iconColor: string;
  prediction?: MatchPredictionResponse['team_1'];
}

const TeamSelector: React.FC<TeamSelectorProps> = ({
  teamNumber,
  teamPlayers,
  availablePlayers,
  onAddPlayer,
  onRemovePlayer,
  getPlayerById,
  bg,
  borderColor,
  iconColor,
  prediction,
}) => {
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>('');

  const handleAddPlayer = (): void => {
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

          {/* Stats Row */}
          {teamPlayers.length > 0 && (
            <SimpleGrid columns={2} spacing={3}>
              <Box p={3} bg="rgba(0, 0, 0, 0.2)" borderRadius="md">
                <Text fontSize="xs" color="gray.500" textTransform="uppercase">Avg MMR</Text>
                <Text fontSize="xl" fontWeight="bold" color={iconColor}>
                  {Math.round(avgMMR)}
                </Text>
              </Box>
              {prediction && (
                <Box p={3} bg="rgba(0, 0, 0, 0.2)" borderRadius="md">
                  <Text fontSize="xs" color="gray.500" textTransform="uppercase">Synergy</Text>
                  <Text fontSize="xl" fontWeight="bold" color={iconColor}>
                    {prediction.avg_synergy_score.toFixed(1)}
                  </Text>
                </Box>
              )}
            </SimpleGrid>
          )}

          {/* Synergy Info */}
          {prediction && prediction.synergies.length > 0 && (
            <Box>
              <Text fontSize="xs" fontWeight="bold" color="gray.500" mb={2} textTransform="uppercase">
                Team Synergies
              </Text>
              <SynergyDisplay synergies={prediction.synergies} />
            </Box>
          )}

          {/* Player List */}
          <VStack align="stretch" spacing={2} minH="150px">
            {teamPlayers.length === 0 ? (
              <Box p={6} textAlign="center" color="gray.500">
                <Icon as={FiPlus} boxSize={8} mb={2} />
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
                    transition="all 0.2s"
                    _hover={{ bg: 'rgba(0, 0, 0, 0.3)' }}
                  >
                    <VStack align="start" spacing={0} flex={1}>
                      <Text fontWeight="bold" fontFamily="heading">
                        {player.name}
                      </Text>
                      <HStack spacing={2}>
                        <Text fontSize="xs" color="gray.500">
                          MMR: {Math.round(player.mmr)}
                        </Text>
                        <Badge
                          colorScheme={player.win_rate >= 50 ? 'green' : 'red'}
                          fontSize="xs"
                          variant="subtle"
                        >
                          {(player.win_rate * 100).toFixed(0)}% WR
                        </Badge>
                      </HStack>
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
            <Text fontSize="sm" fontWeight="bold" color="gray.400" textTransform="uppercase">
              Add Player
            </Text>
            <HStack>
              <Select
                placeholder="Select player..."
                value={selectedPlayerId}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedPlayerId(e.target.value)}
                size="sm"
                bg="rgba(0, 0, 0, 0.2)"
              >
                {availablePlayers.map((player) => (
                  <option key={player.id} value={player.id}>
                    {player.name} ({Math.round(player.mmr)} MMR)
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
