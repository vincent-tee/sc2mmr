/** Separate post-game observations, shown on the match detail page. */
import { useEffect, useState } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Text,
  Textarea,
  VStack,
} from '@chakra-ui/react';
import { judgmentsApi } from '../api/judgments';
import type { FeedbackResponse, PostgameFeedbackType } from '../api/judgments';
import { useToast } from '../hooks/useToast';

const AUTHOR_STORAGE_KEY = 'sc2mmr_judgment_author';

const FEEDBACK_OPTIONS: { value: PostgameFeedbackType; label: string }[] = [
  { value: 'felt_balanced', label: 'Close / felt balanced' },
  { value: 'one_sided', label: 'One-sided' },
  { value: 'snowballed_early', label: 'Snowballed early' },
  { value: 'disconnect', label: 'Disconnect' },
  { value: 'other', label: 'Other' },
];

export interface PostgameFeedbackProps {
  /** At least one of matchId/judgmentId is required by the backend. */
  matchId?: number;
  judgmentId?: number;
  /** Fires after a successful submission, e.g. to refresh a parent list. */
  onSaved?: (feedback: FeedbackResponse) => void;
}

const PostgameFeedback: React.FC<PostgameFeedbackProps> = ({ matchId, judgmentId, onSaved }) => {
  const toast = useToast();
  const [entries, setEntries] = useState<FeedbackResponse[]>([]);
  const [loadingEntries, setLoadingEntries] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [author, setAuthor] = useState(
    () => localStorage.getItem(AUTHOR_STORAGE_KEY) ?? ''
  );
  const [feedback, setFeedback] = useState<PostgameFeedbackType>('felt_balanced');
  const [note, setNote] = useState('');

  const canSubmit = author.trim().length > 0 && (matchId !== undefined || judgmentId !== undefined);

  useEffect(() => {
    let cancelled = false;
    setLoadingEntries(true);
    judgmentsApi
      .listFeedback({ matchId, judgmentId })
      .then(({ data }) => {
        if (!cancelled) setEntries(data);
      })
      .catch(() => {
        // Best-effort: an empty list is a fine fallback for a read-only view.
      })
      .finally(() => {
        if (!cancelled) setLoadingEntries(false);
      });
    return () => {
      cancelled = true;
    };
  }, [matchId, judgmentId]);

  const handleAuthorChange = (value: string) => {
    setAuthor(value);
    localStorage.setItem(AUTHOR_STORAGE_KEY, value);
  };

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return;
    setSubmitting(true);
    try {
      const { data } = await judgmentsApi.createFeedback({
        match_id: matchId,
        judgment_id: judgmentId,
        feedback,
        note: note || null,
        author: author.trim(),
      });
      setEntries((prev) => [data, ...prev]);
      setNote('');
      onSaved?.(data);
      toast.success('Feedback recorded');
    } catch (err) {
      const message = (err as { userMessage?: string })?.userMessage || 'Failed to save feedback';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" p={5}>
      <Text fontFamily="heading" fontSize="sm" fontWeight="700" letterSpacing="0.08em" textTransform="uppercase" color="gray.300" mb={4}>
        Post-Game Feedback
      </Text>

      <VStack align="stretch" spacing={4}>
        <FormControl>
          <FormLabel fontSize="xs" color="gray.500">How did it play out?</FormLabel>
          <ButtonGroup isAttached size="sm" w="100%" flexWrap="wrap">
            {FEEDBACK_OPTIONS.map((opt) => (
              <Button
                key={opt.value}
                flex={1}
                minW="fit-content"
                bg={feedback === opt.value ? 'brand.500' : 'space.900'}
                color={feedback === opt.value ? 'white' : 'gray.400'}
                borderColor="space.700"
                _hover={{ bg: feedback === opt.value ? 'brand.600' : 'space.700' }}
                onClick={() => setFeedback(opt.value)}
              >
                {opt.label}
              </Button>
            ))}
          </ButtonGroup>
        </FormControl>

        <FormControl>
          <FormLabel fontSize="xs" color="gray.500">Note (optional)</FormLabel>
          <Textarea
            size="sm"
            bg="space.900"
            borderColor="space.700"
            rows={2}
            placeholder="What actually happened?"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
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

        <HStack justify="flex-end">
          <Button
            size="sm"
            bg="brand.500"
            color="white"
            _hover={{ bg: 'brand.600' }}
            onClick={handleSubmit}
            isLoading={submitting}
            isDisabled={!canSubmit}
          >
            Submit Feedback
          </Button>
        </HStack>

        {!loadingEntries && entries.length > 0 && (
          <VStack align="stretch" spacing={2} pt={2} borderTop="1px solid" borderColor="whiteAlpha.100">
            <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="0.08em">
              Previous feedback
            </Text>
            {entries.map((entry) => (
              <HStack key={entry.id} justify="space-between" fontSize="sm">
                <Text color="gray.300">
                  {FEEDBACK_OPTIONS.find((o) => o.value === entry.feedback)?.label}
                  {entry.note && <Text as="span" color="gray.500"> — {entry.note}</Text>}
                </Text>
                <Text color="gray.600" fontSize="xs" whiteSpace="nowrap">{entry.author}</Text>
              </HStack>
            ))}
          </VStack>
        )}
      </VStack>
    </Box>
  );
};

export default PostgameFeedback;
