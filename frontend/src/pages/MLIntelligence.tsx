/**
 * ML Intelligence Center
 * Displays model accuracy trends, SHAP importance, and model management tools.
 */
import React, { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  Grid,
  GridItem,
  Icon,
  Badge,
  useToast,
  useColorModeValue,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Divider,
  Alert,
  AlertIcon,
  Tooltip,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import {
  FiCpu,
  FiTrendingUp,
  FiActivity,
  FiZap,
  FiInfo,
  FiRefreshCw,
  FiBarChart2,
  FiTarget,
} from 'react-icons/fi';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { adaptiveApi } from '../api/endpoints';
import LoadingState from '../components/LoadingState';
import TacticalCard from '../components/TacticalCard';
import TacticalBackground from '../components/common/TacticalBackground';

const MLIntelligence: React.FC = () => {
  const [isTraining, setIsTraining] = useState(false);
  const toast = useToast();
  
  const cyanGlow = 'rgba(0, 212, 255, 0.5)';
  const purpleGlow = 'rgba(128, 0, 255, 0.5)';
  const orangeGlow = 'rgba(255, 140, 26, 0.5)';

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const { data: accuracyData, isLoading: accuracyLoading, refetch: refetchAccuracy } = useQuery({
    queryKey: ['ml-accuracy-trends'],
    queryFn: async () => {
      const response = await adaptiveApi.getAccuracyComparison(180); // Last 6 months
      return response.data;
    },
  });

  const { data: shapData, isLoading: shapLoading, refetch: refetchShap } = useQuery({
    queryKey: ['ml-shap-importance'],
    queryFn: async () => {
      const response = await adaptiveApi.getShapImportance();
      return response.data;
    },
  });

  const { data: modelStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['ml-model-status'],
    queryFn: async () => {
      const response = await adaptiveApi.getMLModelsStatus();
      return response.data;
    },
  });

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleRetrain = async () => {
    setIsTraining(true);
    try {
      const response = await adaptiveApi.trainXGBoost();
      if (response.data.status === 'success') {
        toast({
          title: 'Model Retrained Successfully',
          description: `New accuracy: ${response.data.test_accuracy}%`,
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
        refetchAccuracy();
        refetchShap();
        refetchStatus();
      } else {
        toast({
          title: 'Retraining Incomplete',
          description: 'Not enough new data since last training.',
          status: 'warning',
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (error) {
      toast({
        title: 'Retraining Failed',
        description: 'An error occurred while communicating with the neural core.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsTraining(false);
    }
  };

  // ============================================================================
  // Rendering Helpers
  // ============================================================================

  if (accuracyLoading || shapLoading || statusLoading) {
    return <LoadingState message="Connecting to neural core..." />;
  }

  const trends = accuracyData?.trends || [];
  const shapFeatures = shapData?.features || [];
  const trueskillFinal = accuracyData?.results?.trueskill?.total > 0 
    ? (accuracyData.results.trueskill.correct / accuracyData.results.trueskill.total) * 100 
    : 0;
  const hybridFinal = accuracyData?.results?.hybrid?.total > 0 
    ? (accuracyData.results.hybrid.correct / accuracyData.results.hybrid.total) * 100 
    : 0;

  return (
    <Box position="relative" minH="100vh" pb={10}>
      <TacticalBackground opacity={0.05} gridSize={40} variant="cyan" />
      
      <Container maxW="container.xl" pt={8}>
        <VStack spacing={8} align="stretch">
          {/* Header Section */}
          <HStack justify="space-between" align="flex-end">
            <VStack align="start" spacing={1}>
              <HStack spacing={3}>
                <Icon as={FiCpu} boxSize={8} color="cyan.400" />
                <Heading size="xl" fontFamily="heading" letterSpacing="wider">
                  ML INTELLIGENCE
                </Heading>
                <Badge colorScheme="cyan" variant="outline" px={2}>PHASE 2 ACTIVE</Badge>
              </HStack>
              <Text color="gray.400" fontSize="md">
                Strategic analysis and predictive model performance monitoring.
              </Text>
            </VStack>
            
            <HStack spacing={4}>
              <Tooltip label="Refresh all neural data">
                <Button 
                  leftIcon={<FiRefreshCw />} 
                  variant="ghost" 
                  colorScheme="cyan" 
                  size="sm"
                  onClick={() => {
                    refetchAccuracy();
                    refetchShap();
                    refetchStatus();
                  }}
                >
                  Sync Core
                </Button>
              </Tooltip>
              <Button
                leftIcon={<FiZap />}
                colorScheme="purple"
                size="md"
                isLoading={isTraining}
                loadingText="Retraining..."
                onClick={handleRetrain}
                boxShadow={`0 0 15px ${purpleGlow}`}
              >
                Retrain Model
              </Button>
            </HStack>
          </HStack>

          <Divider borderColor="whiteAlpha.200" />

          {/* Quick Stats Grid */}
          <Grid templateColumns={{ base: '1fr', md: 'repeat(4, 1fr)' }} gap={4}>
            <GridItem>
              <TacticalCard variant="command" glowColor="cyan.500">
                <Stat>
                  <StatLabel color="gray.400">Hybrid Accuracy</StatLabel>
                  <StatNumber color="cyan.400" fontSize="3xl">
                    {hybridFinal.toFixed(1)}%
                  </StatNumber>
                  <StatHelpText>
                    <StatArrow type={hybridFinal > trueskillFinal ? "increase" : "decrease"} />
                    vs Baseline
                  </StatHelpText>
                </Stat>
              </TacticalCard>
            </GridItem>
            <GridItem>
              <TacticalCard variant="command" glowColor="purple.500">
                <Stat>
                  <StatLabel color="gray.400">TrueSkill Baseline</StatLabel>
                  <StatNumber color="purple.400" fontSize="3xl">
                    {trueskillFinal.toFixed(1)}%
                  </StatNumber>
                  <StatHelpText>Standard Rating</StatHelpText>
                </Stat>
              </TacticalCard>
            </GridItem>
            <GridItem>
              <TacticalCard variant="command" glowColor="orange.500">
                <Stat>
                  <StatLabel color="gray.400">Total Samples</StatLabel>
                  <StatNumber color="orange.400" fontSize="3xl">
                    {accuracyData?.total_matches || 0}
                  </StatNumber>
                  <StatHelpText>Match Records</StatHelpText>
                </Stat>
              </TacticalCard>
            </GridItem>
            <GridItem>
              <TacticalCard variant="command" glowColor="green.500">
                <Stat>
                  <StatLabel color="gray.400">Model Status</StatLabel>
                  <StatNumber color="green.400" fontSize="xl" mt={2}>
                    {modelStatus?.xgboost?.is_trained ? "OPTIMIZED" : "INITIALIZING"}
                  </StatNumber>
                  <StatHelpText>XGBoost Core</StatHelpText>
                </Stat>
              </TacticalCard>
            </GridItem>
          </Grid>

          <Grid templateColumns={{ base: '1fr', lg: '3fr 2fr' }} gap={6}>
            {/* Accuracy Trends Chart */}
            <GridItem>
              <TacticalCard h="full">
                <VStack align="stretch" spacing={6}>
                  <HStack justify="space-between">
                    <HStack>
                      <Icon as={FiTrendingUp} color="cyan.400" />
                      <Heading size="md" fontFamily="heading">ACCURACY TRENDS</Heading>
                    </HStack>
                    <Badge colorScheme="cyan">6 MONTH WINDOW</Badge>
                  </HStack>
                  
                  {trends.length < 2 ? (
                    <Box h="300px" display="flex" alignItems="center" justifyContent="center">
                      <Alert status="info" variant="subtle" bg="transparent" borderColor="cyan.800" borderWidth={1}>
                        <AlertIcon color="cyan.400" />
                        <Text color="gray.400">Insufficient data for trend analysis. Collect more matches.</Text>
                      </Alert>
                    </Box>
                  ) : (
                    <Box h="400px" w="100%">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trends}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis 
                            dataKey="date" 
                            stroke="rgba(255,255,255,0.5)" 
                            tick={{ fontSize: 10 }}
                            tickFormatter={(str) => str.split('-').slice(1).join('/')}
                          />
                          <YAxis 
                            stroke="rgba(255,255,255,0.5)" 
                            domain={[0.4, 1]}
                            tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                          />
                          <RechartsTooltip 
                            contentStyle={{ backgroundColor: '#0d1121', borderColor: '#00d4ff', color: '#fff' }}
                            itemStyle={{ color: '#00d4ff' }}
                          />
                          <Legend />
                          <Line 
                            type="monotone" 
                            dataKey="hybrid_accuracy" 
                            name="XGBoost Hybrid" 
                            stroke="#00d4ff" 
                            strokeWidth={3}
                            dot={{ fill: '#00d4ff', r: 4 }}
                            activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
                          />
                          <Line 
                            type="monotone" 
                            dataKey="trueskill_accuracy" 
                            name="TrueSkill Baseline" 
                            stroke="#8000ff" 
                            strokeWidth={2}
                            strokeDasharray="5 5"
                            dot={{ fill: '#8000ff', r: 3 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </Box>
                  )}
                  
                  <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderLeft="4px solid" borderColor="cyan.400">
                    <HStack>
                      <Icon as={FiInfo} color="cyan.400" />
                      <Text fontSize="sm" color="gray.300">
                        Accuracy represents the percentage of matches where the model correctly identified the winning team before the match started.
                      </Text>
                    </HStack>
                  </Box>
                </VStack>
              </TacticalCard>
            </GridItem>

            {/* Feature Importance Chart */}
            <GridItem>
              <TacticalCard h="full" glowColor="purple.500">
                <VStack align="stretch" spacing={6}>
                  <HStack justify="space-between">
                    <HStack>
                      <Icon as={FiBarChart2} color="purple.400" />
                      <Heading size="md" fontFamily="heading">SHAP IMPORTANCE</Heading>
                    </HStack>
                    <Tooltip label="SHAP values show which features impact predictions the most.">
                      <Icon as={FiInfo} color="gray.500" />
                    </Tooltip>
                  </HStack>

                  {shapFeatures.length === 0 ? (
                    <Box h="300px" display="flex" alignItems="center" justifyContent="center">
                      <Text color="gray.500">No importance data available.</Text>
                    </Box>
                  ) : (
                    <Box h="450px" w="100%">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={shapFeatures.slice(0, 10)}
                          layout="vertical"
                          margin={{ left: 40 }}
                        >
                          <XAxis type="number" hide />
                          <YAxis 
                            dataKey="feature" 
                            type="category" 
                            stroke="rgba(255,255,255,0.7)"
                            tick={{ fontSize: 11 }}
                            width={100}
                            tickFormatter={(str) => str.replace(/_/g, ' ').replace('diff', '').toUpperCase()}
                          />
                          <RechartsTooltip 
                            contentStyle={{ backgroundColor: '#0d1121', borderColor: '#8000ff', color: '#fff' }}
                            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                          />
                          <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                            {shapFeatures.map((entry, index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={index < 3 ? '#00d4ff' : index < 6 ? '#8000ff' : '#4a5568'} 
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </Box>
                  )}

                  <VStack align="stretch" spacing={2}>
                    <Text fontSize="xs" fontWeight="bold" color="gray.500">KEY DRIVERS</Text>
                    {shapFeatures.slice(0, 3).map((f, i) => (
                      <HStack key={f.feature} justify="space-between">
                        <HStack>
                          <Badge colorScheme={i === 0 ? 'cyan' : 'purple'} variant="solid" size="sm">{i+1}</Badge>
                          <Text fontSize="sm" color="gray.300">{f.feature.replace(/_/g, ' ').toUpperCase()}</Text>
                        </HStack>
                        <Text fontSize="xs" color="gray.500">{(f.importance * 100).toFixed(1)}%</Text>
                      </HStack>
                    ))}
                  </VStack>
                </VStack>
              </TacticalCard>
            </GridItem>
          </Grid>

          {/* Model Controls Card */}
          <TacticalCard variant="angled" glowColor="orange.500">
            <HStack justify="space-between">
              <VStack align="start" spacing={1}>
                <HStack>
                  <Icon as={FiTarget} color="orange.400" />
                  <Heading size="md" fontFamily="heading">MODEL MANAGEMENT</Heading>
                </HStack>
                <Text color="gray.400" fontSize="sm">
                  Neural core maintains historical weights. Manual retraining recommended after 50+ new matches.
                </Text>
              </VStack>
              <HStack spacing={6}>
                <VStack align="end" spacing={0}>
                  <Text fontSize="xs" color="gray.500">LAST OPTIMIZATION</Text>
                  <Text fontWeight="bold" color="orange.400">24H AGO</Text>
                </VStack>
                <Divider orientation="vertical" h="40px" />
                <VStack align="end" spacing={0}>
                  <Text fontSize="xs" color="gray.500">DATASET SIZE</Text>
                  <Text fontWeight="bold" color="cyan.400">{accuracyData?.total_matches || 0} MATCHES</Text>
                </VStack>
              </HStack>
            </HStack>
          </TacticalCard>
        </VStack>
      </Container>
    </Box>
  );
};

export default MLIntelligence;
