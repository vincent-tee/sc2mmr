/**
 * Chakra UI Theme Configuration
 * Gaming-inspired dark mode with blue/cyan primary and orange/gold accent
 */
import { extendTheme } from '@chakra-ui/react';

const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    brand: {
      50: '#E6F7FF',
      100: '#BAE7FF',
      200: '#91D5FF',
      300: '#69C0FF',
      400: '#40A9FF',
      500: '#1890FF', // Primary blue
      600: '#096DD9',
      700: '#0050B3',
      800: '#003A8C',
      900: '#002766',
    },
    accent: {
      50: '#FFF7E6',
      100: '#FFE7BA',
      200: '#FFD591',
      300: '#FFC069',
      400: '#FFA940',
      500: '#FA8C16', // Accent orange
      600: '#D46B08',
      700: '#AD4E00',
      800: '#873800',
      900: '#612500',
    },
  },
  fonts: {
    heading: `'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`,
    body: `'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`,
  },
  styles: {
    global: (props) => ({
      body: {
        bg: props.colorMode === 'dark' ? 'gray.900' : 'gray.50',
        color: props.colorMode === 'dark' ? 'gray.100' : 'gray.900',
      },
    }),
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: 'bold',
        borderRadius: 'md',
      },
      variants: {
        solid: (props) => ({
          bg: props.colorScheme === 'brand' ? 'brand.500' : undefined,
          color: 'white',
          _hover: {
            bg: props.colorScheme === 'brand' ? 'brand.600' : undefined,
            transform: 'translateY(-2px)',
            boxShadow: 'lg',
          },
          _active: {
            transform: 'translateY(0)',
          },
          transition: 'all 0.2s',
        }),
        primary: {
          bg: 'brand.500',
          color: 'white',
          _hover: {
            bg: 'brand.600',
            transform: 'translateY(-2px)',
            boxShadow: 'lg',
          },
          _active: {
            bg: 'brand.700',
            transform: 'translateY(0)',
          },
          transition: 'all 0.2s',
        },
        accent: {
          bg: 'accent.500',
          color: 'white',
          _hover: {
            bg: 'accent.600',
            transform: 'translateY(-2px)',
            boxShadow: 'lg',
          },
          _active: {
            bg: 'accent.700',
            transform: 'translateY(0)',
          },
          transition: 'all 0.2s',
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
          _hover: {
            boxShadow: 'xl',
            transform: 'translateY(-2px)',
          },
        },
      }),
    },
    Badge: {
      variants: {
        'mmr-high': {
          bg: 'green.500',
          color: 'white',
        },
        'mmr-medium': {
          bg: 'yellow.500',
          color: 'gray.900',
        },
        'mmr-low': {
          bg: 'orange.500',
          color: 'white',
        },
        'race-terran': {
          bg: 'blue.500',
          color: 'white',
        },
        'race-protoss': {
          bg: 'yellow.500',
          color: 'gray.900',
        },
        'race-zerg': {
          bg: 'purple.500',
          color: 'white',
        },
      },
    },
  },
  shadows: {
    outline: '0 0 0 3px rgba(24, 144, 255, 0.6)',
  },
});

export default theme;
