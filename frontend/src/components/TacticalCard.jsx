/**
 * TacticalCard Component
 * Angular SC2-style card with corner clips and glows
 */
import { Box, useColorModeValue } from '@chakra-ui/react';

const TacticalCard = ({
  children,
  glowColor = 'brand.500',
  onClick,
  variant = 'default',
  ...props
}) => {
  const bgColor = useColorModeValue('white', 'rgba(26, 32, 44, 0.9)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.3)');

  const variants = {
    default: {
      clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%)',
    },
    angled: {
      clipPath: 'polygon(20px 0, 100% 0, 100% 100%, 0 100%, 0 20px)',
    },
    command: {
      clipPath: 'polygon(0 8px, 8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%)',
    },
  };

  return (
    <Box
      bg={bgColor}
      p={6}
      position="relative"
      cursor={onClick ? 'pointer' : 'default'}
      onClick={onClick}
      transition="all 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
      border="2px solid"
      borderColor={borderColor}
      overflow="hidden"
      {...variants[variant]}
      _hover={onClick ? {
        transform: 'translateY(-4px) scale(1.02)',
        borderColor: glowColor,
        boxShadow: `0 8px 30px rgba(0, 212, 255, 0.4), 0 0 20px ${glowColor}`,
        _before: {
          opacity: 1,
        },
      } : {}}
      _before={{
        content: '""',
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: `linear-gradient(135deg, transparent 40%, ${glowColor} 100%)`,
        opacity: 0,
        transition: 'opacity 0.3s',
        pointerEvents: 'none',
        mixBlendMode: 'soft-light',
      }}
      {...props}
    >
      {/* Animated scanline */}
      <Box
        position="absolute"
        top={0}
        left={0}
        right={0}
        height="2px"
        bg={glowColor}
        opacity={0.3}
        animation="scanline 3s linear infinite"
        sx={{
          '@keyframes scanline': {
            '0%': { transform: 'translateY(0)' },
            '100%': { transform: 'translateY(400px)' },
          },
        }}
      />

      {/* Corner decorations */}
      <Box
        position="absolute"
        top={2}
        left={2}
        width="20px"
        height="20px"
        borderTop="3px solid"
        borderLeft="3px solid"
        borderColor={glowColor}
        opacity={0.6}
      />
      <Box
        position="absolute"
        bottom={2}
        right={2}
        width="20px"
        height="20px"
        borderBottom="3px solid"
        borderRight="3px solid"
        borderColor={glowColor}
        opacity={0.6}
      />

      <Box position="relative" zIndex={1}>
        {children}
      </Box>
    </Box>
  );
};

export default TacticalCard;
