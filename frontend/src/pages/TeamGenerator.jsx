/**
 * Team Generator Page - PRIMARY FEATURE
 * Quick team balancing interface for casual gaming groups
 */
import { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  Button,
  SimpleGrid,
  VStack,
  HStack,
  Badge,
  Card,
  CardHeader,
  CardBody,
  Divider,
  Progress,
  useColorModeValue,
  Spinner,
  Collapse,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
} from '@chakra-ui/react';
import { FiChevronDown, FiCopy, FiDownload, FiShare2 } from 'react-icons/fi';
import { useQuery, useMutation } from '@tanstack/react-query';
import { playersApi, teamsApi } from '../api/endpoints';
import PlayerCard from '../components/PlayerCard';
import EmptyState from '../components/EmptyState';
import LoadingState, { TeamResultSkeleton } from '../components/LoadingState';
import { useToast } from '../hooks/useToast';
import { formatMMR, generateTeamText, copyToClipboard, getFairnessColor } from '../utils/formatting';

const TeamGenerator = () => {
  const [selectedPlayers, setSelectedPlayers] = useState([]);
  const [teamSuggestions, setTeamSuggestions] = useState([]);
  const toast = useToast();

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Fetch all players
  const { data: playersData, isLoading: isLoadingPlayers } = useQuery({
    queryKey: ['players'],
    queryFn: async () => {
      const response = await playersApi.getAll();
      return response.data;
    },
  });

  const players = playersData || [];

  // Balance teams mutation
  const balanceTeamsMutation = useMutation({
    mutationFn: async (playerIds) => {
      const response = await teamsApi.balance(playerIds, 3); // Get top 3 suggestions
      return response.data;
    },
    onSuccess: (data) => {
      setTeamSuggestions(data);
      toast.success('Teams generated successfully!');
    },
    onError: (error) => {
      toast.error(error.userMessage || 'Failed to generate teams');
    },
  });

  // Toggle player selection
  const togglePlayer = (player) => {
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
  const selectAll = () => {
    setSelectedPlayers([...players]);
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedPlayers([]);
    setTeamSuggestions([]);
  };

  // Generate teams
  const generateTeams = () => {
    const playerIds = selectedPlayers.map((p) => p.id);
    balanceTeamsMutation.mutate(playerIds);
  };

  // Can generate teams?
  const canGenerate = selectedPlayers.length >= 6 && selectedPlayers.length % 2 === 0;
  const minPlayers = 6;
  const needMorePlayers = selectedPlayers.length < minPlayers;
  const needEvenPlayers = selectedPlayers.length >= minPlayers && selectedPlayers.length % 2 !== 0;

  // Export team composition
  const handleExport = async (suggestion, format) => {
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
          <Heading>Generate Teams</Heading>
          <LoadingState variant="players" count={8} />
        </VStack>
      </Container>
    );
  }

  if (!players || players.length === 0) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading>Generate Teams</Heading>
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
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="xl" mb={2}>
            Generate Balanced Teams
          </Heading>
          <Text color="gray.500">
            Select players and generate fair team compositions for your next game
          </Text>
        </Box>

        {/* Player Selection Section */}
        <Box>
          <HStack justify="space-between" mb={4}>
            <VStack align="start" spacing={1}>
              <Heading size="md">Select Players</Heading>
              <HStack>
                <Badge colorScheme={canGenerate ? 'green' : 'orange'} fontSize="md">
                  {selectedPlayers.length} players selected
                </Badge>
                {needMorePlayers && (
                  <Text fontSize="sm" color="gray.500">
                    (minimum {minPlayers} required)
                  </Text>
                )}
                {needEvenPlayers && (
                  <Text fontSize="sm" color="orange.500">
                    (need even number of players)
                  </Text>
                )}
              </HStack>
            </VStack>

            <HStack>
              <Button size="sm" variant="ghost" onClick={clearSelection}>
                Clear
              </Button>
              <Button size="sm" variant="outline" onClick={selectAll}>
                Select All
              </Button>
            </HStack>
          </HStack>

          <SimpleGrid columns={{ base: 2, md: 3, lg: 4, xl: 5 }} spacing={4}>
            {players.map((player) => (
              <PlayerCard
                key={player.id}
                player={player}
                isSelected={selectedPlayers.some((p) => p.id === player.id)}
                onClick={() => togglePlayer(player)}
                size="lg"
              />
            ))}
          </SimpleGrid>
        </Box>

        {/* Generate Button */}
        <Box textAlign="center" py={4}>
          <Button
            size="lg"
            variant="primary"
            isDisabled={!canGenerate}
            isLoading={balanceTeamsMutation.isPending}
            loadingText="Analyzing combinations..."
            onClick={generateTeams}
            leftIcon={balanceTeamsMutation.isPending ? <Spinner size="sm" /> : undefined}
            px={12}
            py={6}
            fontSize="xl"
          >
            Generate Teams
          </Button>

          {!canGenerate && selectedPlayers.length > 0 && (
            <Text color="gray.500" mt={2} fontSize="sm">
              {needMorePlayers
                ? `Select at least ${minPlayers - selectedPlayers.length} more players`
                : 'Select one more player for even teams'}
            </Text>
          )}
        </Box>

        {/* Team Results Section */}
        {balanceTeamsMutation.isPending && (
          <VStack spacing={4}>
            <TeamResultSkeleton />
            <TeamResultSkeleton />
            <TeamResultSkeleton />
          </VStack>
        )}

        {teamSuggestions.length > 0 && !balanceTeamsMutation.isPending && (
          <Box>
            <Heading size="md" mb={4}>
              Team Suggestions
            </Heading>

            <VStack spacing={4} align="stretch">
              {teamSuggestions.map((suggestion, index) => (
                <TeamSuggestionCard
                  key={index}
                  suggestion={suggestion}
                  index={index}
                  isRecommended={index === 0}
                  onExport={handleExport}
                />
              ))}
            </VStack>
          </Box>
        )}
      </VStack>
    </Container>
  );
};

// Team Suggestion Card Component
const TeamSuggestionCard = ({ suggestion, index, isRecommended, onExport }) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const labels = ['Most Balanced', 'Best Synergies', 'Alternative'];
  const label = labels[index] || `Option ${index + 1}`;

  const team1WinProb = (suggestion.win_probability_team_1 * 100).toFixed(1);
  const team2WinProb = (suggestion.win_probability_team_2 * 100).toFixed(1);

  return (
    <Card
      bg={bgColor}
      borderWidth={2}
      borderColor={isRecommended ? 'brand.500' : borderColor}
      position="relative"
    >
      {isRecommended && (
        <Badge
          position="absolute"
          top={-3}
          right={4}
          colorScheme="brand"
          fontSize="sm"
          px={3}
          py={1}
        >
          ⭐ Recommended
        </Badge>
      )}

      <CardHeader>
        <VStack align="stretch" spacing={2}>
          <Heading size="md">{label}</Heading>

          {/* Win Probability */}
          <HStack justify="space-between" fontSize="2xl" fontWeight="bold">
            <Text color="blue.500">{team1WinProb}%</Text>
            <Text color="gray.500">vs</Text>
            <Text color="orange.500">{team2WinProb}%</Text>
          </HStack>

          {/* Balance Indicator */}
          <Box>
            <Progress
              value={suggestion.win_probability_team_1 * 100}
              size="sm"
              colorScheme={
                Math.abs(suggestion.win_probability_team_1 - 0.5) < 0.05
                  ? 'green'
                  : Math.abs(suggestion.win_probability_team_1 - 0.5) < 0.1
                  ? 'blue'
                  : 'yellow'
              }
              borderRadius="full"
            />
            <HStack justify="space-between" mt={1}>
              <Badge colorScheme={getFairnessColor(suggestion.fairness_rating)}>
                {suggestion.fairness_rating}
              </Badge>
              <Text fontSize="xs" color="gray.500">
                MMR Diff: {formatMMR(suggestion.mmr_difference)}
              </Text>
            </HStack>
          </Box>
        </VStack>
      </CardHeader>

      <CardBody>
        <HStack spacing={4} align="start">
          {/* Team 1 */}
          <VStack flex={1} align="stretch" spacing={2}>
            <Heading size="sm" color="blue.500">
              Team 1
            </Heading>
            <Divider />
            {suggestion.team_1.players.map((player) => (
              <PlayerCard key={player.id} player={player} size="sm" />
            ))}
            <Text fontSize="sm" color="gray.500" textAlign="center">
              Avg MMR: {formatMMR(suggestion.team_1.avg_mmr)}
            </Text>
          </VStack>

          {/* Team 2 */}
          <VStack flex={1} align="stretch" spacing={2}>
            <Heading size="sm" color="orange.500">
              Team 2
            </Heading>
            <Divider />
            {suggestion.team_2.players.map((player) => (
              <PlayerCard key={player.id} player={player} size="sm" />
            ))}
            <Text fontSize="sm" color="gray.500" textAlign="center">
              Avg MMR: {formatMMR(suggestion.team_2.avg_mmr)}
            </Text>
          </VStack>
        </HStack>

        {/* Export Actions */}
        <HStack justify="center" mt={6}>
          <Menu>
            <MenuButton
              as={Button}
              rightIcon={<FiChevronDown />}
              leftIcon={<FiShare2 />}
              variant="outline"
              size="sm"
            >
              Share
            </MenuButton>
            <MenuList>
              <MenuItem icon={<FiCopy />} onClick={() => onExport(suggestion, 'text')}>
                Copy as Text
              </MenuItem>
              <MenuItem icon={<FiDownload />} onClick={() => onExport(suggestion, 'download')}>
                Download as File
              </MenuItem>
            </MenuList>
          </Menu>
        </HStack>
      </CardBody>
    </Card>
  );
};

export default TeamGenerator;
