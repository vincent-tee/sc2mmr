/**
 * BalanceMethodSelector - Compact method selector with expandable details
 * Redesigned for minimal vertical space with "See Details" expansion
 */
import React, { useEffect, useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Icon,
  Spinner,
  Collapse,
  Button,
  Tooltip,
  Flex,
  Spacer,
} from '@chakra-ui/react';
import { FiTarget, FiClock, FiCpu, FiChevronDown, FiChevronUp, FiInfo } from 'react-icons/fi';
import { colors, shadows, transitions } from '../theme/tokens';
import { adaptiveApi, BalanceMethodSuccessRate } from '../api/endpoints';

export type BalanceMethod = 'trueskill' | 'session' | 'ml-metrics';

interface BalanceMethodInfo {
  id: BalanceMethod;
  name: string;
  shortDesc: string;
  fullDesc: string;
  volatility: string;
  adaptation: string;
  metrics: string[];
  recommended?: boolean;
  icon: React.ComponentType;
}

const BALANCE_METHODS: BalanceMethodInfo[] = [
  {
    id: 'trueskill',
    name: 'Classic',
    shortDesc: 'Pure win/loss',
    fullDesc: 'Uses Microsoft TrueSkill algorithm. Stable ratings based on match outcomes only. Best for long-term accuracy.',
    volatility: 'Low (±20 MMR)',
    adaptation: 'Slow (20+ matches)',
    metrics: ['Wins', 'Losses', 'Match History'],
    icon: FiTarget,
  },
  {
    id: 'session',
    name: 'Session',
    shortDesc: 'Recent games 3x weight',
    fullDesc: 'Weights recent matches more heavily. Adapts faster to hot/cold streaks and returning players.',
    volatility: 'Medium (±30 MMR)',
    adaptation: 'Medium (10 matches)',
    metrics: ['Recent MMR', 'Recency Weights', 'Performance Trend'],
    icon: FiClock,
  },
  {
    id: 'ml-metrics',
    name: 'ML Metrics',
    shortDesc: 'In-game performance',
    fullDesc: 'Analyzes combat, economy, and efficiency metrics. Uses player synergy data for team composition.',
    volatility: 'Aggressive (±50 MMR)',
    adaptation: 'Fast (5 matches)',
    metrics: ['Combat', 'Economic', 'Efficiency', 'Synergy'],
    recommended: true,
    icon: FiCpu,
  },
];

interface BalanceMethodSelectorProps {
  selectedMethod: BalanceMethod;
  onMethodChange: (method: BalanceMethod) => void;
}

const BalanceMethodSelector: React.FC<BalanceMethodSelectorProps> = ({
  selectedMethod,
  onMethodChange,
}) => {
  const [successRates, setSuccessRates] = useState<Record<string, BalanceMethodSuccessRate> | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    const fetchSuccessRates = async () => {
      try {
        const response = await adaptiveApi.getBalanceMethodSuccessRate();
        setSuccessRates(response.data);
      } catch (error) {
        console.error('Failed to fetch balance method success rates:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchSuccessRates();
  }, []);

  const getAccuracyColor = (rate: number) => {
    if (rate >= 70) return 'green.400';
    if (rate >= 55) return 'yellow.400';
    return 'gray.400';
  };

  const selectedInfo = BALANCE_METHODS.find(m => m.id === selectedMethod);

  return (
    <Box
      bg={colors.space[800]}
      border="2px solid"
      borderColor={colors.space[700]}
      borderRadius="xl"
      p={4}
    >
      {/* Compact Method Tabs */}
      <HStack spacing={2} mb={showDetails ? 4 : 0}>
        {BALANCE_METHODS.map((method) => {
          const isSelected = selectedMethod === method.id;
          const methodSuccess = successRates?.[method.id];
          
          return (
            <Box
              key={method.id}
              flex={1}
              p={3}
              border="2px solid"
              borderColor={isSelected ? colors.brand[500] : colors.space[600]}
              borderRadius="lg"
              bg={isSelected ? colors.background.selected : 'transparent'}
              boxShadow={isSelected ? shadows.comic : 'none'}
              transition={`all ${transitions.base} ${transitions.easing.bounce}`}
              cursor="pointer"
              onClick={() => onMethodChange(method.id)}
              _hover={{
                borderColor: isSelected ? colors.brand[500] : colors.brand[400],
                bg: isSelected ? colors.background.selected : colors.space[700],
              }}
              position="relative"
            >
              {method.recommended && (
                <Badge
                  position="absolute"
                  top="-8px"
                  right="-8px"
                  bg={colors.brand[500]}
                  color="white"
                  fontSize="9px"
                  px={1.5}
                  py={0.5}
                  borderRadius="full"
                  textTransform="uppercase"
                  letterSpacing="wide"
                >
                  Best
                </Badge>
              )}
              
              <VStack spacing={1} align="center">
                <HStack spacing={2}>
                  <Icon
                    as={method.icon}
                    boxSize={4}
                    color={isSelected ? colors.brand[400] : colors.space[400]}
                  />
                  <Text
                    fontWeight="bold"
                    fontSize="sm"
                    color={isSelected ? colors.text.primary : colors.text.secondary}
                  >
                    {method.name}
                  </Text>
                </HStack>
                
                <Text
                  fontSize="xs"
                  color={colors.text.muted}
                  textAlign="center"
                  noOfLines={1}
                >
                  {method.shortDesc}
                </Text>
                
                {/* Prediction Accuracy - renamed from Success Rate */}
                <HStack spacing={1} mt={1}>
                  {loading ? (
                    <Spinner size="xs" color={colors.brand[400]} />
                  ) : methodSuccess ? (
                    <Tooltip
                      label={`Based on ${methodSuccess.total_matches} matches where the predicted favored team won`}
                      placement="bottom"
                      hasArrow
                      bg={colors.space[700]}
                      color="white"
                    >
                      <HStack spacing={1} cursor="help">
                        <Text
                          fontSize="xs"
                          fontWeight="bold"
                          color={getAccuracyColor(methodSuccess.success_rate)}
                        >
                          {methodSuccess.success_rate}%
                        </Text>
                        <Text fontSize="xs" color={colors.text.muted}>
                          accuracy
                        </Text>
                      </HStack>
                    </Tooltip>
                  ) : (
                    <Text fontSize="xs" color={colors.text.muted}>—</Text>
                  )}
                </HStack>
              </VStack>
            </Box>
          );
        })}
        
        {/* See Details Toggle */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowDetails(!showDetails)}
          color={colors.text.muted}
          _hover={{ color: colors.brand[400], bg: colors.space[700] }}
          px={2}
          minW="auto"
        >
          <Icon as={showDetails ? FiChevronUp : FiChevronDown} boxSize={4} />
        </Button>
      </HStack>

      {/* Expandable Details Section */}
      <Collapse in={showDetails} animateOpacity>
        <Box
          mt={3}
          pt={3}
          borderTop="1px solid"
          borderColor={colors.space[600]}
        >
          {selectedInfo && (
            <VStack align="stretch" spacing={3}>
              {/* Full Description */}
              <HStack align="start" spacing={2}>
                <Icon as={FiInfo} color={colors.brand[400]} mt={0.5} />
                <Text fontSize="sm" color={colors.text.secondary}>
                  {selectedInfo.fullDesc}
                </Text>
              </HStack>
              
              {/* Stats Grid */}
              <Flex gap={6} wrap="wrap">
                <Box>
                  <Text fontSize="xs" color={colors.text.muted} textTransform="uppercase" letterSpacing="wide">
                    Volatility
                  </Text>
                  <Text fontSize="sm" fontWeight="bold" color={colors.text.secondary}>
                    {selectedInfo.volatility}
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color={colors.text.muted} textTransform="uppercase" letterSpacing="wide">
                    Adaptation Speed
                  </Text>
                  <Text fontSize="sm" fontWeight="bold" color={colors.text.secondary}>
                    {selectedInfo.adaptation}
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color={colors.text.muted} textTransform="uppercase" letterSpacing="wide">
                    Factors Used
                  </Text>
                  <Text fontSize="sm" color={colors.text.secondary}>
                    {selectedInfo.metrics.join(' / ')}
                  </Text>
                </Box>
              </Flex>
            </VStack>
          )}
        </Box>
      </Collapse>
    </Box>
  );
};

export default React.memo(BalanceMethodSelector);
