/**
 * RankBadge Component
 * Displays a visually distinct rank badge based on MMR value
 * Supports various sizes and tooltip with rank tier information
 */
import React from 'react';
import { Badge, Tooltip, HStack, Text, Box } from '@chakra-ui/react';
import { getRankFromMMR, getRankBadgeProps, getRankTierDescription } from '../utils/ranks';
import { formatMMR } from '../utils/formatting';

interface RankBadgeProps {
  /** Player's MMR value */
  mmr: number;
  /** Badge size variant */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** Show MMR value next to rank */
  showMMR?: boolean;
  /** Show rank icon */
  showIcon?: boolean;
  /** Custom className */
  className?: string;
}

const RankBadge: React.FC<RankBadgeProps> = ({
  mmr,
  size = 'md',
  showMMR = false,
  showIcon = true,
  className,
}) => {
  const rankInfo = getRankFromMMR(mmr);
  const badgeProps = getRankBadgeProps(mmr);
  const tierDescription = getRankTierDescription(mmr);

  // Size configuration
  const sizeConfig = {
    xs: { fontSize: 'xs', px: 2, py: 0.5 },
    sm: { fontSize: 'sm', px: 2.5, py: 1 },
    md: { fontSize: 'md', px: 3, py: 1 },
    lg: { fontSize: 'lg', px: 4, py: 1.5 },
  };

  const currentSize = sizeConfig[size];

  return (
    <Tooltip
      label={
        <Box>
          <Text fontWeight="bold">{tierDescription}</Text>
          {showMMR && <Text fontSize="xs" opacity={0.9}>MMR: {formatMMR(mmr)}</Text>}
        </Box>
      }
      fontSize="sm"
      hasArrow
      placement="top"
    >
      <Badge
        {...badgeProps}
        {...currentSize}
        borderRadius="md"
        cursor="help"
        transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
        _hover={{
          transform: 'translateY(-2px)',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
        }}
        className={className}
      >
        <HStack spacing={1} height="100%">
          <Text whiteSpace="nowrap">
            {rankInfo.name === 'Grandmaster' ? 'GM' : rankInfo.name}
          </Text>
          {showIcon && rankInfo.icon && <Text>{rankInfo.icon}</Text>}
          {showMMR && <Text fontWeight="extrabold">{formatMMR(mmr)}</Text>}
        </HStack>
      </Badge>
    </Tooltip>
  );
};

export default RankBadge;
