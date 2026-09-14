/**
 * JudgmentCapture
 *
 * Compact, self-contained widget for recording an organizer's pre-game
 * team-balance judgment alongside a balance suggestion. Designed to be
 * dropped into TeamGenerator/index.tsx later with one import + one JSX
 * line - it owns its own form state, submission, and lock action, and only
 * needs the suggestion context passed in as props.
 *
 * Not wired into any page yet: TeamGenerator/index.tsx is owned by
 * concurrent work this session.
 */
import { useEffect, useRef, useState } from 'react';
import {
  Badge,
  Box,
  Button,
  ButtonGroup,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Select,
  Text,
  Textarea,
  VStack,
} from '@chakra-ui/react';
import { FiCheckCircle, FiLock } from 'react-icons/fi';
import { judgmentsApi } from '../api/judgments';
import type {
  HumanEstimate,
  JudgmentConfidence,
  JudgmentReason,
  JudgmentResponse,
  PlayerRaceContext,
} from '../api/judgments';
import { useToast } from '../hooks/useToast';

const AUTHOR_STORAGE_KEY = 'sc2mmr_judgment_author';

const ESTIMATE_OPTIONS: { value: HumanEstimate; label: string }[] = [
  { value: 'team1_favored', label: 'Team 1' },
  { value: 'even', label: 'Even' },
  { value: 'team2_favored', label: 'Team 2' },
];

const CONFIDENCE_OPTIONS: { value: JudgmentConfidence; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

const REASON_OPTIONS: { value: JudgmentReason; label: string }[] = [
  { value: 'off_race', label: 'Off-race' },
  { value: 'returning_player', label: 'Returning player' },
  { value: 'current_form', label: 'Current form' },
  { value: 'communication', label: 'Communication' },
  { value: 'map', label: 'Map' },
  { value: 'known_synergy', label: 'Known synergy' },
  { value: 'other', label: 'Other' },
];

export interface JudgmentCaptureProps {
  /** Roster the suggestion is for - required, mirrors CreateJudgmentRequest. */
  team1PlayerIds: number[];
  team2PlayerIds: number[];
  /** Optional context snapshotted from the balance suggestion being judged. */
  mapName?: string;
  team1Context?: PlayerRaceContext[];
  team2Context?: PlayerRaceContext[];
  modelVersion?: string;
  modelPredictedTeam1WinProb?: number;
  balancePredictionId?: number;
  /** Known post-upload; omit when judging before a match exists. */
  matchId?: number;
  /** Fires after a successful create/update/lock, e.g. to refresh a parent list. */
  onSaved?: (judgment: JudgmentResponse) => void;
}

const JudgmentCaptureForm: React.FC<JudgmentCaptureProps> = ({
  team1PlayerIds,
  team2PlayerIds,
  mapName,
  team1Context,
  team2Context,
  modelVersion,
  modelPredictedTeam1WinProb,
  balancePredictionId,
  matchId,
  onSaved,
}) => {
  const toast = useToast();
  const [judgment, setJudgment] = useState<JudgmentResponse | null>(null);
  const [editing, setEditing] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [locking, setLocking] = useState(false);

  const [author, setAuthor] = useState(
    () => localStorage.getItem(AUTHOR_STORAGE_KEY) ?? ''
  );
  const [humanEstimate, setHumanEstimate] = useState<HumanEstimate>('even');
  const [humanProbability, setHumanProbability] = useState('50');
  const [confidence, setConfidence] = useState<JudgmentConfidence>('medium');
  const [reason, setReason] = useState<JudgmentReason>('other');
  const [reasonNote, setReasonNote] = useState('');
  const [loadingSaved, setLoadingSaved] = useState(!!balancePredictionId);
  const onSavedRef = useRef(onSaved);
  onSavedRef.current = onSaved;
  const contextKey = (context?: PlayerRaceContext[] | null) => JSON.stringify(
    [...(context ?? [])].sort((a, b) => a.player_id - b.player_id));
  const rosterKey = JSON.stringify([
    [...team1PlayerIds].sort((a,b) => a-b).join(','), [...team2PlayerIds].sort((a,b) => a-b).join(','),
    mapName ?? null, contextKey(team1Context), contextKey(team2Context),
  ]);
  useEffect(() => {
    if (!balancePredictionId) return;
    let active = true;
    judgmentsApi.list({ balancePredictionId }).then(({ data }) => {
      if (!active) return;
      const saved = data.find(j => JSON.stringify([j.team1_player_ids_key, j.team2_player_ids_key,
        j.map_name, contextKey(j.team1_context), contextKey(j.team2_context)]) === rosterKey);
      if (saved) {
        setJudgment(saved); setEditing(false); setAuthor(saved.author);
        setHumanEstimate(saved.human_estimate);
        setHumanProbability(String((saved.human_win_prob ?? .5) * 100));
        setConfidence(saved.confidence); setReason(saved.reason); setReasonNote(saved.reason_note ?? '');
        onSavedRef.current?.(saved);
      }
    }).catch(() => {}).finally(() => { if (active) setLoadingSaved(false); });
    return () => { active = false; };
  }, [balancePredictionId, rosterKey]);


  const probability = Number(humanProbability);
  const validProbability = humanProbability.trim() !== '' && Number.isFinite(probability) && probability >= 0 && probability <= 100;
  const canSubmit = !loadingSaved && validProbability && author.trim().length > 0 && team1PlayerIds.length > 0 && team2PlayerIds.length > 0;

  const handleAuthorChange = (value: string) => {
    setAuthor(value);
    localStorage.setItem(AUTHOR_STORAGE_KEY, value);
  };

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return;
    setSubmitting(true);
    try {
      if (judgment) {
        const { data } = await judgmentsApi.update(judgment.id, {
          human_estimate: humanEstimate,
          human_win_prob: probability / 100,
          confidence,
          reason,
          reason_note: reasonNote || null,
        });
        setJudgment(data);
        onSaved?.(data);
        toast.success('Judgment updated');
      } else {
        const { data } = await judgmentsApi.create({
          team1_player_ids: team1PlayerIds,
          team2_player_ids: team2PlayerIds,
          map_name: mapName,
          team1_context: team1Context,
          team2_context: team2Context,
          model_version: modelVersion,
          model_predicted_team1_win_prob: modelPredictedTeam1WinProb,
          balance_prediction_id: balancePredictionId,
          match_id: matchId,
          human_estimate: humanEstimate,
          human_win_prob: probability / 100,
          confidence,
          reason,
          reason_note: reasonNote || null,
          author: author.trim(),
        });
        setJudgment(data);
        onSaved?.(data);
        toast.success('Judgment recorded');
      }
      setEditing(false);
    } catch (err) {
      const message = (err as { userMessage?: string })?.userMessage || 'Failed to save judgment';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleLock = async () => {
    if (!judgment || locking) return;
    setLocking(true);
    try {
      const { data } = await judgmentsApi.lock(judgment.id);
      setJudgment(data);
      onSaved?.(data);
      toast.success(balancePredictionId ? 'Game started — teams and judgment saved' : 'Judgment locked');
    } catch (err) {
      const message = (err as { userMessage?: string })?.userMessage || 'Failed to lock judgment';
      toast.error(message);
    } finally {
      setLocking(false);
    }
  };

  const isLocked = !!judgment?.is_locked;

  return (
    <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" p={5}>
      <HStack justify="space-between" mb={4}>
        <Text fontFamily="heading" fontSize="sm" fontWeight="700" letterSpacing="0.08em" textTransform="uppercase" color="gray.300">
          Pre-Game Judgment
        </Text>
        {judgment && (
          <Badge
            display="flex"
            alignItems="center"
            gap={1}
            bg={isLocked ? 'accent.500' : 'space.700'}
            color={isLocked ? 'space.900' : 'gray.300'}
            fontSize="xs"
            px={2}
            py={1}
            borderRadius="md"
          >
            {isLocked ? <FiLock size={11} /> : <FiCheckCircle size={11} />}
            {isLocked ? 'Locked' : 'Saved'}
          </Badge>
        )}
      </HStack>

      {!editing && judgment ? (
        <VStack align="stretch" spacing={3}>
          <HStack spacing={4} flexWrap="wrap">
            <VStack align="start" spacing={0}>
              <Text fontSize="xs" color="gray.500">Estimate</Text>
              <Text fontFamily="mono" color="gray.100">
                {ESTIMATE_OPTIONS.find((o) => o.value === judgment.human_estimate)?.label}
              </Text>
            </VStack>
            <VStack align="start" spacing={0}>
              <Text fontSize="xs" color="gray.500">Confidence</Text>
              <Text fontFamily="mono" color="gray.100">
                {CONFIDENCE_OPTIONS.find((o) => o.value === judgment.confidence)?.label}
              </Text>
            </VStack>
            <VStack align="start" spacing={0}>
              <Text fontSize="xs" color="gray.500">Reason</Text>
              <Text fontFamily="mono" color="gray.100">
                {REASON_OPTIONS.find((o) => o.value === judgment.reason)?.label}
              </Text>
            </VStack>
          </HStack>
          {judgment.reason_note && (
            <Text fontSize="sm" color="gray.400" fontStyle="italic">
              &ldquo;{judgment.reason_note}&rdquo;
            </Text>
          )}
          <Text fontSize="sm">Your Team 1 estimate: {Math.round((judgment.human_win_prob ?? 0.5) * 100)}%</Text>
          {judgment.model_predicted_team1_win_prob != null && (
            <Text fontSize="sm">Model estimate for these teams: {Math.round(judgment.model_predicted_team1_win_prob * 100)}%</Text>
          )}
          {judgment.selection_id && <Text fontSize="sm" color="green.300">Game #{judgment.selection_id} recorded. After uploading, confirm this selection on the match page.</Text>}
          <Text fontSize="xs" color="gray.600">By {judgment.author}</Text>
          <HStack spacing={3}>
            {!isLocked && (
              <>
                <Button size="sm" variant="ghost" color="gray.300" onClick={() => setEditing(true)}>
                  Edit
                </Button>
                <Button
                  size="sm"
                  bg="accent.500"
                  color="space.900"
                  _hover={{ bg: 'accent.400' }}
                  leftIcon={<FiLock />}
                  onClick={handleLock}
                  isLoading={locking}
                >
                  {balancePredictionId ? 'Start game with these teams' : 'Lock'}
                </Button>
              </>
            )}
          </HStack>
        </VStack>
      ) : (
        <VStack align="stretch" spacing={4}>
          <FormControl>
            <FormLabel fontSize="xs" color="gray.500">Who's favored?</FormLabel>
            <ButtonGroup isAttached size="sm" w="100%">
              {ESTIMATE_OPTIONS.map((opt) => (
                <Button
                  key={opt.value}
                  flex={1}
                  bg={humanEstimate === opt.value ? 'brand.500' : 'space.900'}
                  color={humanEstimate === opt.value ? 'white' : 'gray.400'}
                  borderColor="space.700"
                  _hover={{ bg: humanEstimate === opt.value ? 'brand.600' : 'space.700' }}
                  onClick={() => { setHumanEstimate(opt.value); setHumanProbability(opt.value === 'even' ? '50' : opt.value === 'team1_favored' ? '65' : '35'); }}
                >
                  {opt.label}
                </Button>
              ))}
            </ButtonGroup>
          </FormControl>

          <HStack spacing={4} align="start">
            <FormControl>
              <FormLabel fontSize="xs" color="gray.500">Confidence</FormLabel>
              <Select
                size="sm"
                bg="space.900"
                borderColor="space.700"
                value={confidence}
                onChange={(e) => setConfidence(e.target.value as JudgmentConfidence)}
              >
                {CONFIDENCE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </Select>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="xs" color="gray.500">Reason</FormLabel>
              <Select
                size="sm"
                bg="space.900"
                borderColor="space.700"
                value={reason}
                onChange={(e) => setReason(e.target.value as JudgmentReason)}
              >
                {REASON_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </Select>
            </FormControl>
          </HStack>

          <FormControl>
            <FormLabel fontSize="xs" color="gray.500">Note (optional)</FormLabel>
            <Textarea
              size="sm"
              bg="space.900"
              borderColor="space.700"
              rows={2}
              placeholder="Anything specific driving this read?"
              value={reasonNote}
              onChange={(e) => setReasonNote(e.target.value)}
            />
          </FormControl>

          <FormControl isRequired>
            <FormLabel fontSize="xs">Your estimate of Team 1 winning (%)</FormLabel>
            <Input type="number" min={0} max={100} value={humanProbability}
              onChange={(e) => {
                setHumanProbability(e.target.value);
                const value = Number(e.target.value);
                setHumanEstimate(value > 50 ? 'team1_favored' : value < 50 ? 'team2_favored' : 'even');
              }} />
          </FormControl>
          <FormControl isRequired>
            <FormLabel fontSize="xs" color="gray.500">Your name</FormLabel>
            <Input
              size="sm"
              bg="space.900"
              borderColor="space.700"
              placeholder="Organizer name"
              value={author}
              onChange={(e) => handleAuthorChange(e.target.value)}
            />
          </FormControl>

          <HStack justify="flex-end" spacing={3}>
            {judgment && (
              <Button size="sm" variant="ghost" color="gray.400" onClick={() => setEditing(false)}>
                Cancel
              </Button>
            )}
            <Button
              size="sm"
              bg="brand.500"
              color="white"
              _hover={{ bg: 'brand.600' }}
              onClick={handleSubmit}
              isLoading={submitting}
              isDisabled={!canSubmit}
            >
              {judgment ? 'Save Changes' : 'Record Judgment'}
            </Button>
          </HStack>
        </VStack>
      )}
    </Box>
  );
};

const JudgmentCapture: React.FC<JudgmentCaptureProps> = (props) => (
  <JudgmentCaptureForm key={JSON.stringify([props.balancePredictionId, props.team1PlayerIds,
    props.team2PlayerIds, props.mapName, props.matchId, props.team1Context, props.team2Context])} {...props} />
);

export default JudgmentCapture;
