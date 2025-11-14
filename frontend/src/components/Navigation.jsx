/**
 * Navigation Component
 * Command Center-inspired tactical navigation
 */
import {
  Box,
  Container,
  Flex,
  HStack,
  Button,
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
  Badge,
} from '@chakra-ui/react';
import { FiMenu, FiZap, FiUpload, FiUsers, FiBarChart2, FiHome, FiInfo, FiAlertCircle, FiBrain } from 'react-icons/fi';
import { useNavigate, useLocation } from 'react-router-dom';

const Navigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const bgColor = useColorModeValue('white', 'rgba(13, 17, 33, 0.95)');
  const borderColor = useColorModeValue('gray.200', 'brand.500');

  const navItems = [
    { path: '/', label: 'Home', icon: FiHome },
    { path: '/balance', label: 'Generate Teams', icon: FiZap, highlight: true },
    { path: '/upload', label: 'Upload', icon: FiUpload },
    { path: '/failed-uploads', label: 'Failed', icon: FiAlertCircle },
    { path: '/players', label: 'Players', icon: FiUsers },
    { path: '/history', label: 'History', icon: FiBarChart2 },
    { path: '/rating-system', label: 'Info', icon: FiInfo },
    { path: '/adaptive-model', label: 'AI Model', icon: FiBrain },
  ];

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <Box
      bg={bgColor}
      borderBottom="2px"
      borderColor={borderColor}
      position="sticky"
      top={0}
      zIndex={10}
      boxShadow="0 4px 20px rgba(0, 212, 255, 0.1)"
      backdropFilter="blur(10px)"
    >
      <Container maxW="container.xl">
        <Flex h={16} alignItems="center" justifyContent="space-between">
          {/* Logo - Command Center Style */}
          <HStack spacing={3} cursor="pointer" onClick={() => navigate('/')} position="relative">
            {/* Corner brackets for tactical look */}
            <Box position="relative">
              <Box
                bg="brand.500"
                color="gray.900"
                px={3}
                py={1}
                fontWeight="black"
                fontSize="xl"
                fontFamily="heading"
                position="relative"
                clipPath="polygon(0 0, 100% 0, 100% 100%, 8px 100%, 0 calc(100% - 8px))"
                boxShadow="0 0 20px rgba(0, 212, 255, 0.4)"
              >
                SC2
                {/* Top-left corner bracket */}
                <Box
                  position="absolute"
                  top={-1}
                  left={-1}
                  width="12px"
                  height="12px"
                  borderTop="2px solid"
                  borderLeft="2px solid"
                  borderColor="brand.300"
                />
                {/* Bottom-right corner bracket */}
                <Box
                  position="absolute"
                  bottom={-1}
                  right={-1}
                  width="12px"
                  height="12px"
                  borderBottom="2px solid"
                  borderRight="2px solid"
                  borderColor="brand.300"
                />
              </Box>
            </Box>
            <VStack spacing={0} align="start" display={{ base: 'none', md: 'flex' }}>
              <Text
                fontSize="sm"
                fontWeight="bold"
                fontFamily="heading"
                color="brand.400"
                lineHeight="1.2"
                letterSpacing="wider"
              >
                MMR TRACKER
              </Text>
              <Text
                fontSize="xs"
                color="gray.500"
                letterSpacing="wide"
              >
                COMMAND CENTER
              </Text>
            </VStack>
          </HStack>

          {/* Desktop Navigation - Tactical Button Grid */}
          <HStack spacing={1} display={{ base: 'none', md: 'flex' }}>
            {navItems.map((item) => {
              const active = isActive(item.path);
              return (
                <Button
                  key={item.path}
                  leftIcon={<item.icon />}
                  variant={active ? 'solid' : 'ghost'}
                  colorScheme={item.highlight ? 'accent' : 'brand'}
                  onClick={() => navigate(item.path)}
                  position="relative"
                  size="sm"
                  fontSize="xs"
                  px={3}
                  borderRadius="md"
                  _before={active ? {
                    content: '""',
                    position: 'absolute',
                    top: '-2px',
                    left: '-2px',
                    right: '-2px',
                    bottom: '-2px',
                    background: 'linear-gradient(45deg, transparent, rgba(0, 212, 255, 0.3), transparent)',
                    borderRadius: 'md',
                    zIndex: -1,
                  } : {}}
                >
                  {item.label}
                  {item.highlight && (
                    <Badge
                      position="absolute"
                      top={-2}
                      right={-2}
                      bg="accent.500"
                      color="gray.900"
                      fontSize="xx-small"
                      px={1.5}
                      borderRadius="full"
                      boxShadow="0 0 10px rgba(255, 179, 0, 0.6)"
                    >
                      ★
                    </Badge>
                  )}
                </Button>
              );
            })}
          </HStack>

          {/* Mobile Menu Button - Tactical Style */}
          <IconButton
            icon={<FiMenu />}
            variant="ghost"
            onClick={onOpen}
            display={{ base: 'flex', md: 'none' }}
            aria-label="Open menu"
            color="brand.400"
            _hover={{
              bg: 'whiteAlpha.100',
              color: 'brand.300',
            }}
          />
        </Flex>
      </Container>

      {/* Mobile Drawer - Command Panel Style */}
      <Drawer isOpen={isOpen} placement="right" onClose={onClose}>
        <DrawerOverlay backdropFilter="blur(4px)" />
        <DrawerContent bg="space.800" borderLeft="2px solid" borderColor="brand.500">
          <DrawerCloseButton color="brand.400" />
          <DrawerHeader
            borderBottom="1px solid"
            borderColor="brand.500"
            fontFamily="heading"
            color="brand.400"
            letterSpacing="wider"
          >
            COMMAND PANEL
          </DrawerHeader>

          <DrawerBody pt={4}>
            <VStack spacing={2} align="stretch">
              {navItems.map((item) => {
                const active = isActive(item.path);
                return (
                  <Button
                    key={item.path}
                    leftIcon={<item.icon />}
                    variant={active ? 'solid' : 'ghost'}
                    colorScheme={item.highlight ? 'accent' : 'brand'}
                    onClick={() => {
                      navigate(item.path);
                      onClose();
                    }}
                    justifyContent="start"
                    size="lg"
                    fontFamily="heading"
                    position="relative"
                    _before={active ? {
                      content: '""',
                      position: 'absolute',
                      left: 0,
                      top: '50%',
                      transform: 'translateY(-50%)',
                      width: '4px',
                      height: '60%',
                      bg: item.highlight ? 'accent.500' : 'brand.500',
                      boxShadow: item.highlight
                        ? '0 0 10px rgba(255, 179, 0, 0.6)'
                        : '0 0 10px rgba(0, 212, 255, 0.6)',
                    } : {}}
                  >
                    {item.label}
                    {item.highlight && (
                      <Badge
                        ml="auto"
                        bg="accent.500"
                        color="gray.900"
                        fontWeight="bold"
                      >
                        PRIMARY
                      </Badge>
                    )}
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
