/**
 * RankBadge Component Examples
 * This file demonstrates various usage patterns for the RankBadge component
 * This is a reference file - not used in production
 */

import { VStack, HStack, Box, Text, Container, Heading, Divider, Grid, GridItem } from '@chakra-ui/react';
import RankBadge from '../RankBadge';

/**
 * Example 1: Basic usage with different MMR values
 * Shows all rank tiers
 */
export const AllRankTiers = () => (
  <VStack spacing={4} align="start">
    <Heading size="md">All Rank Tiers</Heading>
    <HStack spacing={4} wrap="wrap">
      <RankBadge mmr={750} />      {/* Bronze */}
      <RankBadge mmr={1750} />     {/* Silver */}
      <RankBadge mmr={2150} />     {/* Gold */}
      <RankBadge mmr={2450} />     {/* Platinum */}
      <RankBadge mmr={2850} />     {/* Diamond */}
      <RankBadge mmr={3450} />     {/* Master */}
      <RankBadge mmr={3900} />     {/* Grandmaster */}
    </HStack>
  </VStack>
);

/**
 * Example 2: Different size variants
 * Shows the same rank in all available sizes
 */
export const SizeVariants = () => (
  <VStack spacing={4} align="start">
    <Heading size="md">Size Variants (Diamond Rank - 2850 MMR)</Heading>
    <VStack spacing={3}>
      <HStack><Text w="100px">xs (extra small):</Text><RankBadge mmr={2850} size="xs" /></HStack>
      <HStack><Text w="100px">sm (small):</Text><RankBadge mmr={2850} size="sm" /></HStack>
      <HStack><Text w="100px">md (medium):</Text><RankBadge mmr={2850} size="md" /></HStack>
      <HStack><Text w="100px">lg (large):</Text><RankBadge mmr={2850} size="lg" /></HStack>
    </VStack>
  </VStack>
);

/**
 * Example 3: With MMR display
 * Shows rank badge with MMR value displayed
 */
export const WithMMRDisplay = () => (
  <VStack spacing={4} align="start">
    <Heading size="md">With MMR Display</Heading>
    <HStack spacing={4} wrap="wrap">
      <RankBadge mmr={750} showMMR={true} />      {/* Bronze with MMR */}
      <RankBadge mmr={1750} showMMR={true} />     {/* Silver with MMR */}
      <RankBadge mmr={2150} showMMR={true} />     {/* Gold with MMR */}
      <RankBadge mmr={2450} showMMR={true} />     {/* Platinum with MMR */}
      <RankBadge mmr={2850} showMMR={true} />     {/* Diamond with MMR */}
      <RankBadge mmr={3450} showMMR={true} />     {/* Master with MMR */}
      <RankBadge mmr={3900} showMMR={true} />     {/* Grandmaster with MMR */}
    </HStack>
  </VStack>
);

/**
 * Example 4: Without icon display
 * Shows just rank name without icon
 */
export const WithoutIcon = () => (
  <VStack spacing={4} align="start">
    <Heading size="md">Without Icon Display</Heading>
    <HStack spacing={4} wrap="wrap">
      <RankBadge mmr={750} showIcon={false} />      {/* Bronze */}
      <RankBadge mmr={1750} showIcon={false} />     {/* Silver */}
      <RankBadge mmr={2150} showIcon={false} />     {/* Gold */}
      <RankBadge mmr={2450} showIcon={false} />     {/* Platinum */}
      <RankBadge mmr={2850} showIcon={false} />     {/* Diamond */}
      <RankBadge mmr={3450} showIcon={false} />     {/* Master */}
      <RankBadge mmr={3900} showIcon={false} />     {/* Grandmaster */}
    </HStack>
  </VStack>
);

/**
 * Example 5: Player card layout
 * Realistic example of RankBadge in a player display context
 */
export const PlayerCardLayout = () => {
  const mockPlayer = {
    name: 'ProGamer123',
    mmr: 2850,
    winRate: 0.55,
    totalGames: 247,
  };

  return (
    <VStack spacing={4} align="start">
      <Heading size="md">Player Card Layout</Heading>
      <Box
        bg="rgba(26, 32, 44, 0.8)"
        border="1px solid"
        borderColor="whiteAlpha.200"
        borderRadius="lg"
        p={4}
        minW="300px"
      >
        <VStack spacing={3} align="center">
          <Text fontSize="lg" fontWeight="bold">{mockPlayer.name}</Text>
          <RankBadge mmr={mockPlayer.mmr} size="md" showMMR={true} />
          <HStack spacing={4} width="100%">
            <Box flex={1}>
              <Text fontSize="sm" color="gray.500">Win Rate</Text>
              <Text fontWeight="bold">{(mockPlayer.winRate * 100).toFixed(1)}%</Text>
            </Box>
            <Box flex={1}>
              <Text fontSize="sm" color="gray.500">Total Games</Text>
              <Text fontWeight="bold">{mockPlayer.totalGames}</Text>
            </Box>
          </HStack>
        </VStack>
      </Box>
    </VStack>
  );
};

/**
 * Example 6: Match player comparison
 * Showing two players' ranks side-by-side
 */
export const PlayerComparison = () => (
  <VStack spacing={4} align="start">
    <Heading size="md">Match Player Comparison</Heading>
    <HStack spacing={8} justify="center" width="100%">
      {/* Team 1 */}
      <VStack spacing={2} align="center">
        <Text fontWeight="bold" color="brand.300">Team 1</Text>
        <RankBadge mmr={2550} size="md" showMMR={true} />
        <RankBadge mmr={2850} size="md" showMMR={true} />
        <RankBadge mmr={2350} size="md" showMMR={true} />
      </VStack>

      {/* vs */}
      <Text fontSize="2xl" fontWeight="bold" color="gray.500">vs</Text>

      {/* Team 2 */}
      <VStack spacing={2} align="center">
        <Text fontWeight="bold" color="brand.300">Team 2</Text>
        <RankBadge mmr={2650} size="md" showMMR={true} />
        <RankBadge mmr={2450} size="md" showMMR={true} />
        <RankBadge mmr={2500} size="md" showMMR={true} />
      </VStack>
    </HStack>
  </VStack>
);

/**
 * Example 7: Leaderboard row
 * Realistic leaderboard display with rank badges
 */
export const LeaderboardRow = () => {
  const leaderboard = [
    { rank: 1, name: 'ProPlayer', mmr: 3450 },
    { rank: 2, name: 'TopRanked', mmr: 3380 },
    { rank: 3, name: 'MasterTactician', mmr: 3250 },
    { rank: 4, name: 'DiamondProspect', mmr: 2890 },
    { rank: 5, name: 'PlatinumStriver', mmr: 2580 },
  ];

  return (
    <VStack spacing={4} align="start" width="100%">
      <Heading size="md">Leaderboard Example</Heading>
      <Box width="100%">
        {leaderboard.map((player) => (
          <HStack
            key={player.rank}
            spacing={4}
            p={3}
            borderBottom="1px solid"
            borderColor="whiteAlpha.100"
            justify="space-between"
          >
            <HStack flex={1} spacing={4}>
              <Text fontWeight="bold" minW="40px" color="brand.300">#{player.rank}</Text>
              <Text flex={1}>{player.name}</Text>
            </HStack>
            <RankBadge mmr={player.mmr} size="sm" showMMR={true} />
          </HStack>
        ))}
      </Box>
    </VStack>
  );
};

/**
 * Example 8: Rank tier boundaries
 * Demonstrates MMR values at rank boundaries
 */
export const RankBoundaries = () => (
  <VStack spacing={4} align="start">
    <Heading size="md">Rank Boundaries</Heading>
    <Grid templateColumns="repeat(2, 1fr)" gap={4} width="100%">
      <GridItem>
        <Text fontSize="sm" color="gray.500">Bottom of rank</Text>
        <RankBadge mmr={1500} showMMR={true} />
      </GridItem>
      <GridItem>
        <Text fontSize="sm" color="gray.500">Top of rank</Text>
        <RankBadge mmr={1499} showMMR={true} />
      </GridItem>

      <GridItem>
        <Text fontSize="sm" color="gray.500">Bottom of Gold</Text>
        <RankBadge mmr={2000} showMMR={true} />
      </GridItem>
      <GridItem>
        <Text fontSize="sm" color="gray.500">Top of Gold</Text>
        <RankBadge mmr={2299} showMMR={true} />
      </GridItem>

      <GridItem>
        <Text fontSize="sm" color="gray.500">Bottom of Master</Text>
        <RankBadge mmr={3300} showMMR={true} />
      </GridItem>
      <GridItem>
        <Text fontSize="sm" color="gray.500">Grandmaster</Text>
        <RankBadge mmr={3800} showMMR={true} />
      </GridItem>
    </Grid>
  </VStack>
);

/**
 * Main example gallery
 * Displays all examples on one page
 */
export const RankBadgeExamplesGallery = () => (
  <Container maxW="6xl" py={8}>
    <VStack spacing={8} align="stretch">
      <Box>
        <Heading size="lg" mb={4}>RankBadge Component Examples</Heading>
        <Text color="gray.400" mb={6}>
          These examples demonstrate various usage patterns and configurations for the RankBadge component.
        </Text>
      </Box>

      <AllRankTiers />
      <Divider />

      <SizeVariants />
      <Divider />

      <WithMMRDisplay />
      <Divider />

      <WithoutIcon />
      <Divider />

      <PlayerCardLayout />
      <Divider />

      <PlayerComparison />
      <Divider />

      <LeaderboardRow />
      <Divider />

      <RankBoundaries />
    </VStack>
  </Container>
);

// Export individual examples for use in storybook or other contexts
export const examples = [
  { name: 'All Rank Tiers', component: AllRankTiers },
  { name: 'Size Variants', component: SizeVariants },
  { name: 'With MMR Display', component: WithMMRDisplay },
  { name: 'Without Icon', component: WithoutIcon },
  { name: 'Player Card Layout', component: PlayerCardLayout },
  { name: 'Player Comparison', component: PlayerComparison },
  { name: 'Leaderboard Row', component: LeaderboardRow },
  { name: 'Rank Boundaries', component: RankBoundaries },
];
