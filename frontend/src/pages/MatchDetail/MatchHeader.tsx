/**
 * MatchHeader Component - Match info header with metadata
 */
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  Icon,
  Flex,
  Link,
} from '@chakra-ui/react';
import { FiAlertTriangle, FiHelpCircle } from 'react-icons/fi';
import { Link as RouterLink } from 'react-router-dom';
import {
  formatDuration,
  formatDateTime,
  getUpsetIndicator,
  displayedMMRChange,
} from '@/utils/formatting';
import VSScreen from '@/components/VSScreen';
import type { MatchDetail as MatchDetailType } from '@/types/api';

interface MatchHeaderProps {
  matchData: MatchDetailType;
  winningTeam: number | null;
}

const SuggestedResultNotice: React.FC<{
  winningTeam: number;
  durationSeconds: number;
  teamSupply?: Record<string, number>;
  otherRecordings: { winner_team: number }[];
}> = ({ winningTeam, durationSeconds, teamSupply, otherRecordings }) => {
  const disagreement = otherRecordings.find((r) => r.winner_team !== winningTeam);
  return (
    <HStack mt={4} spacing={3} align="start" p={3} borderRadius="lg" bg="whiteAlpha.50" borderLeft="3px solid" borderLeftColor="yellow.400">
      <Icon as={FiHelpCircle} color="yellow.300" mt={0.5} />
      <Text fontSize="sm" color="gray.300">
        <Text as="span" fontWeight="bold" color="yellow.200">
          Recorded through {formatDuration(durationSeconds)} — result unconfirmed.
        </Text>{' '}
        The replay didn&apos;t record who won, so Team {winningTeam} was given the win for its clear supply lead.
        {teamSupply && teamSupply['1'] !== undefined && teamSupply['2'] !== undefined && (
          <> At the last moment everyone was still recorded, Team 1 had <b>{Math.round(teamSupply['1'])}</b> supply
            and Team 2 had <b>{Math.round(teamSupply['2'])}</b>.</>
        )}
        {disagreement && <> Another recording of this game says Team {disagreement.winner_team} won.</>}{' '}
        <Link as={RouterLink} to="/results-review" color="accent.400">Review results</Link>
      </Text>
    </HStack>
  );
};

const UnknownResultNotice: React.FC<{ teamSupply?: Record<string, number> }> = ({ teamSupply }) => (
  <HStack mt={4} spacing={3} align="start" p={3} borderRadius="lg" bg="whiteAlpha.50" borderLeft="3px solid" borderLeftColor="yellow.400">
    <Icon as={FiHelpCircle} color="yellow.300" mt={0.5} />
    <Text fontSize="sm" color="gray.300">
      <Text as="span" fontWeight="bold" color="yellow.200">No result — not rated.</Text>{' '}
      The replay didn&apos;t record who won and neither team had a clear supply lead
      {teamSupply && teamSupply['1'] !== undefined && teamSupply['2'] !== undefined && (
        <> (Team 1 <b>{Math.round(teamSupply['1'])}</b>, Team 2 <b>{Math.round(teamSupply['2'])}</b>)</>
      )}
      . It counts once someone says who won.{' '}
      <Link as={RouterLink} to="/results-review" color="accent.400">Review results</Link>
    </Text>
  </HStack>
);

const MatchHeader: React.FC<MatchHeaderProps> = ({ matchData, winningTeam }) => {
  const cardBg = 'space.800';

  const { match, players } = matchData;

  // Win probability analysis
  const hasWinProb =
    match.predicted_team1_win_prob !== null &&
    match.predicted_team2_win_prob !== null;
  const team1Prob = match.predicted_team1_win_prob || 0.5;
  const team2Prob = match.predicted_team2_win_prob || 0.5;
  const upsetIndicator = hasWinProb && winningTeam !== null
    ? getUpsetIndicator(winningTeam, team1Prob, team2Prob)
    : null;

  const toPanel = (teamNumber: number, winProbability: number) => {
    const teamPlayers = players.filter(p => p.team_number === teamNumber);
    return {
      players: teamPlayers.map(p => ({
        name: p.player_name,
        mmr: p.mmr_after,
        race: p.race,
        mmrChange: displayedMMRChange(p.mmr_before, p.mmr_after),
      })),
      totalMMR: teamPlayers.reduce((sum, p) => sum + p.mmr_before, 0),
      winProbability: winProbability * 100,
    };
  };

  return (
    <VStack spacing={{ base: 3, md: 4 }} align="stretch">
      <Box bg={cardBg} borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100" p={{ base: 4, md: 5 }}>
        <Flex justify="space-between" align="start" flexWrap="wrap" gap={4}>
          <VStack align="start" spacing={2} minW={0}>
            <Flex align="center" gap={3} flexWrap="wrap">
              <Heading size="lg" fontFamily="heading" color="gray.100">
                {match.map_name}
              </Heading>
              <Badge bg="space.900" color="brand.400" fontSize="md" px={3} py={1} borderRadius="md" fontFamily="heading">
                {match.game_mode}
              </Badge>
            </Flex>
            <Text color="gray.400" fontSize="sm">
              {formatDateTime(match.played_at)} ·{' '}
              {winningTeam === null ? (
                <Text as="span" color="gray.400" fontWeight="bold">No result</Text>
              ) : (
                <Text as="span" color={winningTeam === 1 ? 'brand.400' : 'accent.400'} fontWeight="bold">Team {winningTeam} won</Text>
              )}
            </Text>
          </VStack>

          <Stat textAlign="right" flex="0 0 auto">
            <StatLabel color="gray.500" letterSpacing="widest" textTransform="uppercase" fontSize="xs">
              Duration
            </StatLabel>
            <StatNumber fontSize={{ base: '2xl', md: '3xl' }} fontFamily="mono" color="gray.100">
              {formatDuration(match.duration_seconds)}
            </StatNumber>
          </Stat>
        </Flex>

        {match.result_source === 'unknown' && <UnknownResultNotice teamSupply={match.result_evidence?.team_supply} />}

        {match.result_source === 'suggested' && winningTeam !== null && (
          <SuggestedResultNotice
            winningTeam={winningTeam}
            durationSeconds={match.duration_seconds}
            teamSupply={match.result_evidence?.team_supply}
            otherRecordings={match.result_evidence?.other_recordings ?? []}
          />
        )}

        {upsetIndicator && (
          <HStack mt={4} spacing={3} p={3} borderRadius="lg" bg="rgba(255, 179, 0, 0.08)" borderLeft="3px solid" borderLeftColor="accent.500">
            <Icon as={FiAlertTriangle} color="accent.400" />
            <Text fontSize="sm" color="gray.200">
              <Text as="span" fontWeight="bold" color="accent.400">{upsetIndicator}</Text> — the underdogs beat the pre-match odds.
            </Text>
          </HStack>
        )}
      </Box>

      <VSScreen
        team1={toPanel(1, team1Prob)}
        team2={toPanel(2, team2Prob)}
        winner={winningTeam === 1 || winningTeam === 2 ? winningTeam : null}
        probabilityLabel="Pre-match odds"
        totalLabel="Pre-match MMR"
        compact
      />
    </VStack>
  );
};

export default MatchHeader;
