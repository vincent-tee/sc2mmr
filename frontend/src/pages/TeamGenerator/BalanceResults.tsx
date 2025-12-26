/**
 * BalanceResults Component - Team Balance Suggestions Display
 * Shows balance results and allows export of team configurations
 * Includes celebration animations for well-balanced teams
 */
import { useEffect, useState } from 'react';
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
import { keyframes } from '@emotion/react';
import {
  FiChevronDown,
  FiCopy,
  FiDownload,
  FiShare2,
  FiTarget,
  FiActivity,
  FiCheck,
  FiStar,
} from 'react-icons/fi';
import PlayerCard from '@/components/PlayerCard';
import TacticalCard from '@/components/TacticalCard';
import VSScreen from '@/components/VSScreen';
import { formatMMR, getFairnessColor } from '@/utils/formatting';
import type { TeamSuggestion } from '@/types/api';

// Celebration animation keyframes
const celebrationPulse = keyframes`
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.9; }
  100% { transform: scale(1); opacity: 1; }
`;

const confettiFloat = keyframes`
  0% { transform: translateY(0) rotate(0deg); opacity: 1; }
  100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
`;

const starBurst = keyframes`
  0% { transform: scale(0) rotate(0deg); opacity: 0; }
  50% { transform: scale(1.2) rotate(180deg); opacity: 1; }
  100% { transform: scale(1) rotate(360deg); opacity: 1; }
`;

const slideInBounce = keyframes`
  0% { transform: translateY(20px); opacity: 0; }
  60% { transform: translateY(-5px); opacity: 1; }
  100% { transform: translateY(0); opacity: 1; }
`;

// Celebration banner component
const CelebrationBanner: React.FC<{ fairnessRating: string }> = ({ fairnessRating }) => {
  const [show, setShow] = useState(true);
  
  useEffect(() => {
    const timer = setTimeout(() => setShow(false), 4000);
    return () => clearTimeout(timer);
  }, []);
  
  if (!show) return null;
  
  const isPerfect = fairnessRating === 'Perfect';
  
  return (
    <Box
      position="fixed"
      top="50%"
      left="50%"
      transform="translate(-50%, -50%)"
      zIndex={1000}
      animation={`${celebrationPulse} 0.5s ease-in-out`}
      pointerEvents="none"
    >
      <Box
        bg={isPerfect ? 'green.500' : 'blue.500'}
        color="white"
        px={8}
        py={4}
        borderRadius="xl"
        boxShadow={`0 0 60px ${isPerfect ? 'rgba(72, 187, 120, 0.8)' : 'rgba(66, 153, 225, 0.8)'}`}
        textAlign="center"
      >
        <HStack justify="center" spacing={3} mb={2}>
          <Icon 
            as={isPerfect ? FiStar : FiCheck} 
            boxSize={8} 
            animation={`${starBurst} 0.6s ease-out`}
          />
          <Heading size="lg" fontFamily="heading">
            {isPerfect ? 'Perfect Balance!' : 'Teams Balanced!'}
          </Heading>
          <Icon 
            as={isPerfect ? FiStar : FiCheck} 
            boxSize={8} 
            animation={`${starBurst} 0.6s ease-out 0.1s`}
          />
        </HStack>
        <Text fontSize="md" opacity={0.9}>
          {isPerfect 
            ? 'These teams are perfectly matched!' 
            : 'Great team configuration found!'}
        </Text>
      </Box>
      
      {/* Confetti particles for Perfect balance */}
      {isPerfect && (
        <>
          {[...Array(12)].map((_, i) => (
            <Box
              key={i}
              position="absolute"
              top="100%"
              left={`${10 + i * 7}%`}
              width="10px"
              height="10px"
              borderRadius="full"
              bg={['gold', 'green.400', 'blue.400', 'purple.400', 'orange.400'][i % 5]}
              animation={`${confettiFloat} ${1 + Math.random()}s ease-out forwards`}
              style={{ animationDelay: `${i * 0.1}s` }}
            />
          ))}
        </>
      )}
    </Box>
  );
};

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
  const [showCelebration, setShowCelebration] = useState(false);
  const [celebrationRating, setCelebrationRating] = useState<string>('');
  
  // Trigger celebration when suggestions change and top result is good
  useEffect(() => {
    if (suggestions.length > 0) {
      const topRating = suggestions[0].fairness_rating;
      if (topRating === 'Perfect' || topRating === 'Very Good') {
        setCelebrationRating(topRating);
        setShowCelebration(true);
        // Reset after animation
        const timer = setTimeout(() => setShowCelebration(false), 4500);
        return () => clearTimeout(timer);
      }
    }
  }, [suggestions]);

  if (suggestions.length === 0) {
    return null;
  }

  return (
    <Box>
      {/* Celebration overlay for good balance */}
      {showCelebration && <CelebrationBanner fairnessRating={celebrationRating} />}
      
      <Heading
        size="lg"
        mb={6}
        fontFamily="heading"
        letterSpacing="wider"
        color="brand.400"
        textAlign="center"
        animation={suggestions.length > 0 ? `${slideInBounce} 0.5s ease-out` : undefined}
      >
        Team Configurations
      </Heading>

      <VStack spacing={6} align="stretch">
        {suggestions.map((suggestion, index) => (
          <Box
            key={index}
            animation={`${slideInBounce} 0.5s ease-out`}
            style={{ animationDelay: `${index * 0.15}s`, animationFillMode: 'backwards' }}
          >
            <TeamSuggestionCard
              suggestion={suggestion}
              index={index}
              isRecommended={index === 0}
              onExport={onExport}
            />
          </Box>
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
  const labels = ['Optimal Balance', 'Tactical Synergy', 'Alternative Config'];
  const label = labels[index] || `Config ${index + 1}`;

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
            boxShadow="0 0 20px rgba(0, 255, 136, 0.5)"
          >
            Recommended
          </Badge>
        )}

        <VStack align="stretch" spacing={6}>
          {/* Header */}
          <Box>
            <Heading
              size="lg"
              fontFamily="heading"
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
                >
                  Team 1 Win Prob
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
                >
                  VS
                </Text>
              </Box>

              <VStack spacing={1} align="end">
                <Text
                  fontSize="xs"
                  color="gray.500"
                  fontFamily="heading"
                >
                  Team 2 Win Prob
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
                >
                  {suggestion.fairness_rating}
                </Badge>
                <Text
                  fontSize="sm"
                  color="gray.400"
                  fontFamily="heading"
                >
                  MMR Diff: {formatMMR(suggestion.mmr_difference)}
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
                  color="gray.900"
                  letterSpacing="wider"
                >
                  Team 1
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
                  color="gray.900"
                  letterSpacing="wider"
                >
                  Team 2
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
                      Balanced
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
                  fontSize="sm"
                  _hover={{ bg: 'whiteAlpha.100' }}
                >
                  Copy as Text
                </MenuItem>
                <MenuItem
                  icon={<FiDownload />}
                  onClick={() => onExport(suggestion, 'download')}
                  fontFamily="heading"
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
