/**
 * Damage Distribution Chart - Shows damage breakdown by game phase
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
  Progress,
} from '@chakra-ui/react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { FiActivity, FiClock } from 'react-icons/fi';

// =============================================================================
// Type Definitions
// =============================================================================

interface DamageDistribution {
  early: number;
  mid: number;
  late: number;
}

interface DamageDistributionChartProps {
  damageDistribution: DamageDistribution | null;
  playerName: string;
}

interface ChartDataItem {
  phase: 'Early' | 'Mid' | 'Late';
  damage: number;
  percentage: number;
  timeRange: string;
  color: string;
}

interface Archetype {
  name: string;
  color: string;
  description: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: ChartDataItem;
  }>;
}

// =============================================================================
// Component
// =============================================================================

const DamageDistributionChart: React.FC<DamageDistributionChartProps> = ({
  damageDistribution,
  playerName,
}) => {
  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');

  if (!damageDistribution) {
    return null;
  }

  // Parse damage distribution
  const early = damageDistribution.early || 0;
  const mid = damageDistribution.mid || 0;
  const late = damageDistribution.late || 0;
  const total = early + mid + late;

  // Prepare chart data
  const chartData: ChartDataItem[] = [
    {
      phase: 'Early',
      damage: early,
      percentage: total > 0 ? (early / total) * 100 : 0,
      timeRange: '0-5 min',
      color: '#FFB300',
    },
    {
      phase: 'Mid',
      damage: mid,
      percentage: total > 0 ? (mid / total) * 100 : 0,
      timeRange: '5-15 min',
      color: '#00D4FF',
    },
    {
      phase: 'Late',
      damage: late,
      percentage: total > 0 ? (late / total) * 100 : 0,
      timeRange: '15+ min',
      color: '#00FF88',
    },
  ];

  // Determine player archetype based on distribution
  const getArchetype = (): Archetype => {
    if (early > mid && early > late) {
      return { name: 'Early Aggressor', color: 'orange', description: 'Focuses on early game pressure' };
    } else if (mid > early && mid > late) {
      return { name: 'Mid Game Specialist', color: 'cyan', description: 'Peaks in the mid game' };
    } else if (late > early && late > mid) {
      return { name: 'Late Game Player', color: 'green', description: 'Strongest in late game' };
    } else {
      return { name: 'Balanced', color: 'purple', description: 'Consistent across all phases' };
    }
  };

  const archetype = getArchetype();

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
            <Icon as={FiClock} color={data.color} />
            <Text fontFamily="heading" color="brand.400" fontWeight="bold">
              {data.phase} Game
            </Text>
          </HStack>
          <Text fontSize="sm" color="white">
            Damage: <strong>{data.damage.toLocaleString()}</strong>
          </Text>
          <Text fontSize="sm" color="gray.400">
            {data.percentage.toFixed(1)}% of total
          </Text>
          <Text fontSize="xs" color="gray.500" mt={1}>
            {data.timeRange}
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
              <Icon as={FiActivity} color="purple.500" boxSize={5} />
              <Heading size="md" fontFamily="heading">
                Damage by Phase
              </Heading>
            </HStack>
            <Badge colorScheme="cyan" fontSize="sm" fontFamily="heading">
              {playerName}
            </Badge>
          </HStack>

          {/* Archetype Badge */}
          <Box
            p={3}
            bg={`${archetype.color}.900`}
            borderRadius="md"
            border="2px solid"
            borderColor={`${archetype.color}.500`}
            textAlign="center"
          >
            <Text fontSize="xs" color="gray.400" fontFamily="heading">
              Play Style
            </Text>
            <Text fontSize="xl" fontWeight="bold" color={`${archetype.color}.400`} fontFamily="heading">
              {archetype.name}
            </Text>
            <Text fontSize="xs" color="gray.500">
              {archetype.description}
            </Text>
          </Box>

          {/* Bar Chart */}
          <Box height="250px" width="100%">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="phase"
                  stroke="rgba(255,255,255,0.5)"
                  style={{ fontFamily: 'monospace', fontSize: '12px' }}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.5)"
                  style={{ fontFamily: 'monospace', fontSize: '11px' }}
                  tickFormatter={(value: number) => value.toLocaleString()}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ fontFamily: 'monospace', fontSize: '12px' }}
                />
                <Bar dataKey="damage" name="Damage" radius={[8, 8, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Box>

          {/* Detailed Breakdown */}
          <VStack align="stretch" spacing={2}>
            {chartData.map((phase) => (
              <Box key={phase.phase}>
                <HStack justify="space-between" mb={1}>
                  <HStack>
                    <Badge colorScheme={phase.phase === 'Early' ? 'orange' : phase.phase === 'Mid' ? 'cyan' : 'green'}>
                      {phase.phase}
                    </Badge>
                    <Text fontSize="xs" color="gray.500">
                      {phase.timeRange}
                    </Text>
                  </HStack>
                  <Text fontSize="sm" fontWeight="bold">
                    {phase.damage.toLocaleString()} ({phase.percentage.toFixed(1)}%)
                  </Text>
                </HStack>
                <Progress
                  value={phase.percentage}
                  colorScheme={phase.phase === 'Early' ? 'orange' : phase.phase === 'Mid' ? 'cyan' : 'green'}
                  size="sm"
                  borderRadius="full"
                />
              </Box>
            ))}
          </VStack>

          {/* Total */}
          <Box
            p={2}
            bg="rgba(30, 41, 59, 0.5)"
            borderRadius="md"
            borderTop="2px solid"
            borderTopColor="brand.500"
          >
            <HStack justify="space-between">
              <Text fontSize="sm" fontFamily="heading" color="gray.400">
                Total Damage
              </Text>
              <Text fontSize="lg" fontWeight="bold" color="brand.400">
                {total.toLocaleString()}
              </Text>
            </HStack>
          </Box>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default DamageDistributionChart;
