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
import { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
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
  IconButton,
  Divider,
  Alert,
  AlertIcon,
  CloseButton,
  Stat,
  StatNumber,
  StatHelpText,
  Progress,
  Tooltip,
  Flex,
  SimpleGrid,
  Circle,
  ButtonGroup,
  Input,
  InputGroup,
  InputLeftElement,
  Collapse,
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
  FiShuffle,
  FiRepeat,
  FiArrowRight,
  FiArrowLeft,
  FiSearch,
  FiChevronDown,
} from 'react-icons/fi';
import { playersApi, teamsApi } from '../api/endpoints';
import apiClient from '../api/client';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import PlayerCard from '@/components/PlayerCard';
import AnimatedNumber from '@/components/AnimatedNumber';
import RosterSelector from './TeamGenerator/TeamSelector';
import type { Player, MatchPredictionResponse, SynergyInfo, TeamChemistry } from '@/types/api';

interface DraftPlayerRef {
  id: number;
  name: string;
  mmr: number;
  unified_mmr: number | null;
  mu: number;
  sigma: number;
}

interface DraftPick {
  pick_number: number;
  team_index: number;
  role: 'captain' | 'pick';
  player: DraftPlayerRef;
}

interface DraftApiResponse {
  teams: { players: DraftPlayerRef[] }[];
  draft_log: DraftPick[];
}

interface SwapSuggestion {
  player_out_of_team_1: DraftPlayerRef;
  player_out_of_team_2: DraftPlayerRef;
  new_match_quality: number;
  new_win_probability: number;
  quality_delta: number;
}

interface SuggestSwapsApiResponse {
  current_match_quality: number;
  current_win_probability: number;
  suggestions: SwapSuggestion[];
}

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

  // Pre-fill from a specific split passed via navigation state, e.g. the
  // "Fine-tune this split" button on the Team Balancer results page.
  const location = useLocation();
  const [loadedFromBalance, setLoadedFromBalance] = useState(false);
  useEffect(() => {
    const navState = location.state as { initialTeam1Ids?: number[]; initialTeam2Ids?: number[] } | null;
    if (navState?.initialTeam1Ids && navState?.initialTeam2Ids) {
      setTeam1Players(navState.initialTeam1Ids);
      setTeam2Players(navState.initialTeam2Ids);
      setLoadedFromBalance(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Captain's Draft state - an alternative way to populate team1Players/
  // team2Players, alongside the existing manual add/remove controls below
  // (which double as the "manual override" once a draft has run).
  const [showDraftSetup, setShowDraftSetup] = useState(false);
  const [draftPool, setDraftPool] = useState<Player[]>([]);
  const [captain1Id, setCaptain1Id] = useState<number | null>(null);
  const [captain2Id, setCaptain2Id] = useState<number | null>(null);
  const [draftStarted, setDraftStarted] = useState(false);

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

  // Match TeamGenerator's convention: 0-game players are ghost/manual
  // entries with no real history, not real roster candidates.
  const players = (playersData || []).filter((p) => p.total_games > 0);

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

  const swapTeams = (): void => {
    setTeam1Players(team2Players);
    setTeam2Players(team1Players);
  };

  const movePlayerToOtherTeam = (fromTeam: number, playerId: number): void => {
    if (fromTeam === 1) {
      setTeam1Players((prev) => prev.filter((id) => id !== playerId));
      setTeam2Players((prev) => [...prev, playerId]);
    } else {
      setTeam2Players((prev) => prev.filter((id) => id !== playerId));
      setTeam1Players((prev) => [...prev, playerId]);
    }
  };

  const getAvailablePlayers = (): Player[] => {
    const usedIds = new Set([...team1Players, ...team2Players]);
    return players.filter(p => !usedIds.has(p.id)).sort((a, b) => b.mmr - a.mmr);
  };

  const getPlayerById = (id: number): Player | undefined => players.find(p => p.id === id);

  // --- Captain's Draft ---

  const resetDraft = (): void => {
    setShowDraftSetup(false);
    setDraftPool([]);
    setCaptain1Id(null);
    setCaptain2Id(null);
    setDraftStarted(false);
  };

  const remainingDraftPool = draftPool.filter(
    (p) => !team1Players.includes(p.id) && !team2Players.includes(p.id)
  );

  // Whose turn it is, derived (not tracked as separate state that can drift)
  // to exactly match the backend's snake_draft pattern: forward order on
  // even rounds, reversed on odd rounds. Verified against
  // TeamBalancer.snake_draft: [1,2,2,1,1,2,2,1,...] for 2 teams, not plain
  // alternation - plain alternation gives the second-picking team a
  // material MMR-sum disadvantage over many rounds.
  const picksSoFar = draftStarted ? team1Players.length + team2Players.length - 2 : 0;
  const roundNum = Math.floor(picksSoFar / 2);
  const positionInRound = picksSoFar % 2;
  const roundOrder: [1, 2] | [2, 1] = roundNum % 2 === 0 ? [1, 2] : [2, 1];
  const currentTurnTeam: 1 | 2 = roundOrder[positionInRound];

  const startDraft = (): void => {
    if (!captain1Id || !captain2Id) return;
    setTeam1Players([captain1Id]);
    setTeam2Players([captain2Id]);
    setDraftStarted(true);
  };

  const pickPlayerInDraft = (playerId: number): void => {
    if (currentTurnTeam === 1) {
      setTeam1Players((prev) => [...prev, playerId]);
    } else {
      setTeam2Players((prev) => [...prev, playerId]);
    }
  };

  const autoGenerateMutation = useMutation({
    mutationFn: async (playerIds: number[]) => {
      const response = await apiClient.post<DraftApiResponse>('/teams/draft', {
        player_ids: playerIds,
        custom_players: [],
        num_teams: 2,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setTeam1Players(data.teams[0].players.map((p) => p.id));
      setTeam2Players(data.teams[1].players.map((p) => p.id));
      setDraftStarted(true);
    },
  });

  const autoGenerateFully = (): void => {
    if (draftPool.length < 2) return;
    autoGenerateMutation.mutate(draftPool.map((p) => p.id));
  };

  // --- Suggested Swaps (mutations) ---

  const swapSuggestionsMutation = useMutation({
    mutationFn: async ({ team1Ids, team2Ids }: { team1Ids: number[]; team2Ids: number[] }) => {
      const response = await apiClient.post<SuggestSwapsApiResponse>('/teams/suggest-swaps', {
        team_1_ids: team1Ids,
        team_2_ids: team2Ids,
        custom_players: [],
        top_n: 3,
      });
      return response.data;
    },
  });

  useEffect(() => {
    if (team1Players.length >= 2 && team2Players.length >= 2) {
      const timer = setTimeout(() => {
        swapSuggestionsMutation.mutate({ team1Ids: team1Players, team2Ids: team2Players });
      }, 400);
      return () => clearTimeout(timer);
    }
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [team1Players, team2Players]);

  const applySwap = (suggestion: SwapSuggestion): void => {
    const outOf1 = suggestion.player_out_of_team_1.id;
    const outOf2 = suggestion.player_out_of_team_2.id;
    setTeam1Players((prev) => prev.filter((id) => id !== outOf1).concat(outOf2));
    setTeam2Players((prev) => prev.filter((id) => id !== outOf2).concat(outOf1));
  };

  if (playersLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading players..." />
      </Container>
    );
  }

  return (
    <Box position="relative" minH="100vh" pb={16}>
      <PageHeader
        kicker="Crystal Ball"
        title="Match [Predictor]"
        description="Assemble two lineups and see who the model thinks takes it."
      />
      <Container maxW="container.xl" pt={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">

          {/* Acknowledges arriving here via "Fine-tune this split" from the
              Team Balancer, so the pre-filled teams don't look unexplained. */}
          {loadedFromBalance && (
            <Alert status="success" variant="left-accent" borderRadius="md" pr={10} position="relative">
              <AlertIcon />
              <Text fontSize="sm">
                Loaded this split from Team Balancer&apos;s suggestions - fine-tune it below, or{' '}
                <Text
                  as="span"
                  fontWeight="bold"
                  textDecoration="underline"
                  cursor="pointer"
                  onClick={clearAll}
                >
                  clear it
                </Text>{' '}
                to start fresh.
              </Text>
              <CloseButton
                position="absolute"
                right="8px"
                top="8px"
                size="sm"
                aria-label="Dismiss"
                onClick={() => setLoadedFromBalance(false)}
              />
            </Alert>
          )}

          {/* Captain's Draft - alternative way to fill the two lineups below */}
          {!showDraftSetup ? (
            <Button
              leftIcon={<FiShuffle />}
              variant="outline"
              alignSelf="flex-start"
              onClick={() => setShowDraftSetup(true)}
              fontFamily="heading"
            >
              Need a roster? Try Captain&apos;s Draft
            </Button>
          ) : (
            <Box bg={cardBg} borderRadius="xl" border="3px solid" borderColor={borderColor} boxShadow={brandShadow} p={6}>
              <HStack justify="space-between" mb={5}>
                <HStack spacing={3}>
                  <Icon as={FiShuffle} color="brand.400" boxSize={6} />
                  <Heading size="md" fontFamily="heading" textTransform="uppercase" letterSpacing="wide" color="brand.400">
                    Captain&apos;s Draft
                  </Heading>
                </HStack>
                <Button size="sm" variant="ghost" leftIcon={<FiX />} onClick={resetDraft}>
                  Close
                </Button>
              </HStack>

              {!draftStarted ? (
                <VStack align="stretch" spacing={5}>
                  <Text fontSize="sm" color="gray.400">
                    Pick tonight&apos;s roster, choose two captains, then either draft picks
                    one at a time or generate the whole thing instantly.
                  </Text>
                  <RosterSelector
                    players={players}
                    selectedPlayers={draftPool}
                    onTogglePlayer={(player) => {
                      setDraftPool((prev) =>
                        prev.some((p) => p.id === player.id)
                          ? prev.filter((p) => p.id !== player.id)
                          : [...prev, player]
                      );
                      if (captain1Id === player.id) setCaptain1Id(null);
                      if (captain2Id === player.id) setCaptain2Id(null);
                    }}
                    onSelectAll={() => setDraftPool(players)}
                    onClearSelection={() => {
                      setDraftPool([]);
                      setCaptain1Id(null);
                      setCaptain2Id(null);
                    }}
                    onAddGuest={() => {}}
                  />

                  {draftPool.length >= 2 && (
                    <Box>
                      <Text fontSize="xs" fontWeight="bold" color="gray.500" textTransform="uppercase" letterSpacing="wide" mb={3}>
                        Pick two captains
                      </Text>
                      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={2}>
                        {[...draftPool].sort((a, b) => b.mmr - a.mmr).map((p) => {
                          const isCaptain1 = captain1Id === p.id;
                          const isCaptain2 = captain2Id === p.id;
                          return (
                            <Button
                              key={p.id}
                              size="sm"
                              variant={isCaptain1 || isCaptain2 ? 'solid' : 'outline'}
                              colorScheme={isCaptain1 ? 'cyan' : isCaptain2 ? 'orange' : 'gray'}
                              onClick={() => {
                                if (isCaptain1) { setCaptain1Id(null); return; }
                                if (isCaptain2) { setCaptain2Id(null); return; }
                                if (!captain1Id) { setCaptain1Id(p.id); return; }
                                if (!captain2Id) { setCaptain2Id(p.id); return; }
                              }}
                            >
                              {p.name}
                            </Button>
                          );
                        })}
                      </SimpleGrid>
                    </Box>
                  )}

                  <ButtonGroup>
                    <Button
                      leftIcon={<FiUsers />}
                      colorScheme="brand"
                      isDisabled={!captain1Id || !captain2Id}
                      onClick={startDraft}
                    >
                      Start Manual Draft
                    </Button>
                    <Button
                      leftIcon={<FiZap />}
                      variant="outline"
                      isDisabled={draftPool.length < 2}
                      isLoading={autoGenerateMutation.isPending}
                      onClick={autoGenerateFully}
                    >
                      Auto-Generate Fully
                    </Button>
                  </ButtonGroup>
                </VStack>
              ) : (
                remainingDraftPool.length > 0 && (
                  <VStack align="stretch" spacing={4}>
                    <HStack justify="space-between">
                      <Badge colorScheme={currentTurnTeam === 1 ? 'cyan' : 'orange'} fontSize="sm" px={3} py={1}>
                        {currentTurnTeam === 1 ? 'Squad Alpha' : 'Squad Bravo'}&apos;s pick
                      </Badge>
                      <Button size="xs" variant="ghost" leftIcon={<FiZap />} onClick={autoGenerateFully} isLoading={autoGenerateMutation.isPending}>
                        Auto-complete rest
                      </Button>
                    </HStack>
                    <SimpleGrid columns={{ base: 2, md: 4 }} spacing={2}>
                      {remainingDraftPool
                        .sort((a, b) => b.mmr - a.mmr)
                        .map((p) => (
                          <Button
                            key={p.id}
                            size="sm"
                            variant="outline"
                            onClick={() => pickPlayerInDraft(p.id)}
                          >
                            {p.name} <Text as="span" color="gray.500" ml={1} fontSize="xs">{Math.round(p.mmr)}</Text>
                          </Button>
                        ))}
                    </SimpleGrid>
                  </VStack>
                )
              )}
            </Box>
          )}

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
          {(team1Players.length > 0 || team2Players.length > 0) && (
            <Flex justify="center">
              <Tooltip label="Flip Squad Alpha and Squad Bravo's entire rosters">
                <Button
                  leftIcon={<FiRepeat />}
                  variant="outline"
                  size="sm"
                  onClick={swapTeams}
                  fontFamily="heading"
                >
                  Swap Teams
                </Button>
              </Tooltip>
            </Flex>
          )}
          <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
            <TeamSelector
              teamNumber={1}
              teamPlayers={team1Players}
              availablePlayers={getAvailablePlayers()}
              onAddPlayer={addPlayerToTeam}
              onRemovePlayer={removePlayerFromTeam}
              onMovePlayer={movePlayerToOtherTeam}
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
              onMovePlayer={movePlayerToOtherTeam}
              getPlayerById={getPlayerById}
              bg={team2Bg}
              borderColor="accent.500"
              iconColor="accent.400"
              prediction={prediction?.team_2}
            />
          </Grid>

          {/* Suggested Swaps - local improvements around the current split,
              using the same proven TrueSkill scoring as the main balancer
              (not the unproven ML predictor). Works regardless of how the
              teams above were populated: draft, auto-generate, or fully
              manual - this IS the manual-override surface. */}
          {swapSuggestionsMutation.data && swapSuggestionsMutation.data.suggestions.length > 0 && (
            <Box bg={cardBg} borderRadius="xl" border="3px solid" borderColor={borderColor} boxShadow={brandShadow} p={6}>
              <HStack spacing={3} mb={4}>
                <Icon as={FiRepeat} color="accent.400" boxSize={5} />
                <Heading size="sm" fontFamily="heading" textTransform="uppercase" letterSpacing="wide" color="accent.400">
                  Suggested Swaps
                </Heading>
                <Text fontSize="xs" color="gray.500">
                  current match quality {(swapSuggestionsMutation.data.current_match_quality * 100).toFixed(0)}%
                </Text>
              </HStack>
              <VStack align="stretch" spacing={2}>
                {swapSuggestionsMutation.data.suggestions
                  .filter((s) => s.quality_delta > 0.01)
                  .map((s, i) => (
                    <HStack key={i} justify="space-between" p={3} bg="whiteAlpha.50" borderRadius="md">
                      <Text fontSize="sm" color="gray.200">
                        Swap <Text as="span" fontWeight="700" color="cyan.300">{s.player_out_of_team_1.name}</Text>
                        {' '}&harr;{' '}
                        <Text as="span" fontWeight="700" color="orange.300">{s.player_out_of_team_2.name}</Text>
                      </Text>
                      <HStack spacing={3}>
                        <Text fontSize="xs" color="green.400" fontFamily="mono">
                          quality +{(s.quality_delta * 100).toFixed(0)}%
                        </Text>
                        <Button size="xs" colorScheme="brand" onClick={() => applySwap(s)}>
                          Apply
                        </Button>
                      </HStack>
                    </HStack>
                  ))}
                {swapSuggestionsMutation.data.suggestions.every((s) => s.quality_delta <= 0.01) && (
                  <Text fontSize="sm" color="gray.500" textAlign="center" py={2}>
                    This split already looks solid - no swap improves it meaningfully.
                  </Text>
                )}
              </VStack>
            </Box>
          )}

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
  // Replays the VS circle's glow flash whenever the actual numbers change
  // (not on every re-render), by remounting just that one small element.
  const [pulseKey, setPulseKey] = useState(0);
  const lastSignatureRef = useRef<string | null>(null);
  useEffect(() => {
    if (!prediction) return;
    const signature = `${prediction.team_1.win_probability}-${prediction.team_2.win_probability}`;
    if (lastSignatureRef.current !== null && lastSignatureRef.current !== signature) {
      setPulseKey((k) => k + 1);
    }
    lastSignatureRef.current = signature;
  }, [prediction]);

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
                  <AnimatedNumber value={team1WinProb} decimals={1} suffix="%" />
                </StatNumber>
                <StatHelpText fontFamily="mono" color="gray.500">
                  Total MMR: <AnimatedNumber value={prediction.team_1.total_mmr} decimals={0} />
                </StatHelpText>
              </Stat>

              <ChemistryBadge chemistry={prediction.team_1.team_chemistry} />
            </VStack>
          </Box>

          {/* VS Divider with Match Quality */}
          <VStack justify="center" spacing={2}>
            <Circle
              key={pulseKey}
              size="12"
              bg="space.900"
              border="2px solid"
              borderColor="accent.500"
              animation={`${pulseGlow} 0.6s ease-out`}
            >
              <Icon as={FiZap} boxSize={6} color="accent.500" />
            </Circle>
            <Text fontFamily="heading" fontSize="2xl" fontWeight="black" color="accent.500">
              VS
            </Text>
            <VStack spacing={2}>
              <Tooltip label="Match Quality (higher = more even)">
                <Badge colorScheme="purple" fontSize="sm" px={3} py={1} borderRadius="full" variant="outline">
                   Quality: <AnimatedNumber value={prediction.match_quality * 100} decimals={0} suffix="%" />
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
                  <AnimatedNumber value={team2WinProb} decimals={1} suffix="%" />
                </StatNumber>
                <StatHelpText fontFamily="mono" color="gray.500">
                  Total MMR: <AnimatedNumber value={prediction.team_2.total_mmr} decimals={0} />
                </StatHelpText>
              </Stat>

              <ChemistryBadge chemistry={prediction.team_2.team_chemistry} />
            </VStack>
          </Box>
        </Grid>

        {/* Visual probability bar */}
        <Box w="full">
          <HStack spacing={1}>
            <Box flex={team1WinProb / 100} transition="flex 0.6s ease-out">
              <Progress
                value={100}
                size="md"
                colorScheme="cyan"
                borderRadius="full"
                bg="space.900"
              />
            </Box>
            <Box flex={team2WinProb / 100} transition="flex 0.6s ease-out">
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
            <Text fontSize="xs" fontWeight="bold" color="brand.400" fontFamily="mono">
              <AnimatedNumber value={team1WinProb} decimals={1} suffix="%" />
            </Text>
            <Text fontSize="xs" fontWeight="bold" color="accent.400" fontFamily="mono">
              <AnimatedNumber value={team2WinProb} decimals={1} suffix="%" />
            </Text>
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
  onMovePlayer: (teamNumber: number, playerId: number) => void;
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
  onMovePlayer,
  getPlayerById,
  bg,
  borderColor,
  iconColor,
  prediction,
}) => {
  const [recruitSearch, setRecruitSearch] = useState('');
  const [recruitOpen, setRecruitOpen] = useState(false);
  const otherTeamLabel = teamNumber === 1 ? 'Squad Bravo' : 'Squad Alpha';
  const moveIcon = teamNumber === 1 ? <FiArrowRight /> : <FiArrowLeft />;
  const filteredAvailable = availablePlayers.filter((p) =>
    p.name.toLowerCase().includes(recruitSearch.toLowerCase())
  );
  // Collapsed by default - most of the time you already know who you want,
  // especially arriving via Captain's Draft or Fine-tune. Typing or focusing
  // the search box opens it immediately so it never blocks a fast lookup.
  const showRecruitGrid = recruitOpen || recruitSearch.length > 0;

  const totalMMR = teamPlayers.reduce((sum, id) => {
    const player = getPlayerById(id);
    return sum + (player?.mmr || 0);
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
                <AnimatedNumber value={totalMMR} decimals={0} />
              </Text>
            </Box>
            {prediction && (
              <Box p={3} bg="space.900" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100">
                <Text fontSize="10px" fontWeight="black" color="gray.500" textTransform="uppercase" letterSpacing="widest" mb={1}>Synergy Score</Text>
                <Text fontSize="xl" fontWeight="black" color={iconColor} fontFamily="mono">
                  <AnimatedNumber value={prediction.avg_synergy_score} decimals={1} />
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
                        {Math.round(player.mmr)} MMR
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
                  <HStack spacing={1}>
                    <Tooltip label={`Move to ${otherTeamLabel}`} fontSize="xs">
                      <IconButton
                        icon={moveIcon}
                        size="xs"
                        variant="ghost"
                        colorScheme="blue"
                        onClick={() => onMovePlayer(teamNumber, playerId)}
                        aria-label={`Move ${player.name} to ${otherTeamLabel}`}
                        borderRadius="full"
                      />
                    </Tooltip>
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
                </HStack>
              );
            })
          )}
        </VStack>

        <Divider borderColor="whiteAlpha.100" />

        {/* Add Player - card picker, matching the same click-to-add pattern
            used by RosterSelector/Captain's Draft instead of a plain
            dropdown, so the two pages don't teach different interactions.
            Collapsed by default to cut down on always-open card clutter;
            opens on click or as soon as you start typing. */}
        <VStack align="stretch" spacing={3}>
          <HStack
            justify="space-between"
            cursor="pointer"
            onClick={() => setRecruitOpen((o) => !o)}
            userSelect="none"
          >
            <Text fontSize="xs" fontWeight="black" color="gray.500" textTransform="uppercase" letterSpacing="widest">
              Recruit Player
            </Text>
            <HStack spacing={1} color="gray.500">
              <Text fontSize="xs" fontFamily="mono">{availablePlayers.length} available</Text>
              <Icon
                as={FiChevronDown}
                boxSize={3}
                transform={showRecruitGrid ? 'rotate(180deg)' : undefined}
                transition="transform 0.2s ease-out"
              />
            </HStack>
          </HStack>
          <InputGroup size="sm">
            <InputLeftElement pointerEvents="none">
              <Icon as={FiSearch} color="gray.500" />
            </InputLeftElement>
            <Input
              placeholder="Search available players..."
              value={recruitSearch}
              onChange={(e) => setRecruitSearch(e.target.value)}
              onFocus={() => setRecruitOpen(true)}
              bg="space.900"
              borderRadius="md"
              borderColor="space.700"
              _hover={{ borderColor: iconColor }}
            />
          </InputGroup>
          <Collapse in={showRecruitGrid} animateOpacity>
            {filteredAvailable.length === 0 ? (
              <Text fontSize="xs" color="gray.600" textAlign="center" py={4}>
                {availablePlayers.length === 0 ? 'No players left to recruit' : 'No matches'}
              </Text>
            ) : (
              <SimpleGrid columns={{ base: 2, md: 3 }} spacing={2} maxH="280px" overflowY="auto" pr={1} pt={1}>
                {filteredAvailable.map((player) => (
                  <PlayerCard
                    key={player.id}
                    player={player}
                    size="sm"
                    onClick={() => onAddPlayer(teamNumber, String(player.id))}
                  />
                ))}
              </SimpleGrid>
            )}
          </Collapse>
        </VStack>
      </VStack>
    </Box>
  );
};

export default LineupPredictor;
