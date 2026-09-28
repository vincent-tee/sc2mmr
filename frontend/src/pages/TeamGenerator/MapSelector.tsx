/**
 * MapSelector Component - optional map for tonight's game
 */
import { HStack, Icon, Select } from '@chakra-ui/react';
import { FiMap } from 'react-icons/fi';

interface MapSelectorProps {
  selectedMap: string;
  availableMaps: string[];
  onMapChange: (mapName: string) => void;
}

const MapSelector: React.FC<MapSelectorProps> = ({ selectedMap, availableMaps, onMapChange }) => (
  <HStack spacing={2}>
    <Icon as={FiMap} color="brand.400" boxSize={4} />
    <Select
      aria-label="Map"
      size="sm"
      w={{ base: '150px', md: '220px' }}
      value={selectedMap}
      onChange={(e) => onMapChange(e.target.value)}
      bg="space.900"
      borderColor="whiteAlpha.200"
      color="white"
      borderRadius="md"
      _hover={{ borderColor: 'brand.400' }}
    >
      <option value="">Any map</option>
      {availableMaps.map((map) => (
        <option key={map} value={map} style={{ backgroundColor: '#1A202C' }}>
          {map}
        </option>
      ))}
    </Select>
  </HStack>
);

export default MapSelector;
