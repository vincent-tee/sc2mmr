/**
 * Team Generator Page - TACTICAL DEPLOYMENT SYSTEM
 * Quick team balancing interface for casual gaming groups
 *
 * This component orchestrates the team generation workflow with proper state management
 */
import { useState } from 'react';
import { Box, Container, Heading, Text, VStack } from '@chakra-ui/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { playersApi, teamsApi } from '@/api/endpoints';
import TacticalBackground from '@/components/common/TacticalBackground';
import EmptyState from '@/components/EmptyState';
import LoadingState, { TeamResultSkeleton } from '@/components/LoadingState';
import { useToast } from '@/hooks/useToast';
import { generateTeamText, copyToClipboard } from '@/utils/formatting';
import type { Player, TeamSuggestion } from '@/types/api';

import TeamSelector from './TeamSelector';
import BalanceControls from './BalanceControls';
import GenerateButton from './GenerateButton';
import BalanceResults from './BalanceResults';

// Extended TeamSuggestion with additional impact fields
interface TeamSuggestionWithImpact extends TeamSuggestion {
  team_1_avg_impact?: number;
  team_2_avg_impact?: number;
}

const TeamGenerator: React.FC = () => {
  const [selectedPlayers, setSelectedPlayers] = useState<Player[]>([]);
  const [teamSuggestions, setTeamSuggestions] = useState<
    TeamSuggestionWithImpact[]
  >([]);
  const [useImpactBalance, setUseImpactBalance] = useState<boolean>(false);
  const [impactWeight, setImpactWeight] = useState<number>(0.5);
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

  const players = playersData || [];

  // Balance teams mutation
  const balanceTeamsMutation = useMutation({
    mutationFn: async (playerIds: number[]) => {
      if (useImpactBalance) {
        const response = await teamsApi.balanceWithImpact(
          playerIds,
          3,
          impactWeight
        );
        return response.data;
      } else {
        const response = await teamsApi.balance(playerIds, 3); // Get top 3 suggestions
        return response.data;
      }
    },
    onSuccess: (data: TeamSuggestionWithImpact[]) => {
      setTeamSuggestions(data);
      toast.success('Teams generated successfully!');
    },
    onError: (error: Error & { userMessage?: string }) => {
      toast.error(error.userMessage || 'Failed to generate teams');
    },
  });

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
    setSelectedPlayers([...players]);
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
        toast.success('Team composition copied to clipboard!');
      } else {
        toast.error('Failed to copy to clipboard');
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
      toast.success('Team composition downloaded!');
    }
  };

  if (isLoadingPlayers) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading
            size="2xl"
            fontFamily="heading"
            textTransform="uppercase"
            letterSpacing="wider"
            color="brand.400"
            textAlign="center"
          >
            TACTICAL DEPLOYMENT
          </Heading>
          <LoadingState variant="players" count={8} />
        </VStack>
      </Container>
    );
  }

  if (!players || players.length === 0) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading
            size="2xl"
            fontFamily="heading"
            textTransform="uppercase"
            letterSpacing="wider"
            color="brand.400"
            textAlign="center"
          >
            TACTICAL DEPLOYMENT
          </Heading>
          <EmptyState
            variant="players"
            title="No Players Found"
            description="Upload some replay files to start tracking players and generating balanced teams."
          />
        </VStack>
      </Container>
    );
  }

  return (
    <Box position="relative">
      {/* Animated grid background */}
      <TacticalBackground />

      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Tactical Header */}
          <Box textAlign="center" py={6}>
            <Heading
              size="3xl"
              fontFamily="heading"
              fontWeight="black"
              textTransform="uppercase"
              letterSpacing="wider"
              mb={2}
              color="brand.400"
              textShadow="0 0 40px rgba(0, 212, 255, 0.6)"
              position="relative"
            >
              <Box
                as="span"
                display="inline-block"
                position="relative"
                _before={{
                  content: '"<<"',
                  position: 'absolute',
                  left: '-50px',
                  color: 'brand.500',
                  fontSize: '2xl',
                }}
                _after={{
                  content: '">>"',
                  position: 'absolute',
                  right: '-50px',
                  color: 'brand.500',
                  fontSize: '2xl',
                }}
              >
                TACTICAL DEPLOYMENT
              </Box>
            </Heading>
            <Text
              fontSize="lg"
              color="gray.400"
              fontFamily="heading"
              letterSpacing="wide"
              textTransform="uppercase"
            >
              [ BALANCED TEAM GENERATION SYSTEM ]
            </Text>
          </Box>

          {/* Player Selection Section */}
          <TeamSelector
            players={players}
            selectedPlayers={selectedPlayers}
            onTogglePlayer={togglePlayer}
            onSelectAll={selectAll}
            onClearSelection={clearSelection}
          />

          {/* Impact Balancing Controls */}
          <BalanceControls
            useImpactBalance={useImpactBalance}
            impactWeight={impactWeight}
            onUseImpactBalanceChange={setUseImpactBalance}
            onImpactWeightChange={setImpactWeight}
          />

          {/* Generate Button */}
          <GenerateButton
            canGenerate={canGenerate}
            isLoading={balanceTeamsMutation.isPending}
            selectedPlayersCount={selectedPlayers.length}
            hasOddPlayers={hasOddPlayers}
            minPlayers={minPlayers}
            onGenerate={generateTeams}
          />

          {/* Team Results Section */}
          {balanceTeamsMutation.isPending && (
            <VStack spacing={4}>
              <Text
                fontSize="xl"
                fontFamily="heading"
                textTransform="uppercase"
                color="brand.400"
                letterSpacing="wider"
              >
                CALCULATING OPTIMAL CONFIGURATIONS...
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
        </VStack>
      </Container>
    </Box>
  );
};

export default TeamGenerator;
