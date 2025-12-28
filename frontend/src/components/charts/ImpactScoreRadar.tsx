/**
 * Impact Score Radar Chart - Shows breakdown of impact scores
 */
import {
  Box,
  Card,
  CardBody,
  Heading,
  Text,
  VStack,
  HStack,
  Badge,
  Icon,
  useColorModeValue,
  Tooltip,
} from '@chakra-ui/react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from 'recharts';
import { FiTarget, FiTrendingUp, FiDollarSign, FiZap } from 'react-icons/fi';
import type { IconType } from 'react-icons';

// =============================================================================
// Type Definitions
// =============================================================================

interface ImpactMetrics {
  economic_score?: number;
  combat_score?: number;
  efficiency_score?: number;
  overall_impact?: number;
  damage_ratio?: number;
  damage_dealt?: number;
  damage_taken?: number;
}

interface ImpactScoreRadarProps {
  metrics: ImpactMetrics | null;
  playerName: string;
  showComparison?: boolean;
}

interface RadarDataItem {
  category: string;
  score: number;
  fullMark: number;
  icon: IconType;
  color: string;
  description: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: RadarDataItem;
  }>;
}

// =============================================================================
// Component
// =============================================================================

const ImpactScoreRadar: React.FC<ImpactScoreRadarProps> = ({
  metrics,
  playerName,
  showComparison: _showComparison = false,
}) => {
  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');

  if (!metrics) {
    return null;
  }

  // Prepare data for radar chart
  const radarData: RadarDataItem[] = [
    {
      category: 'Economic',
      score: metrics.economic_score || 0,
      fullMark: 100,
      icon: FiDollarSign,
      color: '#FFB300',
      description: 'Resource collection & spending efficiency',
    },
    {
      category: 'Combat',
      score: metrics.combat_score || 0,
      fullMark: 100,
      icon: FiZap,
      color: '#EF4444',
      description: 'Damage dealt & units killed',
    },
    {
      category: 'Efficiency',
      score: metrics.efficiency_score || 0,
      fullMark: 100,
      icon: FiTrendingUp,
      color: '#00FF88',
      description: 'Resource usage & trade efficiency',
    },
  ];

  const overallImpact = metrics.overall_impact || 0;

  // Custom tooltip
  const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Box
          bg="gray.900"
          p={3}
          borderRadius="md"
          border="2px solid"
          borderColor="brand.500"
          boxShadow="0 0 20px rgba(0, 212, 255, 0.3)"
        >
          <HStack mb={1}>
            <Icon as={data.icon} color={data.color} />
            <Text fontFamily="heading" color="brand.400" fontWeight="bold">
              {data.category}
            </Text>
          </HStack>
          <Text fontSize="sm" color="white">
            Score: <strong>{data.score.toFixed(1)}</strong> / 100
          </Text>
          <Text fontSize="xs" color="gray.400" mt={1}>
            {data.description}
          </Text>
        </Box>
      );
    }
    return null;
  };

  return (
    <Card bg={cardBg} border="2px solid" borderColor={borderColor}>
      <CardBody>
        <VStack align="stretch" spacing={4}>
          {/* Header */}
          <HStack justify="space-between">
            <HStack>
              <Icon as={FiTarget} color="brand.400" boxSize={5} />
              <Heading size="md" fontFamily="heading">
                Impact Analysis
              </Heading>
            </HStack>
            <Badge colorScheme="cyan" fontSize="sm" fontFamily="heading">
              {playerName}
            </Badge>
          </HStack>

          {/* Overall Impact Score */}
          <Box
            p={4}
            bg="rgba(0, 212, 255, 0.1)"
            borderRadius="md"
            border="2px solid"
            borderColor="brand.500"
            textAlign="center"
          >
            <Text fontSize="sm" color="gray.400" fontFamily="heading">
              Overall Impact
            </Text>
            <Text fontSize="4xl" fontWeight="black" color="brand.400" fontFamily="heading">
              {overallImpact.toFixed(1)}
            </Text>
            <Text fontSize="xs" color="gray.500">
              / 100
            </Text>
          </Box>

          {/* Radar Chart */}
          <Box height="300px" width="100%">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(0, 212, 255, 0.3)" />
                <PolarAngleAxis
                  dataKey="category"
                  stroke="rgba(255,255,255,0.7)"
                  style={{ fontFamily: 'monospace', fontSize: '12px', fontWeight: 'bold' }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  stroke="rgba(255,255,255,0.5)"
                  style={{ fontFamily: 'monospace', fontSize: '10px' }}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Radar
                  name={playerName}
                  dataKey="score"
                  stroke="#00D4FF"
                  fill="#00D4FF"
                  fillOpacity={0.6}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </Box>

          {/* Score Breakdown */}
          <VStack align="stretch" spacing={2}>
            {radarData.map((item) => (
              <Tooltip key={item.category} label={item.description} placement="top">
                <HStack
                  p={2}
                  bg="rgba(30, 41, 59, 0.5)"
                  borderRadius="md"
                  justify="space-between"
                  cursor="help"
                  _hover={{
                    bg: 'rgba(0, 212, 255, 0.1)',
                    borderColor: 'brand.500',
                  }}
                  transition="all 0.2s"
                >
                  <HStack>
                    <Icon as={item.icon} color={item.color} />
                    <Text fontSize="sm" fontFamily="heading">
                      {item.category}
                    </Text>
                  </HStack>
                  <Badge
                    colorScheme={item.score >= 70 ? 'green' : item.score >= 50 ? 'yellow' : 'red'}
                    fontSize="md"
                    fontFamily="heading"
                  >
                    {item.score.toFixed(1)}
                  </Badge>
                </HStack>
              </Tooltip>
            ))}
          </VStack>

          {/* Additional Metrics */}
          {metrics.damage_ratio !== undefined && (
            <Box p={3} bg="rgba(30, 41, 59, 0.5)" borderRadius="md">
              <HStack justify="space-between">
                <Text fontSize="sm" color="gray.400">
                  {metrics.damage_taken && metrics.damage_taken > 0 ? 'Damage Efficiency' : 'Damage Ratio'}
                </Text>
                <Text fontSize="lg" fontWeight="bold" color={metrics.damage_ratio >= 1 ? 'green.400' : 'orange.400'}>
                  {metrics.damage_taken && metrics.damage_taken > 0
                    ? `${metrics.damage_ratio.toFixed(2)}x`
                    : 'Perfect Game'}
                </Text>
              </HStack>
              <Text fontSize="xs" color="gray.500" mt={1}>
                {metrics.damage_dealt?.toLocaleString()} dealt / {metrics.damage_taken?.toLocaleString()} taken
              </Text>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

export default ImpactScoreRadar;
