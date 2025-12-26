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
  VisuallyHidden,
  FormControl,
  FormLabel,
} from '@chakra-ui/react';
import { FiSearch, FiFilter, FiTarget } from 'react-icons/fi';
import { useState, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi } from '../api/endpoints';
import TacticalCard from '../components/TacticalCard';
import TacticalBackground from '../components/common/TacticalBackground';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import { formatWinRate, getPlayerRaces, getRaceColor } from '../utils/formatting';
import RankBadge from '../components/RankBadge';
import type { Player } from '../types/api';

// Extended Player type with optional fields that may come from the API
interface ExtendedPlayer extends Player {
  hybrid_mmr?: number;
  avg_pim?: number;
}

type SortOption = 'mmr' | 'name' | 'games';

const Players: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortBy, setSortBy] = useState<SortOption>('mmr');

  // Fetch players
  const { data: playersData, isLoading } = useQuery<ExtendedPlayer[]>({
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

  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setSearchTerm(e.target.value);
  };

  const handleSortChange = (e: ChangeEvent<HTMLSelectElement>): void => {
    setSortBy(e.target.value as SortOption);
  };

  if (isLoading) {
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
            Player Database
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
            letterSpacing="wider"
            color="brand.400"
            textAlign="center"
          >
            Player Database
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
      <TacticalBackground />

      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Tactical Header */}
          <Box textAlign="center" py={6}>
            <Heading
              size="2xl"
              fontFamily="heading"
              fontWeight="black"
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
                Player Database
              </Box>
            </Heading>
            <Text
              fontSize="md"
              color="gray.400"
              fontFamily="heading"
              letterSpacing="wide"
            >
              [ {players.length} Active Players ]
            </Text>
          </Box>

          {/* Tactical Filters */}
          <TacticalCard variant="command" glowColor="rgba(0, 212, 255, 0.4)">
            <Box p={4}>
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
                      borderColor="whiteAlpha.200"
                      _placeholder={{ color: 'gray.600' }}
                      _focus={{
                        borderColor: 'brand.500',
                        boxShadow: '0 0 10px rgba(0, 212, 255, 0.3)',
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
                    borderColor="whiteAlpha.200"
                    _focus={{
                      borderColor: 'brand.500',
                      boxShadow: '0 0 10px rgba(0, 212, 255, 0.3)',
                    }}
                  >
                    <option value="mmr">Sort by MMR</option>
                    <option value="name">Sort by Name</option>
                    <option value="games">Sort by Matches</option>
                  </Select>
                </FormControl>
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
                  letterSpacing="wide"
                  fontSize="lg"
                >
                  No players matching "{searchTerm}"
                </Text>
              </Box>
            </TacticalCard>
          ) : (
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
              {filteredPlayers.map((player, index) => {
                const playerRaces = getPlayerRaces(player);
                const primaryRace = playerRaces.length > 0 ? playerRaces[0].name : 'Random';

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
                            letterSpacing="wide"
                            color="brand.300"
                          >
                            {player.name}
                          </Text>
                          <RankBadge
                            mmr={player.hybrid_mmr || player.mmr}
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
                          letterSpacing="wider"
                        >
                          View Profile →
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
