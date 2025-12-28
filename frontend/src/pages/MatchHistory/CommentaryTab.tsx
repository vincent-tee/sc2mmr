/**
 * CommentaryTab - Enhanced SHAP display with story-based feature names
 * Transforms technical ML features into engaging esports-style narratives
 */
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Icon,
  Progress,
  Tooltip,
  Grid,
  Heading,
  Divider,
} from '@chakra-ui/react';
import {
  FiTrendingUp,
  FiZap,
  FiDollarSign,
  FiActivity,
  FiCpu,
  FiTarget,
  FiAward,
  FiStar,
} from 'react-icons/fi';
import type { IconType } from 'react-icons';
import type { MatchPlayerSummary } from '../../types/api';

interface CommentaryTabProps {
  players: MatchPlayerSummary[];
  matchId: number;
  mvpPlayerId: number | null;
  shapValues?: Record<string, number>;
}

// Story-based feature name mappings
const FEATURE_STORIES: Record<string, {
  name: string;
  icon: IconType;
  color: string;
  description: string;
  flavorText: string;
}> = {
  mmr_diff: {
    name: 'Skill Gap',
    icon: FiTrendingUp,
    color: 'purple.400',
    description: 'MMR difference between players',
    flavorText: 'Experience vs. underdog energy',
  },
  apm_diff: {
    name: 'Blazing Fingers',
    icon: FiZap,
    color: 'yellow.400',
    description: 'Actions per minute advantage',
    flavorText: 'Speed demons vs. methodical masters',
  },
  damage_dealt_diff: {
    name: 'Sledgehammer',
    icon: FiTarget,
    color: 'red.400',
    description: 'Raw damage output difference',
    flavorText: 'Who brought the bigger guns?',
  },
  economic_score_diff: {
    name: 'Money Power',
    icon: FiDollarSign,
    color: 'green.400',
    description: 'Economic advantage',
    flavorText: 'The war chest advantage',
  },
  combat_score_diff: {
    name: 'Battle Fury',
    icon: FiActivity,
    color: 'orange.400',
    description: 'Combat effectiveness difference',
    flavorText: 'Trading efficiency matters',
  },
  efficiency_score_diff: {
    name: 'Precision Strike',
    icon: FiCpu,
    color: 'cyan.400',
    description: 'Resource efficiency gap',
    flavorText: 'Waste not, want not',
  },
  team_fight_participation_diff: {
    name: 'Team Spirit',
    icon: FiStar,
    color: 'pink.400',
    description: 'Team fight engagement difference',
    flavorText: 'United we stand',
  },
  damage_ratio_diff: {
    name: 'Trade Master',
    icon: FiTrendingUp,
    color: 'teal.400',
    description: 'Damage trading efficiency',
    flavorText: 'Getting more than you give',
  },
};

// Achievement badges based on player performance
const getAchievementBadges = (player: MatchPlayerSummary): { icon: string; label: string; color: string }[] => {
  const badges: { icon: string; label: string; color: string }[] = [];

  if (player.damage_dealt && player.damage_dealt > 50000) {
    badges.push({ icon: 'Damage Dealer', label: 'Damage Dealer', color: 'red' });
  }
  if (player.damage_ratio && player.damage_ratio > 2) {
    badges.push({ icon: 'Trade God', label: 'Trade God', color: 'green' });
  }
  if (player.damage_ratio && player.damage_ratio === 0) {
    badges.push({ icon: 'Perfect Game', label: 'Perfect Game', color: 'gold' });
  }
  if (player.impact_score && player.impact_score > 80) {
    badges.push({ icon: 'Elite', label: 'Elite Performer', color: 'purple' });
  }
  if (player.units_killed && player.units_killed > 100) {
    badges.push({ icon: 'Army Slayer', label: 'Army Slayer', color: 'orange' });
  }

  return badges;
};

// Generate narrative performance text
const getPerformanceNarrative = (player: MatchPlayerSummary): string => {
  const parts: string[] = [];

  if (player.damage_dealt) {
    if (player.damage_dealt > 100000) {
      parts.push(`unleashed an absolute BARRAGE of ${player.damage_dealt.toLocaleString()} damage`);
    } else if (player.damage_dealt > 50000) {
      parts.push(`dealt a solid ${player.damage_dealt.toLocaleString()} damage`);
    } else {
      parts.push(`contributed ${player.damage_dealt.toLocaleString()} damage`);
    }
  }

  if (player.damage_ratio) {
    if (player.damage_ratio >= 100 || player.damage_ratio === 0) {
      parts.push('achieving PERFECTION with zero deaths');
    } else if (player.damage_ratio > 3) {
      parts.push(`trading at an INSANE ${player.damage_ratio.toFixed(1)}:1 ratio`);
    } else if (player.damage_ratio > 1.5) {
      parts.push(`with efficient ${player.damage_ratio.toFixed(1)}:1 trades`);
    }
  }

  if (player.impact_score) {
    if (player.impact_score > 80) {
      parts.push('delivering MVP-caliber impact');
    } else if (player.impact_score > 60) {
      parts.push('making solid contributions');
    }
  }

  if (parts.length === 0) {
    return `${player.player_name} participated in the battle.`;
  }

  return `${player.player_name} ${parts.join(', ')}.`;
};

const FeatureCard: React.FC<{
  featureKey: string;
  value: number;
  maxValue: number;
}> = ({ featureKey, value, maxValue }) => {
  const feature = FEATURE_STORIES[featureKey] || {
    name: featureKey.replace(/_/g, ' ').replace(/diff$/, ''),
    icon: FiActivity,
    color: 'gray.400',
    description: 'Match factor',
    flavorText: '',
  };

  const absValue = Math.abs(value);
  const normalizedValue = Math.min((absValue / maxValue) * 100, 100);
  const isPositive = value >= 0;

  return (
    <Box
      p={4}
      bg="rgba(30, 41, 59, 0.5)"
      borderRadius="lg"
      border="2px solid"
      borderColor={isPositive ? 'green.500' : 'red.500'}
      opacity={0.9 + (normalizedValue / 500)}
    >
      <HStack justify="space-between" mb={2}>
        <HStack>
          <Icon as={feature.icon} color={feature.color} boxSize={5} />
          <Text fontWeight="bold" fontFamily="heading">
            {feature.name}
          </Text>
        </HStack>
        <Badge colorScheme={isPositive ? 'green' : 'red'}>
          {isPositive ? '+' : ''}{value.toFixed(2)}
        </Badge>
      </HStack>

      <Progress
        value={normalizedValue}
        size="sm"
        colorScheme={isPositive ? 'green' : 'red'}
        bg="whiteAlpha.200"
        borderRadius="full"
        mb={2}
      />

      <Text fontSize="xs" color="gray.400">
        {feature.description}
      </Text>
      <Text fontSize="xs" color="gray.500" fontStyle="italic">
        {feature.flavorText}
      </Text>
    </Box>
  );
};

const PlayerNarrativeCard: React.FC<{
  player: MatchPlayerSummary;
  isMVP: boolean;
}> = ({ player, isMVP }) => {
  const badges = getAchievementBadges(player);
  const narrative = getPerformanceNarrative(player);

  return (
    <Box
      p={4}
      bg={player.won ? 'rgba(72, 187, 120, 0.1)' : 'rgba(245, 101, 101, 0.1)'}
      borderRadius="lg"
      border="2px solid"
      borderColor={player.won ? 'green.400' : 'red.400'}
      position="relative"
    >
      {isMVP && (
        <Badge
          position="absolute"
          top={-2}
          right={2}
          colorScheme="yellow"
          fontSize="sm"
          px={3}
        >
          <Icon as={FiAward} mr={1} />
          MVP
        </Badge>
      )}

      <HStack mb={3}>
        <Text fontWeight="bold" fontSize="lg" fontFamily="heading">
          {player.player_name}
        </Text>
        <Badge colorScheme={player.won ? 'green' : 'red'}>
          {player.won ? 'W' : 'L'}
        </Badge>
      </HStack>

      {/* Achievement Badges */}
      {badges.length > 0 && (
        <HStack spacing={2} mb={3} flexWrap="wrap">
          {badges.map((badge, idx) => (
            <Tooltip key={idx} label={badge.label}>
              <Badge colorScheme={badge.color} fontSize="xs">
                {badge.icon}
              </Badge>
            </Tooltip>
          ))}
        </HStack>
      )}

      {/* Narrative Text */}
      <Text fontSize="sm" color="gray.300" fontStyle="italic">
        {narrative}
      </Text>
    </Box>
  );
};

export const CommentaryTab: React.FC<CommentaryTabProps> = ({
  players,
  matchId: _matchId,
  mvpPlayerId,
  shapValues,
}) => {
  // Sort SHAP values by absolute impact
  const sortedShapValues = shapValues
    ? Object.entries(shapValues)
        .filter(([key]) => key.endsWith('_diff') || key in FEATURE_STORIES)
        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
        .slice(0, 6) // Top 6 factors
    : [];

  const maxShapValue = sortedShapValues.length > 0
    ? Math.max(...sortedShapValues.map(([, v]) => Math.abs(v)))
    : 1;

  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);

  return (
    <VStack spacing={6} align="stretch">
      {/* Key Factors Section */}
      {sortedShapValues.length > 0 && (
        <Box>
          <Heading size="md" fontFamily="heading" color="brand.400" mb={4}>
            <Icon as={FiActivity} mr={2} />
            Key Victory Factors
          </Heading>
          <Text fontSize="sm" color="gray.400" mb={4}>
            These factors most influenced the match outcome according to our ML model.
          </Text>
          <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }} gap={4}>
            {sortedShapValues.map(([key, value]) => (
              <FeatureCard
                key={key}
                featureKey={key}
                value={value}
                maxValue={maxShapValue}
              />
            ))}
          </Grid>
        </Box>
      )}

      <Divider borderColor="whiteAlpha.200" />

      {/* Moments of Glory - Player Narratives */}
      <Box>
        <Heading size="md" fontFamily="heading" color="brand.400" mb={4}>
          <Icon as={FiStar} mr={2} />
          Moments of Glory
        </Heading>
        <Text fontSize="sm" color="gray.400" mb={4}>
          Individual player performances and achievements from this match.
        </Text>

        <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
          {/* Team 1 Narratives */}
          <Box>
            <Text fontFamily="heading" fontSize="sm" color="cyan.400" mb={3}>
              Team 1 Performances
            </Text>
            <VStack spacing={3} align="stretch">
              {team1Players.map((player) => (
                <PlayerNarrativeCard
                  key={player.player_id}
                  player={player}
                  isMVP={player.player_id === mvpPlayerId}
                />
              ))}
            </VStack>
          </Box>

          {/* Team 2 Narratives */}
          <Box>
            <Text fontFamily="heading" fontSize="sm" color="orange.400" mb={3}>
              Team 2 Performances
            </Text>
            <VStack spacing={3} align="stretch">
              {team2Players.map((player) => (
                <PlayerNarrativeCard
                  key={player.player_id}
                  player={player}
                  isMVP={player.player_id === mvpPlayerId}
                />
              ))}
            </VStack>
          </Box>
        </Grid>
      </Box>

      {/* No SHAP data message */}
      {sortedShapValues.length === 0 && (
        <Box
          p={6}
          bg="rgba(30, 41, 59, 0.3)"
          borderRadius="lg"
          textAlign="center"
        >
          <Icon as={FiActivity} boxSize={8} color="gray.500" mb={2} />
          <Text color="gray.400">
            Advanced ML analysis not available for this match.
          </Text>
          <Text fontSize="sm" color="gray.500">
            Re-upload the replay to generate detailed factor analysis.
          </Text>
        </Box>
      )}
    </VStack>
  );
};

export default CommentaryTab;
