/**
 * One suggested split, editable in place: live win chance and match quality,
 * one-for-one swaps (by hand or suggested), race picks, and recording the game.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Button,
  Collapse,
  Flex,
  Grid,
  HStack,
  IconButton,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Select,
  Text,
  VStack,
  Badge,
  useToast,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { toBlob, toJpeg } from 'html-to-image';
import {
  FiChevronDown,
  FiClipboard,
  FiCopy,
  FiDownload,
  FiEdit3,
  FiImage,
  FiRepeat,
  FiRotateCcw,
  FiShare2,
  FiFlag,
} from 'react-icons/fi';
import VSScreen from '@/components/VSScreen';
import JudgmentCapture from '@/components/JudgmentCapture';
import { useAuth } from '@/components/AuthGate';
import apiClient from '@/api/client';
import { teamsApi } from '@/api/endpoints';
import { judgmentsApi } from '@/api/judgments';
import type { TeamPlayer, TeamSuggestionWithImpact } from '@/types/api';

interface SwapSuggestion {
  player_out_of_team_1: { id: number };
  player_out_of_team_2: { id: number };
  quality_delta: number;
}

interface SuggestSwapsResponse {
  suggestions: SwapSuggestion[];
}

interface TeamEditorProps {
  suggestion: TeamSuggestionWithImpact;
  onExport: (suggestion: TeamSuggestionWithImpact, format: 'text' | 'download') => Promise<void>;
}

const RACES = ['Terran', 'Protoss', 'Zerg', 'Random'];
const MEANINGFUL_QUALITY_GAIN = 0.01;

const idsOf = (team: TeamPlayer[]) => team.map((p) => p.id);
const sameRoster = (a: TeamPlayer[], b: TeamPlayer[]) =>
  [...idsOf(a)].sort((x, y) => x - y).join(',') === [...idsOf(b)].sort((x, y) => x - y).join(',');
const totalMMR = (team: TeamPlayer[]) => team.reduce((sum, p) => sum + p.mmr, 0);

const TeamEditor: React.FC<TeamEditorProps> = ({ suggestion, onExport }) => {
  const toast = useToast();
  const { authenticated, ensureSignedIn } = useAuth();
  const shareRef = useRef<HTMLDivElement>(null);

  const [team1, setTeam1] = useState<TeamPlayer[]>(suggestion.team_1.players);
  const [team2, setTeam2] = useState<TeamPlayer[]>(suggestion.team_2.players);
  const [races, setRaces] = useState<Record<number, string>>({});
  const [locked, setLocked] = useState(false);
  const [restoring, setRestoring] = useState(!!suggestion.balance_prediction_id);
  const [pendingSwap, setPendingSwap] = useState<{ team: 1 | 2; id: number } | null>(null);
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [recordOpen, setRecordOpen] = useState(false);

  useEffect(() => {
    if (!suggestion.balance_prediction_id || !authenticated) return;
    let active = true;
    judgmentsApi.list({ balancePredictionId: suggestion.balance_prediction_id }).then(({ data }) => {
      if (!active || !data.length) return;
      const saved = data.find((j) => j.is_locked) ?? data[0];
      const pool = [...suggestion.team_1.players, ...suggestion.team_2.players];
      const ids1 = saved.team1_player_ids_key.split(',').map(Number);
      const ids2 = saved.team2_player_ids_key.split(',').map(Number);
      setTeam1(pool.filter((p) => ids1.includes(p.id)));
      setTeam2(pool.filter((p) => ids2.includes(p.id)));
      setRaces(Object.fromEntries([...(saved.team1_context ?? []), ...(saved.team2_context ?? [])].map((c) => [c.player_id, c.race])));
      setLocked(saved.is_locked);
      setRecordOpen(true);
    }).catch(() => {}).finally(() => { if (active) setRestoring(false); });
    return () => { active = false; };
  }, [suggestion, authenticated]);

  const isEdited = !sameRoster(team1, suggestion.team_1.players) || !sameRoster(team2, suggestion.team_2.players);
  const hasGuests = [...team1, ...team2].some((p) => p.id < 0);
  const ids1 = idsOf(team1);
  const ids2 = idsOf(team2);

  const livePrediction = useQuery({
    queryKey: ['predict', ids1, ids2],
    queryFn: async () => (await teamsApi.predict(ids1, ids2)).data,
    enabled: authenticated && isEdited && !hasGuests,
  });

  const swapSuggestions = useQuery({
    queryKey: ['suggest-swaps', ids1, ids2],
    queryFn: async () => (await apiClient.post<SuggestSwapsResponse>('/teams/suggest-swaps', {
      team_1_ids: ids1,
      team_2_ids: ids2,
      top_n: 3,
    })).data,
    enabled: authenticated && adjustOpen && !locked && !hasGuests && team1.length > 0 && team2.length > 0,
  });

  const { team1WinChance, qualityPercent } = useMemo(() => {
    if (!isEdited) {
      return { team1WinChance: suggestion.win_probability_team_1, qualityPercent: suggestion.match_quality };
    }
    if (!livePrediction.data) return { team1WinChance: undefined, qualityPercent: undefined };
    return {
      team1WinChance: livePrediction.data.team_1.win_probability,
      qualityPercent: livePrediction.data.match_quality * 100,
    };
  }, [isEdited, livePrediction.data, suggestion]);

  const swapPlayers = (id1: number, id2: number) => {
    const out1 = team1.find((p) => p.id === id1);
    const out2 = team2.find((p) => p.id === id2);
    if (!out1 || !out2) return;
    setTeam1(team1.map((p) => (p.id === id1 ? out2 : p)));
    setTeam2(team2.map((p) => (p.id === id2 ? out1 : p)));
    setPendingSwap(null);
  };

  const pickForSwap = (team: 1 | 2, id: number) => {
    if (locked) return;
    if (!pendingSwap || pendingSwap.team === team) {
      setPendingSwap(pendingSwap?.id === id ? null : { team, id });
      return;
    }
    if (team === 2) swapPlayers(pendingSwap.id, id);
    else swapPlayers(id, pendingSwap.id);
  };

  const toggleAdjust = async () => {
    if (!adjustOpen && !(await ensureSignedIn('adjust teams'))) return;
    setAdjustOpen((open) => !open);
  };

  const openRecording = async () => {
    if (await ensureSignedIn('record this game')) setRecordOpen(true);
  };

  const resetSplit = () => {
    setTeam1(suggestion.team_1.players);
    setTeam2(suggestion.team_2.players);
    setPendingSwap(null);
  };

  const exportImage = async (mode: 'save' | 'copy') => {
    if (!shareRef.current) return;
    try {
      if (mode === 'save') {
        const dataUrl = await toJpeg(shareRef.current, { quality: 0.95, backgroundColor: '#0a0f1c' });
        const link = document.createElement('a');
        link.download = 'sc2-teams.jpg';
        link.href = dataUrl;
        link.click();
      } else {
        const blob = await toBlob(shareRef.current, { backgroundColor: '#0a0f1c' });
        if (!blob) throw new Error('Failed to create image');
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      }
      toast({ title: mode === 'save' ? 'Image saved' : 'Image copied', status: 'success', duration: 2000 });
    } catch {
      toast({ title: "Couldn't export the image", status: 'error', duration: 3000 });
    }
  };

  const toPanel = (team: TeamPlayer[], winChance: number | undefined) => ({
    players: team.map((p) => ({ name: p.name, mmr: Math.round(p.mmr), race: races[p.id] || p.favorite_race || 'Random' })),
    totalMMR: Math.round(totalMMR(team)),
    winProbability: winChance,
  });
  const team2WinChance = team1WinChance === undefined ? undefined : 100 - team1WinChance;
  const favoured = team1WinChance === undefined ? null : team1WinChance > 50 ? 1 : team1WinChance < 50 ? 2 : null;
  const currentSuggestion: TeamSuggestionWithImpact = {
    ...suggestion,
    team_1: { ...suggestion.team_1, players: team1 },
    team_2: { ...suggestion.team_2, players: team2 },
    win_probability_team_1: team1WinChance ?? suggestion.win_probability_team_1,
    win_probability_team_2: team2WinChance ?? suggestion.win_probability_team_2,
    match_quality: qualityPercent ?? suggestion.match_quality,
  };
  const usefulSwaps = (swapSuggestions.data?.suggestions ?? []).filter((s) => s.quality_delta > MEANINGFUL_QUALITY_GAIN);

  const renderAdjustColumn = (team: TeamPlayer[], teamNumber: 1 | 2) => (
    <VStack align="stretch" spacing={2}>
      <Text fontSize="xs" fontWeight="bold" color={teamNumber === 1 ? 'brand.400' : 'accent.400'} textTransform="uppercase" letterSpacing="widest">
        Team {teamNumber}
      </Text>
      {team.map((player) => {
        const isPending = pendingSwap?.team === teamNumber && pendingSwap.id === player.id;
        return (
          <HStack
            key={player.id}
            p={2}
            pl={3}
            borderRadius="md"
            bg={isPending ? 'whiteAlpha.200' : 'whiteAlpha.50'}
            border="1px solid"
            borderColor={isPending ? 'brand.400' : 'transparent'}
            spacing={2}
          >
            <Box
              as="button"
              flex={1}
              minW={0}
              textAlign="left"
              onClick={() => pickForSwap(teamNumber, player.id)}
              disabled={locked}
              aria-pressed={isPending}
              aria-label={`Pick ${player.name} to swap`}
            >
              <Text fontWeight="semibold" color="gray.100" noOfLines={1}>{player.name}</Text>
              <Text fontSize="xs" color="gray.500" fontFamily="mono">{Math.round(player.mmr).toLocaleString()}</Text>
            </Box>
            <Select
              aria-label={`Race for ${player.name}`}
              size="xs"
              maxW="110px"
              value={races[player.id] ?? ''}
              isDisabled={locked}
              onChange={(e) => setRaces({ ...races, [player.id]: e.target.value })}
            >
              <option value="">Race?</option>
              {RACES.map((race) => <option key={race}>{race}</option>)}
            </Select>
          </HStack>
        );
      })}
    </VStack>
  );

  return (
    <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" p={{ base: 3, md: 5 }}>
      <Box ref={shareRef}>
        <VSScreen
          team1={toPanel(team1, team1WinChance)}
          team2={toPanel(team2, team2WinChance)}
          winner={favoured}
          isPrediction
          probabilityLabel="Win chance"
        />
      </Box>

      <Flex mt={4} align="center" justify="space-between" gap={3} flexWrap="wrap">
        <HStack spacing={3} flexWrap="wrap" fontSize="sm" color="gray.400">
          <Text>
            Match quality{' '}
            <Text as="span" fontFamily="mono" fontWeight="bold" color="gray.100">
              {qualityPercent === undefined ? (hasGuests ? '—' : '…') : `${Math.round(qualityPercent)}%`}
            </Text>
          </Text>
          <Text>
            MMR gap{' '}
            <Text as="span" fontFamily="mono" fontWeight="bold" color="gray.100">
              {Math.round(Math.abs(totalMMR(team1) - totalMMR(team2))).toLocaleString()}
            </Text>
          </Text>
          {isEdited && <Badge colorScheme="orange" variant="subtle">Adjusted</Badge>}
          {isEdited && hasGuests && <Text fontSize="xs">Win chance isn't calculated for guests.</Text>}
        </HStack>
        <HStack spacing={2}>
          {isEdited && !locked && (
            <Button size="sm" variant="ghost" leftIcon={<FiRotateCcw />} onClick={resetSplit}>Reset</Button>
          )}
          <Button
            size="sm"
            variant={adjustOpen ? 'solid' : 'outline'}
            colorScheme="brand"
            leftIcon={<FiEdit3 />}
            onClick={toggleAdjust}
            aria-expanded={adjustOpen}
          >
            Adjust teams
          </Button>
          <Menu>
            <MenuButton as={IconButton} icon={<FiShare2 />} size="sm" variant="outline" aria-label="Share these teams" />
            <MenuList bg="space.800" borderColor="whiteAlpha.200" zIndex={20}>
              <MenuItem bg="transparent" icon={<FiClipboard />} onClick={() => exportImage('copy')} fontSize="sm">Copy as image</MenuItem>
              <MenuItem bg="transparent" icon={<FiImage />} onClick={() => exportImage('save')} fontSize="sm">Save as image</MenuItem>
              <MenuItem bg="transparent" icon={<FiCopy />} onClick={() => onExport(currentSuggestion, 'text')} fontSize="sm">Copy as text</MenuItem>
              <MenuItem bg="transparent" icon={<FiDownload />} onClick={() => onExport(currentSuggestion, 'download')} fontSize="sm">Download as text</MenuItem>
            </MenuList>
          </Menu>
        </HStack>
      </Flex>

      <Collapse in={adjustOpen} animateOpacity>
        <Box mt={4} pt={4} borderTop="1px solid" borderColor="whiteAlpha.100">
          <Text fontSize="sm" color="gray.400" mb={3}>
            {locked
              ? 'This game has started, so the teams are fixed.'
              : 'Tap a player on each team to swap them. Race picks are optional.'}
          </Text>
          <Grid templateColumns={{ base: '1fr', md: '1fr 1fr' }} gap={4}>
            {renderAdjustColumn(team1, 1)}
            {renderAdjustColumn(team2, 2)}
          </Grid>
          {!locked && !hasGuests && (
            <Box mt={4}>
              <Text fontSize="xs" fontWeight="bold" color="gray.500" textTransform="uppercase" letterSpacing="widest" mb={2}>
                Suggested swaps
              </Text>
              {swapSuggestions.isLoading ? (
                <Text fontSize="sm" color="gray.500">Checking swaps…</Text>
              ) : usefulSwaps.length === 0 ? (
                <Text fontSize="sm" color="gray.500">No single swap makes this split meaningfully fairer.</Text>
              ) : (
                <VStack align="stretch" spacing={2}>
                  {usefulSwaps.map((swap) => {
                    const out1 = team1.find((p) => p.id === swap.player_out_of_team_1.id);
                    const out2 = team2.find((p) => p.id === swap.player_out_of_team_2.id);
                    if (!out1 || !out2) return null;
                    return (
                      <HStack key={`${out1.id}-${out2.id}`} justify="space-between" p={2} pl={3} bg="whiteAlpha.50" borderRadius="md" spacing={3}>
                        <HStack spacing={2} minW={0} fontSize="sm">
                          <FiRepeat />
                          <Text noOfLines={1}>
                            <Text as="span" color="brand.300" fontWeight="bold">{out1.name}</Text> ↔ <Text as="span" color="accent.300" fontWeight="bold">{out2.name}</Text>
                          </Text>
                        </HStack>
                        <HStack spacing={3} flexShrink={0}>
                          <Text fontSize="xs" color="green.400" fontFamily="mono">quality +{Math.round(swap.quality_delta * 100)}%</Text>
                          <Button size="xs" colorScheme="brand" onClick={() => swapPlayers(out1.id, out2.id)}>Apply</Button>
                        </HStack>
                      </HStack>
                    );
                  })}
                </VStack>
              )}
            </Box>
          )}
        </Box>
      </Collapse>

      <Box mt={4} pt={4} borderTop="1px solid" borderColor="whiteAlpha.100">
        {!suggestion.balance_prediction_id ? (
          <Text fontSize="sm" color="gray.500">Recording a game is available for generated teams of registered players.</Text>
        ) : !authenticated ? (
          <Button size="sm" variant="outline" leftIcon={<FiFlag />} onClick={openRecording}>Sign in to record this game</Button>
        ) : restoring ? (
          <Text fontSize="sm" color="gray.500">Loading saved game…</Text>
        ) : (
          <>
            <Button
              size="sm"
              variant={recordOpen ? 'solid' : 'outline'}
              leftIcon={<FiFlag />}
              rightIcon={<FiChevronDown style={{ transform: recordOpen ? 'rotate(180deg)' : undefined }} />}
              onClick={() => setRecordOpen((open) => !open)}
              aria-expanded={recordOpen}
            >
              {locked ? 'Game recorded' : 'Record this game'}
            </Button>
            <Collapse in={recordOpen} animateOpacity>
              <Box mt={3}>
                <JudgmentCapture
                  balancePredictionId={suggestion.balance_prediction_id}
                  mapName={suggestion.map_name ?? undefined}
                  team1PlayerIds={ids1}
                  team2PlayerIds={ids2}
                  team1Context={team1.filter((p) => races[p.id]).map((p) => ({ player_id: p.id, race: races[p.id] }))}
                  team2Context={team2.filter((p) => races[p.id]).map((p) => ({ player_id: p.id, race: races[p.id] }))}
                  onSaved={(judgment) => setLocked(judgment.is_locked)}
                />
              </Box>
            </Collapse>
          </>
        )}
      </Box>
    </Box>
  );
};

export default TeamEditor;
