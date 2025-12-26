/**
 * TacticalBackground Component
 * Reusable animated hex grid background used across tactical pages
 * Features:
 * - Animated grid pattern with tactical cyan color
 * - Fixed positioning for full-screen coverage
 * - Customizable opacity and grid size
 * - Low performance impact (uses CSS only)
 */

import { Box, type BoxProps } from '@chakra-ui/react';

/**
 * Props for TacticalBackground component
 */
interface TacticalBackgroundProps extends BoxProps {
  /** Opacity of the background (0-1). Default: 0.03 */
  opacity?: number;
  /** Whether the background should animate. Default: false */
  animated?: boolean;
  /** Background color variant. Default: 'cyan' */
  variant?: 'cyan' | 'gold' | 'green' | 'custom';
  /** Custom color for the grid. Used when variant is 'custom' */
  customColor?: string;
  /** Size of grid cells in pixels. Default: 40 */
  gridSize?: number;
}

/**
 * Color presets for different tactical variants
 */
const colorPresets = {
  cyan: 'rgba(0, 212, 255, 0.5)', // Tactical cyan (brand primary)
  gold: 'rgba(255, 179, 0, 0.5)', // Vespene gold (accent)
  green: 'rgba(0, 255, 136, 0.5)', // Shield green (success)
};

/**
 * TacticalBackground Component
 * Renders a fixed full-screen animated hex grid pattern
 *
 * @example
 * // Basic usage - default cyan grid
 * <TacticalBackground />
 *
 * @example
 * // Custom opacity
 * <TacticalBackground opacity={0.05} />
 *
 * @example
 * // Gold variant with animation
 * <TacticalBackground variant="gold" animated={true} />
 *
 * @example
 * // Custom color and grid size
 * <TacticalBackground
 *   variant="custom"
 *   customColor="rgba(156, 39, 176, 0.5)"
 *   gridSize={30}
 * />
 */
const TacticalBackground: React.FC<TacticalBackgroundProps> = ({
  opacity = 0.03,
  animated = false,
  variant = 'cyan',
  customColor,
  gridSize = 40,
  ...boxProps
}) => {
  // Determine the grid color
  const gridColor = variant === 'custom'
    ? customColor || colorPresets.cyan
    : colorPresets[variant] || colorPresets.cyan;

  // Create the linear gradient pattern for hex grid effect
  const backgroundImage = `linear-gradient(${gridColor} 1px, transparent 1px), linear-gradient(90deg, ${gridColor} 1px, transparent 1px)`;

  return (
    <Box
      position="fixed"
      top={0}
      left={0}
      right={0}
      bottom={0}
      opacity={opacity}
      pointerEvents="none"
      backgroundImage={backgroundImage}
      backgroundSize={`${gridSize}px ${gridSize}px`}
      zIndex={0}
      transition={animated ? 'opacity 0.3s ease-in-out' : 'none'}
      {...boxProps}
    />
  );
};

export default TacticalBackground;
