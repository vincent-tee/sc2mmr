/**
 * HeadToHead Page
 * Player vs Player comparison with rivalry analysis
 */
import React, { useState, useMemo, useCallback, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  SimpleGrid,
  Button,
  Badge,
  Flex,
  Select,
  useColorModeValue,
  Skeleton,
  Alert,
  AlertIcon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { keyframes } from '@emotion/react';
import { FiTarget } from 'react-icons/fi';
import { headToHeadApi } from '../api/headtohead';
import { playersApi } from '../api/endpoints';
import {
  RivalryResponse,
  getIntensityConfig,
  formatDuration,
  getH2HWinRate,
} from '../types/headtohead';
import { colors } from '../theme/tokens';
import VSScreen from '../components/VSScreen';

// =============================================================================
// Animations
// =============================================================================

// Pulse glow animation - available for future use
// const pulseGlow = keyframes`
//   0%, 100% { box-shadow: 0 0 10px rgba(255, 140, 26, 0.3); }
//   50% { box-shadow: 0 0 25px rgba(255, 140, 26, 0.6); }
// `;

const fillAnimation = keyframes`
  from { width: 0%; }
  to { width: var(--fill-width); }
`;

// =============================================================================
// Helper Components
// =============================================================================

interface RivalryMeterProps {
  score: number;
  intensity: string;
  gamesPlayed: number;
}

const RivalryMeter: React.FC<RivalryMeterProps> = React.memo(({ score, intensity, gamesPlayed }) => {
  const config = getIntensityConfig(intensity as 'Casual' | 'Competitive' | 'Fierce' | 'Epic');
  const cardBg = useColorModeValue('gray.800', 'space.800');

  return (
    <Box
      bg={cardBg}
      borderRadius="xl"
      border="2px solid"
      borderColor={config.color}
      p={6}
      position="relative"
      overflow="hidden"
      boxShadow={config.glowColor ? `0 0 20px ${config.glowColor}` : 'none'}
    >
      <VStack spacing={4}>
        {/* Header */}
        <HStack justify="space-between" w="100%">
          <Text color="gray.500" fontSize="sm" textTransform="uppercase" letterSpacing="wider">
            Rivalry Intensity
          </Text>
          <Badge
            bg={config.bgColor}
            color={config.color}
            px={3}
            py={1}
            borderRadius="full"
            fontWeight="bold"
          >
            {intensity}
          </Badge>
        </HStack>

        {/* Score Display */}
        <Text
          fontSize="5xl"
          fontWeight="black"
          fontFamily="heading"
          color={config.color}
          textShadow={`0 0 30px ${config.glowColor}`}
        >
          {Math.round(score)}
        </Text>

        {/* Progress Bar */}
        <Box w="100%" position="relative">
          <Box
            w="100%"
            h="8px"
            bg="whiteAlpha.200"
            borderRadius="full"
            overflow="hidden"
          >
            <Box
              h="100%"
              bg={config.color}
              borderRadius="full"
              style={{ '--fill-width': `${Math.min(score, 100)}%` } as React.CSSProperties}
              animation={`${fillAnimation} 1s ease-out forwards`}
              boxShadow={`0 0 10px ${config.color}`}
            />
          </Box>
          {/* Markers */}
          <HStack justify="space-between" mt={1}>
            <Text fontSize="xs" color="gray.500">0</Text>
            <Text fontSize="xs" color="gray.500">40</Text>
            <Text fontSize="xs" color="gray.500">60</Text>
            <Text fontSize="xs" color="gray.500">80</Text>
            <Text fontSize="xs" color="gray.500">100+</Text>
          </HStack>
        </Box>

        {/* Games Played */}
        <Text color="gray.400" fontSize="sm">
          Based on <Text as="span" color={config.color} fontWeight="bold">{gamesPlayed}</Text> head-to-head games
        </Text>
      </VStack>
    </Box>
  );
});

RivalryMeter.displayName = 'RivalryMeter';

interface PlayerSelectorProps {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
  players: Array<{ id: number; name: string; mmr: number }>;
  excludeId?: number | null;
}

const PlayerSelector: React.FC<PlayerSelectorProps> = React.memo(({
  label,
  value,
  onChange,
  players,
  excludeId,
}) => {
  const cardBg = useColorModeValue('gray.800', 'space.800');

  const filteredPlayers = useMemo(() => {
    return players.filter(p => p.id !== excludeId);
  }, [players, excludeId]);

  return (
    <VStack align="stretch" spacing={2}>
      <Text color="gray.500" fontSize="sm" fontWeight="bold" textTransform="uppercase">
        {label}
      </Text>
      <Select
        value={value || ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        bg={cardBg}
        border="2px solid"
        borderColor="whiteAlpha.200"
        size="lg"
        fontFamily="heading"
        _hover={{ borderColor: 'brand.500' }}
        _focus={{ borderColor: 'brand.500', boxShadow: '0 0 10px rgba(255, 140, 26, 0.3)' }}
      >
        <option value="">Select player...</option>
        {filteredPlayers.map((player) => (
          <option key={player.id} value={player.id}>
            {player.name} ({Math.round(player.mmr)} MMR)
          </option>
        ))}
      </Select>
    </VStack>
  );
});

PlayerSelector.displayName = 'PlayerSelector';

interface RivalryCardProps {
  rivalry: RivalryResponse;
  onClick: () => void;
}

const RivalryCard: React.FC<RivalryCardProps> = React.memo(({ rivalry, onClick }) => {
  const config = getIntensityConfig(rivalry.intensity as 'Casual' | 'Competitive' | 'Fierce' | 'Epic');
  const cardBg = useColorModeValue('gray.800', 'space.800');

  return (
    <Box
      bg={cardBg}
      borderRadius="lg"
      border="1px solid"
      borderColor="whiteAlpha.100"
      p={4}
      cursor="pointer"
      transition="all 0.3s"
      _hover={{
        borderColor: config.color,
        transform: 'translateY(-2px)',
        boxShadow: `0 0 15px ${config.glowColor}`,
      }}
      onClick={onClick}
    >
      <HStack justify="space-between">
        <VStack align="start" spacing={1}>
          <HStack>
            <Text fontWeight="bold" color="gray.100">
              {rivalry.player1_name}
            </Text>
            <Text color="gray.500">vs</Text>
            <Text fontWeight="bold" color="gray.100">
              {rivalry.player2_name}
            </Text>
          </HStack>
          <Text color="gray.500" fontSize="sm">
            {rivalry.games} games played
          </Text>
        </VStack>
        <VStack align="end" spacing={1}>
          <Badge
            bg={config.bgColor}
            color={config.color}
            px={2}
            py={1}
            borderRadius="md"
          >
            {rivalry.intensity}
          </Badge>
          <Text color={config.color} fontWeight="bold" fontFamily="mono">
            {Math.round(rivalry.score)}
          </Text>
        </VStack>
      </HStack>
    </Box>
  );
});

RivalryCard.displayName = 'RivalryCard';

// =============================================================================
// Main Component
// =============================================================================

const HeadToHead: React.FC = () => {
  const navigate = useNavigate();
  const { player1Id, player2Id } = useParams<{ player1Id?: string; player2Id?: string }>();

  const [selectedPlayer1, setSelectedPlayer1] = useState<number | null>(
    player1Id ? Number(player1Id) : null
  );
  const [selectedPlayer2, setSelectedPlayer2] = useState<number | null>(
    player2Id ? Number(player2Id) : null
  );

  const bgColor = useColorModeValue('gray.900', 'space.900');
  const cardBg = useColorModeValue('gray.800', 'space.800');

  // Update URL when players change
  useEffect(() => {
    if (selectedPlayer1 && selectedPlayer2) {
      navigate(`/h2h/${selectedPlayer1}/${selectedPlayer2}`, { replace: true });
    }
  }, [selectedPlayer1, selectedPlayer2, navigate]);

  // Fetch players list
  const { data: players } = useQuery({
    queryKey: ['players', 'all'],
    queryFn: async () => {
      const response = await playersApi.getAll(true);
      return response.data;
    },
    staleTime: 300000,
  });

  // Fetch H2H data
  const { data: h2hData, isLoading: h2hLoading, error: h2hError } = useQuery({
    queryKey: ['h2h', selectedPlayer1, selectedPlayer2],
    queryFn: async () => {
      if (!selectedPlayer1 || !selectedPlayer2) return null;
      const response = await headToHeadApi.getComparison(selectedPlayer1, selectedPlayer2);
      return response.data;
    },
    enabled: !!selectedPlayer1 && !!selectedPlayer2,
    staleTime: 60000,
  });

  // Fetch biggest rivalries
  const { data: biggestRivalries, isLoading: rivalriesLoading } = useQuery({
    queryKey: ['h2h', 'biggest'],
    queryFn: async () => {
      const response = await headToHeadApi.getBiggestRivalries(10);
      return response.data;
    },
    staleTime: 300000,
  });

  const handleCompare = useCallback(() => {
    if (selectedPlayer1 && selectedPlayer2) {
      navigate(`/h2h/${selectedPlayer1}/${selectedPlayer2}`);
    }
  }, [selectedPlayer1, selectedPlayer2, navigate]);

  const handleRivalryClick = useCallback((rivalry: RivalryResponse) => {
    setSelectedPlayer1(rivalry.player1_id);
    setSelectedPlayer2(rivalry.player2_id);
  }, []);

  // Build VS screen data
  const vsTeam1 = useMemo(() => {
    if (!h2hData) return null;
    return {
      players: [{
        name: h2hData.player1.name,
        mmr: h2hData.player1.mmr,
        race: h2hData.player1.favorite_race,
      }],
      totalMMR: h2hData.player1.mmr,
      winProbability: h2hData.head_to_head.win_rate_player1 * 100,
    };
  }, [h2hData]);

  const vsTeam2 = useMemo(() => {
    if (!h2hData) return null;
    return {
      players: [{
        name: h2hData.player2.name,
        mmr: h2hData.player2.mmr,
        race: h2hData.player2.favorite_race,
      }],
      totalMMR: h2hData.player2.mmr,
      winProbability: (1 - h2hData.head_to_head.win_rate_player1) * 100,
    };
  }, [h2hData]);

  return (
    <Box bg={bgColor} minH="100vh" py={8}>
      <Container maxW="container.xl">
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <Box textAlign="center">
            <Heading
              size="2xl"
              fontFamily="heading"
              color="brand.400"
              textShadow={`0 0 30px ${colors.brand[500]}60`}
              letterSpacing="wider"
            >
              ⚔️ HEAD TO HEAD
            </Heading>
            <Text color="gray.500" mt={2}>
              Compare players and discover rivalries
            </Text>
          </Box>

          {/* Player Selectors */}
          <Box
            bg={cardBg}
            borderRadius="xl"
            border="2px solid"
            borderColor="whiteAlpha.100"
            p={6}
          >
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} alignItems="end">
              <PlayerSelector
                label="Player 1"
                value={selectedPlayer1}
                onChange={setSelectedPlayer1}
                players={players || []}
                excludeId={selectedPlayer2}
              />

              <Flex justify="center" align="center" py={4}>
                <Text fontSize="2xl" fontWeight="black" color="brand.500">
                  VS
                </Text>
              </Flex>

              <PlayerSelector
                label="Player 2"
                value={selectedPlayer2}
                onChange={setSelectedPlayer2}
                players={players || []}
                excludeId={selectedPlayer1}
              />
            </SimpleGrid>

            <Flex justify="center" mt={6}>
              <Button
                colorScheme="brand"
                size="lg"
                onClick={handleCompare}
                isDisabled={!selectedPlayer1 || !selectedPlayer2}
                leftIcon={<FiTarget />}
                fontFamily="heading"
                fontWeight="bold"
                letterSpacing="wider"
              >
                COMPARE
              </Button>
            </Flex>
          </Box>

          {/* H2H Results */}
          {h2hLoading ? (
            <VStack spacing={4}>
              <Skeleton height="300px" width="100%" borderRadius="xl" />
              <Skeleton height="200px" width="100%" borderRadius="xl" />
            </VStack>
          ) : h2hError ? (
            <Alert status="error" borderRadius="md">
              <AlertIcon />
              Failed to load head-to-head data
            </Alert>
          ) : h2hData && vsTeam1 && vsTeam2 ? (
            <VStack spacing={6}>
              {/* VS Screen */}
              <VSScreen
                team1={vsTeam1}
                team2={vsTeam2}
                winner={
                  h2hData.head_to_head.player1_wins > h2hData.head_to_head.player2_wins ? 1 :
                  h2hData.head_to_head.player2_wins > h2hData.head_to_head.player1_wins ? 2 : null
                }
              />

              {/* Rivalry Meter */}
              <RivalryMeter
                score={h2hData.head_to_head.rivalry_score}
                intensity={h2hData.head_to_head.rivalry_intensity}
                gamesPlayed={h2hData.head_to_head.total_games}
              />

              {/* Stats Grid */}
              <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} w="100%">
                <Stat bg={cardBg} p={4} borderRadius="lg">
                  <StatLabel color="gray.500">Total Games</StatLabel>
                  <StatNumber color="brand.400">{h2hData.head_to_head.total_games}</StatNumber>
                </Stat>
                <Stat bg={cardBg} p={4} borderRadius="lg">
                  <StatLabel color="gray.500">{h2hData.player1.name} Wins</StatLabel>
                  <StatNumber color="shield.400">{h2hData.head_to_head.player1_wins}</StatNumber>
                  <StatHelpText>{getH2HWinRate(h2hData.head_to_head.player1_wins, h2hData.head_to_head.total_games)}</StatHelpText>
                </Stat>
                <Stat bg={cardBg} p={4} borderRadius="lg">
                  <StatLabel color="gray.500">{h2hData.player2.name} Wins</StatLabel>
                  <StatNumber color="accent.400">{h2hData.head_to_head.player2_wins}</StatNumber>
                  <StatHelpText>{getH2HWinRate(h2hData.head_to_head.player2_wins, h2hData.head_to_head.total_games)}</StatHelpText>
                </Stat>
                <Stat bg={cardBg} p={4} borderRadius="lg">
                  <StatLabel color="gray.500">Avg MMR Swing</StatLabel>
                  <StatNumber color="gray.200">±{Math.round(h2hData.head_to_head.avg_mmr_swing)}</StatNumber>
                </Stat>
              </SimpleGrid>

              {/* Recent Matches */}
              {h2hData.recent_matches.length > 0 && (
                <Box w="100%">
                  <Heading size="md" color="gray.200" mb={4} fontFamily="heading">
                    Recent Encounters
                  </Heading>
                  <VStack spacing={2} align="stretch">
                    {h2hData.recent_matches.map((match) => (
                      <HStack
                        key={match.match_id}
                        bg={cardBg}
                        p={3}
                        borderRadius="md"
                        justify="space-between"
                        cursor="pointer"
                        _hover={{ bg: 'whiteAlpha.100' }}
                        onClick={() => navigate(`/history/${match.match_id}`)}
                      >
                        <HStack>
                          <Badge
                            colorScheme={match.winner_id === selectedPlayer1 ? 'green' : 'red'}
                          >
                            {match.winner_id === selectedPlayer1 ? h2hData.player1.name : h2hData.player2.name}
                          </Badge>
                          <Text color="gray.400" fontSize="sm">won on</Text>
                          <Text color="gray.200">{match.map_name}</Text>
                        </HStack>
                        <Text color="gray.500" fontSize="sm">
                          {formatDuration(match.duration_seconds)}
                        </Text>
                      </HStack>
                    ))}
                  </VStack>
                </Box>
              )}
            </VStack>
          ) : null}

          {/* Biggest Rivalries */}
          <Box>
            <Heading size="lg" color="gray.200" mb={4} fontFamily="heading">
              🔥 Biggest Rivalries
            </Heading>
            {rivalriesLoading ? (
              <VStack spacing={2}>
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} height="70px" width="100%" borderRadius="lg" />
                ))}
              </VStack>
            ) : biggestRivalries && biggestRivalries.length > 0 ? (
              <VStack spacing={2} align="stretch">
                {biggestRivalries.map((rivalry) => (
                  <RivalryCard
                    key={`${rivalry.player1_id}-${rivalry.player2_id}`}
                    rivalry={rivalry}
                    onClick={() => handleRivalryClick(rivalry)}
                  />
                ))}
              </VStack>
            ) : (
              <Box textAlign="center" py={8}>
                <Text color="gray.500">No rivalries found yet</Text>
              </Box>
            )}
          </Box>
        </VStack>
      </Container>
    </Box>
  );
};

export default HeadToHead;
