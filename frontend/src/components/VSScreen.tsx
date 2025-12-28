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
  useColorModeValue,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { formatMMR, getRaceColor } from '../utils/formatting';

// =============================================================================
// Types
// =============================================================================

interface TeamPlayerInfo {
  name: string;
  mmr: number;
  race: string;
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

// getRaceIconColor available if needed for race-specific icon colors
// const getRaceIconColor = (race: string): string => {
//   const colorMap: Record<string, string> = {
//     Terran: 'terran.500',
//     Protoss: 'protoss.500',
//     Zerg: 'zerg.500',
//     Random: 'gray.400',
//   };
//   return colorMap[race] || 'gray.400';
// };

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
}

const PlayerRow: React.FC<PlayerRowProps> = ({ player, isWinner, side, index }) => {
  const raceBgColor = getRaceColor(player.race);

  const rowContent = (
    <HStack
      spacing={3}
      justify={side === 'left' ? 'flex-end' : 'flex-start'}
      w="100%"
      animation={`${side === 'left' ? slideInLeft : slideInRight} 0.4s ease-out ${index * 0.1}s both`}
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
        textShadow={isWinner ? '0 0 8px rgba(245, 158, 11, 0.5)' : 'none'}
        noOfLines={1}
      >
        {player.name}
      </Text>

      <Text
        fontSize="sm"
        color="gray.400"
        fontFamily="mono"
      >
        {formatMMR(player.mmr)}
      </Text>

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
}

const TeamPanel: React.FC<TeamPanelProps> = ({ team, teamNumber, isWinner, side }) => {
  const bgColor = useColorModeValue('gray.800', 'space.800');
  const borderColor = isWinner ? 'shield.500' : 'whiteAlpha.200';

  return (
    <Box
      flex={1}
      p={5}
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
      {/* Winner Crown */}
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
          bg="shield.500"
          color="space.900"
          borderRadius="md"
          boxShadow="0 3px 12px rgba(245, 158, 11, 0.6)"
          zIndex={2}
          whiteSpace="nowrap"
        >
          🏆 WINNER
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
                Total MMR
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
                  Win Prob
                </Text>
                <Text
                  fontSize="lg"
                  fontWeight="bold"
                  fontFamily="mono"
                  color={team.winProbability >= 50 ? 'shield.400' : 'gray.400'}
                >
                  {team.winProbability.toFixed(1)}%
                </Text>
              </VStack>
            )}
          </HStack>
        </Box>
      </VStack>
    </Box>
  );
};

// =============================================================================
// Win Probability Bar
// =============================================================================

interface WinProbabilityBarProps {
  team1Prob?: number;
  team2Prob?: number;
  winner?: 1 | 2 | null;
}

const WinProbabilityBar: React.FC<WinProbabilityBarProps> = ({ team1Prob, team2Prob, winner }) => {
  if (team1Prob === undefined || team2Prob === undefined) return null;

  return (
    <Box w="100%" maxW="600px" mx="auto" mt={4}>
      <HStack justify="space-between" mb={1}>
        <Text fontSize="xs" color="gray.500" fontWeight="bold">
          {team1Prob.toFixed(1)}%
        </Text>
        <Text fontSize="xs" color="gray.500" letterSpacing="wider">
          Pre-Match Odds
        </Text>
        <Text fontSize="xs" color="gray.500" fontWeight="bold">
          {team2Prob.toFixed(1)}%
        </Text>
      </HStack>
      <Box
        w="100%"
        h="8px"
        bg="whiteAlpha.200"
        borderRadius="full"
        overflow="hidden"
        position="relative"
      >
        <Box
          position="absolute"
          left={0}
          top={0}
          h="100%"
          w={`${team1Prob}%`}
          bg={winner === 1 ? 'shield.500' : 'brand.500'}
          borderRadius="full"
          transition="all 0.5s ease-out"
          boxShadow={winner === 1 ? '0 0 10px rgba(245, 158, 11, 0.6)' : '0 0 10px rgba(255, 140, 26, 0.4)'}
        />
        <Box
          position="absolute"
          right={0}
          top={0}
          h="100%"
          w={`${team2Prob}%`}
          bg={winner === 2 ? 'shield.500' : 'accent.500'}
          borderRadius="full"
          transition="all 0.5s ease-out"
          boxShadow={winner === 2 ? '0 0 10px rgba(245, 158, 11, 0.6)' : '0 0 10px rgba(239, 68, 68, 0.4)'}
        />
      </Box>
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
}) => {
  const bgColor = useColorModeValue('gray.900', 'space.900');

  return (
    <Box
      bg={bgColor}
      borderRadius="2xl"
      p={6}
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
        gap={4}
        align="stretch"
        position="relative"
      >
        {/* Team 1 Panel */}
        <TeamPanel
          team={team1}
          teamNumber={1}
          isWinner={winner === 1}
          side="left"
        />

        {/* VS Divider */}
        <Flex
          direction="column"
          align="center"
          justify="center"
          minW={{ base: 'auto', md: '100px' }}
          py={{ base: 4, md: 0 }}
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
            px={3}
            py={2}
          >
            <Text
              fontSize="4xl"
              fontWeight="black"
              fontFamily="heading"
              color="brand.500"
              animation={`${swordGlow} 2s ease-in-out infinite`}
              letterSpacing="tight"
            >
              VS
            </Text>
          </Box>
        </Flex>

        {/* Team 2 Panel */}
        <TeamPanel
          team={team2}
          teamNumber={2}
          isWinner={winner === 2}
          side="right"
        />
      </Flex>

      {/* Win Probability Bar */}
      <WinProbabilityBar
        team1Prob={team1.winProbability}
        team2Prob={team2.winProbability}
        winner={winner}
      />

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
