/**
 * Match Detail Page - Match Analysis
 * Comprehensive match information with win probability analysis
 */
import {
  Box,
  Container,
  VStack,
  Button,
  Alert,
  AlertIcon,
  Icon,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useColorModeValue,
} from '@chakra-ui/react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiUsers, FiZap, FiTarget } from 'react-icons/fi';
import { replaysApi, impactApi } from '@/api/endpoints';
import LoadingState from '@/components/LoadingState';
import MatchHeader from './MatchHeader';
import OperativesTab from './OperativesTab';
import CommentaryTab from './CommentaryTab';
import AnalyticsTab from './AnalyticsTab';
import type {
  MatchCommentary,
  PlayerMetricsResponse,
  PlayerTimeline,
  TimelineData,
} from './types';
import type { MatchDetail as MatchDetailType } from '@/types/api';

const MatchDetail: React.FC = () => {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();

  // Reserved for future card styling
  void useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');

  // Fetch match details
  const { data: matchData, isLoading: matchLoading } = useQuery<MatchDetailType>({
    queryKey: ['match', matchId],
    queryFn: async () => {
      const response = await replaysApi.getMatchById(matchId!);
      return response.data;
    },
  });

  // Fetch match commentary
  const { data: commentary, isLoading: commentaryLoading } =
    useQuery<MatchCommentary>({
      queryKey: ['match-commentary', matchId],
      queryFn: async () => {
        const response = await replaysApi.getMatchCommentary(matchId!);
        return response.data as unknown as MatchCommentary;
      },
      enabled: !!matchData,
    });

  // Fetch metrics data for all players in the match
  const {
    data: playerMetrics,
    isLoading: metricsLoading,
  } = useQuery<Record<number, PlayerMetricsResponse>>({
    queryKey: ['match-metrics', matchId],
    queryFn: async () => {
      if (!matchData || !matchData.players) return {};

      const metricsPromises = matchData.players.map(async (player) => {
        try {
          const response = await impactApi.getPlayerMatchMetrics(
            player.player_id,
            100
          );
          // Find the metrics for this specific match - response.data is MatchPlayerMetrics[]
          const matchMetric = (response.data as PlayerMetricsResponse[]).find(
            (m) => m.match_id === parseInt(matchId!)
          );
          return {
            player_id: player.player_id,
            player_name: player.player_name,
            metrics: matchMetric,
          };
        } catch (error) {
          console.error(
            `Error fetching metrics for player ${player.player_id}:`,
            error
          );
          return null;
        }
      });

      const results = await Promise.all(metricsPromises);

      // Convert to object keyed by player_id for easy lookup
      const metricsMap: Record<number, PlayerMetricsResponse> = {};
      results.forEach((result) => {
        if (result && result.metrics) {
          metricsMap[result.player_id] = result.metrics;
        }
      });

      return metricsMap;
    },
    enabled: !!matchData,
  });

  // Fetch damage timeline data for players
  const {
    data: damageTimelines,
    isLoading: timelinesLoading,
  } = useQuery<PlayerTimeline[]>({
    queryKey: ['match-damage-timelines', matchId],
    queryFn: async (): Promise<PlayerTimeline[]> => {
      if (!matchData || !matchData.players) return [];

      const timelinePromises = matchData.players.map(async (player): Promise<PlayerTimeline | null> => {
        try {
          const response = await impactApi.getMatchDamageTimeline(
            player.player_id,
            matchId!
          );
          return {
            player_id: player.player_id,
            player_name: player.player_name,
            team_number: player.team_number,
            timeline: response.data as TimelineData,
          };
        } catch {
          // Timeline might not be available for all players
          return null;
        }
      });

      const results = await Promise.all(timelinePromises);
      return results.filter((r): r is PlayerTimeline => r !== null);
    },
    enabled: !!matchData,
  });

  if (matchLoading) {
    return (
      <Box bg="space.900">
        <Container maxW="container.xl" py={8}>
          <LoadingState message="Loading match data..." />
        </Container>
      </Box>
    );
  }

  if (!matchData) {
    return (
      <Box bg="space.900">
        <Container maxW="container.xl" py={8}>
          <Alert status="error">
            <AlertIcon />
            Match data not found
          </Alert>
        </Container>
      </Box>
    );
  }

  const { players } = matchData;

  // Group players by team
  const team1Players = players.filter((p) => p.team_number === 1);
  const team1Won = team1Players.length > 0 && team1Players[0].won;

  return (
    <Box position="relative" bg="space.900">
      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Back Button */}
          <Button
            leftIcon={<FiArrowLeft />}
            variant="ghost"
            alignSelf="flex-start"
            onClick={() => navigate('/history')}
            size="lg"
            fontFamily="heading"
            _hover={{
              transform: 'translateX(-4px)',
              color: 'brand.400',
            }}
            transition="all 0.2s"
          >
            Return to Archive
          </Button>

          {/* Match Header */}
          <MatchHeader matchData={matchData} team1Won={team1Won} />

          {/* Tabs for different views */}
          <Tabs
            colorScheme="brand"
            variant="enclosed"
            size="lg"
            sx={{
              '& .chakra-tabs__tab': {
                fontFamily: 'heading',
                letterSpacing: 'wider',
                _selected: {
                  bg: 'brand.500',
                  color: 'gray.900',
                  borderColor: 'brand.500',
                },
              },
            }}
          >
            <TabList>
              <Tab>
                <Icon as={FiUsers} mr={2} />
                Players
              </Tab>
              <Tab>
                <Icon as={FiZap} mr={2} />
                Commentary
              </Tab>
              <Tab>
                <Icon as={FiTarget} mr={2} />
                Analytics
              </Tab>
            </TabList>

            <TabPanels>
              {/* Operatives Tab */}
              <TabPanel px={0}>
                <OperativesTab matchData={matchData} team1Won={team1Won} />
              </TabPanel>

              {/* Commentary Tab */}
              <TabPanel px={0}>
                <CommentaryTab
                  commentary={commentary}
                  isLoading={commentaryLoading}
                />
              </TabPanel>

              {/* Analytics Tab */}
              <TabPanel px={0}>
                <AnalyticsTab
                  matchData={matchData}
                  playerMetrics={playerMetrics}
                  damageTimelines={damageTimelines}
                  metricsLoading={metricsLoading}
                  timelinesLoading={timelinesLoading}
                />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </VStack>
      </Container>
    </Box>
  );
};

export default MatchDetail;
