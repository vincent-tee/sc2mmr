/**
 * Players List Page
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
  Card,
  CardBody,
  Badge,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiSearch } from 'react-icons/fi';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi } from '../api/endpoints';
import PlayerCard from '../components/PlayerCard';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import { formatMMR, formatWinRate } from '../utils/formatting';

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
          <Heading>Players</Heading>
          <LoadingState variant="players" count={8} />
        </VStack>
      </Container>
    );
  }

  if (players.length === 0) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading>Players</Heading>
          <EmptyState
            variant="players"
            onAction={() => navigate('/upload')}
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
            Players
          </Heading>
          <Text color="gray.500">
            {players.length} players tracked
          </Text>
        </Box>

        {/* Filters */}
        <HStack spacing={4}>
          <InputGroup flex={1}>
            <InputLeftElement>
              <FiSearch />
            </InputLeftElement>
            <Input
              placeholder="Search players..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </InputGroup>

          <Select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            maxW="200px"
          >
            <option value="mmr">Sort by MMR</option>
            <option value="name">Sort by Name</option>
            <option value="games">Sort by Games</option>
          </Select>
        </HStack>

        {/* Player List */}
        {filteredPlayers.length === 0 ? (
          <Text color="gray.500" textAlign="center" py={8}>
            No players found matching "{searchTerm}"
          </Text>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
            {filteredPlayers.map((player) => (
              <Card
                key={player.id}
                bg={cardBg}
                cursor="pointer"
                onClick={() => navigate(`/players/${player.id}`)}
                transition="all 0.2s"
                _hover={{
                  transform: 'translateY(-2px)',
                  boxShadow: 'xl',
                }}
              >
                <CardBody>
                  <HStack spacing={4} align="start">
                    <PlayerCard player={player} size="md" />
                    <VStack flex={1} align="start" spacing={2}>
                      <HStack spacing={2}>
                        <Badge colorScheme="blue">
                          {player.total_games} games
                        </Badge>
                        <Badge colorScheme="green">
                          {formatWinRate(player.win_rate)} WR
                        </Badge>
                      </HStack>
                      <Text fontSize="sm" color="gray.500">
                        {player.wins}W - {player.losses}L
                      </Text>
                    </VStack>
                  </HStack>
                </CardBody>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </VStack>
    </Container>
  );
};

export default Players;
