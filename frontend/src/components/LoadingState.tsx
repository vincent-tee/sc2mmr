/**
 * LoadingState Component
 * Skeleton screens for data loading
 */
import React from 'react';
import {
  Box,
  Skeleton,
  SkeletonCircle,
  VStack,
  HStack,
  SimpleGrid,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';

type LoadingStateVariant = 'players' | 'team' | 'match';

interface LoadingStateProps {
  variant?: LoadingStateVariant;
  count?: number;
  message?: string;
}

interface PlayerGridSkeletonProps {
  count?: number;
}

export const PlayerCardSkeleton: React.FC = () => {
  const bgColor = useColorModeValue('white', 'gray.800');

  return (
    <Box bg={bgColor} borderRadius="lg" p={4}>
      <VStack spacing={2}>
        <SkeletonCircle size="16" />
        <Skeleton height="20px" width="100px" />
        <Skeleton height="16px" width="80px" />
      </VStack>
    </Box>
  );
};

export const PlayerGridSkeleton: React.FC<PlayerGridSkeletonProps> = ({ count = 8 }) => {
  return (
    <SimpleGrid columns={{ base: 2, md: 3, lg: 4 }} spacing={4}>
      {Array.from({ length: count }).map((_, idx) => (
        <PlayerCardSkeleton key={idx} />
      ))}
    </SimpleGrid>
  );
};

export const TeamResultSkeleton: React.FC = () => {
  const bgColor = useColorModeValue('white', 'gray.800');

  return (
    <Box bg={bgColor} borderRadius="lg" p={6}>
      <VStack spacing={4} align="stretch">
        <Skeleton height="24px" width="150px" />
        <Skeleton height="40px" width="200px" />

        <HStack spacing={8} align="start">
          <VStack flex={1} spacing={2}>
            <Skeleton height="20px" width="60px" />
            {Array.from({ length: 3 }).map((_, idx) => (
              <Skeleton key={idx} height="60px" width="100%" />
            ))}
          </VStack>

          <VStack flex={1} spacing={2}>
            <Skeleton height="20px" width="60px" />
            {Array.from({ length: 3 }).map((_, idx) => (
              <Skeleton key={idx} height="60px" width="100%" />
            ))}
          </VStack>
        </HStack>

        <Skeleton height="16px" width="100%" />
        <Skeleton height="40px" width="120px" />
      </VStack>
    </Box>
  );
};

export const MatchCardSkeleton: React.FC = () => {
  const bgColor = useColorModeValue('white', 'gray.800');

  return (
    <Box bg={bgColor} borderRadius="lg" p={4}>
      <HStack spacing={4} justify="space-between">
        <VStack align="start" flex={1}>
          <Skeleton height="20px" width="150px" />
          <Skeleton height="16px" width="100px" />
        </VStack>
        <Skeleton height="24px" width="80px" />
      </HStack>
    </Box>
  );
};

const LoadingState: React.FC<LoadingStateProps> = ({ variant = 'players', count = 8, message }) => {
  const variants: Record<LoadingStateVariant, React.ReactNode> = {
    players: <PlayerGridSkeleton count={count} />,
    team: <TeamResultSkeleton />,
    match: <MatchCardSkeleton />,
  };

  return (
    <VStack spacing={4} align="stretch">
      {message && (
        <Text color="gray.400" textAlign="center" fontSize="sm">
          {message}
        </Text>
      )}
      {variants[variant] || variants.players}
    </VStack>
  );
};

export default LoadingState;
