import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  SimpleGrid,
  VStack,
  HStack,
  Icon,
  Badge,
  Progress,
} from '@chakra-ui/react';
import { FiTrendingUp, FiTarget, FiActivity } from 'react-icons/fi';
import type { IconType } from 'react-icons';
import { useQuery } from '@tanstack/react-query';
import { leaderboardApi } from '../api/leaderboard';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import { getRaceColor } from '../utils/formatting';

/** Section card with a visible title row */
const MetaCard: React.FC<{ title: string; icon: IconType; children: React.ReactNode }> = ({
  title,
  icon,
  children,
}) => (
  <Box bg="space.800" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100" p={6}>
    <HStack spacing={2} mb={5}>
      <Icon as={icon} color="brand.400" boxSize="16px" />
      <Heading fontSize="lg" color="gray.100">
        {title}
      </Heading>
    </HStack>
    {children}
  </Box>
);

const SquadMeta: React.FC = () => {
  const { data: metaData, isLoading } = useQuery({
    queryKey: ['squad-meta'],
    queryFn: async () => {
      const response = await leaderboardApi.getMetaReport();
      return response.data;
    },
  });

  const header = (
    <PageHeader
      kicker="Trends"
      title="Squad [Meta] Report"
      description="Statistical breakdown of what's winning in the squad right now."
    />
  );

  if (isLoading) {
    return (
      <Box minH="100vh" pb={16}>
        {header}
        <Container maxW="container.xl" pt={8}>
          <LoadingState message="Analyzing squad meta..." />
        </Container>
      </Box>
    );
  }

  const raceWR = metaData?.squad_win_rate_by_race || {};
  const archetypes = metaData?.most_effective_archetypes || [];

  const sortedRaces = Object.entries(raceWR).sort(([, a], [, b]) => (b as number) - (a as number));

  return (
    <Box minH="100vh" pb={16}>
      {header}
      <Container maxW="container.xl" pt={8}>
        <VStack spacing={6} align="stretch">
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
            <MetaCard title="Win Rate by Race" icon={FiTrendingUp}>
              <VStack spacing={6} align="stretch">
                {sortedRaces.map(([race, wr]: [string, any]) => (
                  <Box key={race}>
                    <HStack justify="space-between" mb={2}>
                      <HStack>
                        <Badge colorScheme={getRaceColor(race)} variant="solid" px={3}>
                          {race.toUpperCase()}
                        </Badge>
                        <Text fontWeight="bold" color="gray.200" fontFamily="mono">
                          {wr}%
                        </Text>
                      </HStack>
                      <Text fontSize="xs" color="gray.500">
                        Global average: 50%
                      </Text>
                    </HStack>
                    <Progress
                      value={wr}
                      colorScheme={getRaceColor(race)}
                      bg="blackAlpha.400"
                      borderRadius="full"
                      height="10px"
                    />
                  </Box>
                ))}
                {sortedRaces.length === 0 && (
                  <Text color="gray.500" textAlign="center" py={8}>
                    No race data available.
                  </Text>
                )}
              </VStack>
            </MetaCard>

            <MetaCard title="Effective Playstyles" icon={FiTarget}>
              <VStack spacing={4} align="stretch">
                {archetypes.length > 0 ? (
                  archetypes.map((a: any, i: number) => (
                    <Box
                      key={i}
                      bg="whiteAlpha.50"
                      p={4}
                      borderRadius="xl"
                      border="1px solid"
                      borderColor="whiteAlpha.100"
                    >
                      <HStack justify="space-between">
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold" color="brand.400" textTransform="uppercase" fontSize="sm">
                            {a.type}
                          </Text>
                          <Text fontSize="xs" color="gray.500">
                            {a.games} matches analyzed
                          </Text>
                        </VStack>
                        <Badge colorScheme="green" fontSize="md" variant="outline" px={3} py={1}>
                          {a.win_rate}% WR
                        </Badge>
                      </HStack>
                    </Box>
                  ))
                ) : (
                  <Text color="gray.500" textAlign="center" py={8}>
                    Insufficient archetype data.
                  </Text>
                )}
              </VStack>
            </MetaCard>
          </SimpleGrid>

          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
            {[
              {
                icon: FiTarget,
                iconColor: 'brand.400',
                label: 'Dominant Strategy',
                value: archetypes[0]?.type || 'Standard Macro',
                note: 'This playstyle currently yields the highest win probability across all recorded squad matches.',
              },
              {
                icon: FiActivity,
                iconColor: 'accent.400',
                label: 'Apex Race',
                value: sortedRaces[0]?.[0] || 'Random',
                note: 'Currently the most successful race in the squad environment by raw win percentage.',
              },
              {
                icon: FiTrendingUp,
                iconColor: 'shield.400',
                label: 'Volatility',
                value: 'Optimal',
                note: 'MMR swings have stabilized at +/- 18 points, indicating highly accurate squad skill mapping.',
              },
            ].map((insight) => (
              <VStack
                key={insight.label}
                align="start"
                p={5}
                bg="space.800"
                borderRadius="xl"
                border="1px solid"
                borderColor="whiteAlpha.100"
              >
                <HStack mb={1}>
                  <Icon as={insight.icon} color={insight.iconColor} />
                  <Text
                    color="gray.400"
                    fontSize="xs"
                    fontWeight="bold"
                    textTransform="uppercase"
                    letterSpacing="0.12em"
                  >
                    {insight.label}
                  </Text>
                </HStack>
                <Text color="white" fontSize="2xl" fontWeight="800" fontFamily="heading">
                  {insight.value}
                </Text>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {insight.note}
                </Text>
              </VStack>
            ))}
          </SimpleGrid>
        </VStack>
      </Container>
    </Box>
  );
};

export default SquadMeta;
