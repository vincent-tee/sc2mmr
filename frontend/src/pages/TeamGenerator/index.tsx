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
  Flex,
} from '@chakra-ui/react';
import { FiShuffle, FiZap } from 'react-icons/fi';
import { keyframes } from '@emotion/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { playersApi, teamsApi, replaysApi } from '../../api/endpoints';
import apiClient, { ApiClientError } from '../../api/client';
import { Player, TeamPlayer, TeamSuggestionWithImpact } from '../../types/api';
import PageHeader from '../../components/PageHeader';
import AnimatedNumber from '../../components/AnimatedNumber';
import TeamSelector from './TeamSelector';
import BalanceResults from './BalanceResults';
import CaptainsDraft from './CaptainsDraft';
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
  const [draftOpen, setDraftOpen] = useState(false);
  const [resultsTitle, setResultsTitle] = useState('Your teams');

  
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

      const response = await teamsApi.balance(realIds, 4);
      return response.data;
    },
    onSuccess: (data: TeamSuggestionWithImpact[]) => {
      setResultsTitle('Your teams');
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
    onError: (error: ApiClientError) => {
      toast({
        title: 'Failed to generate teams',
        description: error.userMessage || 'An unexpected error occurred',
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

  const toTeamPlayer = (player: Player): TeamPlayer => ({
    id: player.id,
    name: player.name,
    mmr: player.mmr,
    win_rate: player.win_rate,
    total_games: player.total_games,
    favorite_race: player.favorite_race,
    is_core_player: player.is_core_player,
    is_ai: player.is_ai,
  });

  const showDraftedTeams = async (team1: Player[], team2: Player[]): Promise<void> => {
    const teamMMR = (team: Player[]) => team.reduce((sum, p) => sum + p.mmr, 0);
    try {
      const { data } = await teamsApi.predict(team1.map((p) => p.id), team2.map((p) => p.id));
      setResultsTitle('Your drafted teams');
      setTeamSuggestions([{
        balance_prediction_id: null,
        team_1: { players: team1.map(toTeamPlayer), avg_mmr: teamMMR(team1) / team1.length },
        team_2: { players: team2.map(toTeamPlayer), avg_mmr: teamMMR(team2) / team2.length },
        win_probability_team_1: data.team_1.win_probability,
        win_probability_team_2: data.team_2.win_probability,
        fairness_rating: '',
        mmr_difference: Math.abs(teamMMR(team1) - teamMMR(team2)),
        match_quality: data.match_quality * 100,
      }]);
      setDraftOpen(false);
    } catch (error) {
      toast({ title: "Couldn't score the drafted teams", description: (error as ApiClientError).userMessage, status: 'error' });
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
    setDraftOpen(false);
  };

  const generateTeams = (): void => {
    const playerIds = selectedPlayers.map((p) => p.id);
    balanceTeamsMutation.mutate(playerIds);
  };

  // Validation flags
  const minPlayers = 2;
  const canGenerate = selectedPlayers.length >= minPlayers;
  const draftSquad = selectedPlayers.filter((p) => p.id > 0);
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
            Build Teams
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
        title="Build [Teams]"
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

          {draftOpen && teamSuggestions.length === 0 && (
            <CaptainsDraft squad={draftSquad} onComplete={showDraftedTeams} onCancel={() => setDraftOpen(false)} />
          )}

          {/* Display Results */}
          {teamSuggestions.length > 0 && !balanceTeamsMutation.isPending && (
            <BalanceResults
              suggestions={teamSuggestions}
              title={resultsTitle}
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

      {selectedPlayers.length > 0 && teamSuggestions.length === 0 && !draftOpen && (
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
          px={{ base: 3, md: 8 }}
          zIndex={100}
          boxShadow="0 -10px 30px rgba(0, 0, 0, 0.5)"
          animation={`${slideInUp} 0.3s ease-out`}
        >
          <Container maxW="container.xl" px={{ base: 0, md: 4 }}>
            <Flex justify="space-between" align="center" gap={{ base: 2, md: 6 }} flexWrap="wrap">
              <HStack spacing={{ base: 3, md: 5 }} minW={0}>
                <VStack align="start" spacing={0}>
                  <Text fontSize="10px" color="gray.500" fontWeight="black" textTransform="uppercase" letterSpacing="widest">
                    Squad
                  </Text>
                  <Text
                    fontSize={{ base: 'lg', md: 'xl' }}
                    fontWeight="black"
                    color={hasOddPlayers ? 'yellow.400' : 'brand.400'}
                    fontFamily="heading"
                    whiteSpace="nowrap"
                  >
                    {selectedPlayers.length} Players
                  </Text>
                </VStack>
                <Divider orientation="vertical" height="30px" borderColor="whiteAlpha.200" display={{ base: 'none', md: 'block' }} />
                <VStack align="start" spacing={0} display={{ base: 'none', md: 'flex' }}>
                  <Text fontSize="10px" color="gray.500" fontWeight="black" textTransform="uppercase" letterSpacing="widest">
                    Avg MMR
                  </Text>
                  <Text fontSize="xl" fontWeight="black" color="gray.200" fontFamily="mono">
                    <AnimatedNumber
                      value={selectedPlayers.reduce((s, p) => s + p.mmr, 0) / selectedPlayers.length}
                      format={(n) => Math.round(n).toLocaleString()}
                    />
                  </Text>
                </VStack>
                {aiSuggestion && hasOddPlayers && (
                  <>
                    <Divider orientation="vertical" height="30px" borderColor="whiteAlpha.200" display={{ base: 'none', md: 'block' }} />
                    <VStack align="start" spacing={0} display={{ base: 'none', md: 'flex' }}>
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

              <HStack spacing={2} flexWrap="wrap" justify="flex-end">
                <Button
                  variant="outline"
                  size="md"
                  leftIcon={<Icon as={FiShuffle} />}
                  onClick={() => setDraftOpen(true)}
                  isDisabled={draftSquad.length < minPlayers}
                  title={draftSquad.length < selectedPlayers.length ? "Guests and AI aren't included in a draft" : undefined}
                >
                  Draft
                </Button>
                <Button
                  colorScheme="brand"
                  size="md"
                  px={{ base: 4, md: 8 }}
                  fontWeight="black"
                  fontFamily="heading"
                  leftIcon={<Icon as={FiZap} />}
                  onClick={generateTeams}
                  isLoading={balanceTeamsMutation.isPending}
                  isDisabled={!canGenerate}
                >
                  Generate teams
                </Button>
              </HStack>
            </Flex>
          </Container>
        </Box>
      )}
    </Box>
  );
};



export default TeamGenerator;
