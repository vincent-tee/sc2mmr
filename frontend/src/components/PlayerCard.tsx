/**
 * PlayerCard Component
 * Friend Squad edition - Warm, personable, comic-book inspired
 */
import React, { useCallback, KeyboardEvent } from 'react';
import {
  Box,
  Avatar,
  Text,
  Badge,
  VStack,
  HStack,
  Tooltip,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import type { IconType } from 'react-icons';
import { LuCheck, LuFlame, LuSnowflake } from 'react-icons/lu';
import {
  getRaceColor,
  getPlayerRaces,
  getPlayerAvatarUrl,
  formatMMR,
} from '../utils/formatting';
import { getRankFromMMR } from '../utils/ranks';
import RankBadge from './RankBadge';

type CardSize = 'sm' | 'md' | 'lg';

interface SizeConfig {
  padding: number;
  avatarSize: 'sm' | 'md' | 'lg';
  nameSize: 'sm' | 'md' | 'lg';
  badgeSize: 'xs' | 'sm' | 'md';
}

interface RaceInfo {
  name: string;
  games: number;
  emoji: string;
}

// Extended player type for PlayerCard that includes display-specific fields
export interface PlayerCardData {
  id?: number;
  name: string;
  mmr: number;
  win_rate?: number;
  total_games?: number;
  terran_games?: number;
  protoss_games?: number;
  zerg_games?: number;
  random_games?: number;
  favorite_race?: string;
  is_ai?: boolean;
  recent_form?: number | null;  // Win rate from last 5 games
}

// Helper to get form badge based on recent form
const getFormBadge = (recentForm: number | null | undefined): { icon: IconType; color: string; label: string } | null => {
  if (recentForm === null || recentForm === undefined) return null;
  if (recentForm >= 0.7) return { icon: LuFlame, color: 'orange.400', label: 'Hot' };
  if (recentForm <= 0.3) return { icon: LuSnowflake, color: 'blue.400', label: 'Cold' };
  return null; // Stable form, no badge
};

interface PlayerCardProps {
  player: PlayerCardData;
  isSelected?: boolean;
  onClick?: () => void;
  size?: CardSize;
  variant?: 'default' | 'compact';
}

const PlayerCard: React.FC<PlayerCardProps> = ({
  player,
  isSelected = false,
  onClick,
  size = 'md',
  variant = 'default',
}) => {
  const cardBg = useColorModeValue('white', 'space.800');
  const borderColorDefault = useColorModeValue('gray.200', 'whiteAlpha.100');
  const avatarBorderColor = useColorModeValue('gray.800', 'space.900');

  const sizes: Record<CardSize, SizeConfig> = {
    sm: {
      padding: 2,
      avatarSize: 'sm',
      nameSize: 'sm',
      badgeSize: 'xs',
    },
    md: {
      padding: 4,
      avatarSize: 'md',
      nameSize: 'md',
      badgeSize: 'sm',
    },
    lg: {
      padding: 6,
      avatarSize: 'lg',
      nameSize: 'lg',
      badgeSize: 'md',
    },
  };

  const sizeConfig = sizes[size] || sizes.md;
  const playerRaces: RaceInfo[] = getPlayerRaces(player);
  const primaryRace = playerRaces.length > 0 ? playerRaces[0].name : 'Random';

  // Handle keyboard navigation for accessibility
  const handleKeyDown = useCallback((event: KeyboardEvent<HTMLDivElement>) => {
    if (onClick && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      onClick();
    }
  }, [onClick]);

  const formBadge = getFormBadge(player.recent_form);

  if (variant === 'compact') {
    const rank = getRankFromMMR(player.mmr);
    return (
      <HStack
        bg={cardBg}
        borderRadius="lg"
        border="1px solid"
        borderColor={isSelected ? 'brand.500' : borderColorDefault}
        boxShadow={isSelected ? '0 0 0 2px var(--chakra-colors-brand-500)' : 'none'}
        px={2.5}
        py={2}
        spacing={2.5}
        minW={0}
        cursor={onClick ? 'pointer' : 'default'}
        onClick={onClick}
        onKeyDown={handleKeyDown}
        tabIndex={onClick ? 0 : undefined}
        role={onClick ? 'button' : undefined}
        aria-label={onClick ? `Select player ${player.name}` : undefined}
        aria-pressed={onClick ? isSelected : undefined}
        transition="border-color 0.15s, box-shadow 0.15s"
        _hover={onClick ? { borderColor: 'brand.400' } : {}}
        _focusVisible={onClick ? {
          outline: 'none',
          boxShadow: '0 0 0 3px rgba(255, 107, 53, 0.5)',
          borderColor: 'brand.400',
        } : {}}
      >
        <Box position="relative" flexShrink={0}>
          <Avatar
            size="sm"
            src={getPlayerAvatarUrl(player.name, primaryRace, player.is_ai)}
            name={player.name}
            bg={`${getRaceColor(primaryRace)}.500`}
          />
          {isSelected && (
            <Box
              position="absolute"
              bottom="-2px"
              right="-4px"
              bg="brand.500"
              color="white"
              borderRadius="full"
              boxSize="16px"
              display="flex"
              alignItems="center"
              justifyContent="center"
              border="2px solid"
              borderColor="space.800"
            >
              <Icon as={LuCheck} boxSize="10px" strokeWidth={3} />
            </Box>
          )}
        </Box>
        <VStack spacing={0} align="start" flex={1} minW={0}>
          <HStack spacing={1} maxW="100%">
            <Text
              fontSize="sm"
              fontWeight="bold"
              fontFamily="heading"
              noOfLines={1}
              wordBreak="break-all"
              color={isSelected ? 'brand.300' : 'inherit'}
            >
              {player.name}
            </Text>
            {player.is_ai && (
              <Badge colorScheme="purple" variant="solid" fontSize="2xs" flexShrink={0}>AI</Badge>
            )}
          </HStack>
          <HStack spacing={1.5} fontSize="xs" color="gray.400">
            <Box w="6px" h="6px" borderRadius="full" bg={rank.bg} flexShrink={0} />
            <Text fontFamily="mono">{formatMMR(player.mmr)}</Text>
            {formBadge && (
              <Icon as={formBadge.icon} color={formBadge.color} boxSize="12px" flexShrink={0} aria-label={formBadge.label} />
            )}
            {player.total_games !== undefined && player.total_games < 5 && (
              <Text color="orange.300" whiteSpace="nowrap">new</Text>
            )}
          </HStack>
        </VStack>
      </HStack>
    );
  }

  return (
    <Box
      bg={cardBg}
      borderRadius="xl"
      border="1px solid"
      borderColor={isSelected ? 'brand.500' : borderColorDefault}
      boxShadow={isSelected ? '0 0 0 2px var(--chakra-colors-brand-500)' : 'none'}
      p={sizeConfig.padding}
      cursor={onClick ? 'pointer' : 'default'}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : undefined}
      aria-label={onClick ? `Select player ${player.name}` : undefined}
      aria-pressed={onClick ? isSelected : undefined}
      transition="all 0.25s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
      _hover={onClick ? {
        transform: 'translateY(-2px)',
        boxShadow: isSelected ? '0 0 0 2px var(--chakra-colors-brand-500)' : '0 8px 20px rgba(0, 0, 0, 0.35)',
        borderColor: 'brand.400',
      } : {}}
      _focus={onClick ? {
        outline: 'none',
        boxShadow: '0 0 0 3px rgba(255, 107, 53, 0.5)',
        borderColor: 'brand.400',
      } : {}}
      position="relative"
      overflow="hidden"
    >
      {/* Selection checkmark */}
      {isSelected && (
        <Box
          position="absolute"
          top={2}
          right={2}
          bg="brand.500"
          color="white"
          borderRadius="full"
          width="24px"
          height="24px"
          display="flex"
          alignItems="center"
          justifyContent="center"
          fontSize="sm"
          fontWeight="bold"
          border="2px solid"
          borderColor="space.900"
        >
          ✓
        </Box>
      )}

      <VStack spacing={3} align="center" pt={2}>
        <Avatar
          size={sizeConfig.avatarSize}
          src={getPlayerAvatarUrl(player.name, primaryRace, player.is_ai)}
          name={player.name}
          bg={`${getRaceColor(primaryRace)}.500`}
          border="3px solid"
          borderColor={avatarBorderColor}
        />

        <VStack spacing={1.5} align="center" width="100%">
          <HStack justify="center" width="100%">
            {/* Form Badge - Hot/Cold indicator */}
            {getFormBadge(player.recent_form) && (
              <Tooltip
                label={`${getFormBadge(player.recent_form)?.label}: ${Math.round((player.recent_form || 0) * 100)}% last 5 games`}
                hasArrow
                fontSize="xs"
              >
                <Box color={getFormBadge(player.recent_form)?.color} filter="drop-shadow(0 0 4px currentColor)">
                  <Icon as={getFormBadge(player.recent_form)!.icon} boxSize="14px" display="block" />
                </Box>
              </Tooltip>
            )}
            <Text
              fontSize={sizeConfig.nameSize}
              fontWeight="bold"
              textAlign="center"
              noOfLines={1}
              fontFamily="heading"
              color={isSelected ? 'brand.400' : 'inherit'}
            >
              {player.name}
            </Text>
            {player.is_ai && (
              <Badge colorScheme="purple" variant="solid" fontSize="2xs" borderRadius="full">
                AI
              </Badge>
            )}
          </HStack>

          {/* Rank Badge - Shows SC2 rank based on MMR (the rating of record) */}
          <RankBadge
            mmr={player.mmr}
            size={sizeConfig.badgeSize}
            showMMR={true}
            showIcon={size !== 'sm'}
          />

          {/* New Player Indicator */}
          {player.total_games !== undefined && player.total_games < 5 && (
            <Badge
              colorScheme="orange"
              fontSize="xs"
              px={2}
              py={0.5}
              borderRadius="md"
              letterSpacing="wider"
            >
              New ({player.total_games} games)
            </Badge>
          )}


        </VStack>
      </VStack>
    </Box>
  );
};

export default React.memo(PlayerCard);
