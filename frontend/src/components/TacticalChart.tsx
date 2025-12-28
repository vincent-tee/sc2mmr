/**
 * TacticalChart Component
 * A reusable wrapper for Recharts that provides a consistent Tactical design
 * and ensures ResponsiveContainer has a parent with explicit dimensions.
 */
import React, { ReactNode } from 'react';
import {
  Box,
  Heading,
  HStack,
  Icon,
  VStack,
  useColorModeValue,
  Alert,
  AlertIcon,
  Text,
  Flex,
} from '@chakra-ui/react';
import { IconType } from 'react-icons';
import { ResponsiveContainer } from 'recharts';
import TacticalCard from './TacticalCard';

interface TacticalChartProps {
  title: string;
  icon?: IconType;
  children: React.ReactElement;
  height?: string | number;
  subtitle?: string;
  glowColor?: string;
  variant?: 'default' | 'angled' | 'command';
  isNoData?: boolean;
  noDataMessage?: string;
}

const TacticalChart: React.FC<TacticalChartProps> = ({
  title,
  icon,
  children,
  height = '350px',
  subtitle,
  glowColor = 'brand.500',
  variant = 'default',
  isNoData = false,
  noDataMessage = "Insufficient data for analysis.",
}) => {
  const titleColor = useColorModeValue('gray.800', 'white');
  const subtitleColor = useColorModeValue('gray.600', 'gray.400');

  return (
    <TacticalCard variant={variant} glowColor={glowColor} h="full">
      <VStack align="stretch" spacing={4} h="full">
        {/* Chart Header */}
        <HStack justify="space-between" align="flex-start">
          <VStack align="start" spacing={0}>
            <HStack>
              {icon && <Icon as={icon} color={glowColor} boxSize={5} />}
              <Heading size="md" fontFamily="heading" color={titleColor}>
                {title}
              </Heading>
            </HStack>
            {subtitle && (
              <Box fontSize="xs" color={subtitleColor} fontFamily="heading" mt={1}>
                {subtitle}
              </Box>
            )}
          </VStack>
        </HStack>

        {/* Chart Container - Fixed height to solve ResponsiveContainer issues */}
        <Box 
          height={height} 
          width="100%" 
          position="relative"
          minH={height}
        >
          {isNoData ? (
            <Flex height="100%" align="center" justify="center" p={4}>
              <Alert 
                status="info" 
                variant="subtle" 
                bg="transparent" 
                borderColor={`${glowColor.split('.')[0]}.800`} 
                borderWidth={1}
              >
                <AlertIcon color={glowColor} />
                <Text color="gray.400" fontSize="sm">{noDataMessage}</Text>
              </Alert>
            </Flex>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              {children}
            </ResponsiveContainer>
          )}
        </Box>
      </VStack>
    </TacticalCard>
  );
};

export default TacticalChart;
