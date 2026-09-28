/**
 * Rating System Transparency Page
 * One scrolling explainer: the three numbers, the formula, how games move it, and the settings.
 */
import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Code,
  Badge,
  Grid,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Icon,
} from '@chakra-ui/react';
import { FiCheckCircle, FiActivity, FiTarget } from 'react-icons/fi';
import type { IconType } from 'react-icons';
import PageHeader from '../components/PageHeader';

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" p={{ base: 4, md: 6 }} minW={0}>
    <Heading size="md" mb={5} fontFamily="heading">{title}</Heading>
    {children}
  </Box>
);

const CONCEPTS: { icon: IconType; color: string; title: string; desc: string }[] = [
  { icon: FiCheckCircle, color: 'green.400', title: 'Skill (μ)', desc: "The system's best guess at your true skill. It rises when you win, more so against stronger opponents." },
  { icon: FiActivity, color: 'orange.400', title: 'Uncertainty (σ)', desc: 'How sure the system is about that guess. New players start high; it shrinks with every game.' },
  { icon: FiTarget, color: 'brand.400', title: 'MMR', desc: 'The one number you see everywhere: skill minus a deduction for uncertainty, so a rank has to be earned over games. Two players with the same MMR can differ in skill if one is less settled.' },
];

const CHANGES: { title: string; desc: string }[] = [
  { title: 'Win or lose', desc: 'Skill moves toward the result and uncertainty shrinks. Most games move MMR by 10–50 points. New players, players back from a long break and big upsets can move by hundreds, because their uncertainty is high and it drops quickly.' },
  { title: 'Coming back from a break', desc: 'After a long gap your uncertainty is raised when your next game is processed, so your first games back move your rating further.' },
  { title: 'Team games', desc: 'Every player on the winning team gains and every player on the losing team drops, scaled by how surprising the result was and how settled each rating already is.' },
];

const RatingSystem: React.FC = () => (
  <Box minH="100vh" pb={16}>
    <PageHeader
      kicker="Under the Hood"
      title="How the [Rating] Works"
      description="We use TrueSkill, the Microsoft Research system behind Xbox Live matchmaking, tuned for our squad."
    />
    <Container maxW="container.xl" pt={8}>
      <VStack spacing={6} align="stretch">
        <Section title="Three numbers">
          <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={6}>
            {CONCEPTS.map((concept) => (
              <Box key={concept.title}>
                <HStack mb={2}>
                  <Icon as={concept.icon} color={concept.color} />
                  <Text fontWeight="bold">{concept.title}</Text>
                </HStack>
                <Text fontSize="sm" color="gray.400">{concept.desc}</Text>
              </Box>
            ))}
          </Grid>
        </Section>

        <Grid templateColumns={{ base: '1fr', lg: '3fr 2fr' }} gap={6}>
          <Section title="The formula">
            <Box bg="space.900" p={{ base: 3, md: 5 }} borderRadius="lg" border="1px dashed" borderColor="brand.500" mb={4} textAlign="center">
              <Text fontSize={{ base: 'sm', sm: 'lg', md: '2xl' }} fontWeight="black" fontFamily="mono" color="brand.400">
                MMR = 1000 + (100 × μ) − (200 × σ)
              </Text>
            </Box>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr><Th color="gray.500">Example</Th><Th isNumeric color="gray.500">μ</Th><Th isNumeric color="gray.500">σ</Th><Th isNumeric color="gray.500">MMR</Th></Tr>
              </Thead>
              <Tbody fontFamily="mono">
                <Tr><Td fontFamily="body"><Badge>Brand new</Badge></Td><Td isNumeric>25.0</Td><Td isNumeric>8.3</Td><Td isNumeric fontWeight="bold">1,834</Td></Tr>
                <Tr><Td fontFamily="body"><Badge colorScheme="brand">Settled regular</Badge></Td><Td isNumeric>32.0</Td><Td isNumeric>3.5</Td><Td isNumeric fontWeight="bold">3,500</Td></Tr>
                <Tr><Td fontFamily="body"><Badge colorScheme="purple">Top of the ladder</Badge></Td><Td isNumeric>36.0</Td><Td isNumeric>2.5</Td><Td isNumeric fontWeight="bold" color="purple.400">4,100</Td></Tr>
              </Tbody>
            </Table>
          </Section>

          <Section title="What moves it">
            <VStack align="stretch" spacing={4}>
              {CHANGES.map((change) => (
                <Box key={change.title} borderLeft="2px solid" borderColor="accent.500" pl={4}>
                  <Text fontWeight="bold" fontSize="sm">{change.title}</Text>
                  <Text fontSize="sm" color="gray.400">{change.desc}</Text>
                </Box>
              ))}
            </VStack>
          </Section>
        </Grid>

        <Grid templateColumns={{ base: '1fr', lg: '2fr 3fr' }} gap={6}>
          <Section title="Fair teams">
            <Text fontSize="sm" color="gray.400">
              The Teams page tries every possible split of tonight's players and ranks them mostly by how
              close the predicted win chance is to 50%, using these same ratings. When you adjust a split by hand, the win chance
              and suggested swaps use the same maths.
            </Text>
          </Section>

          <Section title="Settings">
            <Table variant="simple" size="sm">
              <Tbody>
                <Tr><Td fontWeight="bold">Starting skill (μ)</Td><Td><Code>25.0</Code></Td></Tr>
                <Tr><Td fontWeight="bold">Starting uncertainty (σ)</Td><Td><Code>8.333</Code></Td></Tr>
                <Tr><Td fontWeight="bold">MMR offset</Td><Td><Code>1000</Code></Td></Tr>
                <Tr><Td fontWeight="bold">Points per μ / per σ</Td><Td><Code>+100 / −200</Code></Td></Tr>
                <Tr><Td fontWeight="bold">Stat-average half-life</Td><Td><Code>90 days</Code></Td></Tr>
              </Tbody>
            </Table>
          </Section>
        </Grid>
      </VStack>
    </Container>
  </Box>
);

export default RatingSystem;
