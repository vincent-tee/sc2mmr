/**
 * Match History Page
 * Browse past games and results
 */
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  Badge,
  Button,
  useColorModeValue,
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { replaysApi } from '../api/endpoints';
import EmptyState from '../components/EmptyState';
import LoadingState, { MatchCardSkeleton } from '../components/LoadingState';
import { formatDuration } from '../utils/formatting';

const MatchHistory = () => {
  const navigate = useNavigate();
  const cardBg = useColorModeValue('white', 'gray.800');

  // Fetch matches
  const { data: matchesData, isLoading } = useQuery({
    queryKey: ['matches'],
    queryFn: async () => {
      const response = await replaysApi.getMatches(50);
      return response.data;
    },
  });

  const matches = matchesData || [];

  if (isLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading>Match History</Heading>
          <VStack spacing={4}>
            {Array.from({ length: 10 }).map((_, idx) => (
              <MatchCardSkeleton key={idx} />
            ))}
          </VStack>
        </VStack>
      </Container>
    );
  }

  if (matches.length === 0) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading>Match History</Heading>
          <EmptyState
            variant="stats"
            title="No Matches Yet"
            description="Upload some replay files to start tracking your game history."
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
            Match History
          </Heading>
          <Text color="gray.500">
            {matches.length} matches recorded
          </Text>
        </Box>

        {/* Match List */}
        <VStack spacing={4} align="stretch">
          {matches.map((match) => (
            <Card
              key={match.id}
              bg={cardBg}
              cursor="pointer"
              onClick={() => navigate(`/history/${match.id}`)}
              transition="all 0.2s"
              _hover={{
                transform: 'translateY(-2px)',
                boxShadow: 'xl',
              }}
            >
              <CardBody>
                <HStack justify="space-between" align="start">
                  <VStack align="start" spacing={2} flex={1}>
                    <HStack spacing={3}>
                      <Heading size="md">{match.map_name}</Heading>
                      <Badge colorScheme="blue">{match.game_mode}</Badge>
                    </HStack>

                    <HStack spacing={4} fontSize="sm" color="gray.500">
                      <Text>
                        {new Date(match.played_at).toLocaleString()}
                      </Text>
                      <Text>•</Text>
                      <Text>
                        Duration: {formatDuration(match.duration_seconds)}
                      </Text>
                    </HStack>
                  </VStack>

                  <Button size="sm" variant="ghost">
                    View Details
                  </Button>
                </HStack>
              </CardBody>
            </Card>
          ))}
        </VStack>
      </VStack>
    </Container>
  );
};

export default MatchHistory;
