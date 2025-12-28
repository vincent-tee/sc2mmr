/**
 * BalanceControls Component - Impact-Aware Balancing Configuration
 * Allows users to configure team balancing with impact weight settings
 */
import {
  Box,
  Collapse,
  Divider,
  HStack,
  VStack,
  Heading,
  Text,
  Badge,
  Icon,
  Switch,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Tooltip,
} from '@chakra-ui/react';
import { FiActivity } from 'react-icons/fi';
import TacticalCard from '@/components/TacticalCard';
import type { ChangeEvent } from 'react';

interface BalanceControlsProps {
  useImpactBalance: boolean;
  impactWeight: number;
  onUseImpactBalanceChange: (checked: boolean) => void;
  onImpactWeightChange: (value: number) => void;
}

const BalanceControls: React.FC<BalanceControlsProps> = ({
  useImpactBalance,
  impactWeight,
  onUseImpactBalanceChange,
  onImpactWeightChange,
}) => {
  return (
    <TacticalCard glowColor="rgba(138, 43, 226, 0.4)">
      <Box p={2}>
        <VStack spacing={6} align="stretch">
          <HStack justify="space-between">
            <HStack>
              <Icon as={FiActivity} color="purple.400" boxSize={6} filter="drop-shadow(2px 2px 0 var(--chakra-colors-space-900))" />
              <Heading
                size="md"
                fontFamily="heading"
                fontWeight="black"
                letterSpacing="wider"
                color="purple.300"
              >
                Impact-Aware Balancing
              </Heading>
            </HStack>
            <Switch
              isChecked={useImpactBalance}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                onUseImpactBalanceChange(e.target.checked)
              }
              size="lg"
              colorScheme="purple"
            />
          </HStack>

          <Text fontSize="md" color="gray.400" fontFamily="body" fontWeight="medium">
            Distribute high-impact players (shot callers, strong players) and
            low-impact players (learning, weaker) evenly across teams.
          </Text>

          <Collapse in={useImpactBalance} animateOpacity>
            <VStack spacing={4} align="stretch">
              <Divider borderColor="whiteAlpha.200" />
              <Box>
                <HStack justify="space-between" mb={3}>
                  <Text
                    fontSize="sm"
                    color="gray.400"
                    fontFamily="heading"
                  >
                    Impact Weight
                  </Text>
                  <Badge
                    colorScheme="purple"
                    fontSize="md"
                    px={3}
                    py={1}
                    fontFamily="heading"
                  >
                    {(impactWeight * 100).toFixed(0)}%
                  </Badge>
                </HStack>
                <Slider
                  value={impactWeight}
                  onChange={onImpactWeightChange}
                  min={0}
                  max={1}
                  step={0.1}
                  colorScheme="purple"
                >
                  <SliderTrack bg="whiteAlpha.200">
                    <SliderFilledTrack bg="purple.500" />
                  </SliderTrack>
                  <Tooltip
                    label={`${(impactWeight * 100).toFixed(0)}%`}
                    placement="top"
                    isOpen={false}
                  >
                    <SliderThumb boxSize={6} bg="purple.400" />
                  </Tooltip>
                </Slider>
                <HStack justify="space-between" mt={2}>
                  <Text fontSize="xs" color="gray.500" fontFamily="heading">
                    Pure MMR Balance
                  </Text>
                  <Text
                    fontSize="xs"
                    color="purple.400"
                    fontWeight="bold"
                    fontFamily="heading"
                  >
                    {impactWeight === 0.5 ? 'Balanced' : ''}
                  </Text>
                  <Text fontSize="xs" color="gray.500" fontFamily="heading">
                    Pure Impact Balance
                  </Text>
                </HStack>
              </Box>
            </VStack>
          </Collapse>
        </VStack>
      </Box>
    </TacticalCard>
  );
};

export default BalanceControls;
