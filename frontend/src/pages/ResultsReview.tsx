/**
 * Results to review: games whose replay didn't record a winner, doubtful ones first.
 */
import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Badge,
  Box,
  Button,
  Container,
  Flex,
  Grid,
  HStack,
  Input,
  Link,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LuCrown } from 'react-icons/lu';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import { matchResultsApi, type ResultReviewItem } from '../api/matchResults';
import { hasAdminToken } from '../utils/adminToken';
import { formatDateTime, formatDuration } from '../utils/formatting';
import { useToast } from '../hooks/useToast';

const NAME_STORAGE_KEY = 'sc2mmr_judgment_author';
const PAGE_SIZE = 25;
const TEAM_ACCENT: Record<number, string> = { 1: 'brand.400', 2: 'accent.400' };

const readStoredName = (): string => {
  try {
    return localStorage.getItem(NAME_STORAGE_KEY) ?? '';
  } catch {
    return '';
  }
};

const whyInQueue = (item: ResultReviewItem): string | null => {
  const disagreeing = item.other_recordings.find((r) => r.winner_team !== item.winner_team);
  if (disagreeing) return `Another recording says Team ${disagreeing.winner_team} won`;
  if (item.conflicts && item.supply_favourite_team) {
    const ratio = item.supply_ratio ? ` (${item.supply_ratio.toFixed(1)}x)` : '';
    return `Team ${item.supply_favourite_team} had more supply${ratio}`;
  }
  return null;
};

const ReviewCard: React.FC<{
  item: ResultReviewItem;
  canConfirm: boolean;
  busy: boolean;
  onConfirm: (winnerTeam: number) => void;
}> = ({ item, canConfirm, busy, onConfirm }) => {
  const reason = whyInQueue(item);
  const hasTwoTeams = item.rosters.length === 2 && item.rosters.every((r) => r.team === 1 || r.team === 2);
  return (
    <Box
      bg="space.800"
      border="1px solid"
      borderColor={item.conflicts ? 'yellow.600' : 'whiteAlpha.100'}
      borderRadius="xl"
      p={{ base: 4, md: 5 }}
    >
      <Flex justify="space-between" align="start" gap={3} flexWrap="wrap" mb={3}>
        <Box minW={0}>
          <Link as={RouterLink} to={`/history/${item.match_id}`} fontFamily="heading" fontSize="lg" color="gray.50">
            {item.map_name}
          </Link>
          <Text fontSize="xs" color="gray.500">
            {formatDateTime(item.played_at)} · recorded through {formatDuration(item.duration_seconds)}
          </Text>
        </Box>
        {reason && <Badge colorScheme="yellow" variant="subtle" whiteSpace="normal">{reason}</Badge>}
      </Flex>

      <Grid templateColumns={{ base: '1fr', md: '1fr 1fr' }} gap={3}>
        {item.rosters.map(({ team, players }) => {
          const isWinner = item.winner_team === team;
          const supply = item.team_supply[String(team)];
          return (
            <Box key={team} p={3} borderRadius="lg" bg="whiteAlpha.50" borderLeft="3px solid" borderLeftColor={TEAM_ACCENT[team]}>
              <HStack justify="space-between" mb={1}>
                <HStack spacing={2}>
                  <Text fontWeight="bold" color={TEAM_ACCENT[team]}>Team {team}</Text>
                  {isWinner && (
                    <Badge variant="subtle" colorScheme="gray" display="flex" alignItems="center" gap={1}>
                      <LuCrown aria-hidden /> given the win
                    </Badge>
                  )}
                </HStack>
                {supply !== undefined && (
                  <Text fontFamily="mono" fontSize="sm" color="gray.300">{Math.round(supply)} supply</Text>
                )}
              </HStack>
              <Text fontSize="sm" color="gray.400">{players.join(', ')}</Text>
            </Box>
          );
        })}
      </Grid>

      {!hasTwoTeams && (
        <Text mt={3} fontSize="sm" color="gray.400">
          This game&apos;s teams aren&apos;t recorded as Team 1 against Team 2, so it can&apos;t be confirmed here.
        </Text>
      )}

      {canConfirm && hasTwoTeams && (
        <HStack mt={4} spacing={2} flexWrap="wrap">
          {[1, 2].map((team) => (
            <Button
              key={team}
              size="sm"
              isDisabled={busy}
              variant={item.winner_team === team ? 'solid' : 'outline'}
              colorScheme={item.winner_team === team ? 'brand' : 'gray'}
              onClick={() => onConfirm(team)}
            >
              {item.winner_team === team ? `Confirm Team ${team} won` : `Team ${team} won instead`}
            </Button>
          ))}
        </HStack>
      )}
    </Box>
  );
};

const ResultsReview: React.FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [name, setName] = useState(readStoredName);
  const [shown, setShown] = useState(PAGE_SIZE);
  const canConfirm = hasAdminToken();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['result-review'],
    queryFn: async () => (await matchResultsApi.reviewQueue()).data,
  });

  const confirm = useMutation({
    mutationFn: ({ matchId, winnerTeam }: { matchId: number; winnerTeam: number }) =>
      matchResultsApi.confirm(matchId, winnerTeam, name),
    onSuccess: ({ data: result }) => {
      queryClient.invalidateQueries({ queryKey: ['result-review'] });
      queryClient.invalidateQueries({ queryKey: ['match', String(result.item.match_id)] });
      toast.success(result.changed
        ? `Changed to Team ${result.item.winner_team}. Ratings will rebuild shortly.`
        : 'Result confirmed');
    },
    onError: (error) => toast.error((error as { userMessage?: string }).userMessage || 'Could not save the result'),
  });

  const updateName = (value: string) => {
    setName(value);
    try {
      localStorage.setItem(NAME_STORAGE_KEY, value);
    } catch {
      // Remembering the name is a convenience only.
    }
  };

  return (
    <Box minH="100vh" pb={16}>
      <PageHeader
        kicker="Housekeeping"
        title="Results to [Review]"
        description="These replays didn't record who won, so a winner was suggested from team stats. Confirm or correct them."
        stats={data ? [
          { label: 'To review', value: data.total },
          { label: 'Doubtful', value: data.conflicts },
        ] : undefined}
      />
      <Container maxW="container.lg" pt={8}>
        <VStack align="stretch" spacing={4}>
          {data && data.unchecked > 0 && (
            <Text fontSize="sm" color="gray.400">
              {data.unchecked} older games haven&apos;t been checked yet; they&apos;ll appear here once they are.
            </Text>
          )}
          {canConfirm ? (
            <HStack spacing={3} flexWrap="wrap">
              <Text fontSize="sm" color="gray.400" as="label" htmlFor="confirmer-name">Confirming as</Text>
              <Input id="confirmer-name" size="sm" maxW="220px" value={name} placeholder="Your name"
                onChange={(e) => updateName(e.target.value)} />
            </HStack>
          ) : (
            <Text fontSize="sm" color="gray.500">Confirming results needs the admin token in this browser.</Text>
          )}

          {isLoading && <LoadingState message="Loading results to review..." />}
          {isError && <Text color="red.300">Couldn&apos;t load the review queue.</Text>}
          {data && data.items.length === 0 && (
            <EmptyState title="Nothing to review" description="Every rated game has a recorded or confirmed result." />
          )}
          {data?.items.slice(0, shown).map((item) => (
            <ReviewCard
              key={item.match_id}
              item={item}
              canConfirm={canConfirm && name.trim().length > 0}
              busy={confirm.isPending}
              onConfirm={(winnerTeam) => confirm.mutate({ matchId: item.match_id, winnerTeam })}
            />
          ))}
          {data && data.items.length > shown && (
            <Button alignSelf="center" variant="outline" onClick={() => setShown((n) => n + PAGE_SIZE)}>
              Show {Math.min(PAGE_SIZE, data.items.length - shown)} more of {data.items.length - shown}
            </Button>
          )}
        </VStack>
      </Container>
    </Box>
  );
};

export default ResultsReview;
