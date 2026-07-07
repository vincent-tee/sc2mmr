/**
 * CommentaryTab Component - AI-generated match commentary
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
  Icon,
  Grid,
  GridItem,
  Alert,
  AlertIcon,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  FiZap,
  FiAward,
  FiTarget,
  FiTrendingUp,
} from 'react-icons/fi';
import LoadingState from '@/components/LoadingState';
import MatchSHAPExplainer from '@/components/MatchSHAPExplainer';
import type { MatchCommentary } from './types';
import type { MatchDetail as MatchDetailType } from '@/types/api';

interface CommentaryTabProps {
  commentary: MatchCommentary | undefined;
  isLoading: boolean;
  matchData?: MatchDetailType;
}

const CommentaryTab: React.FC<CommentaryTabProps> = ({
  commentary,
  isLoading,
  matchData,
}) => {
  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.8)');
  const teamBg = useColorModeValue('gray.50', 'rgba(30, 41, 59, 0.5)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');

  if (isLoading) {
    return <LoadingState message="Generating tactical analysis..." />;
  }

  if (!commentary || commentary.error) {
    return (
      <Alert status="info">
        <AlertIcon />
        Tactical commentary is only available for advanced replay uploads.
      </Alert>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      {/* Match Overview */}
      <Grid templateColumns={{ base: '1fr', lg: '3fr 2fr' }} gap={6}>
        <GridItem>
          <Card bg={cardBg} border="2px solid" borderColor={borderColor} h="full">
            <CardBody>
              <Heading
                size="md"
                mb={3}
                fontFamily="heading"
                letterSpacing="wider"
              >
                Match Overview
              </Heading>
              <Text lineHeight="tall">{commentary.overview}</Text>
            </CardBody>
          </Card>
        </GridItem>
        <GridItem>
          {commentary.shap_impacts && (
            <MatchSHAPExplainer impacts={commentary.shap_impacts} />
          )}
        </GridItem>
      </Grid>

      {/* Key Moments */}
      <Card bg={cardBg} border="2px solid" borderColor={borderColor}>
        <CardBody>
          <HStack mb={4}>
            <Icon as={FiZap} color="yellow.500" />
            <Heading
              size="md"
              fontFamily="heading"
              letterSpacing="wider"
            >
              Critical Moments
            </Heading>
          </HStack>
          <VStack align="stretch" spacing={3}>
            {(commentary.key_moments ?? []).map((moment, idx) => (
              <Box
                key={idx}
                p={3}
                bg={teamBg}
                borderRadius="md"
                borderLeft="4px solid"
                borderLeftColor="brand.500"
              >
                <Text>{moment}</Text>
              </Box>
            ))}
          </VStack>
        </CardBody>
      </Card>

      {/* MVP Analysis */}
      {commentary.mvp_analysis &&
        commentary.mvp_analysis.player_name !== 'Unknown' && (
          <Card
            bg={cardBg}
            borderWidth="3px"
            borderColor="yellow.400"
            boxShadow="0 0 30px rgba(255, 215, 0, 0.3)"
          >
            <CardBody>
              <HStack mb={4}>
                <Icon as={FiAward} color="yellow.500" boxSize={6} />
                <Heading
                  size="md"
                  fontFamily="heading"
                  letterSpacing="wider"
                >
                  Match MVP
                </Heading>
              </HStack>
              <VStack align="stretch" spacing={3}>
                <HStack>
                  <Text
                    fontWeight="bold"
                    fontSize="xl"
                    fontFamily="heading"
                  >
                    {commentary.mvp_analysis.player_name}
                  </Text>
                  <Badge colorScheme="yellow" fontSize="md">
                    Team {commentary.mvp_analysis.team}
                  </Badge>
                  {commentary.mvp_analysis.impact_score && (
                    <Badge colorScheme="green" fontSize="md">
                      Impact: {commentary.mvp_analysis.impact_score.toFixed(1)}
                    </Badge>
                  )}
                </HStack>
                <Text lineHeight="tall">
                  {commentary.mvp_analysis.reasoning}
                </Text>
              </VStack>
            </CardBody>
          </Card>
        )}

      {/* Player Performances */}
      <Card bg={cardBg} border="2px solid" borderColor={borderColor}>
        <CardBody>
          <HStack mb={4}>
            <Icon as={FiTarget} color="blue.500" />
            <Heading
              size="md"
              fontFamily="heading"
              letterSpacing="wider"
            >
              Player Performance
            </Heading>
          </HStack>
          <VStack align="stretch" spacing={4}>
            {Object.entries(commentary.player_performances ?? {}).map(
              ([name, analysis]) => {
                const playerInfo = matchData?.players.find(p => p.player_name === name);
                const race = playerInfo?.race || 'Random';
                const won = playerInfo?.won || false;
                
                return (
                  <Box 
                    key={name} 
                    p={4} 
                    bg={teamBg} 
                    borderRadius="md"
                    borderLeft="4px solid"
                    borderLeftColor={won ? 'green.400' : 'red.400'}
                  >
                    <HStack mb={2} justify="space-between">
                      <HStack>
                        <Heading size="sm" fontFamily="heading">
                          {name}
                        </Heading>
                        <Badge colorScheme={won ? 'green' : 'red'} variant="outline" fontSize="2xs">
                          {won ? 'Winner' : 'Defeat'}
                        </Badge>
                        <Badge variant={`race-${race.toLowerCase()}`} fontSize="2xs">
                          {race}
                        </Badge>
                      </HStack>
                    </HStack>
                    <Text fontSize="sm" lineHeight="tall" color="gray.300">
                      {analysis}
                    </Text>
                  </Box>
                );
              }
            )}
          </VStack>
        </CardBody>
      </Card>

      {/* Team Analysis */}
      {commentary.team_analysis && (
        <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={6}>
          <GridItem>
            <Card bg={cardBg} border="2px solid" borderColor={borderColor}>
              <CardBody>
                <Heading
                  size="md"
                  mb={3}
                  fontFamily="heading"
                  letterSpacing="wider"
                  color="brand.400"
                >
                  Team 1 Analysis
                </Heading>
                <Text fontSize="sm" lineHeight="tall">
                  {commentary.team_analysis.team_1}
                </Text>
              </CardBody>
            </Card>
          </GridItem>
          <GridItem>
            <Card bg={cardBg} border="2px solid" borderColor={borderColor}>
              <CardBody>
                <Heading
                  size="md"
                  mb={3}
                  fontFamily="heading"
                  letterSpacing="wider"
                  color="accent.400"
                >
                  Team 2 Analysis
                </Heading>
                <Text fontSize="sm" lineHeight="tall">
                  {commentary.team_analysis.team_2}
                </Text>
              </CardBody>
            </Card>
          </GridItem>
        </Grid>
      )}

      {/* Match Summary */}
      <Card bg={cardBg} border="2px solid" borderColor={borderColor}>
        <CardBody>
          <HStack mb={4}>
            <Icon as={FiTrendingUp} color="purple.500" />
            <Heading
              size="md"
              fontFamily="heading"
              letterSpacing="wider"
            >
              Final Assessment
            </Heading>
          </HStack>
          <Text lineHeight="tall" fontSize="md">
            {commentary.match_summary}
          </Text>
        </CardBody>
      </Card>
    </VStack>
  );
};

export default CommentaryTab;
