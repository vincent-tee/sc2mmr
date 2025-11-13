/**
 * Navigation Component
 * Top navigation bar with logo and menu items
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
import { FiMenu, FiZap, FiUpload, FiUsers, FiBarChart2, FiHome, FiInfo, FiAlertCircle } from 'react-icons/fi';
import { useNavigate, useLocation } from 'react-router-dom';

const Navigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const navItems = [
    { path: '/', label: 'Home', icon: FiHome },
    { path: '/balance', label: 'Generate Teams', icon: FiZap, highlight: true },
    { path: '/upload', label: 'Upload', icon: FiUpload },
    { path: '/failed-uploads', label: 'Failed Uploads', icon: FiAlertCircle },
    { path: '/players', label: 'Players', icon: FiUsers },
    { path: '/history', label: 'History', icon: FiBarChart2 },
    { path: '/rating-system', label: 'Rating System', icon: FiInfo },
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
      borderBottom="1px"
      borderColor={borderColor}
      position="sticky"
      top={0}
      zIndex={10}
      boxShadow="sm"
    >
      <Container maxW="container.xl">
        <Flex h={16} alignItems="center" justifyContent="space-between">
          {/* Logo */}
          <HStack spacing={3} cursor="pointer" onClick={() => navigate('/')}>
            <Box
              bg="brand.500"
              color="white"
              px={3}
              py={1}
              borderRadius="md"
              fontWeight="bold"
              fontSize="lg"
            >
              SC2
            </Box>
            <Text fontSize="lg" fontWeight="bold" display={{ base: 'none', md: 'block' }}>
              MMR Tracker
            </Text>
          </HStack>

          {/* Desktop Navigation */}
          <HStack spacing={2} display={{ base: 'none', md: 'flex' }}>
            {navItems.map((item) => (
              <Button
                key={item.path}
                leftIcon={<item.icon />}
                variant={isActive(item.path) ? 'solid' : 'ghost'}
                colorScheme={item.highlight ? 'accent' : 'brand'}
                onClick={() => navigate(item.path)}
                position="relative"
              >
                {item.label}
                {item.highlight && (
                  <Badge
                    position="absolute"
                    top={-1}
                    right={-1}
                    colorScheme="accent"
                    fontSize="xx-small"
                    px={1}
                  >
                    ★
                  </Badge>
                )}
              </Button>
            ))}
          </HStack>

          {/* Mobile Menu Button */}
          <IconButton
            icon={<FiMenu />}
            variant="ghost"
            onClick={onOpen}
            display={{ base: 'flex', md: 'none' }}
            aria-label="Open menu"
          />
        </Flex>
      </Container>

      {/* Mobile Drawer */}
      <Drawer isOpen={isOpen} placement="right" onClose={onClose}>
        <DrawerOverlay />
        <DrawerContent>
          <DrawerCloseButton />
          <DrawerHeader>Menu</DrawerHeader>

          <DrawerBody>
            <VStack spacing={2} align="stretch">
              {navItems.map((item) => (
                <Button
                  key={item.path}
                  leftIcon={<item.icon />}
                  variant={isActive(item.path) ? 'solid' : 'ghost'}
                  colorScheme={item.highlight ? 'accent' : 'brand'}
                  onClick={() => {
                    navigate(item.path);
                    onClose();
                  }}
                  justifyContent="start"
                  size="lg"
                >
                  {item.label}
                  {item.highlight && (
                    <Badge ml={2} colorScheme="accent">
                      Primary
                    </Badge>
                  )}
                </Button>
              ))}
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </Box>
  );
};

export default Navigation;
