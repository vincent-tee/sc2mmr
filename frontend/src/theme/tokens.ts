/**
 * Design Tokens for SC2 MMR Tracker
 * "Friend Squad" Edition - Warm, Personable, Comic-Book Inspired
 * Philosophy: Cozy gaming cafe, not sterile command center
 */

// Color palette - Friend Squad warm comic-book theme
export const colors = {
  // Brand/Primary palette - Sunset Orange (warm, inviting)
  brand: {
    50: '#FFF5F0',
    100: '#FFE4D6',
    200: '#FFCBB3',
    300: '#FFAB85',
    400: '#FF8C5A',
    500: '#FF6B35', // Sunset Orange - Main CTA
    600: '#E85A2A',
    700: '#CC4A22',
    800: '#A33D1C',
    900: '#7A2E15',
  },

  // Accent palette - Friendly Teal (complementary, fresh)
  accent: {
    50: '#E6FAF8',
    100: '#C2F2ED',
    200: '#9AE8E0',
    300: '#7EDCD6',
    400: '#66D4CC',
    500: '#4ECDC4', // Friendly Teal - Accents
    600: '#3DBDB4',
    700: '#2EA39B',
    800: '#1F8A82',
    900: '#106B65',
  },

  // Gold/Bronze (success/positive & achievements)
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

  // Cozy dark backgrounds (warm purple-brown, not cold black)
  space: {
    50: '#F5F3F7',
    100: '#E8E4ED',
    200: '#D4CDE0',
    300: '#B5AAC7',
    400: '#9286A8',
    500: '#6B5B7A',
    600: '#4A3D5C',
    700: '#2F2A40', // Elevated surface
    800: '#252136', // Card background
    900: '#1A1625', // Deep background (warm purple)
  },

  // StarCraft 2 race colors - FRIENDLIER versions (softer, warmer)
  race: {
    terran: {
      50: '#EBF4FB',
      100: '#D1E6F6',
      200: '#A3CEF0',
      300: '#89B8E5',
      400: '#6FA6DB',
      500: '#5B9BD5', // Soft Sky Blue (friendlier)
      600: '#4A8AC4',
      700: '#3A7BBD',
      800: '#2A5A8A',
      900: '#1A3A5A',
    },
    protoss: {
      50: '#FFFEF5',
      100: '#FFF9E0',
      200: '#FFF0B3',
      300: '#FFE566',
      400: '#FFDF4D',
      500: '#FFD93D', // Warm Butter Gold (friendlier)
      600: '#E5C235',
      700: '#CCAC2D',
      800: '#998122',
      900: '#665617',
    },
    zerg: {
      50: '#FAF0FF',
      100: '#F2E0FF',
      200: '#E5C2FF',
      300: '#D9A3FF',
      400: '#CC85FF',
      500: '#C77DFF', // Soft Lavender (friendlier)
      600: '#B366E6',
      700: '#A855F7',
      800: '#8B3ECF',
      900: '#6B2FA8',
    },
    random: {
      50: '#F8FAFC',
      100: '#F1F5F9',
      200: '#E2E8F0',
      300: '#CBD5E1',
      400: '#94A3B8', // Warm Slate (friendlier)
      500: '#64748B',
      600: '#475569',
      700: '#334155',
      800: '#1E293B',
      900: '#0F172A',
    },
  },

  // Status/semantic colors (fun, not harsh)
  status: {
    win: '#4ADE80', // Victory Green (softer)
    loss: '#F87171', // Defeat Red (not harsh)
    draw: '#FBBF24', // Draw Gold
    neutral: '#94A3B8',
    hotStreak: '#FF6B35', // On Fire!
    coldStreak: '#60A5FA', // Ice Cold
    rivalry: '#F472B6', // Rivalry Pink
  },

  // Background colors (cozy, warm)
  background: {
    deep: '#1A1625', // Main background (warm purple)
    card: '#252136', // Card surfaces
    cardHover: '#2F2A40', // Elevated surface
    elevated: '#2F2A40', // Modals, dropdowns
    overlay: 'rgba(26, 22, 37, 0.9)', // Modal overlay
    selected: 'rgba(78, 205, 196, 0.2)', // Teal selection
  },

  // Text colors (warm, readable)
  text: {
    primary: '#F8FAFC',
    secondary: '#CBD5E1',
    disabled: '#64748B',
    muted: '#475569',
    accent: '#4ECDC4', // Teal accent text
  },

  // Border colors (comic-book style)
  border: {
    light: 'rgba(255, 255, 255, 0.1)',
    medium: 'rgba(255, 107, 53, 0.3)', // Orange tint
    heavy: '#1A1625', // Bold comic border
    brand: '#FF6B35', // Orange brand
    accent: '#4ECDC4', // Teal accent
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

// Shadow definitions - Comic-book style (hard offset shadows, not glows)
export const shadows = {
  none: 'none',
  sm: '2px 2px 0 rgba(26, 22, 37, 0.3)',
  md: '4px 4px 0 rgba(26, 22, 37, 0.4)',
  lg: '6px 6px 0 rgba(26, 22, 37, 0.5)',
  xl: '8px 8px 0 rgba(26, 22, 37, 0.6)',
  // Comic-book card shadows (hard offset, not soft glow)
  comic: '4px 4px 0 #1A1625',
  comicHover: '6px 6px 0 #1A1625',
  comicLarge: '8px 8px 0 #1A1625',
  // Subtle glows for special states (not tactical neon)
  brandGlow: '0 4px 14px rgba(255, 107, 53, 0.3)',
  brandGlowSubtle: '0 2px 8px rgba(255, 107, 53, 0.2)',
  accentGlow: '0 4px 14px rgba(78, 205, 196, 0.3)',
  accentGlowSubtle: '0 2px 8px rgba(78, 205, 196, 0.2)',
  shieldGlow: '0 4px 14px rgba(245, 158, 11, 0.3)',
  // Fire effect for hot streaks
  fireGlow: '0 0 15px rgba(255, 107, 53, 0.5), 0 0 30px rgba(255, 107, 53, 0.3)',
  // Ice effect for cold streaks
  iceGlow: '0 0 15px rgba(96, 165, 250, 0.5), 0 0 30px rgba(96, 165, 250, 0.3)',
  // Elevation for modals/dropdowns
  elevation: '0 10px 40px rgba(0, 0, 0, 0.3)',
  hoverElevation: '0 12px 28px rgba(255, 107, 53, 0.2)',
} as const;

// Typography scale - Friendly Modern (Nunito + Quicksand)
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
    '5xl': '48px', // Hero titles
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
    heading: "'Bricolage Grotesque', 'Nunito', -apple-system, BlinkMacSystemFont, sans-serif",
    body: "'Nunito', -apple-system, BlinkMacSystemFont, sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', monospace",
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
    tighter: '-0.02em',
    tight: '-0.01em',
    none: '0',
    wide: '0.02em',
    wider: '0.05em',
    widest: '0.1em',
  },
} as const;

// Transition/animation timing - Medium Playful (bouncy but not excessive)
export const transitions = {
  fast: '150ms',
  base: '250ms',
  slow: '350ms',
  slowest: '500ms',
  easing: {
    // Smooth easing
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    // Bouncy easing (medium playful)
    bounce: 'cubic-bezier(0.68, -0.35, 0.265, 1.35)',
    bouncier: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    // Spring easing
    spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
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

// Animation keyframes - Friend Squad style (bouncy, playful)
export const keyframes = {
  // Bouncy entrance
  bounceIn: {
    '0%': { transform: 'scale(0)', opacity: 0 },
    '50%': { transform: 'scale(1.08)' },
    '70%': { transform: 'scale(0.95)' },
    '100%': { transform: 'scale(1)', opacity: 1 },
  },
  // Subtle wobble on hover
  wiggle: {
    '0%, 100%': { transform: 'rotate(0deg)' },
    '25%': { transform: 'rotate(-2deg)' },
    '75%': { transform: 'rotate(2deg)' },
  },
  // Victory celebration
  celebrate: {
    '0%, 100%': { transform: 'rotate(0deg) scale(1)' },
    '25%': { transform: 'rotate(-5deg) scale(1.05)' },
    '75%': { transform: 'rotate(5deg) scale(1.05)' },
  },
  // Fire glow for hot streaks
  fireGlow: {
    '0%, 100%': { boxShadow: '0 0 8px rgba(255, 107, 53, 0.4)' },
    '50%': { boxShadow: '0 0 20px rgba(255, 107, 53, 0.6), 0 0 40px rgba(255, 107, 53, 0.3)' },
  },
  // Gentle pulse (softer than tactical)
  pulse: {
    '0%, 100%': { opacity: 0.8 },
    '50%': { opacity: 1 },
  },
  // Slide in from bottom
  slideUp: {
    from: { transform: 'translateY(20px)', opacity: 0 },
    to: { transform: 'translateY(0)', opacity: 1 },
  },
  // Fade in
  fadeIn: {
    from: { opacity: 0 },
    to: { opacity: 1 },
  },
  // Card hover lift
  lift: {
    from: { transform: 'translateY(0)' },
    to: { transform: 'translateY(-4px)' },
  },
} as const;

// Preset combinations for common patterns - Friend Squad style
export const presets = {
  // Card styles - Comic-book inspired
  card: {
    base: {
      bg: colors.background.card,
      border: '3px solid',
      borderColor: colors.border.heavy,
      borderRadius: radii.lg,
      boxShadow: shadows.comic,
      transition: `all ${transitions.base} ${transitions.easing.bounce}`,
    },
    hover: {
      transform: 'translateY(-4px) rotate(0.5deg)',
      boxShadow: shadows.comicHover,
    },
  },

  // Button styles - Friendly, chunky
  button: {
    base: {
      fontFamily: typography.fontFamily.heading,
      fontWeight: typography.fontWeight.bold,
      borderRadius: radii.lg,
      border: '3px solid',
      borderColor: colors.border.heavy,
      transition: `all ${transitions.base} ${transitions.easing.bounce}`,
    },
    primary: {
      bg: colors.brand[500],
      color: '#FFFFFF',
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
      color: '#1A1625',
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

  // Background - Subtle warm gradient
  background: {
    gradient: 'linear-gradient(135deg, #1A1625 0%, #252136 50%, #1F1A2E 100%)',
    gradientSubtle: 'linear-gradient(180deg, #1A1625 0%, #1F1A2E 100%)',
  },

  // Halftone pattern for comic effect
  halftone: {
    pattern: 'radial-gradient(circle, #1A1625 1px, transparent 1px)',
    size: '4px 4px',
    opacity: 0.15,
  },

  // Text styles
  textShadow: {
    comic: '2px 2px 0 #1A1625',
    comicLight: '1px 1px 0 rgba(26, 22, 37, 0.5)',
    glow: '0 0 20px rgba(255, 107, 53, 0.4)',
  },

  // Race mascot colors (for future mascot components)
  mascot: {
    terran: { primary: colors.race.terran[500], accent: colors.race.terran[300] },
    protoss: { primary: colors.race.protoss[500], accent: colors.race.protoss[300] },
    zerg: { primary: colors.race.zerg[500], accent: colors.race.zerg[300] },
    random: { primary: colors.race.random[400], accent: colors.race.random[200] },
  },
} as const;

// Export type for theme extension
export type ColorTokens = typeof colors;
export type SpacingTokens = typeof spacing;
export type RadiiTokens = typeof radii;
export type ShadowTokens = typeof shadows;
export type TypographyTokens = typeof typography;
export type TransitionTokens = typeof transitions;
