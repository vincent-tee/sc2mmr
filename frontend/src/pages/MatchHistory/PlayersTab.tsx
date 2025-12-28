/**
 * PlayersTab - Player details and avatars for Match History
 */
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Avatar,
  Grid,
  Icon,
  Tooltip,
} from '@chakra-ui/react';
import {
  FiUsers,
  FiZap,
  FiTarget,
  FiActivity,
  FiAward,
} from 'react-icons/fi';
import { getPlayerAvatarUrl, getRaceColor } from '../../utils/formatting';
import { generatePlayerHighlight } from '../../utils/esportsCommentary';
import type { MatchPlayerSummary } from '../../types/api';

interface PlayersTabProps {
  players: MatchPlayerSummary[];
  winnerTeam: number;
  matchId: number;
  mvpPlayerId: number | null;
}

const PlayerCard: React.FC<{
  player: MatchPlayerSummary;
  matchId: number;
  isMVP: boolean;
}> = ({ player, matchId, isMVP }) => {
  const bgColor = player.won
    ? 'rgba(72, 187, 120, 0.1)'
    : 'rgba(245, 101, 101, 0.1)';
  const borderColor = player.won ? 'green.400' : 'red.400';

  const commentary = generatePlayerHighlight(
    {
      name: player.player_name,
      won: player.won,
      damageDealt: player.damage_dealt || 0,
      damageRatio: player.damage_ratio || 1,
      impactScore: player.impact_score || undefined,
    },
    matchId
  );

  return (
    <Box
      bg={bgColor}
      p={4}
      borderRadius="lg"
      border="2px solid"
      borderColor={borderColor}
      position="relative"
      transition="all 0.2s"
      _hover={{
        transform: 'translateY(-2px)',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
      }}
    >
      {isMVP && (
        <Badge
          position="absolute"
          top={-2}
          right={2}
          colorScheme="yellow"
          fontSize="xs"
          px={2}
          py={1}
        >
          <Icon as={FiAward} mr={1} />
          MVP
        </Badge>
      )}

      <HStack spacing={4} mb={3}>
        <Avatar
          size="lg"
          name={player.player_name}
          src={getPlayerAvatarUrl(player.player_name, player.race)}
          bg={`${getRaceColor(player.race)}.500`}
        />
        <VStack align="start" spacing={1} flex={1}>
          <HStack>
            <Text fontWeight="bold" fontSize="lg" fontFamily="heading">
              {player.player_name}
            </Text>
            <Badge
              colorScheme={getRaceColor(player.race)}
              fontSize="sm"
              fontFamily="heading"
            >
              {player.race}
            </Badge>
          </HStack>
          <HStack spacing={2}>
            <Badge colorScheme={player.won ? 'green' : 'red'}>
              {player.won ? 'WINNER' : 'DEFEAT'}
            </Badge>
            <Text
              fontSize="sm"
              fontWeight="bold"
              color={player.mmr_change >= 0 ? 'green.400' : 'red.400'}
            >
              {player.mmr_change >= 0 ? '+' : ''}{Math.round(player.mmr_change)} MMR
            </Text>
          </HStack>
        </VStack>
      </HStack>

      {/* Stats Grid */}
      <Grid templateColumns="repeat(3, 1fr)" gap={3} mb={3}>
        {player.damage_dealt !== null && (
          <Tooltip label="Total Damage Dealt">
            <VStack spacing={0} p={2} bg="whiteAlpha.100" borderRadius="md">
              <Icon as={FiZap} color="orange.400" />
              <Text fontSize="lg" fontWeight="bold" fontFamily="heading">
                {player.damage_dealt.toLocaleString()}
              </Text>
              <Text fontSize="xs" color="gray.500">Damage</Text>
            </VStack>
          </Tooltip>
        )}
        {player.damage_ratio !== null && (
          <Tooltip label="Damage Dealt / Damage Taken">
            <VStack spacing={0} p={2} bg="whiteAlpha.100" borderRadius="md">
              <Icon as={FiTarget} color="cyan.400" />
              <Text fontSize="lg" fontWeight="bold" fontFamily="heading">
                {player.damage_ratio >= 100 ? 'Perfect' : `${player.damage_ratio.toFixed(1)}:1`}
              </Text>
              <Text fontSize="xs" color="gray.500">Ratio</Text>
            </VStack>
          </Tooltip>
        )}
        {player.impact_score !== null && (
          <Tooltip label="Overall Impact Score (0-100)">
            <VStack spacing={0} p={2} bg="whiteAlpha.100" borderRadius="md">
              <Icon as={FiActivity} color="purple.400" />
              <Text fontSize="lg" fontWeight="bold" fontFamily="heading">
                {player.impact_score.toFixed(0)}
              </Text>
              <Text fontSize="xs" color="gray.500">Impact</Text>
            </VStack>
          </Tooltip>
        )}
      </Grid>

      {/* Commentary */}
      <Text fontSize="sm" fontStyle="italic" color="gray.400" noOfLines={2}>
        {commentary}
      </Text>
    </Box>
  );
};

export const PlayersTab: React.FC<PlayersTabProps> = ({
  players,
  winnerTeam,
  matchId,
  mvpPlayerId,
}) => {
  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);

  return (
    <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={6}>
      {/* Team 1 */}
      <Box>
        <HStack mb={4} spacing={2}>
          <Icon as={FiUsers} color="cyan.400" boxSize={5} />
          <Text
            fontFamily="heading"
            fontSize="lg"
            fontWeight="bold"
            color={winnerTeam === 1 ? 'green.400' : 'gray.400'}
          >
            Team 1 {winnerTeam === 1 && '- WINNERS'}
          </Text>
        </HStack>
        <VStack spacing={4} align="stretch">
          {team1Players.map((player) => (
            <PlayerCard
              key={player.player_id}
              player={player}
              matchId={matchId}
              isMVP={player.player_id === mvpPlayerId}
            />
          ))}
        </VStack>
      </Box>

      {/* Team 2 */}
      <Box>
        <HStack mb={4} spacing={2}>
          <Icon as={FiUsers} color="orange.400" boxSize={5} />
          <Text
            fontFamily="heading"
            fontSize="lg"
            fontWeight="bold"
            color={winnerTeam === 2 ? 'green.400' : 'gray.400'}
          >
            Team 2 {winnerTeam === 2 && '- WINNERS'}
          </Text>
        </HStack>
        <VStack spacing={4} align="stretch">
          {team2Players.map((player) => (
            <PlayerCard
              key={player.player_id}
              player={player}
              matchId={matchId}
              isMVP={player.player_id === mvpPlayerId}
            />
          ))}
        </VStack>
      </Box>
    </Grid>
  );
};

export default PlayersTab;
