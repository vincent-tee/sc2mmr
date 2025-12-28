/**
 * Team Generator Page - Team Balancing System
 * Quick team balancing interface for casual gaming groups
 *
 * This component orchestrates the team generation workflow with proper state management
 */
import { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  useToast,
  SimpleGrid,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { playersApi, teamsApi } from '../../api/endpoints';
import apiClient from '../../api/client';
import { Player, TeamSuggestionWithImpact, Race } from '../../types/api';
import TacticalBackground from '../../components/common/TacticalBackground';
import TeamSelector from './TeamSelector';
import BalanceControls from './BalanceControls';
import GenerateButton from './GenerateButton';
import BalanceResults from './BalanceResults';
import LoadingState, { TeamResultSkeleton } from '../../components/LoadingState';
import { copyToClipboard, generateTeamText } from '../../utils/formatting';
import BalanceMethodSelector, { BalanceMethod } from '../../components/BalanceMethodSelector';
import AdaptiveWeightControls from '../../components/AdaptiveWeightControls';
import BalanceBreakdown, { MLBalanceData } from '../../components/BalanceBreakdown';

const slideInUp = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

const TeamGenerator: React.FC = () => {
  const [selectedPlayers, setSelectedPlayers] = useState<Player[]>([]);
  const [guestPlayers, setGuestPlayers] = useState<Player[]>([]);
  const [teamSuggestions, setTeamSuggestions] = useState<
    TeamSuggestionWithImpact[]
  >([]);
  const [useImpactBalance, setUseImpactBalance] = useState<boolean>(false);
  const [impactWeight, setImpactWeight] = useState<number>(0.5);
  const [aiDifficulties, setAIDifficulties] = useState<Record<string, number>>({});
  const [balanceMethod, setBalanceMethod] = useState<BalanceMethod>('ml-metrics');
  const [mlBalanceData, setMlBalanceData] = useState<MLBalanceData | null>(null);
  const [useAdaptiveWeights, setUseAdaptiveWeights] = useState<boolean>(true);
  const [manualWeights, setManualWeights] = useState<Record<string, number>>({
    session_mmr: 0.40,
    combat: 0.25,
    economic: 0.20,
    efficiency: 0.15,
  });
  
  const toast = useToast();

  // Fetch all players
  const { data: playersData, isLoading: isLoadingPlayers } = useQuery<
    Player[]
  >({
    queryKey: ['players'],
    queryFn: async () => {
      const response = await playersApi.getAll();
      return response.data;
    },
  });

  // Fetch AI difficulties
  useEffect(() => {
    const fetchAI = async () => {
      try {
        const response = await teamsApi.getAIDifficulties();
        setAIDifficulties(response.data.difficulties);
      } catch (error) {
        console.error('Failed to fetch AI difficulties', error);
      }
    };
    fetchAI();
  }, []);

  const players = playersData || [];
  const allAvailablePlayers = [...players, ...guestPlayers];

  // Balance teams mutation
  const balanceTeamsMutation = useMutation({
    mutationFn: async (playerIds: number[]) => {
      // Split into real IDs and guest players
      const realIds = playerIds.filter(id => id > 0);
      const guests = allAvailablePlayers.filter(gp => gp.id < 0 && playerIds.includes(gp.id));

      // ML Metrics balancing
      if (balanceMethod === 'ml-metrics') {
        const response = await apiClient.post('/teams/balance-with-ml-metrics', {
          player_ids: realIds.length > 0 ? realIds : playerIds,
          use_adaptive_weights: useAdaptiveWeights,
          manual_weights: useAdaptiveWeights ? null : manualWeights,
        });
        return { type: 'ml', data: response.data };
      }

      // Session or TrueSkill balancing
      if (balanceMethod === 'session' || balanceMethod === 'trueskill') {
        const response = await teamsApi.balanceWithModel(
          realIds,
          balanceMethod
        );
        
        const modelData = response.data;
        
        // Adapt ModelBalanceResponse to TeamSuggestionWithImpact
        const adaptedSuggestion: TeamSuggestionWithImpact = {
          team_1: {
            players: modelData.team_1.map((p: any) => ({
              id: p.id,
              name: p.name,
              mmr: p.mmr,
              mu: (p.mmr - 1000) / 100, // Approximate
              sigma: 8.333 // Default
            })),
            total_mmr: modelData.team_1_rating,
            avg_mmr: modelData.team_1_rating / modelData.team_1.length
          },
          team_2: {
            players: modelData.team_2.map((p: any) => ({
              id: p.id,
              name: p.name,
              mmr: p.mmr,
              mu: (p.mmr - 1000) / 100, // Approximate
              sigma: 8.333 // Default
            })),
            total_mmr: modelData.team_2_rating,
            avg_mmr: modelData.team_2_rating / modelData.team_2.length
          },
          win_probability_team_1: modelData.predicted_winner === 1 ? modelData.win_confidence * 100 : (1 - modelData.win_confidence) * 100,
          win_probability_team_2: modelData.predicted_winner === 2 ? modelData.win_confidence * 100 : (1 - modelData.win_confidence) * 100,
          fairness_rating: modelData.match_quality > 0.8 ? 'Excellent' : modelData.match_quality > 0.6 ? 'Good' : 'Fair',
          mmr_difference: modelData.rating_difference,
          impact_balance_score: modelData.match_quality * 100,
          impact_difference: 0
        };

        return { type: 'standard', data: [adaptedSuggestion] };
      }

      if (guests.length > 0) {
        // Use the new custom-players endpoint
        const response = await apiClient.post('/teams/balance-with-custom-players', {
          player_ids: realIds,
          custom_players: guests.map(g => ({
            name: g.name,
            mmr: g.mmr,
            mu: g.mu,
            sigma: g.sigma,
            overall_impact: g.avg_overall_impact,
            total_games: g.total_games
          })),
          top_n: 3
        });
        return { type: 'standard', data: response.data };
      }

      if (useImpactBalance) {
        const response = await teamsApi.balanceWithImpact(
          realIds,
          10,
          impactWeight
        );
        return { type: 'standard', data: response.data };
      } else {
        const response = await teamsApi.balance(realIds, 10);
        return { type: 'standard', data: response.data };
      }
    },
    onSuccess: (result: { type: string; data: any }) => {
      if (result.type === 'ml') {
        // Handle ML balance response
        setMlBalanceData(result.data);
        // Convert ML response to team suggestions format if available
        if (result.data.suggestions) {
          setTeamSuggestions(result.data.suggestions);
        } else {
          // Create a basic team suggestion from ML data
          setTeamSuggestions([]);
        }
      } else {
        // Standard balance response
        setTeamSuggestions(result.data);
        setMlBalanceData(null);
      }
      toast({
        title: 'Teams generated successfully!',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to generate teams',
        description: error.response?.data?.detail || 'An unexpected error occurred',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Logic to suggest best AI difficulty for uneven teams
  const getAISuggestion = useCallback(() => {
    if (selectedPlayers.length % 2 === 0 || selectedPlayers.length < 1 || selectedPlayers.length > 9) {
      return null;
    }

    const n = selectedPlayers.length;
    const team1Size = Math.ceil(n / 2);
    const mmrs = selectedPlayers.map(p => p.mmr);
    
    // Helper to get all combinations
    const getCombinations = (arr: number[], k: number): number[][] => {
      const results: number[][] = [];
      const f = (start: number, combo: number[]) => {
        if (combo.length === k) {
          results.push(combo);
          return;
        }
        for (let i = start; i < arr.length; i++) {
          f(i + 1, [...combo, arr[i]]);
        }
      };
      f(0, []);
      return results;
    };

    const combos = getCombinations(mmrs, team1Size);
    const totalMMR = mmrs.reduce((a, b) => a + b, 0);
    
    let bestDiff = Infinity;
    let idealMMR = 0;

    combos.forEach(combo => {
      const team1Sum = combo.reduce((a, b) => a + b, 0);
      const team2Sum = totalMMR - team1Sum;
      const gap = team1Sum - team2Sum;
      
      // Gap is what the AI needs to fill
      if (gap > 0) {
        // Find which AI difficulty is closest to this gap
        Object.values(aiDifficulties).forEach(aiMMR => {
          const diff = Math.abs(gap - aiMMR);
          if (diff < bestDiff) {
            bestDiff = diff;
            idealMMR = aiMMR;
          }
        });
      }
    });

    if (idealMMR === 0) return null;

    // Find the difficulty name for this MMR
    const difficulty = Object.entries(aiDifficulties).find(([_, mmr]) => mmr === idealMMR)?.[0];
    return difficulty ? { difficulty, mmr: idealMMR } : null;
  }, [selectedPlayers, aiDifficulties]);

  const aiSuggestion = getAISuggestion();

  // Handler functions for ML metrics
  const handleToggleAdaptive = () => {
    setUseAdaptiveWeights(!useAdaptiveWeights);
  };

  const handleManualWeightChange = (component: string, value: number) => {
    setManualWeights(prev => ({
      ...prev,
      [component]: value,
    }));
  };

  // Toggle player selection
  const togglePlayer = (player: Player): void => {
    setSelectedPlayers((prev) => {
      const isSelected = prev.some((p) => p.id === player.id);
      if (isSelected) {
        return prev.filter((p) => p.id !== player.id);
      } else {
        return [...prev, player];
      }
    });
  };

  // Select all players
  const selectAll = (): void => {
    setSelectedPlayers([...allAvailablePlayers]);
  };

  // Clear selection
  const clearSelection = (): void => {
    setSelectedPlayers([]);
    setTeamSuggestions([]);
  };

  // Generate teams
  const generateTeams = (): void => {
    const playerIds = selectedPlayers.map((p) => p.id);
    balanceTeamsMutation.mutate(playerIds);
  };

  const handleAddAI = (difficulty: string, mmr: number) => {
    const name = `Computer (${difficulty})`;
    // Check if already exists in guest players to avoid duplicates
    const existing = guestPlayers.find(p => p.name === name);
    if (existing) {
      if (!selectedPlayers.some(p => p.id === existing.id)) {
        setSelectedPlayers(prev => [...prev, existing]);
      }
      return;
    }

    const newAI: Player = {
      id: -(guestPlayers.length + 1) * 1000 - 1, // Unique negative ID
      name: name,
      mmr: mmr,
      mu: (mmr - 1000) / 100,
      sigma: 0.1, // Very certain for AI
      total_games: 0,
      win_rate: 0,
      favorite_race: 'Random',
      hybrid_mmr: mmr,
      avg_pim: 0,
      recency_weighted_mmr: mmr,
      wins: 0,
      losses: 0,
      terran_games: 0,
      protoss_games: 0,
      zerg_games: 0,
      random_games: 0,
      is_core_player: false,
      is_ai: true,
      avg_economic_score: 50,
      avg_combat_score: 50,
      avg_efficiency_score: 50,
      avg_overall_impact: 50,
      avg_first_damage_timing: null,
      primary_archetype: null,
      avg_aggression_score: 50,
      created_at: new Date().toISOString(),
      last_played: null
    };
    setGuestPlayers(prev => [...prev, newAI]);
    setSelectedPlayers(prev => [...prev, newAI]);
    toast({ title: `${name} added to balance teams`, status: 'info', duration: 2000 });
  };

  // Validation flags
  const minPlayers = 2;
  const canGenerate = selectedPlayers.length >= minPlayers;
  const hasOddPlayers = selectedPlayers.length % 2 !== 0;

  // Export team composition
  const handleExport = async (
    suggestion: TeamSuggestionWithImpact,
    format: 'text' | 'download'
  ): Promise<void> => {
    if (format === 'text') {
      const text = generateTeamText(suggestion);
      const success = await copyToClipboard(text);
      if (success) {
        toast({
          title: 'Team composition copied to clipboard!',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      } else {
        toast({
          title: 'Failed to copy to clipboard',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
      }
    } else if (format === 'download') {
      const text = generateTeamText(suggestion);
      const blob = new Blob([text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `team-composition-${Date.now()}.txt`;
      a.click();
      URL.revokeObjectURL(url);
      toast({
        title: 'Team composition downloaded!',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  if (isLoadingPlayers) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading
            size="2xl"
            fontFamily="heading"
            letterSpacing="wider"
            color="brand.400"
            textAlign="center"
          >
            Team Generator
          </Heading>
          <LoadingState variant="players" count={8} />
        </VStack>
      </Container>
    );
  }

  return (
    <Box position="relative">
      <TacticalBackground />

      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Friend Squad Header */}
          <Box textAlign="center" py={4} animation={`${slideInUp} 0.5s ease-out`}>
            <Heading
              size="2xl"
              fontFamily="heading"
              fontWeight="black"
              letterSpacing="wider"
              mb={2}
              color="brand.400"
            >
              <Text as="span" className="emoji-font">⚖️</Text> Team Generator
            </Heading>
            <Text
              fontSize="lg"
              color="gray.400"
              fontFamily="heading"
              letterSpacing="wide"
            >
              Get perfectly balanced squads for your next session
            </Text>
          </Box>

          {/* Balance Method Selection */}
          <BalanceMethodSelector
            selectedMethod={balanceMethod}
            onMethodChange={setBalanceMethod}
          />

          {/* Player Selection Section */}
          <TeamSelector
            players={allAvailablePlayers}
            selectedPlayers={selectedPlayers}
            onTogglePlayer={togglePlayer}
            onSelectAll={selectAll}
            onClearSelection={clearSelection}
            onAddAI={(difficulty, mmr) => {
              const name = `Computer (${difficulty})`;
              // Check if already exists in guest players to avoid duplicates
              const existing = guestPlayers.find(p => p.name === name);
              if (existing) {
                if (!selectedPlayers.some(p => p.id === existing.id)) {
                  setSelectedPlayers(prev => [...prev, existing]);
                }
                return;
              }

              const newAI: Player = {
                id: -(guestPlayers.length + 1) * 1000 - 1, // Unique negative ID
                name: name,
                mmr: mmr,
                mu: (mmr - 1000) / 100,
                sigma: 0.1, // Very certain for AI
                total_games: 0,
                win_rate: 0,
                favorite_race: 'Random',
                hybrid_mmr: mmr,
                avg_pim: 0,
                recency_weighted_mmr: mmr,
                wins: 0,
                losses: 0,
                terran_games: 0,
                protoss_games: 0,
                zerg_games: 0,
                random_games: 0,
                is_core_player: false,
                is_ai: true,
                avg_economic_score: 50,
                avg_combat_score: 50,
                avg_efficiency_score: 50,
                avg_overall_impact: 50,
                avg_first_damage_timing: null,
                primary_archetype: null,
                avg_aggression_score: 50,
                created_at: new Date().toISOString(),
                last_played: null
              };
              setGuestPlayers(prev => [...prev, newAI]);
              setSelectedPlayers(prev => [...prev, newAI]);
              toast({ title: `${name} added to session`, status: 'info', duration: 2000 });
            }}
            onAddGuest={(name, mmr) => {
              const newGuest: Player = {
                id: -(guestPlayers.length + 1) * 1000, // Large negative ID to avoid conflicts
                name: `${name} (Guest)`,
                mmr: mmr,
                mu: (mmr - 1000) / 100,
                sigma: 8.333,
                total_games: 0,
                win_rate: 0,
                favorite_race: 'Random',
                hybrid_mmr: mmr,
                avg_pim: 0,
                recency_weighted_mmr: mmr,
                wins: 0,
                losses: 0,
                terran_games: 0,
                protoss_games: 0,
                zerg_games: 0,
                random_games: 0,
                is_core_player: false,
                avg_economic_score: 50,
                avg_combat_score: 50,
                avg_efficiency_score: 50,
                avg_overall_impact: 50,
                avg_first_damage_timing: null,
                primary_archetype: null,
                avg_aggression_score: 50,
                created_at: new Date().toISOString(),
                last_played: null
              };
              setGuestPlayers(prev => [...prev, newGuest]);
              setSelectedPlayers(prev => [...prev, newGuest]);
              toast({ title: `${name} added to session (${mmr} MMR)`, status: 'success', duration: 2000 });
            }}
            onEditGuest={(playerId, name, mmr) => {
              setGuestPlayers(prev => prev.map(p => {
                if (p.id === playerId) {
                  return {
                    ...p,
                    name: `${name} (Guest)`,
                    mmr: mmr,
                    hybrid_mmr: mmr,
                    recency_weighted_mmr: mmr,
                    mu: (mmr - 1000) / 100,
                  };
                }
                return p;
              }));
              setSelectedPlayers(prev => prev.map(p => {
                if (p.id === playerId) {
                  return {
                    ...p,
                    name: `${name} (Guest)`,
                    mmr: mmr,
                    hybrid_mmr: mmr,
                    recency_weighted_mmr: mmr,
                    mu: (mmr - 1000) / 100,
                  };
                }
                return p;
              }));
              toast({ title: `${name} updated`, status: 'info', duration: 2000 });
            }}
            onDeleteGuest={(playerId) => {
              const player = guestPlayers.find(p => p.id === playerId);
              setGuestPlayers(prev => prev.filter(p => p.id !== playerId));
              setSelectedPlayers(prev => prev.filter(p => p.id !== playerId));
              toast({ title: `${player?.name.replace(' (Guest)', '') || 'Guest'} removed`, status: 'warning', duration: 2000 });
            }}
          />

          {/* Impact Balancing Controls - only show for non-ML methods */}
          {balanceMethod !== 'ml-metrics' && (
            <BalanceControls
              useImpactBalance={useImpactBalance}
              impactWeight={impactWeight}
              onUseImpactBalanceChange={setUseImpactBalance}
              onImpactWeightChange={setImpactWeight}
            />
          )}

          {/* ML Metrics Weight Controls */}
          <AdaptiveWeightControls
            isVisible={balanceMethod === 'ml-metrics'}
            weights={manualWeights}
            accuracies={{
              session_mmr: 0.72,
              combat: 0.68,
              economic: 0.65,
              efficiency: 0.63,
            }}
            isAdaptive={useAdaptiveWeights}
            onToggleAdaptive={handleToggleAdaptive}
            onManualWeightChange={handleManualWeightChange}
          />

          {/* Generate Button */}
          <GenerateButton
            canGenerate={canGenerate}
            isLoading={balanceTeamsMutation.isPending}
            selectedPlayersCount={selectedPlayers.length}
            hasOddPlayers={hasOddPlayers}
            minPlayers={minPlayers}
            onGenerate={generateTeams}
            aiSuggestion={aiSuggestion}
            onAddAI={handleAddAI}
          />

          {/* Team Results Section */}
          {balanceTeamsMutation.isPending && (
            <VStack spacing={4}>
              <Text
                fontSize="xl"
                fontFamily="heading"
                color="brand.400"
                letterSpacing="wider"
              >
                Calculating optimal configurations...
              </Text>
              <TeamResultSkeleton />
              <TeamResultSkeleton />
              <TeamResultSkeleton />
            </VStack>
          )}

          {/* Display Results */}
          {teamSuggestions.length > 0 && !balanceTeamsMutation.isPending && (
            <BalanceResults
              suggestions={teamSuggestions}
              onExport={handleExport}
            />
          )}

          {/* ML Balance Breakdown */}
          {balanceMethod === 'ml-metrics' && mlBalanceData && !balanceTeamsMutation.isPending && (
            <BalanceBreakdown balanceData={mlBalanceData} />
          )}
        </VStack>
      </Container>
    </Box>
  );
};

export default TeamGenerator;
