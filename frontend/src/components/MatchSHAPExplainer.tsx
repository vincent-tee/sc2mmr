import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Tooltip,
  Heading,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { FaInfoCircle, FaArrowUp, FaArrowDown } from 'react-icons/fa';

interface SHAPImpact {
  feature: string;
  impact: number;
  magnitude: number;
}

interface MatchSHAPExplainerProps {
  impacts: SHAPImpact[];
}

const MatchSHAPExplainer: React.FC<MatchSHAPExplainerProps> = ({ impacts }) => {
  const bgColor = useColorModeValue('gray.800', 'whiteAlpha.100');
  const borderColor = useColorModeValue('whiteAlpha.300', 'whiteAlpha.200');

  const formatFeatureName = (name: string) => {
    return name
      .replace(/_diff$/, '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  if (!impacts || impacts.length === 0) {
    return null;
  }

  // Use the top 5 impacts
  const displayImpacts = impacts.slice(0, 5);

  return (
    <Box
      p={4}
      bg={bgColor}
      borderWidth="1px"
      borderColor={borderColor}
      borderRadius="lg"
      className="shap-explainer"
    >
      <HStack mb={4} spacing={2}>
        <Heading size="sm" color="whiteAlpha.900" fontFamily="heading" letterSpacing="wide">
          PREDICTION FACTORS
        </Heading>
        <Tooltip 
          label="SHAP (SHapley Additive exPlanations) values show how each factor contributed to the model's prediction. Up arrows favor Team 1, down arrows favor Team 2."
          hasArrow
          placement="top"
        >
          <Box display="inline-flex">
            <Icon as={FaInfoCircle} color="blue.400" cursor="help" />
          </Box>
        </Tooltip>
      </HStack>

      <VStack spacing={4} align="stretch">
        {displayImpacts.map((impact) => {
          const isPositive = impact.impact > 0;
          // Scale magnitude for display - SHAP values can be small, so we normalize
          const maxMagnitude = Math.max(...displayImpacts.map(i => i.magnitude));
          const normalizedValue = (impact.magnitude / maxMagnitude) * 100;
          const color = isPositive ? 'blue' : 'orange';

          return (
            <Box key={impact.feature}>
              <HStack justify="space-between" mb={1.5}>
                <HStack spacing={2}>
                  <Icon
                    as={isPositive ? FaArrowUp : FaArrowDown}
                    color={`${color}.400`}
                    w={3}
                    h={3}
                  />
                  <Text fontSize="xs" fontWeight="bold" color="whiteAlpha.800" textTransform="uppercase">
                    {formatFeatureName(impact.feature)}
                  </Text>
                </HStack>
                <Text fontSize="2xs" color="whiteAlpha.600" fontWeight="semibold">
                  {isPositive ? 'FAVORS TEAM 1' : 'FAVORS TEAM 2'}
                </Text>
              </HStack>
              <Progress
                value={normalizedValue}
                size="xs"
                colorScheme={color}
                borderRadius="full"
                bg="whiteAlpha.100"
              />
            </Box>
          );
        })}
      </VStack>
    </Box>
  );
};

export default MatchSHAPExplainer;
