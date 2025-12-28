/**
 * Lineup Predictor - Enhanced match prediction with synergy analysis
 *
 * Features:
 * - Team selection with player search
 * - Win probability prediction
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
  Button,
  Badge,
  Icon,
  Grid,
  Select,
  IconButton,
  Divider,
  Alert,
  AlertIcon,
  Stat,
  StatNumber,
  StatHelpText,
  Progress,
  Tooltip,
  Flex,
  SimpleGrid,
  Circle,
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
import type { Player, MatchPredictionResponse, SynergyInfo, TeamChemistry } from '@/types/api';

// Design tokens
const cardBg = 'space.800';
const borderColor = 'space.900';
const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';
const team1Glow = '0 0 15px rgba(0, 212, 255, 0.4)';
const team2Glow = '0 0 15px rgba(255, 140, 26, 0.4)';

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

  const team1Bg = 'rgba(0, 212, 255, 0.08)';
  const team2Bg = 'rgba(255, 140, 26, 0.08)';
  const overlayBg = 'rgba(0, 0, 0, 0.3)';

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
    <Box position="relative" minH="100vh" bg="space.900">
      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          <Box animation={`${slideInUp} 0.5s ease-out`} textAlign="center">
            <Heading
              size="2xl"
              fontFamily="heading"
              fontWeight="black"
              letterSpacing="wider"
              color="brand.400"
              mb={2}
            >
              <Text as="span" className="emoji-font">🎯</Text> Match Predictor
            </Heading>
            <Text color="gray.400" fontSize="lg">
              Assemble lineups to calculate win probability and synergy
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
}) => {
  if (isLoading) {
    return (
      <Box
        bg={cardBg}
        borderRadius="xl"
        border="3px solid"
        borderColor={borderColor}
        boxShadow={brandShadow}
        p={8}
      >
        <LoadingState message="Calculating win probabilities..." />
      </Box>
    );
  }

  if (!prediction) return null;

  const team1WinProb = prediction.team_1.win_probability;
  const team2WinProb = prediction.team_2.win_probability;
  const confidenceConfig = getConfidenceConfig(prediction.confidence);

  return (
    <Box
      bg={cardBg}
      borderRadius="xl"
      border="3px solid"
      borderColor={prediction.upset_potential ? 'yellow.500' : borderColor}
      boxShadow={prediction.upset_potential ? '0 0 20px rgba(255, 179, 0, 0.4)' : brandShadow}
      p={6}
      animation={prediction.upset_potential ? `${upsetPulse} 2s ease-in-out infinite` : `${slideInUp} 0.5s ease-out`}
    >
      <VStack spacing={6}>
        {/* Header with confidence and upset alert */}
        <Flex justify="space-between" align="center" w="full" flexWrap="wrap" gap={2}>
          <HStack>
            <Icon as={FiTarget} color="brand.400" boxSize={6} />
            <Heading size="md" fontFamily="heading" textTransform="uppercase" color="brand.400" letterSpacing="wide">
              Strategic Forecast
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
                variant="solid"
                fontSize="sm"
                px={3}
                py={1}
                borderRadius="full"
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
          <Box
            bg="space.900"
            p={5}
            borderRadius="xl"
            border="2px solid"
            borderColor={prediction.predicted_winner === 1 ? 'brand.400' : 'space.700'}
            boxShadow={prediction.predicted_winner === 1 ? team1Glow : 'none'}
          >
            <VStack spacing={3}>
              <HStack>
                <Icon as={FiShield} color="brand.400" boxSize={5} />
                <Text fontFamily="heading" fontWeight="bold" textTransform="uppercase" color="brand.400" letterSpacing="wide">
                  Squad Alpha
                </Text>
                {prediction.predicted_winner === 1 && (
                  <Badge colorScheme="green" ml={2} variant="solid">
                    FAVORED
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
                <StatHelpText fontFamily="mono" color="gray.500">
                  Total MMR: {Math.round(prediction.team_1.total_mmr)}
                </StatHelpText>
              </Stat>

              <ChemistryBadge chemistry={prediction.team_1.team_chemistry} />
            </VStack>
          </Box>

          {/* VS Divider with Match Quality */}
          <VStack justify="center" spacing={2}>
            <Circle size="12" bg="space.900" border="2px solid" borderColor="accent.500">
              <Icon as={FiZap} boxSize={6} color="accent.500" />
            </Circle>
            <Text fontFamily="heading" fontSize="2xl" fontWeight="black" color="accent.500">
              VS
            </Text>
            <VStack spacing={2}>
              <Tooltip label="Match Quality (higher = more even)">
                <Badge colorScheme="purple" fontSize="sm" px={3} py={1} borderRadius="full" variant="outline">
                   Quality: {(prediction.match_quality * 100).toFixed(0)}%
                </Badge>
              </Tooltip>
            </VStack>
          </VStack>

          {/* Team 2 */}
          <Box
            bg="space.900"
            p={5}
            borderRadius="xl"
            border="2px solid"
            borderColor={prediction.predicted_winner === 2 ? 'accent.400' : 'space.700'}
            boxShadow={prediction.predicted_winner === 2 ? team2Glow : 'none'}
          >
            <VStack spacing={3}>
              <HStack>
                <Icon as={FiShield} color="accent.400" boxSize={5} />
                <Text fontFamily="heading" fontWeight="bold" textTransform="uppercase" color="accent.400" letterSpacing="wide">
                  Squad Bravo
                </Text>
                {prediction.predicted_winner === 2 && (
                  <Badge colorScheme="green" ml={2} variant="solid">
                    FAVORED
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
                <StatHelpText fontFamily="mono" color="gray.500">
                  Total MMR: {Math.round(prediction.team_2.total_mmr)}
                </StatHelpText>
              </Stat>

              <ChemistryBadge chemistry={prediction.team_2.team_chemistry} />
            </VStack>
          </Box>
        </Grid>

        {/* Visual probability bar */}
        <Box w="full">
          <HStack spacing={1}>
            <Box flex={team1WinProb / 100}>
              <Progress
                value={100}
                size="md"
                colorScheme="cyan"
                borderRadius="full"
                bg="space.900"
              />
            </Box>
            <Box flex={team2WinProb / 100}>
              <Progress
                value={100}
                size="md"
                colorScheme="orange"
                borderRadius="full"
                bg="space.900"
              />
            </Box>
          </HStack>
          <HStack justify="space-between" mt={2} px={1}>
            <Text fontSize="xs" fontWeight="bold" color="brand.400" fontFamily="mono">{team1WinProb.toFixed(1)}%</Text>
            <Text fontSize="xs" fontWeight="bold" color="accent.400" fontFamily="mono">{team2WinProb.toFixed(1)}%</Text>
          </HStack>
        </Box>

        {/* Prediction Factors */}
        {prediction.factors.length > 0 && (
          <Box w="full" p={5} bg="rgba(0, 0, 0, 0.4)" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100">
            <HStack mb={3}>
                <Icon as={FiActivity} color="gray.500" />
                <Text fontSize="xs" fontWeight="black" color="gray.500" textTransform="uppercase" letterSpacing="widest">
                Forecast Analysis
                </Text>
            </HStack>
            <VStack align="start" spacing={2}>
              {prediction.factors.map((factor, idx) => (
                <HStack key={idx} spacing={3}>
                  <Icon
                    as={factor.includes('⚡') ? FiZap : FiTrendingUp}
                    color={factor.includes('⚡') ? 'yellow.400' : 'gray.500'}
                    boxSize={3}
                  />
                  <Text fontSize="sm" color="gray.300" fontWeight="medium">{factor}</Text>
                </HStack>
              ))}
            </VStack>
          </Box>
        )}
      </VStack>
    </Box>
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
    return sum + (player?.recency_weighted_mmr || player?.mmr || 0);
  }, 0);

  const avgMMR = teamPlayers.length > 0 ? totalMMR / teamPlayers.length : 0;

  return (
    <Box
      bg={cardBg}
      borderRadius="xl"
      border="3px solid"
      borderColor={borderColor}
      boxShadow={brandShadow}
      p={6}
    >
      <VStack align="stretch" spacing={5}>
        {/* Header */}
        <HStack justify="space-between">
          <HStack spacing={3}>
            <Icon as={FiUsers} color={iconColor} boxSize={6} />
            <Heading size="md" fontFamily="heading" textTransform="uppercase" letterSpacing="wider" color="gray.200">
              Squad {teamNumber === 1 ? 'Alpha' : 'Bravo'}
            </Heading>
          </HStack>
          <Badge bg={teamNumber === 1 ? 'cyan.500' : 'orange.500'} color="white" fontSize="sm" px={3} py={1} borderRadius="full">
            {teamPlayers.length} Active
          </Badge>
        </HStack>

        {/* Stats Row */}
        {teamPlayers.length > 0 && (
          <SimpleGrid columns={2} spacing={3}>
            <Box p={3} bg="space.900" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100">
              <Text fontSize="10px" fontWeight="black" color="gray.500" textTransform="uppercase" letterSpacing="widest" mb={1}>Total Power</Text>
              <Text fontSize="xl" fontWeight="black" color={iconColor} fontFamily="mono">
                {Math.round(totalMMR)}
              </Text>
            </Box>
            {prediction && (
              <Box p={3} bg="space.900" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100">
                <Text fontSize="10px" fontWeight="black" color="gray.500" textTransform="uppercase" letterSpacing="widest" mb={1}>Synergy Score</Text>
                <Text fontSize="xl" fontWeight="black" color={iconColor} fontFamily="mono">
                  {prediction.avg_synergy_score.toFixed(1)}
                </Text>
              </Box>
            )}
          </SimpleGrid>
        )}

        {/* Synergy Info */}
        {prediction && prediction.synergies.length > 0 && (
          <Box>
            <Text fontSize="xs" fontWeight="black" color="gray.500" mb={2} textTransform="uppercase" letterSpacing="widest">
              Team Synergies
            </Text>
            <SynergyDisplay synergies={prediction.synergies} />
          </Box>
        )}

        {/* Player List */}
        <VStack align="stretch" spacing={2} minH="120px">
          {teamPlayers.length === 0 ? (
            <Box
              p={8}
              textAlign="center"
              color="gray.600"
              border="2px dashed"
              borderColor="space.700"
              borderRadius="xl"
            >
              <Icon as={FiPlus} boxSize={8} mb={2} opacity={0.5} />
              <Text fontSize="sm" fontFamily="heading">Draft players to this squad</Text>
            </Box>
          ) : (
            teamPlayers.map((playerId) => {
              const player = getPlayerById(playerId);
              if (!player) return null;

              return (
                <HStack
                  key={playerId}
                  p={3}
                  bg="space.900"
                  borderRadius="xl"
                  border="1px solid"
                  borderColor="whiteAlpha.100"
                  justify="space-between"
                  transition="all 0.2s"
                  _hover={{ borderColor: iconColor }}
                >
                  <VStack align="start" spacing={0} flex={1}>
                    <Text fontWeight="bold" color="gray.200">
                      {player.name}
                    </Text>
                    <HStack spacing={2}>
                      <Text fontSize="xs" color="gray.500" fontFamily="mono">
                        {Math.round(player.recency_weighted_mmr || player.mmr)} MMR
                      </Text>
                      <Badge
                        colorScheme={player.win_rate >= 0.5 ? 'green' : 'red'}
                        fontSize="10px"
                        variant="subtle"
                        borderRadius="sm"
                      >
                        {(player.win_rate * 100).toFixed(0)}% WR
                      </Badge>
                    </HStack>
                  </VStack>
                  <IconButton
                    icon={<FiX />}
                    size="xs"
                    variant="ghost"
                    colorScheme="red"
                    onClick={() => onRemovePlayer(teamNumber, playerId)}
                    aria-label="Remove player"
                    borderRadius="full"
                  />
                </HStack>
              );
            })
          )}
        </VStack>

        <Divider borderColor="whiteAlpha.100" />

        {/* Add Player */}
        <VStack align="stretch" spacing={3}>
          <Text fontSize="xs" fontWeight="black" color="gray.500" textTransform="uppercase" letterSpacing="widest">
            Recruit Player
          </Text>
          <HStack>
            <Select
              placeholder="Search squad..."
              value={selectedPlayerId}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedPlayerId(e.target.value)}
              size="sm"
              bg="space.900"
              borderRadius="md"
              borderColor="space.700"
              fontFamily="heading"
              _hover={{ borderColor: iconColor }}
            >
              {availablePlayers.map((player) => (
                <option key={player.id} value={player.id} style={{ background: '#1A202C' }}>
                  {player.name} ({Math.round(player.recency_weighted_mmr || player.mmr)})
                </option>
              ))}
            </Select>
            <Button
              leftIcon={<FiPlus />}
              size="sm"
              bg={teamNumber === 1 ? 'brand.500' : 'accent.500'}
              color={teamNumber === 1 ? 'white' : 'space.900'}
              onClick={handleAddPlayer}
              isDisabled={!selectedPlayerId}
              _hover={{ bg: teamNumber === 1 ? 'brand.600' : 'accent.400' }}
              fontFamily="heading"
              px={6}
            >
              Draft
            </Button>
          </HStack>
        </VStack>
      </VStack>
    </Box>
  );
};
  );
};

export default LineupPredictor;
