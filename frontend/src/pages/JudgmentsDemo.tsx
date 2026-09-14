/**
 * Judgments Demo Page
 *
 * Standalone harness for exercising JudgmentCapture and PostgameFeedback
 * without needing them wired into TeamGenerator/MatchDetail yet (those pages
 * are owned by concurrent work this session). Lets an organizer type in a
 * roster/match by hand and try the full create -> edit -> lock -> feedback
 * flow against the real API.
 */
import { useState } from 'react';
import {
  Box,
  Container,
  FormControl,
  FormLabel,
  Grid,
  GridItem,
  Input,
  Text,
  VStack,
} from '@chakra-ui/react';
import PageHeader from '../components/PageHeader';
import JudgmentCapture from '../components/JudgmentCapture';
import PostgameFeedback from '../components/PostgameFeedback';

/** Parses "1, 2, 3" into [1, 2, 3], dropping anything that isn't a positive integer. */
const parseIds = (raw: string): number[] =>
  raw
    .split(',')
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => Number.isInteger(n) && n > 0);

const JudgmentsDemo: React.FC = () => {
  const [team1Raw, setTeam1Raw] = useState('1, 2');
  const [team2Raw, setTeam2Raw] = useState('3, 4');
  const [mapName, setMapName] = useState('Site Delta');
  const [matchIdRaw, setMatchIdRaw] = useState('');

  const team1PlayerIds = parseIds(team1Raw);
  const team2PlayerIds = parseIds(team2Raw);
  const matchId = matchIdRaw.trim() ? parseInt(matchIdRaw.trim(), 10) : undefined;

  return (
    <Box minH="100vh" pb={16}>
      <PageHeader
        kicker="Internal Tooling"
        title="Judgments [Demo]"
        description="Test harness for the pre-game judgment and post-game feedback components against the real API - not linked from navigation."
      />
      <Container maxW="container.lg" pt={8}>
        <VStack align="stretch" spacing={8}>
          <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" p={5}>
            <Text fontFamily="heading" fontSize="sm" fontWeight="700" letterSpacing="0.08em" textTransform="uppercase" color="gray.300" mb={4}>
              Scenario Inputs
            </Text>
            <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={4}>
              <GridItem>
                <FormControl>
                  <FormLabel fontSize="xs" color="gray.500">Team 1 player IDs</FormLabel>
                  <Input
                    size="sm"
                    bg="space.900"
                    borderColor="space.700"
                    value={team1Raw}
                    onChange={(e) => setTeam1Raw(e.target.value)}
                    placeholder="e.g. 1, 2"
                  />
                </FormControl>
              </GridItem>
              <GridItem>
                <FormControl>
                  <FormLabel fontSize="xs" color="gray.500">Team 2 player IDs</FormLabel>
                  <Input
                    size="sm"
                    bg="space.900"
                    borderColor="space.700"
                    value={team2Raw}
                    onChange={(e) => setTeam2Raw(e.target.value)}
                    placeholder="e.g. 3, 4"
                  />
                </FormControl>
              </GridItem>
              <GridItem>
                <FormControl>
                  <FormLabel fontSize="xs" color="gray.500">Map name (optional)</FormLabel>
                  <Input
                    size="sm"
                    bg="space.900"
                    borderColor="space.700"
                    value={mapName}
                    onChange={(e) => setMapName(e.target.value)}
                  />
                </FormControl>
              </GridItem>
              <GridItem>
                <FormControl>
                  <FormLabel fontSize="xs" color="gray.500">Match ID (optional - for feedback below)</FormLabel>
                  <Input
                    size="sm"
                    bg="space.900"
                    borderColor="space.700"
                    value={matchIdRaw}
                    onChange={(e) => setMatchIdRaw(e.target.value)}
                    placeholder="e.g. 42"
                  />
                </FormControl>
              </GridItem>
            </Grid>
          </Box>

          <JudgmentCapture
            team1PlayerIds={team1PlayerIds}
            team2PlayerIds={team2PlayerIds}
            mapName={mapName || undefined}
            matchId={matchId}
            modelVersion="demo-harness"
            modelPredictedTeam1WinProb={0.5}
          />

          <PostgameFeedback matchId={matchId} />
        </VStack>
      </Container>
    </Box>
  );
};

export default JudgmentsDemo;
