/**
 * MatchHeader Component - Match info header with metadata
 */
import {
  Box,
  Card,
  CardBody,
  VStack,
  HStack,
  Heading,
  Text,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Divider,
  Grid,
  Alert,
  useColorModeValue,
  Progress,
  Flex,
} from '@chakra-ui/react';
import {
  FiActivity,
  FiTrendingUp,
  FiZap,
  FiAward,
  FiAlertTriangle,
} from 'react-icons/fi';
import {
  formatDuration,
  formatDateTime,
  formatWinProbability,
  getUpsetIndicator,
} from '@/utils/formatting';
import VSScreen from '@/components/VSScreen';
import type { MatchDetail as MatchDetailType } from '@/types/api';

interface MatchHeaderProps {
  matchData: MatchDetailType;
  team1Won: boolean;
}

const MatchHeader: React.FC<MatchHeaderProps> = ({ matchData, team1Won }) => {
  const cardBg = 'space.800';
  const winnerBg = 'rgba(72, 187, 120, 0.1)';
  const loserBg = 'rgba(245, 101, 101, 0.1)';
  const borderColor = 'space.900';
  const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';

  const { match, players } = matchData;

  // Win probability analysis
  const hasWinProb =
    match.predicted_team1_win_prob !== null &&
    match.predicted_team2_win_prob !== null;
  const team1Prob = match.predicted_team1_win_prob || 0.5;
  const team2Prob = match.predicted_team2_win_prob || 0.5;
  const winningTeam = team1Won ? 1 : 2;
  const predictedWinningTeam = team1Prob > team2Prob ? 1 : 2;
  const upsetIndicator = hasWinProb
    ? getUpsetIndicator(winningTeam, team1Prob, team2Prob)
    : null;

  // Prepare VSScreen data
  const team1Players = players.filter(p => p.team_number === 1);
  const team2Players = players.filter(p => p.team_number === 2);
  const team1TotalMMR = team1Players.reduce((sum, p) => sum + (p.mmr ?? p.mmr_before), 0);
  const team2TotalMMR = team2Players.reduce((sum, p) => sum + (p.mmr ?? p.mmr_before), 0);

  const vsScreenData = {
    team1: {
      players: team1Players.map(p => ({
        name: p.player_name,
        mmr: p.mmr ?? p.mmr_before,
        race: p.race,
      })),
      totalMMR: team1TotalMMR,
      winProbability: team1Prob * 100,
    },
    team2: {
      players: team2Players.map(p => ({
        name: p.player_name,
        mmr: p.mmr ?? p.mmr_before,
        race: p.race,
      })),
      totalMMR: team2TotalMMR,
      winProbability: team2Prob * 100,
    },
    matchInfo: {
      mapName: match.map_name,
      gameMode: match.game_mode,
    },
    winner: winningTeam,
  };

  return (
    <VStack spacing={6} align="stretch">
      {/* VSScreen - Dramatic Team vs Team Display */}
      <VSScreen
        team1={vsScreenData.team1}
        team2={vsScreenData.team2}
        matchInfo={vsScreenData.matchInfo}
        winner={vsScreenData.winner as 1 | 2}
      />

      {/* Detailed Match Information Card */}
      <Box
        bg={cardBg}
        borderRadius="xl"
        border="3px solid"
        borderColor={borderColor}
        boxShadow={brandShadow}
        position="relative"
        overflow="hidden"
      >
        <Box p={6}>
          <VStack align="stretch" spacing={6}>
            {/* Match Title and Duration */}
            <Flex justify="space-between" align="start" flexWrap="wrap" gap={4}>
            <VStack align="start" spacing={2}>
              <HStack spacing={3}>
                <Icon as={FiActivity} boxSize={6} color="brand.400" />
                <Heading
                  size="xl"
                  fontFamily="heading"
                  letterSpacing="wider"
                  color="gray.100"
                >
                  {match.map_name}
                </Heading>
                <Badge
                  bg="space.900"
                  color="brand.400"
                  fontSize="md"
                  px={4}
                  py={1}
                  borderRadius="md"
                  fontFamily="heading"
                >
                  {match.game_mode}
                </Badge>
              </HStack>
              <Text color="gray.500" fontFamily="heading" fontSize="sm">
                {formatDateTime(match.played_at)}
              </Text>
            </VStack>

            <Stat textAlign="right">
              <StatLabel fontFamily="heading" color="brand.400" letterSpacing="widest" textTransform="uppercase" fontSize="xs">
                Battle Duration
              </StatLabel>
              <StatNumber fontSize="3xl" fontFamily="heading" color="gray.100">
                {formatDuration(match.duration_seconds)}
              </StatNumber>
            </Stat>
          </Flex>

          {/* Win Probability Section */}
          {hasWinProb && (
            <Box>
              <Divider my={5} borderColor="whiteAlpha.100" />

              {/* Upset Alert */}
              {upsetIndicator && (
                <Alert
                  status="warning"
                  variant="left-accent"
                  borderRadius="xl"
                  mb={6}
                  bg="rgba(255, 179, 0, 0.1)"
                  borderColor="accent.500"
                  borderWidth="2px"
                  boxShadow="inner"
                >
                  <Icon
                    as={FiAlertTriangle}
                    boxSize={6}
                    mr={3}
                    color="accent.500"
                  />
                  <Box>
                    <Text
                      fontWeight="black"
                      fontSize="lg"
                      fontFamily="heading"
                      letterSpacing="wider"
                      color="accent.400"
                    >
                      {upsetIndicator}
                    </Text>
                    <Text fontSize="sm" color="gray.300">
                      The underdog squad defied the forecast and secured victory!
                    </Text>
                  </Box>
                </Alert>
              )}

              <VStack spacing={6}>
                <Heading
                  size="sm"
                  fontFamily="heading"
                  letterSpacing="widest"
                  color="gray.500"
                  textTransform="uppercase"
                >
                  Neural Forecast Analysis
                </Heading>

                <Grid
                  templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }}
                  gap={6}
                  w="full"
                >
                  {/* Team 1 Prediction */}
                  <Box
                    bg={team1Won ? 'rgba(72, 187, 120, 0.05)' : 'rgba(245, 101, 101, 0.05)'}
                    borderRadius="xl"
                    border="2px solid"
                    borderColor={team1Won ? 'shield.500' : 'red.500'}
                    p={5}
                    position="relative"
                    boxShadow={team1Won ? '0 0 20px rgba(0, 255, 136, 0.1)' : 'none'}
                  >
                    <VStack spacing={3}>
                      <HStack w="full" justify="space-between">
                        <HStack>
                          <Icon
                            as={FiTrendingUp}
                            color="brand.400"
                            boxSize={4}
                          />
                          <Text
                            fontFamily="heading"
                            fontWeight="black"
                            fontSize="xs"
                            letterSpacing="widest"
                            color="brand.400"
                            textTransform="uppercase"
                          >
                            Squad Alpha
                          </Text>
                        </HStack>
                        {team1Won && (
                          <Badge colorScheme="green" variant="solid" borderRadius="sm">
                            VICTORY
                          </Badge>
                        )}
                      </HStack>
                       <Stat textAlign="center">
                         <StatLabel fontSize="10px" color="gray.500" textTransform="uppercase" letterSpacing="widest">
                           Win Probability
                         </StatLabel>
                         <StatNumber
                           fontSize="4xl"
                           fontFamily="heading"
                           color={
                             team1Prob > 0.5 ? 'shield.400' : 'gray.500'
                           }
                         >
                           {formatWinProbability(team1Prob)}
                         </StatNumber>
                       </Stat>
                    </VStack>
                  </Box>

                  {/* VS Divider */}
                  <Flex align="center" justify="center">
                    <VStack spacing={0}>
                      <Icon as={FiZap} boxSize={10} color="accent.500" mb={1} />
                      <Text
                        fontFamily="heading"
                        fontSize="2xl"
                        fontWeight="black"
                        letterSpacing="wider"
                        color="accent.500"
                      >
                        VS
                      </Text>
                    </VStack>
                  </Flex>

                  {/* Team 2 Prediction */}
                  <Box
                    bg={!team1Won ? 'rgba(72, 187, 120, 0.05)' : 'rgba(245, 101, 101, 0.05)'}
                    borderRadius="xl"
                    border="2px solid"
                    borderColor={!team1Won ? 'shield.500' : 'red.500'}
                    p={5}
                    position="relative"
                    boxShadow={!team1Won ? '0 0 20px rgba(0, 255, 136, 0.1)' : 'none'}
                  >
                    <VStack spacing={3}>
                       <HStack w="full" justify="space-between">
                        <HStack>
                          <Icon
                            as={FiTrendingUp}
                            color="accent.400"
                            boxSize={4}
                          />
                          <Text
                            fontFamily="heading"
                            fontWeight="black"
                            fontSize="xs"
                            letterSpacing="widest"
                            color="accent.400"
                            textTransform="uppercase"
                          >
                            Squad Bravo
                          </Text>
                        </HStack>
                        {!team1Won && (
                          <Badge colorScheme="green" variant="solid" borderRadius="sm">
                            VICTORY
                          </Badge>
                        )}
                      </HStack>
                       <Stat textAlign="center">
                         <StatLabel fontSize="10px" color="gray.500" textTransform="uppercase" letterSpacing="widest">
                           Win Probability
                         </StatLabel>
                         <StatNumber
                           fontSize="4xl"
                           fontFamily="heading"
                           color={
                             team2Prob > 0.5 ? 'shield.400' : 'gray.500'
                           }
                         >
                           {formatWinProbability(team2Prob)}
                         </StatNumber>
                       </Stat>
                    </VStack>
                  </Box>
                </Grid>

                {/* Visual probability comparison */}
                <Box w="full">
                  <HStack spacing={1}>
                    <Box flex={team1Prob}>
                      <Progress
                        value={100}
                        size="md"
                        colorScheme="cyan"
                        borderRadius="full"
                        bg="space.900"
                      />
                    </Box>
                    <Box flex={team2Prob}>
                      <Progress
                        value={100}
                        size="md"
                        colorScheme="orange"
                        borderRadius="full"
                        bg="space.900"
                      />
                    </Box>
                  </HStack>
                </Box>
              </VStack>
            </Box>
          )}
        </VStack>
      </Box>
    </Box>
    </VStack>
  );
};

export default MatchHeader;
