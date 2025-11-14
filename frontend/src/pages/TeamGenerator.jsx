/**
 * Team Generator Page - TACTICAL DEPLOYMENT SYSTEM
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
  Divider,
  Progress,
  Icon,
  useColorModeValue,
  Spinner,
  Collapse,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
} from '@chakra-ui/react';
import { FiChevronDown, FiCopy, FiDownload, FiShare2, FiZap, FiUsers, FiCheck, FiX, FiTarget } from 'react-icons/fi';
import { useQuery, useMutation } from '@tanstack/react-query';
import { playersApi, teamsApi } from '../api/endpoints';
import PlayerCard from '../components/PlayerCard';
import TacticalCard from '../components/TacticalCard';
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
      <Box
        position="fixed"
        top={0}
        left={0}
        right={0}
        bottom={0}
        opacity={0.03}
        pointerEvents="none"
        backgroundImage="linear-gradient(rgba(0, 212, 255, 0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.5) 1px, transparent 1px)"
        backgroundSize="40px 40px"
        zIndex={0}
      />

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
                  content: '"◢"',
                  position: 'absolute',
                  left: '-50px',
                  color: 'brand.500',
                  fontSize: '2xl',
                }}
                _after={{
                  content: '"◣"',
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
          <Box>
            <TacticalCard variant="command" glowColor="rgba(0, 212, 255, 0.5)">
              <Box p={6}>
                <HStack justify="space-between" mb={6}>
                  <VStack align="start" spacing={2}>
                    <HStack>
                      <Icon as={FiUsers} color="brand.400" boxSize={6} />
                      <Heading
                        size="md"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wider"
                        color="brand.300"
                      >
                        OPERATIVE SELECTION
                      </Heading>
                    </HStack>
                    <HStack spacing={3}>
                      <Badge
                        colorScheme={canGenerate ? 'green' : 'orange'}
                        fontSize="lg"
                        px={3}
                        py={1}
                        fontFamily="heading"
                      >
                        {selectedPlayers.length} SELECTED
                      </Badge>
                      {needMorePlayers && (
                        <Text fontSize="sm" color="gray.500" fontFamily="heading">
                          (MIN {minPlayers} REQUIRED)
                        </Text>
                      )}
                      {needEvenPlayers && (
                        <Text fontSize="sm" color="orange.400" fontFamily="heading">
                          (EVEN NUMBER REQUIRED)
                        </Text>
                      )}
                    </HStack>
                  </VStack>

                  <HStack>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={clearSelection}
                      fontFamily="heading"
                      textTransform="uppercase"
                      leftIcon={<FiX />}
                    >
                      Clear
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={selectAll}
                      fontFamily="heading"
                      textTransform="uppercase"
                      leftIcon={<FiCheck />}
                    >
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
            </TacticalCard>
          </Box>

          {/* Generate Button */}
          <Box textAlign="center" py={6}>
            <Button
              size="lg"
              variant="accent"
              isDisabled={!canGenerate}
              isLoading={balanceTeamsMutation.isPending}
              loadingText="ANALYZING COMBINATIONS..."
              onClick={generateTeams}
              leftIcon={<FiZap />}
              px={16}
              py={8}
              fontSize="2xl"
              fontFamily="heading"
              textTransform="uppercase"
              letterSpacing="wider"
              position="relative"
              overflow="visible"
              _before={{
                content: '""',
                position: 'absolute',
                top: -2,
                left: -2,
                right: -2,
                bottom: -2,
                background: 'linear-gradient(45deg, transparent, rgba(255, 179, 0, 0.3), transparent)',
                animation: canGenerate ? 'shimmer 2s ease-in-out infinite' : 'none',
                borderRadius: 'md',
                zIndex: -1,
              }}
              sx={{
                '@keyframes shimmer': {
                  '0%, 100%': { opacity: 0.5 },
                  '50%': { opacity: 1 },
                },
              }}
            >
              ⚡ GENERATE TEAMS
            </Button>

            {!canGenerate && selectedPlayers.length > 0 && (
              <Text
                color="gray.500"
                mt={4}
                fontSize="sm"
                fontFamily="heading"
                textTransform="uppercase"
              >
                {needMorePlayers
                  ? `SELECT ${minPlayers - selectedPlayers.length} MORE OPERATIVES`
                  : 'SELECT ONE MORE FOR EVEN TEAMS'}
              </Text>
            )}
          </Box>

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
                ⚡ CALCULATING OPTIMAL CONFIGURATIONS...
              </Text>
              <TeamResultSkeleton />
              <TeamResultSkeleton />
              <TeamResultSkeleton />
            </VStack>
          )}

          {teamSuggestions.length > 0 && !balanceTeamsMutation.isPending && (
            <Box>
              <Heading
                size="lg"
                mb={6}
                fontFamily="heading"
                textTransform="uppercase"
                letterSpacing="wider"
                color="brand.400"
                textAlign="center"
              >
                ▸ DEPLOYMENT CONFIGURATIONS
              </Heading>

              <VStack spacing={6} align="stretch">
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
    </Box>
  );
};

// Team Suggestion Card Component
const TeamSuggestionCard = ({ suggestion, index, isRecommended, onExport }) => {
  const labels = ['OPTIMAL BALANCE', 'TACTICAL SYNERGY', 'ALTERNATIVE CONFIG'];
  const label = labels[index] || `CONFIG ${index + 1}`;

  const team1WinProb = (suggestion.win_probability_team_1 * 100).toFixed(1);
  const team2WinProb = (suggestion.win_probability_team_2 * 100).toFixed(1);

  return (
    <TacticalCard
      variant={isRecommended ? 'command' : index % 2 === 0 ? 'angled' : 'default'}
      glowColor={isRecommended ? 'rgba(0, 255, 136, 0.6)' : 'rgba(0, 212, 255, 0.4)'}
    >
      <Box p={6} position="relative">
        {isRecommended && (
          <Badge
            position="absolute"
            top={4}
            right={4}
            bg="shield.500"
            color="gray.900"
            fontSize="md"
            px={4}
            py={2}
            fontFamily="heading"
            textTransform="uppercase"
            boxShadow="0 0 20px rgba(0, 255, 136, 0.5)"
          >
            ⭐ RECOMMENDED
          </Badge>
        )}

        <VStack align="stretch" spacing={6}>
          {/* Header */}
          <Box>
            <Heading
              size="lg"
              fontFamily="heading"
              textTransform="uppercase"
              letterSpacing="wider"
              color="brand.300"
              mb={4}
            >
              {label}
            </Heading>

            {/* Win Probability Display */}
            <HStack justify="space-between" mb={4}>
              <VStack spacing={1} align="start">
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  TEAM 1 WIN PROB
                </Text>
                <Text
                  fontSize="4xl"
                  fontWeight="black"
                  fontFamily="heading"
                  color="brand.400"
                  textShadow="0 0 20px rgba(0, 212, 255, 0.5)"
                >
                  {team1WinProb}%
                </Text>
              </VStack>

              <Box textAlign="center">
                <Icon as={FiTarget} boxSize={12} color="accent.500" />
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  VS
                </Text>
              </Box>

              <VStack spacing={1} align="end">
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  TEAM 2 WIN PROB
                </Text>
                <Text
                  fontSize="4xl"
                  fontWeight="black"
                  fontFamily="heading"
                  color="accent.400"
                  textShadow="0 0 20px rgba(255, 179, 0, 0.5)"
                >
                  {team2WinProb}%
                </Text>
              </VStack>
            </HStack>

            {/* Balance Indicator */}
            <Box>
              <Progress
                value={suggestion.win_probability_team_1 * 100}
                size="lg"
                colorScheme={
                  Math.abs(suggestion.win_probability_team_1 - 0.5) < 0.05
                    ? 'green'
                    : Math.abs(suggestion.win_probability_team_1 - 0.5) < 0.1
                    ? 'blue'
                    : 'yellow'
                }
                borderRadius="md"
                bg="whiteAlpha.100"
                sx={{
                  '& > div': {
                    transition: 'all 0.3s',
                  },
                }}
              />
              <HStack justify="space-between" mt={3}>
                <Badge
                  colorScheme={getFairnessColor(suggestion.fairness_rating)}
                  fontSize="md"
                  px={3}
                  py={1}
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  {suggestion.fairness_rating}
                </Badge>
                <Text
                  fontSize="sm"
                  color="gray.400"
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  MMR DIFF: {formatMMR(suggestion.mmr_difference)}
                </Text>
              </HStack>
            </Box>
          </Box>

          <Divider borderColor="whiteAlpha.200" />

          {/* Teams Display */}
          <HStack spacing={6} align="start">
            {/* Team 1 */}
            <VStack flex={1} align="stretch" spacing={4}>
              <Box
                bg="brand.500"
                px={4}
                py={2}
                clipPath="polygon(0 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%)"
              >
                <Heading
                  size="md"
                  fontFamily="heading"
                  textTransform="uppercase"
                  color="gray.900"
                  letterSpacing="wider"
                >
                  ◢ TEAM 1
                </Heading>
              </Box>
              <VStack spacing={2} align="stretch">
                {suggestion.team_1.players.map((player) => (
                  <PlayerCard key={player.id} player={player} size="sm" />
                ))}
              </VStack>
              <Box
                bg="whiteAlpha.50"
                p={3}
                borderRadius="md"
                border="1px solid"
                borderColor="brand.400"
                textAlign="center"
              >
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                  mb={1}
                >
                  Average MMR
                </Text>
                <Text
                  fontSize="2xl"
                  fontWeight="black"
                  fontFamily="heading"
                  color="brand.400"
                >
                  {formatMMR(suggestion.team_1.avg_mmr)}
                </Text>
              </Box>
            </VStack>

            {/* Team 2 */}
            <VStack flex={1} align="stretch" spacing={4}>
              <Box
                bg="accent.500"
                px={4}
                py={2}
                clipPath="polygon(8px 0, 100% 0, 100% 100%, 0 100%, 0 8px)"
              >
                <Heading
                  size="md"
                  fontFamily="heading"
                  textTransform="uppercase"
                  color="gray.900"
                  letterSpacing="wider"
                >
                  TEAM 2 ◣
                </Heading>
              </Box>
              <VStack spacing={2} align="stretch">
                {suggestion.team_2.players.map((player) => (
                  <PlayerCard key={player.id} player={player} size="sm" />
                ))}
              </VStack>
              <Box
                bg="whiteAlpha.50"
                p={3}
                borderRadius="md"
                border="1px solid"
                borderColor="accent.400"
                textAlign="center"
              >
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                  mb={1}
                >
                  Average MMR
                </Text>
                <Text
                  fontSize="2xl"
                  fontWeight="black"
                  fontFamily="heading"
                  color="accent.400"
                >
                  {formatMMR(suggestion.team_2.avg_mmr)}
                </Text>
              </Box>
            </VStack>
          </HStack>

          {/* Export Actions */}
          <HStack justify="center" pt={4}>
            <Menu>
              <MenuButton
                as={Button}
                rightIcon={<FiChevronDown />}
                leftIcon={<FiShare2 />}
                variant="outline"
                size="md"
                fontFamily="heading"
                textTransform="uppercase"
                borderColor="brand.400"
                _hover={{
                  bg: 'whiteAlpha.100',
                  borderColor: 'brand.300',
                }}
              >
                Share Config
              </MenuButton>
              <MenuList bg="gray.800" borderColor="brand.500">
                <MenuItem
                  icon={<FiCopy />}
                  onClick={() => onExport(suggestion, 'text')}
                  fontFamily="heading"
                  textTransform="uppercase"
                  fontSize="sm"
                  _hover={{ bg: 'whiteAlpha.100' }}
                >
                  Copy as Text
                </MenuItem>
                <MenuItem
                  icon={<FiDownload />}
                  onClick={() => onExport(suggestion, 'download')}
                  fontFamily="heading"
                  textTransform="uppercase"
                  fontSize="sm"
                  _hover={{ bg: 'whiteAlpha.100' }}
                >
                  Download File
                </MenuItem>
              </MenuList>
            </Menu>
          </HStack>
        </VStack>
      </Box>
    </TacticalCard>
  );
};

export default TeamGenerator;
