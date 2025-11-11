/**
 * PlayerCard Component
 * Displays player information with avatar, name, MMR, and race
 */
import {
  Box,
  Avatar,
  Text,
  Badge,
  VStack,
  HStack,
  useColorModeValue,
} from '@chakra-ui/react';
import { formatMMR, getInitials, getRaceColor, getMMRBadgeColor } from '../utils/formatting';

const PlayerCard = ({ player, isSelected = false, onClick, size = 'md' }) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  const selectedBg = useColorModeValue('brand.50', 'brand.900');
  const selectedBorder = 'brand.500';

  const sizes = {
    sm: {
      padding: 2,
      avatarSize: 'sm',
      nameSize: 'sm',
      badgeSize: 'sm',
    },
    md: {
      padding: 4,
      avatarSize: 'md',
      nameSize: 'md',
      badgeSize: 'md',
    },
    lg: {
      padding: 6,
      avatarSize: 'lg',
      nameSize: 'lg',
      badgeSize: 'md',
    },
  };

  const sizeConfig = sizes[size] || sizes.md;

  return (
    <Box
      bg={isSelected ? selectedBg : bgColor}
      borderRadius="lg"
      borderWidth={2}
      borderColor={isSelected ? selectedBg : 'transparent'}
      p={sizeConfig.padding}
      cursor={onClick ? 'pointer' : 'default'}
      onClick={onClick}
      transition="all 0.2s"
      _hover={onClick ? {
        bg: isSelected ? selectedBg : hoverBg,
        transform: 'translateY(-2px)',
        boxShadow: 'lg',
      } : {}}
      position="relative"
    >
      {isSelected && (
        <Box
          position="absolute"
          top={2}
          right={2}
          color="brand.500"
          fontSize="xl"
        >
          ✓
        </Box>
      )}

      <VStack spacing={2} align="center">
        <Avatar
          size={sizeConfig.avatarSize}
          name={player.name}
          bg={`${getRaceColor(player.favorite_race)}.500`}
          color="white"
        >
          {getInitials(player.name)}
        </Avatar>

        <VStack spacing={1} align="center">
          <Text
            fontSize={sizeConfig.nameSize}
            fontWeight="bold"
            textAlign="center"
            noOfLines={1}
          >
            {player.name}
          </Text>

          <HStack spacing={1}>
            <Badge
              colorScheme={getMMRBadgeColor(player.mmr)}
              fontSize={sizeConfig.badgeSize}
            >
              {formatMMR(player.mmr)} MMR
            </Badge>
          </HStack>

          {player.favorite_race && (
            <Badge
              variant={`race-${player.favorite_race.toLowerCase()}`}
              fontSize="xs"
            >
              {player.favorite_race}
            </Badge>
          )}

          {player.total_games !== undefined && player.total_games < 5 && (
            <Badge colorScheme="orange" fontSize="xs">
              New ({player.total_games} games)
            </Badge>
          )}
        </VStack>
      </VStack>
    </Box>
  );
};

export default PlayerCard;
