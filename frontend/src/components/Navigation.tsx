/**
 * Navigation Component
 * Friend Squad Edition - Warm, icon-focused, less noisy
 * Groups features into logical sections with larger touch targets
 */
import React from 'react';
import {
  Box,
  Container,
  Flex,
  HStack,
  IconButton,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  VStack,
  useDisclosure,
  useColorModeValue,
  Text,
  Tooltip,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  MenuDivider,
  Button,
} from '@chakra-ui/react';
import { 
  FiMenu, 
  FiZap, 
  FiUpload, 
  FiUsers, 
  FiHome, 
  FiMoreHorizontal,
  FiTarget,
  FiBarChart2,
  FiInfo,
  FiCpu,
  FiTrendingUp,
  FiAlertCircle,
} from 'react-icons/fi';
import { useNavigate, useLocation } from 'react-router-dom';
import type { IconType } from 'react-icons';

interface NavItem {
  path: string;
  label: string;
  icon: IconType;
  emoji?: string;
}

const Navigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const bgColor = useColorModeValue('white', 'space.800');
  const borderColor = useColorModeValue('gray.200', 'space.900');

  // Primary nav items - most used, always visible
  const primaryItems: NavItem[] = [
    { path: '/', label: 'Home', icon: FiHome, emoji: '🏠' },
    { path: '/balance', label: 'Teams', icon: FiZap, emoji: '⚡' },
    { path: '/players', label: 'Squad', icon: FiUsers, emoji: '👥' },
    { path: '/upload', label: 'Upload', icon: FiUpload, emoji: '📤' },
  ];

  // Secondary items - in "More" menu
  const secondaryItems: NavItem[] = [
    { path: '/leaderboard', label: 'Leaderboard', icon: FiTrendingUp, emoji: '🏆' },
    { path: '/predictor', label: 'Predict Match', icon: FiTarget, emoji: '🎯' },
    { path: '/history', label: 'Match History', icon: FiBarChart2, emoji: '📊' },
    { path: '/ml-intelligence', label: 'ML Insights', icon: FiCpu, emoji: '🧠' },
    { path: '/rating-system', label: 'How It Works', icon: FiInfo, emoji: 'ℹ️' },
    { path: '/failed-uploads', label: 'Failed Uploads', icon: FiAlertCircle, emoji: '⚠️' },
  ];

  // Alpha features - moved to bottom
  const alphaItems: NavItem[] = [
    { path: '/achievements', label: 'Achievements', icon: FiZap, emoji: '🏅' },
    { path: '/h2h', label: 'Head to Head', icon: FiUsers, emoji: '⚔️' },
  ];

  const isActive = (path: string): boolean => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  // Check if any secondary or alpha item is active
  const secondaryActive = [...secondaryItems, ...alphaItems].some(item => isActive(item.path));

  return (
    <Box
      as="nav"
      role="navigation"
      aria-label="Main navigation"
      bg={bgColor}
      borderBottom="3px solid"
      borderColor={borderColor}
      position="sticky"
      top={0}
      zIndex={10}
      boxShadow="0 4px 0 var(--chakra-colors-space-900)"
    >
      <Container maxW="container.xl">
        <Flex h={16} alignItems="center" justifyContent="space-between">
          {/* Logo - Friend Squad Style */}
          <HStack 
            spacing={2} 
            cursor="pointer" 
            onClick={() => navigate('/')}
            transition="transform 0.2s"
            _hover={{ transform: 'scale(1.02)' }}
          >
            <Box
              bg="brand.500"
              color="white"
              px={3}
              py={1.5}
              fontWeight="black"
              fontSize="lg"
              fontFamily="heading"
              borderRadius="lg"
              border="3px solid"
              borderColor="space.900"
              boxShadow="3px 3px 0 var(--chakra-colors-space-900)"
            >
              SC2
            </Box>
            <VStack spacing={0} align="start" display={{ base: 'none', sm: 'flex' }}>
              <Text
                fontSize="md"
                fontWeight="bold"
                fontFamily="heading"
                color="brand.500"
                lineHeight="1.2"
              >
                Squad Tracker
              </Text>
              <Text fontSize="xs" color="gray.500">
                Track • Balance • Compete
              </Text>
            </VStack>
          </HStack>

          {/* Desktop Navigation - Icon-focused with tooltips */}
          <HStack spacing={2} display={{ base: 'none', md: 'flex' }}>
            {primaryItems.map((item) => {
              const active = isActive(item.path);
              return (
                <Tooltip 
                  key={item.path} 
                  label={item.label} 
                  hasArrow 
                  placement="bottom"
                  bg="space.700"
                  color="white"
                >
                  <IconButton
                    aria-label={item.label}
                    icon={
                      <Box fontSize="xl">
                        {active ? item.emoji : <item.icon />}
                      </Box>
                    }
                    variant="ghost"
                    size="lg"
                    borderRadius="xl"
                    bg={active ? 'brand.500' : 'transparent'}
                    color={active ? 'white' : 'gray.400'}
                    border={active ? '3px solid' : '3px solid transparent'}
                    borderColor={active ? 'space.900' : 'transparent'}
                    boxShadow={active ? '3px 3px 0 var(--chakra-colors-space-900)' : 'none'}
                    onClick={() => navigate(item.path)}
                    transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
                    _hover={{
                      bg: active ? 'brand.400' : 'space.700',
                      color: active ? 'white' : 'brand.400',
                      transform: 'translateY(-2px)',
                    }}
                  />
                </Tooltip>
              );
            })}

            {/* More Menu */}
            <Menu>
              <Tooltip label="More" hasArrow placement="bottom" bg="space.700" color="white">
                <MenuButton
                  as={IconButton}
                  aria-label="More options"
                  icon={<FiMoreHorizontal size={20} />}
                  variant="ghost"
                  size="lg"
                  borderRadius="xl"
                  bg={secondaryActive ? 'accent.500' : 'transparent'}
                  color={secondaryActive ? 'space.900' : 'gray.400'}
                  border={secondaryActive ? '3px solid' : '3px solid transparent'}
                  borderColor={secondaryActive ? 'space.900' : 'transparent'}
                  boxShadow={secondaryActive ? '3px 3px 0 var(--chakra-colors-space-900)' : 'none'}
                  _hover={{
                    bg: secondaryActive ? 'accent.400' : 'space.700',
                    color: secondaryActive ? 'space.900' : 'accent.400',
                  }}
                />
              </Tooltip>
              <MenuList
                bg="space.800"
                borderColor="space.700"
                border="3px solid"
                boxShadow="4px 4px 0 var(--chakra-colors-space-900)"
                borderRadius="xl"
                py={2}
                px={2}
                overflow="hidden"
              >
                {secondaryItems.map((item) => (
                  <MenuItem
                    key={item.path}
                    icon={<Text fontSize="lg" className="emoji-font">{item.emoji}</Text>}
                    onClick={() => navigate(item.path)}
                    bg={isActive(item.path) ? 'brand.500' : 'transparent'}
                    color={isActive(item.path) ? 'white' : 'gray.300'}
                    fontFamily="heading"
                    fontWeight="medium"
                    borderRadius="lg"
                    my={0.5}
                    _hover={{
                      bg: isActive(item.path) ? 'brand.400' : 'space.700',
                    }}
                  >
                    {item.label}
                  </MenuItem>
                ))}

                {alphaItems.length > 0 && (
                  <>
                    <MenuDivider borderColor="space.700" mx={-2} my={2} />
                    <Text fontSize="10px" fontWeight="bold" color="gray.600" px={3} py={1} letterSpacing="widest">ALPHA FEATURES</Text>
                    {alphaItems.map((item) => (
                      <MenuItem
                        key={item.path}
                        icon={<Text fontSize="lg" className="emoji-font" opacity={0.4}>{item.emoji}</Text>}
                        onClick={() => navigate(item.path)}
                        bg={isActive(item.path) ? 'brand.500' : 'transparent'}
                        color={isActive(item.path) ? 'white' : 'gray.500'}
                        fontFamily="heading"
                        fontWeight="medium"
                        borderRadius="lg"
                        opacity={0.7}
                        my={0.5}
                        _hover={{
                          bg: isActive(item.path) ? 'brand.400' : 'space.700',
                          opacity: 1,
                        }}
                      >
                        {item.label}
                      </MenuItem>
                    ))}
                  </>
                )}
              </MenuList>
            </Menu>
          </HStack>

          {/* Mobile Menu Button */}
          <IconButton
            icon={<FiMenu size={24} />}
            variant="ghost"
            onClick={onOpen}
            display={{ base: 'flex', md: 'none' }}
            aria-label="Open menu"
            size="lg"
            color="brand.500"
            _hover={{
              bg: 'space.700',
            }}
          />
        </Flex>
      </Container>

      {/* Mobile Drawer - Friend Squad Style */}
      <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="xs">
        <DrawerOverlay backdropFilter="blur(4px)" />
        <DrawerContent 
          bg="space.800" 
          borderLeft="3px solid" 
          borderColor="space.900"
        >
          <DrawerCloseButton color="gray.400" size="lg" />
          <DrawerHeader
            borderBottom="3px solid"
            borderColor="space.900"
            fontFamily="heading"
            fontSize="xl"
            color="brand.500"
          >
            🎮 Menu
          </DrawerHeader>

          <DrawerBody pt={4}>
            <VStack spacing={2} align="stretch">
              {/* Primary Items */}
              <Text fontSize="xs" color="gray.500" fontWeight="bold" px={2} pt={2}>
                QUICK ACCESS
              </Text>
              {primaryItems.map((item) => {
                const active = isActive(item.path);
                return (
                  <Button
                    key={item.path}
                    leftIcon={<Text fontSize="xl">{item.emoji}</Text>}
                    variant="ghost"
                    onClick={() => {
                      navigate(item.path);
                      onClose();
                    }}
                    justifyContent="start"
                    size="lg"
                    fontFamily="heading"
                    fontWeight="medium"
                    bg={active ? 'brand.500' : 'transparent'}
                    color={active ? 'white' : 'gray.300'}
                    border={active ? '3px solid' : '3px solid transparent'}
                    borderColor={active ? 'space.900' : 'transparent'}
                    boxShadow={active ? '3px 3px 0 var(--chakra-colors-space-900)' : 'none'}
                    borderRadius="xl"
                    _hover={{
                      bg: active ? 'brand.400' : 'space.700',
                    }}
                  >
                    {item.label}
                  </Button>
                );
              })}

              {/* Secondary Items */}
              <Text fontSize="xs" color="gray.500" fontWeight="bold" px={2} pt={4}>
                MORE FEATURES
              </Text>
              {secondaryItems.map((item) => {
                const active = isActive(item.path);
                return (
                  <Button
                    key={item.path}
                    leftIcon={<Text fontSize="lg">{item.emoji}</Text>}
                    variant="ghost"
                    onClick={() => {
                      navigate(item.path);
                      onClose();
                    }}
                    justifyContent="start"
                    size="md"
                    fontFamily="heading"
                    fontWeight="medium"
                    bg={active ? 'accent.500' : 'transparent'}
                    color={active ? 'space.900' : 'gray.400'}
                    borderRadius="lg"
                    _hover={{
                      bg: active ? 'accent.400' : 'space.700',
                      color: active ? 'space.900' : 'gray.300',
                    }}
                  >
                    {item.label}
                  </Button>
                );
              })}

              {/* Alpha Items */}
              {alphaItems.length > 0 && (
                <>
                  <Text fontSize="10px" color="gray.600" fontWeight="bold" px={2} pt={4} letterSpacing="widest">
                    ALPHA FEATURES
                  </Text>
                  {alphaItems.map((item) => {
                    const active = isActive(item.path);
                    return (
                      <Button
                        key={item.path}
                        leftIcon={<Text fontSize="lg" opacity={0.4}>{item.emoji}</Text>}
                        variant="ghost"
                        onClick={() => {
                          navigate(item.path);
                          onClose();
                        }}
                        justifyContent="start"
                        size="sm"
                        fontFamily="heading"
                        fontWeight="medium"
                        opacity={0.7}
                        color={active ? 'accent.500' : 'gray.500'}
                        borderRadius="lg"
                        _hover={{
                          bg: 'space.700',
                          opacity: 1,
                        }}
                      >
                        {item.label}
                      </Button>
                    );
                  })}
                </>
              )}
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </Box>
  );
};

export default Navigation;
