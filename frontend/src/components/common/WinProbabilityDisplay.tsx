/**
 * WinProbabilityDisplay Component
 * Displays win probability comparison between two teams with visual indicators
 */
import React, { useMemo } from 'react';
import {
  Box,
  HStack,
  VStack,
  Text,
  Badge,
  Progress,
  Icon,
} from '@chakra-ui/react';
import { FiTarget } from 'react-icons/fi';

export interface WinProbabilityDisplayProps {
  /** Team 1 win probability (0-1 range) */
  team1Probability: number;
  /** Team 2 win probability (0-1 range) */
  team2Probability: number;
  /** Label for team 1 (default: "Team 1") */
  team1Label?: string;
  /** Label for team 2 (default: "Team 2") */
  team2Label?: string;
  /** Display size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show probability as percentage (default: true) */
  showPercentage?: boolean;
  /** Show fairness rating badge (default: true) */
  showFairnessRating?: boolean;
  /** Custom fairness rating text (optional) */
  fairnessRating?: string;
  /** Show balance bar below probabilities (default: true) */
  showBalanceBar?: boolean;
  /** Show VS separator (default: true) */
  showVsSeparator?: boolean;
}

/**
 * Get balance color based on probability difference
 * Excellent: < 5% difference
 * Good: < 10% difference
 * Fair: < 15% difference
 * Poor: 15%+ difference
 */
const getBalanceColor = (prob1: number): 'green' | 'blue' | 'yellow' | 'orange' => {
  const diff = Math.abs(prob1 - 0.5);
  if (diff < 0.05) return 'green';
  if (diff < 0.1) return 'blue';
  if (diff < 0.15) return 'yellow';
  return 'orange';
};

/**
 * Get fairness rating text based on probability difference
 */
const getFairnessRating = (prob1: number): string => {
  const diff = Math.abs(prob1 - 0.5);
  if (diff < 0.05) return 'Excellent';
  if (diff < 0.1) return 'Good';
  if (diff < 0.15) return 'Fair';
  if (diff < 0.25) return 'Poor';
  return 'Very Poor';
};

/**
 * Size configuration for responsive design
 */
const sizeConfig = {
  sm: {
    labelFontSize: 'xs',
    labelTextTransform: 'uppercase',
    probabilityFontSize: '2xl',
    headingSize: 'sm',
    badgeFontSize: 'xs',
    progressSize: 'sm',
    spacing: 2,
  },
  md: {
    labelFontSize: 'xs',
    labelTextTransform: 'uppercase',
    probabilityFontSize: '4xl',
    headingSize: 'md',
    badgeFontSize: 'md',
    progressSize: 'lg',
    spacing: 4,
  },
  lg: {
    labelFontSize: 'sm',
    labelTextTransform: 'uppercase',
    probabilityFontSize: '5xl',
    headingSize: 'lg',
    badgeFontSize: 'lg',
    progressSize: 'xl',
    spacing: 6,
  },
};

const WinProbabilityDisplay: React.FC<WinProbabilityDisplayProps> = ({
  team1Probability,
  team2Probability,
  team1Label = 'Team 1',
  team2Label = 'Team 2',
  size = 'md',
  showPercentage = true,
  showFairnessRating = true,
  fairnessRating: customFairnessRating,
  showBalanceBar = true,
  showVsSeparator = true,
}) => {
  const config = sizeConfig[size];

  // Calculate percentages
  const team1Percent = team1Probability * 100;
  const team2Percent = team2Probability * 100;

  // Calculate fairness rating
  const fairnessRating = useMemo(
    () => customFairnessRating || getFairnessRating(team1Probability),
    [team1Probability, customFairnessRating]
  );

  // Calculate balance color
  const balanceColor = useMemo(
    () => getBalanceColor(team1Probability),
    [team1Probability]
  );

  return (
    <VStack align="stretch" spacing={config.spacing}>
      {/* Probability Display */}
      <HStack justify="space-between" align="flex-start">
        {/* Team 1 */}
        <VStack spacing={1} align="start" flex={1}>
          <Text
            fontSize={config.labelFontSize}
            color="gray.500"
            fontFamily="heading"
            textTransform={config.labelTextTransform as any}
          >
            {team1Label} WIN PROB
          </Text>
          <Text
            fontSize={config.probabilityFontSize}
            fontWeight="black"
            fontFamily="heading"
            color="brand.400"
            textShadow="0 0 20px rgba(0, 212, 255, 0.5)"
          >
            {showPercentage ? `${team1Percent.toFixed(1)}%` : team1Probability.toFixed(2)}
          </Text>
        </VStack>

        {/* VS Separator */}
        {showVsSeparator && (
          <Box textAlign="center" px={2}>
            <Icon as={FiTarget} boxSize={size === 'sm' ? 6 : size === 'md' ? 10 : 12} color="accent.500" />
            <Text
              fontSize={config.labelFontSize}
              color="gray.500"
              fontFamily="heading"
              textTransform="uppercase"
              mt={1}
            >
              VS
            </Text>
          </Box>
        )}

        {/* Team 2 */}
        <VStack spacing={1} align="end" flex={1}>
          <Text
            fontSize={config.labelFontSize}
            color="gray.500"
            fontFamily="heading"
            textTransform={config.labelTextTransform as any}
          >
            {team2Label} WIN PROB
          </Text>
          <Text
            fontSize={config.probabilityFontSize}
            fontWeight="black"
            fontFamily="heading"
            color="accent.400"
            textShadow="0 0 20px rgba(255, 179, 0, 0.5)"
          >
            {showPercentage ? `${team2Percent.toFixed(1)}%` : team2Probability.toFixed(2)}
          </Text>
        </VStack>
      </HStack>

      {/* Balance Bar */}
      {showBalanceBar && (
        <VStack spacing={3} align="stretch">
          <Progress
            value={team1Percent}
            size={config.progressSize}
            colorScheme={balanceColor}
            borderRadius="md"
            bg="whiteAlpha.100"
            sx={{
              '& > div': {
                transition: 'all 0.3s',
              },
            }}
          />

          {/* Fairness Rating Badge */}
          {showFairnessRating && (
            <Badge
              colorScheme={balanceColor}
              fontSize={config.badgeFontSize}
              px={3}
              py={1}
              fontFamily="heading"
              textTransform="uppercase"
              alignSelf="center"
            >
              {fairnessRating}
            </Badge>
          )}
        </VStack>
      )}

      {/* Probability Comparison Bar (Optional - used in MatchHeader style) */}
      {size === 'lg' && (
        <HStack spacing={1} w="full">
          <Box flex={team1Probability}>
            <Progress
              value={100}
              size="xl"
              colorScheme="cyan"
              borderRadius="md"
              bg="gray.700"
              sx={{
                '& > div': {
                  background:
                    'linear-gradient(90deg, rgba(0, 212, 255, 0.6), rgba(0, 212, 255, 1))',
                  boxShadow: '0 0 15px rgba(0, 212, 255, 0.6)',
                },
              }}
            />
          </Box>
          <Box flex={team2Probability}>
            <Progress
              value={100}
              size="xl"
              colorScheme="orange"
              borderRadius="md"
              bg="gray.700"
              sx={{
                '& > div': {
                  background:
                    'linear-gradient(90deg, rgba(255, 179, 0, 1), rgba(255, 179, 0, 0.6))',
                  boxShadow: '0 0 15px rgba(255, 179, 0, 0.6)',
                },
              }}
            />
          </Box>
        </HStack>
      )}
    </VStack>
  );
};

export default WinProbabilityDisplay;
