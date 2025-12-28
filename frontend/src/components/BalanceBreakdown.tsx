/**
 * BalanceBreakdown - Collapsible detailed breakdown of ML balance results
 * Shows player components, synergy bonuses, and accuracy metrics
 */
import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Badge,
  Button,
  Collapse,
  Grid,
  Progress,
  Alert,
  AlertIcon,
  AlertTitle,
  Tooltip,
  Divider,
  useDisclosure,
  Icon,
} from '@chakra-ui/react';
import { FiChevronDown, FiChevronUp, FiUsers, FiZap } from 'react-icons/fi';

interface MLPlayerBreakdown {
  player_id: number;
  player_name: string;
  session_mmr: number;
  combat: number;
  economic: number;
  efficiency: number;
  ml_rating: number;
  total_games: number;
}

interface TeamMLBreakdown {
  players: MLPlayerBreakdown[];
  total_ml_rating: number;
  synergy_bonus: number;
}

export interface MLBalanceData {
  team_1: TeamMLBreakdown;
  team_2: TeamMLBreakdown;
  balance_score: number;
  weights_used: Record<string, number>;
  component_accuracies: Record<string, number>;
  is_adaptive: boolean;
}

interface BalanceBreakdownProps {
  balanceData: MLBalanceData;
}

const BalanceBreakdown: React.FC<BalanceBreakdownProps> = ({ balanceData }) => {
  const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: false });

  const getBalanceRating = (score: number) => {
    if (score > 0.85) return { label: 'Excellent', color: 'green' as const };
    if (score > 0.7) return { label: 'Good', color: 'yellow' as const };
    return { label: 'Fair', color: 'red' as const };
  };

  const balanceRating = getBalanceRating(balanceData.balance_score);

  const PlayerCard = ({ player }: { player: MLPlayerBreakdown }) => (
    <HStack
      justify="space-between"
      p={3}
      bg="space.900"
      borderRadius="md"
      mb={2}
    >
      <VStack align="start" spacing={0}>
        <Text fontWeight="bold" color="white">{player.player_name}</Text>
        <Text fontSize="xs" color="gray.500">
          {player.total_games} matches | ML: {Math.round(player.ml_rating)}
        </Text>
      </VStack>

      <HStack spacing={3}>
        <Tooltip label="Session-Weighted MMR" placement="top">
          <Box textAlign="right">
            <Text fontSize="xs" color="gray.400">MMR</Text>
            <Text fontWeight="bold" fontSize="sm" color="white">
              {Math.round(player.session_mmr)}
            </Text>
          </Box>
        </Tooltip>

        <Tooltip label="Combat Score" placement="top">
          <Box textAlign="right">
            <Text fontSize="xs" color="orange.400">CBT</Text>
            <Text fontWeight="bold" fontSize="sm" color="orange.400">
              {player.combat.toFixed(0)}
            </Text>
          </Box>
        </Tooltip>

        <Tooltip label="Economic Score" placement="top">
          <Box textAlign="right">
            <Text fontSize="xs" color="green.400">ECO</Text>
            <Text fontWeight="bold" fontSize="sm" color="green.400">
              {player.economic.toFixed(0)}
            </Text>
          </Box>
        </Tooltip>

        <Tooltip label="Efficiency Score" placement="top">
          <Box textAlign="right">
            <Text fontSize="xs" color="blue.400">EFF</Text>
            <Text fontWeight="bold" fontSize="sm" color="blue.400">
              {player.efficiency.toFixed(0)}
            </Text>
          </Box>
        </Tooltip>
      </HStack>
    </HStack>
  );

  const TeamBreakdown = ({
    team,
    teamName,
  }: {
    team: TeamMLBreakdown;
    teamName: string;
  }) => (
    <VStack align="stretch" spacing={3}>
      <HStack justify="space-between" align="center">
        <HStack>
          <Icon as={FiUsers} color="brand.400" />
          <Heading size="sm" color="white">{teamName}</Heading>
        </HStack>
        <HStack spacing={2}>
          <Badge colorScheme="purple" variant="outline">
            Total: {Math.round(team.total_ml_rating)}
          </Badge>
          {team.synergy_bonus > 0 && (
            <Badge colorScheme="cyan">
              +{team.synergy_bonus.toFixed(1)} Synergy
            </Badge>
          )}
        </HStack>
      </HStack>

      {team.players.map((player, i) => (
        <PlayerCard key={`${teamName}-${i}`} player={player} />
      ))}

      {team.synergy_bonus > 0 && (
        <Alert status="success" variant="subtle" borderRadius="md">
          <AlertIcon as={FiZap} />
          <VStack align="start" spacing={0}>
            <AlertTitle fontSize="sm">
              Synergy Bonus: +{team.synergy_bonus.toFixed(1)}
            </AlertTitle>
            <Text fontSize="xs" color="gray.300">
              Players on this team have good historical chemistry (duo/trio win rates)
            </Text>
          </VStack>
        </Alert>
      )}
    </VStack>
  );

  return (
    <Box mt={6}>
      <Button
        onClick={onToggle}
        variant="outline"
        colorScheme="brand"
        width="full"
        size="md"
        rightIcon={isOpen ? <FiChevronUp /> : <FiChevronDown />}
      >
        {isOpen ? 'Hide' : 'Show'} Balance Breakdown
      </Button>

      <Collapse in={isOpen} animateOpacity>
        <VStack
          align="stretch"
          spacing={6}
          mt={4}
          p={4}
          bg="space.800"
          borderRadius="lg"
          border="1px solid"
          borderColor="gray.700"
        >
          {/* Overall Balance Score */}
          <Box>
            <HStack justify="space-between" mb={2}>
              <Text fontWeight="bold" color="white">Overall Balance Score</Text>
              <Badge colorScheme={balanceRating.color} fontSize="sm">
                {balanceRating.label}
              </Badge>
            </HStack>
            <Progress
              value={balanceData.balance_score * 100}
              colorScheme={balanceRating.color}
              size="lg"
              borderRadius="full"
              bg="whiteAlpha.200"
            />
            <Text fontSize="xs" color="gray.400" mt={1}>
              {Math.round(balanceData.balance_score * 100)}% balanced
            </Text>
          </Box>

          {/* Teams */}
          <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
            <TeamBreakdown team={balanceData.team_1} teamName="Team 1" />
            <TeamBreakdown team={balanceData.team_2} teamName="Team 2" />
          </Grid>

          {/* Component Accuracies */}
          <Box>
            <Heading size="sm" mb={3} color="white">
              Component Accuracy (All Match History)
            </Heading>

            <VStack align="stretch" spacing={2}>
              {Object.entries(balanceData.component_accuracies).map(([comp, accuracy]) => {
                const weight = balanceData.weights_used[comp] || 0;
                const weightPercent = Math.round(weight * 100);
                const accuracyPercent = Math.round(accuracy * 100);

                return (
                  <HStack
                    key={comp}
                    justify="space-between"
                    p={2}
                    bg="space.900"
                    borderRadius="md"
                  >
                    <Text fontSize="sm" fontWeight="medium" color="white" textTransform="capitalize">
                      {comp.replace('_', ' ')}
                    </Text>
                    <HStack spacing={4}>
                      <Badge
                        colorScheme={accuracy > 0.7 ? 'green' : accuracy > 0.65 ? 'yellow' : 'red'}
                      >
                        {accuracyPercent}% accurate
                      </Badge>
                      <Badge variant="outline" colorScheme="gray">
                        {weightPercent}% weight
                      </Badge>
                    </HStack>
                    <Progress
                      value={accuracyPercent}
                      width="80px"
                      colorScheme={accuracy > 0.7 ? 'green' : 'yellow'}
                      size="sm"
                      bg="whiteAlpha.200"
                    />
                  </HStack>
                );
              })}
            </VStack>

            <Text fontSize="xs" color="gray.500" mt={3} fontStyle="italic">
              {balanceData.is_adaptive
                ? 'Weights automatically adapt based on prediction accuracy across all matches.'
                : 'Using manually configured weights.'}
            </Text>
          </Box>
        </VStack>
      </Collapse>
    </Box>
  );
};

export default BalanceBreakdown;
