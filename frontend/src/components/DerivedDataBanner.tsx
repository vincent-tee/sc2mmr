import { useEffect, useRef, useState } from 'react';
import { Alert, AlertDescription, AlertIcon, Button, Flex, Spinner, Text } from '@chakra-ui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { maintenanceApi, type DerivedDataStatus } from '../api/maintenance';
import { useAuth } from './AuthGate';

const STATUS_QUERY_KEY = ['derived-data-status'];
const POLL_WHILE_STALE_MS = 15_000;
const POLL_WHILE_FRESH_MS = 60_000;
const CLOCK_TICK_MS = 5_000;

const parseServerTime = (value: string | null): number | null =>
  value ? Date.parse(value.endsWith('Z') ? value : `${value}Z`) : null;

const hasAdminToken = (): boolean => {
  try {
    return Boolean(localStorage.getItem('sc2mmr_admin_token'));
  } catch {
    return false;
  }
};

const secondsUntil = (timestamp: number, now: number): number =>
  Math.max(0, Math.ceil((timestamp - now) / 1000));

function DerivedDataBanner(): React.ReactElement | null {
  const { authenticated } = useAuth();
  const queryClient = useQueryClient();
  const [now, setNow] = useState(() => Date.now());
  const lastAutoTriggeredDueAt = useRef<number | null>(null);

  const { data: status } = useQuery({
    queryKey: STATUS_QUERY_KEY,
    queryFn: async () => (await maintenanceApi.getDerivedDataStatus()).data,
    refetchInterval: (query) => (query.state.data?.stale ? POLL_WHILE_STALE_MS : POLL_WHILE_FRESH_MS),
    retry: false,
  });

  const applyNewStatus = (next: DerivedDataStatus) => {
    queryClient.setQueryData(STATUS_QUERY_KEY, next);
    if (!next.stale) {
      queryClient.invalidateQueries();
    }
  };

  const rebuildIfDue = useMutation({
    mutationFn: async () => (await maintenanceApi.rebuildIfDue()).data,
    onSuccess: applyNewStatus,
  });

  const rebuildNow = useMutation({
    mutationFn: async () => (await maintenanceApi.rebuildNow()).data,
    onSuccess: applyNewStatus,
  });

  const dueAt = parseServerTime(status?.rebuild_due_at ?? null);
  const stale = Boolean(status?.stale);
  const rebuilding = Boolean(status?.rebuilding) || rebuildIfDue.isPending || rebuildNow.isPending;

  useEffect(() => {
    if (!stale) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), CLOCK_TICK_MS);
    return () => window.clearInterval(timer);
  }, [stale]);

  useEffect(() => {
    const isDue = stale && !rebuilding && dueAt !== null && dueAt <= now;
    if (isDue && authenticated && lastAutoTriggeredDueAt.current !== dueAt) {
      lastAutoTriggeredDueAt.current = dueAt;
      rebuildIfDue.mutate();
    }
  }, [stale, rebuilding, dueAt, now, authenticated, rebuildIfDue]);

  if (!stale && !rebuilding) return null;

  const message = rebuilding
    ? 'Recalculating ratings from match history…'
    : dueAt !== null && dueAt > now
      ? `Ratings will be recalculated in ${secondsUntil(dueAt, now)}s so older uploads count in the right order.`
      : 'Ratings are waiting to be recalculated so older uploads count in the right order.';

  return (
    <Alert status={status?.last_error && !rebuilding ? 'warning' : 'info'} variant="left-accent" borderRadius={0}>
      <AlertIcon />
      <Flex flex="1" align="center" justify="space-between" gap={4} wrap="wrap">
        <AlertDescription>
          <Text as="span">{message}</Text>
          {status?.stale_reason && !rebuilding && (
            <Text as="span" color="gray.400" ml={2}>({status.stale_reason})</Text>
          )}
          {status?.last_error && !rebuilding && (
            <Text as="span" color="gray.400" ml={2}>The last attempt failed and will be retried.</Text>
          )}
        </AlertDescription>
        {rebuilding ? (
          <Spinner size="sm" />
        ) : (
          authenticated && hasAdminToken() && (
            <Button size="sm" variant="outline" onClick={() => rebuildNow.mutate()}>
              Rebuild now
            </Button>
          )
        )}
      </Flex>
    </Alert>
  );
}

export default DerivedDataBanner;
