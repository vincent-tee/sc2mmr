/**
 * RaceBackground Component
 * Provides race-themed background styling for cards and containers
 * with customizable intensity levels and smooth transitions
 */

import React, { CSSProperties, ReactNode } from 'react';
import { Box, BoxProps } from '@chakra-ui/react';
import {
  getRaceTheme,
  getRaceBoxShadow,
  getRaceGradient,
  getRaceIcon,
  isValidRace,
} from '../utils/raceThemes';
import { transitions } from '../theme/tokens';

export interface RaceBackgroundProps extends BoxProps {
  /**
   * Race identifier: 'terran', 'protoss', 'zerg', or 'random'
   */
  race: string;

  /**
   * Child elements to render inside the background container
   */
  children: ReactNode;

  /**
   * Background intensity: 'subtle', 'medium', or 'strong'
   * @default 'medium'
   */
  intensity?: 'subtle' | 'medium' | 'strong';

  /**
   * Show race icon in the background
   * @default false
   */
  showRaceIcon?: boolean;

  /**
   * Position of race icon: 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'
   * @default 'top-right'
   */
  iconPosition?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';

  /**
   * Icon size in pixels
   * @default 32
   */
  iconSize?: number;

  /**
   * Icon opacity (0-1)
   * @default 0.15
   */
  iconOpacity?: number;

  /**
   * Apply animated glow effect on hover
   * @default true
   */
  hoverGlow?: boolean;

  /**
   * Border style for race theme
   * @default 'none'
   */
  borderStyle?: 'none' | 'subtle' | 'medium' | 'strong';

  /**
   * Apply pattern overlay
   * @default true
   */
  showPattern?: boolean;
}

/**
 * Helper function to get icon position styles
 */
function getIconPositionStyles(
  position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center'
): CSSProperties {
  const baseStyles: CSSProperties = {
    position: 'absolute',
    fontSize: 'inherit',
  };

  switch (position) {
    case 'top-left':
      return { ...baseStyles, top: '12px', left: '12px' };
    case 'top-right':
      return { ...baseStyles, top: '12px', right: '12px' };
    case 'bottom-left':
      return { ...baseStyles, bottom: '12px', left: '12px' };
    case 'bottom-right':
      return { ...baseStyles, bottom: '12px', right: '12px' };
    case 'center':
      return { ...baseStyles, top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
    default:
      return { ...baseStyles, top: '12px', right: '12px' };
  }
}

/**
 * Get intensity multiplier for effects
 */
function getIntensityMultiplier(intensity: 'subtle' | 'medium' | 'strong'): number {
  switch (intensity) {
    case 'subtle':
      return 0.5;
    case 'medium':
      return 1;
    case 'strong':
      return 1.5;
    default:
      return 1;
  }
}

/**
 * RaceBackground Component
 * Renders a container with race-themed background styling
 *
 * @example
 * ```tsx
 * <RaceBackground race="terran" intensity="medium">
 *   <Card>Your content here</Card>
 * </RaceBackground>
 * ```
 */
export const RaceBackground: React.FC<RaceBackgroundProps> = ({
  race,
  children,
  intensity = 'medium',
  showRaceIcon = false,
  iconPosition = 'top-right',
  iconSize = 32,
  iconOpacity = 0.15,
  hoverGlow = true,
  borderStyle = 'none',
  showPattern = true,
  ...boxProps
}) => {
  const theme = getRaceTheme(race);
  const isValid = isValidRace(race);
  const intensityMultiplier = getIntensityMultiplier(intensity);

  // Determine border styling based on intensity
  const getBorderStyles = () => {
    if (borderStyle === 'none') return {};

    const borderWidth =
      borderStyle === 'subtle' ? '1px' : borderStyle === 'medium' ? '2px' : '3px';

    return {
      border: `${borderWidth} solid`,
      borderColor: theme.primaryColor,
      boxShadow: getRaceBoxShadow(race, intensity),
    };
  };

  // Determine initial box shadow
  const initialBoxShadow =
    borderStyle !== 'none'
      ? getRaceBoxShadow(race, intensity)
      : intensity === 'subtle'
        ? 'none'
        : getRaceBoxShadow(race, intensity);

  // Build style object
  const styleObject: CSSProperties = {
    background: getRaceGradient(race),
    position: 'relative',
    overflow: 'hidden',
    boxShadow: initialBoxShadow,
    transition: `all ${transitions.base} ${transitions.easing.easeInOut}`,
    ...getBorderStyles(),
  };

  // Add hover effect if enabled
  const _hover = hoverGlow
    ? {
        boxShadow: getRaceBoxShadow(race, 'strong'),
        filter: `brightness(${1 + 0.1 * intensityMultiplier})`,
      }
    : undefined;

  return (
    <Box
      {...boxProps}
      sx={{
        ...styleObject,
        _hover,
      }}
    >
      {/* Pattern Overlay */}
      {showPattern && theme.pattern && (
        <Box
          as="div"
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          pointerEvents="none"
          opacity={0.3}
          sx={{
            background: theme.pattern,
          }}
        />
      )}

      {/* Race Icon Background */}
      {showRaceIcon && (
        <Box
          as="div"
          position="absolute"
          fontSize={`${iconSize}px`}
          opacity={iconOpacity}
          pointerEvents="none"
          userSelect="none"
          sx={getIconPositionStyles(iconPosition)}
        >
          {getRaceIcon(race)}
        </Box>
      )}

      {/* Content */}
      <Box position="relative" zIndex={1}>
        {children}
      </Box>

      {/* Validation Message (Development Only) */}
      {!isValid && import.meta.env.DEV && (
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          display="flex"
          alignItems="center"
          justifyContent="center"
          bg="rgba(255, 0, 0, 0.3)"
          borderRadius="inherit"
        >
          <Box color="white" textAlign="center" zIndex={2}>
            Invalid race: {race}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default RaceBackground;
