/**
 * Players List Page - Player Roster
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
  VisuallyHidden,
  FormControl,
  FormLabel,
} from '@chakra-ui/react';
import { FiSearch, FiFilter, FiTarget } from 'react-icons/fi';
import { useState, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi } from '../api/endpoints';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import { formatWinRate, getPlayerRaces, getRaceColor, getPlayerAvatarUrl } from '../utils/formatting';
import RankBadge from '../components/RankBadge';
import type { Player } from '../types/api';

type SortOption = 'mmr' | 'name' | 'games';

const Players: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortBy, setSortBy] = useState<SortOption>('mmr');

  // Fetch players
  const { data: playersData, isLoading } = useQuery<Player[]>({
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
          case 'mmr': {
            const mmrA = a.recency_weighted_mmr ?? a.mmr;
            const mmrB = b.recency_weighted_mmr ?? b.mmr;
            return mmrB - mmrA;
          }
          case 'name':
            return a.name.localeCompare(b.name);
          case 'games':
            return b.total_games - a.total_games;
          default:
            return 0;
        }
      });

  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setSearchTerm(e.target.value);
  };

  const handleSortChange = (e: ChangeEvent<HTMLSelectElement>): void => {
    setSortBy(e.target.value as SortOption);
  };

  if (isLoading) {
    return (
      <Box bg="space.900">
        <Container maxW="container.xl" py={8}>
          <VStack spacing={8} align="stretch">
            <Heading
              size="2xl"
              fontFamily="heading"
              letterSpacing="wider"
              color="brand.400"
              textAlign="center"
            >
              Player Roster
            </Heading>
            <LoadingState variant="players" count={8} />
          </VStack>
        </Container>
      </Box>
    );
  }

  if (players.length === 0) {
    return (
      <Box bg="space.900">
        <Container maxW="container.xl" py={8}>
          <VStack spacing={8} align="stretch">
            <Heading
              size="2xl"
              fontFamily="heading"
              letterSpacing="wider"
              color="brand.400"
              textAlign="center"
            >
              Player Roster
            </Heading>
            <EmptyState
              variant="players"
              onAction={() => navigate('/upload')}
            />
          </VStack>
        </Container>
      </Box>
    );
  }

  return (
    <Box position="relative" bg="space.900">
      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <Box textAlign="center" py={6}>
            <Heading
              size="2xl"
              fontFamily="heading"
              fontWeight="black"
              letterSpacing="wider"
              mb={2}
              color="brand.400"
            >
              Player Roster
            </Heading>
            <Text
              fontSize="md"
              color="gray.400"
              fontFamily="heading"
              letterSpacing="wide"
            >
              {players.length} Active Players
            </Text>
          </Box>

          {/* Filters */}
          <Box
            bg="space.800"
            border="3px solid"
            borderColor="space.700"
            borderRadius="xl"
            boxShadow="3px 3px 0 space.900"
            p={4}
          >
            <HStack spacing={4}>
              <FormControl flex={1}>
                <VisuallyHidden>
                  <FormLabel htmlFor="player-search">Search players</FormLabel>
                </VisuallyHidden>
                <InputGroup>
                  <InputLeftElement pointerEvents="none">
                    <Icon as={FiSearch} color="brand.400" />
                  </InputLeftElement>
                  <Input
                    id="player-search"
                    placeholder="Search players..."
                    value={searchTerm}
                    onChange={handleSearchChange}
                    fontFamily="heading"
                    letterSpacing="wide"
                    borderColor="space.700"
                    bg="space.800"
                    _placeholder={{ color: 'gray.600' }}
                    _focus={{
                      borderColor: 'brand.500',
                      boxShadow: '0 0 0 2px rgba(255, 107, 53, 0.3)',
                    }}
                  />
                </InputGroup>
              </FormControl>

              <FormControl as={HStack} maxW="280px">
                <VisuallyHidden>
                  <FormLabel htmlFor="player-sort">Sort players by</FormLabel>
                </VisuallyHidden>
                <Icon as={FiFilter} color="brand.400" />
                <Select
                  id="player-sort"
                  value={sortBy}
                  onChange={handleSortChange}
                  maxW="250px"
                  fontFamily="heading"
                  letterSpacing="wide"
                  fontSize="sm"
                  borderColor="space.700"
                  bg="space.800"
                  _focus={{
                    borderColor: 'brand.500',
                  }}
                >
                  <option value="mmr">Sort by MMR</option>
                  <option value="name">Sort by Name</option>
                  <option value="games">Sort by Matches</option>
                </Select>
              </FormControl>
            </HStack>
          </Box>

          {/* Player Grid */}
          {filteredPlayers.length === 0 ? (
            <Box
              bg="space.800"
              border="3px solid"
              borderColor="space.700"
              borderRadius="xl"
              boxShadow="3px 3px 0 space.900"
              p={12}
              textAlign="center"
            >
              <Icon as={FiTarget} boxSize={16} color="gray.600" mb={4} />
              <Text
                color="gray.500"
                fontFamily="heading"
                letterSpacing="wide"
                fontSize="lg"
              >
                No players matching "{searchTerm}"
              </Text>
            </Box>
          ) : (
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
              {filteredPlayers.map((player, index) => {
                const playerRaces = getPlayerRaces(player);
                const primaryRace = playerRaces.length > 0 ? playerRaces[0].name : 'Random';

                return (
                  <Box
                    key={player.id}
                    bg="space.800"
                    border="3px solid"
                    borderColor="space.700"
                    borderRadius="xl"
                    boxShadow="3px 3px 0 space.900"
                    p={5}
                    cursor="pointer"
                    transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
                    _hover={{
                      transform: 'translateY(-4px)',
                      borderColor: 'brand.500',
                    }}
                    onClick={() => navigate(`/players/${player.id}`)}
                  >
                    <VStack spacing={4} align="stretch">
                      {/* Header with Avatar */}
                      <HStack spacing={4}>
                        <Box position="relative">
                          <Avatar
                            src={getPlayerAvatarUrl(player.name, primaryRace, player.is_ai)}
                            name={player.name}
                            size="lg"
                            bg={`${getRaceColor(primaryRace)}.500`}
                            color="white"
                            border="3px solid"
                            borderColor="brand.500"
                          />
                        </Box>

                        <VStack flex={1} align="start" spacing={1}>
                          <HStack>
                            <Text
                              fontWeight="black"
                              fontSize="xl"
                              fontFamily="heading"
                              letterSpacing="wide"
                              color="brand.300"
                            >
                              {player.name}
                            </Text>
                            {player.is_ai && (
                              <Badge colorScheme="purple" variant="solid" fontSize="xs">
                                AI
                              </Badge>
                            )}
                          </HStack>
                           <RankBadge
                             mmr={player.recency_weighted_mmr || player.mmr}
                             size="md"
                             showMMR={true}
                             showIcon={true}
                           />
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
                          bg="space.700"
                          p={3}
                          borderRadius="lg"
                          border="2px solid"
                          borderColor="space.600"
                        >
                          <Text
                            fontSize="xs"
                            color="gray.500"
                            fontFamily="heading"
                            letterSpacing="wider"
                          >
                            Matches
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
                          bg="space.700"
                          p={3}
                          borderRadius="lg"
                          border="2px solid"
                          borderColor="space.600"
                        >
                          <Text
                            fontSize="xs"
                            color="gray.500"
                            fontFamily="heading"
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
                          >
                            Win/Loss Record
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
                          bg="space.700"
                        />
                      </Box>

                      {/* Footer */}
                      <HStack justify="center" pt={2}>
                        <Icon as={FiTarget} color="brand.400" boxSize={4} />
                        <Text
                          fontSize="xs"
                          color="brand.400"
                          fontFamily="heading"
                          letterSpacing="wider"
                        >
                          View Profile →
                        </Text>
                      </HStack>
                    </VStack>
                  </Box>
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
