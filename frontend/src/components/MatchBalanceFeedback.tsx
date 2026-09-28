import { useEffect, useState } from 'react';
import { Box, Button, Collapse, HStack, Text, VStack } from '@chakra-ui/react';
import { FiChevronDown, FiMessageSquare } from 'react-icons/fi';
import { judgmentsApi, selectionsApi } from '@/api/judgments';
import type { BalanceSelection, JudgmentResponse } from '@/api/judgments';
import { useToast } from '@/hooks/useToast';
import PostgameFeedback from './PostgameFeedback';

export default function MatchBalanceFeedback({ matchId }: { matchId: number }) {
  const [candidates, setCandidates] = useState<BalanceSelection[]>([]);
  const [judgments, setJudgments] = useState<JudgmentResponse[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const toast = useToast();
  useEffect(() => {
    let active = true;
    Promise.all([selectionsApi.candidates(matchId), judgmentsApi.list({ matchId })])
      .then(([choices, linked]) => {
        if (active) { setCandidates(choices.data); setJudgments(linked.data); }
      }).catch(() => { if (active) setError('Could not load pre-game selections. Reload to retry.'); });
    return () => { active = false; };
  }, [matchId]);
  const attach = async (selection: BalanceSelection) => {
    setBusy(true);
    try {
      await selectionsApi.attach(selection.id, matchId);
      const linked = await judgmentsApi.list({ matchId });
      setJudgments(linked.data); setCandidates([]);
      toast.success('Pre-game selection linked');
    } catch {
      toast.error('Could not link this selection. It may already belong to another match.');
    } finally { setBusy(false); }
  };
  return (
    <VStack align="stretch" spacing={3}>
      {error && <Text color="orange.300">{error}</Text>}
      {!judgments.length && candidates.length > 0 && (
        <Box p={4} bg="space.800" borderRadius="lg">
          <Text fontWeight="bold">Which pre-game selection was this match?</Text>
          <Text fontSize="sm">Confirm the start time, especially if you played these teams more than once.</Text>
          {candidates.map(selection => (
            <HStack key={selection.id} my={2} justify="space-between">
              <Text>Game #{selection.id} · {new Date(`${selection.started_at}Z`).toLocaleString()}</Text>
              <Button size="sm" onClick={() => attach(selection)} isDisabled={busy}>This was our game</Button>
            </HStack>
          ))}
        </Box>
      )}
      {judgments.map(j => <Text key={j.id} fontSize="sm">Pre-game assessment by {j.author}: {j.human_estimate.replace(/_/g, ' ')} ({j.confidence} confidence). Team numbers refer to the saved selection.</Text>)}
      <Button
        alignSelf="flex-start"
        variant="outline"
        size="sm"
        leftIcon={<FiMessageSquare />}
        rightIcon={<FiChevronDown style={{ transform: feedbackOpen ? 'rotate(180deg)' : undefined }} />}
        onClick={() => setFeedbackOpen((open) => !open)}
        aria-expanded={feedbackOpen}
      >
        How did it play? Leave feedback
      </Button>
      <Collapse in={feedbackOpen} animateOpacity>
        <PostgameFeedback matchId={matchId} judgmentId={judgments[0]?.id} />
      </Collapse>
    </VStack>
  );
}
