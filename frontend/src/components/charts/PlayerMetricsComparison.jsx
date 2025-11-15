/**
 * Player Metrics Comparison - Compare all players in a match
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
  Grid,
  GridItem,
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
import { FiUsers, FiAward, FiDollarSign, FiZap, FiTrendingUp } from 'react-icons/fi';

const PlayerMetricsComparison = ({ players, metricsData }) => {
  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');

  if (!players || players.length === 0 || !metricsData) {
    return null;
  }

  // Color by team
  const getPlayerColor = (teamNumber) => {
    return teamNumber === 1 ? '#00D4FF' : '#FFB300';
  };

  // Prepare comparison data
  const economicData = players.map((player) => ({
    name: player.player_name.substring(0, 10),
    fullName: player.player_name,
    score: metricsData[player.player_id]?.economic_score || 0,
    team: player.team_number,
  }));

  const combatData = players.map((player) => ({
    name: player.player_name.substring(0, 10),
    fullName: player.player_name,
    score: metricsData[player.player_id]?.combat_score || 0,
    team: player.team_number,
  }));

  const overallData = players.map((player) => ({
    name: player.player_name.substring(0, 10),
    fullName: player.player_name,
    score: metricsData[player.player_id]?.overall_impact || 0,
    team: player.team_number,
  }));

  // Find MVP (highest overall impact)
  const mvp = overallData.reduce((max, p) => (p.score > max.score ? p : max), overallData[0]);

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
            {data.fullName}
          </Text>
          <HStack>
            <Badge colorScheme={data.team === 1 ? 'cyan' : 'orange'}>
              Team {data.team}
            </Badge>
            <Text fontSize="sm" color="white">
              <strong>{data.score.toFixed(1)}</strong> / 100
            </Text>
          </HStack>
        </Box>
      );
    }
    return null;
  };

  return (
    <Card bg={cardBg} border="2px solid" borderColor={borderColor}>
      <CardBody>
        <VStack align="stretch" spacing={6}>
          {/* Header */}
          <HStack justify="space-between">
            <HStack>
              <Icon as={FiUsers} color="purple.500" boxSize={5} />
              <Heading size="md" fontFamily="heading" textTransform="uppercase">
                Player Comparison
              </Heading>
            </HStack>
            {mvp && (
              <HStack>
                <Icon as={FiAward} color="yellow.500" />
                <Text fontSize="sm" fontFamily="heading" color="yellow.500">
                  MVP: {mvp.fullName}
                </Text>
              </HStack>
            )}
          </HStack>

          {/* Overall Impact Comparison */}
          <Box>
            <HStack mb={3}>
              <Icon as={FiTrendingUp} color="purple.400" />
              <Text fontSize="sm" fontWeight="bold" fontFamily="heading">
                OVERALL IMPACT
              </Text>
            </HStack>
            <Box height="200px" width="100%">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overallData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="name"
                    stroke="rgba(255,255,255,0.5)"
                    style={{ fontFamily: 'monospace', fontSize: '10px' }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    stroke="rgba(255,255,255,0.5)"
                    style={{ fontFamily: 'monospace', fontSize: '10px' }}
                  />
                  <RechartsTooltip content={<CustomTooltip />} />
                  <Bar dataKey="score" name="Overall Impact" radius={[4, 4, 0, 0]}>
                    {overallData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={getPlayerColor(entry.team)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Box>

          {/* Economic vs Combat Comparison */}
          <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={4}>
            {/* Economic */}
            <GridItem>
              <Box>
                <HStack mb={3}>
                  <Icon as={FiDollarSign} color="yellow.400" />
                  <Text fontSize="sm" fontWeight="bold" fontFamily="heading">
                    ECONOMIC
                  </Text>
                </HStack>
                <Box height="180px" width="100%">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={economicData} layout="horizontal">
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis
                        type="number"
                        domain={[0, 100]}
                        stroke="rgba(255,255,255,0.5)"
                        style={{ fontFamily: 'monospace', fontSize: '9px' }}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        stroke="rgba(255,255,255,0.5)"
                        style={{ fontFamily: 'monospace', fontSize: '9px' }}
                        width={70}
                      />
                      <RechartsTooltip content={<CustomTooltip />} />
                      <Bar dataKey="score" name="Economic" radius={[0, 4, 4, 0]}>
                        {economicData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={getPlayerColor(entry.team)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            </GridItem>

            {/* Combat */}
            <GridItem>
              <Box>
                <HStack mb={3}>
                  <Icon as={FiZap} color="red.400" />
                  <Text fontSize="sm" fontWeight="bold" fontFamily="heading">
                    COMBAT
                  </Text>
                </HStack>
                <Box height="180px" width="100%">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={combatData} layout="horizontal">
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis
                        type="number"
                        domain={[0, 100]}
                        stroke="rgba(255,255,255,0.5)"
                        style={{ fontFamily: 'monospace', fontSize: '9px' }}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        stroke="rgba(255,255,255,0.5)"
                        style={{ fontFamily: 'monospace', fontSize: '9px' }}
                        width={70}
                      />
                      <RechartsTooltip content={<CustomTooltip />} />
                      <Bar dataKey="score" name="Combat" radius={[0, 4, 4, 0]}>
                        {combatData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={getPlayerColor(entry.team)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            </GridItem>
          </Grid>

          {/* Legend */}
          <HStack justify="center" spacing={6}>
            <HStack>
              <Box w={4} h={4} bg="#00D4FF" borderRadius="sm" />
              <Text fontSize="sm" fontFamily="heading">
                Team 1
              </Text>
            </HStack>
            <HStack>
              <Box w={4} h={4} bg="#FFB300" borderRadius="sm" />
              <Text fontSize="sm" fontFamily="heading">
                Team 2
              </Text>
            </HStack>
          </HStack>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default PlayerMetricsComparison;
