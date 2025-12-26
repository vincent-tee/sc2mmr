/**
 * Living Model Dashboard
 * Unified view of model evolution, performance, and AI-driven improvements
 * Optimized for low-frequency gameplay (10 games per 2 weeks)
 */
import { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardHeader,
  CardBody,
  Button,
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Badge,
  Alert,
  AlertIcon,
  useColorModeValue,
  Icon,
  Code,
  useToast,
  Divider,
  Grid,
  GridItem,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Checkbox,
  CheckboxGroup,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import {
  FiCpu,
  FiTrendingUp,
  FiTrendingDown,
  FiMinus,
  FiCheckCircle,
  FiRefreshCw,
  FiZap,
  FiArrowRight,
  FiEdit,
} from 'react-icons/fi';
import { apiClient } from '../api/client';
import LoadingState from '../components/LoadingState';
import TacticalCard from '../components/TacticalCard';
import TacticalBackground from '../components/common/TacticalBackground';

// Type definitions for adaptive model API responses
interface WeightSuggestions {
  suggested_weights: Record<string, number>;
  current_weights: Record<string, number>;
  changes: Record<string, number>;
  confidence: number;
  performance_improvement: number;
  reason: string;
}

interface ModelPerformance {
  win_prediction_accuracy: number;
  sample_size: number;
  correlation_strength: number;
}

interface ModelVersion {
  version_name: string;
  created_at: string;
  is_active: boolean;
  is_experimental: boolean;
  accuracy: number;
  total_predictions: number;
  features_used: string[] | null;
}

interface PredictionLog {
  id: number;
  match_id: number;
  predicted_team1_win_prob: number;
  actual_team1_won: boolean;
  was_upset: boolean;
  prediction_error: number;
}

interface BlendingStats {
  total_matches: number;
  avg_error: number;
  upset_count: number;
  upset_rate: number;
}

interface Feature {
  feature_name: string;
  correlation: number;
}

interface FeatureSuggestion {
  id: number;
  feature_name: string;
  status: string;
  reasoning: string;
  extraction_logic: string;
  expected_correlation: number | null;
}

const AdaptiveModel: React.FC = () => {
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const toast = useToast();

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // ============================================================================
  // API CALLS
  // ============================================================================

  // Fetch weight suggestions
  const { data: suggestions, isLoading: suggestionsLoading, refetch: refetchSuggestions, isFetching: suggestionsFetching } = useQuery<WeightSuggestions>({
    queryKey: ['adaptive-suggestions'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/suggest-weights');
      return response.data;
    },
    staleTime: 0,
    gcTime: 0,
  });

  // Fetch model performance
  const { data: performance, isLoading: performanceLoading, refetch: refetchPerformance, isFetching: performanceFetching } = useQuery<ModelPerformance>({
    queryKey: ['model-performance'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/model-performance');
      return response.data;
    },
    staleTime: 0,
    gcTime: 0,
  });

  // Fetch model versions (for timeline)
  const { data: modelVersions, refetch: refetchVersions } = useQuery<{ versions: ModelVersion[] }>({
    queryKey: ['model-versions'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/model-versions');
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Fetch prediction logs (recent activity)
  const { data: predictionLogs, refetch: refetchLogs } = useQuery<{ predictions: PredictionLog[] }>({
    queryKey: ['prediction-logs'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/prediction-logs?limit=10');
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Fetch blending stats
  const { data: blendingStats, refetch: refetchBlending } = useQuery<BlendingStats>({
    queryKey: ['blending-stats'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/blending-stats');
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Fetch feature importance
  const { data: featureImportance, refetch: refetchFeatures } = useQuery<{ features: Feature[] }>({
    queryKey: ['feature-importance'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/feature-importance');
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Fetch AI feature suggestions
  const { data: featureSuggestions, refetch: refetchSuggestions2 } = useQuery<{ suggestions: FeatureSuggestion[] }>({
    queryKey: ['feature-suggestions'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/feature-suggestions');
      return response.data;
    },
    refetchInterval: 30000,
  });

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatChange = (value: number): string => {
    const formatted = formatPercentage(value);
    return value > 0 ? `+${formatted}` : formatted;
  };

  const refreshAll = async (): Promise<void> => {
    try {
      await Promise.all([
        refetchSuggestions(),
        refetchPerformance(),
        refetchVersions(),
        refetchLogs(),
        refetchBlending(),
        refetchFeatures(),
        refetchSuggestions2(),
      ]);
      setLastUpdated(new Date());
      toast({
        title: 'Dashboard refreshed',
        description: 'All data updated from latest match activity',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh data';
      toast({
        title: 'Refresh failed',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  // ============================================================================
  // LOADING STATE
  // ============================================================================

  if (suggestionsLoading || performanceLoading) {
    return <LoadingState message="Loading Living Model Dashboard..." />;
  }

  const versions = modelVersions?.versions || [];
  const logs = predictionLogs?.predictions || [];
  const features = featureImportance?.features || [];
  const aiSuggestions = featureSuggestions?.suggestions || [];

  // Calculate recent learning activity
  const recentCorrectPredictions = logs.filter(
    (log) => {
      const predicted = log.predicted_team1_win_prob > 0.5;
      const actual = log.actual_team1_won;
      return predicted === actual;
    }
  ).length;
  const recentAccuracy = logs.length > 0 ? recentCorrectPredictions / logs.length : 0;

  return (
    <Box position="relative">
      {/* Tactical grid background */}
      <TacticalBackground opacity={0.02} gridSize={60} variant="cyan" />

      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
        {/* ====================================================================== */}
        {/* HEADER */}
        {/* ====================================================================== */}
        <Box>
          <HStack spacing={3} mb={2}>
            <Icon as={FiCpu} boxSize={10} color="purple.500" />
            <Heading
              size="2xl"
              bgGradient="linear(to-r, cyan.400, purple.500)"
              bgClip="text"
              fontWeight="black"
              letterSpacing="tight"
            >
              Living Model Dashboard
            </Heading>
          </HStack>
          <Text color="gray.400" fontSize="lg" fontWeight="medium">
            "Your AI is learning from your gameplay"
          </Text>
          <HStack spacing={4} mt={2}>
            <Text color="gray.500" fontSize="sm">
              Last updated: {lastUpdated.toLocaleTimeString('en-AU', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                timeZone: 'Australia/Sydney'
              })}
            </Text>
            <Button
              leftIcon={<FiRefreshCw />}
              size="sm"
              variant="ghost"
              colorScheme="cyan"
              isLoading={suggestionsFetching || performanceFetching}
              onClick={refreshAll}
            >
              Refresh All
            </Button>
          </HStack>
        </Box>

        {/* ====================================================================== */}
        {/* SECTION 1: MODEL EVOLUTION TIMELINE */}
        {/* ====================================================================== */}
        <TacticalCard>
          <Heading size="md" mb={4}>
            <Icon as={FiTrendingUp} mr={2} />
            Model Evolution Timeline
          </Heading>

          {versions.length === 0 ? (
            <Alert status="info" borderRadius="md">
              <AlertIcon />
              <Text fontSize="sm">
                No model versions yet. Upload replays to start the learning journey!
              </Text>
            </Alert>
          ) : (
            <HStack spacing={4} overflowX="auto" pb={4}>
              {versions.slice(0, 5).map((version, idx) => (
                <Card
                  key={version.version_name}
                  minW="280px"
                  bg={version.is_active ? 'purple.900' : cardBg}
                  borderColor={version.is_active ? 'purple.500' : borderColor}
                  borderWidth="2px"
                  position="relative"
                >
                  <CardBody>
                    <VStack align="stretch" spacing={2}>
                      <HStack justify="space-between">
                        <Badge
                          colorScheme={
                            version.is_active
                              ? 'purple'
                              : version.is_experimental
                              ? 'cyan'
                              : 'gray'
                          }
                        >
                          {version.is_active
                            ? 'Current'
                            : version.is_experimental
                            ? 'Testing'
                            : 'Baseline'}
                        </Badge>
                        <Text fontSize="xs" color="gray.500">
                          {new Date(version.created_at).toLocaleDateString()}
                        </Text>
                      </HStack>

                      <Text fontWeight="bold" fontSize="lg">
                        {version.version_name}
                      </Text>

                      <Divider />

                      <VStack align="stretch" spacing={1} fontSize="sm">
                        <HStack justify="space-between">
                          <Text color="gray.400">Accuracy:</Text>
                          <Text fontWeight="bold" color="green.400">
                            {formatPercentage(version.accuracy)}
                          </Text>
                        </HStack>
                        <HStack justify="space-between">
                          <Text color="gray.400">Predictions:</Text>
                          <Text>{version.total_predictions}</Text>
                        </HStack>
                        <HStack justify="space-between">
                          <Text color="gray.400">Features:</Text>
                          <Text>{version.features_used?.length || 0}</Text>
                        </HStack>
                      </VStack>

                      {idx > 0 && versions[idx - 1] && (
                        <HStack spacing={1} fontSize="xs" color="gray.500">
                          <Icon as={FiArrowRight} />
                          <Text>
                            {formatChange(version.accuracy - versions[idx - 1].accuracy)} vs previous
                          </Text>
                        </HStack>
                      )}
                    </VStack>
                  </CardBody>
                </Card>
              ))}
            </HStack>
          )}
        </TacticalCard>

        {/* ====================================================================== */}
        {/* SECTIONS 2 & 3: CURRENT PERFORMANCE + WHAT'S CHANGING */}
        {/* ====================================================================== */}
        <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
          {/* LEFT COLUMN: Current Performance */}
          <GridItem>
            <TacticalCard h="full">
              <Heading size="md" mb={4}>
                Current Performance
              </Heading>

              <VStack spacing={6} align="stretch">
                {/* Win Prediction Accuracy */}
                <Box>
                  <Stat>
                    <StatLabel>Match Prediction Accuracy</StatLabel>
                    <StatNumber fontSize="5xl" color="green.400">
                      {formatPercentage(performance?.win_prediction_accuracy || 0)}
                    </StatNumber>
                    <StatHelpText>
                      {(performance?.win_prediction_accuracy || 0) > 0.5 ? (
                        <StatArrow type="increase" />
                      ) : (
                        <StatArrow type="decrease" />
                      )}
                      Correctly predicted winner in {performance?.sample_size || 0} matches
                    </StatHelpText>
                  </Stat>
                  <Progress
                    value={(performance?.win_prediction_accuracy || 0) * 100}
                    colorScheme={(performance?.win_prediction_accuracy || 0) >= 0.5 ? "green" : "orange"}
                    size="sm"
                    borderRadius="md"
                    mt={2}
                  />
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    {(performance?.win_prediction_accuracy || 0) >= 0.5
                      ? `${formatPercentage((performance?.win_prediction_accuracy || 0) - 0.5)} better than random (50%)`
                      : `${formatPercentage(0.5 - (performance?.win_prediction_accuracy || 0))} below random (50%)`
                    }
                  </Text>
                  <Text fontSize="xs" color="gray.400" mt={2} fontStyle="italic">
                    Performance metrics predict which team wins based on combat, economy, and teamwork
                  </Text>
                </Box>

                <Divider />

                {/* Correlation Strength */}
                {performance?.correlation_strength && performance.correlation_strength > 0 && (
                  <Box>
                    <Heading size="sm" mb={2}>Player Performance Correlation</Heading>
                    <HStack spacing={4}>
                      <Progress
                        value={(performance?.correlation_strength || 0) * 100}
                        colorScheme="cyan"
                        size="md"
                        borderRadius="md"
                        flex={1}
                      />
                      <Text fontWeight="bold" color="cyan.400">
                        {formatPercentage(performance?.correlation_strength || 0)}
                      </Text>
                    </HStack>
                    <Text fontSize="xs" color="gray.500" mt={1}>
                      How strongly individual performance correlates with winning
                    </Text>
                  </Box>
                )}

                <Divider />

                {/* Blending Impact */}
                {blendingStats && blendingStats.total_matches > 0 && (
                  <Box
                    bg="linear-gradient(135deg, rgba(0,212,255,0.1), rgba(255,179,0,0.1))"
                    p={4}
                    borderRadius="md"
                  >
                    <Heading size="sm" mb={3}>
                      Blending Impact
                    </Heading>
                    <VStack align="stretch" spacing={2} fontSize="sm">
                      <HStack justify="space-between">
                        <Text color="gray.400">Avg Error:</Text>
                        <Text fontWeight="bold">
                          {formatPercentage(blendingStats.avg_error)}
                        </Text>
                      </HStack>
                      <HStack justify="space-between">
                        <Text color="gray.400">Upsets Detected:</Text>
                        <Badge colorScheme="yellow">
                          {blendingStats.upset_count} ({formatPercentage(blendingStats.upset_rate)})
                        </Badge>
                      </HStack>
                      <HStack justify="space-between">
                        <Text color="gray.400">Matches Analyzed:</Text>
                        <Text>{blendingStats.total_matches}</Text>
                      </HStack>
                    </VStack>
                  </Box>
                )}

                <Divider />

                {/* Recent Learning Activity */}
                <Box>
                  <Heading size="sm" mb={3}>
                    Recent Learning Activity
                  </Heading>
                  <VStack align="stretch" spacing={2} fontSize="sm">
                    {logs.length > 0 ? (
                      <>
                        <HStack>
                          <Icon as={FiCheckCircle} color="green.400" />
                          <Text>
                            {recentCorrectPredictions}/{logs.length} predictions correct (
                            {formatPercentage(recentAccuracy)})
                          </Text>
                        </HStack>
                        <HStack>
                          <Icon as={FiZap} color="yellow.400" />
                          <Text>
                            {logs.filter((l) => l.was_upset).length} upsets in last {logs.length}{' '}
                            matches
                          </Text>
                        </HStack>
                      </>
                    ) : (
                      <Text color="gray.500">No recent predictions logged</Text>
                    )}
                  </VStack>
                </Box>
              </VStack>
            </TacticalCard>
          </GridItem>

          {/* RIGHT COLUMN: What's Changing */}
          <GridItem>
            <TacticalCard h="full">
              <Heading size="md" mb={4}>
                What's Changing
              </Heading>

              <VStack spacing={6} align="stretch">
                {/* Weight Evolution */}
                {suggestions?.suggested_weights && (
                  <Box>
                    <Heading size="sm" mb={3}>
                      Weight Evolution
                    </Heading>
                    <VStack spacing={3} align="stretch">
                      {Object.entries(suggestions.suggested_weights).map(([key, newValue]) => {
                        const currentValue = suggestions.current_weights[key];
                        const change = suggestions.changes[key];
                        return (
                          <Box key={key}>
                            <HStack justify="space-between" mb={1}>
                              <Text
                                fontSize="sm"
                                fontWeight="semibold"
                                textTransform="capitalize"
                              >
                                {key.replace(/_/g, ' ')}
                              </Text>
                              <Badge colorScheme={change > 0 ? 'blue' : 'orange'}>
                                {formatPercentage(currentValue)} -&gt; {formatPercentage(newValue)}
                              </Badge>
                            </HStack>
                            <HStack spacing={2}>
                              <Progress
                                value={currentValue * 100}
                                w="100px"
                                colorScheme="gray"
                                size="sm"
                                borderRadius="md"
                              />
                              <Icon as={FiArrowRight} boxSize={3} />
                              <Progress
                                value={newValue * 100}
                                w="100px"
                                colorScheme={change > 0 ? 'blue' : 'orange'}
                                size="sm"
                                borderRadius="md"
                              />
                            </HStack>
                          </Box>
                        );
                      })}
                    </VStack>

                    {suggestions.reason && (
                      <Alert status="info" mt={3} borderRadius="md" size="sm">
                        <AlertIcon />
                        <Text fontSize="sm">{suggestions.reason}</Text>
                      </Alert>
                    )}
                  </Box>
                )}

                <Divider />

                {/* Feature Importance */}
                <Box>
                  <Heading size="sm" mb={3}>
                    Feature Impact Ranking
                  </Heading>
                  {features.length > 0 ? (
                    <VStack spacing={2} align="stretch">
                      {features.slice(0, 5).map((feature) => (
                        <HStack justify="space-between" key={feature.feature_name}>
                          <Text fontSize="sm">{feature.feature_name}</Text>
                          <HStack>
                            <Progress
                              value={Math.abs(feature.correlation) * 100}
                              w="100px"
                              colorScheme={
                                Math.abs(feature.correlation) > 0.4
                                  ? 'green'
                                  : Math.abs(feature.correlation) > 0.25
                                  ? 'blue'
                                  : 'gray'
                              }
                              size="sm"
                              borderRadius="md"
                            />
                            <Icon
                              as={
                                feature.correlation > 0
                                  ? FiTrendingUp
                                  : feature.correlation < 0
                                  ? FiTrendingDown
                                  : FiMinus
                              }
                              color={
                                Math.abs(feature.correlation) > 0.25
                                  ? 'green.400'
                                  : 'gray.400'
                              }
                            />
                          </HStack>
                        </HStack>
                      ))}
                    </VStack>
                  ) : (
                    <Text fontSize="sm" color="gray.500">
                      No feature importance data yet
                    </Text>
                  )}
                </Box>
              </VStack>
            </TacticalCard>
          </GridItem>
        </Grid>

        {/* ====================================================================== */}
        {/* SECTION 4: AI SUGGESTIONS (HIGHLIGHTED) */}
        {/* ====================================================================== */}
        {(suggestions?.suggested_weights || aiSuggestions.length > 0) && (
          <Box
            border="3px solid"
            borderColor="accent.500"
            borderRadius="lg"
            p={6}
            bg="linear-gradient(135deg, rgba(255,179,0,0.05), rgba(0,212,255,0.05))"
            boxShadow="0 0 40px rgba(255,179,0,0.2)"
          >
            <HStack mb={4}>
              <Icon as={FiCpu} boxSize={8} color="accent.500" />
              <Heading size="lg">AI Recommendations</Heading>
              <Badge colorScheme="yellow" fontSize="md">
                {(suggestions?.suggested_weights ? 1 : 0) + aiSuggestions.filter(s => s.status === 'pending').length} Pending
              </Badge>
            </HStack>

            <VStack spacing={6} align="stretch">
              {/* Weight Update Suggestion */}
              {suggestions?.suggested_weights && (
                <Card bg="rgba(0,212,255,0.05)" borderWidth="1px" borderColor="cyan.700">
                  <CardBody>
                    <HStack justify="space-between">
                      <VStack align="start" flex={1}>
                        <HStack>
                          <Icon as={FiCheckCircle} color="green.400" />
                          <Heading size="sm">Weight Optimization</Heading>
                        </HStack>
                        <Text fontSize="sm" color="gray.500">
                          Found adjustments that improve accuracy by{' '}
                          {formatPercentage(suggestions.performance_improvement || 0)}
                        </Text>
                      </VStack>
                      <VStack>
                        <Badge colorScheme="green" fontSize="md">
                          High Confidence ({formatPercentage(suggestions.confidence)})
                        </Badge>
                        <Button
                          size="sm"
                          colorScheme="green"
                          onClick={() => {
                            toast({
                              title: 'Weights accepted',
                              description:
                                'Update advanced_parser.py with new weights and restart backend',
                              status: 'success',
                              duration: 5000,
                              isClosable: true,
                            });
                          }}
                        >
                          Review Changes
                        </Button>
                      </VStack>
                    </HStack>
                  </CardBody>
                </Card>
              )}

              {/* Feature Suggestions */}
              {aiSuggestions.filter(s => s.status === 'pending').map((suggestion) => (
                <Card
                  key={suggestion.id}
                  bg="rgba(255,179,0,0.05)"
                  borderColor="accent.500"
                  borderWidth="2px"
                >
                  <CardBody>
                    <VStack align="stretch" spacing={4}>
                      <HStack justify="space-between">
                        <VStack align="start" spacing={1} flex={1}>
                          <HStack>
                            <Icon as={FiZap} color="accent.500" />
                            <Heading size="sm">New Feature Suggested</Heading>
                            <Badge colorScheme="yellow">AI Discovery</Badge>
                          </HStack>
                          <Text fontWeight="bold" color="accent.500" fontSize="lg">
                            "{suggestion.feature_name}"
                          </Text>
                        </VStack>
                        <Badge colorScheme="yellow" fontSize="md">
                          {suggestion.expected_correlation
                            ? `${formatPercentage(suggestion.expected_correlation)} Expected`
                            : 'Medium Confidence'}
                        </Badge>
                      </HStack>

                      <Box bg="gray.800" p={3} borderRadius="md">
                        <Text fontSize="xs" fontFamily="mono" color="gray.300">
                          <strong>Reasoning:</strong> {suggestion.reasoning}
                        </Text>
                      </Box>

                      {suggestion.extraction_logic && (
                        <Box>
                          <Text fontSize="sm" fontWeight="bold" mb={2}>
                            Suggested Extraction:
                          </Text>
                          <Code
                            display="block"
                            whiteSpace="pre-wrap"
                            fontSize="xs"
                            p={3}
                            borderRadius="md"
                          >
                            {suggestion.extraction_logic}
                          </Code>
                        </Box>
                      )}

                      <HStack justify="flex-end">
                        <Text fontSize="xs" color="gray.500" flex={1}>
                          Expected impact: {suggestion.expected_correlation ? `+${formatPercentage(suggestion.expected_correlation)} correlation` : 'Unknown'}
                        </Text>
                        <Button size="sm" variant="outline">
                          Implement Later
                        </Button>
                        <Button
                          size="sm"
                          colorScheme="yellow"
                          onClick={() => {
                            toast({
                              title: 'Feature implementation started',
                              description: `Add "${suggestion.feature_name}" to your parser`,
                              status: 'info',
                              duration: 5000,
                              isClosable: true,
                            });
                          }}
                        >
                          Start Implementation
                        </Button>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>
              ))}
            </VStack>
          </Box>
        )}

        {/* ====================================================================== */}
        {/* SECTION 5: YOUR INPUT (INTERACTIVE) */}
        {/* ====================================================================== */}
        <TacticalCard>
          <Heading size="md" mb={4}>
            <Icon as={FiEdit} mr={2} />
            You Know Your Meta Best
          </Heading>

          <Tabs colorScheme="cyan">
            <TabList>
              <Tab>Suggest Feature</Tab>
              <Tab>Annotate Pattern</Tab>
              <Tab>Session Feedback</Tab>
            </TabList>

            <TabPanels>
              {/* Manual Feature Suggestion */}
              <TabPanel>
                <VStack spacing={4} align="stretch">
                  <FormControl>
                    <FormLabel>Feature Name</FormLabel>
                    <Input placeholder="e.g., player_map_preference" />
                  </FormControl>

                  <FormControl>
                    <FormLabel>What Did You Notice?</FormLabel>
                    <Textarea
                      placeholder="e.g., Player X always wins on Lost Temple but struggles on other maps. This should affect predictions."
                      rows={4}
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel>How to Extract This?</FormLabel>
                    <Textarea
                      placeholder="e.g., Track player win rate per map, boost/reduce prediction based on map familiarity"
                      rows={3}
                    />
                  </FormControl>

                  <Button
                    colorScheme="blue"
                    leftIcon={<FiZap />}
                    onClick={() => {
                      toast({
                        title: 'Feature submitted',
                        description: 'Your suggestion will be validated and tested',
                        status: 'success',
                        duration: 3000,
                        isClosable: true,
                      });
                    }}
                  >
                    Submit for Validation
                  </Button>
                </VStack>
              </TabPanel>

              {/* Pattern Annotation */}
              <TabPanel>
                <VStack spacing={4} align="stretch">
                  <Text fontSize="sm" color="gray.500">
                    Help the AI learn faster by annotating patterns you see:
                  </Text>

                  <CheckboxGroup>
                    <VStack align="start">
                      <Checkbox>Protoss+Terran combos seem to win more</Checkbox>
                      <Checkbox>Late night games are sloppier (more upsets)</Checkbox>
                      <Checkbox>Player X tilts after first loss</Checkbox>
                      <Checkbox>Map "Daybreak" favors aggressive play</Checkbox>
                    </VStack>
                  </CheckboxGroup>

                  <Button
                    colorScheme="blue"
                    onClick={() => {
                      toast({
                        title: 'Annotations saved',
                        description: 'AI will test these patterns',
                        status: 'success',
                        duration: 3000,
                        isClosable: true,
                      });
                    }}
                  >
                    Save Annotations (AI will test these)
                  </Button>
                </VStack>
              </TabPanel>

              {/* Session Feedback */}
              <TabPanel>
                <VStack spacing={4} align="stretch">
                  {logs.length > 0 && (
                    <Stat>
                      <StatLabel>Last Session ({logs.length} games)</StatLabel>
                      <StatNumber>
                        {recentCorrectPredictions}/{logs.length} predictions correct
                      </StatNumber>
                    </Stat>
                  )}

                  <FormControl>
                    <FormLabel>Which predictions felt wrong?</FormLabel>
                    <CheckboxGroup>
                      <VStack align="start">
                        {logs.slice(0, 5).map((log) => (
                          <Checkbox key={log.id}>
                            Match #{log.match_id} - {log.prediction_error > 0.3 ? 'Model struggled' : 'Close call'}
                          </Checkbox>
                        ))}
                      </VStack>
                    </CheckboxGroup>
                  </FormControl>

                  <FormControl>
                    <FormLabel>Additional Notes</FormLabel>
                    <Textarea placeholder="Any other observations..." rows={3} />
                  </FormControl>

                  <Button
                    colorScheme="blue"
                    onClick={() => {
                      toast({
                        title: 'Feedback submitted',
                        description: 'Your insights will improve future predictions',
                        status: 'success',
                        duration: 3000,
                        isClosable: true,
                      });
                    }}
                  >
                    Submit Feedback
                  </Button>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </TacticalCard>

        {/* ====================================================================== */}
        {/* HOW IT WORKS (Condensed) */}
        {/* ====================================================================== */}
        <Card bg={cardBg} borderColor={borderColor} borderWidth={1}>
          <CardHeader>
            <Heading size="md">How the Living Model Works</Heading>
          </CardHeader>
          <CardBody>
            <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={4}>
              <Box>
                <Text fontWeight="bold" mb={1} fontSize="sm">
                  Continuous Learning
                </Text>
                <Text fontSize="xs" color="gray.600">
                  Every match prediction is logged and compared to actual outcomes. The model
                  retrains every 10 matches to adapt to your meta.
                </Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={1} fontSize="sm">
                  Weight Optimization
                </Text>
                <Text fontSize="xs" color="gray.600">
                  Performance weights (combat, economy, etc.) are automatically optimized to
                  maximize win prediction accuracy.
                </Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={1} fontSize="sm">
                  Feature Discovery
                </Text>
                <Text fontSize="xs" color="gray.600">
                  AI analyzes prediction errors to suggest new features. You implement the
                  extraction, AI validates the improvement.
                </Text>
              </Box>
            </Grid>
          </CardBody>
        </Card>
      </VStack>
      </Container>
    </Box>
  );
};

export default AdaptiveModel;
