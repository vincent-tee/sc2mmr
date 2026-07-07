/**
 * AchievementBadge Component
 * Hexagonal badge displaying achievement with rarity-based glow effects
 */
import React, { memo } from 'react';
import {
  Box,
  Text,
  Tooltip,
  VStack,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiLock } from 'react-icons/fi';
import { keyframes } from '@emotion/react';
import {
  type AchievementRarity,
  type AchievementCategory,
  RARITY_COLORS,
  getRarityLabel,
} from '@/types/achievements';
import { layout, transitions } from '@/theme/tokens';
import { formatDateTime } from '@/utils/formatting';

// =============================================================================
// Types
// =============================================================================

export interface AchievementBadgeProps {
  /** Unique achievement code */
  code: string;
  /** Achievement name */
  name: string;
  /** Achievement description */
  description: string;
  /** Flavor text (lore/fun text) */
  flavor_text?: string;
  /** Icon emoji */
  icon: string;
  /** Achievement rarity */
  rarity: AchievementRarity;
  /** Achievement category */
  category: AchievementCategory;
  /** Points value */
  points: number;
  /** Whether achievement is earned */
  earned?: boolean;
  /** Timestamp when earned */
  earned_at?: string;
  /** Show tooltip on hover */
  showTooltip?: boolean;
  /** Badge size */
  size?: 'sm' | 'md' | 'lg';
  /** Click handler */
  onClick?: () => void;
}

// =============================================================================
// Size Configuration
// =============================================================================

interface SizeConfig {
  container: string;
  hexagon: string;
  glowSize: string;
  iconSize: string;
  cornerDotSize: string;
}

const SIZE_CONFIG: Record<'sm' | 'md' | 'lg', SizeConfig> = {
  sm: {
    container: '60px',
    hexagon: '48px',
    glowSize: '56px',
    iconSize: '20px',
    cornerDotSize: '3px',
  },
  md: {
    container: '90px',
    hexagon: '72px',
    glowSize: '84px',
    iconSize: '28px',
    cornerDotSize: '4px',
  },
  lg: {
    container: '120px',
    hexagon: '96px',
    glowSize: '112px',
    iconSize: '36px',
    cornerDotSize: '5px',
  },
};

// =============================================================================
// Keyframe Animations
// =============================================================================

const pulseGlow = keyframes`
  0%, 100% {
    opacity: 0.4;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0.7;
    transform: translate(-50%, -50%) scale(1.05);
  }
`;

const shimmer = keyframes`
  0% {
    background-position: -200% center;
  }
  100% {
    background-position: 200% center;
  }
`;

const lockPulse = keyframes`
  0%, 100% {
    opacity: 0.6;
  }
  50% {
    opacity: 0.8;
  }
`;

// =============================================================================
// Tooltip Content Component
// =============================================================================

interface TooltipContentProps {
  name: string;
  description: string;
  flavor_text?: string;
  rarity: AchievementRarity;
  points: number;
  earned?: boolean;
  earned_at?: string;
}

const TooltipContent: React.FC<TooltipContentProps> = ({
  name,
  description,
  flavor_text,
  rarity,
  points,
  earned,
  earned_at,
}) => {
  const rarityColors = RARITY_COLORS[rarity];

  return (
    <VStack align="start" spacing={1} maxW="250px" p={1}>
      <Text fontWeight="bold" color={rarityColors.text} fontSize="md">
        {name}
      </Text>
      <Text fontSize="sm" color="gray.200">
        {description}
      </Text>
      {flavor_text && (
        <Text fontSize="xs" fontStyle="italic" color="gray.400" mt={1}>
          "{flavor_text}"
        </Text>
      )}
      <Box
        mt={2}
        pt={2}
        borderTop="1px solid"
        borderColor="whiteAlpha.200"
        w="100%"
      >
        <Text fontSize="xs" color="gray.400">
          {getRarityLabel(rarity)} - {points} points
        </Text>
        {earned && earned_at && (
          <Text fontSize="xs" color="green.400" mt={1}>
            Earned: {formatDateTime(earned_at)}
          </Text>
        )}
        {!earned && (
          <Text fontSize="xs" color="gray.500" mt={1}>
            Not yet earned
          </Text>
        )}
      </Box>
    </VStack>
  );
};

// =============================================================================
// Main Component
// =============================================================================

const AchievementBadge: React.FC<AchievementBadgeProps> = ({
  code: _code,
  name,
  description,
  flavor_text,
  icon,
  rarity,
  category: _category,
  points,
  earned = false,
  earned_at,
  showTooltip = true,
  size = 'md',
  onClick,
}) => {
  // Props prefixed with _ are intentionally unused but kept for API consistency
  void _code;
  void _category;
  const sizeConfig = SIZE_CONFIG[size];
  const rarityColors = RARITY_COLORS[rarity];
  const bgColor = useColorModeValue('gray.700', 'space.800');

  const badge = (
    <Box
      position="relative"
      width={sizeConfig.container}
      height={sizeConfig.container}
      cursor={onClick ? 'pointer' : 'default'}
      onClick={onClick}
      role="button"
      tabIndex={onClick ? 0 : undefined}
      aria-label={`${name} achievement - ${earned ? 'earned' : 'locked'}`}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
      transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
      _hover={onClick ? {
        transform: 'scale(1.1)',
      } : {}}
      _focus={{
        outline: 'none',
        boxShadow: earned ? rarityColors.glow : 'none',
      }}
    >
      {/* Glow effect (only for earned badges) */}
      {earned && rarityColors.glow !== 'none' && (
        <Box
          position="absolute"
          top="50%"
          left="50%"
          transform="translate(-50%, -50%)"
          width={sizeConfig.glowSize}
          height={sizeConfig.glowSize}
          bg={rarityColors.border}
          clipPath={layout.hexagonClipPath}
          opacity={0.3}
          filter="blur(12px)"
          animation={`${pulseGlow} 2s ease-in-out infinite`}
          pointerEvents="none"
        />
      )}

      {/* Hexagon background */}
      <Box
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        width={sizeConfig.hexagon}
        height={sizeConfig.hexagon}
        bg={earned ? rarityColors.bg : bgColor}
        clipPath={layout.hexagonClipPath}
        border="2px solid"
        borderColor={earned ? rarityColors.border : 'gray.600'}
        boxShadow={earned ? rarityColors.glow : 'none'}
        transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
        filter={!earned ? 'grayscale(100%)' : 'none'}
        opacity={!earned ? 0.5 : 1}
        overflow="hidden"
        _hover={{
          transform: earned
            ? 'translate(-50%, -50%) scale(1.05)'
            : 'translate(-50%, -50%)',
          boxShadow: earned ? rarityColors.glow : 'none',
        }}
      >
        {/* Shimmer effect for legendary/mythic */}
        {earned && (rarity === 'legendary' || rarity === 'mythic') && (
          <Box
            position="absolute"
            top={0}
            left={0}
            right={0}
            bottom={0}
            background={`linear-gradient(90deg, transparent, ${rarityColors.border}40, transparent)`}
            backgroundSize="200% 100%"
            animation={`${shimmer} 3s ease-in-out infinite`}
            pointerEvents="none"
          />
        )}
      </Box>

      {/* Icon */}
      <Box
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        fontSize={sizeConfig.iconSize}
        filter={!earned ? 'grayscale(100%)' : 'none'}
        opacity={!earned ? 0.4 : 1}
        transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
        zIndex={2}
        userSelect="none"
      >
        {earned ? icon : <Icon as={FiLock} color="gray.500" />}
      </Box>

      {/* Lock overlay for unearned */}
      {!earned && (
        <Box
          position="absolute"
          top="50%"
          left="50%"
          transform="translate(-50%, -50%)"
          width={sizeConfig.hexagon}
          height={sizeConfig.hexagon}
          clipPath={layout.hexagonClipPath}
          bg="blackAlpha.400"
          animation={`${lockPulse} 3s ease-in-out infinite`}
          pointerEvents="none"
        />
      )}

      {/* Corner dots (decorative, visible on earned) */}
      {earned && (
        <>
          <Box
            position="absolute"
            top="15%"
            left="20%"
            width={sizeConfig.cornerDotSize}
            height={sizeConfig.cornerDotSize}
            bg={rarityColors.border}
            borderRadius="full"
            boxShadow={`0 0 6px ${rarityColors.border}`}
          />
          <Box
            position="absolute"
            top="15%"
            right="20%"
            width={sizeConfig.cornerDotSize}
            height={sizeConfig.cornerDotSize}
            bg={rarityColors.border}
            borderRadius="full"
            boxShadow={`0 0 6px ${rarityColors.border}`}
          />
          <Box
            position="absolute"
            bottom="15%"
            left="20%"
            width={sizeConfig.cornerDotSize}
            height={sizeConfig.cornerDotSize}
            bg={rarityColors.border}
            borderRadius="full"
            boxShadow={`0 0 6px ${rarityColors.border}`}
          />
          <Box
            position="absolute"
            bottom="15%"
            right="20%"
            width={sizeConfig.cornerDotSize}
            height={sizeConfig.cornerDotSize}
            bg={rarityColors.border}
            borderRadius="full"
            boxShadow={`0 0 6px ${rarityColors.border}`}
          />
        </>
      )}
    </Box>
  );

  if (!showTooltip) {
    return badge;
  }

  return (
    <Tooltip
      label={
        <TooltipContent
          name={name}
          description={description}
          flavor_text={flavor_text}
          rarity={rarity}
          points={points}
          earned={earned}
          earned_at={earned_at}
        />
      }
      placement="top"
      hasArrow
      bg="gray.800"
      color="white"
      borderRadius="md"
      p={2}
    >
      {badge}
    </Tooltip>
  );
};

export default memo(AchievementBadge);
