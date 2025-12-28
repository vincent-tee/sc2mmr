/**
 * MMR Notification Bar Component
 * Static notification showing the most recent significant rating change
 * Replaces scrolling ticker for better UX (less cognitive load)
 */
import React, { useMemo } from 'react';
import {
  Box,
  HStack,
  Text,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiTrendingUp, FiTrendingDown, FiActivity } from 'react-icons/fi';

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

const MMRTicker: React.FC<MMRTickerProps> = ({ changes, isLoading }) => {
  // Style values
  const bgColor = useColorModeValue('white', 'rgba(13, 17, 33, 0.9)');
  const borderColor = useColorModeValue('gray.200', 'brand.500');
  const textColor = useColorModeValue('gray.600', 'gray.300');
  const positiveColor = useColorModeValue('shield.600', 'shield.400');
  const negativeColor = useColorModeValue('accent.600', 'accent.400');

  // Find the most significant change (largest absolute value)
  const topChange = useMemo(() => {
    if (changes.length === 0) return null;
    return changes.reduce((max, current) =>
      Math.abs(current.change) > Math.abs(max.change) ? current : max
    , changes[0]);
  }, [changes]);

  // Format time ago
  const formatTimeAgo = (timestamp: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - timestamp.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  // Handle loading state
  if (isLoading) {
    return (
      <Box
        bg={bgColor}
        borderBottom="1px"
        borderColor={borderColor}
        px={4}
        py={2}
        display={{ base: 'none', md: 'block' }}
      >
        <HStack justify="center" spacing={2}>
          <Icon as={FiActivity} color="gray.500" />
          <Text fontSize="xs" color="gray.500">
            Loading activity...
          </Text>
        </HStack>
      </Box>
    );
  }

  // Handle empty state
  if (!topChange || changes.length === 0) {
    return (
      <Box
        bg={bgColor}
        borderBottom="1px"
        borderColor={borderColor}
        px={4}
        py={2}
        display={{ base: 'none', md: 'block' }}
      >
        <HStack justify="center" spacing={2}>
          <Icon as={FiActivity} color="gray.500" />
          <Text fontSize="xs" color="gray.500">
            Waiting for rating changes...
          </Text>
        </HStack>
      </Box>
    );
  }

  const isPositive = topChange.change > 0;
  const changeColor = isPositive ? positiveColor : negativeColor;
  const ChangeIcon = isPositive ? FiTrendingUp : FiTrendingDown;
  const changeSign = isPositive ? '+' : '';

  return (
    <Box
      bg={bgColor}
      borderBottom="1px"
      borderColor={borderColor}
      px={4}
      py={2}
      display={{ base: 'none', md: 'block' }}
      sx={{
        '@media (prefers-reduced-motion: reduce)': {
          animation: 'none !important',
        },
      }}
    >
      <HStack justify="space-between" maxW="container.xl" mx="auto">
        <HStack spacing={3}>
          <Icon
            as={ChangeIcon}
            color={changeColor}
            boxSize={4}
          />
          <Text fontSize="sm" color={textColor}>
            <Text as="span" fontWeight="bold" color="gray.100">
              {topChange.playerName}
            </Text>
            {' '}
            {isPositive ? 'gained' : 'lost'}
            {' '}
            <Text as="span" fontWeight="bold" color={changeColor}>
              {changeSign}{Math.abs(topChange.change)} MMR
            </Text>
          </Text>
        </HStack>
        <HStack spacing={4}>
          <Text fontSize="xs" color="gray.500">
            {formatTimeAgo(topChange.timestamp)}
          </Text>
          <Text fontSize="xs" color="gray.600">
            {changes.length} recent changes
          </Text>
        </HStack>
      </HStack>
    </Box>
  );
};

export default MMRTicker;
