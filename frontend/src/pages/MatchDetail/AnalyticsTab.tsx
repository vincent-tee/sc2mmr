/**
 * AnalyticsTab Component - one comparison table of every player's impact metrics
 */
import {
  Box,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Alert,
  AlertIcon,
  Badge,
  HStack,
} from '@chakra-ui/react';
import LoadingState from '@/components/LoadingState';
import type { PlayerMetricsResponse } from './types';
import type { MatchDetail as MatchDetailType } from '@/types/api';

interface AnalyticsTabProps {
  matchData: MatchDetailType;
  playerMetrics: Record<number, PlayerMetricsResponse> | undefined;
  metricsLoading: boolean;
}

const TEAM_COLORS: Record<number, string> = { 1: 'brand.400', 2: 'accent.400' };

const ScoreCell: React.FC<{ value: number; highlight?: boolean }> = ({ value, highlight }) => (
  <Td isNumeric>
    <HStack justify="flex-end" spacing={2}>
      <Box w="48px" h="4px" bg="whiteAlpha.100" borderRadius="full" display={{ base: 'none', md: 'block' }}>
        <Box w={`${Math.min(100, Math.max(0, value))}%`} h="100%" bg={highlight ? 'brand.400' : 'gray.500'} borderRadius="full" />
      </Box>
      <Text as="span" fontWeight={highlight ? 'bold' : 'normal'} color={highlight ? 'gray.50' : 'gray.300'}>
        {value.toFixed(1)}
      </Text>
    </HStack>
  </Td>
);

const AnalyticsTab: React.FC<AnalyticsTabProps> = ({ matchData, playerMetrics, metricsLoading }) => {
  if (metricsLoading) {
    return <LoadingState message="Loading match analytics..." />;
  }

  if (!playerMetrics || Object.keys(playerMetrics).length === 0) {
    return (
      <Alert status="info" borderRadius="lg">
        <AlertIcon />
        Detailed metrics aren't available for this match.
      </Alert>
    );
  }

  const rows = [...matchData.players]
    .filter((player) => playerMetrics[player.player_id])
    .sort((a, b) => a.team_number - b.team_number || playerMetrics[b.player_id].overall_impact - playerMetrics[a.player_id].overall_impact);
  const topImpact = Math.max(...rows.map((player) => playerMetrics[player.player_id].overall_impact));

  return (
    <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" overflow="hidden">
      <TableContainer>
        <Table size="sm" variant="simple" fontFamily="mono" sx={{ 'th, td': { borderColor: 'whiteAlpha.100', px: [2, null, 4] } }}>
          <Thead>
            <Tr>
              <Th position="sticky" left={0} bg="space.800" zIndex={1}>Player</Th>
              <Th isNumeric>Impact</Th>
              <Th isNumeric>Economy</Th>
              <Th isNumeric>Combat</Th>
              <Th isNumeric>Efficiency</Th>
              <Th isNumeric>Army killed</Th>
              <Th isNumeric>Killed ÷ lost</Th>
            </Tr>
          </Thead>
          <Tbody>
            {rows.map((player) => {
              const metrics = playerMetrics[player.player_id];
              const isTop = metrics.overall_impact === topImpact;
              return (
                <Tr key={player.player_id}>
                  <Td position="sticky" left={0} bg="space.800" zIndex={1} fontFamily="body" borderLeft="3px solid" borderLeftColor={TEAM_COLORS[player.team_number] ?? 'gray.500'}>
                    <HStack spacing={2}>
                      <Text fontWeight="bold" color="gray.100" noOfLines={1} maxW={{ base: '96px', md: 'none' }}>{player.player_name}</Text>
                      {isTop && <Badge colorScheme="yellow" variant="subtle" fontSize="2xs">MVP</Badge>}
                    </HStack>
                    <Text fontSize="xs" color="gray.500">Team {player.team_number}{matchData.match.result_source === 'unknown' ? '' : player.won ? ' · won' : ' · lost'}</Text>
                  </Td>
                  <ScoreCell value={metrics.overall_impact} highlight />
                  <ScoreCell value={metrics.economic_score} />
                  <ScoreCell value={metrics.combat_score} />
                  <ScoreCell value={metrics.efficiency_score} />
                  <Td isNumeric color="gray.300">{Math.round(metrics.damage_dealt).toLocaleString()}</Td>
                  <Td isNumeric color={metrics.damage_ratio >= 1 ? 'green.300' : 'red.300'}>{metrics.damage_ratio.toFixed(2)}×</Td>
                </Tr>
              );
            })}
          </Tbody>
        </Table>
      </TableContainer>
      <Text fontSize="xs" color="gray.500" px={4} py={3} borderTop="1px solid" borderColor="whiteAlpha.100">
        Scores are 0–100 and describe how this game was played; they don't change anyone's rating.
      </Text>
    </Box>
  );
};

export default AnalyticsTab;
