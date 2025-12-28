/**
 * AnalyticsTab - Match Story architecture with dramatic narratives
 * Features: Match headlines, Narrative Arc, Performance Identity, What If scenarios
 */
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Icon,
  Grid,
  Heading,
  Progress,
  Divider,
} from '@chakra-ui/react';
import {
  FiClock,
  FiActivity,
  FiStar,
  FiAward,
  FiEye,
  FiAlertTriangle,
} from 'react-icons/fi';
import type { MatchPlayerSummary, MatchWithPlayers } from '../../types/api';

interface AnalyticsTabProps {
  match: MatchWithPlayers;
  players: MatchPlayerSummary[];
}

// Generate dramatic match headline
const generateMatchHeadline = (match: MatchWithPlayers): { headline: string; subtitle: string } => {
  const duration = match.duration_seconds;
  const hasUpset = match.predicted_team1_win_prob && match.predicted_team2_win_prob &&
    ((match.winner_team === 1 && match.predicted_team1_win_prob < 0.4) ||
     (match.winner_team === 2 && match.predicted_team2_win_prob < 0.4));

  if (hasUpset) {
    return {
      headline: 'AGAINST ALL ODDS',
      subtitle: `The underdogs defy the ${((match.winner_team === 1 ? match.predicted_team2_win_prob : match.predicted_team1_win_prob) || 0.5) * 100}% prediction!`,
    };
  }

  if (duration < 300) {
    return {
      headline: 'SWIFT DOMINATION',
      subtitle: `A decisive ${Math.floor(duration / 60)}:${(duration % 60).toString().padStart(2, '0')} victory`,
    };
  }

  if (duration > 1200) {
    return {
      headline: 'EPIC WAR OF ATTRITION',
      subtitle: `${Math.floor(duration / 60)} minutes of non-stop action`,
    };
  }

  if (match.total_damage && match.total_damage > 200000) {
    return {
      headline: 'ABSOLUTE CARNAGE',
      subtitle: `${match.total_damage.toLocaleString()} total damage dealt`,
    };
  }

  return {
    headline: 'BATTLE FOR SUPREMACY',
    subtitle: `Team ${match.winner_team} claims victory on ${match.map_name}`,
  };
};

// Generate narrative arc phases
const generateNarrativeArc = (match: MatchWithPlayers, _players: MatchPlayerSummary[]) => {
  const duration = match.duration_seconds;

  // Opening Fire (0-5 min)
  const earlyPhase = {
    title: 'Opening Fire',
    timeRange: '0:00 - 5:00',
    description: duration < 300
      ? 'The game ended before the mid-game even began!'
      : 'Both sides established their economies and scouted.',
    intensity: Math.min(30 + (Math.random() * 20), 50),
  };

  // Mid-Game Clash (5-10 min)
  const midPhase = {
    title: 'Mid-Game Clash',
    timeRange: '5:00 - 10:00',
    description: duration < 300
      ? 'N/A - Game ended early'
      : duration < 600
        ? 'Decisive engagements shaped the outcome.'
        : 'Intense battles erupted across the map.',
    intensity: duration < 300 ? 0 : Math.min(50 + (Math.random() * 30), 80),
  };

  // Breaking Point (10+ min)
  const latePhase = {
    title: 'Breaking Point',
    timeRange: '10:00+',
    description: duration < 600
      ? 'N/A - Game ended mid-game'
      : 'The final push that decided everything.',
    intensity: duration < 600 ? 0 : Math.min(70 + (Math.random() * 30), 100),
  };

  return [earlyPhase, midPhase, latePhase];
};

// Performance Identity titles
const getPerformanceIdentity = (player: MatchPlayerSummary): { title: string; subtitle: string; color: string } => {
  if (player.damage_ratio && player.damage_ratio >= 100) {
    return { title: 'The Untouchable', subtitle: 'Perfect preservation', color: 'yellow' };
  }
  if (player.damage_dealt && player.damage_dealt > 100000) {
    return { title: 'The Destroyer', subtitle: 'Maximum carnage', color: 'red' };
  }
  if (player.damage_ratio && player.damage_ratio > 3) {
    return { title: 'The Trader', subtitle: 'Efficiency master', color: 'green' };
  }
  if (player.impact_score && player.impact_score > 80) {
    return { title: 'The Carry', subtitle: 'Team backbone', color: 'purple' };
  }
  if (player.impact_score && player.impact_score > 60) {
    return { title: 'The Contributor', subtitle: 'Solid performance', color: 'blue' };
  }
  return { title: 'The Fighter', subtitle: 'Stayed in the battle', color: 'gray' };
};

// Generate "What If" scenarios
const generateWhatIfScenarios = (match: MatchWithPlayers, players: MatchPlayerSummary[]): string[] => {
  const scenarios: string[] = [];

  // Find MVP and lowest performer
  const sortedByImpact = [...players].sort((a, b) => (b.impact_score || 0) - (a.impact_score || 0));
  const mvp = sortedByImpact[0];
  const lowestPerformer = sortedByImpact[sortedByImpact.length - 1];

  if (mvp && mvp.impact_score && mvp.impact_score > 70) {
    scenarios.push(`What if ${mvp.player_name} had an average game? Team ${mvp.team_number === 1 ? 2 : 1} might have won.`);
  }

  if (lowestPerformer && lowestPerformer.impact_score && lowestPerformer.impact_score < 40) {
    scenarios.push(`What if ${lowestPerformer.player_name} had matched their team's average? The result could be different.`);
  }

  if (match.predicted_team1_win_prob && match.predicted_team2_win_prob) {
    const favoredTeam = match.predicted_team1_win_prob > match.predicted_team2_win_prob ? 1 : 2;
    if (match.winner_team !== favoredTeam) {
      scenarios.push(`The favored team lost - what if they had executed their strategy better?`);
    }
  }

  if (match.duration_seconds < 360) {
    scenarios.push(`What if the losing team had survived the early aggression? A longer game might have favored their style.`);
  }

  return scenarios.slice(0, 3);
};

// Match DNA fingerprint component
const MatchDNA: React.FC<{ match: MatchWithPlayers; players: MatchPlayerSummary[] }> = ({ match, players }) => {
  const totalDamage = match.total_damage || 0;
  const duration = match.duration_seconds;
  const playerCount = players.length;

  // Calculate DNA "genes"
  const aggression = Math.min(100, (totalDamage / duration) / 50 * 100);
  const balance = 100 - Math.abs(50 - ((match.predicted_team1_win_prob || 0.5) * 100)) * 2;
  const intensity = Math.min(100, (totalDamage / 100000) * 100);
  const efficiency = players.reduce((sum, p) => sum + (p.damage_ratio || 1), 0) / playerCount * 20;

  const genes = [
    { name: 'Aggression', value: aggression, color: 'red' },
    { name: 'Balance', value: balance, color: 'blue' },
    { name: 'Intensity', value: intensity, color: 'orange' },
    { name: 'Efficiency', value: Math.min(100, efficiency), color: 'green' },
  ];

  return (
    <Box p={4} bg="rgba(30, 41, 59, 0.5)" borderRadius="lg">
      <Heading size="sm" fontFamily="heading" color="brand.400" mb={4}>
        <Icon as={FiActivity} mr={2} />
        Match DNA Fingerprint
      </Heading>
      <VStack spacing={3} align="stretch">
        {genes.map((gene) => (
          <Box key={gene.name}>
            <HStack justify="space-between" mb={1}>
              <Text fontSize="sm" fontFamily="heading">{gene.name}</Text>
              <Badge colorScheme={gene.color}>{gene.value.toFixed(0)}%</Badge>
            </HStack>
            <Progress
              value={gene.value}
              size="sm"
              colorScheme={gene.color}
              bg="whiteAlpha.200"
              borderRadius="full"
            />
          </Box>
        ))}
      </VStack>
    </Box>
  );
};

export const AnalyticsTab: React.FC<AnalyticsTabProps> = ({ match, players }) => {
  const headline = generateMatchHeadline(match);
  const narrativeArc = generateNarrativeArc(match, players);
  const whatIfScenarios = generateWhatIfScenarios(match, players);

  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);

  return (
    <VStack spacing={6} align="stretch">
      {/* Match Headline */}
      <Box
        p={6}
        bg="linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(255, 179, 0, 0.1))"
        borderRadius="lg"
        border="2px solid"
        borderColor="brand.500"
        textAlign="center"
      >
        <Text fontSize="3xl" fontWeight="black" fontFamily="heading" color="brand.400">
          {headline.headline}
        </Text>
        <Text fontSize="md" color="gray.400" mt={2}>
          {headline.subtitle}
        </Text>
      </Box>

      {/* Narrative Arc */}
      <Box>
        <Heading size="md" fontFamily="heading" color="brand.400" mb={4}>
          <Icon as={FiClock} mr={2} />
          Narrative Arc
        </Heading>
        <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={4}>
          {narrativeArc.map((phase, idx) => (
            <Box
              key={phase.title}
              p={4}
              bg="rgba(30, 41, 59, 0.5)"
              borderRadius="lg"
              border="2px solid"
              borderColor={phase.intensity > 0 ? 'whiteAlpha.300' : 'whiteAlpha.100'}
              opacity={phase.intensity > 0 ? 1 : 0.5}
            >
              <HStack mb={2}>
                <Badge colorScheme={idx === 0 ? 'blue' : idx === 1 ? 'orange' : 'red'}>
                  {phase.timeRange}
                </Badge>
              </HStack>
              <Text fontWeight="bold" fontFamily="heading" mb={2}>
                {phase.title}
              </Text>
              {phase.intensity > 0 && (
                <Progress
                  value={phase.intensity}
                  size="sm"
                  colorScheme={phase.intensity > 70 ? 'red' : phase.intensity > 40 ? 'orange' : 'blue'}
                  bg="whiteAlpha.200"
                  borderRadius="full"
                  mb={2}
                />
              )}
              <Text fontSize="sm" color="gray.400">
                {phase.description}
              </Text>
            </Box>
          ))}
        </Grid>
      </Box>

      <Divider borderColor="whiteAlpha.200" />

      {/* Performance Identity Cards */}
      <Box>
        <Heading size="md" fontFamily="heading" color="brand.400" mb={4}>
          <Icon as={FiStar} mr={2} />
          Performance Identities
        </Heading>
        <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
          {/* Team 1 */}
          <Box>
            <Text fontFamily="heading" fontSize="sm" color="cyan.400" mb={3}>
              Team 1
            </Text>
            <VStack spacing={3} align="stretch">
              {team1Players.map((player) => {
                const identity = getPerformanceIdentity(player);
                return (
                  <HStack
                    key={player.player_id}
                    p={3}
                    bg={player.won ? 'rgba(72, 187, 120, 0.1)' : 'rgba(245, 101, 101, 0.1)'}
                    borderRadius="md"
                    border="1px solid"
                    borderColor="whiteAlpha.200"
                  >
                    <Box flex={1}>
                      <Text fontWeight="bold" fontFamily="heading">
                        {player.player_name}
                      </Text>
                      <HStack spacing={2}>
                        <Badge colorScheme={identity.color}>{identity.title}</Badge>
                        <Text fontSize="xs" color="gray.500">{identity.subtitle}</Text>
                      </HStack>
                    </Box>
                    {player.player_id === match.mvp_player_id && (
                      <Icon as={FiAward} color="yellow.400" boxSize={5} />
                    )}
                  </HStack>
                );
              })}
            </VStack>
          </Box>

          {/* Team 2 */}
          <Box>
            <Text fontFamily="heading" fontSize="sm" color="orange.400" mb={3}>
              Team 2
            </Text>
            <VStack spacing={3} align="stretch">
              {team2Players.map((player) => {
                const identity = getPerformanceIdentity(player);
                return (
                  <HStack
                    key={player.player_id}
                    p={3}
                    bg={player.won ? 'rgba(72, 187, 120, 0.1)' : 'rgba(245, 101, 101, 0.1)'}
                    borderRadius="md"
                    border="1px solid"
                    borderColor="whiteAlpha.200"
                  >
                    <Box flex={1}>
                      <Text fontWeight="bold" fontFamily="heading">
                        {player.player_name}
                      </Text>
                      <HStack spacing={2}>
                        <Badge colorScheme={identity.color}>{identity.title}</Badge>
                        <Text fontSize="xs" color="gray.500">{identity.subtitle}</Text>
                      </HStack>
                    </Box>
                    {player.player_id === match.mvp_player_id && (
                      <Icon as={FiAward} color="yellow.400" boxSize={5} />
                    )}
                  </HStack>
                );
              })}
            </VStack>
          </Box>
        </Grid>
      </Box>

      <Divider borderColor="whiteAlpha.200" />

      {/* Match DNA + What If Side by Side */}
      <Grid templateColumns={{ base: '1fr', lg: '1fr 1fr' }} gap={6}>
        {/* Match DNA */}
        <MatchDNA match={match} players={players} />

        {/* What If Scenarios */}
        <Box p={4} bg="rgba(30, 41, 59, 0.5)" borderRadius="lg">
          <Heading size="sm" fontFamily="heading" color="brand.400" mb={4}>
            <Icon as={FiEye} mr={2} />
            What If? Scenarios
          </Heading>
          {whatIfScenarios.length > 0 ? (
            <VStack spacing={3} align="stretch">
              {whatIfScenarios.map((scenario, idx) => (
                <HStack
                  key={idx}
                  p={3}
                  bg="whiteAlpha.50"
                  borderRadius="md"
                  border="1px dashed"
                  borderColor="whiteAlpha.300"
                >
                  <Icon as={FiAlertTriangle} color="yellow.400" />
                  <Text fontSize="sm" color="gray.300">
                    {scenario}
                  </Text>
                </HStack>
              ))}
            </VStack>
          ) : (
            <Text fontSize="sm" color="gray.500">
              No significant alternate scenarios identified.
            </Text>
          )}
        </Box>
      </Grid>
    </VStack>
  );
};

export default AnalyticsTab;
