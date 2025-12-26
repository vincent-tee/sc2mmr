/**
 * TeamSelector Component - Player Selection UI
 * Displays available players with selection toggles and bulk actions
 */
import {
  Box,
  HStack,
  VStack,
  Heading,
  Text,
  Button,
  SimpleGrid,
  Badge,
  Icon,
} from '@chakra-ui/react';
import { FiUsers, FiCheck, FiX } from 'react-icons/fi';
import PlayerCard from '@/components/PlayerCard';
import TacticalCard from '@/components/TacticalCard';
import type { Player } from '@/types/api';

interface TeamSelectorProps {
  players: Player[];
  selectedPlayers: Player[];
  onTogglePlayer: (player: Player) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
}

const TeamSelector: React.FC<TeamSelectorProps> = ({
  players,
  selectedPlayers,
  onTogglePlayer,
  onSelectAll,
  onClearSelection,
}) => {
  const minPlayers = 2;
  const canGenerate = selectedPlayers.length >= minPlayers;
  const needMorePlayers = selectedPlayers.length < minPlayers;
  const hasOddPlayers = selectedPlayers.length % 2 !== 0;

  const getGameMode = (count: number): string => {
    if (count === 2) return '1v1';
    if (count === 4) return '2v2';
    if (count === 6) return '3v3';
    if (count === 8) return '4v4';
    if (count === 10) return '5v5';
    if (count % 2 === 0) return `${count / 2}v${count / 2}`;
    return `${Math.ceil(count / 2)}v${Math.floor(count / 2)}`;
  };

  return (
    <Box>
      <TacticalCard variant="command" glowColor="rgba(0, 212, 255, 0.5)">
        <Box p={6}>
          <HStack justify="space-between" mb={6}>
            <VStack align="start" spacing={2}>
              <HStack>
                <Icon as={FiUsers} color="brand.400" boxSize={6} />
                <Heading
                  size="md"
                  fontFamily="heading"
                  textTransform="uppercase"
                  letterSpacing="wider"
                  color="brand.300"
                >
                  OPERATIVE SELECTION
                </Heading>
              </HStack>
              <HStack spacing={3} flexWrap="wrap">
                <Badge
                  colorScheme={canGenerate ? 'green' : 'orange'}
                  fontSize="lg"
                  px={3}
                  py={1}
                  fontFamily="heading"
                >
                  {selectedPlayers.length} SELECTED
                </Badge>
                {selectedPlayers.length >= minPlayers && (
                  <Badge
                    colorScheme={hasOddPlayers ? 'yellow' : 'blue'}
                    fontSize="lg"
                    px={3}
                    py={1}
                    fontFamily="heading"
                  >
                    {getGameMode(selectedPlayers.length)}
                  </Badge>
                )}
                {needMorePlayers && (
                  <Text fontSize="sm" color="gray.500" fontFamily="heading">
                    (MIN {minPlayers} REQUIRED)
                  </Text>
                )}
                {hasOddPlayers && selectedPlayers.length >= minPlayers && (
                  <Badge
                    colorScheme="purple"
                    fontSize="sm"
                    px={2}
                    py={1}
                    fontFamily="heading"
                  >
                    UNEVEN TEAMS - CONSIDER AI PLAYER
                  </Badge>
                )}
              </HStack>
            </VStack>

            <HStack>
              <Button
                size="sm"
                variant="ghost"
                onClick={onClearSelection}
                fontFamily="heading"
                textTransform="uppercase"
                leftIcon={<FiX />}
              >
                Clear
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={onSelectAll}
                fontFamily="heading"
                textTransform="uppercase"
                leftIcon={<FiCheck />}
              >
                Select All
              </Button>
            </HStack>
          </HStack>

          <SimpleGrid columns={{ base: 2, md: 3, lg: 4, xl: 5 }} spacing={4}>
            {players.map((player) => (
              <PlayerCard
                key={player.id}
                player={player}
                isSelected={selectedPlayers.some((p) => p.id === player.id)}
                onClick={() => onTogglePlayer(player)}
                size="lg"
              />
            ))}
          </SimpleGrid>
        </Box>
      </TacticalCard>
    </Box>
  );
};

export default TeamSelector;
