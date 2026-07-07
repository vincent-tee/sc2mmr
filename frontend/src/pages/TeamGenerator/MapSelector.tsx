/**
 * MapSelector Component - Map Affinity Selection
 * Allows users to select the current map to apply map-specific bonuses
 */
import {
  Box,
  HStack,
  VStack,
  Heading,
  Text,
  Select,
  Icon,
} from '@chakra-ui/react';
import { FiMap } from 'react-icons/fi';
import TacticalCard from '@/components/TacticalCard';

interface MapSelectorProps {
  selectedMap: string;
  availableMaps: string[];
  onMapChange: (mapName: string) => void;
}

const MapSelector: React.FC<MapSelectorProps> = ({
  selectedMap,
  availableMaps,
  onMapChange,
}) => {
  return (
    <Box 
      bg="rgba(10, 15, 28, 0.6)" 
      p={3} 
      borderRadius="xl" 
      border="1px solid" 
      borderColor="whiteAlpha.100"
      backdropFilter="blur(8px)"
    >
      <HStack spacing={4} justify="space-between">
        <HStack spacing={3}>
          <Icon as={FiMap} color="brand.400" boxSize={5} />
          <VStack align="start" spacing={0}>
            <Heading size="xs" color="gray.200" textTransform="uppercase" letterSpacing="widest">
              Map Affinity
            </Heading>
            <Text fontSize="10px" color="gray.500">
              Apply Map Specialist bonuses
            </Text>
          </VStack>
        </HStack>

        <Select
          size="sm"
          maxW="300px"
          value={selectedMap}
          onChange={(e) => onMapChange(e.target.value)}
          bg="space.900"
          borderColor="gray.700"
          color="white"
          borderRadius="md"
          _hover={{ borderColor: 'brand.400' }}
        >
          <option value="">Global Balance (No Map)</option>
          {availableMaps.map((map) => (
            <option key={map} value={map} style={{ backgroundColor: '#1A202C' }}>
              {map}
            </option>
          ))}
        </Select>
      </HStack>
    </Box>
  );
};

export default MapSelector;
