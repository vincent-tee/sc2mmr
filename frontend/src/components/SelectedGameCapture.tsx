import { useEffect, useState } from 'react';
import { Box, Button, HStack, Select, Text, VStack } from '@chakra-ui/react';
import type { TeamSuggestionWithImpact } from '@/types/api';
import JudgmentCapture from './JudgmentCapture';
import { judgmentsApi } from '@/api/judgments';

export default function SelectedGameCapture({ suggestion }: { suggestion: TeamSuggestionWithImpact }) {
  const [team1, setTeam1] = useState(suggestion.team_1.players);
  const [team2, setTeam2] = useState(suggestion.team_2.players);
  const [swap1, setSwap1] = useState('');
  const [swap2, setSwap2] = useState('');
  const [locked, setLocked] = useState(false);
  const [races, setRaces] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!suggestion.balance_prediction_id) { setLoading(false); return; }
    let active = true;
    judgmentsApi.list({ balancePredictionId: suggestion.balance_prediction_id }).then(({ data }) => {
      if (!active || !data.length) return;
      const saved = data.find(j => j.is_locked) ?? data[0];
      const pool = [...suggestion.team_1.players, ...suggestion.team_2.players];
      const ids1 = saved.team1_player_ids_key.split(',').map(Number);
      const ids2 = saved.team2_player_ids_key.split(',').map(Number);
      setTeam1(pool.filter(p => ids1.includes(p.id)));
      setTeam2(pool.filter(p => ids2.includes(p.id)));
      setRaces(Object.fromEntries([...(saved.team1_context ?? []), ...(saved.team2_context ?? [])].map(c => [c.player_id, c.race])));
      setLocked(saved.is_locked);
    }).catch(() => {}).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [suggestion]);

  const swap = () => {
    const first = team1.find(p => p.id === Number(swap1));
    const second = team2.find(p => p.id === Number(swap2));
    if (!first || !second) return;
    setTeam1(team1.map(p => p.id === first.id ? second : p));
    setTeam2(team2.map(p => p.id === second.id ? first : p));
    setSwap1(''); setSwap2('');
  };
  if (loading) return <Text mt={4}>Loading saved game assessment…</Text>;
  return (
    <VStack align="stretch" spacing={4} mt={6}>
      <Text fontWeight="bold">Choose these teams for your game</Text>
      <Text fontSize="sm" color="gray.400">Optional swaps and race choices apply to this game only. Record your assessment, then start the game before playing.</Text>
      <HStack align="start" spacing={6}>
        {[team1, team2].map((team, index) => (
          <Box key={index} flex={1}>
            <Text fontWeight="bold">Final Team {index + 1}</Text>
            {team.map(player => (
              <HStack key={player.id} my={2}>
                <Text flex={1}>{player.name}</Text>
                <Select aria-label={`Race for ${player.name}`} size="sm" maxW="140px"
                  value={races[player.id] ?? ''} isDisabled={locked}
                  onChange={e => setRaces({ ...races, [player.id]: e.target.value })}>
                  <option value="">Race unknown</option>
                  {['Terran', 'Protoss', 'Zerg', 'Random'].map(race => <option key={race}>{race}</option>)}
                </Select>
              </HStack>
            ))}
          </Box>
        ))}
      </HStack>
      <HStack>
        <Select aria-label="Swap from Team 1" placeholder="Team 1 player" value={swap1} isDisabled={locked} onChange={e => setSwap1(e.target.value)}>
          {team1.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        <Select aria-label="Swap from Team 2" placeholder="Team 2 player" value={swap2} isDisabled={locked} onChange={e => setSwap2(e.target.value)}>
          {team2.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        <Button onClick={swap} isDisabled={locked || !swap1 || !swap2}>Swap</Button>
      </HStack>
      <JudgmentCapture balancePredictionId={suggestion.balance_prediction_id ?? undefined}
        mapName={suggestion.map_name ?? undefined}
        team1PlayerIds={team1.map(p => p.id)} team2PlayerIds={team2.map(p => p.id)}
        team1Context={team1.filter(p => races[p.id]).map(p => ({ player_id: p.id, race: races[p.id] }))}
        team2Context={team2.filter(p => races[p.id]).map(p => ({ player_id: p.id, race: races[p.id] }))}
        onSaved={judgment => setLocked(judgment.is_locked)} />
    </VStack>
  );
}
