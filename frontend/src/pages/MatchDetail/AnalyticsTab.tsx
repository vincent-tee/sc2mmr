/**
 * AnalyticsTab Component - Match analytics and player metrics
 */
import {
  Box,
  VStack,
  Heading,
  Grid,
  GridItem,
  Alert,
  AlertIcon,
  Divider,
} from '@chakra-ui/react';
import DamageTimelineChart from '@/components/charts/DamageTimelineChart';
import ImpactScoreRadar from '@/components/charts/ImpactScoreRadar';
import DamageDistributionChart from '@/components/charts/DamageDistributionChart';
import PlayerMetricsComparison from '@/components/charts/PlayerMetricsComparison';
import LoadingState from '@/components/LoadingState';
import {
  transformDamageDistribution,
  transformTimelineData,
} from './helpers';
import type {
  PlayerMetricsResponse,
  PlayerTimeline,
} from './types';
import type { MatchDetail as MatchDetailType } from '@/types/api';

interface AnalyticsTabProps {
  matchData: MatchDetailType;
  playerMetrics: Record<number, PlayerMetricsResponse> | undefined;
  damageTimelines: PlayerTimeline[] | undefined;
  metricsLoading: boolean;
  timelinesLoading: boolean;
}

const AnalyticsTab: React.FC<AnalyticsTabProps> = ({
  matchData,
  playerMetrics,
  damageTimelines,
  metricsLoading,
  timelinesLoading,
}) => {
  const { players } = matchData;

  // Group players by team
  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);

  if (metricsLoading || timelinesLoading) {
    return <LoadingState message="Loading match analytics..." />;
  }

  if (!playerMetrics || Object.keys(playerMetrics).length === 0) {
    return (
      <Alert status="info">
        <AlertIcon />
        Advanced analytics are only available for matches with detailed metrics data.
        Upload replays using the "Advanced Upload" option to enable analytics.
      </Alert>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      {/* Player Comparison */}
      <PlayerMetricsComparison
        players={players}
        metricsData={playerMetrics}
      />

      {/* Team 1 Individual Analytics */}
      <Box>
        <Heading
          size="lg"
          mb={4}
          fontFamily="heading"
          letterSpacing="wider"
        >
          Team 1 Analytics
        </Heading>
        <VStack spacing={4} align="stretch">
          {team1Players.map((player) => {
            const metrics = playerMetrics[player.player_id];
            const timeline = damageTimelines?.find(
              (t) => t.player_id === player.player_id
            );

            if (!metrics) return null;

            return (
              <Box key={player.player_id}>
                <Grid
                  templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }}
                  gap={4}
                >
                  {/* Impact Score Radar */}
                  <GridItem>
                    <ImpactScoreRadar
                      metrics={metrics}
                      playerName={player.player_name}
                    />
                  </GridItem>

                  {/* Damage Distribution */}
                  <GridItem>
                    {timeline && timeline.timeline.damage_distribution && (
                      <DamageDistributionChart
                        damageDistribution={transformDamageDistribution(
                          timeline.timeline.damage_distribution
                        )}
                        playerName={player.player_name}
                      />
                    )}
                  </GridItem>
                </Grid>

                {/* Damage Timeline */}
                {timeline && (
                  <Box mt={4}>
                    <DamageTimelineChart
                      timelineData={transformTimelineData(timeline.timeline)}
                      playerName={player.player_name}
                    />
                  </Box>
                )}

                <Divider my={6} borderColor="whiteAlpha.200" />
              </Box>
            );
          })}
        </VStack>
      </Box>

      {/* Team 2 Individual Analytics */}
      <Box>
        <Heading
          size="lg"
          mb={4}
          fontFamily="heading"
          letterSpacing="wider"
        >
          Team 2 Analytics
        </Heading>
        <VStack spacing={4} align="stretch">
          {team2Players.map((player, playerIndex) => {
            const metrics = playerMetrics[player.player_id];
            const timeline = damageTimelines?.find(
              (t) => t.player_id === player.player_id
            );

            if (!metrics) return null;

            return (
              <Box key={player.player_id}>
                <Grid
                  templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }}
                  gap={4}
                >
                  {/* Impact Score Radar */}
                  <GridItem>
                    <ImpactScoreRadar
                      metrics={metrics}
                      playerName={player.player_name}
                    />
                  </GridItem>

                  {/* Damage Distribution */}
                  <GridItem>
                    {timeline && timeline.timeline.damage_distribution && (
                      <DamageDistributionChart
                        damageDistribution={transformDamageDistribution(
                          timeline.timeline.damage_distribution
                        )}
                        playerName={player.player_name}
                      />
                    )}
                  </GridItem>
                </Grid>

                {/* Damage Timeline */}
                {timeline && (
                  <Box mt={4}>
                    <DamageTimelineChart
                      timelineData={transformTimelineData(timeline.timeline)}
                      playerName={player.player_name}
                    />
                  </Box>
                )}

                {playerIndex !== team2Players.length - 1 && (
                  <Divider my={6} borderColor="whiteAlpha.200" />
                )}
              </Box>
            );
          })}
        </VStack>
      </Box>
    </VStack>
  );
};

export default AnalyticsTab;
