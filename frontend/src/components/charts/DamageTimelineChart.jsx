/**
 * Damage Timeline Chart - Interactive visualization of damage dealt over time
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
  Tooltip,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from 'recharts';
import { FiZap, FiClock } from 'react-icons/fi';

const DamageTimelineChart = ({ timelineData, playerName }) => {
  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');

  if (!timelineData || !timelineData.damage_timeline) {
    return null;
  }

  // Parse the damage timeline JSON
  const timeline = JSON.parse(timelineData.damage_timeline || '{}');
  const damageBySecond = timeline.damage_by_second || {};

  // Convert to chart data format
  const chartData = Object.entries(damageBySecond).map(([second, damage]) => ({
    second: parseInt(second),
    time: `${Math.floor(second / 60)}:${String(second % 60).padStart(2, '0')}`,
    damage: damage,
  }));

  // Sort by second
  chartData.sort((a, b) => a.second - b.second);

  // Calculate cumulative damage
  let cumulative = 0;
  chartData.forEach((point) => {
    cumulative += point.damage;
    point.cumulativeDamage = cumulative;
  });

  // Get timing attacks
  const timingAttacks = timelineData.timing_attacks || [];

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
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
          <Text fontFamily="heading" color="brand.400" fontWeight="bold">
            {data.time}
          </Text>
          <Text fontSize="sm" color="white">
            Damage: <strong>{data.damage.toLocaleString()}</strong>
          </Text>
          <Text fontSize="sm" color="gray.400">
            Total: {data.cumulativeDamage.toLocaleString()}
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
              <Icon as={FiZap} color="yellow.500" boxSize={5} />
              <Heading size="md" fontFamily="heading" textTransform="uppercase">
                Damage Timeline
              </Heading>
            </HStack>
            <Badge colorScheme="cyan" fontSize="sm" fontFamily="heading">
              {playerName}
            </Badge>
          </HStack>

          {/* Stats Summary */}
          <HStack spacing={6}>
            <VStack align="start" spacing={0}>
              <Text fontSize="xs" color="gray.500" fontFamily="heading">
                TOTAL DAMAGE
              </Text>
              <Text fontSize="xl" fontWeight="bold" color="brand.400">
                {timelineData.total_damage?.toLocaleString() || 0}
              </Text>
            </VStack>
            {timelineData.first_damage_time && (
              <VStack align="start" spacing={0}>
                <Text fontSize="xs" color="gray.500" fontFamily="heading">
                  FIRST STRIKE
                </Text>
                <HStack>
                  <Icon as={FiClock} color="yellow.500" />
                  <Text fontSize="xl" fontWeight="bold" color="yellow.500">
                    {timelineData.first_damage_time}
                  </Text>
                </HStack>
              </VStack>
            )}
            {timelineData.peak_damage_time && (
              <VStack align="start" spacing={0}>
                <Text fontSize="xs" color="gray.500" fontFamily="heading">
                  PEAK DAMAGE
                </Text>
                <Text fontSize="xl" fontWeight="bold" color="red.500">
                  {timelineData.peak_damage_amount?.toLocaleString()} @ {timelineData.peak_damage_time}
                </Text>
              </VStack>
            )}
          </HStack>

          {/* Chart */}
          <Box height="300px" width="100%">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <defs>
                  <linearGradient id="damageGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00D4FF" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00D4FF" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="time"
                  stroke="rgba(255,255,255,0.5)"
                  style={{ fontFamily: 'monospace', fontSize: '11px' }}
                  interval="preserveStartEnd"
                  minTickGap={50}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.5)"
                  style={{ fontFamily: 'monospace', fontSize: '11px' }}
                  tickFormatter={(value) => value.toLocaleString()}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ fontFamily: 'monospace', fontSize: '12px' }}
                />

                {/* Highlight timing attacks */}
                {timingAttacks.map((attack, idx) => (
                  <ReferenceLine
                    key={idx}
                    x={attack.start_time}
                    stroke="rgba(255, 179, 0, 0.6)"
                    strokeWidth={2}
                    label={{
                      value: `Attack ${idx + 1}`,
                      fill: '#FFB300',
                      fontSize: 10,
                      fontFamily: 'monospace',
                    }}
                  />
                ))}

                <Area
                  type="monotone"
                  dataKey="damage"
                  fill="url(#damageGradient)"
                  stroke="none"
                />
                <Line
                  type="monotone"
                  dataKey="damage"
                  stroke="#00D4FF"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: '#00D4FF' }}
                  name="Damage per Second"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </Box>

          {/* Timing Attacks List */}
          {timingAttacks.length > 0 && (
            <Box>
              <Text fontSize="sm" fontWeight="bold" mb={2} fontFamily="heading">
                TIMING ATTACKS DETECTED:
              </Text>
              <VStack align="stretch" spacing={2}>
                {timingAttacks.map((attack, idx) => (
                  <HStack
                    key={idx}
                    p={2}
                    bg="rgba(255, 179, 0, 0.1)"
                    borderRadius="md"
                    borderLeft="3px solid"
                    borderLeftColor="accent.500"
                    spacing={3}
                  >
                    <Badge colorScheme="orange" fontFamily="heading">
                      #{idx + 1}
                    </Badge>
                    <Text fontSize="sm">
                      <strong>{attack.start_time}</strong> - {attack.total_damage.toLocaleString()} damage
                      over {attack.duration_seconds}s
                    </Text>
                  </HStack>
                ))}
              </VStack>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

export default DamageTimelineChart;
