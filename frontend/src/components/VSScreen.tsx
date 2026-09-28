/**
 * VSScreen Component
 * Esports-style "Team 1 VS Team 2" showdown display for match details
 */
import React from 'react';
import {
  Box,
  Flex,
  Text,
  VStack,
  HStack,
  Badge,
  Button,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { LuCrown } from 'react-icons/lu';
import { FiArrowUp, FiArrowDown } from 'react-icons/fi';
import { formatMMR, getRaceColor } from '../utils/formatting';

// =============================================================================
// Types
// =============================================================================

interface TeamPlayerInfo {
  name: string;
  mmr: number;
  race: string;
  /** Rating change from this game, shown next to the MMR. */
  mmrChange?: number;
}

interface TeamData {
  players: TeamPlayerInfo[];
  totalMMR: number;
  winProbability?: number;
}

interface MatchInfo {
  mapName: string;
  gameMode: string;
}

export interface VSScreenProps {
  team1: TeamData;
  team2: TeamData;
  matchInfo?: MatchInfo;
  winner?: 1 | 2 | null;
  onViewDetails?: () => void;
  /** True for a not-yet-played, model-predicted matchup (BalanceResults). Swaps the
   * "WINNER" crown for a lower-key "Advantage" badge so a prediction isn't mistaken
   * for a recorded result. */
  isPrediction?: boolean;
  /**
   * Label for the per-team win-probability stat. Defaults to "Win Prob",
   * which is only accurate when `winProbability` is a model/TrueSkill
   * estimate (as in BalanceResults/MatchHeader). Callers passing a
   * historical win RATE instead (e.g. head-to-head record) should override
   * this - e.g. "Win Rate" - so the UI doesn't claim predictive precision
   * a plain historical tally doesn't have.
   */
  probabilityLabel?: string;
  /** Label for the team's summed MMR. */
  totalLabel?: string;
  /** Slimmer panels without glow/animation, stats in the team header. */
  compact?: boolean;
}

// =============================================================================
// Race Icon Helper
// =============================================================================

const getRaceIcon = (race: string): string => {
  const raceMap: Record<string, string> = {
    Terran: 'T',
    Protoss: 'P',
    Zerg: 'Z',
    Random: 'R',
  };
  return raceMap[race] || '?';
};

// =============================================================================
// Keyframe Animations
// =============================================================================

const pulseGlow = keyframes`
  0%, 100% {
    box-shadow: 0 0 20px rgba(255, 140, 26, 0.4), 0 0 40px rgba(255, 140, 26, 0.2);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 30px rgba(255, 140, 26, 0.6), 0 0 60px rgba(255, 140, 26, 0.3);
    transform: scale(1.05);
  }
`;

const swordGlow = keyframes`
  0%, 100% {
    text-shadow: 0 0 20px rgba(255, 140, 26, 0.8), 0 0 40px rgba(255, 140, 26, 0.4);
    filter: brightness(1);
  }
  50% {
    text-shadow: 0 0 30px rgba(255, 140, 26, 1), 0 0 60px rgba(255, 140, 26, 0.6);
    filter: brightness(1.2);
  }
`;

const winnerShine = keyframes`
  0% {
    background-position: -200% center;
  }
  100% {
    background-position: 200% center;
  }
`;

const slideInLeft = keyframes`
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
`;

const slideInRight = keyframes`
  from {
    opacity: 0;
    transform: translateX(30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
`;

// =============================================================================
// Sub-components
// =============================================================================

interface PlayerRowProps {
  player: TeamPlayerInfo;
  isWinner: boolean;
  side: 'left' | 'right';
  index: number;
  compact?: boolean;
}

const MMRChange: React.FC<{ change: number }> = ({ change }) => (
  <HStack spacing={0} color={change >= 0 ? 'green.400' : 'red.400'} flexShrink={0} minW="40px">
    <Icon as={change >= 0 ? FiArrowUp : FiArrowDown} boxSize={3} />
    <Text fontSize="sm" fontFamily="mono" fontWeight="bold">
      {Math.abs(change)}
    </Text>
  </HStack>
);

const PlayerRow: React.FC<PlayerRowProps> = ({ player, isWinner, side, index, compact }) => {
  const raceBgColor = getRaceColor(player.race);

  const rowContent = (
    <HStack
      spacing={3}
      justify={side === 'left' ? 'flex-end' : 'flex-start'}
      w="100%"
      animation={compact ? undefined : `${side === 'left' ? slideInLeft : slideInRight} 0.4s ease-out ${index * 0.1}s both`}
    >
      {side === 'right' && (
        <Badge
          bg={`${raceBgColor}.500`}
          color={player.race === 'Protoss' ? 'gray.900' : 'white'}
          fontSize="sm"
          fontWeight="bold"
          px={2}
          py={1}
          borderRadius="md"
          minW="28px"
          textAlign="center"
        >
          {getRaceIcon(player.race)}
        </Badge>
      )}

      <Text
        fontSize="md"
        fontWeight="semibold"
        fontFamily="heading"
        color={isWinner ? 'shield.400' : 'gray.100'}
        letterSpacing="wide"
        textShadow={isWinner && !compact ? '0 0 8px rgba(245, 158, 11, 0.5)' : 'none'}
        noOfLines={1}
        minW={{ base: 0, md: 'auto' }}
      >
        {player.name}
      </Text>

      <Text
        fontSize="sm"
        color="gray.400"
        fontFamily="mono"
        flexShrink={0}
      >
        {formatMMR(player.mmr)}
      </Text>

      {player.mmrChange !== undefined && <MMRChange change={player.mmrChange} />}

      {side === 'left' && (
        <Badge
          bg={`${raceBgColor}.500`}
          color={player.race === 'Protoss' ? 'gray.900' : 'white'}
          fontSize="sm"
          fontWeight="bold"
          px={2}
          py={1}
          borderRadius="md"
          minW="28px"
          textAlign="center"
        >
          {getRaceIcon(player.race)}
        </Badge>
      )}
    </HStack>
  );

  return rowContent;
};

interface TeamPanelProps {
  team: TeamData;
  teamNumber: 1 | 2;
  isWinner: boolean;
  side: 'left' | 'right';
  isPrediction?: boolean;
  probabilityLabel?: string;
  totalLabel?: string;
}

const TeamPanel: React.FC<TeamPanelProps> = ({ team, teamNumber, isWinner, side, isPrediction, probabilityLabel = 'Win Prob', totalLabel = 'Total MMR' }) => {
  const bgColor = useColorModeValue('gray.800', 'space.800');
  const borderColor = isWinner ? 'shield.500' : 'whiteAlpha.200';

  return (
    <Box
      flex={1}
      minW={{ base: 0, md: 'auto' }}
      p={{ base: 4, md: 5 }}
      bg={bgColor}
      borderRadius="xl"
      border="2px solid"
      borderColor={borderColor}
      position="relative"
      overflow={isWinner ? 'visible' : 'hidden'}
      transition="all 0.3s"
      _hover={{
        borderColor: isWinner ? 'shield.400' : 'brand.500',
        transform: 'translateY(-2px)',
      }}
      sx={isWinner ? {
        animation: `${pulseGlow} 2s ease-in-out infinite`,
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'linear-gradient(90deg, transparent, rgba(245, 158, 11, 0.1), transparent)',
          backgroundSize: '200% 100%',
          animation: `${winnerShine} 3s ease-in-out infinite`,
          pointerEvents: 'none',
        },
      } : {}}
    >
      {/* Winner/Favored Crown */}
      {isWinner && (
        <Box
          position="absolute"
          top="-12px"
          left="50%"
          transform="translateX(-50%)"
          fontSize="xs"
          fontWeight="bold"
          fontFamily="heading"
          px={3}
          py={1}
          bg={isPrediction ? 'whiteAlpha.300' : 'shield.500'}
          color={isPrediction ? 'gray.200' : 'space.900'}
          borderRadius="md"
          boxShadow={isPrediction ? 'none' : '0 3px 12px rgba(245, 158, 11, 0.6)'}
          zIndex={2}
          whiteSpace="nowrap"
          display="flex"
          alignItems="center"
          gap={1}
        >
          {isPrediction ? 'ADVANTAGE' : <><LuCrown aria-hidden /> WINNER</>}
        </Box>
      )}

      {/* Team Header */}
      <VStack spacing={4} align={side === 'left' ? 'flex-end' : 'flex-start'}>
        <HStack spacing={3} justify={side === 'left' ? 'flex-end' : 'flex-start'} w="100%">
          <Text
            fontSize="xl"
            fontWeight="black"
            fontFamily="heading"
            letterSpacing="wider"
            color={isWinner ? 'shield.400' : 'brand.400'}
            textShadow={isWinner ? '0 0 20px rgba(245, 158, 11, 0.6)' : '0 0 10px rgba(255, 140, 26, 0.3)'}
          >
            Team {teamNumber}
          </Text>
        </HStack>

        {/* Players List */}
        <VStack spacing={2} align={side === 'left' ? 'flex-end' : 'flex-start'} w="100%">
          {team.players.map((player, index) => (
            <PlayerRow
              key={`${player.name}-${index}`}
              player={player}
              isWinner={isWinner}
              side={side}
              index={index}
            />
          ))}
        </VStack>

        {/* Team Stats */}
        <Box
          w="100%"
          pt={3}
          borderTop="1px solid"
          borderColor="whiteAlpha.200"
        >
          <HStack justify={side === 'left' ? 'flex-end' : 'flex-start'} spacing={4}>
            <VStack spacing={0} align={side === 'left' ? 'flex-end' : 'flex-start'}>
              <Text fontSize="xs" color="gray.500" letterSpacing="wider">
                {totalLabel}
              </Text>
              <Text
                fontSize="lg"
                fontWeight="bold"
                fontFamily="mono"
                color={isWinner ? 'shield.400' : 'gray.200'}
              >
                {formatMMR(team.totalMMR)}
              </Text>
            </VStack>

            {team.winProbability !== undefined && (
              <VStack spacing={0} align={side === 'left' ? 'flex-end' : 'flex-start'}>
                <Text fontSize="xs" color="gray.500" letterSpacing="wider">
                  {probabilityLabel}
                </Text>
                <HStack spacing={1}>
                  <Text
                    fontSize="lg"
                    fontWeight="bold"
                    fontFamily="mono"
                    color={team.winProbability >= 50 ? 'shield.400' : 'gray.400'}
                  >
                    {team.winProbability.toFixed(1)}%
                  </Text>
                </HStack>
              </VStack>
            )}
          </HStack>
        </Box>
      </VStack>
    </Box>
  );
};

const CompactTeamPanel: React.FC<TeamPanelProps> = ({ team, teamNumber, isWinner, side, isPrediction, probabilityLabel = 'Win Prob', totalLabel = 'Total MMR' }) => {
  const align = side === 'left' ? 'flex-end' : 'flex-start';

  return (
    <Box
      flex={1}
      minW={0}
      px={{ base: 3, md: 4 }}
      py={3}
      bg="space.800"
      borderRadius="xl"
      border="1px solid"
      borderColor={isWinner ? 'shield.500' : 'whiteAlpha.100'}
    >
      <VStack spacing={2} align={align}>
        <Flex
          w="100%"
          direction={side === 'left' ? 'row-reverse' : 'row'}
          justify="space-between"
          align="center"
          gap={3}
          flexWrap="wrap"
          pb={2}
          borderBottom="1px solid"
          borderColor="whiteAlpha.100"
        >
          <Flex gap={2} align="center" direction={side === 'left' ? 'row-reverse' : 'row'}>
            <Text fontSize="md" fontWeight="black" fontFamily="heading" letterSpacing="wider" color={isWinner ? 'shield.400' : 'brand.400'}>
              Team {teamNumber}
            </Text>
            {isWinner && (
              <Badge
                display="flex"
                alignItems="center"
                gap={1}
                fontFamily="heading"
                fontSize="2xs"
                bg={isPrediction ? 'whiteAlpha.300' : 'shield.500'}
                color={isPrediction ? 'gray.200' : 'space.900'}
              >
                {isPrediction ? 'ADVANTAGE' : <><LuCrown aria-hidden /> WINNER</>}
              </Badge>
            )}
          </Flex>
          <HStack spacing={3} fontSize="xs" color="gray.500">
            <Text>
              {totalLabel}{' '}
              <Text as="span" fontFamily="mono" fontWeight="bold" color="gray.200">
                {formatMMR(team.totalMMR)}
              </Text>
            </Text>
            {team.winProbability !== undefined && (
              <Text>
                {probabilityLabel}{' '}
                <Text as="span" fontFamily="mono" fontWeight="bold" color={team.winProbability >= 50 ? 'shield.400' : 'gray.400'}>
                  {team.winProbability.toFixed(1)}%
                </Text>
              </Text>
            )}
          </HStack>
        </Flex>

        <VStack spacing={1} align={align} w="100%">
          {team.players.map((player, index) => (
            <PlayerRow
              key={`${player.name}-${index}`}
              player={player}
              isWinner={isWinner}
              side={side}
              index={index}
              compact
            />
          ))}
        </VStack>
      </VStack>
    </Box>
  );
};

// =============================================================================
// Main Component
// =============================================================================

const VSScreen: React.FC<VSScreenProps> = ({
  team1,
  team2,
  matchInfo,
  winner = null,
  onViewDetails,
  isPrediction = false,
  probabilityLabel,
  totalLabel,
  compact = false,
}) => {
  const bgColor = useColorModeValue('gray.900', 'space.900');
  const Panel = compact ? CompactTeamPanel : TeamPanel;

  return (
    <Box
      bg={bgColor}
      borderRadius="2xl"
      p={compact ? { base: 2, md: 3 } : { base: 3, md: 6 }}
      position="relative"
      overflow="hidden"
      border="1px solid"
      borderColor="whiteAlpha.100"
    >
      {/* Match Info Header */}
      {matchInfo && (
        <Box textAlign="center" mb={6}>
          <Text
            fontSize="sm"
            color="gray.500"
            letterSpacing="widest"
            fontWeight="bold"
          >
            {matchInfo.gameMode}
          </Text>
          <Text
            fontSize="lg"
            fontWeight="bold"
            fontFamily="heading"
            color="gray.300"
            letterSpacing="wide"
          >
            {matchInfo.mapName}
          </Text>
        </Box>
      )}

      {/* Main VS Layout */}
      <Flex
        direction={{ base: 'column', md: 'row' }}
        gap={compact ? 2 : 4}
        align="stretch"
        position="relative"
      >
        {/* Team 1 Panel */}
        <Panel
          team={team1}
          teamNumber={1}
          isWinner={winner === 1}
          side="left"
          isPrediction={isPrediction}
          probabilityLabel={probabilityLabel}
          totalLabel={totalLabel}
        />

        {/* VS Divider */}
        <Flex
          direction="column"
          align="center"
          justify="center"
          minW={{ base: 'auto', md: compact ? '48px' : '100px' }}
          py={{ base: 0, md: 0 }}
          position="relative"
        >
          {/* Vertical Line (hidden on mobile) */}
          <Box
            display={{ base: 'none', md: 'block' }}
            position="absolute"
            top={0}
            bottom={0}
            w="2px"
            bg="whiteAlpha.200"
          />

          {/* VS Icon */}
          <Box
            position="relative"
            zIndex={1}
            bg={bgColor}
            px={compact ? 1 : 3}
            py={compact ? 0 : 2}
          >
            <Text
              fontSize={compact ? { base: 'md', md: 'xl' } : { base: '2xl', md: '4xl' }}
              fontWeight="black"
              fontFamily="heading"
              color="brand.500"
              animation={compact ? undefined : `${swordGlow} 2s ease-in-out infinite`}
              letterSpacing="tight"
            >
              VS
            </Text>
          </Box>
        </Flex>

        {/* Team 2 Panel */}
        <Panel
          team={team2}
          teamNumber={2}
          isWinner={winner === 2}
          side="right"
          isPrediction={isPrediction}
          probabilityLabel={probabilityLabel}
          totalLabel={totalLabel}
        />
      </Flex>

      {/* View Details Button */}
      {onViewDetails && (
        <Box textAlign="center" mt={6}>
          <Button
            onClick={onViewDetails}
            variant="outline"
            colorScheme="brand"
            size="md"
            fontFamily="heading"
            fontWeight="bold"
            letterSpacing="wider"
            borderWidth={2}
            _hover={{
              bg: 'brand.500',
              color: 'gray.900',
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 20px rgba(255, 140, 26, 0.4)',
            }}
          >
            View Match Details
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default VSScreen;
