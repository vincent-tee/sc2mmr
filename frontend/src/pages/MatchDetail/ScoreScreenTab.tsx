/**
 * ScoreScreenTab Component - Recreates the classic StarCraft II post-game
 * score screen (Summary / Economy / Military) using our own parsed match
 * metrics, grouped by team.
 */
import {
  Box,
  VStack,
  HStack,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Badge,
  Icon,
  Button,
  ButtonGroup,
} from '@chakra-ui/react';
import { FiAward } from 'react-icons/fi';
import { useState } from 'react';
import { formatDuration } from '@/utils/formatting';
import type { MatchDetail as MatchDetailType, MatchPlayer } from '@/types/api';

interface ScoreScreenTabProps {
  matchData: MatchDetailType;
  team1Won: boolean;
}

type Section = 'summary' | 'economy' | 'military';

const SECTIONS: { key: Section; label: string }[] = [
  { key: 'summary', label: 'Summary' },
  { key: 'economy', label: 'Economy' },
  { key: 'military', label: 'Military' },
];

// "—" for stats we never parsed for this match (e.g. an old or voided game)
const fmtNum = (v: number | null | undefined): string =>
  v === null || v === undefined ? '—' : Math.round(v).toLocaleString();

const fmtPct = (v: number | null | undefined): string =>
  v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`;

const fmtSeconds = (v: number | null | undefined): string =>
  v === null || v === undefined ? '—' : formatDuration(v);

// The backend's stored kill_death_ratio is the source of truth (computed and
// capped at 10 by the parser). One exception: rows uploaded before the K/D
// fix all carry the old poisoned default of exactly 1.0 — when the unit
// counts contradict a stored 1.0, trust the counts. Self-healing: once the
// backfill runs, stored and derived agree and the exception never fires.
const KD_CAP = 10;
const fmtKD = (p: MatchPlayer): string => {
  if (!p.units_killed && !p.units_lost) return '—';
  const derived =
    p.units_killed != null && p.units_lost != null
      ? p.units_lost > 0
        ? Math.min(p.units_killed / p.units_lost, KD_CAP)
        : KD_CAP
      : null;
  const stored = p.kill_death_ratio;
  const storedIsPoisoned =
    stored === 1.0 && derived != null && Math.abs(derived - 1.0) > 1e-9;
  if (stored != null && !storedIsPoisoned) return stored.toFixed(2);
  if (derived != null) return derived.toFixed(2);
  return '—';
};

interface ColumnDef {
  label: string;
  render: (p: MatchPlayer) => string;
}

const COLUMNS: Record<Section, ColumnDef[]> = {
  summary: [
    { label: 'APM', render: (p) => fmtNum(p.apm) },
    { label: 'Resources Collected', render: (p) => fmtNum(p.total_resources_collected) },
    { label: 'Workers Made', render: (p) => fmtNum(p.workers_created) },
    { label: 'Supply Blocked', render: (p) => fmtSeconds(p.supply_block_seconds) },
    { label: 'K/D', render: fmtKD },
  ],
  economy: [
    { label: 'Minerals', render: (p) => fmtNum(p.minerals_collected) },
    { label: 'Vespene', render: (p) => fmtNum(p.vespene_collected) },
    { label: 'Total Collected', render: (p) => fmtNum(p.total_resources_collected) },
    { label: 'Spent', render: (p) => fmtNum(p.resources_spent) },
    {
      label: 'Unspent',
      render: (p) =>
        p.total_resources_collected != null && p.resources_spent != null
          ? fmtNum(p.total_resources_collected - p.resources_spent)
          : '—',
    },
    { label: 'Efficiency', render: (p) => fmtPct(p.spending_efficiency) },
    { label: 'Workers Made', render: (p) => fmtNum(p.workers_created) },
  ],
  military: [
    { label: 'Army Built', render: (p) => fmtNum(p.army_value_built) },
    { label: 'Army Killed', render: (p) => fmtNum(p.army_value_killed) },
    { label: 'Army Lost', render: (p) => fmtNum(p.army_value_lost) },
    { label: 'Units Killed', render: (p) => fmtNum(p.units_killed) },
    { label: 'Units Lost', render: (p) => fmtNum(p.units_lost) },
    { label: 'K/D', render: fmtKD },
    { label: 'Damage Dealt', render: (p) => fmtNum(p.damage_dealt) },
    { label: 'Damage Taken', render: (p) => fmtNum(p.damage_taken) },
  ],
};

const TeamTable: React.FC<{
  title: string;
  accentColor: string;
  won: boolean;
  players: MatchPlayer[];
  columns: ColumnDef[];
}> = ({ title, accentColor, won, players, columns }) => {
  const winnerBg = 'rgba(72, 187, 120, 0.05)';
  const loserBg = 'rgba(245, 101, 101, 0.05)';

  return (
    <Box>
      <HStack mb={4} spacing={3}>
        <Heading
          size="md"
          fontFamily="heading"
          letterSpacing="widest"
          textTransform="uppercase"
          color={accentColor}
        >
          {title}
        </Heading>
        {won && (
          <Badge
            colorScheme="green"
            variant="solid"
            fontSize="sm"
            px={3}
            py={1}
            borderRadius="md"
            fontFamily="heading"
          >
            <Icon as={FiAward} mr={1} />
            Victory
          </Badge>
        )}
      </HStack>
      <Box
        bg="space.800"
        borderRadius="xl"
        border="3px solid"
        borderColor="space.900"
        boxShadow="3px 3px 0 var(--chakra-colors-space-900)"
        overflow="hidden"
      >
        <Box p={4} bg={won ? winnerBg : loserBg}>
          <TableContainer overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th fontFamily="heading" color="gray.500">Player</Th>
                  <Th fontFamily="heading" color="gray.500">Race</Th>
                  {columns.map((c) => (
                    <Th key={c.label} isNumeric fontFamily="heading" color="gray.500" whiteSpace="nowrap">
                      {c.label}
                    </Th>
                  ))}
                </Tr>
              </Thead>
              <Tbody>
                {players.map((player) => (
                  <Tr key={player.player_id}>
                    <Td fontWeight="bold" fontFamily="heading" color="gray.100">
                      {player.player_name}
                    </Td>
                    <Td>
                      <Badge size="sm" variant={`race-${player.race.toLowerCase()}`} fontFamily="heading">
                        {player.race}
                      </Badge>
                    </Td>
                    {columns.map((c) => (
                      <Td key={c.label} isNumeric fontFamily="mono" color="gray.200">
                        {c.render(player)}
                      </Td>
                    ))}
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </TableContainer>
        </Box>
      </Box>
    </Box>
  );
};

const ScoreScreenTab: React.FC<ScoreScreenTabProps> = ({ matchData, team1Won }) => {
  const [section, setSection] = useState<Section>('summary');
  const { players } = matchData;

  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);
  const columns = COLUMNS[section];

  const anyMetrics = players.some((p) => p.total_resources_collected !== null);

  return (
    <VStack spacing={6} align="stretch">
      <ButtonGroup size="sm" isAttached variant="outline" alignSelf="flex-start">
        {SECTIONS.map((s) => (
          <Button
            key={s.key}
            onClick={() => setSection(s.key)}
            fontFamily="heading"
            letterSpacing="wide"
            colorScheme={section === s.key ? 'brand' : 'gray'}
            variant={section === s.key ? 'solid' : 'outline'}
          >
            {s.label}
          </Button>
        ))}
      </ButtonGroup>

      {!anyMetrics && (
        <Badge alignSelf="flex-start" colorScheme="gray" px={3} py={1} borderRadius="md" fontFamily="heading">
          No in-game stats were recorded for this match — showing what we have
        </Badge>
      )}

      <TeamTable
        title="Team 1"
        accentColor="brand.400"
        won={team1Won}
        players={team1Players}
        columns={columns}
      />
      <TeamTable
        title="Team 2"
        accentColor="accent.400"
        won={!team1Won}
        players={team2Players}
        columns={columns}
      />
    </VStack>
  );
};

export default ScoreScreenTab;
