/**
 * HexagonalStat Component
 * Hexagon-shaped stat display for tactical aesthetic
 */
import React from 'react';
import { Box, VStack, Text, useColorModeValue } from '@chakra-ui/react';

interface HexagonalStatProps {
  label: string;
  value: string | number;
  subtext?: string;
  color?: string;
}

const HexagonalStat: React.FC<HexagonalStatProps> = ({
  label,
  value,
  subtext,
  color = 'brand.500',
}) => {
  const bgColor = useColorModeValue('white', 'rgba(26, 32, 44, 0.9)');

  return (
    <Box position="relative" width="180px" height="200px" mx="auto">
      {/* Hexagon background */}
      <Box
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        width="160px"
        height="160px"
        bg={bgColor}
        clipPath="polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)"
        border="3px solid"
        borderColor={color}
        boxShadow={`0 0 30px ${color}40`}
        transition="all 0.3s"
        _hover={{
          transform: 'translate(-50%, -50%) scale(1.1) rotate(5deg)',
          boxShadow: `0 0 40px ${color}80`,
        }}
      />

      {/* Glow effect */}
      <Box
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        width="180px"
        height="180px"
        bg={color}
        clipPath="polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)"
        opacity={0.1}
        filter="blur(20px)"
        animation="pulse 2s ease-in-out infinite"
        sx={{
          '@keyframes pulse': {
            '0%, 100%': { opacity: 0.1, transform: 'translate(-50%, -50%) scale(1)' },
            '50%': { opacity: 0.2, transform: 'translate(-50%, -50%) scale(1.05)' },
          },
        }}
      />

      {/* Content */}
      <VStack
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        spacing={1}
        textAlign="center"
        zIndex={2}
      >
        <Text
          fontSize="xs"
          fontWeight="bold"
          textTransform="uppercase"
          letterSpacing="wider"
          color="gray.500"
        >
          {label}
        </Text>
        <Text
          fontSize="4xl"
          fontWeight="black"
          fontFamily="heading"
          color={color}
          textShadow={`0 0 20px ${color}60`}
          lineHeight="1"
        >
          {value}
        </Text>
        {subtext && (
          <Text fontSize="xs" color="gray.600">
            {subtext}
          </Text>
        )}
      </VStack>

      {/* Corner markers */}
      <Box
        position="absolute"
        top="20%"
        left="15%"
        width="6px"
        height="6px"
        bg={color}
        borderRadius="full"
        boxShadow={`0 0 8px ${color}`}
      />
      <Box
        position="absolute"
        top="20%"
        right="15%"
        width="6px"
        height="6px"
        bg={color}
        borderRadius="full"
        boxShadow={`0 0 8px ${color}`}
      />
      <Box
        position="absolute"
        bottom="20%"
        left="15%"
        width="6px"
        height="6px"
        bg={color}
        borderRadius="full"
        boxShadow={`0 0 8px ${color}`}
      />
      <Box
        position="absolute"
        bottom="20%"
        right="15%"
        width="6px"
        height="6px"
        bg={color}
        borderRadius="full"
        boxShadow={`0 0 8px ${color}`}
      />
    </Box>
  );
};

export default HexagonalStat;
