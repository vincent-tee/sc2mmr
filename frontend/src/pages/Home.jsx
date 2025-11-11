/**
 * Home/Dashboard Page
 * Overview with quick actions and recent stats
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
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Card,
  CardBody,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiUpload, FiUsers, FiZap, FiTrendingUp } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { playersApi, replaysApi } from '../api/endpoints';
import LoadingState from '../components/LoadingState';

const Home = () => {
  const navigate = useNavigate();
  const cardBg = useColorModeValue('white', 'gray.800');

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
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Hero Section */}
        <Box textAlign="center" py={8}>
          <Heading size="2xl" mb={4}>
            SC2 MMR Tracker
          </Heading>
          <Text fontSize="xl" color="gray.500" mb={8}>
            Build fair teams and track your gaming group's performance
          </Text>

          <HStack spacing={4} justify="center">
            <Button
              size="lg"
              variant="primary"
              leftIcon={<FiZap />}
              onClick={() => navigate('/balance')}
            >
              Generate Teams
            </Button>
            <Button
              size="lg"
              variant="outline"
              leftIcon={<FiUpload />}
              onClick={() => navigate('/upload')}
            >
              Upload Replays
            </Button>
          </HStack>
        </Box>

        {/* Stats Grid */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
          <Card bg={cardBg}>
            <CardBody>
              <Stat>
                <StatLabel>Total Players</StatLabel>
                <StatNumber>{isLoading ? '-' : totalPlayers}</StatNumber>
                <StatHelpText>Active in your group</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={cardBg}>
            <CardBody>
              <Stat>
                <StatLabel>Games Played</StatLabel>
                <StatNumber>{isLoading ? '-' : totalGames}</StatNumber>
                <StatHelpText>Total matches tracked</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={cardBg}>
            <CardBody>
              <Stat>
                <StatLabel>Average MMR</StatLabel>
                <StatNumber>{isLoading ? '-' : avgMMR}</StatNumber>
                <StatHelpText>Group skill level</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Quick Actions */}
        <Box>
          <Heading size="md" mb={4}>
            Quick Actions
          </Heading>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
            <QuickActionCard
              icon={FiZap}
              title="Generate Teams"
              description="Create balanced team compositions"
              color="brand.500"
              onClick={() => navigate('/balance')}
            />
            <QuickActionCard
              icon={FiUpload}
              title="Upload Replays"
              description="Add new replay files"
              color="accent.500"
              onClick={() => navigate('/upload')}
            />
            <QuickActionCard
              icon={FiUsers}
              title="View Players"
              description="See player statistics"
              color="purple.500"
              onClick={() => navigate('/players')}
            />
            <QuickActionCard
              icon={FiTrendingUp}
              title="Match History"
              description="Browse past games"
              color="green.500"
              onClick={() => navigate('/history')}
            />
          </SimpleGrid>
        </Box>

        {/* Recent Activity (if we have data) */}
        {matches.length > 0 && (
          <Box>
            <HStack justify="space-between" mb={4}>
              <Heading size="md">Recent Matches</Heading>
              <Button size="sm" variant="ghost" onClick={() => navigate('/history')}>
                View All
              </Button>
            </HStack>
            <VStack spacing={2} align="stretch">
              {matches.slice(0, 5).map((match) => (
                <Card key={match.id} bg={cardBg}>
                  <CardBody>
                    <HStack justify="space-between">
                      <VStack align="start" spacing={0}>
                        <Text fontWeight="bold">{match.map_name}</Text>
                        <Text fontSize="sm" color="gray.500">
                          {match.game_mode} • {new Date(match.played_at).toLocaleDateString()}
                        </Text>
                      </VStack>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => navigate(`/history/${match.id}`)}
                      >
                        Details
                      </Button>
                    </HStack>
                  </CardBody>
                </Card>
              ))}
            </VStack>
          </Box>
        )}
      </VStack>
    </Container>
  );
};

// Quick Action Card Component
const QuickActionCard = ({ icon, title, description, color, onClick }) => {
  const cardBg = useColorModeValue('white', 'gray.800');

  return (
    <Card
      bg={cardBg}
      cursor="pointer"
      onClick={onClick}
      transition="all 0.2s"
      _hover={{
        transform: 'translateY(-4px)',
        boxShadow: 'xl',
      }}
    >
      <CardBody>
        <VStack spacing={3} align="start">
          <Icon as={icon} boxSize={8} color={color} />
          <VStack align="start" spacing={1}>
            <Text fontWeight="bold" fontSize="lg">
              {title}
            </Text>
            <Text fontSize="sm" color="gray.500">
              {description}
            </Text>
          </VStack>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default Home;
