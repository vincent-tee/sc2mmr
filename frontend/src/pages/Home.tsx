/**
 * Home Page - Clubhouse Edition
 * Asymmetric editorial masthead: big headline + reigning champ card,
 * then a battles feed and a top-five ladder strip. No centered hero,
 * no three-equal-columns grid.
 */
import {
  Box,
  Container,
  Heading,
  Text,
  Button,
  VStack,
  HStack,
  Flex,
  Grid,
  GridItem,
  Avatar,
  AvatarGroup,
  Icon,
  Badge,
  Progress,
} from '@chakra-ui/react';
import { FiUpload, FiZap, FiTarget, FiArrowRight, FiAward } from 'react-icons/fi';
import { LuCrown } from 'react-icons/lu';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi, replaysApi } from '../api/endpoints';
import { leaderboardApi } from '../api/leaderboard';
import RankBadge from '../components/RankBadge';
import { formatDateTimeShort, getPlayerAvatarUrl, getPlayerRaces, getRaceColor } from '../utils/formatting';
import type { Player, MatchWithPlayers } from '../types/api';

/** Compact match row for the battles feed */
const MatchRow: React.FC<{ match: MatchWithPlayers; onClick: () => void }> = ({ match, onClick }) => {
  const allPlayers = match.players || [];
  const winners = allPlayers.filter((p) => p.won);
  const losers = allPlayers.filter((p) => !p.won);
  const winnerNames = winners.map((p) => p.player_name).join(', ');
  const teamColor = match.winner_team === 2 ? 'accent' : 'brand';
  // Winners first so the emphasized avatars lead the stack
  const orderedPlayers = [...winners, ...losers];

  return (
    <Flex
      as="button"
      onClick={onClick}
      w="100%"
      textAlign="left"
      align="center"
      gap={4}
      px={4}
      py={3}
      bg="space.800"
      borderRadius="xl"
      border="1px solid"
      borderColor="whiteAlpha.100"
      transition="all 0.18s ease"
      _hover={{ borderColor: 'brand.500', bg: 'space.700', transform: 'translateX(4px)' }}
    >
      <Flex
        flexShrink={0}
        w="34px"
        h="34px"
        align="center"
        justify="center"
        borderRadius="md"
        bg={match.winner_team === 2 ? 'rgba(78, 205, 196, 0.12)' : 'rgba(255, 107, 53, 0.15)'}
        border="1px solid"
        borderColor={`${teamColor}.500`}
      >
        <Icon as={FiAward} color={`${teamColor}.400`} boxSize="16px" />
      </Flex>
      <Box flex={1} minW={0}>
        <Text fontWeight="800" fontFamily="heading" color="gray.100" noOfLines={1}>
          {match.map_name}
        </Text>
        <Text fontSize="xs" color="gray.500" noOfLines={1}>
          {winnerNames ? `Won by ${winnerNames}` : `Team ${match.winner_team} won`} · {formatDateTimeShort(match.played_at)}
        </Text>
      </Box>
      <AvatarGroup size="xs" max={5} flexShrink={0}>
        {orderedPlayers.slice(0, 5).map((player, idx) => (
          <Avatar
            key={player.player_id || idx}
            src={getPlayerAvatarUrl(player.player_name, player.race)}
            name={player.player_name}
            size="xs"
            bg={`${getRaceColor(player.race)}.500`}
            opacity={player.won ? 1 : 0.4}
            borderColor={player.won ? `${teamColor}.400` : 'space.800'}
          />
        ))}
      </AvatarGroup>
    </Flex>
  );
};

/** Ladder strip row with oversized rank numeral */
const LadderRow: React.FC<{ player: Player; rank: number; onClick: () => void }> = ({
  player,
  rank,
  onClick,
}) => {
  const races = getPlayerRaces(player);
  const primaryRace = races.length > 0 ? races[0].name : 'Random';
  const isFirst = rank === 1;

  return (
    <Flex
      as="button"
      onClick={onClick}
      w="100%"
      textAlign="left"
      align="center"
      gap={3}
      px={4}
      py={2.5}
      bg={isFirst ? 'rgba(255, 107, 53, 0.08)' : 'transparent'}
      borderRadius="lg"
      border="1px solid"
      borderColor={isFirst ? 'rgba(255, 107, 53, 0.35)' : 'transparent'}
      transition="all 0.18s ease"
      _hover={{ bg: 'whiteAlpha.100' }}
    >
      <Text
        fontFamily="heading"
        fontWeight="800"
        fontSize="2xl"
        w="34px"
        textAlign="center"
        color={isFirst ? 'brand.500' : 'whiteAlpha.300'}
        flexShrink={0}
      >
        {rank}
      </Text>
      <Avatar
        size="sm"
        src={getPlayerAvatarUrl(player.name, primaryRace, player.is_ai)}
        name={player.name}
        bg={`${getRaceColor(primaryRace)}.500`}
      />
      <Text fontWeight="700" fontFamily="heading" color="gray.100" flex={1} noOfLines={1}>
        {player.name}
      </Text>
      <Text fontFamily="mono" fontWeight="700" color={isFirst ? 'brand.400' : 'gray.400'}>
        {Math.round(player.mmr).toLocaleString()}
      </Text>
    </Flex>
  );
};

const Home: React.FC = () => {
  const navigate = useNavigate();

  const { data: playersData, isLoading: loadingPlayers } = useQuery<Player[]>({
    queryKey: ['players'],
    queryFn: async () => {
      const response = await playersApi.getAll();
      return response.data;
    },
  });

  const { data: matchesData, isLoading: loadingMatches } = useQuery<{
    matches: MatchWithPlayers[];
    total_count: number;
  }>({
    queryKey: ['matches-with-players-home'],
    queryFn: async () => {
      const response = await replaysApi.getMatchesWithPlayers(10);
      return response.data;
    },
  });

  const { data: metaData } = useQuery({
    queryKey: ['squad-meta'],
    queryFn: async () => (await leaderboardApi.getMetaReport()).data,
  });
  const raceWR: Record<string, number> = metaData?.squad_win_rate_by_race || {};
  const sortedRaces = Object.entries(raceWR).sort(([, a], [, b]) => b - a);

  const players = playersData || [];
  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_count || 0;

  const rankedPlayers = [...players]
    .filter((p) => p.total_games >= 15 && !p.is_ai && p.is_core_player)
    .sort((a, b) => b.mmr - a.mmr);
  const champion = rankedPlayers[0];
  const championRaces = champion ? getPlayerRaces(champion) : [];
  const championRace = championRaces.length > 0 ? championRaces[0].name : 'Random';

  const totalPlayers = players.filter((p) => p.total_games > 0).length;
  const isLoading = loadingPlayers || loadingMatches;

  return (
    <Box minH="100vh" pb={16}>
      <Container maxW="container.xl">
        {/* ===== Masthead: headline left, champion card right ===== */}
        <Grid templateColumns="repeat(12, 1fr)" gap={{ base: 8, lg: 10 }} pt={{ base: 8, md: 14 }} pb={{ base: 8, md: 12 }}>
          <GridItem colSpan={{ base: 12, lg: 7 }}>
            <HStack spacing={2} mb={3}>
              <Box w="18px" h="3px" bg="brand.500" borderRadius="full" />
              <Text
                fontFamily="mono"
                fontSize="xs"
                fontWeight="600"
                letterSpacing="0.18em"
                textTransform="uppercase"
                color="accent.400"
              >
                The Clubhouse Ladder
              </Text>
            </HStack>
            <Heading
              as="h1"
              fontSize={{ base: '4xl', md: '6xl' }}
              lineHeight="1.02"
              color="gray.50"
              mb={4}
            >
              Who&apos;s{' '}
              <Text as="span" color="brand.500">
                actually
              </Text>{' '}
              the best?
            </Heading>
            <Text fontSize={{ base: 'md', md: 'lg' }} color="gray.400" maxW="480px" mb={7}>
              Every replay counted, every excuse recorded. Track your friend group&apos;s
              StarCraft II matches and settle the debate with math.
            </Text>
            <HStack spacing={3} mb={8} flexWrap="wrap">
              <Button
                size="lg"
                variant="primary"
                leftIcon={<FiZap />}
                onClick={() => navigate('/balance')}
                fontFamily="heading"
              >
                Generate Teams
              </Button>
              <Button
                size="lg"
                variant="outline"
                leftIcon={<FiUpload />}
                onClick={() => navigate('/upload')}
                fontFamily="heading"
                fontWeight="700"
                color="gray.200"
                borderColor="whiteAlpha.300"
                borderRadius="lg"
                _hover={{ bg: 'whiteAlpha.100', borderColor: 'gray.400' }}
              >
                Upload Replays
              </Button>
            </HStack>
            <HStack spacing={7} flexWrap="wrap">
              {[
                { value: isLoading ? '—' : totalPlayers, label: 'Players' },
                { value: isLoading ? '—' : totalMatches.toLocaleString(), label: 'Matches' },
                {
                  value:
                    isLoading || players.length === 0
                      ? '—'
                      : Math.round(Math.max(...players.map((p) => p.mmr))).toLocaleString(),
                  label: 'Top MMR',
                },
              ].map((stat) => (
                <Box key={stat.label}>
                  <Text fontFamily="mono" fontWeight="700" fontSize="2xl" color="gray.100" lineHeight="1.1">
                    {stat.value}
                  </Text>
                  <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="0.1em">
                    {stat.label}
                  </Text>
                </Box>
              ))}
            </HStack>
          </GridItem>

          {/* Champion card - tilted, spotlighted */}
          <GridItem colSpan={{ base: 12, lg: 5 }} display="flex" alignItems="center">
            {champion && (
              <Box
                w="100%"
                maxW="360px"
                mx={{ base: 'auto', lg: 'unset' }}
                ml={{ lg: 'auto' }}
                position="relative"
                bg="space.800"
                borderRadius="2xl"
                border="1px solid"
                borderColor="rgba(255, 107, 53, 0.4)"
                boxShadow="0 0 60px rgba(255, 107, 53, 0.12), 8px 8px 0 rgba(0,0,0,0.35)"
                transform="rotate(1.5deg)"
                transition="transform 0.25s ease"
                _hover={{ transform: 'rotate(0deg) translateY(-4px)' }}
                cursor="pointer"
                onClick={() => navigate(`/players/${champion.id}`)}
                p={6}
              >
                <HStack spacing={2} mb={4}>
                  <Icon as={LuCrown} color="shield.400" boxSize="18px" />
                  <Text
                    fontFamily="mono"
                    fontSize="xs"
                    fontWeight="600"
                    letterSpacing="0.18em"
                    textTransform="uppercase"
                    color="shield.400"
                  >
                    Reigning Champ
                  </Text>
                </HStack>
                <HStack spacing={4} mb={5}>
                  <Avatar
                    size="xl"
                    src={getPlayerAvatarUrl(champion.name, championRace, champion.is_ai)}
                    name={champion.name}
                    bg={`${getRaceColor(championRace)}.500`}
                    border="3px solid"
                    borderColor="shield.400"
                  />
                  <Box>
                    <Heading fontSize="2xl" color="gray.50" mb={1}>
                      {champion.name}
                    </Heading>
                    <RankBadge mmr={champion.mmr} size="sm" showMMR />
                  </Box>
                </HStack>
                <Flex justify="space-between" borderTop="1px solid" borderColor="whiteAlpha.100" pt={4}>
                  {[
                    { value: champion.total_games, label: 'Games' },
                    { value: `${(champion.win_rate * 100).toFixed(1)}%`, label: 'Win rate' },
                    { value: `${champion.wins}W ${champion.losses}L`, label: 'Record' },
                  ].map((stat) => (
                    <Box key={stat.label}>
                      <Text fontFamily="mono" fontWeight="700" color="gray.100">
                        {stat.value}
                      </Text>
                      <Text fontSize="10px" color="gray.500" textTransform="uppercase" letterSpacing="0.1em">
                        {stat.label}
                      </Text>
                    </Box>
                  ))}
                </Flex>
              </Box>
            )}
          </GridItem>
        </Grid>

        {/* ===== Feed + ladder strip ===== */}
        <Grid templateColumns="repeat(12, 1fr)" gap={{ base: 8, lg: 6 }}>
          <GridItem colSpan={{ base: 12, lg: 7 }}>
            <Flex justify="space-between" align="center" mb={4}>
              <Heading fontSize="xl" color="gray.100">
                Latest battles
              </Heading>
              <Button
                size="sm"
                variant="ghost"
                rightIcon={<FiArrowRight />}
                color="brand.400"
                fontFamily="heading"
                onClick={() => navigate('/history')}
              >
                View all
              </Button>
            </Flex>
            {matches.length > 0 ? (
              <VStack spacing={2} align="stretch">
                {matches.slice(0, 7).map((match) => (
                  <MatchRow key={match.id} match={match} onClick={() => navigate(`/history/${match.id}`)} />
                ))}
              </VStack>
            ) : (
              <Box
                bg="space.800"
                borderRadius="xl"
                border="1px dashed"
                borderColor="whiteAlpha.300"
                p={10}
                textAlign="center"
              >
                <Text color="gray.500">No matches yet — upload some replays to get started.</Text>
              </Box>
            )}
          </GridItem>

          <GridItem colSpan={{ base: 12, lg: 5 }}>
            <Flex justify="space-between" align="center" mb={4}>
              <Heading fontSize="xl" color="gray.100">
                Top five
              </Heading>
              <Button
                size="sm"
                variant="ghost"
                rightIcon={<FiArrowRight />}
                color="brand.400"
                fontFamily="heading"
                onClick={() => navigate('/leaderboard')}
              >
                Full ladder
              </Button>
            </Flex>
            <Box bg="space.800" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100" p={2}>
              {rankedPlayers.slice(0, 5).map((player, idx) => (
                <LadderRow
                  key={player.id}
                  player={player}
                  rank={idx + 1}
                  onClick={() => navigate(`/players/${player.id}`)}
                />
              ))}
            </Box>

            {/* Win rate by race - folded in from the old standalone Squad Meta
                page, which was down to just this one real, non-redundant stat */}
            {sortedRaces.length > 0 && (
              <Box bg="space.800" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100" p={5} mt={6}>
                <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="0.1em" mb={4} fontWeight="700">
                  Win Rate by Race
                </Text>
                <VStack spacing={4} align="stretch">
                  {sortedRaces.map(([race, wr]) => (
                    <Box key={race}>
                      <HStack justify="space-between" mb={1.5}>
                        <Badge colorScheme={getRaceColor(race)} variant="solid" px={2.5} fontSize="10px">
                          {race.toUpperCase()}
                        </Badge>
                        <Text fontWeight="700" color="gray.200" fontFamily="mono" fontSize="sm">
                          {wr}%
                        </Text>
                      </HStack>
                      <Progress
                        value={wr}
                        colorScheme={getRaceColor(race)}
                        bg="blackAlpha.400"
                        borderRadius="full"
                        height="6px"
                        sx={{ '& > div': { bg: `${getRaceColor(race)}.500` } }}
                      />
                    </Box>
                  ))}
                </VStack>
              </Box>
            )}

            {/* Quick links */}
            <VStack spacing={2} align="stretch" mt={6}>
              {[
                { label: 'Predict a match', icon: FiTarget, path: '/predictor' },
                { label: 'Achievements', icon: FiAward, path: '/achievements' },
              ].map((link) => (
                <Flex
                  key={link.path}
                  as="button"
                  onClick={() => navigate(link.path)}
                  align="center"
                  gap={3}
                  px={4}
                  py={3}
                  borderRadius="lg"
                  border="1px solid"
                  borderColor="whiteAlpha.100"
                  color="gray.300"
                  transition="all 0.18s ease"
                  _hover={{ borderColor: 'accent.500', color: 'accent.400', transform: 'translateX(4px)' }}
                >
                  <Icon as={link.icon} boxSize="16px" />
                  <Text fontFamily="heading" fontWeight="700" fontSize="sm" flex={1} textAlign="left">
                    {link.label}
                  </Text>
                  <Icon as={FiArrowRight} boxSize="14px" />
                </Flex>
              ))}
            </VStack>
          </GridItem>
        </Grid>
      </Container>
    </Box>
  );
};

export default Home;
