/**
 * FriendlyStat Component
 * Replaces HexagonalStat with a comic-book inspired, friendly design
 * Uses rounded cards with bold borders instead of hexagons
 */
import React from 'react';
import { Box, VStack, Text, useColorModeValue } from '@chakra-ui/react';

interface FriendlyStatProps {
  label: string;
  value: string | number;
  subtext?: string;
  color?: string;
  emoji?: string;
  size?: 'sm' | 'md' | 'lg';
}

const FriendlyStat: React.FC<FriendlyStatProps> = ({
  label,
  value,
  subtext,
  color = 'brand.500',
  emoji,
  size = 'md',
}) => {
  const bgColor = useColorModeValue('white', 'space.800');
  const borderColor = useColorModeValue('gray.800', 'space.900');
  
  const sizes = {
    sm: { width: '100px', height: '100px', valueSize: '2xl', labelSize: 'xs' },
    md: { width: '140px', height: '140px', valueSize: '4xl', labelSize: 'sm' },
    lg: { width: '180px', height: '180px', valueSize: '5xl', labelSize: 'md' },
  };
  
  const sizeConfig = sizes[size];

  return (
    <Box position="relative" width={sizeConfig.width} mx="auto">
      {/* Main card - rounded rectangle with comic border */}
      <Box
        bg={bgColor}
        borderRadius="xl"
        border="3px solid"
        borderColor={borderColor}
        boxShadow="4px 4px 0 var(--chakra-colors-space-900)"
        p={4}
        transition="all 0.25s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
        _hover={{
          transform: 'translateY(-4px) rotate(1deg)',
          boxShadow: '6px 6px 0 var(--chakra-colors-space-900)',
        }}
        position="relative"
        overflow="hidden"
      >
        {/* Subtle color accent at top */}
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          height="4px"
          bg={color}
          borderTopRadius="lg"
        />
        
        {/* Content */}
        <VStack spacing={1} textAlign="center" pt={2}>
          {/* Optional emoji */}
          {emoji && (
            <Text fontSize="2xl" lineHeight="1">
              {emoji}
            </Text>
          )}
          
          {/* Label */}
          <Text
            fontSize={sizeConfig.labelSize}
            fontWeight="bold"
            fontFamily="heading"
            color="gray.500"
            textTransform="uppercase"
            letterSpacing="wide"
          >
            {label}
          </Text>
          
          {/* Value - big chunky number */}
          <Text
            fontSize={sizeConfig.valueSize}
            fontWeight="black"
            fontFamily="heading"
            color={color}
            lineHeight="1"
            textShadow="2px 2px 0 var(--chakra-colors-space-900)"
          >
            {value}
          </Text>
          
          {/* Subtext */}
          {subtext && (
            <Text 
              fontSize="xs" 
              color="gray.500"
              fontFamily="body"
            >
              {subtext}
            </Text>
          )}
        </VStack>
      </Box>
    </Box>
  );
};

export default FriendlyStat;
