/**
 * PlayerCard Component
 * Tactical unit card with hexagonal styling and multi-race support
 */
import {
  Box,
  Avatar,
  Text,
  Badge,
  VStack,
  HStack,
  Wrap,
  Tooltip,
  useColorModeValue,
} from '@chakra-ui/react';
import { formatMMR, getInitials, getRaceColor, getMMRBadgeColor, getPlayerRaces } from '../utils/formatting';

const PlayerCard = ({ player, isSelected = false, onClick, size = 'md' }) => {
  const bgColor = useColorModeValue('white', 'rgba(26, 32, 44, 0.8)');
  const hoverBg = useColorModeValue('gray.50', 'rgba(45, 55, 72, 0.8)');
  const selectedBg = useColorModeValue('brand.50', 'rgba(0, 82, 102, 0.3)');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.100');

  const sizes = {
    sm: {
      padding: 2,
      avatarSize: 'sm',
      nameSize: 'sm',
      badgeSize: 'xs',
    },
    md: {
      padding: 4,
      avatarSize: 'md',
      nameSize: 'md',
      badgeSize: 'sm',
    },
    lg: {
      padding: 6,
      avatarSize: 'lg',
      nameSize: 'lg',
      badgeSize: 'md',
    },
  };

  const sizeConfig = sizes[size] || sizes.md;
  const playerRaces = getPlayerRaces(player);
  const primaryRace = playerRaces.length > 0 ? playerRaces[0].name : 'Random';

  return (
    <Box
      bg={isSelected ? selectedBg : bgColor}
      borderRadius="lg"
      borderWidth={2}
      borderColor={isSelected ? 'brand.500' : borderColor}
      p={sizeConfig.padding}
      cursor={onClick ? 'pointer' : 'default'}
      onClick={onClick}
      transition="all 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
      _hover={onClick ? {
        bg: isSelected ? selectedBg : hoverBg,
        transform: 'translateY(-4px)',
        boxShadow: isSelected
          ? '0 8px 30px rgba(0, 212, 255, 0.4), 0 0 0 1px rgba(0, 212, 255, 0.5)'
          : '0 8px 20px rgba(0, 212, 255, 0.2)',
        borderColor: 'brand.400',
      } : {}}
      position="relative"
      overflow="visible"
      boxShadow={isSelected ? '0 4px 20px rgba(0, 212, 255, 0.3)' : 'md'}
    >
      {/* Corner Brackets - Top Left */}
      <Box
        position="absolute"
        top={-1}
        left={-1}
        width="16px"
        height="16px"
        borderTop="2px solid"
        borderLeft="2px solid"
        borderColor={isSelected ? 'brand.400' : 'transparent'}
        transition="all 0.3s"
        opacity={isSelected ? 1 : 0}
      />

      {/* Corner Brackets - Bottom Right */}
      <Box
        position="absolute"
        bottom={-1}
        right={-1}
        width="16px"
        height="16px"
        borderBottom="2px solid"
        borderRight="2px solid"
        borderColor={isSelected ? 'brand.400' : 'transparent'}
        transition="all 0.3s"
        opacity={isSelected ? 1 : 0}
      />

      {/* Selection Indicator */}
      {isSelected && (
        <Box
          position="absolute"
          top={2}
          right={2}
          color="brand.400"
          fontSize="xl"
          fontWeight="bold"
          textShadow="0 0 10px rgba(0, 212, 255, 0.8)"
        >
          ✓
        </Box>
      )}

      <VStack spacing={3} align="center">
        {/* Hexagonal Avatar Frame */}
        <Box position="relative">
          {/* Hexagonal glow effect */}
          {isSelected && (
            <Box
              position="absolute"
              top="50%"
              left="50%"
              transform="translate(-50%, -50%)"
              width="calc(100% + 16px)"
              height="calc(100% + 16px)"
              borderRadius="full"
              bg="brand.500"
              opacity={0.2}
              filter="blur(8px)"
              animation="pulse 2s ease-in-out infinite"
              sx={{
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 0.2 },
                  '50%': { opacity: 0.4 },
                },
              }}
            />
          )}

          <Avatar
            size={sizeConfig.avatarSize}
            name={player.name}
            bg={`${getRaceColor(primaryRace)}.500`}
            color="white"
            border="3px solid"
            borderColor={isSelected ? 'brand.400' : 'whiteAlpha.200'}
            boxShadow={isSelected ? '0 0 20px rgba(0, 212, 255, 0.4)' : 'md'}
            position="relative"
            zIndex={1}
          >
            {getInitials(player.name)}
          </Avatar>
        </Box>

        <VStack spacing={1.5} align="center" width="100%">
          <Text
            fontSize={sizeConfig.nameSize}
            fontWeight="bold"
            textAlign="center"
            noOfLines={1}
            fontFamily="heading"
            letterSpacing="wide"
            color={isSelected ? 'brand.300' : 'inherit'}
            textShadow={isSelected ? '0 0 8px rgba(0, 212, 255, 0.3)' : 'none'}
          >
            {player.name}
          </Text>

          {/* MMR Badge */}
          <Badge
            variant={`mmr-${getMMRBadgeColor(player.mmr)}`}
            fontSize={sizeConfig.badgeSize}
            px={2}
            py={0.5}
            borderRadius="md"
          >
            {formatMMR(player.mmr)} MMR
          </Badge>

          {/* Multi-Race Display */}
          {playerRaces.length > 0 && (
            <Wrap spacing={1} justify="center" width="100%">
              {playerRaces.map((race, index) => (
                <Tooltip
                  key={race.name}
                  label={`${race.name}: ${race.games} games`}
                  fontSize="xs"
                  hasArrow
                >
                  <Badge
                    variant={`race-${race.name.toLowerCase()}`}
                    fontSize="xs"
                    px={1.5}
                    py={0.5}
                    borderRadius="sm"
                    opacity={index === 0 ? 1 : 0.7}
                    border={index === 0 ? '1px solid' : 'none'}
                    borderColor={index === 0 ? 'whiteAlpha.300' : 'transparent'}
                  >
                    {race.emoji} {race.name}
                    {playerRaces.length > 1 && ` (${race.games})`}
                  </Badge>
                </Tooltip>
              ))}
            </Wrap>
          )}

          {/* New Player Indicator */}
          {player.total_games !== undefined && player.total_games < 5 && (
            <Badge
              colorScheme="orange"
              fontSize="xs"
              px={2}
              py={0.5}
              borderRadius="md"
              textTransform="uppercase"
              letterSpacing="wider"
            >
              ⚡ New ({player.total_games} games)
            </Badge>
          )}

          {/* Win Rate Bar (optional, if available) */}
          {player.win_rate !== undefined && player.total_games >= 5 && (
            <Box width="100%" mt={1}>
              <HStack spacing={1} fontSize="xs" color="gray.500" mb={1}>
                <Text>Win Rate</Text>
                <Text fontWeight="bold" color={player.win_rate >= 0.5 ? 'shield.400' : 'gray.400'}>
                  {(player.win_rate * 100).toFixed(0)}%
                </Text>
              </HStack>
              <Box
                width="100%"
                height="3px"
                bg="whiteAlpha.200"
                borderRadius="full"
                overflow="hidden"
              >
                <Box
                  width={`${player.win_rate * 100}%`}
                  height="100%"
                  bg={player.win_rate >= 0.5 ? 'shield.500' : 'gray.500'}
                  borderRadius="full"
                  transition="width 0.3s"
                  boxShadow={player.win_rate >= 0.5 ? '0 0 8px rgba(0, 255, 136, 0.5)' : 'none'}
                />
              </Box>
            </Box>
          )}
        </VStack>
      </VStack>
    </Box>
  );
};

export default PlayerCard;
