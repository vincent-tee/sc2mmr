/**
 * Players List Page - Squad Roster
 * Clubhouse edition: editorial header with inline search/sort,
 * roster cards with faded rank numerals and race-tinted accents.
 */
import {
  Box,
  Container,
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
  Flex,
  Heading,
  Switch,
} from '@chakra-ui/react';
import { FiSearch, FiTarget, FiArrowRight } from 'react-icons/fi';
import { useState, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi } from '../api/endpoints';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import { formatWinRate, getPlayerRaces, getRaceColor, getPlayerAvatarUrl } from '../utils/formatting';
import RankBadge from '../components/RankBadge';
import type { Player } from '../types/api';

type SortOption = 'mmr' | 'name' | 'games';

const Players: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortBy, setSortBy] = useState<SortOption>('mmr');
  const [showLegacy, setShowLegacy] = useState(false);

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
    .filter(
      (player) =>
        player.total_games > 0 &&
        player.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
        (showLegacy || player.is_active)
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

  // Count only the players actually rendered by the grid's active/legacy
  // filter, so the header stat never disagrees with the card count. Search
  // is intentionally excluded so the header reflects roster size, not results.
  const rosterCount = players.filter(
    (p) => p.total_games > 0 && (showLegacy || p.is_active)
  ).length;

  const header = (
    <PageHeader
      kicker="The Roster"
      title="Squad [Roster]"
      description="Everyone who's ever laddered with the squad — records, races, and receipts."
      stats={[{ label: showLegacy ? 'Players' : 'Active players', value: rosterCount }]}
      actions={
        <HStack spacing={3}>
          <FormControl w={{ base: '100%', md: '240px' }}>
            <VisuallyHidden>
              <FormLabel htmlFor="player-search">Search players</FormLabel>
            </VisuallyHidden>
            <InputGroup size="sm">
              <InputLeftElement pointerEvents="none">
                <Icon as={FiSearch} color="gray.500" />
              </InputLeftElement>
              <Input
                id="player-search"
                placeholder="Search players..."
                value={searchTerm}
                onChange={handleSearchChange}
                borderRadius="full"
                bg="whiteAlpha.100"
                border="1px solid"
                borderColor="whiteAlpha.200"
                _placeholder={{ color: 'gray.500' }}
                _focus={{ borderColor: 'brand.500', boxShadow: '0 0 0 2px rgba(255, 107, 53, 0.3)' }}
              />
            </InputGroup>
          </FormControl>
          <FormControl w="150px">
            <VisuallyHidden>
              <FormLabel htmlFor="player-sort">Sort players by</FormLabel>
            </VisuallyHidden>
            <Select
              id="player-sort"
              size="sm"
              value={sortBy}
              onChange={handleSortChange}
              borderRadius="full"
              bg="whiteAlpha.100"
              border="1px solid"
              borderColor="whiteAlpha.200"
              _focus={{ borderColor: 'brand.500' }}
            >
              <option value="mmr">By MMR</option>
              <option value="name">By Name</option>
              <option value="games">By Matches</option>
            </Select>
          </FormControl>
          <FormControl w="auto" display="flex" alignItems="center" gap={2}>
            <FormLabel htmlFor="show-legacy" mb={0} fontSize="sm" color="gray.500" whiteSpace="nowrap" cursor="pointer">
              Show legacy
            </FormLabel>
            <Switch
              id="show-legacy"
              size="sm"
              colorScheme="orange"
              isChecked={showLegacy}
              onChange={(e) => setShowLegacy(e.target.checked)}
            />
          </FormControl>
        </HStack>
      }
    />
  );

  if (isLoading) {
    return (
      <Box minH="100vh" pb={16}>
        {header}
        <Container maxW="container.xl" pt={8}>
          <LoadingState variant="players" count={8} />
        </Container>
      </Box>
    );
  }

  if (players.length === 0) {
    return (
      <Box minH="100vh" pb={16}>
        {header}
        <Container maxW="container.xl" pt={8}>
          <EmptyState variant="players" onAction={() => navigate('/upload')} />
        </Container>
      </Box>
    );
  }

  return (
    <Box minH="100vh" pb={16}>
      {header}
      <Container maxW="container.xl" pt={8}>
        {filteredPlayers.length === 0 ? (
          <Box
            bg="space.800"
            border="1px dashed"
            borderColor="whiteAlpha.300"
            borderRadius="xl"
            p={12}
            textAlign="center"
          >
            <Icon as={FiTarget} boxSize={12} color="gray.600" mb={4} />
            <Text color="gray.500" fontFamily="heading" fontSize="lg">
              No players matching &quot;{searchTerm}&quot;
            </Text>
          </Box>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={5}>
            {filteredPlayers.map((player, index) => {
              const playerRaces = getPlayerRaces(player);
              const primaryRace = playerRaces.length > 0 ? playerRaces[0].name : 'Random';
              const raceColor = getRaceColor(primaryRace);
              const rosterRank = sortBy === 'mmr' && searchTerm === '' ? index + 1 : null;

              return (
                <Box
                  key={player.id}
                  position="relative"
                  overflow="hidden"
                  bg="space.800"
                  border="1px solid"
                  borderColor="whiteAlpha.100"
                  borderTop="3px solid"
                  borderTopColor={`${raceColor}.500`}
                  borderRadius="xl"
                  p={5}
                  cursor="pointer"
                  transition="all 0.2s ease"
                  _hover={{ transform: 'translateY(-4px)', borderColor: 'brand.500', borderTopColor: 'brand.500' }}
                  onClick={() => navigate(`/players/${player.id}`)}
                >
                  {rosterRank && (
                    <Text
                      aria-hidden
                      position="absolute"
                      top="-14px"
                      right="4px"
                      fontFamily="heading"
                      fontWeight="800"
                      fontSize="80px"
                      lineHeight="1"
                      color="whiteAlpha.100"
                      pointerEvents="none"
                    >
                      {rosterRank}
                    </Text>
                  )}
                  <VStack spacing={4} align="stretch" position="relative">
                    {/* Header with Avatar */}
                    <HStack spacing={4}>
                      <Avatar
                        src={getPlayerAvatarUrl(player.name, primaryRace, player.is_ai)}
                        name={player.name}
                        size="lg"
                        bg={`${raceColor}.500`}
                        color="white"
                        border="2px solid"
                        borderColor={`${raceColor}.500`}
                      />
                      <VStack flex={1} align="start" spacing={1}>
                        <HStack>
                          <Heading fontSize="xl" color="gray.50">
                            {player.name}
                          </Heading>
                          {player.is_ai && (
                            <Badge colorScheme="purple" variant="solid" fontSize="xs">
                              AI
                            </Badge>
                          )}
                          {player.is_new && (
                            <Badge colorScheme="teal" fontSize="9px">
                              NEW
                            </Badge>
                          )}
                          {!player.is_active && (
                            <Badge colorScheme="gray" fontSize="9px">
                              LEGACY
                            </Badge>
                          )}
                        </HStack>
                        <RankBadge mmr={player.mmr} size="sm" showMMR showIcon={false} />
                      </VStack>
                    </HStack>

                    {/* Races */}
                    <HStack spacing={2} flexWrap="wrap">
                      {playerRaces.map((race) => (
                        <Badge key={race.name} variant={`race-${race.name.toLowerCase()}`} fontSize="10px" px={2} py={0.5}>
                          {race.name.toUpperCase()}
                        </Badge>
                      ))}
                    </HStack>

                    {/* Inline stats */}
                    <Flex justify="space-between" borderTop="1px solid" borderColor="whiteAlpha.100" pt={3}>
                      {[
                        { label: 'Matches', value: player.total_games, color: 'gray.100' },
                        { label: 'Win rate', value: formatWinRate(player.win_rate), color: 'accent.400' },
                        { label: 'Record', value: `${player.wins}W ${player.losses}L`, color: 'gray.100' },
                      ].map((stat) => (
                        <Box key={stat.label}>
                          <Text fontFamily="mono" fontWeight="700" fontSize="md" color={stat.color}>
                            {stat.value}
                          </Text>
                          <Text fontSize="10px" color="gray.500" textTransform="uppercase" letterSpacing="0.1em">
                            {stat.label}
                          </Text>
                        </Box>
                      ))}
                    </Flex>

                    <Box>
                      <Progress
                        value={player.win_rate * 100}
                        size="xs"
                        colorScheme={player.win_rate >= 0.55 ? 'green' : player.win_rate >= 0.45 ? 'teal' : 'orange'}
                        borderRadius="full"
                        bg="space.700"
                      />
                    </Box>

                    <HStack justify="end" spacing={1} color="brand.400">
                      <Text fontSize="xs" fontFamily="heading" fontWeight="700" letterSpacing="0.05em">
                        View profile
                      </Text>
                      <Icon as={FiArrowRight} boxSize={3} />
                    </HStack>
                  </VStack>
                </Box>
              );
            })}
          </SimpleGrid>
        )}
      </Container>
    </Box>
  );
};

export default Players;
