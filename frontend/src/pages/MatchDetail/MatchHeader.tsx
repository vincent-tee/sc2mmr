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
  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');
  const winnerBg = useColorModeValue('green.50', 'rgba(0, 255, 136, 0.1)');
  const loserBg = useColorModeValue('red.50', 'rgba(239, 68, 68, 0.1)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');

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
      <Card
        bg={cardBg}
        border="2px solid"
        borderColor={borderColor}
        boxShadow="0 8px 32px rgba(0, 212, 255, 0.2)"
        position="relative"
        overflow="hidden"
        _before={{
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background:
            'linear-gradient(90deg, rgba(0, 212, 255, 0.8), rgba(255, 179, 0, 0.8))',
        }}
      >
        <CardBody>
          <VStack align="stretch" spacing={6}>
            {/* Match Title and Duration */}
            <Flex justify="space-between" align="start" flexWrap="wrap" gap={4}>
            <VStack align="start" spacing={2}>
              <HStack spacing={3}>
                <Icon as={FiActivity} boxSize={6} color="brand.400" />
                <Heading
                  size="2xl"
                  fontFamily="heading"
                  letterSpacing="wider"
                >
                  {match.map_name}
                </Heading>
                <Badge
                  colorScheme="blue"
                  fontSize="lg"
                  px={4}
                  py={1}
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
              <StatLabel fontFamily="heading" color="brand.400">
                Match Duration
              </StatLabel>
              <StatNumber fontSize="3xl" fontFamily="heading">
                {formatDuration(match.duration_seconds)}
              </StatNumber>
            </Stat>
          </Flex>

          {/* Win Probability Section */}
          {hasWinProb && (
            <Box>
              <Divider my={4} borderColor="whiteAlpha.200" />

              {/* Upset Alert */}
              {upsetIndicator && (
                <Alert
                  status="warning"
                  variant="left-accent"
                  mb={4}
                  bg="rgba(255, 179, 0, 0.1)"
                  borderColor="accent.500"
                  borderWidth="2px"
                >
                  <Icon
                    as={FiAlertTriangle}
                    boxSize={6}
                    mr={3}
                    color="accent.500"
                  />
                  <Box>
                    <Text
                      fontWeight="bold"
                      fontSize="lg"
                      fontFamily="heading"
                      letterSpacing="wider"
                    >
                      {upsetIndicator}
                    </Text>
                    <Text fontSize="sm" mt={1}>
                      The underdog team defied the odds and secured victory!
                    </Text>
                  </Box>
                </Alert>
              )}

              <VStack spacing={4}>
                <Heading
                  size="md"
                  fontFamily="heading"
                  letterSpacing="wider"
                  color="brand.400"
                >
                  Win Probability Analysis
                </Heading>

                <Grid
                  templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }}
                  gap={6}
                  w="full"
                >
                  {/* Team 1 Prediction */}
                  <Card
                    bg={team1Won ? winnerBg : loserBg}
                    border="2px solid"
                    borderColor={team1Won ? 'shield.500' : 'red.500'}
                    boxShadow={
                      team1Won ? '0 0 20px rgba(0, 255, 136, 0.3)' : 'none'
                    }
                  >
                    <CardBody>
                      <VStack spacing={3}>
                        <HStack>
                          <Icon
                            as={FiTrendingUp}
                            color="brand.400"
                            boxSize={5}
                          />
                          <Text
                            fontFamily="heading"
                            fontWeight="bold"
                            color="brand.400"
                          >
                            Team 1
                          </Text>
                          {team1Won && (
                            <Badge colorScheme="green" ml="auto">
                              <Icon as={FiAward} mr={1} />
                              Victory
                            </Badge>
                          )}
                        </HStack>
                         <Stat textAlign="center">
                           <StatLabel fontSize="xs" color="gray.500">
                             Predicted Win Chance
                           </StatLabel>
                           <StatNumber
                             fontSize="4xl"
                             fontFamily="heading"
                             color={
                               team1Prob > 0.5 ? 'shield.500' : 'gray.400'
                             }
                           >
                             {formatWinProbability(team1Prob)}
                           </StatNumber>
                           {predictedWinningTeam === 1 && (
                             <StatHelpText>
                               {team1Won
                                 ? 'Prediction: Correct'
                                 : 'Prediction: Incorrect'}
                             </StatHelpText>
                           )}
                         </Stat>
                      </VStack>
                    </CardBody>
                  </Card>

                  {/* VS Divider */}
                  <Flex align="center" justify="center">
                    <Box textAlign="center">
                      <Icon as={FiZap} boxSize={12} color="accent.500" mb={2} />
                      <Text
                        fontFamily="heading"
                        fontSize="2xl"
                        fontWeight="black"
                        letterSpacing="wider"
                        color="accent.500"
                      >
                        VS
                      </Text>
                    </Box>
                  </Flex>

                  {/* Team 2 Prediction */}
                  <Card
                    bg={!team1Won ? winnerBg : loserBg}
                    border="2px solid"
                    borderColor={!team1Won ? 'shield.500' : 'red.500'}
                    boxShadow={
                      !team1Won ? '0 0 20px rgba(0, 255, 136, 0.3)' : 'none'
                    }
                  >
                    <CardBody>
                      <VStack spacing={3}>
                        <HStack>
                          <Icon
                            as={FiTrendingUp}
                            color="accent.400"
                            boxSize={5}
                          />
                          <Text
                            fontFamily="heading"
                            fontWeight="bold"
                            color="accent.400"
                          >
                            Team 2
                          </Text>
                          {!team1Won && (
                            <Badge colorScheme="green" ml="auto">
                              <Icon as={FiAward} mr={1} />
                              Victory
                            </Badge>
                          )}
                        </HStack>
                         <Stat textAlign="center">
                           <StatLabel fontSize="xs" color="gray.500">
                             Predicted Win Chance
                           </StatLabel>
                           <StatNumber
                             fontSize="4xl"
                             fontFamily="heading"
                             color={
                               team2Prob > 0.5 ? 'shield.500' : 'gray.400'
                             }
                           >
                             {formatWinProbability(team2Prob)}
                           </StatNumber>
                           {predictedWinningTeam === 2 && (
                             <StatHelpText>
                               {!team1Won
                                 ? 'Prediction: Correct'
                                 : 'Prediction: Incorrect'}
                             </StatHelpText>
                           )}
                         </Stat>
                      </VStack>
                    </CardBody>
                  </Card>
                </Grid>

                {/* Visual probability comparison */}
                <Box w="full">
                  <HStack spacing={1}>
                    <Box flex={team1Prob}>
                      <Progress
                        value={100}
                        size="xl"
                        colorScheme="cyan"
                        borderRadius="md"
                        bg="gray.700"
                        sx={{
                          '& > div': {
                            background:
                              'linear-gradient(90deg, rgba(0, 212, 255, 0.6), rgba(0, 212, 255, 1))',
                            boxShadow: '0 0 15px rgba(0, 212, 255, 0.6)',
                          },
                        }}
                      />
                    </Box>
                    <Box flex={team2Prob}>
                      <Progress
                        value={100}
                        size="xl"
                        colorScheme="orange"
                        borderRadius="md"
                        bg="gray.700"
                        sx={{
                          '& > div': {
                            background:
                              'linear-gradient(90deg, rgba(255, 179, 0, 1), rgba(255, 179, 0, 0.6))',
                            boxShadow: '0 0 15px rgba(255, 179, 0, 0.6)',
                          },
                        }}
                      />
                    </Box>
                  </HStack>
                </Box>
              </VStack>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
    </VStack>
  );
};

export default MatchHeader;
