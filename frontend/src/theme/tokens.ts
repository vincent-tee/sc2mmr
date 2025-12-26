/**
 * Design Tokens for SC2 MMR Tracker
 * Centralized color, spacing, and styling values
 * Replaces hardcoded values throughout the codebase
 */

// Color palette - Warm oranges, reds, golds SC2 theme
export const colors = {
  // Brand/Primary palette - Warm Orange/Amber (primary warmth)
  brand: {
    50: '#FFF7ED',
    100: '#FFEAD5',
    200: '#FFD6A8',
    300: '#FFC178',
    400: '#FFAA44',
    500: '#FF8C1A', // Primary warm orange
    600: '#E67E0A',
    700: '#CC6B1F',
    800: '#B35E1F',
    900: '#8B4513',
  },

  // Accent palette - Deep Red/Burgundy (warm secondary)
  accent: {
    50: '#FEF2F2',
    100: '#FEE2E2',
    200: '#FECACA',
    300: '#FCA5A5',
    400: '#F87171',
    500: '#EF4444', // Deep red accent
    600: '#DC2626',
    700: '#B91C1C',
    800: '#991B1B',
    900: '#7F1D1D',
  },

  // Gold/Bronze (success/positive & accents)
  shield: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    200: '#FDE68A',
    300: '#FCD34D',
    400: '#FBBF24',
    500: '#F59E0B', // Gold accent
    600: '#D97706',
    700: '#B45309',
    800: '#92400E',
    900: '#78350F',
  },

  // Warm grays & dark warm tones (background) - Warm aesthetic
  space: {
    50: '#FAF5F0',
    100: '#F5EFE7',
    200: '#EAE5DC',
    300: '#D4C9B9',
    400: '#B5A89A',
    500: '#8B7355', // Warm brown-gray
    600: '#6B5B47',
    700: '#504535',
    800: '#3C3428',
    900: '#2A241F', // Deep warm brown
  },

  // StarCraft 2 race colors
  race: {
    terran: {
      50: '#E0F2FF',
      100: '#BAE0FF',
      200: '#7FCBFF',
      300: '#48B5FF',
      400: '#1A9FFF',
      500: '#0080FF', // Terran blue
      600: '#0066CC',
      700: '#004D99',
      800: '#003366',
      900: '#001A33',
    },
    protoss: {
      50: '#FFFAF0',
      100: '#FFE8B3',
      200: '#FFD700', // Protoss gold
      300: '#E6C200',
      400: '#CCAC00',
      500: '#CCAC00',
      600: '#998100',
      700: '#665600',
      800: '#332B00',
      900: '#1A1600',
    },
    zerg: {
      50: '#F3E5F5',
      100: '#E1BEE7',
      200: '#CE93D8',
      300: '#BA68C8',
      400: '#AB47BC',
      500: '#9C27B0', // Zerg purple
      600: '#7D1F8D',
      700: '#5E176A',
      800: '#3E0D47',
      900: '#1F0624',
    },
    random: {
      50: '#F5F5F5',
      100: '#E0E0E0',
      200: '#BDBDBD',
      300: '#9E9E9E',
      400: '#757575',
      500: '#616161', // Random gray
      600: '#424242',
      700: '#212121',
      800: '#121212',
      900: '#000000',
    },
  },

  // Status/semantic colors
  status: {
    win: '#00FF88', // Shield green
    loss: '#FF4444',
    draw: '#FFB300', // Accent gold
    neutral: '#808080',
  },

  // Background colors
  background: {
    card: 'rgba(26, 32, 44, 0.8)',
    cardHover: 'rgba(45, 55, 72, 0.8)',
    overlay: 'rgba(13, 17, 33, 0.95)',
    selected: 'rgba(0, 82, 102, 0.3)',
  },

  // Text/semantic colors
  text: {
    primary: '#FFFFFF',
    secondary: '#A0AEC0',
    disabled: '#718096',
    muted: '#4A5568',
  },

  // Border colors
  border: {
    light: 'rgba(255, 255, 255, 0.1)',
    medium: 'rgba(0, 212, 255, 0.3)',
    brand: '#00D4FF',
    accent: '#FFB300',
  },
} as const;

// Spacing scale - consistent sizing
export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
  '2xl': '32px',
  '3xl': '48px',
  '4xl': '64px',
} as const;

// Border radius scale
export const radii = {
  none: '0',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
} as const;

// Shadow definitions
export const shadows = {
  none: 'none',
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
  // Brand/tactical shadows
  brandGlow: '0 0 20px rgba(0, 212, 255, 0.4)',
  brandGlowLarge: '0 0 40px rgba(0, 212, 255, 0.8)',
  brandGlowSubtle: '0 0 10px rgba(0, 212, 255, 0.6)',
  accentGlow: '0 0 20px rgba(255, 179, 0, 0.4)',
  accentGlowSubtle: '0 0 10px rgba(255, 179, 0, 0.6)',
  shieldGlow: '0 0 20px rgba(0, 255, 136, 0.4)',
  shieldGlowSubtle: '0 0 8px rgba(0, 255, 136, 0.5)',
  zergGlow: '0 0 20px rgba(156, 39, 176, 0.4)',
  zergGlowSubtle: '0 0 10px rgba(156, 39, 176, 0.6)',
  elevation: '0 0 20px rgba(0, 212, 255, 0.2)',
  hoverElevation: '0 8px 30px rgba(0, 212, 255, 0.4), 0 0 20px rgba(0, 212, 255, 0.4)',
} as const;

// Typography scale
export const typography = {
  fontSize: {
    xs: '12px',
    sm: '14px',
    md: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '30px',
    '4xl': '36px',
  },
  fontWeight: {
    light: 300,
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
    black: 900,
  },
  fontFamily: {
    heading: "'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    body: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  lineHeight: {
    none: '1',
    tight: '1.25',
    snug: '1.375',
    normal: '1.5',
    relaxed: '1.625',
    loose: '2',
  },
  letterSpacing: {
    none: '0',
    xs: '0.04em',
    sm: '0.05em',
    md: '0.1em',
    lg: '0.15em',
    wide: '0.15em',
    wider: '0.2em',
  },
} as const;

// Transition/animation timing
export const transitions = {
  fast: '150ms',
  base: '250ms',
  slow: '350ms',
  slowest: '500ms',
  easing: {
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
  },
} as const;

// Size scale for components
export const sizes = {
  button: {
    sm: {
      height: '32px',
      fontSize: '12px',
      padding: '0 12px',
    },
    md: {
      height: '40px',
      fontSize: '14px',
      padding: '0 16px',
    },
    lg: {
      height: '48px',
      fontSize: '16px',
      padding: '0 24px',
    },
  },
  input: {
    sm: {
      height: '32px',
      fontSize: '12px',
      padding: '0 8px',
    },
    md: {
      height: '40px',
      fontSize: '14px',
      padding: '0 12px',
    },
    lg: {
      height: '48px',
      fontSize: '16px',
      padding: '0 16px',
    },
  },
} as const;

// Breakpoints for responsive design
export const breakpoints = {
  xs: '320px',
  sm: '480px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// Opacity scale
export const opacity = {
  0: '0',
  5: '0.05',
  10: '0.1',
  20: '0.2',
  25: '0.25',
  30: '0.3',
  40: '0.4',
  50: '0.5',
  60: '0.6',
  70: '0.7',
  75: '0.75',
  80: '0.8',
  90: '0.9',
  95: '0.95',
  100: '1',
} as const;

// Z-index scale
export const zIndex = {
  auto: 'auto',
  hide: '-1',
  base: '0',
  docked: '10',
  dropdown: '1000',
  sticky: '1100',
  fixed: '1200',
  modalBackdrop: '1300',
  modal: '1400',
  popover: '1500',
  skipLink: '1600',
  toast: '1700',
  tooltip: '1800',
} as const;

// Layout constants
export const layout = {
  navHeight: '64px',
  containerMaxWidth: '1280px',
  sidebarWidth: '256px',
  cardBorderRadius: '12px',
  hexagonClipPath: 'polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)',
} as const;

// Animation keyframes
export const keyframes = {
  pulse: {
    '0%, 100%': { opacity: 0.2 },
    '50%': { opacity: 0.4 },
  },
  twinkle: {
    '0%, 100%': { opacity: 0.6 },
    '50%': { opacity: 1 },
  },
  shimmer: {
    '0%, 100%': { opacity: 0.5 },
    '50%': { opacity: 1 },
  },
  scanline: {
    '0%': { transform: 'translateY(0)' },
    '100%': { transform: 'translateY(400px)' },
  },
  slideIn: {
    from: { transform: 'translateX(-100%)' },
    to: { transform: 'translateX(0)' },
  },
  fadeIn: {
    from: { opacity: 0 },
    to: { opacity: 1 },
  },
} as const;

// Preset combinations for common patterns
export const presets = {
  // Card styles
  card: {
    base: {
      bg: colors.background.card,
      border: '2px solid',
      borderColor: colors.border.medium,
      borderRadius: radii.lg,
      transition: `all ${transitions.base} ${transitions.easing.easeInOut}`,
    },
    hover: {
      transform: 'translateY(-4px)',
      borderColor: colors.border.brand,
      boxShadow: shadows.hoverElevation,
    },
  },

  // Button styles
  button: {
    base: {
      fontWeight: typography.fontWeight.bold,
      borderRadius: radii.md,
      textTransform: 'uppercase',
      letterSpacing: typography.letterSpacing.sm,
      transition: `all ${transitions.base} ${transitions.easing.easeInOut}`,
    },
    primary: {
      bg: colors.brand[500],
      color: '#1A1A1A',
      _hover: {
        bg: colors.brand[400],
        transform: 'translateY(-2px)',
        boxShadow: shadows.brandGlow,
      },
      _active: {
        bg: colors.brand[600],
        transform: 'translateY(0)',
      },
    },
    accent: {
      bg: colors.accent[500],
      color: '#1A1A1A',
      _hover: {
        bg: colors.accent[400],
        transform: 'translateY(-2px)',
        boxShadow: shadows.accentGlow,
      },
      _active: {
        bg: colors.accent[600],
        transform: 'translateY(0)',
      },
    },
  },

  // Text shadow for tactical look
  textShadow: {
    glow: `0 0 40px rgba(0, 212, 255, 0.6)`,
    glowSubtle: `0 0 20px rgba(0, 212, 255, 0.3)`,
    accentGlow: `0 0 20px rgba(255, 179, 0, 0.3)`,
  },

  // Gradient overlays
  gradient: {
    brandGradient: 'linear-gradient(45deg, transparent, rgba(0, 212, 255, 0.3), transparent)',
    accentGradient: 'linear-gradient(45deg, transparent, rgba(255, 179, 0, 0.3), transparent)',
    commandGradient: 'linear-gradient(135deg, transparent 40%, rgba(0, 212, 255, 0.4) 100%)',
  },

  // Corner bracket styling
  cornerBracket: {
    size: '16px',
    width: '2px',
    color: colors.brand[300],
  },
} as const;

// Export type for theme extension
export type ColorTokens = typeof colors;
export type SpacingTokens = typeof spacing;
export type RadiiTokens = typeof radii;
export type ShadowTokens = typeof shadows;
export type TypographyTokens = typeof typography;
export type TransitionTokens = typeof transitions;
