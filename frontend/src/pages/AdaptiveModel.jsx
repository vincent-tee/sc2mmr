/**
 * Adaptive Model Page
 * Visualize self-improving model performance and suggested weight updates
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
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  useColorModeValue,
  Icon,
  Tooltip,
  Code,
  useToast,
  Divider,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FiCpu,
  FiTrendingUp,
  FiCheckCircle,
  FiAlertCircle,
  FiRefreshCw,
  FiInfo,
} from 'react-icons/fi';
import { apiClient } from '../api/client';
import LoadingState from '../components/LoadingState';
import TacticalCard from '../components/TacticalCard';

const AdaptiveModel = () => {
  const [acceptingUpdate, setAcceptingUpdate] = useState(false);
  const toast = useToast();
  const queryClient = useQueryClient();

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Fetch weight suggestions
  const { data: suggestions, isLoading: suggestionsLoading, refetch: refetchSuggestions, isFetching: suggestionsFetching } = useQuery({
    queryKey: ['adaptive-suggestions'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/suggest-weights');
      return response.data;
    },
    staleTime: 0, // Always fetch fresh data
    cacheTime: 0, // Don't cache
  });

  // Fetch model performance
  const { data: performance, isLoading: performanceLoading, refetch: refetchPerformance, isFetching: performanceFetching } = useQuery({
    queryKey: ['model-performance'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/model-performance');
      return response.data;
    },
    staleTime: 0, // Always fetch fresh data
    cacheTime: 0, // Don't cache
  });

  const getSuggestionStatus = (suggestion) => {
    switch (suggestion) {
      case 'update_recommended':
        return 'success';
      case 'no_change_needed':
        return 'info';
      case 'insufficient_data':
        return 'warning';
      default:
        return 'info';
    }
  };

  const getSuggestionIcon = (suggestion) => {
    switch (suggestion) {
      case 'update_recommended':
        return FiCheckCircle;
      case 'no_change_needed':
        return FiInfo;
      case 'insufficient_data':
        return FiAlertCircle;
      default:
        return FiInfo;
    }
  };

  const formatPercentage = (value) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatChange = (value) => {
    const formatted = formatPercentage(value);
    return value > 0 ? `+${formatted}` : formatted;
  };

  if (suggestionsLoading || performanceLoading) {
    return <LoadingState message="Analyzing model performance..." />;
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <HStack spacing={3} mb={2}>
            <Icon as={FiCpu} boxSize={8} color="purple.500" />
            <Heading size="xl">Adaptive Model Performance</Heading>
          </HStack>
          <Text color="gray.500" fontSize="lg">
            Self-improving model that optimizes performance weights based on match outcomes
          </Text>
        </Box>

        {/* Status Banner */}
        <Alert
          status={getSuggestionStatus(suggestions?.suggestion)}
          variant="left-accent"
          borderRadius="md"
        >
          <AlertIcon as={getSuggestionIcon(suggestions?.suggestion)} />
          <Box flex="1">
            <AlertTitle textTransform="capitalize">
              {suggestions?.suggestion?.replace(/_/g, ' ')}
            </AlertTitle>
            <AlertDescription>{suggestions?.reason}</AlertDescription>
          </Box>
          <Button
            leftIcon={<FiRefreshCw />}
            size="sm"
            variant="ghost"
            isLoading={suggestionsFetching || performanceFetching}
            loadingText="Analyzing..."
            onClick={async () => {
              try {
                await Promise.all([
                  refetchSuggestions(),
                  refetchPerformance()
                ]);
                toast({
                  title: 'Analysis refreshed',
                  description: 'Model performance recalculated from latest match data',
                  status: 'success',
                  duration: 3000,
                  isClosable: true,
                });
              } catch (error) {
                toast({
                  title: 'Refresh failed',
                  description: error.message || 'Failed to refresh analysis',
                  status: 'error',
                  duration: 5000,
                  isClosable: true,
                });
              }
            }}
          >
            Refresh Analysis
          </Button>
        </Alert>

        <HStack spacing={6} align="stretch">
          {/* Model Performance Stats */}
          <TacticalCard flex={1}>
            <Box mb={4}>
              <Heading size="md">Model Performance</Heading>
            </Box>
            <VStack spacing={4} align="stretch">
                <Stat>
                  <StatLabel>Win Prediction Accuracy</StatLabel>
                  <StatNumber fontSize="3xl">
                    {formatPercentage(performance?.win_prediction_accuracy || 0)}
                  </StatNumber>
                  <StatHelpText>
                    Correlation between performance and wins
                  </StatHelpText>
                </Stat>

                <Divider />

                <Stat>
                  <StatLabel>Sample Size</StatLabel>
                  <StatNumber>{performance?.sample_size || 0}</StatNumber>
                  <StatHelpText>Matches analyzed</StatHelpText>
                </Stat>

                <Divider />

                <Stat>
                  <StatLabel>Confidence Score</StatLabel>
                  <StatNumber>
                    <HStack>
                      <Text>{formatPercentage(performance?.confidence_score || 0)}</Text>
                      <Badge
                        colorScheme={
                          (performance?.confidence_score || 0) > 0.75
                            ? 'green'
                            : (performance?.confidence_score || 0) > 0.5
                            ? 'yellow'
                            : 'red'
                        }
                      >
                        {(performance?.confidence_score || 0) > 0.75
                          ? 'High'
                          : (performance?.confidence_score || 0) > 0.5
                          ? 'Medium'
                          : 'Low'}
                      </Badge>
                    </HStack>
                  </StatNumber>
                  <StatHelpText>Model reliability</StatHelpText>
                </Stat>

                <Progress
                  value={(performance?.confidence_score || 0) * 100}
                  colorScheme={
                    (performance?.confidence_score || 0) > 0.75
                      ? 'green'
                      : (performance?.confidence_score || 0) > 0.5
                      ? 'yellow'
                      : 'red'
                  }
                  size="sm"
                  borderRadius="md"
                />
            </VStack>
          </TacticalCard>

          {/* Current Weights */}
          <TacticalCard flex={1}>
            <Box mb={4}>
              <Heading size="md">Current Weights</Heading>
            </Box>
            <VStack spacing={4} align="stretch">
                {suggestions?.current_weights &&
                  Object.entries(suggestions.current_weights).map(([key, value]) => (
                    <Box key={key}>
                      <HStack justify="space-between" mb={1}>
                        <Text fontWeight="semibold" textTransform="capitalize">
                          {key.replace(/_/g, ' ')}
                        </Text>
                        <Code>{formatPercentage(value)}</Code>
                      </HStack>
                      <Progress
                        value={value * 100}
                        colorScheme="blue"
                        size="sm"
                        borderRadius="md"
                      />
                    </Box>
                  ))}
            </VStack>
          </TacticalCard>
        </HStack>

        {/* Suggested Updates */}
        {suggestions?.suggested_weights && (
          <TacticalCard>
            <Box mb={4}>
              <HStack justify="space-between">
                <Heading size="md">Suggested Weight Updates</Heading>
                <Badge
                  colorScheme="green"
                  fontSize="md"
                  px={3}
                  py={1}
                  borderRadius="md"
                >
                  {formatPercentage(suggestions.confidence)} Confidence
                </Badge>
              </HStack>
            </Box>
            <VStack spacing={6} align="stretch">
                <Alert status="info" borderRadius="md">
                  <AlertIcon />
                  <Box>
                    <AlertDescription>
                      The model analyzed <Code>{suggestions.sample_size}</Code> recent
                      matches and found weight adjustments that improve win prediction by{' '}
                      <Code>
                        {formatPercentage(suggestions.performance_improvement || 0)}
                      </Code>
                      .
                    </AlertDescription>
                  </Box>
                </Alert>

                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Metric</Th>
                      <Th isNumeric>Current</Th>
                      <Th isNumeric>Suggested</Th>
                      <Th isNumeric>Change</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {Object.entries(suggestions.suggested_weights).map(([key, value]) => {
                      const current = suggestions.current_weights[key];
                      const change = suggestions.changes[key];
                      return (
                        <Tr key={key}>
                          <Td fontWeight="semibold" textTransform="capitalize">
                            {key.replace(/_/g, ' ')}
                          </Td>
                          <Td isNumeric>
                            <Code>{formatPercentage(current)}</Code>
                          </Td>
                          <Td isNumeric>
                            <Code>{formatPercentage(value)}</Code>
                          </Td>
                          <Td isNumeric>
                            <HStack justify="flex-end">
                              <StatArrow
                                type={change > 0 ? 'increase' : 'decrease'}
                              />
                              <Code
                                colorScheme={change > 0 ? 'green' : 'red'}
                              >
                                {formatChange(change)}
                              </Code>
                            </HStack>
                          </Td>
                        </Tr>
                      );
                    })}
                  </Tbody>
                </Table>

                <Alert status="warning" borderRadius="md">
                  <AlertIcon />
                  <Box fontSize="sm">
                    <AlertDescription>
                      <strong>Note:</strong> Weight updates are currently manual and
                      require restarting the backend service. Automatic application
                      coming soon via config system.
                    </AlertDescription>
                  </Box>
                </Alert>

                <HStack justify="flex-end">
                  <Button
                    variant="ghost"
                    onClick={() => toast({
                      title: 'Changes discarded',
                      status: 'info',
                      duration: 2000,
                    })}
                  >
                    Dismiss
                  </Button>
                  <Tooltip label="Accepts suggested weights (manual update required)">
                    <Button
                      colorScheme="green"
                      leftIcon={<FiCheckCircle />}
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
                      Accept Suggested Weights
                    </Button>
                  </Tooltip>
                </HStack>
            </VStack>
          </TacticalCard>
        )}

        {/* How It Works */}
        <Card bg={cardBg} borderColor={borderColor} borderWidth={1}>
          <CardHeader>
            <Heading size="md">How the Adaptive Model Works</Heading>
          </CardHeader>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Box>
                <Text fontWeight="bold" mb={2}>
                  1. Data Collection
                </Text>
                <Text fontSize="sm" color="gray.600">
                  The system analyzes recent matches ({suggestions?.sample_size || 0}{' '}
                  matches), examining player performance metrics and match outcomes.
                </Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={2}>
                  2. Correlation Analysis
                </Text>
                <Text fontSize="sm" color="gray.600">
                  It calculates how well each performance metric (combat, economy, team
                  contribution, efficiency) predicts winning. Metrics with stronger
                  correlation get higher weights.
                </Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={2}>
                  3. Optimization
                </Text>
                <Text fontSize="sm" color="gray.600">
                  Using gradient-free optimization (Nelder-Mead), the system finds weights
                  that maximize win prediction accuracy on a training set.
                </Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={2}>
                  4. Validation
                </Text>
                <Text fontSize="sm" color="gray.600">
                  The optimized weights are tested on held-out matches (20% validation
                  split) to ensure they generalize well and aren't overfitting.
                </Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={2}>
                  5. Confidence Scoring
                </Text>
                <Text fontSize="sm" color="gray.600">
                  Only suggests changes when confidence is high (75%+), based on sample
                  size and validation performance. Prevents noisy updates from small
                  datasets.
                </Text>
              </Box>
            </VStack>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};

export default AdaptiveModel;
