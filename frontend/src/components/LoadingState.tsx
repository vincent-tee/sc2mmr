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
  return (
    <Box bg="space.800" border="2px solid" borderColor="space.700" borderRadius="xl" p={4}>
      <VStack spacing={2}>
        <SkeletonCircle size="16" startColor="space.700" endColor="space.600" />
        <Skeleton height="20px" width="100px" startColor="space.700" endColor="space.600" />
        <Skeleton height="16px" width="80px" startColor="space.700" endColor="space.600" />
      </VStack>
    </Box>
  );
};

export const PlayerGridSkeleton: React.FC<PlayerGridSkeletonProps> = ({ count = 8 }) => {
  return (
    <SimpleGrid columns={{ base: 2, md: 3, lg: 4, xl: 5 }} spacing={4}>
      {Array.from({ length: count }).map((_, idx) => (
        <PlayerCardSkeleton key={idx} />
      ))}
    </SimpleGrid>
  );
};

export const TeamResultSkeleton: React.FC = () => {
  return (
    <Box bg="space.800" border="3px solid" borderColor="space.700" borderRadius="xl" p={6}>
      <VStack spacing={4} align="stretch">
        <Skeleton height="24px" width="150px" startColor="space.700" endColor="space.600" />
        <Skeleton height="40px" width="200px" startColor="space.700" endColor="space.600" />

        <HStack spacing={8} align="start">
          <VStack flex={1} spacing={2}>
            <Skeleton height="20px" width="60px" startColor="space.700" endColor="space.600" />
            {Array.from({ length: 3 }).map((_, idx) => (
              <Skeleton key={idx} height="60px" width="100%" startColor="space.700" endColor="space.600" borderRadius="lg" />
            ))}
          </VStack>

          <VStack flex={1} spacing={2}>
            <Skeleton height="20px" width="60px" startColor="space.700" endColor="space.600" />
            {Array.from({ length: 3 }).map((_, idx) => (
              <Skeleton key={idx} height="60px" width="100%" startColor="space.700" endColor="space.600" borderRadius="lg" />
            ))}
          </VStack>
        </HStack>

        <Skeleton height="16px" width="100%" startColor="space.700" endColor="space.600" />
        <Skeleton height="40px" width="120px" startColor="space.700" endColor="space.600" borderRadius="lg" />
      </VStack>
    </Box>
  );
};

export const MatchCardSkeleton: React.FC = () => {
  return (
    <Box bg="space.800" border="2px solid" borderColor="space.700" borderRadius="xl" p={4}>
      <HStack spacing={4} justify="space-between">
        <VStack align="start" flex={1}>
          <Skeleton height="20px" width="150px" startColor="space.700" endColor="space.600" />
          <Skeleton height="16px" width="100px" startColor="space.700" endColor="space.600" />
        </VStack>
        <Skeleton height="24px" width="80px" startColor="space.700" endColor="space.600" borderRadius="md" />
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

  const defaultMessages: Record<LoadingStateVariant, string> = {
    players: 'Loading players...',
    team: 'Loading team data...',
    match: 'Loading match data...',
  };

  return (
    <VStack
      spacing={6}
      align="stretch"
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={message || defaultMessages[variant]}
      pt={8}
    >
      {message && (
        <Text 
          color="brand.400" 
          textAlign="center" 
          fontSize="lg" 
          fontWeight="bold"
          fontFamily="heading"
          letterSpacing="wide"
        >
          {message.toUpperCase()}
        </Text>
      )}
      <Box px={message ? 4 : 0}>
        {variants[variant] || variants.players}
      </Box>
    </VStack>
  );
};

export default LoadingState;
