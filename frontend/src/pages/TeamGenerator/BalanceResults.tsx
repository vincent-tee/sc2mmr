/**
 * BalanceResults Component - Team Balance Suggestions Display
 * Shows balance results and allows export of team configurations
 */
import {
  Box,
  Heading,
  VStack,
  HStack,
  Text,
  Badge,
  Progress,
  Icon,
  Divider,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Button,
} from '@chakra-ui/react';
import {
  FiChevronDown,
  FiCopy,
  FiDownload,
  FiShare2,
  FiTarget,
  FiActivity,
} from 'react-icons/fi';
import PlayerCard from '@/components/PlayerCard';
import TacticalCard from '@/components/TacticalCard';
import VSScreen from '@/components/VSScreen';
import { formatMMR, getFairnessColor } from '@/utils/formatting';
import type { TeamSuggestion } from '@/types/api';

// Extended TeamSuggestion with additional impact fields
interface TeamSuggestionWithImpact extends TeamSuggestion {
  team_1_avg_impact?: number;
  team_2_avg_impact?: number;
}

interface BalanceResultsProps {
  suggestions: TeamSuggestionWithImpact[];
  onExport: (
    suggestion: TeamSuggestionWithImpact,
    format: 'text' | 'download'
  ) => Promise<void>;
}

const BalanceResults: React.FC<BalanceResultsProps> = ({
  suggestions,
  onExport,
}) => {
  if (suggestions.length === 0) {
    return null;
  }

  return (
    <Box>
      <Heading
        size="lg"
        mb={6}
        fontFamily="heading"
        textTransform="uppercase"
        letterSpacing="wider"
        color="brand.400"
        textAlign="center"
      >
        DEPLOYMENT CONFIGURATIONS
      </Heading>

      <VStack spacing={6} align="stretch">
        {suggestions.map((suggestion, index) => (
          <TeamSuggestionCard
            key={index}
            suggestion={suggestion}
            index={index}
            isRecommended={index === 0}
            onExport={onExport}
          />
        ))}
      </VStack>
    </Box>
  );
};

interface TeamSuggestionCardProps {
  suggestion: TeamSuggestionWithImpact;
  index: number;
  isRecommended: boolean;
  onExport: (
    suggestion: TeamSuggestionWithImpact,
    format: 'text' | 'download'
  ) => Promise<void>;
}

const TeamSuggestionCard: React.FC<TeamSuggestionCardProps> = ({
  suggestion,
  index,
  isRecommended,
  onExport,
}) => {
  const labels = ['OPTIMAL BALANCE', 'TACTICAL SYNERGY', 'ALTERNATIVE CONFIG'];
  const label = labels[index] || `CONFIG ${index + 1}`;

  const team1WinProb = (suggestion.win_probability_team_1 * 100).toFixed(1);
  const team2WinProb = (suggestion.win_probability_team_2 * 100).toFixed(1);

  // Prepare VSScreen data
  const vsScreenData = {
    team1: {
      players: suggestion.team_1.players.map(p => ({
        name: p.name,
        mmr: p.mmr,
        race: p.favorite_race || 'Random',
      })),
      totalMMR: suggestion.team_1.avg_mmr * suggestion.team_1.players.length,
      winProbability: suggestion.win_probability_team_1 * 100,
    },
    team2: {
      players: suggestion.team_2.players.map(p => ({
        name: p.name,
        mmr: p.mmr,
        race: p.favorite_race || 'Random',
      })),
      totalMMR: suggestion.team_2.avg_mmr * suggestion.team_2.players.length,
      winProbability: suggestion.win_probability_team_2 * 100,
    },
    matchInfo: {
      mapName: `${suggestion.team_1.players.length}v${suggestion.team_2.players.length} Match`,
      gameMode: 'Balanced Teams',
    },
  };

  return (
    <TacticalCard
      variant={isRecommended ? 'command' : index % 2 === 0 ? 'angled' : 'default'}
      glowColor={
        isRecommended
          ? 'rgba(0, 255, 136, 0.6)'
          : 'rgba(0, 212, 255, 0.4)'
      }
    >
      <Box p={6} position="relative">
        {isRecommended && (
          <Badge
            position="absolute"
            top={4}
            right={4}
            bg="shield.500"
            color="gray.900"
            fontSize="md"
            px={4}
            py={2}
            fontFamily="heading"
            textTransform="uppercase"
            boxShadow="0 0 20px rgba(0, 255, 136, 0.5)"
          >
            RECOMMENDED
          </Badge>
        )}

        <VStack align="stretch" spacing={6}>
          {/* Header */}
          <Box>
            <Heading
              size="lg"
              fontFamily="heading"
              textTransform="uppercase"
              letterSpacing="wider"
              color="brand.300"
              mb={4}
            >
              {label}
            </Heading>

            {/* Win Probability Display */}
            <HStack justify="space-between" mb={4}>
              <VStack spacing={1} align="start">
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  TEAM 1 WIN PROB
                </Text>
                <Text
                  fontSize="4xl"
                  fontWeight="black"
                  fontFamily="heading"
                  color="brand.400"
                  textShadow="0 0 20px rgba(0, 212, 255, 0.5)"
                >
                  {team1WinProb}%
                </Text>
              </VStack>

              <Box textAlign="center">
                <Icon as={FiTarget} boxSize={12} color="accent.500" />
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  VS
                </Text>
              </Box>

              <VStack spacing={1} align="end">
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  TEAM 2 WIN PROB
                </Text>
                <Text
                  fontSize="4xl"
                  fontWeight="black"
                  fontFamily="heading"
                  color="accent.400"
                  textShadow="0 0 20px rgba(255, 179, 0, 0.5)"
                >
                  {team2WinProb}%
                </Text>
              </VStack>
            </HStack>

            {/* Balance Indicator */}
            <Box>
              <Progress
                value={suggestion.win_probability_team_1 * 100}
                size="lg"
                colorScheme={
                  Math.abs(suggestion.win_probability_team_1 - 0.5) < 0.05
                    ? 'green'
                    : Math.abs(suggestion.win_probability_team_1 - 0.5) < 0.1
                    ? 'blue'
                    : 'yellow'
                }
                borderRadius="md"
                bg="whiteAlpha.100"
                sx={{
                  '& > div': {
                    transition: 'all 0.3s',
                  },
                }}
              />
              <HStack justify="space-between" mt={3}>
                <Badge
                  colorScheme={getFairnessColor(suggestion.fairness_rating)}
                  fontSize="md"
                  px={3}
                  py={1}
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  {suggestion.fairness_rating}
                </Badge>
                <Text
                  fontSize="sm"
                  color="gray.400"
                  fontFamily="heading"
                  textTransform="uppercase"
                >
                  MMR DIFF: {formatMMR(suggestion.mmr_difference)}
                </Text>
              </HStack>
            </Box>
          </Box>

          <Divider borderColor="whiteAlpha.200" />

          {/* VSScreen - Visual Team Showdown */}
          <VSScreen
            team1={vsScreenData.team1}
            team2={vsScreenData.team2}
            matchInfo={vsScreenData.matchInfo}
          />

          <Divider borderColor="whiteAlpha.200" />

          {/* Detailed Teams Display */}
          <HStack spacing={6} align="start">
            {/* Team 1 */}
            <VStack flex={1} align="stretch" spacing={4}>
              <Box
                bg="brand.500"
                px={4}
                py={2}
                clipPath="polygon(0 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%)"
              >
                <Heading
                  size="md"
                  fontFamily="heading"
                  textTransform="uppercase"
                  color="gray.900"
                  letterSpacing="wider"
                >
                  TEAM 1
                </Heading>
              </Box>
              <VStack spacing={2} align="stretch">
                {suggestion.team_1.players.map((player) => (
                  <PlayerCard key={player.id} player={player} size="sm" />
                ))}
              </VStack>
              <VStack spacing={2} align="stretch">
                <Box
                  bg="whiteAlpha.50"
                  p={3}
                  borderRadius="md"
                  border="1px solid"
                  borderColor="brand.400"
                  textAlign="center"
                >
                  <Text
                    fontSize="xs"
                    color="gray.500"
                    fontFamily="heading"
                    textTransform="uppercase"
                    mb={1}
                  >
                    Average MMR
                  </Text>
                  <Text
                    fontSize="2xl"
                    fontWeight="black"
                    fontFamily="heading"
                    color="brand.400"
                  >
                    {formatMMR(suggestion.team_1.avg_mmr)}
                  </Text>
                </Box>
                {suggestion.team_1_avg_impact &&
                  suggestion.team_1_avg_impact > 0 && (
                    <Box
                      bg="whiteAlpha.50"
                      p={2}
                      borderRadius="md"
                      border="1px solid"
                      borderColor="purple.400"
                      textAlign="center"
                    >
                      <Text
                        fontSize="xs"
                        color="gray.500"
                        fontFamily="heading"
                        textTransform="uppercase"
                        mb={1}
                      >
                        Avg Impact
                      </Text>
                      <HStack justify="center" spacing={1}>
                        <Icon
                          as={FiActivity}
                          color="purple.400"
                          boxSize={4}
                        />
                        <Text
                          fontSize="lg"
                          fontWeight="bold"
                          fontFamily="heading"
                          color="purple.400"
                        >
                          {suggestion.team_1_avg_impact.toFixed(1)}
                        </Text>
                      </HStack>
                    </Box>
                  )}
              </VStack>
            </VStack>

            {/* Team 2 */}
            <VStack flex={1} align="stretch" spacing={4}>
              <Box
                bg="accent.500"
                px={4}
                py={2}
                clipPath="polygon(8px 0, 100% 0, 100% 100%, 0 100%, 0 8px)"
              >
                <Heading
                  size="md"
                  fontFamily="heading"
                  textTransform="uppercase"
                  color="gray.900"
                  letterSpacing="wider"
                >
                  TEAM 2
                </Heading>
              </Box>
              <VStack spacing={2} align="stretch">
                {suggestion.team_2.players.map((player) => (
                  <PlayerCard key={player.id} player={player} size="sm" />
                ))}
              </VStack>
              <VStack spacing={2} align="stretch">
                <Box
                  bg="whiteAlpha.50"
                  p={3}
                  borderRadius="md"
                  border="1px solid"
                  borderColor="accent.400"
                  textAlign="center"
                >
                  <Text
                    fontSize="xs"
                    color="gray.500"
                    fontFamily="heading"
                    textTransform="uppercase"
                    mb={1}
                  >
                    Average MMR
                  </Text>
                  <Text
                    fontSize="2xl"
                    fontWeight="black"
                    fontFamily="heading"
                    color="accent.400"
                  >
                    {formatMMR(suggestion.team_2.avg_mmr)}
                  </Text>
                </Box>
                {suggestion.team_2_avg_impact &&
                  suggestion.team_2_avg_impact > 0 && (
                    <Box
                      bg="whiteAlpha.50"
                      p={2}
                      borderRadius="md"
                      border="1px solid"
                      borderColor="purple.400"
                      textAlign="center"
                    >
                      <Text
                        fontSize="xs"
                        color="gray.500"
                        fontFamily="heading"
                        textTransform="uppercase"
                        mb={1}
                      >
                        Avg Impact
                      </Text>
                      <HStack justify="center" spacing={1}>
                        <Icon
                          as={FiActivity}
                          color="purple.400"
                          boxSize={4}
                        />
                        <Text
                          fontSize="lg"
                          fontWeight="bold"
                          fontFamily="heading"
                          color="purple.400"
                        >
                          {suggestion.team_2_avg_impact.toFixed(1)}
                        </Text>
                      </HStack>
                    </Box>
                  )}
              </VStack>
            </VStack>
          </HStack>

          {/* Impact Balance Score */}
          {suggestion.impact_balance_score !== undefined &&
            suggestion.impact_balance_score < 1 && (
              <Box mt={4}>
                <VStack spacing={2} align="stretch">
                  <HStack justify="space-between">
                    <Text
                      fontSize="sm"
                      color="gray.400"
                      fontFamily="heading"
                      textTransform="uppercase"
                    >
                      Impact Distribution
                    </Text>
                    <Badge
                      colorScheme={
                        suggestion.impact_balance_score >= 0.95
                          ? 'green'
                          : suggestion.impact_balance_score >= 0.85
                          ? 'blue'
                          : suggestion.impact_balance_score >= 0.75
                          ? 'yellow'
                          : 'orange'
                      }
                      fontSize="md"
                      px={3}
                      py={1}
                      fontFamily="heading"
                    >
                      {(suggestion.impact_balance_score * 100).toFixed(0)}%
                      BALANCED
                    </Badge>
                  </HStack>
                  <Progress
                    value={suggestion.impact_balance_score * 100}
                    size="md"
                    colorScheme={
                      suggestion.impact_balance_score >= 0.95
                        ? 'green'
                        : suggestion.impact_balance_score >= 0.85
                        ? 'blue'
                        : suggestion.impact_balance_score >= 0.75
                        ? 'yellow'
                        : 'orange'
                    }
                    borderRadius="md"
                    bg="whiteAlpha.100"
                  />
                  <Text fontSize="xs" color="gray.500" fontFamily="heading">
                    Impact Difference:{' '}
                    {suggestion.impact_difference?.toFixed(1) || 'N/A'} |
                    Each team has{' '}
                    {suggestion.impact_balance_score >= 0.95
                      ? 'an excellent'
                      : suggestion.impact_balance_score >= 0.85
                      ? 'a good'
                      : 'an uneven'}{' '}
                    mix of high and low impact players
                  </Text>
                </VStack>
              </Box>
            )}

          {/* Export Actions */}
          <HStack justify="center" pt={4}>
            <Menu>
              <MenuButton
                as={Button}
                rightIcon={<FiChevronDown />}
                leftIcon={<FiShare2 />}
                variant="outline"
                size="md"
                fontFamily="heading"
                textTransform="uppercase"
                borderColor="brand.400"
                _hover={{
                  bg: 'whiteAlpha.100',
                  borderColor: 'brand.300',
                }}
              >
                Share Config
              </MenuButton>
              <MenuList bg="gray.800" borderColor="brand.500">
                <MenuItem
                  icon={<FiCopy />}
                  onClick={() => onExport(suggestion, 'text')}
                  fontFamily="heading"
                  textTransform="uppercase"
                  fontSize="sm"
                  _hover={{ bg: 'whiteAlpha.100' }}
                >
                  Copy as Text
                </MenuItem>
                <MenuItem
                  icon={<FiDownload />}
                  onClick={() => onExport(suggestion, 'download')}
                  fontFamily="heading"
                  textTransform="uppercase"
                  fontSize="sm"
                  _hover={{ bg: 'whiteAlpha.100' }}
                >
                  Download File
                </MenuItem>
              </MenuList>
            </Menu>
          </HStack>
        </VStack>
      </Box>
    </TacticalCard>
  );
};

export default BalanceResults;
