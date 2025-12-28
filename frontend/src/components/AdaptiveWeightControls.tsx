/**
 * AdaptiveWeightControls - Configure ML metrics weights with auto/manual toggle
 * Features hover tooltips explaining each weight component
 */
import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Badge,
  Switch,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Progress,
  Alert,
  AlertIcon,
  AlertTitle,
  Tooltip,
  Divider,
  Icon,
} from '@chakra-ui/react';
import { FiActivity, FiInfo } from 'react-icons/fi';

// Weight explanations for hover tooltips
const WEIGHT_EXPLANATIONS: Record<string, {
  title: string;
  description: string;
  example: string;
}> = {
  session_mmr: {
    title: 'Session-Weighted MMR',
    description: 'Recent matches (last 4 hours) count 3x more than older matches. Adapts fast to player improvement or decline.',
    example: 'If you played 10 matches yesterday but are crushing it today, session MMR reflects your current skill level immediately.',
  },
  combat: {
    title: 'Combat Score',
    description: 'Historical combat performance from match analysis. Measures damage dealing, fight participation, and army engagement efficiency.',
    example: 'High combat score indicates player consistently wins fights and deals effective damage.',
  },
  economic: {
    title: 'Economic Score',
    description: 'Resource collection and army value building from match analysis. Measures economy management and spending efficiency.',
    example: 'High economic score indicates player gets good income and spends efficiently on units.',
  },
  efficiency: {
    title: 'Efficiency',
    description: 'Damage dealt per resource spent (DPS per mineral). Measures how much value player gets from army investment.',
    example: 'High efficiency means player deals massive damage with fewer resources spent.',
  },
};

const COMPONENTS = [
  { key: 'session_mmr', label: 'Session MMR', color: 'brand' },
  { key: 'combat', label: 'Combat Score', color: 'orange' },
  { key: 'economic', label: 'Economic Score', color: 'green' },
  { key: 'efficiency', label: 'Efficiency', color: 'blue' },
] as const;

interface AdaptiveWeightControlsProps {
  isVisible: boolean;
  weights: Record<string, number>;
  accuracies: Record<string, number>;
  isAdaptive: boolean;
  onToggleAdaptive: () => void;
  onManualWeightChange: (component: string, value: number) => void;
}

const AdaptiveWeightControls: React.FC<AdaptiveWeightControlsProps> = ({
  isVisible,
  weights,
  accuracies,
  isAdaptive,
  onToggleAdaptive,
  onManualWeightChange,
}) => {
  if (!isVisible) return null;

  return (
    <Box
      bg="space.800"
      border="2px solid"
      borderColor="gray.700"
      borderRadius="lg"
      p={5}
      mt={4}
    >
      <VStack align="stretch" spacing={5}>
        {/* Header */}
        <HStack justify="space-between">
          <HStack>
            <Icon as={FiActivity} color="purple.400" boxSize={5} />
            <Heading size="md" color="white">
              ML Metrics Configuration
            </Heading>
          </HStack>
          <HStack spacing={3}>
            <Text fontSize="sm" color="gray.400">
              {isAdaptive ? 'Auto Weights' : 'Manual Override'}
            </Text>
            <Switch
              isChecked={isAdaptive}
              onChange={onToggleAdaptive}
              size="md"
              colorScheme="purple"
            />
          </HStack>
        </HStack>

        {/* Mode explanation */}
        {isAdaptive ? (
          <Alert status="info" variant="subtle" borderRadius="md">
            <AlertIcon />
            <VStack align="start" spacing={1}>
              <AlertTitle fontSize="sm">Adaptive Weights Active</AlertTitle>
              <Text fontSize="xs" color="gray.300">
                Weights automatically adjust based on prediction accuracy (EMA with alpha=0.1).
                Recent predictions have more influence. Hover over components to see what they measure.
              </Text>
            </VStack>
          </Alert>
        ) : (
          <Alert status="warning" variant="subtle" borderRadius="md">
            <AlertIcon />
            <VStack align="start" spacing={1}>
              <AlertTitle fontSize="sm">Manual Override Active</AlertTitle>
              <Text fontSize="xs" color="gray.300">
                Adjusting sliders will override adaptive weights.{' '}
                <Text as="span" color="brand.400" fontWeight="bold">
                  Hover over components for explanations.
                </Text>{' '}
                <Text as="span" color="brand.400" fontWeight="bold">
                  Toggle switch to re-enable adaptive mode.
                </Text>
              </Text>
            </VStack>
          </Alert>
        )}

        {/* Weights with tooltips */}
        <VStack align="stretch" spacing={3}>
          {COMPONENTS.map((comp) => {
            const weight = weights[comp.key] || 0;
            const accuracy = accuracies[comp.key] || 0.5;
            const weightPercent = Math.round(weight * 100);
            const accuracyPercent = Math.round(accuracy * 100);
            const explanation = WEIGHT_EXPLANATIONS[comp.key];

            return (
              <Tooltip
                key={comp.key}
                hasArrow
                placement="top"
                bg="space.700"
                color="white"
                borderRadius="lg"
                px={4}
                py={3}
                maxW="350px"
                label={
                  <VStack align="start" spacing={2}>
                    <Text fontWeight="bold" color="brand.300" fontSize="sm">
                      {explanation.title}
                    </Text>
                    <Text fontSize="xs" color="gray.200" lineHeight="tall">
                      {explanation.description}
                    </Text>
                    <Divider borderColor="whiteAlpha.200" />
                    <HStack>
                      <Icon as={FiInfo} color="gray.400" boxSize={3} />
                      <Text fontSize="xs" color="gray.400" fontStyle="italic">
                        {explanation.example}
                      </Text>
                    </HStack>
                  </VStack>
                }
              >
                <Box
                  p={3}
                  bg="space.900"
                  borderRadius="md"
                  borderLeft="3px solid"
                  borderColor={`${comp.color}.400`}
                  cursor="pointer"
                  transition="all 0.2s"
                  _hover={{ bg: 'space.700' }}
                >
                  <HStack justify="space-between" mb={2}>
                    <Text fontSize="sm" fontWeight="bold" color="white">
                      {comp.label}
                    </Text>
                    <HStack spacing={2}>
                      <Badge
                        colorScheme={accuracy > 0.7 ? 'green' : accuracy > 0.65 ? 'yellow' : 'red'}
                        size="sm"
                      >
                        {accuracyPercent}% accurate
                      </Badge>
                    </HStack>
                  </HStack>

                  {isAdaptive ? (
                    /* Read-only progress bar */
                    <Box position="relative">
                      <Progress
                        value={weightPercent}
                        colorScheme={comp.color}
                        size="lg"
                        borderRadius="full"
                        bg="whiteAlpha.200"
                      />
                      <Text
                        position="absolute"
                        right={2}
                        top="50%"
                        transform="translateY(-50%)"
                        fontSize="xs"
                        fontWeight="bold"
                        color="white"
                      >
                        {weightPercent}%
                      </Text>
                    </Box>
                  ) : (
                    /* Editable slider */
                    <Box>
                      <Slider
                        value={weight}
                        onChange={(val) => onManualWeightChange(comp.key, val)}
                        min={0}
                        max={1}
                        step={0.05}
                        colorScheme={comp.color}
                      >
                        <SliderTrack bg="whiteAlpha.200">
                          <SliderFilledTrack bg={`${comp.color}.400`} />
                        </SliderTrack>
                        <SliderThumb boxSize={5} bg={`${comp.color}.300`} />
                      </Slider>
                      <HStack justify="space-between" mt={1}>
                        <Text fontSize="xs" color="gray.500">
                          0%
                        </Text>
                        <Text fontSize="xs" fontWeight="bold" color={`${comp.color}.300`}>
                          {weightPercent}%
                        </Text>
                        <Text fontSize="xs" color="gray.500">
                          100%
                        </Text>
                      </HStack>
                    </Box>
                  )}
                </Box>
              </Tooltip>
            );
          })}
        </VStack>

        {/* Footer */}
        <Text fontSize="xs" color="gray.500" fontStyle="italic">
          {isAdaptive
            ? 'Weights optimize automatically based on prediction accuracy across all match history. Hover over components to see what they measure.'
            : 'Manual weights will persist until you re-enable adaptive mode. Hover over components for explanations.'}
        </Text>
      </VStack>
    </Box>
  );
};

export default AdaptiveWeightControls;
