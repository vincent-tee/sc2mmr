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
} from '@chakra-ui/react';
import { FiAlertTriangle } from 'react-icons/fi';
import {
  formatDuration,
  formatDateTime,
  getUpsetIndicator,
} from '@/utils/formatting';
import VSScreen from '@/components/VSScreen';
import type { MatchDetail as MatchDetailType } from '@/types/api';

interface MatchHeaderProps {
  matchData: MatchDetailType;
  team1Won: boolean;
}

const MatchHeader: React.FC<MatchHeaderProps> = ({ matchData, team1Won }) => {
  const cardBg = 'space.800';

  const { match, players } = matchData;

  // Win probability analysis
  const hasWinProb =
    match.predicted_team1_win_prob !== null &&
    match.predicted_team2_win_prob !== null;
  const team1Prob = match.predicted_team1_win_prob || 0.5;
  const team2Prob = match.predicted_team2_win_prob || 0.5;
  const winningTeam = team1Won ? 1 : 2;
  const upsetIndicator = hasWinProb
    ? getUpsetIndicator(winningTeam, team1Prob, team2Prob)
    : null;

  // Prepare VSScreen data
  const team1Players = players.filter(p => p.team_number === 1);
  const team2Players = players.filter(p => p.team_number === 2);
  const team1TotalMMR = team1Players.reduce((sum, p) => sum + (p.mmr ?? p.mmr_before), 0);
  const team2TotalMMR = team2Players.reduce((sum, p) => sum + (p.mmr ?? p.mmr_before), 0);

  const vsScreenData = {
    team1: {
      players: team1Players.map(p => ({
        name: p.player_name,
        mmr: p.mmr ?? p.mmr_before,
        race: p.race,
      })),
      totalMMR: team1TotalMMR,
      winProbability: team1Prob * 100,
    },
    team2: {
      players: team2Players.map(p => ({
        name: p.player_name,
        mmr: p.mmr ?? p.mmr_before,
        race: p.race,
      })),
      totalMMR: team2TotalMMR,
      winProbability: team2Prob * 100,
    },
    winner: winningTeam,
  };

  return (
    <VStack spacing={{ base: 4, md: 6 }} align="stretch">
      <Box bg={cardBg} borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100" p={{ base: 4, md: 6 }}>
        <Flex justify="space-between" align="start" flexWrap="wrap" gap={4}>
          <VStack align="start" spacing={2} minW={0}>
            <Flex align="center" gap={3} flexWrap="wrap">
              <Heading size={{ base: 'lg', md: 'xl' }} fontFamily="heading" color="gray.100">
                {match.map_name}
              </Heading>
              <Badge bg="space.900" color="brand.400" fontSize="md" px={3} py={1} borderRadius="md" fontFamily="heading">
                {match.game_mode}
              </Badge>
            </Flex>
            <Text color="gray.400" fontSize="sm">
              {formatDateTime(match.played_at)} · <Text as="span" color={team1Won ? 'brand.400' : 'accent.400'} fontWeight="bold">Team {winningTeam} won</Text>
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
        team1={vsScreenData.team1}
        team2={vsScreenData.team2}
        winner={vsScreenData.winner as 1 | 2}
        probabilityLabel="Pre-match odds"
      />
    </VStack>
  );
};

export default MatchHeader;
