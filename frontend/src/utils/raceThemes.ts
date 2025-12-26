/**
 * Race-themed background utilities for SC2 MMR
 * Provides visual themes and styling helpers for each StarCraft 2 race
 */

import { colors, transitions } from '../theme/tokens';

export interface RaceTheme {
  name: string;
  primaryColor: string;
  gradientBg: string;
  glowColor: string;
  icon: string;
  /** @deprecated Use primaryColor for secondary color needs */
  secondaryColor?: string;
  pattern?: string;
}

/**
 * Race theme definitions with consistent styling
 * Colors: Terran #0080FF (blue), Protoss #FFD700 (gold), Zerg #9C27B0 (purple), Random gray
 */
export const RACE_THEMES: Record<string, RaceTheme> = {
  terran: {
    name: 'Terran',
    primaryColor: '#0080FF',
    gradientBg: 'linear-gradient(135deg, rgba(0, 128, 255, 0.15) 0%, rgba(0, 77, 153, 0.25) 100%)',
    glowColor: 'rgba(0, 128, 255, 0.4)',
    icon: 'T',
    secondaryColor: colors.race.terran[700],
    pattern: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0, 128, 255, 0.05) 10px, rgba(0, 128, 255, 0.05) 20px)',
  },
  protoss: {
    name: 'Protoss',
    primaryColor: '#FFD700',
    gradientBg: 'linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(153, 129, 0, 0.25) 100%)',
    glowColor: 'rgba(255, 215, 0, 0.4)',
    icon: 'P',
    secondaryColor: colors.race.protoss[600],
    pattern: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255, 215, 0, 0.05) 10px, rgba(255, 215, 0, 0.05) 20px)',
  },
  zerg: {
    name: 'Zerg',
    primaryColor: '#9C27B0',
    gradientBg: 'linear-gradient(135deg, rgba(156, 39, 176, 0.15) 0%, rgba(94, 23, 106, 0.25) 100%)',
    glowColor: 'rgba(156, 39, 176, 0.4)',
    icon: 'Z',
    secondaryColor: colors.race.zerg[700],
    pattern: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(156, 39, 176, 0.05) 10px, rgba(156, 39, 176, 0.05) 20px)',
  },
  random: {
    name: 'Random',
    primaryColor: '#616161',
    gradientBg: 'linear-gradient(135deg, rgba(97, 97, 97, 0.15) 0%, rgba(33, 33, 33, 0.25) 100%)',
    glowColor: 'rgba(97, 97, 97, 0.4)',
    icon: 'R',
    secondaryColor: colors.race.random[700],
    pattern: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(97, 97, 97, 0.05) 10px, rgba(97, 97, 97, 0.05) 20px)',
  },
};

/**
 * Get race theme by race identifier
 * @param race - Race identifier (terran, protoss, zerg, random)
 * @returns RaceTheme object
 */
export function getRaceTheme(race: string): RaceTheme {
  const normalizedRace = (race || '').toLowerCase().trim();
  return RACE_THEMES[normalizedRace] || RACE_THEMES.random;
}

/**
 * Get CSS gradient string for a race
 * @param race - Race identifier
 * @returns CSS gradient string
 */
export function getRaceGradient(race: string): string {
  return getRaceTheme(race).gradientBg;
}

/**
 * Get CSS rgba glow color for a race
 * @param race - Race identifier
 * @param intensity - Glow intensity level
 * @returns CSS rgba color string for use in box-shadow, etc.
 */
export function getRaceGlow(
  race: string,
  intensity: 'subtle' | 'medium' | 'strong' = 'medium'
): string {
  const theme = getRaceTheme(race);
  // glowColor is already in rgba format, adjust opacity based on intensity
  const baseGlow = theme.glowColor;

  // Parse base opacity and adjust
  const opacityMultiplier = intensity === 'subtle' ? 0.5 : intensity === 'strong' ? 1.5 : 1.0;

  return baseGlow.replace(
    /rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)/,
    (_, r, g, b, a) => {
      const newOpacity = Math.min(1, parseFloat(a) * opacityMultiplier);
      return `rgba(${r}, ${g}, ${b}, ${newOpacity.toFixed(2)})`;
    }
  );
}

/**
 * Get CSS box-shadow glow effect for a race
 * @param race - Race identifier
 * @param intensity - Glow intensity level
 * @returns CSS box-shadow string
 */
export function getRaceBoxShadow(
  race: string,
  intensity: 'subtle' | 'medium' | 'strong' = 'medium'
): string {
  const glowColor = getRaceGlow(race, intensity);
  const spreadRadius = intensity === 'subtle' ? '10px' : intensity === 'strong' ? '40px' : '20px';

  if (intensity === 'strong') {
    return `0 0 ${spreadRadius} ${glowColor}, 0 0 20px ${glowColor}`;
  }
  return `0 0 ${spreadRadius} ${glowColor}`;
}

/**
 * Get CSS text shadow for a race
 * @param race - Race identifier
 * @param intensity - Shadow intensity level
 * @returns CSS text-shadow string
 */
export function getRaceTextShadow(
  race: string,
  intensity: 'subtle' | 'medium' | 'strong' = 'medium'
): string {
  const theme = getRaceTheme(race);
  const color = theme.glowColor;

  switch (intensity) {
    case 'subtle':
      return `0 0 8px rgba(${hexToRgb(color)}, 0.4)`;
    case 'medium':
      return `0 0 16px rgba(${hexToRgb(color)}, 0.6)`;
    case 'strong':
      return `0 0 32px rgba(${hexToRgb(color)}, 0.8), 0 0 16px rgba(${hexToRgb(color)}, 0.6)`;
    default:
      return `0 0 16px rgba(${hexToRgb(color)}, 0.6)`;
  }
}

/**
 * Get CSS filter glow effect for a race
 * @param race - Race identifier
 * @param intensity - Filter intensity (0-1)
 * @returns CSS filter string
 */
export function getRaceFilterGlow(race: string, intensity: number = 0.5): string {
  const clampedIntensity = Math.max(0, Math.min(1, intensity));
  return `drop-shadow(0 0 ${10 * clampedIntensity}px ${getRaceTheme(race).glowColor})`;
}

/**
 * Convert hex color to RGB values
 * @param hex - Hex color string
 * @returns RGB values as "r, g, b"
 */
function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (result) {
    const r = parseInt(result[1], 16);
    const g = parseInt(result[2], 16);
    const b = parseInt(result[3], 16);
    return `${r}, ${g}, ${b}`;
  }
  return '128, 128, 128'; // fallback to gray
}

/**
 * Get race icon emoji
 * @param race - Race identifier
 * @returns Race icon emoji
 */
export function getRaceIcon(race: string): string {
  return getRaceTheme(race).icon;
}

/**
 * Check if race is valid
 * @param race - Race identifier
 * @returns True if race is valid
 */
export function isValidRace(race: string): boolean {
  const normalizedRace = (race || '').toLowerCase().trim();
  return Object.keys(RACE_THEMES).includes(normalizedRace);
}

/**
 * Get all valid race identifiers
 * @returns Array of race identifiers
 */
export function getAllRaces(): string[] {
  return Object.keys(RACE_THEMES);
}

/**
 * Race-themed style presets for common use cases
 */
export const raceStylePresets = {
  cardBackground: (race: string, intensity: 'subtle' | 'medium' | 'strong' = 'medium') => ({
    background: getRaceGradient(race),
    boxShadow: getRaceBoxShadow(race, intensity),
    transition: `all ${transitions.base} ${transitions.easing.easeInOut}`,
  }),

  textGlow: (race: string, intensity: 'subtle' | 'medium' | 'strong' = 'medium') => ({
    textShadow: getRaceTextShadow(race, intensity),
    transition: `text-shadow ${transitions.base} ${transitions.easing.easeInOut}`,
  }),

  borderGlow: (race: string, intensity: 'subtle' | 'medium' | 'strong' = 'medium') => {
    const theme = getRaceTheme(race);
    return {
      borderColor: theme.primaryColor,
      boxShadow: getRaceBoxShadow(race, intensity),
      transition: `all ${transitions.base} ${transitions.easing.easeInOut}`,
    };
  },

  hoverEffect: (race: string) => ({
    _hover: {
      boxShadow: getRaceBoxShadow(race, 'strong'),
      transform: 'translateY(-4px)',
      transition: `all ${transitions.fast} ${transitions.easing.easeOut}`,
    },
  }),
};
