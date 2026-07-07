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
  HStack,
  useToast,
  Divider,
  Button,
  Icon,
} from '@chakra-ui/react';
import { FiZap } from 'react-icons/fi';
import { keyframes } from '@emotion/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { playersApi, teamsApi, replaysApi } from '../../api/endpoints';
import apiClient from '../../api/client';
import { Player, TeamSuggestionWithImpact } from '../../types/api';
import PageHeader from '../../components/PageHeader';
import AnimatedNumber from '../../components/AnimatedNumber';
import TeamSelector from './TeamSelector';
import MapSelector from './MapSelector';
import BalanceResults from './BalanceResults';
import LoadingState, { TeamResultSkeleton } from '../../components/LoadingState';
import { 
  copyToClipboard, 
  generateTeamText, 
  generateAllTeamsText 
} from '../../utils/formatting';

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
  const [aiDifficulties, setAIDifficulties] = useState<Record<string, number>>({});
  const [selectedMap, setSelectedMap] = useState<string>('');
  const [availableMaps, setAvailableMaps] = useState<string[]>([]);

  
  const toast = useToast({
    position: 'top',
    isClosable: true,
  });

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

  // Fetch available maps
  useEffect(() => {
    const fetchMaps = async () => {
      try {
        const response = await replaysApi.getMatches(100);
        const maps = Array.from(new Set(response.data.matches.map(m => m.map_name))).sort();
        setAvailableMaps(maps);
      } catch (error) {
        console.error('Failed to fetch maps', error);
      }
    };
    fetchMaps();
  }, []);

  const players = playersData || [];
  // Only show players who have actual game history; 0-game players are ghost/manual entries
  const activePlayers = players.filter(p => p.total_games > 0);
  const allAvailablePlayers = [...activePlayers, ...guestPlayers];

  const balanceTeamsMutation = useMutation({
    mutationFn: async (playerIds: number[]) => {
      const realIds = playerIds.filter(id => id > 0);
      const guests = allAvailablePlayers.filter(gp => gp.id < 0 && playerIds.includes(gp.id));

      if (guests.length > 0) {
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
          top_n: 4
        });
        return response.data;
      }

      const response = await teamsApi.balance(realIds, 4, selectedMap);
      return response.data;
    },
    onSuccess: (data: TeamSuggestionWithImpact[]) => {
      setTeamSuggestions(data);
      
      // Clear any pending toasts and show single completion message
      toast.closeAll();
      toast({
        title: 'Squads Optimized',
        status: 'success',
        duration: 2000,
      });
      
      setTimeout(() => {
        const resultsElement = document.getElementById('balance-results');
        if (resultsElement) {
          resultsElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
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
        // MINIMUM DIFFICULTY: Only suggest Hard (2100) or higher
        // Lower difficulties are too weak for meaningful balance
        Object.entries(aiDifficulties).forEach(([diffName, aiMMR]) => {
          if (aiMMR < 3200 && diffName !== 'hard') return; 
          
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

  // Select players from last match
  const selectLastMatch = async () => {
    try {
      const response = await replaysApi.getMatchesWithPlayers(1);
      if (response.data.matches && response.data.matches.length > 0) {
        const lastMatch = response.data.matches[0];
        const playerIds = lastMatch.players.map(p => p.player_id);
        const matchPlayers = allAvailablePlayers.filter(p => playerIds.includes(p.id));
        setSelectedPlayers(matchPlayers);
        toast({
          title: `Selected ${matchPlayers.length} players from last match`,
          description: lastMatch.map_name,
          status: 'success',
          duration: 3000,
        });
      } else {
        toast({ title: 'No recent matches found', status: 'warning' });
      }
    } catch (error) {
      console.error('Failed to fetch last match players', error);
      toast({ title: 'Failed to fetch last match', status: 'error' });
    }
  };

  const togglePlayer = (player: Player): void => {
    if (teamSuggestions.length > 0) {
      setTeamSuggestions([]);
    }
    setSelectedPlayers((prev) => {
      const isSelected = prev.some((p) => p.id === player.id);
      if (isSelected) {
        return prev.filter((p) => p.id !== player.id);
      } else {
        return [...prev, player];
      }
    });
  };

  const selectAll = (): void => {
    if (teamSuggestions.length > 0) {
      setTeamSuggestions([]);
    }
    setSelectedPlayers([...allAvailablePlayers]);
  };

  const clearSelection = (): void => {
    setSelectedPlayers([]);
    setTeamSuggestions([]);
  };

  const generateTeams = (): void => {
    const playerIds = selectedPlayers.map((p) => p.id);
    balanceTeamsMutation.mutate(playerIds);
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

  const handleExportAll = async (): Promise<void> => {
    if (teamSuggestions.length < 2) return;
    
    // Only copy first two (Optimal and Tactical)
    const bestSuggestions = teamSuggestions.slice(0, 2);
    const text = generateAllTeamsText(bestSuggestions);
    const success = await copyToClipboard(text);
    
    if (success) {
      toast({
        title: 'Optimal & Tactical configs copied!',
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
      <PageHeader
        kicker="Matchmaking"
        title="Team [Generator]"
        description="Pick who's playing tonight — we'll do the math and hand you fair teams."
      />

      <Container maxW="container.xl" pt={8} pb={selectedPlayers.length > 0 ? "140px" : "8"} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Player Selection Section */}
          <TeamSelector
            players={allAvailablePlayers}
            selectedPlayers={selectedPlayers}
            onTogglePlayer={togglePlayer}
            onSelectAll={selectAll}
            onClearSelection={clearSelection}
            onSelectLastMatch={selectLastMatch}
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
                id: -(guestPlayers.length + 1) * 1000 - 1,
                name: name,
                mmr: mmr,
                mu: (mmr - 1000 + 200 * 0.1) / 100, // invert display MMR: mmr = 1000 + 100*mu - 200*sigma
                sigma: 0.1,
                total_games: 0,
                win_rate: 0,
                favorite_race: 'Random',
                unified_mmr: mmr,
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
                last_played: null,
                recent_form: null,
                is_new: false,
                is_active: true,
                days_since_played: null
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
                mu: (mmr - 1000 + 200 * 8.333) / 100, // invert display MMR: mmr = 1000 + 100*mu - 200*sigma
                sigma: 8.333,
                total_games: 0,
                win_rate: 0,
                favorite_race: 'Random',
                unified_mmr: mmr,
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
                is_ai: false,
                avg_economic_score: 50,
                avg_combat_score: 50,
                avg_efficiency_score: 50,
                avg_overall_impact: 50,
                avg_first_damage_timing: null,
                primary_archetype: null,
                avg_aggression_score: 50,
                created_at: new Date().toISOString(),
                last_played: null,
                recent_form: null,
                is_new: false,
                is_active: true,
                days_since_played: null
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
                    unified_mmr: mmr,
                    hybrid_mmr: mmr,
                    recency_weighted_mmr: mmr,
                    mu: (mmr - 1000 + 200 * p.sigma) / 100, // invert display MMR
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
                    unified_mmr: mmr,
                    hybrid_mmr: mmr,
                    recency_weighted_mmr: mmr,
                    mu: (mmr - 1000 + 200 * p.sigma) / 100, // invert display MMR
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

          {/* Team Results Section */}
          {balanceTeamsMutation.isPending && (
            <Box
              p={8}
              bg="space.800"
              borderRadius="xl"
              border="2px solid"
              borderColor="brand.500"
              textAlign="center"
            >
              <Text fontSize="lg" fontFamily="heading" color="brand.400" letterSpacing="wider" mb={4}>
                Calculating optimal configurations...
              </Text>
              <TeamResultSkeleton />
            </Box>
          )}

          {/* Display Results */}
          {teamSuggestions.length > 0 && !balanceTeamsMutation.isPending && (
            <BalanceResults
              suggestions={teamSuggestions}
              onExport={handleExport}
              onExportAll={handleExportAll}
              onClear={() => {
                setTeamSuggestions([]);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            />
          )}
        </VStack>
      </Container>

      {selectedPlayers.length > 0 && teamSuggestions.length === 0 && (
        <Box
          position="fixed"
          bottom={0}
          left={0}
          right={0}
          bg="rgba(10, 15, 28, 0.95)"
          backdropFilter="blur(12px)"
          borderTop="1px solid"
          borderColor="brand.500"
          py={3}
          px={8}
          zIndex={100}
          boxShadow="0 -10px 30px rgba(0, 0, 0, 0.5)"
          animation={`${slideInUp} 0.3s ease-out`}
        >
          <Container maxW="container.xl">
            <HStack justify="space-between" spacing={6}>
              {/* Left: player count + avg MMR */}
              <HStack spacing={5}>
                <VStack align="start" spacing={0}>
                  <Text fontSize="10px" color="gray.500" fontWeight="black" textTransform="uppercase" letterSpacing="widest">
                    Squad
                  </Text>
                  <Text
                    fontSize="xl"
                    fontWeight="black"
                    color={hasOddPlayers ? 'yellow.400' : 'brand.400'}
                    fontFamily="heading"
                  >
                    {selectedPlayers.length} Players
                  </Text>
                </VStack>
                <Divider orientation="vertical" height="30px" borderColor="whiteAlpha.200" />
                <VStack align="start" spacing={0}>
                  <Text fontSize="10px" color="gray.500" fontWeight="black" textTransform="uppercase" letterSpacing="widest">
                    Avg MMR
                  </Text>
                  <Text fontSize="xl" fontWeight="black" color="gray.200" fontFamily="mono">
                    {selectedPlayers.length > 0 ? (
                      <AnimatedNumber
                        value={selectedPlayers.reduce((s, p) => s + p.mmr, 0) / selectedPlayers.length}
                        format={(n) => Math.round(n).toLocaleString()}
                      />
                    ) : (
                      '—'
                    )}
                  </Text>
                </VStack>
                {aiSuggestion && hasOddPlayers && (
                  <>
                    <Divider orientation="vertical" height="30px" borderColor="whiteAlpha.200" />
                    <VStack align="start" spacing={0}>
                      <Text fontSize="10px" color="yellow.500" fontWeight="black" textTransform="uppercase" letterSpacing="widest">
                        Suggested AI
                      </Text>
                      <Text fontSize="sm" color="gray.300" fontFamily="mono">
                        {aiSuggestion.difficulty} · {aiSuggestion.mmr} MMR
                      </Text>
                    </VStack>
                  </>
                )}
              </HStack>

              {/* Right: map selector + actions */}
              <HStack spacing={3}>
                <MapSelector
                  selectedMap={selectedMap}
                  availableMaps={availableMaps}
                  onMapChange={setSelectedMap}
                />
                <Divider orientation="vertical" height="30px" borderColor="whiteAlpha.200" />
                <Button
                  variant="ghost"
                  colorScheme="gray"
                  onClick={clearSelection}
                  fontFamily="heading"
                  size="sm"
                >
                  Clear
                </Button>
                <Button
                  colorScheme="brand"
                  size="md"
                  px={8}
                  fontSize="lg"
                  fontWeight="black"
                  fontFamily="heading"
                  leftIcon={<Icon as={FiZap} />}
                  onClick={generateTeams}
                  isLoading={balanceTeamsMutation.isPending}
                  isDisabled={!canGenerate}
                  boxShadow="0 0 15px rgba(255, 107, 53, 0.25)"
                  _hover={{
                    transform: 'translateY(-1px)',
                    boxShadow: '0 0 25px rgba(255, 107, 53, 0.45)',
                  }}
                >
                  Launch Match
                </Button>
              </HStack>
            </HStack>
          </Container>
        </Box>
      )}
    </Box>
  );
};



export default TeamGenerator;
