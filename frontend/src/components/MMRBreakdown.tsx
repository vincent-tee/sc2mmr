/**
 * Shows a player's displayed MMR as the sum the rating formula produces:
 * 1000 + skill points − uncertainty deduction.
 */
import { Box, Flex, Text } from '@chakra-ui/react';

interface MMRBreakdownProps {
  mu: number;
  sigma: number;
  mmr: number;
}

const MMR_OFFSET = 1000;
const POINTS_PER_MU = 100;

const Term: React.FC<{ value: string; label: string; detail?: string; color?: string }> = ({
  value,
  label,
  detail,
  color = 'gray.100',
}) => (
  <Box>
    <Text fontFamily="mono" fontSize={{ base: 'xl', md: '2xl' }} fontWeight="bold" color={color} lineHeight="1.1">
      {value}
    </Text>
    <Text fontSize="xs" color="gray.400">{label}</Text>
    {detail && <Text fontSize="xs" color="gray.500" fontFamily="mono">{detail}</Text>}
  </Box>
);

const Operator: React.FC<{ symbol: string }> = ({ symbol }) => (
  <Text fontFamily="mono" fontSize="xl" color="gray.600" alignSelf="flex-start">{symbol}</Text>
);

const MMRBreakdown: React.FC<MMRBreakdownProps> = ({ mu, sigma, mmr }) => {
  const shownMMR = Math.round(mmr);
  const skillPoints = Math.round(POINTS_PER_MU * mu);
  const uncertaintyDeduction = MMR_OFFSET + skillPoints - shownMMR;

  return (
    <Box bg="space.800" borderRadius="xl" border="1px solid" borderColor="whiteAlpha.100" p={5} h="100%">
      <Text color="gray.400" fontFamily="heading" letterSpacing="wide" fontSize="sm" mb={3}>
        How this MMR adds up
      </Text>
      <Flex align="flex-start" gap={{ base: 2, md: 3 }} flexWrap="wrap">
        <Term value={MMR_OFFSET.toLocaleString()} label="start" />
        <Operator symbol="+" />
        <Term value={skillPoints.toLocaleString()} label="skill" detail={`μ ${mu.toFixed(1)}`} color="shield.400" />
        <Operator symbol="−" />
        <Term value={uncertaintyDeduction.toLocaleString()} label="uncertainty" detail={`σ ${sigma.toFixed(2)}`} color="purple.300" />
        <Operator symbol="=" />
        <Term value={shownMMR.toLocaleString()} label="MMR" color="brand.400" />
      </Flex>
      <Text fontSize="xs" color="gray.500" mt={3}>
        Uncertainty (σ) shrinks with every game; a lower σ means a more settled rating and a smaller deduction.
      </Text>
    </Box>
  );
};

export default MMRBreakdown;
