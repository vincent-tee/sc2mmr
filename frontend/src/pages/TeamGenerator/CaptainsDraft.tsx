/**
 * Captain's Draft over the already-selected squad: two captains, then snake-order
 * picks by hand or drafted automatically.
 */
import { useState } from 'react';
import { Badge, Box, Button, ButtonGroup, Flex, Heading, HStack, SimpleGrid, Text, VStack } from '@chakra-ui/react';
import { useMutation } from '@tanstack/react-query';
import { FiShuffle, FiUsers, FiX, FiZap } from 'react-icons/fi';
import apiClient, { isUnauthenticated } from '@/api/client';
import { useAuth } from '@/components/AuthGate';
import type { Player } from '@/types/api';

interface DraftResponse {
  teams: { players: { id: number }[] }[];
}

interface CaptainsDraftProps {
  squad: Player[];
  onComplete: (team1: Player[], team2: Player[]) => void;
  onCancel: () => void;
}

const byMMR = (a: Player, b: Player) => b.mmr - a.mmr;

// Matches TeamBalancer.snake_draft: 1,2,2,1,1,2,2,1,... after the captains.
const teamOnTheClock = (picksMade: number): 1 | 2 => {
  const round = Math.floor(picksMade / 2);
  const firstInRound = round % 2 === 0 ? 1 : 2;
  return picksMade % 2 === 0 ? firstInRound : firstInRound === 1 ? 2 : 1;
};

const CaptainsDraft: React.FC<CaptainsDraftProps> = ({ squad, onComplete, onCancel }) => {
  const [captain1, setCaptain1] = useState<Player | null>(null);
  const [captain2, setCaptain2] = useState<Player | null>(null);
  const [team1, setTeam1] = useState<Player[]>([]);
  const [team2, setTeam2] = useState<Player[]>([]);
  const drafting = team1.length > 0;
  const { signIn } = useAuth();

  const autoDraft = useMutation({
    mutationFn: async (_: { afterSignIn?: boolean } = {}) => (await apiClient.post<DraftResponse>('/teams/draft', {
      player_ids: squad.map((p) => p.id),
      custom_players: [],
      num_teams: 2,
    })).data,
    onSuccess: (data) => {
      const pick = (ids: { id: number }[]) => ids.map(({ id }) => squad.find((p) => p.id === id)).filter((p): p is Player => !!p);
      onComplete(pick(data.teams[0].players), pick(data.teams[1].players));
    },
    onError: (error, { afterSignIn }) => {
      if (!isUnauthenticated(error) || afterSignIn) return;
      signIn('draft teams').then((signedIn) => {
        if (signedIn) autoDraft.mutate({ afterSignIn: true });
      });
    },
  });

  const toggleCaptain = (player: Player) => {
    if (captain1?.id === player.id) return setCaptain1(null);
    if (captain2?.id === player.id) return setCaptain2(null);
    if (!captain1) return setCaptain1(player);
    if (!captain2) return setCaptain2(player);
  };

  const startDraft = () => {
    if (!captain1 || !captain2) return;
    if (squad.length === 2) return onComplete([captain1], [captain2]);
    setTeam1([captain1]);
    setTeam2([captain2]);
  };

  const remaining = squad.filter((p) => !team1.some((t) => t.id === p.id) && !team2.some((t) => t.id === p.id)).sort(byMMR);
  const onTheClock = teamOnTheClock(team1.length + team2.length - 2);

  const pick = (player: Player) => {
    const next1 = onTheClock === 1 ? [...team1, player] : team1;
    const next2 = onTheClock === 2 ? [...team2, player] : team2;
    setTeam1(next1);
    setTeam2(next2);
    if (remaining.length === 1) onComplete(next1, next2);
  };

  return (
    <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" p={{ base: 4, md: 6 }}>
      <Flex justify="space-between" align="center" mb={4} gap={3}>
        <HStack spacing={3}>
          <FiShuffle />
          <Heading size="md" fontFamily="heading">Captain&apos;s draft</Heading>
        </HStack>
        <Button size="sm" variant="ghost" leftIcon={<FiX />} onClick={onCancel}>Cancel</Button>
      </Flex>

      {!drafting ? (
        <VStack align="stretch" spacing={4}>
          <Text fontSize="sm" color="gray.400">Pick two captains from tonight&apos;s squad.</Text>
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={2}>
            {[...squad].sort(byMMR).map((player) => {
              const isCaptain1 = captain1?.id === player.id;
              const isCaptain2 = captain2?.id === player.id;
              return (
                <Button
                  key={player.id}
                  size="sm"
                  variant={isCaptain1 || isCaptain2 ? 'solid' : 'outline'}
                  colorScheme={isCaptain1 ? 'brand' : isCaptain2 ? 'teal' : 'gray'}
                  onClick={() => toggleCaptain(player)}
                  aria-pressed={isCaptain1 || isCaptain2}
                >
                  <Text noOfLines={1}>{player.name}</Text>
                </Button>
              );
            })}
          </SimpleGrid>
          <ButtonGroup size="sm" flexWrap="wrap" gap={2} spacing={0}>
            <Button leftIcon={<FiUsers />} colorScheme="brand" isDisabled={!captain1 || !captain2} onClick={startDraft}>
              Draft pick by pick
            </Button>
            <Button leftIcon={<FiZap />} variant="outline" isLoading={autoDraft.isPending} onClick={() => autoDraft.mutate({})}>
              Draft automatically
            </Button>
          </ButtonGroup>
        </VStack>
      ) : (
        <VStack align="stretch" spacing={4}>
          <HStack justify="space-between" flexWrap="wrap" gap={2}>
            <Badge colorScheme={onTheClock === 1 ? 'orange' : 'teal'} fontSize="sm" px={3} py={1}>
              {(onTheClock === 1 ? captain1 : captain2)?.name}&apos;s pick (Team {onTheClock})
            </Badge>
            <Text fontSize="sm" color="gray.400">
              Team 1: {team1.map((p) => p.name).join(', ')} · Team 2: {team2.map((p) => p.name).join(', ')}
            </Text>
          </HStack>
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={2}>
            {remaining.map((player) => (
              <Button key={player.id} size="sm" variant="outline" onClick={() => pick(player)}>
                <Text noOfLines={1}>{player.name}</Text>
                <Text as="span" ml={2} fontSize="xs" color="gray.500" fontFamily="mono">{Math.round(player.mmr)}</Text>
              </Button>
            ))}
          </SimpleGrid>
        </VStack>
      )}
    </Box>
  );
};

export default CaptainsDraft;
