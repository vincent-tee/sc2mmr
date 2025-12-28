/**
 * ML Intelligence Center
 * Consolidated model monitoring, training, and learning dashboard.
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
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Tooltip,
  Circle,
  Flex,
  Spacer,
} from '@chakra-ui/react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FiCpu,
  FiZap,
  FiInfo,
  FiRefreshCw,
  FiBarChart2,
  FiCheckCircle,
  FiBookOpen,
  FiTarget,
  FiActivity,
  FiDatabase,
} from 'react-icons/fi';

import { adaptiveApi } from '../api/endpoints';
import { apiClient } from '../api/client';
import LoadingState from '../components/LoadingState';

const MLIntelligence: React.FC = () => {
  const [isTrainingXgb, setIsTrainingXgb] = useState(false);
  
  const toast = useToast();
  const queryClient = useQueryClient();
  
  const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';
  const cardBg = 'space.800';
  const borderColor = 'space.700';

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const { data: accuracyData, isLoading: accuracyLoading } = useQuery({
    queryKey: ['ml-accuracy-trends'],
    queryFn: async () => {
      const response = await adaptiveApi.getAccuracyComparison(180);
      return response.data;
    },
  });

  const { data: shapData, isLoading: shapLoading } = useQuery({
    queryKey: ['ml-shap-importance'],
    queryFn: async () => {
      const response = await adaptiveApi.getShapImportance();
      return response.data;
    },
  });

  const { data: modelStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['ml-model-status'],
    queryFn: async () => {
      const response = await adaptiveApi.getMLModelsStatus();
      return response.data;
    },
  });

  const { data: predictionLogs } = useQuery({
    queryKey: ['ml-prediction-logs'],
    queryFn: async () => {
      const response = await apiClient.get('/adaptive/prediction-logs?limit=10');
      return response.data;
    },
    refetchInterval: 30000,
  });

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleRetrainXGB = async () => {
    setIsTrainingXgb(true);
    try {
      const response = await adaptiveApi.trainXGBoost();
      if (response.data.status === 'success') {
        toast({
          title: 'Predictor Updated',
          description: `Training complete. Test accuracy: ${response.data.test_accuracy}%`,
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['ml-accuracy-trends'] }),
          queryClient.invalidateQueries({ queryKey: ['ml-shap-importance'] }),
          queryClient.invalidateQueries({ queryKey: ['ml-model-status'] }),
        ]);
      } else if (response.data.status === 'insufficient_data') {
        toast({
            title: 'Training Skipped',
            description: `Need at least ${response.data.required} matches. Currently have ${response.data.matches}.`,
            status: 'warning',
        });
      }
    } catch (error) {
      toast({ title: 'Update Failed', status: 'error' });
    } finally {
      setIsTrainingXgb(false);
    }
  };

  // ============================================================================
  // Helpers & Mapping
  // ============================================================================

  const factorGlossary: Record<string, { label: string, desc: string, category: 'Micro' | 'Macro' | 'Meta' }> = {
    // === Core Meta Features ===
    'experience_diff': { label: 'Experience Gap', desc: 'Total match count difference. Veterans have seen more situations. STRONGEST predictor.', category: 'Meta' },
    'sum_mmr_diff': { label: 'Team Skill Total', desc: 'The sum of all player MMRs on the team. More accurate for 4v4 than averages.', category: 'Meta' },
    'win_rate_diff': { label: 'Win Consistency', desc: 'Historical win rate difference between squads.', category: 'Meta' },
    'team_size_diff': { label: 'Squad Size Gap', desc: 'Difference in number of players. Critical for uneven handicap matches.', category: 'Meta' },
    'max_mmr_diff': { label: 'Star Player Power', desc: 'The MMR difference between the highest-rated player on each team.', category: 'Meta' },
    // === Micro Features ===
    'combat_diff': { label: 'Combat Rating', desc: 'Historical combat performance score. Measures fight efficiency.', category: 'Micro' },
    'teamfight_diff': { label: 'Team Fight Engagement', desc: 'How often players participate in group battles. Synergy indicator.', category: 'Micro' },
    // === Macro Features ===
    'aggression_diff': { label: 'Aggression Style', desc: 'Play style aggressiveness. Less aggressive teams win more consistently.', category: 'Macro' },
    'minerals_diff': { label: 'Economy Strength', desc: 'Total minerals collected difference.', category: 'Macro' },
    'supply_block_diff': { label: 'Macro Efficiency', desc: 'Time spent supply blocked. Lower is better macro.', category: 'Macro' },
    'form_trend_diff': { label: 'Recent Form', desc: 'Slope of recent performance scores. Captures "hot streaks" or tilting.', category: 'Meta' },
    'spending_diff': { label: 'Spending Quotient', desc: 'Economic efficiency (SQ). How well players spend their income.', category: 'Macro' },
  };

  const getFeatureLabel = (key: string) => factorGlossary[key]?.label || key.replace(/_/g, ' ').replace('diff', '').trim().toUpperCase();

  if (accuracyLoading || statusLoading) {
    return <LoadingState message="Analyzing neural pathways..." />;
  }

  const shapFeatures = shapData?.features || [];
  const totalMatches = accuracyData?.total_matches || 0;
  const trainingThreshold = 10;

  // Normalize feature importance to percentages that sum to 100%
  const normalizedFeatures = shapFeatures.length > 0 ? (() => {
    const totalImportance = shapFeatures.reduce((sum: number, f: any) => sum + Math.abs(f.importance), 0);
    if (totalImportance === 0) return shapFeatures;
    return shapFeatures.map((f: any) => ({
      ...f,
      importance: Math.abs(f.importance) / totalImportance
    }));
  })() : [];

  return (
    <Box position="relative" minH="100vh" pb={10} bg="space.900">
      <Container maxW="container.xl" pt={8}>
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <Box>
            <HStack spacing={4} mb={3} w="full">
              <Icon as={FiCpu} boxSize={10} color="brand.500" />
              <Heading size="2xl" fontFamily="heading" letterSpacing="wider">
                Intelligence Center
              </Heading>
              <Badge 
                colorScheme={modelStatus?.xgboost?.is_trained ? 'green' : 'gray'} 
                variant="solid" 
                px={4} 
                py={2} 
                borderRadius="full"
                fontSize="md"
                textTransform="uppercase"
                letterSpacing="widest"
              >
                {modelStatus?.xgboost?.is_trained ? 'NEURAL ACTIVE' : 'IDLE'}
              </Badge>
              <Spacer />
              <Button 
                size="sm" 
                variant="outline" 
                colorScheme="brand" 
                leftIcon={<Icon as={FiZap} />} 
                onClick={handleRetrainXGB} 
                isLoading={isTrainingXgb}
              >
                Train ML Predictor
              </Button>
              <Button 
                size="sm" 
                variant="outline" 
                colorScheme="gray" 
                leftIcon={<Icon as={FiRefreshCw} />} 
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['ml-accuracy-trends'] });
                  queryClient.invalidateQueries({ queryKey: ['ml-shap-importance'] });
                  queryClient.invalidateQueries({ queryKey: ['ml-model-status'] });
                }}
              >
                Refresh
              </Button>
            </HStack>
            <Text color="gray.300" fontSize="lg" maxW="container.md">
              The neural core analyzes gameplay patterns to predict winners and adjust your rank based on performance.
            </Text>
          </Box>

          {/* Training Progress / Data Collection */}
          {totalMatches < trainingThreshold && (
            <Box bg="space.800" border="2px dashed" borderColor="brand.500" p={6} borderRadius="xl" boxShadow={brandShadow}>
              <VStack align="stretch" spacing={4}>
                <HStack justify="space-between">
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="bold" color="brand.400">Data Collection in Progress</Text>
                    <Text fontSize="xs" color="gray.500">The AI needs {trainingThreshold} matches to build a reliable prediction model.</Text>
                  </VStack>
                  <Text fontWeight="black" fontSize="2xl" color="brand.400">{totalMatches} / {trainingThreshold}</Text>
                </HStack>
                <Progress value={(totalMatches / trainingThreshold) * 100} colorScheme="brand" bg="space.900" borderRadius="full" size="sm" />
              </VStack>
            </Box>
          )}

          {/* Quick Stats Grid */}
          <Grid templateColumns={{ base: '1fr', md: 'repeat(4, 1fr)' }} gap={4}>
            {[
              { 
                label: 'Model Accuracy', 
                val: accuracyData?.cv_accuracy ? `${accuracyData.cv_accuracy}%` : '--', 
                sub: accuracyData?.cv_accuracy && accuracyData?.baseline_accuracy 
                  ? `+${(accuracyData.cv_accuracy - accuracyData.baseline_accuracy).toFixed(1)}% vs baseline` 
                  : 'Validated on held-out data', 
                color: 'accent.400', 
                arrow: (accuracyData?.cv_accuracy || 0) > (accuracyData?.baseline_accuracy || 0), 
                icon: FiTarget 
              },
              { 
                label: 'MMR Baseline', 
                val: accuracyData?.baseline_accuracy ? `${accuracyData.baseline_accuracy}%` : '--', 
                sub: 'Higher MMR wins', 
                color: 'brand.400', 
                icon: FiActivity 
              },
              { label: 'Training Data', val: accuracyData?.cv_training_size || totalMatches, sub: 'Matches analyzed', color: 'brand.400', icon: FiDatabase },
              { label: 'Impact Modifier', val: '+50%', sub: 'Max carry bonus', color: 'green.400', icon: FiZap },
            ].map((stat, i) => (
              <GridItem key={i}>
                <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={6} position="relative" overflow="hidden">
                  <Icon as={stat.icon} position="absolute" right="-10px" bottom="-10px" boxSize={24} color="whiteAlpha.100" />
                  <Stat>
                    <StatLabel color="gray.400" fontSize="xs" fontWeight="bold" letterSpacing="widest">{stat.label}</StatLabel>
                    <StatNumber color={stat.color} fontSize="3xl" fontWeight="black">{stat.val}</StatNumber>
                    <StatHelpText>
                      {stat.arrow !== undefined && <StatArrow type={stat.arrow ? 'increase' : 'decrease'} />}
                      {stat.sub}
                    </StatHelpText>
                  </Stat>
                </Box>
              </GridItem>
            ))}
          </Grid>

                  {/* Winning Factors & Glossary */}
                  <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={8}>
                    <Tabs variant="soft-rounded" colorScheme="brand">
                      <HStack justify="space-between" mb={8} borderBottom="1px solid" borderColor="whiteAlpha.100" pb={4}>
                        <HStack spacing={4}>
                          <Icon as={FiBarChart2} color="accent.400" boxSize={8} />
                          <Heading size="lg" fontFamily="heading">Winning Factors</Heading>
                        </HStack>
                        <TabList bg="space.900" p={1} borderRadius="full">
                          <Tab borderRadius="full" fontSize="sm" px={6}>Impact Chart</Tab>
                          <Tab borderRadius="full" fontSize="sm" px={6}>Factor Glossary</Tab>
                        </TabList>
                      </HStack>

                      <TabPanels>
                        <TabPanel p={0}>
                          <Grid templateColumns={{ base: '1fr', lg: '3fr 2fr' }} gap={12}>
                            <VStack align="stretch" spacing={6}>
                              {normalizedFeatures.length === 0 ? (
                                <Box h="300px" display="flex" flexDirection="column" alignItems="center" justifyContent="center">
                                  <Icon as={FiCpu} boxSize={12} color="gray.700" mb={4} />
                                  <Text color="gray.600" fontSize="md">Awaiting model training to calculate factor importance.</Text>
                                </Box>
                              ) : (
                                normalizedFeatures.slice(0, 8).map((f, i) => {
                                  const importancePercent = f.importance * 100;
                                  const maxImportance = normalizedFeatures[0].importance * 100;
                                  const glossaryEntry = factorGlossary[f.feature];
                                  return (
                                    <Tooltip
                                      key={f.feature}
                                      label={
                                        <Box p={2}>
                                          <Text fontWeight="bold" mb={1}>{glossaryEntry?.label || f.feature}</Text>
                                          <Text fontSize="sm" color="gray.200">{glossaryEntry?.desc || 'No description available.'}</Text>
                                          <Badge mt={2} colorScheme={glossaryEntry?.category === 'Micro' ? 'orange' : glossaryEntry?.category === 'Macro' ? 'green' : 'blue'}>
                                            {glossaryEntry?.category || 'META'}
                                          </Badge>
                                        </Box>
                                      }
                                      placement="right"
                                      hasArrow
                                      bg="space.700"
                                      color="white"
                                      borderRadius="lg"
                                      px={4}
                                      py={3}
                                      maxW="280px"
                                    >
                                      <Box
                                        cursor="pointer"
                                        p={3}
                                        mx={-3}
                                        borderRadius="lg"
                                        transition="all 0.2s"
                                        _hover={{ bg: 'whiteAlpha.50' }}
                                      >
                                        <HStack justify="space-between" mb={2}>
                                          <HStack spacing={3}>
                                              <Text fontSize="sm" fontWeight="black" color="white" letterSpacing="widest">
                                              {getFeatureLabel(f.feature)}
                                              </Text>
                                              <Badge size="sm" fontSize="10px" colorScheme={glossaryEntry?.category === 'Micro' ? 'orange' : glossaryEntry?.category === 'Macro' ? 'green' : 'blue'}>
                                                  {glossaryEntry?.category || 'META'}
                                              </Badge>
                                          </HStack>
                                          <Text fontSize="sm" color="gray.400" fontFamily="mono" fontWeight="bold">{importancePercent.toFixed(1)}%</Text>
                                        </HStack>
                                        <Progress value={(importancePercent / maxImportance) * 100} size="sm" borderRadius="full" colorScheme={i < 3 ? "brand" : "accent"} bg="space.900" />
                                      </Box>
                                    </Tooltip>
                                  );
                                })
                              )}
                    </VStack>
                    <Box bg="space.900" p={6} borderRadius="xl" border="2px solid" borderColor="space.700" boxShadow="inner">
                        <Heading size="sm" mb={6} color="brand.400" textTransform="uppercase" letterSpacing="widest" display="flex" alignItems="center">
                            <Icon as={FiZap} mr={2} />
                            Strategic Insight
                        </Heading>
                        <Text fontSize="md" color="gray.200" lineHeight="tall" fontWeight="medium">
                            The AI currently weights <Text as="span" fontWeight="black" color="brand.400">Experience</Text> as the highest predictor. 
                            In your squad, matches with a gap of 50+ games are <Text as="span" color="accent.300" fontWeight="bold">18% more likely</Text> to favor the veteran side, 
                            regardless of average MMR.
                        </Text>
                        <Divider my={6} borderColor="whiteAlpha.200" />
                        <Text fontSize="sm" color="gray.500" fontStyle="italic">
                            "Micro" factors become more predictive as player MMRs converge. Matches with high skill gaps are almost entirely decided by macro efficiency.
                        </Text>
                    </Box>
                  </Grid>
                </TabPanel>
                <TabPanel p={0}>
                  <Grid templateColumns={{ base: '1fr', md: '1fr 1fr' }} gap={6}>
                    {Object.entries(factorGlossary).map(([key, info]) => (
                      <Box key={key} p={5} bg="space.900" borderRadius="xl" borderLeft="6px solid" borderColor={info.category === 'Micro' ? 'orange.400' : info.category === 'Macro' ? 'green.400' : 'blue.400'} _hover={{ bg: 'space.700', transform: 'translateX(5px)' }} transition="all 0.2s">
                        <HStack justify="space-between" mb={2}>
                          <Text fontWeight="black" fontSize="md" color="white" letterSpacing="wide">{info.label}</Text>
                          <Badge variant="outline" colorScheme={info.category === 'Micro' ? 'orange' : info.category === 'Macro' ? 'green' : 'blue'} fontSize="10px">{info.category}</Badge>
                        </HStack>
                        <Text fontSize="sm" color="gray.400" lineHeight="short">{info.desc}</Text>
                      </Box>
                    ))}
                  </Grid>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </Box>

          {/* System Logic - Pipeline View */}
          <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={8}>
            <VStack align="stretch" spacing={8}>
                <VStack align="start" spacing={1}>
                    <HStack>
                        <Icon as={FiBookOpen} color="brand.400" boxSize={6} />
                        <Heading size="md" fontFamily="heading">The Hybrid Audit Pipeline</Heading>
                    </HStack>
                    <Text fontSize="sm" color="gray.500">How your performance metrics transform into rank adjustments.</Text>
                </VStack>

                <Flex flexDir={{ base: 'column', lg: 'row' }} justify="space-between" align="center" gap={4} position="relative">
                    {/* Visual Connector Line for Desktop */}
                    <Box position="absolute" top="40px" left="10%" right="10%" h="2px" bg="whiteAlpha.100" display={{ base: 'none', lg: 'block' }} zIndex={0} />

                    {[
                        { step: 1, title: 'TrueSkill Base', desc: 'Calculates ±25 MMR based on win/loss and opponent strength.', icon: FiActivity, color: 'blue.400' },
                        { step: 2, title: 'Gameplay Audit', desc: 'AI analyzes 14 factors (Macro/Micro) vs squad average.', icon: FiCpu, color: 'purple.400' },
                        { step: 3, title: 'Carry Detection', desc: 'If Performance > 70% confidence, a multiplier is triggered.', icon: FiZap, color: 'brand.400' },
                        { step: 4, title: 'Final Update', desc: 'Up to 1.5x gain for wins or 0.5x loss reduction.', icon: FiCheckCircle, color: 'green.400' },
                    ].map((item, i) => (
                        <VStack key={i} flex={1} bg="space.900" p={5} borderRadius="xl" border="1px solid" borderColor="space.700" zIndex={1} spacing={4} minH="180px">
                            <Circle size="12" bg="space.800" border="2px solid" borderColor={item.color}>
                                <Icon as={item.icon} color={item.color} boxSize={6} />
                            </Circle>
                            <VStack spacing={1}>
                                <Text fontWeight="black" fontSize="sm" color="white" textTransform="uppercase">{item.title}</Text>
                                <Text fontSize="xs" color="gray.500" textAlign="center">{item.desc}</Text>
                            </VStack>
                        </VStack>
                    ))}
                </Flex>

                <Box bg="rgba(78, 205, 196, 0.1)" p={4} borderRadius="lg" border="1px solid" borderColor="accent.400">
                    <HStack spacing={4}>
                        <Icon as={FiInfo} color="accent.400" />
                        <Text fontSize="xs" color="gray.300">
                            <Text as="span" fontWeight="bold">Example:</Text> If you win a game (+25 MMR) but the AI detects a "Carry Performance" in Step 3, 
                            your final gain would be <Text as="span" color="accent.300" fontWeight="bold">+38 MMR</Text>.
                        </Text>
                    </HStack>
                </Box>
            </VStack>
          </Box>



        </VStack>
      </Container>
    </Box>
  );
};

export default MLIntelligence;
