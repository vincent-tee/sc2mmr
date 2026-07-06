/**
 * TeamSelector Component - Player Selection UI
 * Displays available players with selection toggles and bulk actions
 */
import {
  Box,
  HStack,
  VStack,
  Heading,
  Text,
  Button,
  SimpleGrid,
  Badge,
  Icon,
  Input,
  InputGroup,
  InputLeftElement,
  IconButton,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Divider,
  Switch,
  FormControl,
  FormLabel,
} from '@chakra-ui/react';
import { FiUsers, FiCheck, FiX, FiPlus, FiCpu, FiChevronDown, FiEdit2, FiTrash2, FiClock, FiSearch } from 'react-icons/fi';
import PlayerCard from '@/components/PlayerCard';
import TacticalCard from '@/components/TacticalCard';
import type { Player } from '@/types/api';
import React, { useState, useEffect, useRef } from 'react';
import { teamsApi } from '@/api/endpoints';

interface TeamSelectorProps {
  players: Player[];
  selectedPlayers: Player[];
  onTogglePlayer: (player: Player) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onAddGuest: (name: string, mmr: number) => void;
  onEditGuest?: (playerId: number, name: string, mmr: number) => void;
  onDeleteGuest?: (playerId: number) => void;
  onAddAI?: (difficulty: string, mmr: number) => void;
  onSelectLastMatch?: () => void;
}

const TeamSelector: React.FC<TeamSelectorProps> = ({
  players,
  selectedPlayers,
  onTogglePlayer,
  onSelectAll,
  onClearSelection,
  onAddGuest,
  onEditGuest,
  onDeleteGuest,
  onAddAI,
  onSelectLastMatch,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isEditOpen, onOpen: onEditOpen, onClose: onEditClose } = useDisclosure();
  // Refs so closed modals return keyboard focus to the button that opened them,
  // instead of relying on Chakra/react-focus-lock's implicit "last active element"
  // capture (which can resolve incorrectly - see handleOpenEdit/Add Guest button below).
  const addGuestButtonRef = useRef<HTMLButtonElement>(null);
  const editGuestTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [guestName, setGuestName] = useState('');
  const [guestMMR, setGuestMMR] = useState(2500);
  const [editingPlayer, setEditingPlayer] = useState<Player | null>(null);
  const [editName, setEditName] = useState('');
  const [editMMR, setEditMMR] = useState(2500);
  const [aiDifficulties, setAIDifficulties] = useState<Record<string, number>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [showLegacy, setShowLegacy] = useState(false);

  // Identify guest players (negative IDs, not AI)
  const guestPlayers = players.filter(p => p.id < 0 && !p.is_ai);

  useEffect(() => {
    const fetchAI = async () => {
      try {
        const response = await teamsApi.getAIDifficulties();
        setAIDifficulties(response.data.difficulties);
      } catch (error) {
        console.error('Failed to fetch AI difficulties', error);
      }
    };
    fetchAI();
  }, []);

  const handleAddGuest = () => {
    if (guestName.trim()) {
      onAddGuest(guestName, guestMMR);
      setGuestName('');
      setGuestMMR(2500);
      onClose();
    }
  };

  const handleOpenEdit = (player: Player, triggerEl: HTMLButtonElement | null) => {
    editGuestTriggerRef.current = triggerEl;
    setEditingPlayer(player);
    setEditName(player.name.replace(' (Guest)', ''));
    setEditMMR(player.mmr);
    onEditOpen();
  };

  const handleSaveEdit = () => {
    if (editingPlayer && editName.trim() && onEditGuest) {
      onEditGuest(editingPlayer.id, editName, editMMR);
      onEditClose();
      setEditingPlayer(null);
    }
  };

  const handleDeleteGuest = (playerId: number) => {
    if (onDeleteGuest) {
      onDeleteGuest(playerId);
    }
  };

  const minPlayers = 2;
  const canGenerate = selectedPlayers.length >= minPlayers;
  const needMorePlayers = selectedPlayers.length < minPlayers;
  const hasOddPlayers = selectedPlayers.length % 2 !== 0;

  const getGameMode = (count: number): string => {
    if (count === 2) return '1v1';
    if (count === 4) return '2v2';
    if (count === 6) return '3v3';
    if (count === 8) return '4v4';
    if (count === 10) return '5v5';
    if (count % 2 === 0) return `${count / 2}v${count / 2}`;
    return `${Math.ceil(count / 2)}v${Math.floor(count / 2)}`;
  };

  return (
    <Box>
      <TacticalCard variant="command" glowColor="rgba(0, 212, 255, 0.5)">
        <Box p={6}>
          <HStack justify="space-between" mb={6}>
            <VStack align="start" spacing={2}>
              <HStack>
                <Icon as={FiUsers} color="brand.400" boxSize={6} filter="drop-shadow(2px 2px 0 var(--chakra-colors-space-900))" />
                <Heading
                  size="md"
                  fontFamily="heading"
                  fontWeight="black"
                  letterSpacing="wider"
                  color="brand.300"
                >
                  Player Selection
                </Heading>
              </HStack>
              <HStack spacing={3} flexWrap="wrap">
                <Badge
                  colorScheme={canGenerate ? 'green' : 'orange'}
                  fontSize="lg"
                  fontWeight="black"
                  px={3}
                  py={1}
                  borderRadius="lg"
                  fontFamily="heading"
                  boxShadow="2px 2px 0 var(--chakra-colors-space-900)"
                >
                  {selectedPlayers.length} selected
                </Badge>
                {selectedPlayers.length >= minPlayers && (
                  <Badge
                    colorScheme={hasOddPlayers ? 'yellow' : 'blue'}
                    fontSize="lg"
                    fontWeight="black"
                    px={3}
                    py={1}
                    borderRadius="lg"
                    fontFamily="heading"
                    boxShadow="2px 2px 0 var(--chakra-colors-space-900)"
                  >
                    {getGameMode(selectedPlayers.length)}
                  </Badge>
                )}
              </HStack>
            </VStack>

            <HStack>
              <Menu>
                <MenuButton
                  as={Button}
                  size="sm"
                  variant="ghost"
                  colorScheme="purple"
                  leftIcon={<FiCpu />}
                  rightIcon={<FiChevronDown />}
                  fontFamily="heading"
                >
                  Add AI
                </MenuButton>
                <MenuList bg="space.800" borderColor="space.700" boxShadow="4px 4px 0 var(--chakra-colors-space-900)" borderRadius="xl">
                  <Text px={3} py={2} fontSize="10px" color="gray.500" fontWeight="black" textTransform="uppercase" letterSpacing="widest">
                    Select Difficulty
                  </Text>
                  <Divider mb={2} borderColor="whiteAlpha.100" />
                  {Object.entries(aiDifficulties).map(([diff, mmr]) => (
                    <MenuItem
                      key={diff}
                      bg="transparent"
                      _hover={{ bg: 'space.700' }}
                      onClick={() => onAddAI && onAddAI(diff, mmr)}
                      fontFamily="heading"
                    >
                      <HStack justify="space-between" w="full">
                        <Text textTransform="capitalize" fontSize="sm">{diff.replace('_', ' ')}</Text>
                        <Badge variant="solid" bg="space.900" color="purple.400" fontFamily="mono">{mmr}</Badge>
                      </HStack>
                    </MenuItem>
                  ))}
                </MenuList>
              </Menu>
              <Button
                size="sm"
                variant="ghost"
                colorScheme="brand"
                onClick={onSelectLastMatch}
                leftIcon={<FiClock />}
                fontFamily="heading"
              >
                Last Match
              </Button>
              <Button
                ref={addGuestButtonRef}
                size="sm"
                variant="ghost"
                colorScheme="brand"
                onClick={onOpen}
                leftIcon={<FiPlus />}
                fontFamily="heading"
              >
                Add Guest
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={onClearSelection}
                fontFamily="heading"
                leftIcon={<FiX />}
                color="gray.400"
              >
                Clear
              </Button>
            </HStack>
          </HStack>

          <HStack mb={4} spacing={3} flexWrap="wrap">
            <InputGroup size="sm" maxW="240px">
              <InputLeftElement pointerEvents="none">
                <Icon as={FiSearch} color="gray.500" />
              </InputLeftElement>
              <Input
                placeholder="Search players..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                borderRadius="full"
                bg="whiteAlpha.100"
                border="1px solid"
                borderColor="whiteAlpha.200"
                _placeholder={{ color: 'gray.500' }}
              />
            </InputGroup>
            <FormControl w="auto" display="flex" alignItems="center" gap={2}>
              <FormLabel htmlFor="team-selector-show-legacy" mb={0} fontSize="sm" color="gray.500" whiteSpace="nowrap" cursor="pointer">
                Show legacy
              </FormLabel>
              <Switch
                id="team-selector-show-legacy"
                size="sm"
                colorScheme="orange"
                isChecked={showLegacy}
                onChange={(e) => setShowLegacy(e.target.checked)}
              />
            </FormControl>
          </HStack>

          <SimpleGrid columns={{ base: 2, md: 3, lg: 4, xl: 5 }} spacing={4}>
            {[...players]
              .filter((p) => p.is_active === undefined || showLegacy || p.is_active)
              .filter((p) => p.name.toLowerCase().includes(searchTerm.toLowerCase()))
              .sort((a, b) => {
                // Sort by last_played date descending
                const dateA = a.last_played ? new Date(a.last_played).getTime() : 0;
                const dateB = b.last_played ? new Date(b.last_played).getTime() : 0;
                if (dateB !== dateA) return dateB - dateA;
                // If same date or both null, sort by name
                return a.name.localeCompare(b.name);
              })
              .map((player) => (
                <PlayerCard
                  key={player.id}
                  player={player}
                  isSelected={selectedPlayers.some((p) => p.id === player.id)}
                  onClick={() => onTogglePlayer(player)}
                  size="md"
                />
              ))}
          </SimpleGrid>
        </Box>
      </TacticalCard>

      {/* Add Guest Modal */}
      <Modal isOpen={isOpen} onClose={onClose} isCentered finalFocusRef={addGuestButtonRef}>
        <ModalOverlay backdropFilter="blur(8px)" />
        <ModalContent bg="space.800" border="3px solid" borderColor="space.700" borderRadius="xl">
          <ModalHeader>Add Guest Player</ModalHeader>
          <ModalBody pb={6}>
            <VStack spacing={4} align="stretch">
              <Text fontSize="sm" color="gray.400">Add a friend who hasn't played with the squad before.</Text>
              <Box>
                <Text fontSize="xs" color="gray.500" mb={1} fontWeight="bold">Name</Text>
                <Input
                  placeholder="Friend's Name"
                  value={guestName}
                  onChange={(e) => setGuestName(e.target.value)}
                  bg="space.900"
                  border="none"
                  autoFocus
                />
              </Box>
              <Box>
                <Text fontSize="xs" color="gray.500" mb={1} fontWeight="bold" fontFamily="heading" letterSpacing="wide">Starting MMR</Text>
                <Input
                  type="number"
                  placeholder="2500"
                  value={guestMMR}
                  onChange={(e) => setGuestMMR(parseInt(e.target.value) || 2500)}
                  bg="space.900"
                  border="none"
                  fontFamily="mono"
                />
                <Text fontSize="10px" color="gray.600" mt={2} textTransform="uppercase" letterSpacing="widest">
                  Baseline is 2500 (Platinum). Adjust for player skill.
                </Text>
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>Cancel</Button>
            <Button colorScheme="brand" onClick={handleAddGuest}>Add to Session</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Edit Guest Modal */}
      <Modal isOpen={isEditOpen} onClose={onEditClose} isCentered finalFocusRef={editGuestTriggerRef}>
        <ModalOverlay backdropFilter="blur(8px)" />
        <ModalContent bg="space.800" border="3px solid" borderColor="space.700" borderRadius="xl">
          <ModalHeader>Edit Guest Player</ModalHeader>
          <ModalBody pb={6}>
            <VStack spacing={4} align="stretch">
              <Box>
                <Text fontSize="xs" color="gray.500" mb={1} fontWeight="bold">Name</Text>
                <Input
                  placeholder="Friend's Name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  bg="space.900"
                  border="none"
                  autoFocus
                />
              </Box>
              <Box>
                <Text fontSize="xs" color="gray.500" mb={1} fontWeight="bold" fontFamily="heading" letterSpacing="wide">MMR</Text>
                <Input
                  type="number"
                  placeholder="2500"
                  value={editMMR}
                  onChange={(e) => setEditMMR(parseInt(e.target.value) || 2500)}
                  bg="space.900"
                  border="none"
                  fontFamily="mono"
                />
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onEditClose}>Cancel</Button>
            <Button colorScheme="brand" onClick={handleSaveEdit}>Save Changes</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Guest Players List (if any) */}
      {guestPlayers.length > 0 && (
        <Box mt={4} p={4} bg="space.800" borderRadius="lg" border="2px solid" borderColor="space.700">
          <Text fontSize="sm" fontWeight="bold" color="gray.400" mb={3}>Guest Players</Text>
          <VStack spacing={2} align="stretch">
            {guestPlayers.map((guest) => (
              <HStack key={guest.id} justify="space-between" p={2} bg="space.700" borderRadius="md">
                <HStack>
                  <Badge colorScheme="orange" variant="solid" fontSize="xs">GUEST</Badge>
                  <Text fontSize="sm" color="gray.200">{guest.name.replace(' (Guest)', '')}</Text>
                  <Badge colorScheme="blue" fontSize="xs">{guest.mmr} MMR</Badge>
                </HStack>
                <HStack spacing={1}>
                  <IconButton
                    aria-label="Edit guest"
                    icon={<FiEdit2 />}
                    size="xs"
                    variant="ghost"
                    colorScheme="blue"
                    onClick={(e) => handleOpenEdit(guest, e.currentTarget)}
                  />
                  <IconButton
                    aria-label="Delete guest"
                    icon={<FiTrash2 />}
                    size="xs"
                    variant="ghost"
                    colorScheme="red"
                    onClick={() => handleDeleteGuest(guest.id)}
                  />
                </HStack>
              </HStack>
            ))}
          </VStack>
        </Box>
      )}
    </Box>
  );
};

export default TeamSelector;
