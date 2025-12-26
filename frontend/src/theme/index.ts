/**
 * Chakra UI Theme Configuration
 * StarCraft-inspired gamer aesthetic with tactical UI elements
 */
import { extendTheme, type ThemeConfig, type StyleFunctionProps } from '@chakra-ui/react';

const config: ThemeConfig = {
  initialColorMode: 'dark',
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  colors: {
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
    // Warm grays & dark warm tones (background)
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
    // Race-specific colors (unchanged - canonical SC2 colors)
    terran: {
      500: '#0080FF',
      600: '#0066CC',
      700: '#004D99',
    },
    protoss: {
      500: '#FFD700',
      600: '#CCAC00',
      700: '#998100',
    },
    zerg: {
      500: '#9C27B0',
      600: '#7D1F8D',
      700: '#5E176A',
    },
  },
  fonts: {
    heading: `'Rajdhani', 'Orbitron', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`,
    body: `'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`,
  },
  styles: {
    global: (props: StyleFunctionProps) => ({
      '@keyframes twinkle': {
        '0%, 100%': { opacity: 0.6 },
        '50%': { opacity: 1 },
      },
      body: {
        bg: props.colorMode === 'dark' ? 'space.900' : 'gray.50',
        color: props.colorMode === 'dark' ? 'gray.100' : 'gray.900',
        // Warm starfield effect with orange/gold tones
        position: 'relative',
        '&::before': {
          content: '""',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: 'radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.4), rgba(0,0,0,0)), radial-gradient(2px 2px at 60px 70px, rgba(255,255,255,0.3), rgba(0,0,0,0)), radial-gradient(1px 1px at 50px 50px, rgba(255,255,255,0.5), rgba(0,0,0,0)), radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.3), rgba(0,0,0,0)), radial-gradient(2px 2px at 90px 10px, rgba(255,255,255,0.4), rgba(0,0,0,0)), radial-gradient(1px 1px at 10px 100px, rgba(255,140,26,0.2), rgba(0,0,0,0)), radial-gradient(1px 1px at 180px 20px, rgba(245,158,11,0.15), rgba(0,0,0,0)), radial-gradient(2px 2px at 140px 140px, rgba(239,68,68,0.1), rgba(0,0,0,0))',
          backgroundSize: '200px 200px',
          backgroundRepeat: 'repeat',
          opacity: props.colorMode === 'dark' ? 0.8 : 0,
          pointerEvents: 'none',
          zIndex: 0,
          animation: 'twinkle 3s ease-in-out infinite',
        },
        // Subtle warm scanline effect
        '&::after': {
          content: '""',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'repeating-linear-gradient(0deg, rgba(255, 140, 26, 0.02), rgba(255, 140, 26, 0.02) 1px, transparent 1px, transparent 2px)',
          opacity: props.colorMode === 'dark' ? 0.5 : 0,
          pointerEvents: 'none',
          zIndex: 0,
        },
      },
    }),
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: 'bold',
        borderRadius: 'md',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
      },
      variants: {
        solid: (props: StyleFunctionProps) => ({
          bg: props.colorScheme === 'brand' ? 'brand.500' : undefined,
          color: props.colorScheme === 'brand' ? 'gray.900' : 'white',
          _hover: {
            bg: props.colorScheme === 'brand' ? 'brand.400' : undefined,
            transform: 'translateY(-2px)',
            boxShadow: props.colorScheme === 'brand'
              ? '0 4px 14px 0 rgba(255, 140, 26, 0.39)'
              : 'lg',
          },
          _active: {
            transform: 'translateY(0)',
          },
          transition: 'all 0.2s',
        }),
        primary: {
          bg: 'brand.500',
          color: 'gray.900',
          _hover: {
            bg: 'brand.400',
            transform: 'translateY(-2px)',
            boxShadow: '0 4px 14px 0 rgba(255, 140, 26, 0.39)',
          },
          _active: {
            bg: 'brand.600',
            transform: 'translateY(0)',
          },
          transition: 'all 0.2s',
        },
        accent: {
          bg: 'accent.500',
          color: 'white',
          _hover: {
            bg: 'accent.400',
            transform: 'translateY(-2px)',
            boxShadow: '0 4px 14px 0 rgba(239, 68, 68, 0.39)',
          },
          _active: {
            bg: 'accent.600',
            transform: 'translateY(0)',
          },
          transition: 'all 0.2s',
        },
        ghost: {
          color: 'gray.300',
          _hover: {
            bg: 'whiteAlpha.100',
            color: 'brand.300',
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
          boxShadow: 'md',
          transition: 'all 0.2s',
          border: '1px solid',
          borderColor: props.colorMode === 'dark' ? 'whiteAlpha.100' : 'gray.200',
          _hover: {
            boxShadow: props.colorMode === 'dark'
              ? '0 0 20px rgba(255, 140, 26, 0.2)'
              : 'xl',
            transform: 'translateY(-2px)',
            borderColor: props.colorMode === 'dark' ? 'brand.500' : 'gray.300',
          },
        },
      }),
    },
    Badge: {
      variants: {
        'mmr-high': {
          bg: 'shield.500',
          color: 'gray.900',
          fontWeight: 'bold',
        },
        'mmr-medium': {
          bg: 'accent.500',
          color: 'gray.900',
          fontWeight: 'bold',
        },
        'mmr-low': {
          bg: 'orange.500',
          color: 'white',
          fontWeight: 'bold',
        },
        'race-terran': {
          bg: 'terran.500',
          color: 'white',
          fontWeight: 'bold',
        },
        'race-protoss': {
          bg: 'protoss.500',
          color: 'gray.900',
          fontWeight: 'bold',
        },
        'race-zerg': {
          bg: 'zerg.500',
          color: 'white',
          fontWeight: 'bold',
        },
        'race-random': {
          bg: 'gray.500',
          color: 'white',
          fontWeight: 'bold',
        },
      },
    },
  },
  shadows: {
    outline: '0 0 0 3px rgba(255, 140, 26, 0.6)',
    brandGlow: '0 0 20px rgba(255, 140, 26, 0.4)',
    accentGlow: '0 0 20px rgba(239, 68, 68, 0.4)',
    shieldGlow: '0 0 20px rgba(245, 158, 11, 0.4)',
  },
});

export default theme;
