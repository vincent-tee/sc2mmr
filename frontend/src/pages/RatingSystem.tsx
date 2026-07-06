/**
 * Rating System Transparency Page
 * Explains how the MMR system works with the Friend Squad aesthetic.
 */
import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Code,
  Divider,
  Badge,
  SimpleGrid,
  Grid,
  GridItem,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Icon,
} from '@chakra-ui/react';
import {
  FiInfo,
  FiTrendingUp,
  FiCheckCircle,
  FiActivity,
  FiTarget,
  FiClock,
  FiUsers,
} from 'react-icons/fi';
import type { IconType } from 'react-icons';
import PageHeader from '../components/PageHeader';

const RatingSystem: React.FC = () => {
  const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';
  const cardBg = 'space.800';
  const borderColor = 'space.700';

  return (
    <Box minH="100vh" pb={16}>
      <PageHeader
        kicker="Under the Hood"
        title="How the [Rating] Works"
        description="Understanding how your skill is tracked, rated, and balanced."
      />
      <Container maxW="container.xl" pt={8}>
        <VStack spacing={8} align="stretch">

          {/* Overview Alert */}
          <Alert
            status="info"
            bg="space.800"
            borderLeft="4px solid"
            borderColor="accent.400"
            borderRadius="xl"
            boxShadow={brandShadow}
            p={6}
          >
            <AlertIcon color="accent.400" />
            <Box>
              <AlertTitle color="gray.100" mb={1}>TrueSkill™ Logic</AlertTitle>
              <AlertDescription color="gray.400">
                We use the TrueSkill algorithm to track skill. Your rating isn't just a number—it's a probability curve that accounts for your consistency and experience.
              </AlertDescription>
            </Box>
          </Alert>

          {/* Main Content Tabs */}
          <Tabs variant="soft-rounded" colorScheme="brand">
            <TabList bg="space.800" p={1.5} borderRadius="full" border="2px solid" borderColor="space.700">
              <Tab borderRadius="full" px={6} fontWeight="bold">How It Works</Tab>
              <Tab borderRadius="full" px={6} fontWeight="bold">The Formula</Tab>
              <Tab borderRadius="full" px={6} fontWeight="bold">MMR Changes</Tab>
              <Tab borderRadius="full" px={6} fontWeight="bold">Configuration</Tab>
            </TabList>

            <TabPanels pt={6}>
              {/* How It Works */}
              <TabPanel p={0}>
                <VStack spacing={6} align="stretch">
                  <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={6}>
                    <Heading size="md" mb={6} fontFamily="heading">Core Concepts</Heading>
                    <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={6}>
                      <Box>
                        <HStack mb={2}>
                          <Icon as={FiCheckCircle} color="green.400" />
                          <Text fontWeight="bold">Skill (μ)</Text>
                        </HStack>
                        <Text fontSize="sm" color="gray.400">
                          The system's best guess at your true skill level. Increases when you win against strong opponents.
                        </Text>
                      </Box>
                      <Box>
                        <HStack mb={2}>
                          <Icon as={FiActivity} color="orange.400" />
                          <Text fontWeight="bold">Uncertainty (σ)</Text>
                        </HStack>
                        <Text fontSize="sm" color="gray.400">
                          How much the system trusts its guess. New players have high uncertainty; veterans have low.
                        </Text>
                      </Box>
                      <Box>
                        <HStack mb={2}>
                          <Icon as={FiTarget} color="brand.400" />
                          <Text fontWeight="bold">Visible MMR</Text>
                        </HStack>
                        <Text fontSize="sm" color="gray.400">
                          A conservative estimate that combines skill and uncertainty to give you a competitive rank.
                        </Text>
                      </Box>
                    </Grid>
                  </Box>

                  <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={6}>
                    <Heading size="md" mb={4} fontFamily="heading">Why use this?</Heading>
                    <SimpleGrid columns={{ base: 1, md: 2 }} spacingX={8} spacingY={4}>
                      {([
                        { icon: FiUsers, title: 'Natural Team Balancing', desc: 'Handles team games (2v2, 3v3, 4v4) by analyzing individual contributions to the team result.' },
                        { icon: FiTrendingUp, title: 'Uncertainty Tracking', desc: 'New players move fast through ranks until their "true" skill is found.' },
                        { icon: FiTarget, title: 'Fair Teams', desc: 'Uses your hidden metrics to create the closest matches possible, aiming for a 50% win chance.' }
                      ] as { icon: IconType; title: string; desc: string }[]).map((item, i) => (
                        <HStack key={i} align="start">
                          <Icon as={item.icon} color="accent.400" mt={1} />
                          <Box>
                            <Text fontWeight="bold" fontSize="sm">{item.title}</Text>
                            <Text fontSize="xs" color="gray.500">{item.desc}</Text>
                          </Box>
                        </HStack>
                      ))}
                    </SimpleGrid>
                  </Box>
                </VStack>
              </TabPanel>

              {/* The Formula */}
              <TabPanel p={0}>
                <VStack spacing={6} align="stretch">
                  <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={8} textAlign="center">
                    <Text fontSize="sm" color="gray.500" mb={4} fontWeight="bold" letterSpacing="widest">THE CALCULATION</Text>
                    <Box bg="space.900" p={6} borderRadius="xl" display="inline-block" border="2px dashed" borderColor="brand.500">
                      <Text fontSize="2xl" fontWeight="black" fontFamily="mono" color="brand.400">
                        MMR = 1000 + (100 × μ) - (200 × σ)
                      </Text>
                    </Box>
                    <Text mt={6} fontSize="sm" color="gray.400" maxW="600px" mx="auto">
                      We start with a baseline of 1000, add 100 points per skill level (mu), and subtract 200 points per uncertainty level (sigma).
                      This ensures that as the system gets more certain about you, your MMR stabilizes upwards.
                    </Text>
                  </Box>

                  <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={6}>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr><Th color="gray.500">Player State</Th><Th isNumeric color="gray.500">Skill (μ)</Th><Th isNumeric color="gray.500">Uncertainty (σ)</Th><Th isNumeric color="gray.500">Final MMR</Th></Tr>
                      </Thead>
                      <Tbody>
                        <Tr><Td><Badge>New Recruit</Badge></Td><Td isNumeric>25.0</Td><Td isNumeric>8.3</Td><Td isNumeric fontWeight="bold">1,840</Td></Tr>
                        <Tr><Td><Badge colorScheme="brand">Rising Star</Badge></Td><Td isNumeric>32.0</Td><Td isNumeric>3.5</Td><Td isNumeric fontWeight="bold">3,500</Td></Tr>
                        <Tr><Td><Badge colorScheme="purple">Squad Leader</Badge></Td><Td isNumeric>36.0</Td><Td isNumeric>2.5</Td><Td isNumeric fontWeight="bold" color="purple.400">4,100</Td></Tr>
                      </Tbody>
                    </Table>
                  </Box>
                </VStack>
              </TabPanel>

              {/* MMR Changes */}
              <TabPanel p={0}>
                <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={6}>
                  <Heading size="md" mb={6} fontFamily="heading">Dynamic Adjustments</Heading>
                  <Accordion allowToggle>
                    {[
                      { title: 'Winning a Match', content: 'Your skill estimate (μ) increases and uncertainty (σ) decreases. MMR typically rises by 25-75 points.' },
                      { title: 'Losing a Match', content: 'Your skill estimate (μ) decreases and uncertainty (σ) decreases. MMR typically drops by 25-75 points.' },
                      { title: 'Skill Decay', content: 'Extended inactivity increases your uncertainty (σ). While your skill stays the same, your displayed rank will become more conservative until you play again.' }
                    ].map((item, i) => (
                      <AccordionItem key={i} border="none" mb={2}>
                        <AccordionButton bg="space.700" borderRadius="lg" _hover={{ bg: 'space.600' }}>
                          <Box flex="1" textAlign="left" fontWeight="bold" fontSize="sm">{item.title}</Box>
                          <AccordionIcon />
                        </AccordionButton>
                        <AccordionPanel pb={4} color="gray.400" fontSize="sm">{item.content}</AccordionPanel>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </Box>
              </TabPanel>

              {/* Configuration */}
              <TabPanel p={0}>
                <Box bg={cardBg} border="3px solid" borderColor={borderColor} borderRadius="xl" boxShadow={brandShadow} p={6}>
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr><Th color="gray.500">System Parameter</Th><Th color="gray.500">Current Value</Th><Th color="gray.500">Description</Th></Tr>
                    </Thead>
                    <Tbody>
                      <Tr><Td fontWeight="bold">Starting Skill</Td><Td><Code>25.0</Code></Td><Td fontSize="xs" color="gray.400">Baseline for all new players</Td></Tr>
                      <Tr><Td fontWeight="bold">Starting Uncertainty</Td><Td><Code>8.333</Code></Td><Td fontSize="xs" color="gray.400">Maximum initial volatility</Td></Tr>
                      <Tr><Td fontWeight="bold">MMR Base</Td><Td><Code>1000</Code></Td><Td fontSize="xs" color="gray.400">Floor for all displayed ratings</Td></Tr>
                      <Tr><Td fontWeight="bold">Display Scale</Td><Td><Code>100x</Code></Td><Td fontSize="xs" color="gray.400">Points awarded per mu point</Td></Tr>
                      <Tr><Td fontWeight="bold">Recency Half-Life</Td><Td><Code>90 Days</Code></Td><Td fontSize="xs" color="gray.400">Recent matches count for more</Td></Tr>
                    </Tbody>
                  </Table>
                </Box>
              </TabPanel>
            </TabPanels>
          </Tabs>

          {/* Footer */}
          <Box bg="rgba(78, 205, 196, 0.1)" border="2px solid" borderColor="accent.400" borderRadius="xl" p={6}>
            <HStack align="start" spacing={4}>
              <Icon as={FiInfo} color="accent.400" boxSize={6} mt={1} />
              <VStack align="start" spacing={2}>
                <Heading size="sm">Technical Roots</Heading>
                <Text fontSize="sm" color="gray.300">
                  Developed by Microsoft Research, TrueSkill is used by global platforms like Xbox Live to provide fair matching. 
                  Our implementation is tuned specifically for our squad's play frequency and team dynamics.
                </Text>
              </VStack>
            </HStack>
          </Box>
        </VStack>
      </Container>
    </Box>
  );
};

export default RatingSystem;
