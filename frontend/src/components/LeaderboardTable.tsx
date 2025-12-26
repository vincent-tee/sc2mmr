/**
 * LeaderboardTable Component
 * Reusable table for displaying leaderboard rankings
 */
import React, { memo, useCallback } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  HStack,
  Badge,
  Flex,
  useColorModeValue,
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { keyframes } from '@emotion/react';
import {
  type LeaderboardEntry,
  type DuoLeaderboardEntry,
  type LeaderboardCategoryKey,
  getRankMedal,
  formatLeaderboardValue,
  isDuoCategory,
} from '@/types/leaderboard';
import { getRaceEmoji, getRaceColor } from '@/utils/formatting';
import { spacing, radii, transitions } from '@/theme/tokens';

// =============================================================================
// Types
// =============================================================================

export interface LeaderboardTableProps {
  /** Leaderboard entries */
  entries: LeaderboardEntry[] | DuoLeaderboardEntry[];
  /** Category key for formatting */
  category: LeaderboardCategoryKey;
  /** Show race icon */
  showRace?: boolean;
  /** Make rows clickable (navigates to player detail) */
  clickable?: boolean;
  /** Loading state */
  isLoading?: boolean;
  /** Empty state message */
  emptyMessage?: string;
  /** Custom value formatter */
  valueFormatter?: (value: number) => string;
  /** Maximum rows to display */
  maxRows?: number;
}

// =============================================================================
// Keyframe Animations
// =============================================================================

const medalShine = keyframes`
  0%, 100% {
    transform: scale(1);
    filter: brightness(1);
  }
  50% {
    transform: scale(1.1);
    filter: brightness(1.2);
  }
`;

// Row hover glow animation - available for future use
// const rowHoverGlow = keyframes`
//   0% { box-shadow: 0 0 0 rgba(255, 140, 26, 0); }
//   100% { box-shadow: 0 0 10px rgba(255, 140, 26, 0.3); }
// `;

// =============================================================================
// Medal Badge Component
// =============================================================================

interface MedalBadgeProps {
  rank: number;
}

const MedalBadge: React.FC<MedalBadgeProps> = memo(({ rank }) => {
  const medal = getRankMedal(rank);

  if (!medal) {
    return (
      <Text
        fontFamily="mono"
        fontSize="md"
        fontWeight="bold"
        color="gray.400"
        minW="30px"
        textAlign="center"
      >
        {rank}
      </Text>
    );
  }

  return (
    <Text
      fontSize="xl"
      animation={`${medalShine} 3s ease-in-out infinite`}
      minW="30px"
      textAlign="center"
      cursor="default"
      aria-label={`Rank ${rank}`}
    >
      {medal}
    </Text>
  );
});

MedalBadge.displayName = 'MedalBadge';

// =============================================================================
// Race Badge Component
// =============================================================================

interface RaceBadgeProps {
  race?: string;
}

const RaceBadge: React.FC<RaceBadgeProps> = memo(({ race }) => {
  if (!race) return null;

  const raceColor = getRaceColor(race);
  const raceEmoji = getRaceEmoji(race);

  return (
    <Badge
      bg={`${raceColor}.500`}
      color={race === 'Protoss' ? 'gray.900' : 'white'}
      fontSize="xs"
      fontWeight="bold"
      px={1.5}
      py={0.5}
      borderRadius="sm"
      minW="24px"
      textAlign="center"
    >
      {raceEmoji}
    </Badge>
  );
});

RaceBadge.displayName = 'RaceBadge';

// =============================================================================
// Standard Entry Row Component
// =============================================================================

interface StandardRowProps {
  entry: LeaderboardEntry;
  category: LeaderboardCategoryKey;
  showRace: boolean;
  clickable: boolean;
  valueFormatter?: (value: number) => string;
  onRowClick: (playerId: number) => void;
  rowBgColor: string;
  hoverBgColor: string;
  textColor: string;
  isTopThree: boolean;
}

const StandardRow: React.FC<StandardRowProps> = memo(({
  entry,
  category,
  showRace,
  clickable,
  valueFormatter,
  onRowClick,
  rowBgColor,
  hoverBgColor,
  textColor,
  isTopThree,
}) => {
  const formattedValue = valueFormatter
    ? valueFormatter(entry.value)
    : formatLeaderboardValue(entry.value, category);

  return (
    <Tr
      bg={isTopThree ? 'whiteAlpha.50' : rowBgColor}
      cursor={clickable ? 'pointer' : 'default'}
      onClick={clickable ? () => onRowClick(entry.player_id) : undefined}
      transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
      _hover={clickable ? {
        bg: hoverBgColor,
        transform: 'translateX(4px)',
      } : {}}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onKeyDown={clickable ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onRowClick(entry.player_id);
        }
      } : undefined}
      aria-label={clickable ? `View ${entry.name}'s profile` : undefined}
    >
      <Td borderColor="whiteAlpha.100" py={3}>
        <MedalBadge rank={entry.rank} />
      </Td>
      <Td borderColor="whiteAlpha.100" py={3}>
        <HStack spacing={2}>
          {showRace && <RaceBadge race={entry.extra_info} />}
          <Text
            fontWeight={isTopThree ? 'bold' : 'medium'}
            fontFamily="heading"
            letterSpacing="wide"
            color={isTopThree ? 'brand.300' : textColor}
            textShadow={isTopThree ? '0 0 10px rgba(255, 140, 26, 0.3)' : 'none'}
          >
            {entry.name}
          </Text>
        </HStack>
      </Td>
      <Td borderColor="whiteAlpha.100" py={3} isNumeric>
        <Text
          fontFamily="mono"
          fontWeight="bold"
          fontSize="md"
          color={isTopThree ? 'shield.400' : 'gray.200'}
        >
          {formattedValue}
        </Text>
        {entry.secondary_value !== undefined && (
          <Text fontSize="xs" color="gray.500">
            {entry.secondary_value.toLocaleString()}
          </Text>
        )}
      </Td>
    </Tr>
  );
});

StandardRow.displayName = 'StandardRow';

// =============================================================================
// Duo Entry Row Component
// =============================================================================

interface DuoRowProps {
  entry: DuoLeaderboardEntry;
  clickable: boolean;
  onRowClick: (playerId: number) => void;
  rowBgColor: string;
  hoverBgColor: string;
  textColor: string;
  isTopThree: boolean;
}

const DuoRow: React.FC<DuoRowProps> = memo(({
  entry,
  clickable,
  onRowClick,
  rowBgColor,
  hoverBgColor,
  textColor,
  isTopThree,
}) => {
  return (
    <Tr
      bg={isTopThree ? 'whiteAlpha.50' : rowBgColor}
      transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
      _hover={{
        bg: hoverBgColor,
      }}
    >
      <Td borderColor="whiteAlpha.100" py={3}>
        <MedalBadge rank={entry.rank} />
      </Td>
      <Td borderColor="whiteAlpha.100" py={3}>
        <Flex align="center" wrap="wrap" gap={2}>
          <Text
            fontWeight={isTopThree ? 'bold' : 'medium'}
            fontFamily="heading"
            letterSpacing="wide"
            color={isTopThree ? 'brand.300' : textColor}
            cursor={clickable ? 'pointer' : 'default'}
            onClick={clickable ? () => onRowClick(entry.player1_id) : undefined}
            _hover={clickable ? { textDecoration: 'underline' } : {}}
          >
            {entry.player1_name}
          </Text>
          <Text color="gray.500" fontSize="sm">
            &
          </Text>
          <Text
            fontWeight={isTopThree ? 'bold' : 'medium'}
            fontFamily="heading"
            letterSpacing="wide"
            color={isTopThree ? 'brand.300' : textColor}
            cursor={clickable ? 'pointer' : 'default'}
            onClick={clickable ? () => onRowClick(entry.player2_id) : undefined}
            _hover={clickable ? { textDecoration: 'underline' } : {}}
          >
            {entry.player2_name}
          </Text>
        </Flex>
      </Td>
      <Td borderColor="whiteAlpha.100" py={3} isNumeric>
        <Text
          fontFamily="mono"
          fontWeight="bold"
          fontSize="md"
          color={isTopThree ? 'shield.400' : 'gray.200'}
        >
          {entry.wins_together}W
        </Text>
        <Text fontSize="xs" color="gray.500">
          {(entry.win_rate * 100).toFixed(0)}% WR
        </Text>
      </Td>
    </Tr>
  );
});

DuoRow.displayName = 'DuoRow';

// =============================================================================
// Main Component
// =============================================================================

const LeaderboardTable: React.FC<LeaderboardTableProps> = ({
  entries,
  category,
  showRace = true,
  clickable = true,
  isLoading = false,
  emptyMessage = 'No leaderboard data available',
  valueFormatter,
  maxRows,
}) => {
  const navigate = useNavigate();

  const bgColor = useColorModeValue('white', 'space.800');
  const hoverBgColor = useColorModeValue('gray.50', 'whiteAlpha.100');
  const textColor = useColorModeValue('gray.800', 'gray.100');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.100');

  // Handle row click navigation
  const handleRowClick = useCallback((playerId: number) => {
    navigate(`/players/${playerId}`);
  }, [navigate]);

  // Type guard for duo entries
  const isDuo = isDuoCategory(category);

  // Limit entries if maxRows is set
  const displayedEntries = maxRows ? entries.slice(0, maxRows) : entries;

  // Loading state
  if (isLoading) {
    return (
      <Box
        bg={bgColor}
        borderRadius={radii.lg}
        p={spacing.xl}
        textAlign="center"
      >
        <Text color="gray.500" fontSize="lg">
          Loading leaderboard...
        </Text>
      </Box>
    );
  }

  // Empty state
  if (displayedEntries.length === 0) {
    return (
      <Box
        bg={bgColor}
        borderRadius={radii.lg}
        p={spacing.xl}
        textAlign="center"
      >
        <Text fontSize="4xl" mb={3}>
          {isDuo ? '🤝' : '🏆'}
        </Text>
        <Text color="gray.500" fontSize="lg">
          {emptyMessage}
        </Text>
      </Box>
    );
  }

  return (
    <Box
      bg={bgColor}
      borderRadius={radii.lg}
      border="1px solid"
      borderColor={borderColor}
      overflow="hidden"
    >
      <Table variant="simple" size="md">
        <Thead bg="whiteAlpha.50">
          <Tr>
            <Th
              borderColor={borderColor}
              color="gray.400"
              letterSpacing="wider"
              fontSize="xs"
              w="60px"
            >
              Rank
            </Th>
            <Th
              borderColor={borderColor}
              color="gray.400"
              letterSpacing="wider"
              fontSize="xs"
            >
              {isDuo ? 'Duo' : 'Player'}
            </Th>
            <Th
              borderColor={borderColor}
              color="gray.400"
              letterSpacing="wider"
              fontSize="xs"
              isNumeric
            >
              {isDuo ? 'Wins' : 'Value'}
            </Th>
          </Tr>
        </Thead>
        <Tbody>
          {displayedEntries.map((entry) => {
            const isTopThree = entry.rank <= 3;

            if (isDuo) {
              return (
                <DuoRow
                  key={`${(entry as DuoLeaderboardEntry).player1_id}-${(entry as DuoLeaderboardEntry).player2_id}`}
                  entry={entry as DuoLeaderboardEntry}
                  clickable={clickable}
                  onRowClick={handleRowClick}
                  rowBgColor="transparent"
                  hoverBgColor={hoverBgColor}
                  textColor={textColor}
                  isTopThree={isTopThree}
                />
              );
            }

            return (
              <StandardRow
                key={(entry as LeaderboardEntry).player_id}
                entry={entry as LeaderboardEntry}
                category={category}
                showRace={showRace}
                clickable={clickable}
                valueFormatter={valueFormatter}
                onRowClick={handleRowClick}
                rowBgColor="transparent"
                hoverBgColor={hoverBgColor}
                textColor={textColor}
                isTopThree={isTopThree}
              />
            );
          })}
        </Tbody>
      </Table>
    </Box>
  );
};

export default memo(LeaderboardTable);
