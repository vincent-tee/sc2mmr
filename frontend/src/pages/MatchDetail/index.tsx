/**
 * Match Detail Page - Match Analysis
 * Comprehensive match information with win probability analysis
 */
import {
  Box,
  Container,
  VStack,
  HStack,
  Button,
  Alert,
  AlertIcon,
  Icon,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiZap, FiTarget, FiDownload, FiMonitor } from 'react-icons/fi';
import { replaysApi, impactApi } from '@/api/endpoints';
import LoadingState from '@/components/LoadingState';
import MatchBalanceFeedback from '@/components/MatchBalanceFeedback';
import { useAuth } from '@/components/AuthGate';
import MatchHeader from './MatchHeader';
import CommentaryTab from './CommentaryTab';
import AnalyticsTab from './AnalyticsTab';
import ScoreScreenTab from './ScoreScreenTab';
import type {
  MatchCommentary,
  PlayerMetricsResponse,
} from './types';
import type { MatchDetail as MatchDetailType } from '@/types/api';

const MatchDetail: React.FC = () => {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const { authEnabled, authenticated, requireLogin } = useAuth();

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

  if (matchLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading match data..." />
      </Container>
    );
  }

  if (!matchData) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert status="error">
          <AlertIcon />
          Match data not found
        </Alert>
      </Container>
    );
  }

  const { players } = matchData;

  const winningTeam = players.find((p) => p.won)?.team_number ?? null;

  return (
    <Box position="relative">
      <Container maxW="container.xl" py={{ base: 4, md: 6 }} position="relative" zIndex={1}>
        <VStack spacing={{ base: 4, md: 5 }} align="stretch">
          {/* Back Button + Replay Download */}
          <HStack justify="space-between" align="center" flexWrap="wrap" gap={3}>
            <Button
              leftIcon={<FiArrowLeft />}
              variant="ghost"
              alignSelf="flex-start"
              onClick={() => navigate('/history')}
              size="md"
              fontFamily="heading"
              _hover={{
                transform: 'translateX(-4px)',
                color: 'brand.400',
              }}
              transition="all 0.2s"
            >
              All matches
            </Button>
            {matchData.match.replay_hash && (
              <Button
                as="a"
                href={replaysApi.getMatchDownloadUrl(matchId!)}
                onClick={(e: React.MouseEvent) => {
                  // Downloads are a raw browser navigation (not axios), so a
                  // 401 would dump raw JSON instead of the login screen. When
                  // auth is on and we're not signed in, prompt for the squad
                  // password instead of navigating.
                  if (authEnabled && !authenticated) {
                    e.preventDefault();
                    requireLogin();
                  }
                }}
                leftIcon={<FiDownload />}
                variant="outline"
                colorScheme="brand"
                size="sm"
                fontFamily="heading"
              >
                Download Replay
              </Button>
            )}
          </HStack>

          {/* Match Header */}
          <MatchHeader matchData={matchData} winningTeam={winningTeam} />

          {/* Tabs for different views */}
          <Tabs
            colorScheme="brand"
            variant="enclosed"
            size={{ base: 'sm', md: 'md' }}
            isLazy
            sx={{
              '& .chakra-tabs__tab': {
                fontFamily: 'heading',
                letterSpacing: 'wider',
                whiteSpace: 'nowrap',
                flexShrink: 0,
                _selected: {
                  bg: 'brand.500',
                  color: 'gray.900',
                  borderColor: 'brand.500',
                },
              },
            }}
          >
            <TabList overflowX="auto" overflowY="hidden">
              <Tab>
                <Icon as={FiMonitor} mr={2} />
                Scores
              </Tab>
              <Tab>
                <Icon as={FiZap} mr={2} />
                Recap
              </Tab>
              <Tab>
                <Icon as={FiTarget} mr={2} />
                Impact
              </Tab>
            </TabList>

            <TabPanels>
              {/* Score Screen Tab */}
              <TabPanel px={0}>
                <ScoreScreenTab matchData={matchData} winningTeam={winningTeam} />
              </TabPanel>

              {/* Commentary Tab */}
              <TabPanel px={0}>
                <CommentaryTab commentary={commentary} isLoading={commentaryLoading} />
              </TabPanel>

              {/* Analytics Tab */}
              <TabPanel px={0}>
                <AnalyticsTab matchData={matchData} playerMetrics={playerMetrics} metricsLoading={metricsLoading} />
              </TabPanel>
            </TabPanels>
          </Tabs>
          {authenticated && <MatchBalanceFeedback key={matchId} matchId={Number(matchId)} />}
        </VStack>
      </Container>
    </Box>
  );
};

export default MatchDetail;
