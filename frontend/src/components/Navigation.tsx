/**
 * Navigation Component
 * Clubhouse scoreboard bar: labeled links (no mystery icon buttons),
 * orange active pill, Upload as a distinct CTA, overflow in a "More" menu.
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
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  MenuDivider,
  Button,
  Icon,
} from '@chakra-ui/react';
import {
  FiMenu,
  FiZap,
  FiUpload,
  FiUsers,
  FiHome,
  FiChevronDown,
  FiTarget,
  FiBarChart2,
  FiInfo,
  FiCpu,
  FiAward,
  FiAlertCircle,
  FiActivity,
  FiCrosshair,
} from 'react-icons/fi';
import { LuTrophy, LuSwords } from 'react-icons/lu';
import { useNavigate, useLocation } from 'react-router-dom';
import type { IconType } from 'react-icons';

interface NavItem {
  path: string;
  label: string;
  icon: IconType;
}

// Always-visible links, left to right in priority order
const primaryItems: NavItem[] = [
  { path: '/', label: 'Home', icon: FiHome },
  { path: '/balance', label: 'Teams', icon: FiZap },
  { path: '/players', label: 'Squad', icon: FiUsers },
  { path: '/leaderboard', label: 'Ladder', icon: LuTrophy },
  { path: '/history', label: 'Matches', icon: FiBarChart2 },
];

// Overflow links in the "More" menu
const secondaryItems: NavItem[] = [
  { path: '/meta', label: 'Squad Meta', icon: FiActivity },
  { path: '/predictor', label: 'Predict Match', icon: FiTarget },
  { path: '/ml-intelligence', label: 'ML Insights', icon: FiCpu },
  { path: '/rating-system', label: 'How It Works', icon: FiInfo },
  { path: '/failed-uploads', label: 'Failed Uploads', icon: FiAlertCircle },
];

const alphaItems: NavItem[] = [
  { path: '/achievements', label: 'Achievements', icon: FiAward },
  { path: '/h2h', label: 'Head to Head', icon: LuSwords },
];

const Navigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const isActive = (path: string): boolean => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const secondaryActive = [...secondaryItems, ...alphaItems].some((item) => isActive(item.path));

  return (
    <Box
      as="nav"
      role="navigation"
      aria-label="Main navigation"
      bg="rgba(26, 22, 37, 0.85)"
      backdropFilter="blur(12px)"
      borderBottom="1px solid"
      borderColor="whiteAlpha.100"
      position="sticky"
      top={0}
      zIndex={10}
    >
      <Container maxW="container.xl">
        <Flex h={16} alignItems="center" gap={6}>
          {/* Logo */}
          <HStack
            spacing={2.5}
            cursor="pointer"
            onClick={() => navigate('/')}
            flexShrink={0}
            transition="transform 0.2s"
            _hover={{ transform: 'scale(1.03)' }}
          >
            <Box
              bg="brand.500"
              color="white"
              px={2.5}
              py={1}
              fontWeight="800"
              fontSize="md"
              fontFamily="heading"
              borderRadius="md"
              transform="rotate(-3deg)"
              boxShadow="2px 2px 0 rgba(0,0,0,0.45)"
            >
              SC2
            </Box>
            <VStack spacing={0} align="start" display={{ base: 'none', lg: 'flex' }}>
              <Text fontSize="sm" fontWeight="800" fontFamily="heading" color="gray.100" lineHeight="1.1">
                Squad Tracker
              </Text>
              <Text fontSize="10px" color="gray.500" letterSpacing="0.12em" textTransform="uppercase">
                Track · Balance · Compete
              </Text>
            </VStack>
          </HStack>

          {/* Desktop links */}
          <HStack spacing={1} display={{ base: 'none', md: 'flex' }} flex={1}>
            {primaryItems.map((item) => {
              const active = isActive(item.path);
              return (
                <Button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  variant="unstyled"
                  display="flex"
                  alignItems="center"
                  gap={2}
                  px={3.5}
                  h="38px"
                  fontFamily="heading"
                  fontWeight={active ? '800' : '600'}
                  fontSize="sm"
                  borderRadius="full"
                  bg={active ? 'brand.500' : 'transparent'}
                  color={active ? 'white' : 'gray.400'}
                  transition="all 0.18s ease"
                  _hover={{
                    bg: active ? 'brand.400' : 'whiteAlpha.100',
                    color: active ? 'white' : 'gray.100',
                  }}
                >
                  <Icon as={item.icon} boxSize="15px" />
                  {item.label}
                </Button>
              );
            })}

            {/* More menu */}
            <Menu>
              <MenuButton
                as={Button}
                variant="unstyled"
                display="flex"
                alignItems="center"
                px={3.5}
                h="38px"
                fontFamily="heading"
                fontWeight={secondaryActive ? '800' : '600'}
                fontSize="sm"
                borderRadius="full"
                bg={secondaryActive ? 'accent.500' : 'transparent'}
                color={secondaryActive ? 'space.900' : 'gray.400'}
                _hover={{
                  bg: secondaryActive ? 'accent.400' : 'whiteAlpha.100',
                  color: secondaryActive ? 'space.900' : 'gray.100',
                }}
              >
                <HStack spacing={1}>
                  <Text>More</Text>
                  <Icon as={FiChevronDown} boxSize="14px" />
                </HStack>
              </MenuButton>
              <MenuList
                bg="space.800"
                borderColor="whiteAlpha.200"
                boxShadow="0 16px 40px rgba(0, 0, 0, 0.5)"
                borderRadius="xl"
                py={2}
                px={2}
                minW="220px"
              >
                {secondaryItems.map((item) => (
                  <MenuItem
                    key={item.path}
                    icon={<Icon as={item.icon} boxSize="16px" />}
                    onClick={() => navigate(item.path)}
                    bg={isActive(item.path) ? 'brand.500' : 'transparent'}
                    color={isActive(item.path) ? 'white' : 'gray.300'}
                    fontFamily="heading"
                    fontWeight="600"
                    fontSize="sm"
                    borderRadius="lg"
                    my={0.5}
                    _hover={{ bg: isActive(item.path) ? 'brand.400' : 'whiteAlpha.100' }}
                  >
                    {item.label}
                  </MenuItem>
                ))}
                <MenuDivider borderColor="whiteAlpha.200" mx={-2} my={2} />
                <Text fontSize="10px" fontWeight="bold" color="gray.600" px={3} py={1} letterSpacing="widest">
                  ALPHA FEATURES
                </Text>
                {alphaItems.map((item) => (
                  <MenuItem
                    key={item.path}
                    icon={<Icon as={item.icon} boxSize="16px" opacity={0.6} />}
                    onClick={() => navigate(item.path)}
                    bg={isActive(item.path) ? 'brand.500' : 'transparent'}
                    color={isActive(item.path) ? 'white' : 'gray.500'}
                    fontFamily="heading"
                    fontWeight="600"
                    fontSize="sm"
                    borderRadius="lg"
                    my={0.5}
                    _hover={{ bg: isActive(item.path) ? 'brand.400' : 'whiteAlpha.100', color: 'gray.300' }}
                  >
                    {item.label}
                  </MenuItem>
                ))}
              </MenuList>
            </Menu>
          </HStack>

          {/* Upload CTA */}
          <Button
            display={{ base: 'none', md: 'inline-flex' }}
            onClick={() => navigate('/upload')}
            leftIcon={<FiUpload />}
            size="sm"
            h="38px"
            px={4}
            fontFamily="heading"
            fontWeight="800"
            fontSize="sm"
            borderRadius="full"
            bg={isActive('/upload') ? 'brand.400' : 'transparent'}
            color={isActive('/upload') ? 'white' : 'brand.400'}
            border="2px solid"
            borderColor="brand.500"
            transition="all 0.18s ease"
            _hover={{ bg: 'brand.500', color: 'white', transform: 'translateY(-1px)' }}
            _active={{ transform: 'translateY(0)' }}
          >
            Upload
          </Button>

          {/* Mobile menu button */}
          <IconButton
            icon={<FiMenu size={22} />}
            variant="ghost"
            onClick={onOpen}
            display={{ base: 'flex', md: 'none' }}
            aria-label="Open menu"
            ml="auto"
            color="gray.300"
            _hover={{ bg: 'whiteAlpha.100' }}
          />
        </Flex>
      </Container>

      {/* Mobile Drawer */}
      <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="xs">
        <DrawerOverlay backdropFilter="blur(4px)" />
        <DrawerContent bg="space.800" borderLeft="1px solid" borderColor="whiteAlpha.200">
          <DrawerCloseButton color="gray.400" size="lg" />
          <DrawerHeader
            borderBottom="1px solid"
            borderColor="whiteAlpha.200"
            fontFamily="heading"
            fontWeight="800"
            fontSize="lg"
            color="gray.100"
          >
            <HStack spacing={2}>
              <Icon as={FiCrosshair} color="brand.500" />
              <Text>Menu</Text>
            </HStack>
          </DrawerHeader>

          <DrawerBody pt={4}>
            <VStack spacing={1} align="stretch">
              {[...primaryItems, { path: '/upload', label: 'Upload Replays', icon: FiUpload }].map((item) => {
                const active = isActive(item.path);
                return (
                  <Button
                    key={item.path}
                    leftIcon={<Icon as={item.icon} boxSize="18px" />}
                    variant="ghost"
                    onClick={() => {
                      navigate(item.path);
                      onClose();
                    }}
                    justifyContent="start"
                    size="lg"
                    fontFamily="heading"
                    fontWeight={active ? '800' : '600'}
                    bg={active ? 'brand.500' : 'transparent'}
                    color={active ? 'white' : 'gray.300'}
                    borderRadius="xl"
                    _hover={{ bg: active ? 'brand.400' : 'whiteAlpha.100' }}
                  >
                    {item.label}
                  </Button>
                );
              })}

              <Text fontSize="xs" color="gray.500" fontWeight="bold" px={2} pt={4} letterSpacing="widest">
                MORE
              </Text>
              {[...secondaryItems, ...alphaItems].map((item) => {
                const active = isActive(item.path);
                return (
                  <Button
                    key={item.path}
                    leftIcon={<Icon as={item.icon} boxSize="16px" />}
                    variant="ghost"
                    onClick={() => {
                      navigate(item.path);
                      onClose();
                    }}
                    justifyContent="start"
                    size="md"
                    fontFamily="heading"
                    fontWeight="600"
                    bg={active ? 'accent.500' : 'transparent'}
                    color={active ? 'space.900' : 'gray.400'}
                    borderRadius="lg"
                    _hover={{ bg: active ? 'accent.400' : 'whiteAlpha.100', color: active ? 'space.900' : 'gray.200' }}
                  >
                    {item.label}
                  </Button>
                );
              })}
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </Box>
  );
};

export default Navigation;
