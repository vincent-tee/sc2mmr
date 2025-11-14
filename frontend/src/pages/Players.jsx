/**
 * Players List Page - Tactical Operative Database
 * View all players with statistics
 */
import {
  Box,
  Container,
  Heading,
  Text,
  SimpleGrid,
  VStack,
  HStack,
  Input,
  Select,
  InputGroup,
  InputLeftElement,
  Icon,
  Badge,
  Avatar,
  Progress,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiSearch, FiFilter, FiTarget } from 'react-icons/fi';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi } from '../api/endpoints';
import TacticalCard from '../components/TacticalCard';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import { formatMMR, formatWinRate, getPlayerRaces, getRaceColor } from '../utils/formatting';

const Players = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('mmr'); // mmr, name, games

  const cardBg = useColorModeValue('white', 'gray.800');

  // Fetch players
  const { data: playersData, isLoading } = useQuery({
    queryKey: ['players'],
    queryFn: async () => {
      const response = await playersApi.getAll();
      return response.data;
    },
  });

  const players = playersData || [];

  // Filter and sort players
  const filteredPlayers = players
    .filter((player) =>
      player.name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'mmr':
          return b.mmr - a.mmr;
        case 'name':
          return a.name.localeCompare(b.name);
        case 'games':
          return b.total_games - a.total_games;
        default:
          return 0;
      }
    });

  if (isLoading) {
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
            OPERATIVE DATABASE
          </Heading>
          <LoadingState variant="players" count={8} />
        </VStack>
      </Container>
    );
  }

  if (players.length === 0) {
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
            OPERATIVE DATABASE
          </Heading>
          <EmptyState
            variant="players"
            onAction={() => navigate('/upload')}
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
              size="2xl"
              fontFamily="heading"
              fontWeight="black"
              textTransform="uppercase"
              letterSpacing="wider"
              mb={2}
              color="brand.400"
              textShadow="0 0 30px rgba(0, 212, 255, 0.6)"
              position="relative"
            >
              <Box
                as="span"
                display="inline-block"
                position="relative"
                _before={{
                  content: '"▸"',
                  position: 'absolute',
                  left: '-40px',
                  color: 'brand.500',
                  fontSize: 'xl',
                }}
                _after={{
                  content: '"◂"',
                  position: 'absolute',
                  right: '-40px',
                  color: 'brand.500',
                  fontSize: 'xl',
                }}
              >
                OPERATIVE DATABASE
              </Box>
            </Heading>
            <Text
              fontSize="md"
              color="gray.400"
              fontFamily="heading"
              letterSpacing="wide"
              textTransform="uppercase"
            >
              [ {players.length} ACTIVE OPERATIVES ]
            </Text>
          </Box>

          {/* Tactical Filters */}
          <TacticalCard variant="command" glowColor="rgba(0, 212, 255, 0.4)">
            <Box p={4}>
              <HStack spacing={4}>
                <InputGroup flex={1}>
                  <InputLeftElement pointerEvents="none">
                    <Icon as={FiSearch} color="brand.400" />
                  </InputLeftElement>
                  <Input
                    placeholder="SEARCH OPERATIVES..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    textTransform="uppercase"
                    fontFamily="heading"
                    letterSpacing="wide"
                    borderColor="whiteAlpha.200"
                    _placeholder={{ color: 'gray.600' }}
                    _focus={{
                      borderColor: 'brand.500',
                      boxShadow: '0 0 10px rgba(0, 212, 255, 0.3)',
                    }}
                  />
                </InputGroup>

                <HStack>
                  <Icon as={FiFilter} color="brand.400" />
                  <Select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    maxW="250px"
                    fontFamily="heading"
                    textTransform="uppercase"
                    letterSpacing="wide"
                    fontSize="sm"
                    borderColor="whiteAlpha.200"
                    _focus={{
                      borderColor: 'brand.500',
                      boxShadow: '0 0 10px rgba(0, 212, 255, 0.3)',
                    }}
                  >
                    <option value="mmr">SORT BY MMR</option>
                    <option value="name">SORT BY NAME</option>
                    <option value="games">SORT BY MISSIONS</option>
                  </Select>
                </HStack>
              </HStack>
            </Box>
          </TacticalCard>

          {/* Player Grid */}
          {filteredPlayers.length === 0 ? (
            <TacticalCard variant="angled" glowColor="rgba(255, 179, 0, 0.4)">
              <Box p={12} textAlign="center">
                <Icon as={FiTarget} boxSize={16} color="gray.600" mb={4} />
                <Text
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                  letterSpacing="wide"
                  fontSize="lg"
                >
                  NO OPERATIVES MATCHING "{searchTerm}"
                </Text>
              </Box>
            </TacticalCard>
          ) : (
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
              {filteredPlayers.map((player, index) => {
                const playerRaces = getPlayerRaces(player);
                const primaryRace = playerRaces.length > 0 ? playerRaces[0].name : 'Random';
                const mmrLevel = player.mmr >= 1600 ? 'high' : player.mmr >= 1400 ? 'medium' : 'low';

                return (
                  <TacticalCard
                    key={player.id}
                    variant={index % 3 === 0 ? 'command' : index % 3 === 1 ? 'angled' : 'default'}
                    glowColor="rgba(0, 212, 255, 0.4)"
                    onClick={() => navigate(`/players/${player.id}`)}
                  >
                    <VStack p={5} spacing={4} align="stretch">
                      {/* Header with Avatar */}
                      <HStack spacing={4}>
                        <Box position="relative">
                          <Avatar
                            name={player.name}
                            size="lg"
                            bg={`${getRaceColor(primaryRace)}.500`}
                            color="white"
                            border="3px solid"
                            borderColor="brand.400"
                            boxShadow="0 0 20px rgba(0, 212, 255, 0.4)"
                          />
                          {/* Corner brackets */}
                          <Box
                            position="absolute"
                            top={-1}
                            left={-1}
                            width="12px"
                            height="12px"
                            borderTop="2px solid"
                            borderLeft="2px solid"
                            borderColor="brand.400"
                          />
                          <Box
                            position="absolute"
                            bottom={-1}
                            right={-1}
                            width="12px"
                            height="12px"
                            borderBottom="2px solid"
                            borderRight="2px solid"
                            borderColor="brand.400"
                          />
                        </Box>

                        <VStack flex={1} align="start" spacing={1}>
                          <Text
                            fontWeight="black"
                            fontSize="xl"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wide"
                            color="brand.300"
                          >
                            {player.name}
                          </Text>
                          <Badge
                            variant={`mmr-${mmrLevel}`}
                            fontSize="md"
                            px={2}
                            py={1}
                            fontFamily="heading"
                          >
                            MMR {formatMMR(player.mmr)}
                          </Badge>
                        </VStack>
                      </HStack>

                      {/* Race Info */}
                      <HStack spacing={2} flexWrap="wrap">
                        {playerRaces.map((race) => (
                          <Badge
                            key={race.name}
                            variant={`race-${race.name.toLowerCase()}`}
                            fontSize="xs"
                            px={2}
                            py={1}
                          >
                            {race.emoji} {race.name.toUpperCase()}
                          </Badge>
                        ))}
                      </HStack>

                      {/* Stats Grid */}
                      <SimpleGrid columns={2} spacing={3}>
                        <Box
                          bg="whiteAlpha.50"
                          p={3}
                          borderRadius="md"
                          border="1px solid"
                          borderColor="whiteAlpha.100"
                        >
                          <Text
                            fontSize="xs"
                            color="gray.500"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wider"
                          >
                            Missions
                          </Text>
                          <Text
                            fontSize="2xl"
                            fontWeight="black"
                            fontFamily="heading"
                            color="accent.400"
                          >
                            {player.total_games}
                          </Text>
                        </Box>

                        <Box
                          bg="whiteAlpha.50"
                          p={3}
                          borderRadius="md"
                          border="1px solid"
                          borderColor="whiteAlpha.100"
                        >
                          <Text
                            fontSize="xs"
                            color="gray.500"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wider"
                          >
                            Win Rate
                          </Text>
                          <Text
                            fontSize="2xl"
                            fontWeight="black"
                            fontFamily="heading"
                            color="shield.500"
                          >
                            {formatWinRate(player.win_rate)}
                          </Text>
                        </Box>
                      </SimpleGrid>

                      {/* Win/Loss Record */}
                      <Box>
                        <HStack justify="space-between" mb={2}>
                          <Text
                            fontSize="xs"
                            color="gray.500"
                            fontFamily="heading"
                            textTransform="uppercase"
                          >
                            Combat Record
                          </Text>
                          <Text fontSize="xs" color="gray.400" fontFamily="heading">
                            {player.wins}W - {player.losses}L
                          </Text>
                        </HStack>
                        <Progress
                          value={player.win_rate * 100}
                          size="sm"
                          colorScheme={player.win_rate >= 0.55 ? 'green' : player.win_rate >= 0.45 ? 'blue' : 'orange'}
                          borderRadius="full"
                          bg="whiteAlpha.100"
                        />
                      </Box>

                      {/* Tactical Footer */}
                      <HStack justify="center" pt={2}>
                        <Icon as={FiTarget} color="brand.400" boxSize={4} />
                        <Text
                          fontSize="xs"
                          color="brand.400"
                          fontFamily="heading"
                          textTransform="uppercase"
                          letterSpacing="wider"
                        >
                          VIEW PROFILE →
                        </Text>
                      </HStack>
                    </VStack>
                  </TacticalCard>
                );
              })}
            </SimpleGrid>
          )}
        </VStack>
      </Container>
    </Box>
  );
};

export default Players;
