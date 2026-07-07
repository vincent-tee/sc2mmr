/**
 * TacticalCard Component
 * Friend Squad edition - Warm, personable, comic-book inspired
 */
import React, { ReactNode, useCallback, KeyboardEvent } from 'react';
import { Box, BoxProps, useColorModeValue } from '@chakra-ui/react';
import { shadows, transitions } from '../theme/tokens';

type TacticalCardVariant = 'default' | 'angled' | 'command';

interface TacticalCardProps extends Omit<BoxProps, 'onClick'> {
  children: ReactNode;
  glowColor?: string;
  onClick?: () => void;
  variant?: TacticalCardVariant;
}

const TacticalCard: React.FC<TacticalCardProps> = ({
  children,
  glowColor = 'brand.500',
  onClick,
  variant = 'default',
  ...props
}) => {
  const bgColor = useColorModeValue('white', 'space.800');
  const borderColor = useColorModeValue('space.900', 'space.900');
  const hoverBorderColor = useColorModeValue('brand.500', 'brand.400');

  // Handle keyboard navigation for accessibility
  const handleKeyDown = useCallback((event: KeyboardEvent<HTMLDivElement>) => {
    if (onClick && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      onClick();
    }
  }, [onClick]);

  return (
    <Box
      bg={bgColor}
      p={6}
      position="relative"
      cursor={onClick ? 'pointer' : 'default'}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : undefined}
      aria-label={onClick ? 'Interactive card' : undefined}
      transition={`all ${transitions.base} ${transitions.easing.bounce}`}
      border="3px solid"
      borderColor={borderColor}
      borderRadius="2xl"
      boxShadow={shadows.comic}
      overflow="visible"
      _hover={onClick ? {
        transform: 'translateY(-4px) rotate(0.5deg)',
        borderColor: hoverBorderColor,
        boxShadow: shadows.comicHover,
      } : {}}
      _focus={onClick ? {
        outline: 'none',
        boxShadow: '0 0 0 3px rgba(255, 107, 53, 0.5)',
        borderColor: hoverBorderColor,
      } : {}}
      {...props}
    >
      <Box position="relative" zIndex={1}>
        {children}
      </Box>
    </Box>
  );
};

export default React.memo(TacticalCard);
