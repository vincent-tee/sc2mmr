/**
 * Home/Dashboard Page
 * Tactical Command Center Interface
 */
import {
  Box,
  Container,
  Heading,
  Text,
  Button,
  SimpleGrid,
  VStack,
  HStack,
  Icon,
  Flex,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiUpload, FiUsers, FiZap, FiTrendingUp, FiTarget, FiActivity } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi, replaysApi } from '../api/endpoints';
import TacticalCard from '../components/TacticalCard';
import HexagonalStat from '../components/HexagonalStat';
import { formatDateOnly } from '../utils/formatting';

const Home = () => {
  const navigate = useNavigate();
  const accentGlow = useColorModeValue('rgba(255, 179, 0, 0.2)', 'rgba(255, 179, 0, 0.1)');

  // Fetch stats
  const { data: playersData, isLoading: loadingPlayers } = useQuery({
    queryKey: ['players'],
    queryFn: async () => {
      const response = await playersApi.getAll();
      return response.data;
    },
  });

  const { data: matchesData, isLoading: loadingMatches } = useQuery({
    queryKey: ['matches'],
    queryFn: async () => {
      const response = await replaysApi.getMatches(10);
      return response.data;
    },
  });

  const players = playersData || [];
  const matches = matchesData || [];

  // Calculate stats
  const totalPlayers = players.length;
  const totalGames = players.reduce((sum, p) => sum + (p.total_games || 0), 0);
  const avgMMR =
    players.length > 0
      ? Math.round(players.reduce((sum, p) => sum + p.mmr, 0) / players.length)
      : 0;

  const isLoading = loadingPlayers || loadingMatches;

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
        <VStack spacing={12} align="stretch">
          {/* Tactical Hero Section */}
          <Box position="relative" textAlign="center" py={12}>
            {/* Title with dramatic styling */}
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
                  left: '-40px',
                  color: 'brand.500',
                  fontSize: '2xl',
                }}
                _after={{
                  content: '"◣"',
                  position: 'absolute',
                  right: '-40px',
                  color: 'brand.500',
                  fontSize: '2xl',
                }}
              >
                TACTICAL COMMAND
              </Box>
            </Heading>

            <Text
              fontSize="xl"
              color="gray.400"
              mb={8}
              fontFamily="heading"
              letterSpacing="wide"
              textTransform="uppercase"
            >
              [ MMR TRACKING & TEAM BALANCING SYSTEM ]
            </Text>

            {/* Primary action with dramatic styling */}
            <HStack spacing={6} justify="center" mt={8}>
              <Button
                size="lg"
                variant="accent"
                leftIcon={<FiZap />}
                onClick={() => navigate('/balance')}
                fontSize="lg"
                px={8}
                py={7}
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
                  animation: 'shimmer 2s ease-in-out infinite',
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
              <Button
                size="lg"
                variant="primary"
                leftIcon={<FiUpload />}
                onClick={() => navigate('/upload')}
                fontSize="lg"
                px={8}
                py={7}
              >
                UPLOAD REPLAYS
              </Button>
            </HStack>
          </Box>

          {/* Hexagonal Stats Display */}
          <Box>
            <Heading
              size="md"
              mb={8}
              textAlign="center"
              fontFamily="heading"
              textTransform="uppercase"
              letterSpacing="wider"
              color="brand.400"
            >
              — SYSTEM STATUS —
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={8}>
              <HexagonalStat
                label="OPERATIVES"
                value={isLoading ? '—' : totalPlayers}
                subtext="Active Players"
                color="brand.500"
              />
              <HexagonalStat
                label="MISSIONS"
                value={isLoading ? '—' : totalGames}
                subtext="Completed"
                color="accent.500"
              />
              <HexagonalStat
                label="AVG RATING"
                value={isLoading ? '—' : avgMMR}
                subtext="MMR Score"
                color="shield.500"
              />
            </SimpleGrid>
          </Box>

          {/* Tactical Command Grid */}
          <Box>
            <Heading
              size="md"
              mb={6}
              fontFamily="heading"
              textTransform="uppercase"
              letterSpacing="wider"
              color="brand.400"
            >
              ▸ COMMAND MODULES
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
              <TacticalCard
                variant="command"
                glowColor="rgba(0, 212, 255, 0.6)"
                onClick={() => navigate('/balance')}
              >
                <VStack align="start" spacing={3}>
                  <HStack>
                    <Box
                      bg="brand.500"
                      p={3}
                      borderRadius="md"
                      boxShadow="0 0 20px rgba(0, 212, 255, 0.4)"
                    >
                      <Icon as={FiZap} boxSize={8} color="gray.900" />
                    </Box>
                    <VStack align="start" spacing={0}>
                      <Text
                        fontWeight="black"
                        fontSize="xl"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wide"
                      >
                        TEAM GENERATOR
                      </Text>
                      <Text fontSize="xs" color="brand.400" fontFamily="heading">
                        PRIMARY SYSTEM
                      </Text>
                    </VStack>
                  </HStack>
                  <Text color="gray.500" fontSize="sm">
                    Generate balanced team compositions using advanced MMR algorithms.
                    Fair matches guaranteed.
                  </Text>
                </VStack>
              </TacticalCard>

              <TacticalCard
                variant="angled"
                glowColor="rgba(255, 179, 0, 0.6)"
                onClick={() => navigate('/upload')}
              >
                <VStack align="start" spacing={3}>
                  <HStack>
                    <Box
                      bg="accent.500"
                      p={3}
                      borderRadius="md"
                      boxShadow="0 0 20px rgba(255, 179, 0, 0.4)"
                    >
                      <Icon as={FiUpload} boxSize={8} color="gray.900" />
                    </Box>
                    <VStack align="start" spacing={0}>
                      <Text
                        fontWeight="black"
                        fontSize="xl"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wide"
                      >
                        REPLAY UPLOAD
                      </Text>
                      <Text fontSize="xs" color="accent.400" fontFamily="heading">
                        DATA PROCESSING
                      </Text>
                    </VStack>
                  </HStack>
                  <Text color="gray.500" fontSize="sm">
                    Import SC2 replay files for automatic analysis and rating updates.
                  </Text>
                </VStack>
              </TacticalCard>

              <TacticalCard
                variant="default"
                glowColor="rgba(156, 39, 176, 0.6)"
                onClick={() => navigate('/players')}
              >
                <VStack align="start" spacing={3}>
                  <HStack>
                    <Box
                      bg="zerg.500"
                      p={3}
                      borderRadius="md"
                      boxShadow="0 0 20px rgba(156, 39, 176, 0.4)"
                    >
                      <Icon as={FiUsers} boxSize={8} color="white" />
                    </Box>
                    <VStack align="start" spacing={0}>
                      <Text
                        fontWeight="black"
                        fontSize="xl"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wide"
                      >
                        PLAYER ROSTER
                      </Text>
                      <Text fontSize="xs" color="zerg.400" fontFamily="heading">
                        PERSONNEL DATABASE
                      </Text>
                    </VStack>
                  </HStack>
                  <Text color="gray.500" fontSize="sm">
                    View detailed player statistics, ratings, and performance metrics.
                  </Text>
                </VStack>
              </TacticalCard>

              <TacticalCard
                variant="angled"
                glowColor="rgba(0, 255, 136, 0.6)"
                onClick={() => navigate('/history')}
              >
                <VStack align="start" spacing={3}>
                  <HStack>
                    <Box
                      bg="shield.500"
                      p={3}
                      borderRadius="md"
                      boxShadow="0 0 20px rgba(0, 255, 136, 0.4)"
                    >
                      <Icon as={FiTrendingUp} boxSize={8} color="gray.900" />
                    </Box>
                    <VStack align="start" spacing={0}>
                      <Text
                        fontWeight="black"
                        fontSize="xl"
                        fontFamily="heading"
                        textTransform="uppercase"
                        letterSpacing="wide"
                      >
                        MATCH ARCHIVE
                      </Text>
                      <Text fontSize="xs" color="shield.400" fontFamily="heading">
                        HISTORICAL DATA
                      </Text>
                    </VStack>
                  </HStack>
                  <Text color="gray.500" fontSize="sm">
                    Browse complete match history with AI-powered analysis and insights.
                  </Text>
                </VStack>
              </TacticalCard>
            </SimpleGrid>
          </Box>

          {/* Recent Activity with tactical styling */}
          {matches.length > 0 && (
            <Box>
              <HStack justify="space-between" mb={6}>
                <Heading
                  size="md"
                  fontFamily="heading"
                  textTransform="uppercase"
                  letterSpacing="wider"
                  color="brand.400"
                >
                  ▸ RECENT OPERATIONS
                </Heading>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => navigate('/history')}
                  fontFamily="heading"
                >
                  VIEW ALL →
                </Button>
              </HStack>
              <VStack spacing={3} align="stretch">
                {matches.slice(0, 5).map((match) => (
                  <TacticalCard
                    key={match.id}
                    variant="command"
                    glowColor="rgba(0, 212, 255, 0.4)"
                    onClick={() => navigate(`/history/${match.id}`)}
                  >
                    <Flex justify="space-between" align="center">
                      <HStack spacing={4}>
                        <Box
                          bg="brand.500"
                          p={2}
                          borderRadius="md"
                          boxShadow="0 0 10px rgba(0, 212, 255, 0.3)"
                        >
                          <Icon as={FiActivity} boxSize={5} color="gray.900" />
                        </Box>
                        <VStack align="start" spacing={0}>
                          <Text
                            fontWeight="bold"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wide"
                          >
                            {match.map_name}
                          </Text>
                          <Text fontSize="sm" color="gray.500" fontFamily="heading">
                            {match.game_mode} • {formatDateOnly(match.played_at)}
                          </Text>
                        </VStack>
                      </HStack>
                      <Icon as={FiTarget} color="brand.400" />
                    </Flex>
                  </TacticalCard>
                ))}
              </VStack>
            </Box>
          )}
        </VStack>
      </Container>
    </Box>
  );
};

export default Home;
