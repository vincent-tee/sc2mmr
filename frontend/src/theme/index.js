/**
 * Chakra UI Theme Configuration
 * StarCraft-inspired gamer aesthetic with tactical UI elements
 */
import { extendTheme } from '@chakra-ui/react';

const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    // Tactical Blue (primary) - SC2 unit selection glow
    brand: {
      50: '#E6FBFF',
      100: '#B3F3FF',
      200: '#80EBFF',
      300: '#4DE3FF',
      400: '#1ADBFF',
      500: '#00D4FF', // Tactical cyan
      600: '#00A8CC',
      700: '#007D99',
      800: '#005266',
      900: '#002733',
    },
    // Vespene Gold (accent) - Resource gathering aesthetic
    accent: {
      50: '#FFF8E6',
      100: '#FFEAB3',
      200: '#FFDC80',
      300: '#FFCE4D',
      400: '#FFC01A',
      500: '#FFB300', // Vespene gold
      600: '#CC8F00',
      700: '#996B00',
      800: '#664700',
      900: '#332400',
    },
    // Shield Green (success) - Protoss shields
    shield: {
      50: '#E6FFF5',
      100: '#B3FFE0',
      200: '#80FFCB',
      300: '#4DFFB6',
      400: '#1AFFA1',
      500: '#00FF88',
      600: '#00CC6D',
      700: '#009952',
      800: '#006637',
      900: '#00331B',
    },
    // Deep Space (background) - Space aesthetic
    space: {
      50: '#E8EAEF',
      100: '#C1C5D1',
      200: '#9AA0B3',
      300: '#737B95',
      400: '#4C5677',
      500: '#252F5D',
      600: '#1D2549',
      700: '#151B35',
      800: '#0D1121',
      900: '#0A0E27', // Deep space blue-black
    },
    // Race-specific colors
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
    global: (props) => ({
      '@keyframes twinkle': {
        '0%, 100%': { opacity: 0.6 },
        '50%': { opacity: 1 },
      },
      body: {
        bg: props.colorMode === 'dark' ? 'space.900' : 'gray.50',
        color: props.colorMode === 'dark' ? 'gray.100' : 'gray.900',
        // Dramatic starfield effect
        position: 'relative',
        '&::before': {
          content: '""',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: 'radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.4), rgba(0,0,0,0)), radial-gradient(2px 2px at 60px 70px, rgba(255,255,255,0.3), rgba(0,0,0,0)), radial-gradient(1px 1px at 50px 50px, rgba(255,255,255,0.5), rgba(0,0,0,0)), radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.3), rgba(0,0,0,0)), radial-gradient(2px 2px at 90px 10px, rgba(255,255,255,0.4), rgba(0,0,0,0)), radial-gradient(1px 1px at 10px 100px, rgba(0,212,255,0.2), rgba(0,0,0,0)), radial-gradient(1px 1px at 180px 20px, rgba(0,212,255,0.15), rgba(0,0,0,0)), radial-gradient(2px 2px at 140px 140px, rgba(255,179,0,0.1), rgba(0,0,0,0))',
          backgroundSize: '200px 200px',
          backgroundRepeat: 'repeat',
          opacity: props.colorMode === 'dark' ? 0.8 : 0,
          pointerEvents: 'none',
          zIndex: 0,
          animation: 'twinkle 3s ease-in-out infinite',
        },
        // Subtle scanline effect
        '&::after': {
          content: '""',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'repeating-linear-gradient(0deg, rgba(0, 212, 255, 0.03), rgba(0, 212, 255, 0.03) 1px, transparent 1px, transparent 2px)',
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
        solid: (props) => ({
          bg: props.colorScheme === 'brand' ? 'brand.500' : undefined,
          color: props.colorScheme === 'brand' ? 'gray.900' : 'white',
          _hover: {
            bg: props.colorScheme === 'brand' ? 'brand.400' : undefined,
            transform: 'translateY(-2px)',
            boxShadow: props.colorScheme === 'brand'
              ? '0 4px 14px 0 rgba(0, 212, 255, 0.39)'
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
            boxShadow: '0 4px 14px 0 rgba(0, 212, 255, 0.39)',
          },
          _active: {
            bg: 'brand.600',
            transform: 'translateY(0)',
          },
          transition: 'all 0.2s',
        },
        accent: {
          bg: 'accent.500',
          color: 'gray.900',
          _hover: {
            bg: 'accent.400',
            transform: 'translateY(-2px)',
            boxShadow: '0 4px 14px 0 rgba(255, 179, 0, 0.39)',
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
      baseStyle: (props) => ({
        container: {
          bg: props.colorMode === 'dark' ? 'gray.800' : 'white',
          borderRadius: 'lg',
          boxShadow: 'md',
          transition: 'all 0.2s',
          border: '1px solid',
          borderColor: props.colorMode === 'dark' ? 'whiteAlpha.100' : 'gray.200',
          _hover: {
            boxShadow: props.colorMode === 'dark'
              ? '0 0 20px rgba(0, 212, 255, 0.2)'
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
    outline: '0 0 0 3px rgba(0, 212, 255, 0.6)',
  },
});

export default theme;
