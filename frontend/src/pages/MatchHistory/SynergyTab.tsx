/**
 * SynergyTab - Team chemistry and duo analysis
 * Features: Power Duo analysis, Team chemistry metrics, Duo titles
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
  Avatar,
  AvatarGroup,
  Tooltip,
} from '@chakra-ui/react';
import {
  FiUsers,
  FiHeart,
  FiZap,
  FiTrendingUp,
  FiStar,
  FiActivity,
} from 'react-icons/fi';
import { getPlayerAvatarUrl, getRaceColor } from '../../utils/formatting';
import type { MatchPlayerSummary, PlayerSynergy } from '../../types/api';

interface SynergyTabProps {
  players: MatchPlayerSummary[];
  matchId: number;
  winnerTeam: number;
  synergies?: PlayerSynergy[];
}

// Duo title generator based on playstyle
const getDuoTitle = (
  player1: MatchPlayerSummary,
  player2: MatchPlayerSummary
): { title: string; subtitle: string; color: string } => {
  const totalDamage = (player1.damage_dealt || 0) + (player2.damage_dealt || 0);
  const avgRatio = ((player1.damage_ratio || 1) + (player2.damage_ratio || 1)) / 2;
  const avgImpact = ((player1.impact_score || 50) + (player2.impact_score || 50)) / 2;

  // Both high damage
  if (totalDamage > 100000) {
    return { title: 'The Demolition Crew', subtitle: 'Pure destruction', color: 'red' };
  }

  // Both high efficiency
  if (avgRatio > 2.5) {
    return { title: 'The Surgeons', subtitle: 'Precision strikes', color: 'green' };
  }

  // High impact duo
  if (avgImpact > 70) {
    return { title: 'The Dream Team', subtitle: 'Elite synergy', color: 'purple' };
  }

  // Mixed styles
  if ((player1.damage_dealt || 0) > 50000 && (player2.damage_ratio || 1) > 2) {
    return { title: 'The Hammer & Scalpel', subtitle: 'Force meets finesse', color: 'orange' };
  }

  if ((player2.damage_dealt || 0) > 50000 && (player1.damage_ratio || 1) > 2) {
    return { title: 'The Scalpel & Hammer', subtitle: 'Finesse meets force', color: 'orange' };
  }

  // Race-based titles
  if (player1.race === player2.race) {
    const raceMap: Record<string, { title: string; subtitle: string }> = {
      Terran: { title: 'The Marine Corps', subtitle: 'Terran brothers' },
      Protoss: { title: 'The Golden Armada', subtitle: 'For Aiur!' },
      Zerg: { title: 'The Swarm Lords', subtitle: 'Endless tide' },
    };
    const raceTitle = raceMap[player1.race];
    if (raceTitle) {
      return { ...raceTitle, color: getRaceColor(player1.race) };
    }
  }

  // Mixed race
  if (player1.race !== player2.race) {
    return { title: 'Fire & Ice', subtitle: 'Opposites unite', color: 'teal' };
  }

  return { title: 'Battle Partners', subtitle: 'Fighting together', color: 'blue' };
};

// Calculate team chemistry score
const calculateTeamChemistry = (players: MatchPlayerSummary[]): number => {
  if (players.length < 2) return 50;

  let score = 50; // Base score

  // Add points for consistent performance
  const impacts = players.map((p) => p.impact_score || 50);
  const avgImpact = impacts.reduce((a, b) => a + b, 0) / impacts.length;
  const variance = impacts.reduce((sum, i) => sum + Math.abs(i - avgImpact), 0) / impacts.length;

  // Low variance = good chemistry
  score += Math.max(0, 25 - variance);

  // Bonus for high average impact
  if (avgImpact > 60) score += 10;
  if (avgImpact > 70) score += 10;

  // Bonus if all players have positive trade ratios
  const allPositiveRatios = players.every((p) => (p.damage_ratio || 1) >= 1);
  if (allPositiveRatios) score += 5;

  return Math.min(100, Math.max(0, score));
};

// Generate all duo combinations
const generateDuoCombinations = (
  players: MatchPlayerSummary[]
): Array<{ player1: MatchPlayerSummary; player2: MatchPlayerSummary }> => {
  const duos: Array<{ player1: MatchPlayerSummary; player2: MatchPlayerSummary }> = [];

  for (let i = 0; i < players.length; i++) {
    for (let j = i + 1; j < players.length; j++) {
      duos.push({ player1: players[i], player2: players[j] });
    }
  }

  return duos;
};

const DuoCard: React.FC<{
  player1: MatchPlayerSummary;
  player2: MatchPlayerSummary;
  synergy?: PlayerSynergy;
}> = ({ player1, player2, synergy }) => {
  const duoTitle = getDuoTitle(player1, player2);
  const combinedDamage = (player1.damage_dealt || 0) + (player2.damage_dealt || 0);
  const avgRatio = ((player1.damage_ratio || 1) + (player2.damage_ratio || 1)) / 2;

  return (
    <Box
      p={4}
      bg="rgba(30, 41, 59, 0.5)"
      borderRadius="lg"
      border="2px solid"
      borderColor="whiteAlpha.200"
      transition="all 0.2s"
      _hover={{
        borderColor: 'brand.500',
        transform: 'translateY(-2px)',
      }}
    >
      {/* Duo Avatars */}
      <HStack justify="center" mb={3}>
        <AvatarGroup size="lg" max={2}>
          <Avatar
            name={player1.player_name}
            src={getPlayerAvatarUrl(player1.player_name, player1.race)}
            bg={`${getRaceColor(player1.race)}.500`}
          />
          <Avatar
            name={player2.player_name}
            src={getPlayerAvatarUrl(player2.player_name, player2.race)}
            bg={`${getRaceColor(player2.race)}.500`}
          />
        </AvatarGroup>
      </HStack>

      {/* Player Names */}
      <HStack justify="center" mb={2}>
        <Text fontWeight="bold" fontFamily="heading" fontSize="sm">
          {player1.player_name}
        </Text>
        <Icon as={FiHeart} color="pink.400" />
        <Text fontWeight="bold" fontFamily="heading" fontSize="sm">
          {player2.player_name}
        </Text>
      </HStack>

      {/* Duo Title */}
      <Box textAlign="center" mb={3}>
        <Badge colorScheme={duoTitle.color} fontSize="sm" px={3}>
          {duoTitle.title}
        </Badge>
        <Text fontSize="xs" color="gray.500" mt={1}>
          {duoTitle.subtitle}
        </Text>
      </Box>

      {/* Stats */}
      <Grid templateColumns="repeat(2, 1fr)" gap={2}>
        <Tooltip label="Combined Damage">
          <VStack spacing={0} p={2} bg="whiteAlpha.100" borderRadius="md">
            <Icon as={FiZap} color="orange.400" boxSize={4} />
            <Text fontSize="sm" fontWeight="bold" fontFamily="heading">
              {combinedDamage.toLocaleString()}
            </Text>
            <Text fontSize="xs" color="gray.500">Damage</Text>
          </VStack>
        </Tooltip>
        <Tooltip label="Average Trade Ratio">
          <VStack spacing={0} p={2} bg="whiteAlpha.100" borderRadius="md">
            <Icon as={FiTrendingUp} color="green.400" boxSize={4} />
            <Text fontSize="sm" fontWeight="bold" fontFamily="heading">
              {avgRatio >= 100 ? 'Perfect' : `${avgRatio.toFixed(1)}:1`}
            </Text>
            <Text fontSize="xs" color="gray.500">Ratio</Text>
          </VStack>
        </Tooltip>
      </Grid>

      {/* Historical Synergy Data */}
      {synergy && synergy.games_together > 0 && (
        <Box mt={3} pt={3} borderTop="1px solid" borderColor="whiteAlpha.200">
          <Text fontSize="xs" color="gray.400" textAlign="center">
            {synergy.games_together} games together
            {' '}|{' '}
            {synergy.win_rate_together.toFixed(0)}% win rate
          </Text>
        </Box>
      )}
    </Box>
  );
};

const TeamChemistryCard: React.FC<{
  players: MatchPlayerSummary[];
  teamNumber: number;
  isWinner: boolean;
}> = ({ players, teamNumber, isWinner }) => {
  const chemistry = calculateTeamChemistry(players);
  const chemistryColor =
    chemistry >= 70 ? 'green' :
    chemistry >= 50 ? 'yellow' :
    'red';

  const chemistryLabel =
    chemistry >= 80 ? 'Legendary' :
    chemistry >= 70 ? 'Strong' :
    chemistry >= 50 ? 'Average' :
    chemistry >= 30 ? 'Weak' :
    'Poor';

  return (
    <Box
      p={4}
      bg={isWinner ? 'rgba(72, 187, 120, 0.1)' : 'rgba(245, 101, 101, 0.1)'}
      borderRadius="lg"
      border="2px solid"
      borderColor={isWinner ? 'green.400' : 'red.400'}
    >
      <HStack justify="space-between" mb={3}>
        <HStack>
          <Icon
            as={FiUsers}
            color={teamNumber === 1 ? 'cyan.400' : 'orange.400'}
            boxSize={5}
          />
          <Text fontWeight="bold" fontFamily="heading">
            Team {teamNumber}
          </Text>
        </HStack>
        <Badge colorScheme={isWinner ? 'green' : 'red'}>
          {isWinner ? 'WINNER' : 'DEFEAT'}
        </Badge>
      </HStack>

      {/* Chemistry Score */}
      <Box mb={4}>
        <HStack justify="space-between" mb={2}>
          <Text fontSize="sm" color="gray.400">Team Chemistry</Text>
          <HStack>
            <Badge colorScheme={chemistryColor}>{chemistryLabel}</Badge>
            <Text fontWeight="bold" fontFamily="heading">
              {chemistry.toFixed(0)}%
            </Text>
          </HStack>
        </HStack>
        <Progress
          value={chemistry}
          size="sm"
          colorScheme={chemistryColor}
          bg="whiteAlpha.200"
          borderRadius="full"
        />
      </Box>

      {/* Player List */}
      <VStack spacing={2} align="stretch">
        {players.map((player) => (
          <HStack key={player.player_id} justify="space-between">
            <HStack>
              <Avatar
                size="xs"
                name={player.player_name}
                src={getPlayerAvatarUrl(player.player_name, player.race)}
              />
              <Text fontSize="sm">{player.player_name}</Text>
            </HStack>
            <Badge colorScheme={getRaceColor(player.race)} size="sm">
              {player.race.charAt(0)}
            </Badge>
          </HStack>
        ))}
      </VStack>
    </Box>
  );
};

export const SynergyTab: React.FC<SynergyTabProps> = ({
  players,
  matchId: _matchId,
  winnerTeam,
  synergies,
}) => {
  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);

  const team1Duos = generateDuoCombinations(team1Players);
  const team2Duos = generateDuoCombinations(team2Players);

  // Find synergy data for players if available
  const findSynergy = (p1: MatchPlayerSummary, p2: MatchPlayerSummary): PlayerSynergy | undefined => {
    if (!synergies) return undefined;
    return synergies.find(
      (s) =>
        (s.player1_id === p1.player_id && s.player2_id === p2.player_id) ||
        (s.player1_id === p2.player_id && s.player2_id === p1.player_id)
    );
  };

  return (
    <VStack spacing={6} align="stretch">
      {/* Team Chemistry Overview */}
      <Box>
        <Heading size="md" fontFamily="heading" color="brand.400" mb={4}>
          <Icon as={FiActivity} mr={2} />
          Team Chemistry
        </Heading>
        <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
          <TeamChemistryCard
            players={team1Players}
            teamNumber={1}
            isWinner={winnerTeam === 1}
          />
          <TeamChemistryCard
            players={team2Players}
            teamNumber={2}
            isWinner={winnerTeam === 2}
          />
        </Grid>
      </Box>

      <Divider borderColor="whiteAlpha.200" />

      {/* Power Duos Section */}
      <Box>
        <Heading size="md" fontFamily="heading" color="brand.400" mb={4}>
          <Icon as={FiStar} mr={2} />
          Power Duos
        </Heading>
        <Text fontSize="sm" color="gray.400" mb={4}>
          Player combinations and their synergy in this match.
        </Text>

        <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
          {/* Team 1 Duos */}
          {team1Duos.length > 0 && (
            <Box>
              <Text fontFamily="heading" fontSize="sm" color="cyan.400" mb={3}>
                Team 1 Duos
              </Text>
              <VStack spacing={4} align="stretch">
                {team1Duos.map((duo, idx) => (
                  <DuoCard
                    key={`t1-${idx}`}
                    player1={duo.player1}
                    player2={duo.player2}
                    synergy={findSynergy(duo.player1, duo.player2)}
                  />
                ))}
              </VStack>
            </Box>
          )}

          {/* Team 2 Duos */}
          {team2Duos.length > 0 && (
            <Box>
              <Text fontFamily="heading" fontSize="sm" color="orange.400" mb={3}>
                Team 2 Duos
              </Text>
              <VStack spacing={4} align="stretch">
                {team2Duos.map((duo, idx) => (
                  <DuoCard
                    key={`t2-${idx}`}
                    player1={duo.player1}
                    player2={duo.player2}
                    synergy={findSynergy(duo.player1, duo.player2)}
                  />
                ))}
              </VStack>
            </Box>
          )}
        </Grid>

        {/* No duos message for 1v1 or small teams */}
        {team1Duos.length === 0 && team2Duos.length === 0 && (
          <Box
            p={6}
            bg="rgba(30, 41, 59, 0.3)"
            borderRadius="lg"
            textAlign="center"
          >
            <Icon as={FiUsers} boxSize={8} color="gray.500" mb={2} />
            <Text color="gray.400">
              Duo analysis requires team games with 2+ players per team.
            </Text>
          </Box>
        )}
      </Box>
    </VStack>
  );
};

export default SynergyTab;
