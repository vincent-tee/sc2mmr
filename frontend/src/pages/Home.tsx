/**
 * Home Page - Friend Squad Edition
 * A cozy gaming clubhouse, not a sterile command center
 * Desktop-first design with personality
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
  Flex,
  Avatar,
  AvatarGroup,
  Badge,
  Divider,
} from '@chakra-ui/react';
import { FiUpload, FiUsers, FiZap, FiTrendingUp, FiCalendar, FiAward } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi, replaysApi } from '../api/endpoints';
import FriendlyStat from '../components/FriendlyStat';
import { formatDateOnly, getInitials, getPlayerAvatarUrl, getPlayerRaces, getRaceColor } from '../utils/formatting';
import type { Player, MatchWithPlayers } from '../types/api';

/**
 * Quick Action Card - Comic book style button
 */
interface QuickActionProps {
  emoji: string;
  title: string;
  subtitle: string;
  color: string;
  onClick: () => void;
  isPrimary?: boolean;
}

const QuickAction: React.FC<QuickActionProps> = ({ 
  emoji, title, subtitle, color, onClick, isPrimary 
}) => (
  <Box
    as="button"
    onClick={onClick}
    bg={isPrimary ? color : 'space.800'}
    borderRadius="xl"
    border="3px solid"
    borderColor="space.900"
    boxShadow="4px 4px 0 var(--chakra-colors-space-900)"
    p={5}
    textAlign="left"
    transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
    _hover={{
      transform: 'translateY(-4px) rotate(1deg)',
      boxShadow: '6px 6px 0 var(--chakra-colors-space-900)',
    }}
    _active={{
      transform: 'translateY(-2px)',
      boxShadow: '3px 3px 0 var(--chakra-colors-space-900)',
    }}
    width="100%"
  >
    <HStack spacing={4}>
      <Text fontSize="3xl" className="emoji-font">
        {emoji}
      </Text>
      <VStack align="start" spacing={0}>
        <Text
          fontWeight="bold"
          fontSize="lg"
          fontFamily="heading"
          color={isPrimary ? 'space.900' : 'gray.100'}
        >
          {title}
        </Text>
        <Text 
          fontSize="sm" 
          color={isPrimary ? 'space.700' : 'gray.500'}
        >
          {subtitle}
        </Text>
      </VStack>
    </HStack>
  </Box>
);

/**
 * Recent Match Card - Friendly style
 */
interface MatchCardProps {
  match: MatchWithPlayers;
  onClick: () => void;
}

const MatchCard: React.FC<MatchCardProps> = ({ match, onClick }) => (
  <Box
    as="button"
    onClick={onClick}
    bg="space.800"
    borderRadius="xl"
    border="3px solid"
    borderColor="space.900"
    boxShadow="3px 3px 0 var(--chakra-colors-space-900)"
    p={4}
    width="100%"
    textAlign="left"
    transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
    _hover={{
      transform: 'translateY(-2px)',
      boxShadow: '5px 5px 0 var(--chakra-colors-space-900)',
      borderColor: 'brand.500',
    }}
  >
    <Flex justify="space-between" align="center">
      <HStack spacing={3}>
        <Text fontSize="xl" className="emoji-font">
          🎮
        </Text>
        <VStack align="start" spacing={0}>
          <Text fontWeight="bold" fontFamily="heading" color="gray.100">
            {match.map_name}
          </Text>
          <Text fontSize="xs" color="gray.500">
            {match.game_mode} • {formatDateOnly(match.played_at)}
          </Text>
        </VStack>
      </HStack>
      <AvatarGroup size="sm" max={4}>
        {(match.players || []).slice(0, 4).map((player, idx) => (
          <Avatar
            key={player.player_id || idx}
            src={getPlayerAvatarUrl(player.player_name, player.race)}
            name={player.player_name}
            size="sm"
            bg={`${getRaceColor(player.race)}.500`}
            color="white"
            border="2px solid"
            borderColor="space.900"
          />
        ))}
      </AvatarGroup>
    </Flex>
  </Box>
);

/**
 * Player Spotlight - Shows top players
 */
interface PlayerSpotlightProps {
  players: Player[];
  onClick: (id: number) => void;
}

const PlayerSpotlight: React.FC<PlayerSpotlightProps> = ({ players, onClick }) => {
  const topPlayers = [...players]
    .filter(p => p.total_games >= 5) // Minimum 5 games to be featured on Home
    .sort((a, b) => (b.recency_weighted_mmr || b.mmr) - (a.recency_weighted_mmr || a.mmr))
    .slice(0, 5);

  return (
    <VStack spacing={2} align="stretch">
      {topPlayers.map((player, idx) => {
        const playerRaces = getPlayerRaces(player);
        const primaryRace = playerRaces.length > 0 ? playerRaces[0].name : 'Random';

        return (
          <HStack
            key={player.id}
            as="button"
            onClick={() => onClick(player.id)}
            bg="space.800"
            borderRadius="lg"
            border="2px solid"
            borderColor="space.900"
            p={3}
            justify="space-between"
            transition="all 0.2s"
            _hover={{
              bg: 'space.700',
              borderColor: 'brand.500',
            }}
          >
            <HStack spacing={3}>
              <Text
                fontSize="lg"
                fontWeight="bold"
                color="gray.500"
                width="24px"
                className="emoji-font"
              >
                {idx === 0 ? '👑' : `#${idx + 1}`}
              </Text>
              <Avatar
                size="sm"
                src={getPlayerAvatarUrl(player.name, primaryRace, player.is_ai)}
                name={player.name}
                bg={`${getRaceColor(primaryRace)}.500`}
                color="white"
                border="2px solid"
                borderColor="space.900"
              />
              <Text fontWeight="bold" fontFamily="heading" color="gray.100">
                {player.name}
              </Text>
            </HStack>
            <Badge
              bg="space.700"
              color="brand.400"
              fontSize="sm"
              fontFamily="mono"
              px={2}
              borderRadius="md"
            >
              {Math.round(player.recency_weighted_mmr || player.mmr)}
            </Badge>
          </HStack>
        );
      })}
    </VStack>
  );
};

const Home: React.FC = () => {
  const navigate = useNavigate();

  // Fetch stats
  const { data: playersData, isLoading: loadingPlayers } = useQuery<Player[]>({
    queryKey: ['players'],
    queryFn: async () => {
      const response = await playersApi.getAll();
      return response.data;
    },
  });

  const { data: matchesData, isLoading: loadingMatches } = useQuery<{matches: MatchWithPlayers[], total_count: number}>({
    queryKey: ['matches-with-players-home'],
    queryFn: async () => {
      const response = await replaysApi.getMatchesWithPlayers(10);
      return response.data;
    },
  });

  const players = playersData || [];
  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_count || 0; // Use actual match count from API

  // Calculate stats
  const totalPlayers = players.length;
  const avgMMR = players.length > 0
    ? Math.round(players.reduce((sum, p) => sum + (p.recency_weighted_mmr || p.mmr), 0) / players.length)
    : 0;

  const isLoading = loadingPlayers || loadingMatches;

  return (
    <Box minH="100vh" py={8}>
      <Container maxW="container.xl">
        {/* Hero Section - Welcome message */}
        <Box textAlign="center" mb={10}>
          <Heading
            size="2xl"
            fontFamily="heading"
            fontWeight="bold"
            mb={3}
            color="gray.100"
          >
            Welcome to the{' '}
            <Text as="span" color="brand.500">
              Squad
            </Text>{' '}
            🎮
          </Heading>
          <Text fontSize="lg" color="gray.500" maxW="600px" mx="auto">
            Track your friend group's StarCraft matches, generate balanced teams, 
            and settle the debate of who's actually the best.
          </Text>
        </Box>

        {/* Main Layout - Desktop First: 3 columns */}
        <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={8}>
          
          {/* Left Column - Quick Actions */}
          <VStack spacing={4} align="stretch">
            <Heading size="md" fontFamily="heading" color="gray.300" mb={2}>
              <Text className="emoji-font" as="span">⚡</Text> Quick Actions
            </Heading>
            
            <QuickAction
              emoji="⚡"
              title="Generate Teams"
              subtitle="Fair and balanced matchups"
              color="brand.500"
              onClick={() => navigate('/balance')}
              isPrimary
            />
            
            <QuickAction
              emoji="📤"
              title="Upload Replays"
              subtitle="Add new match data"
              color="accent.500"
              onClick={() => navigate('/upload')}
            />
            
            <QuickAction
              emoji="🎯"
              title="Predict Match"
              subtitle="Who will win?"
              color="shield.500"
              onClick={() => navigate('/predictor')}
            />
            
            <QuickAction
              emoji="👥"
              title="View Squad"
              subtitle="All player stats"
              color="zerg.500"
              onClick={() => navigate('/players')}
            />
          </VStack>

          {/* Center Column - Stats & Recent Activity */}
          <VStack spacing={6} align="stretch">
            {/* Stats Row */}
            <Box>
              <Heading size="md" fontFamily="heading" color="gray.300" mb={4}>
                <Text className="emoji-font" as="span">📊</Text> Squad Stats
              </Heading>
              <SimpleGrid columns={3} spacing={3}>
                <FriendlyStat
                  label="Players"
                  value={isLoading ? '—' : totalPlayers}
                  emoji="👥"
                  color="brand.500"
                  size="sm"
                />
                <FriendlyStat
                  label="Matches"
                  value={isLoading ? '—' : totalMatches}
                  emoji="🎮"
                  color="accent.500"
                  size="sm"
                />
                <FriendlyStat
                  label="Avg MMR"
                  value={isLoading ? '—' : avgMMR}
                  emoji="📈"
                  color="shield.500"
                  size="sm"
                />
              </SimpleGrid>
            </Box>

            <Divider borderColor="space.700" />

            {/* Recent Matches */}
            <Box>
              <HStack justify="space-between" mb={4}>
                <Heading size="md" fontFamily="heading" color="gray.300">
                  <Text className="emoji-font" as="span">🕐</Text> Recent Matches
                </Heading>
                <Button
                  size="sm"
                  variant="ghost"
                  color="brand.400"
                  onClick={() => navigate('/history')}
                  fontFamily="heading"
                >
                  View All →
                </Button>
              </HStack>
              
              {matches.length > 0 ? (
                <VStack spacing={2} align="stretch">
                  {matches.slice(0, 5).map((match) => (
                    <MatchCard
                      key={match.id}
                      match={match}
                      onClick={() => navigate(`/history/${match.id}`)}
                    />
                  ))}
                </VStack>
              ) : (
                <Box
                  bg="space.800"
                  borderRadius="xl"
                  border="3px solid"
                  borderColor="space.900"
                  p={6}
                  textAlign="center"
                >
                  <Text fontSize="3xl" mb={2} className="emoji-font">
                    🎮
                  </Text>
                  <Text color="gray.500">
                    No matches yet. Upload some replays to get started!
                  </Text>
                </Box>
              )}
            </Box>
          </VStack>

          {/* Right Column - Leaderboard */}
          <VStack spacing={4} align="stretch">
            <HStack justify="space-between">
              <Heading size="md" fontFamily="heading" color="gray.300">
                <Text className="emoji-font" as="span">🏆</Text> Leaderboard
              </Heading>
              <Button
                size="sm"
                variant="ghost"
                color="brand.400"
                onClick={() => navigate('/leaderboard')}
                fontFamily="heading"
              >
                View Rankings →
              </Button>
            </HStack>
            
            {players.length > 0 ? (
              <PlayerSpotlight 
                players={players} 
                onClick={(id) => navigate(`/players/${id}`)}
              />
            ) : (
              <Box
                bg="space.800"
                borderRadius="xl"
                border="3px solid"
                borderColor="space.900"
                p={6}
                textAlign="center"
              >
                <Text fontSize="3xl" mb={2} className="emoji-font">
                  👥
                </Text>
                <Text color="gray.500">
                  No players yet. Upload replays to add players!
                </Text>
              </Box>
            )}

            <Divider borderColor="space.700" my={2} />

            {/* Fun Stats / Achievements teaser */}
            <Box
              bg="space.800"
              borderRadius="xl"
              border="3px solid"
              borderColor="space.900"
              boxShadow="3px 3px 0 var(--chakra-colors-space-900)"
              p={4}
            >
              <HStack spacing={3} mb={3}>
                <Text fontSize="xl" className="emoji-font">
                  🎖️
                </Text>
                <Text fontWeight="bold" fontFamily="heading" color="gray.100">
                  Quick Stats
                </Text>
              </HStack>
              <VStack spacing={2} align="stretch" fontSize="sm" color="gray.400">
                <HStack justify="space-between">
                  <Text>Total Games Played</Text>
                  <Text fontWeight="bold" color="brand.400">{totalMatches}</Text>
                </HStack>
                <HStack justify="space-between">
                  <Text>Active Players</Text>
                  <Text fontWeight="bold" color="accent.400">{totalPlayers}</Text>
                </HStack>
                 <HStack justify="space-between">
                   <Text>Highest MMR</Text>
                   <Text fontWeight="bold" color="shield.400">
                     {players.length > 0 
                       ? Math.round(Math.max(...players.map(p => p.recency_weighted_mmr || p.mmr)))
                       : '—'
                     }
                   </Text>
                 </HStack>
              </VStack>
            </Box>
          </VStack>
        </SimpleGrid>
      </Container>
    </Box>
  );
};

export default Home;
