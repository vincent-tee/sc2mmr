/**
 * Chakra UI Theme Configuration
 * "Friend Squad" Edition - Warm, Personable, Comic-Book Inspired
 * Philosophy: Cozy gaming cafe, not sterile command center
 */
import { extendTheme, type ThemeConfig, type StyleFunctionProps } from '@chakra-ui/react';

const config: ThemeConfig = {
  initialColorMode: 'dark',
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  colors: {
    // Brand/Primary palette - Sunset Orange
    brand: {
      50: '#FFF5F0',
      100: '#FFE4D6',
      200: '#FFCBB3',
      300: '#FFAB85',
      400: '#FF8C5A',
      500: '#FF6B35', // Sunset Orange - Main
      600: '#E85A2A',
      700: '#CC4A22',
      800: '#A33D1C',
      900: '#7A2E15',
    },
    // Accent palette - Friendly Teal
    accent: {
      50: '#E6FAF8',
      100: '#C2F2ED',
      200: '#9AE8E0',
      300: '#7EDCD6',
      400: '#66D4CC',
      500: '#4ECDC4', // Friendly Teal
      600: '#3DBDB4',
      700: '#2EA39B',
      800: '#1F8A82',
      900: '#106B65',
    },
    // Gold/Bronze (achievements)
    shield: {
      50: '#FFFBEB',
      100: '#FEF3C7',
      200: '#FDE68A',
      300: '#FCD34D',
      400: '#FBBF24',
      500: '#F59E0B',
      600: '#D97706',
      700: '#B45309',
      800: '#92400E',
      900: '#78350F',
    },
    // Cozy dark backgrounds (warm purple)
    space: {
      50: '#F5F3F7',
      100: '#E8E4ED',
      200: '#D4CDE0',
      300: '#B5AAC7',
      400: '#9286A8',
      500: '#6B5B7A',
      600: '#4A3D5C',
      700: '#2F2A40',
      800: '#252136',
      900: '#1A1625',
    },
    // Race-specific colors - FRIENDLIER versions
    terran: {
      300: '#89B8E5',
      400: '#6FA6DB',
      500: '#5B9BD5', // Soft Sky Blue
      600: '#4A8AC4',
      700: '#3A7BBD',
    },
    protoss: {
      300: '#FFE566',
      400: '#FFDF4D',
      500: '#FFD93D', // Warm Butter Gold
      600: '#E5C235',
      700: '#CCAC2D',
    },
    zerg: {
      300: '#D9A3FF',
      400: '#CC85FF',
      500: '#C77DFF', // Soft Lavender
      600: '#B366E6',
      700: '#A855F7',
    },
    random: {
      300: '#CBD5E1',
      400: '#94A3B8', // Warm Slate
      500: '#64748B',
      600: '#475569',
      700: '#334155',
    },
  },
  fonts: {
    heading: `'Bricolage Grotesque', 'Nunito', -apple-system, BlinkMacSystemFont, 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif`,
    body: `'Nunito', -apple-system, BlinkMacSystemFont, 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif`,
    mono: `'JetBrains Mono', 'Fira Code', monospace`,
  },
  styles: {
    global: (props: StyleFunctionProps) => ({
      // Emoji font class
      '.emoji-font': {
        fontFamily: 'system-ui, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji", sans-serif',
      },
      // Bouncy animations
      '@keyframes bounceIn': {
        '0%': { transform: 'scale(0)', opacity: 0 },
        '50%': { transform: 'scale(1.08)' },
        '70%': { transform: 'scale(0.95)' },
        '100%': { transform: 'scale(1)', opacity: 1 },
      },
      '@keyframes wiggle': {
        '0%, 100%': { transform: 'rotate(0deg)' },
        '25%': { transform: 'rotate(-2deg)' },
        '75%': { transform: 'rotate(2deg)' },
      },
      '@keyframes fireGlow': {
        '0%, 100%': { boxShadow: '0 0 8px rgba(255, 107, 53, 0.4)' },
        '50%': { boxShadow: '0 0 20px rgba(255, 107, 53, 0.6), 0 0 40px rgba(255, 107, 53, 0.3)' },
      },
      '@keyframes pulse': {
        '0%, 100%': { opacity: 0.8 },
        '50%': { opacity: 1 },
      },
      body: {
        bg: props.colorMode === 'dark' ? 'space.900' : 'gray.50',
        color: props.colorMode === 'dark' ? 'gray.100' : 'gray.900',
        // Unified clubhouse backdrop: warm glow top-left, teal wash bottom-right,
        // faint dot grid for texture. Every page sits on this — no per-page tints.
        backgroundImage: props.colorMode === 'dark'
          ? `radial-gradient(ellipse 900px 500px at 12% -8%, rgba(255, 107, 53, 0.10), transparent),
             radial-gradient(ellipse 800px 500px at 95% 105%, rgba(78, 205, 196, 0.06), transparent),
             radial-gradient(circle, rgba(255, 255, 255, 0.025) 1px, transparent 1px)`
          : 'none',
        backgroundSize: props.colorMode === 'dark' ? '100% 100%, 100% 100%, 28px 28px' : 'auto',
        backgroundAttachment: 'fixed',
        minHeight: '100vh',
      },
      '::selection': {
        bg: 'rgba(255, 107, 53, 0.4)',
      },
    }),
  },
  components: {
    Button: {
      baseStyle: {
        fontFamily: 'heading',
        fontWeight: 'bold',
        borderRadius: 'lg',
        transition: 'all 0.25s cubic-bezier(0.68, -0.35, 0.265, 1.35)',
      },
      variants: {
        solid: (props: StyleFunctionProps) => ({
          bg: props.colorScheme === 'brand' ? 'brand.500' : undefined,
          color: props.colorScheme === 'brand' ? 'white' : 'white',
          border: '3px solid',
          borderColor: 'space.900',
          boxShadow: '3px 3px 0 var(--chakra-colors-space-900)',
          _hover: {
            bg: props.colorScheme === 'brand' ? 'brand.400' : undefined,
            transform: 'translateY(-2px)',
            boxShadow: '5px 5px 0 var(--chakra-colors-space-900)',
          },
          _active: {
            transform: 'translateY(0)',
            boxShadow: '2px 2px 0 var(--chakra-colors-space-900)',
          },
        }),
        primary: {
          bg: 'brand.500',
          color: 'white',
          border: '3px solid',
          borderColor: 'space.900',
          boxShadow: '3px 3px 0 var(--chakra-colors-space-900)',
          _hover: {
            bg: 'brand.400',
            transform: 'translateY(-2px)',
            boxShadow: '5px 5px 0 var(--chakra-colors-space-900)',
          },
          _active: {
            bg: 'brand.600',
            transform: 'translateY(0)',
            boxShadow: '2px 2px 0 var(--chakra-colors-space-900)',
          },
        },
        accent: {
          bg: 'accent.500',
          color: 'space.900',
          border: '3px solid',
          borderColor: 'space.900',
          boxShadow: '3px 3px 0 var(--chakra-colors-space-900)',
          _hover: {
            bg: 'accent.400',
            transform: 'translateY(-2px)',
            boxShadow: '5px 5px 0 var(--chakra-colors-space-900)',
          },
          _active: {
            bg: 'accent.600',
            transform: 'translateY(0)',
            boxShadow: '2px 2px 0 var(--chakra-colors-space-900)',
          },
        },
        ghost: {
          color: 'gray.300',
          _hover: {
            bg: 'whiteAlpha.100',
            color: 'brand.400',
          },
        },
      },
      defaultProps: {
        colorScheme: 'brand',
      },
    },
    Card: {
      baseStyle: (props: StyleFunctionProps) => ({
        container: {
          bg: props.colorMode === 'dark' ? 'space.800' : 'white',
          borderRadius: 'lg',
          border: '3px solid',
          borderColor: props.colorMode === 'dark' ? 'space.900' : 'gray.200',
          boxShadow: props.colorMode === 'dark' 
            ? '4px 4px 0 var(--chakra-colors-space-900)'
            : 'md',
          transition: 'all 0.25s cubic-bezier(0.68, -0.35, 0.265, 1.35)',
          _hover: {
            transform: 'translateY(-4px) rotate(0.5deg)',
            boxShadow: props.colorMode === 'dark'
              ? '6px 6px 0 var(--chakra-colors-space-900)'
              : 'xl',
          },
        },
      }),
    },
    Badge: {
      baseStyle: {
        borderRadius: 'md',
        fontFamily: 'heading',
        fontWeight: 'bold',
        border: '2px solid',
        borderColor: 'space.900',
      },
      variants: {
        'mmr-high': {
          bg: 'shield.500',
          color: 'space.900',
        },
        'mmr-medium': {
          bg: 'brand.500',
          color: 'white',
        },
        'mmr-low': {
          bg: 'orange.500',
          color: 'white',
        },
        'race-terran': {
          bg: 'terran.500',
          color: 'white',
        },
        'race-protoss': {
          bg: 'protoss.500',
          color: 'space.900',
        },
        'race-zerg': {
          bg: 'zerg.500',
          color: 'white',
        },
        'race-random': {
          bg: 'random.400',
          color: 'space.900',
        },
        // Fun status badges
        'hot-streak': {
          bg: 'brand.500',
          color: 'white',
          animation: 'fireGlow 2s ease-in-out infinite',
        },
        'cold-streak': {
          bg: 'blue.400',
          color: 'white',
        },
      },
    },
    Heading: {
      baseStyle: {
        fontFamily: 'heading',
        fontWeight: '800',
        letterSpacing: '-0.02em',
      },
    },
    Text: {
      baseStyle: {
        fontFamily: 'body',
      },
    },
  },
  shadows: {
    outline: '0 0 0 3px rgba(255, 107, 53, 0.5)',
    comic: '4px 4px 0 var(--chakra-colors-space-900)',
    comicHover: '6px 6px 0 var(--chakra-colors-space-900)',
    brandGlow: '0 4px 14px rgba(255, 107, 53, 0.3)',
    accentGlow: '0 4px 14px rgba(78, 205, 196, 0.3)',
    shieldGlow: '0 4px 14px rgba(245, 158, 11, 0.3)',
  },
  radii: {
    none: '0',
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    '2xl': '24px',
    full: '9999px',
  },
});

export default theme;
