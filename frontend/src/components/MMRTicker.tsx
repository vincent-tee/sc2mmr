/**
 * MMR Ticker Component
 * Horizontal scrolling ticker showing recent rating changes
 * Uses warm color scheme with shield (green) for gains and accent (red) for losses
 */
import React, { useMemo } from 'react';
import {
  Box,
  HStack,
  Text,
  Flex,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiTrendingUp, FiTrendingDown } from 'react-icons/fi';

interface MMRChange {
  playerName: string;
  change: number;
  timestamp: Date;
  id?: string;
}

interface MMRTickerProps {
  changes: MMRChange[];
  isLoading?: boolean;
}

const MMRTicker: React.FC<MMRTickerProps> = ({ changes }) => {
  // Style values
  const bgColor = useColorModeValue('white', 'rgba(13, 17, 33, 0.8)');
  const borderColor = useColorModeValue('gray.200', 'brand.500');
  const textColor = useColorModeValue('gray.700', 'gray.100');

  // Duplicate ticker content for seamless loop
  const doubledChanges = useMemo(() => {
    if (changes.length === 0) return [];
    return [...changes, ...changes];
  }, [changes]);

  // Format change display
  const formatChange = (change: number): string => {
    const sign = change > 0 ? '+' : '';
    return `${sign}${change}`;
  };

  // Get color based on positive/negative change
  const getChangeColor = (change: number) => {
    if (change > 0) {
      return {
        color: 'shield.400', // Gold/green for positive
        icon: FiTrendingUp,
      };
    }
    return {
      color: 'accent.400', // Red for negative
      icon: FiTrendingDown,
    };
  };

  // Handle empty state
  if (changes.length === 0) {
    return (
      <Box
        bg={bgColor}
        borderBottom="1px"
        borderColor={borderColor}
        px={4}
        py={2}
        display={{ base: 'none', md: 'block' }}
      >
        <Text fontSize="xs" color="gray.500" textAlign="center">
          Waiting for rating changes...
        </Text>
      </Box>
    );
  }

  return (
    <Box
      bg={bgColor}
      borderBottom="1px"
      borderColor={borderColor}
      overflow="hidden"
      display={{ base: 'none', md: 'block' }}
      py={2}
    >
      <Box
        position="relative"
        width="100%"
        maxW="100%"
        overflow="hidden"
      >
        {/* Gradient fade effect on left */}
        <Box
          position="absolute"
          left={0}
          top={0}
          bottom={0}
          width="60px"
          background="linear-gradient(to right, rgba(13, 17, 33, 0.95), transparent)"
          zIndex={10}
          pointerEvents="none"
        />

        {/* Gradient fade effect on right */}
        <Box
          position="absolute"
          right={0}
          top={0}
          bottom={0}
          width="60px"
          background="linear-gradient(to left, rgba(13, 17, 33, 0.95), transparent)"
          zIndex={10}
          pointerEvents="none"
        />

        {/* Scrolling ticker container */}
        <Flex
          sx={{
            animation: `mmrTickerScroll ${Math.max(8, changes.length * 0.8)}s linear infinite`,
            '@keyframes mmrTickerScroll': {
              '0%': {
                transform: 'translateX(0)',
              },
              '100%': {
                transform: `translateX(-50%)`,
              },
            },
          }}
          gap={6}
          px={4}
          whiteSpace="nowrap"
        >
          {doubledChanges.map((change, idx) => {
            const { color: changeColor, icon: Icon } = getChangeColor(change.change);
            const uniqueKey = `${change.id || `${change.playerName}-${idx}`}`;

            return (
              <HStack
                key={uniqueKey}
                spacing={1}
                flexShrink={0}
                px={2}
                py={1}
                borderRadius="md"
                bg={useColorModeValue('gray.100', 'space.700')}
                border="1px solid"
                borderColor={useColorModeValue('gray.200', 'space.600')}
                transition="all 0.2s"
                _hover={{
                  borderColor: changeColor,
                  boxShadow: `0 0 8px rgba(${
                    change.change > 0
                      ? '245, 158, 11, 0.3' // shield gold
                      : '239, 68, 68, 0.3' // accent red
                  })`,
                }}
              >
                {/* Change indicator icon */}
                <Icon
                  size={14}
                  color={`var(--chakra-colors-${changeColor})`}
                  style={{ flexShrink: 0 }}
                />

                {/* Player name */}
                <Text
                  fontSize="xs"
                  fontWeight="medium"
                  color={textColor}
                  fontFamily="heading"
                  minW="max-content"
                >
                  {change.playerName}
                </Text>

                {/* MMR change value */}
                <Text
                  fontSize="xs"
                  fontWeight="bold"
                  color={changeColor}
                  minW="max-content"
                  letterSpacing="tight"
                >
                  {formatChange(change.change)}
                </Text>
              </HStack>
            );
          })}
        </Flex>
      </Box>
    </Box>
  );
};

export default MMRTicker;
