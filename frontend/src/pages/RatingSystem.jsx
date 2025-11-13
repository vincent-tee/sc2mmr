/**
 * Rating System Transparency Page
 * Explains how the MMR system works and shows configuration
 */
import { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardHeader,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Code,
  Divider,
  Badge,
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
  useColorModeValue,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  List,
  ListItem,
  ListIcon,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
} from '@chakra-ui/react';
import {
  FiInfo,
  FiTrendingUp,
  FiCheckCircle,
  FiActivity,
  FiTarget,
  FiClock,
} from 'react-icons/fi';

const RatingSystem = () => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const codeBg = useColorModeValue('gray.100', 'gray.900');

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="xl" mb={2}>
            Rating System Transparency
          </Heading>
          <Text color="gray.500" fontSize="lg">
            Understanding how your MMR is calculated and updated
          </Text>
        </Box>

        {/* Overview Alert */}
        <Alert
          status="info"
          variant="left-accent"
          borderRadius="md"
          flexDirection="column"
          alignItems="start"
        >
          <HStack mb={2}>
            <AlertIcon />
            <AlertTitle>TrueSkill-Based Rating System</AlertTitle>
          </HStack>
          <AlertDescription>
            This system uses Microsoft's TrueSkill algorithm adapted for team-based StarCraft 2 matches.
            Your skill is represented as a probability distribution (mean and uncertainty) rather than a single number.
          </AlertDescription>
        </Alert>

        {/* Main Tabs */}
        <Tabs variant="enclosed" colorScheme="brand">
          <TabList>
            <Tab>
              <HStack>
                <FiInfo />
                <Text>How It Works</Text>
              </HStack>
            </Tab>
            <Tab>
              <HStack>
                <FiActivity />
                <Text>MMR Formula</Text>
              </HStack>
            </Tab>
            <Tab>
              <HStack>
                <FiTrendingUp />
                <Text>Rating Changes</Text>
              </HStack>
            </Tab>
            <Tab>
              <HStack>
                <FiTarget />
                <Text>Configuration</Text>
              </HStack>
            </Tab>
          </TabList>

          <TabPanels>
            {/* How It Works Tab */}
            <TabPanel>
              <VStack spacing={6} align="stretch">
                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">Core Concepts</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      <Box>
                        <Heading size="sm" mb={2}>
                          <HStack>
                            <FiCheckCircle color="green" />
                                <Text>Mu (μ) - Skill Estimate</Text>
                          </HStack>
                        </Heading>
                        <Text color="gray.600">
                          Represents the system's best guess at your true skill level.
                          Starts at <Code>25.0</Code> for new players and adjusts based on match results.
                        </Text>
                      </Box>

                      <Divider />

                      <Box>
                        <Heading size="sm" mb={2}>
                          <HStack>
                            <FiActivity color="orange" />
                            <Text>Sigma (σ) - Uncertainty</Text>
                          </HStack>
                        </Heading>
                        <Text color="gray.600">
                          Measures how confident the system is about your skill estimate.
                          Starts at <Code>8.333</Code> for new players and decreases as you play more games.
                          Lower sigma = more certain about your skill level.
                        </Text>
                      </Box>

                      <Divider />

                      <Box>
                        <Heading size="sm" mb={2}>
                          <HStack>
                            <FiTarget color="blue" />
                            <Text>Displayed MMR</Text>
                          </HStack>
                        </Heading>
                        <Text color="gray.600">
                          The MMR number you see combines both mu and sigma using a scaled formula
                          to provide an intuitive rating in the range of ~800-2200.
                        </Text>
                      </Box>
                    </VStack>
                  </CardBody>
                </Card>

                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">Why This System?</Heading>
                  </CardHeader>
                  <CardBody>
                    <List spacing={3}>
                      <ListItem>
                        <HStack align="start">
                          <ListIcon as={FiCheckCircle} color="green.500" mt={1} />
                          <Box>
                            <Text fontWeight="semibold">Handles Team Games Naturally</Text>
                            <Text fontSize="sm" color="gray.600">
                              TrueSkill was designed for team-based games and handles 2v2-5v5 matches effectively
                            </Text>
                          </Box>
                        </HStack>
                      </ListItem>

                      <ListItem>
                        <HStack align="start">
                          <ListIcon as={FiCheckCircle} color="green.500" mt={1} />
                          <Box>
                            <Text fontWeight="semibold">Uncertainty Tracking</Text>
                            <Text fontSize="sm" color="gray.600">
                              New players start with high uncertainty, so wins/losses have bigger impact.
                              As you play more, the system becomes more confident and changes are smaller.
                            </Text>
                          </Box>
                        </HStack>
                      </ListItem>

                      <ListItem>
                        <HStack align="start">
                          <ListIcon as={FiCheckCircle} color="green.500" mt={1} />
                          <Box>
                            <Text fontWeight="semibold">Balanced Matches</Text>
                            <Text fontSize="sm" color="gray.600">
                              The team balancer uses your rating to create fair teams with ~50% win probability
                            </Text>
                          </Box>
                        </HStack>
                      </ListItem>

                      <ListItem>
                        <HStack align="start">
                          <ListIcon as={FiCheckCircle} color="green.500" mt={1} />
                          <Box>
                            <Text fontWeight="semibold">Recency Weighting</Text>
                            <Text fontSize="sm" color="gray.600">
                              Recent matches are weighted more heavily to reflect your current skill level
                            </Text>
                          </Box>
                        </HStack>
                      </ListItem>
                    </List>
                  </CardBody>
                </Card>
              </VStack>
            </TabPanel>

            {/* MMR Formula Tab */}
            <TabPanel>
              <VStack spacing={6} align="stretch">
                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">MMR Calculation Formula</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      <Box
                        bg={codeBg}
                        p={4}
                        borderRadius="md"
                        borderLeft="4px"
                        borderColor="brand.500"
                      >
                        <Text fontFamily="mono" fontSize="lg" fontWeight="bold">
                          MMR = 1000 + (40 × μ) - (120 × σ)
                        </Text>
                      </Box>

                      <Table variant="simple" size="sm">
                        <Thead>
                          <Tr>
                            <Th>Variable</Th>
                            <Th>Description</Th>
                            <Th isNumeric>Default</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          <Tr>
                            <Td fontFamily="mono">μ (mu)</Td>
                            <Td>Skill estimate</Td>
                            <Td isNumeric>25.0</Td>
                          </Tr>
                          <Tr>
                            <Td fontFamily="mono">σ (sigma)</Td>
                            <Td>Uncertainty</Td>
                            <Td isNumeric>8.333</Td>
                          </Tr>
                        </Tbody>
                      </Table>
                    </VStack>
                  </CardBody>
                </Card>

                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">Example MMR Values</Heading>
                  </CardHeader>
                  <CardBody>
                    <Table variant="simple">
                      <Thead>
                        <Tr>
                          <Th>Scenario</Th>
                          <Th isNumeric>μ (mu)</Th>
                          <Th isNumeric>σ (sigma)</Th>
                          <Th isNumeric>MMR</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        <Tr>
                          <Td>
                            <Badge>New Player</Badge>
                          </Td>
                          <Td isNumeric>25.0</Td>
                          <Td isNumeric>8.333</Td>
                          <Td isNumeric fontWeight="bold">
                            1000
                          </Td>
                        </Tr>
                        <Tr>
                          <Td>After 5 wins</Td>
                          <Td isNumeric>28.5</Td>
                          <Td isNumeric>6.2</Td>
                          <Td isNumeric fontWeight="bold">
                            1396
                          </Td>
                        </Tr>
                        <Tr>
                          <Td>Experienced winner</Td>
                          <Td isNumeric>32.0</Td>
                          <Td isNumeric>3.5</Td>
                          <Td isNumeric fontWeight="bold">
                            1860
                          </Td>
                        </Tr>
                        <Tr>
                          <Td>
                            <Badge colorScheme="purple">Highly Skilled</Badge>
                          </Td>
                          <Td isNumeric>38.0</Td>
                          <Td isNumeric>2.5</Td>
                          <Td isNumeric fontWeight="bold" color="purple.500">
                            2220
                          </Td>
                        </Tr>
                        <Tr>
                          <Td>After 5 losses</Td>
                          <Td isNumeric>21.5</Td>
                          <Td isNumeric>6.2</Td>
                          <Td isNumeric fontWeight="bold">
                            616
                          </Td>
                        </Tr>
                      </Tbody>
                    </Table>
                  </CardBody>
                </Card>

                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">Why This Formula?</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={3} align="stretch">
                      <Text>
                        The formula <Code>1000 + (40 × μ) - (120 × σ)</Code> provides several benefits:
                      </Text>
                      <List spacing={2} ml={4}>
                        <ListItem>
                          <HStack>
                            <ListIcon as={FiCheckCircle} color="green.500" />
                            <Text>
                              <Text as="span" fontWeight="bold">Intuitive Range:</Text> MMR values roughly
                              match familiar systems like Elo (~800-2200)
                            </Text>
                          </HStack>
                        </ListItem>
                        <ListItem>
                          <HStack>
                            <ListIcon as={FiCheckCircle} color="green.500" />
                            <Text>
                              <Text as="span" fontWeight="bold">Visible Differences:</Text> Players of different
                              skill levels have meaningfully different MMR values
                            </Text>
                          </HStack>
                        </ListItem>
                        <ListItem>
                          <HStack>
                            <ListIcon as={FiCheckCircle} color="green.500" />
                            <Text>
                              <Text as="span" fontWeight="bold">Uncertainty Penalty:</Text> Higher uncertainty
                              reduces displayed MMR (conservative estimate)
                            </Text>
                          </HStack>
                        </ListItem>
                      </List>
                    </VStack>
                  </CardBody>
                </Card>
              </VStack>
            </TabPanel>

            {/* Rating Changes Tab */}
            <TabPanel>
              <VStack spacing={6} align="stretch">
                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">How Ratings Change After Matches</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      <Accordion allowToggle>
                        <AccordionItem>
                          <h2>
                            <AccordionButton>
                              <Box flex="1" textAlign="left" fontWeight="semibold">
                                Winning a Match
                              </Box>
                              <AccordionIcon />
                            </AccordionButton>
                          </h2>
                          <AccordionPanel>
                            <VStack spacing={3} align="stretch">
                              <Text>
                                <Text as="span" fontWeight="bold">μ increases:</Text> Your skill estimate goes up
                              </Text>
                              <Text>
                                <Text as="span" fontWeight="bold">σ decreases:</Text> The system becomes more certain about your skill
                              </Text>
                              <Text color="gray.600" fontSize="sm">
                                Typical MMR gain: +15 to +50 points depending on opponent strength and your uncertainty
                              </Text>
                            </VStack>
                          </AccordionPanel>
                        </AccordionItem>

                        <AccordionItem>
                          <h2>
                            <AccordionButton>
                              <Box flex="1" textAlign="left" fontWeight="semibold">
                                Losing a Match
                              </Box>
                              <AccordionIcon />
                            </AccordionButton>
                          </h2>
                          <AccordionPanel>
                            <VStack spacing={3} align="stretch">
                              <Text>
                                <Text as="span" fontWeight="bold">μ decreases:</Text> Your skill estimate goes down
                              </Text>
                              <Text>
                                <Text as="span" fontWeight="bold">σ decreases:</Text> The system becomes more certain about your skill
                              </Text>
                              <Text color="gray.600" fontSize="sm">
                                Typical MMR loss: -15 to -50 points depending on opponent strength and your uncertainty
                              </Text>
                            </VStack>
                          </AccordionPanel>
                        </AccordionItem>

                        <AccordionItem>
                          <h2>
                            <AccordionButton>
                              <Box flex="1" textAlign="left" fontWeight="semibold">
                                New Player Bonus
                              </Box>
                              <AccordionIcon />
                            </AccordionButton>
                          </h2>
                          <AccordionPanel>
                            <VStack spacing={3} align="stretch">
                              <Text>
                                New players have high σ (uncertainty), which means:
                              </Text>
                              <List spacing={2} ml={4}>
                                <ListItem>
                                  <ListIcon as={FiTrendingUp} color="blue.500" />
                                  Larger MMR swings per match (~30-80 points)
                                </ListItem>
                                <ListItem>
                                  <ListIcon as={FiTrendingUp} color="blue.500" />
                                  Faster convergence to true skill level
                                </ListItem>
                                <ListItem>
                                  <ListIcon as={FiTrendingUp} color="blue.500" />
                                  After ~10-15 games, changes become more stable
                                </ListItem>
                              </List>
                            </VStack>
                          </AccordionPanel>
                        </AccordionItem>

                        <AccordionItem>
                          <h2>
                            <AccordionButton>
                              <Box flex="1" textAlign="left" fontWeight="semibold">
                                <HStack>
                                  <FiClock />
                                  <Text>Skill Decay (Inactivity)</Text>
                                </HStack>
                              </Box>
                              <AccordionIcon />
                            </AccordionButton>
                          </h2>
                          <AccordionPanel>
                            <VStack spacing={3} align="stretch">
                              <Text>
                                If you don't play for a while:
                              </Text>
                              <List spacing={2} ml={4}>
                                <ListItem>
                                  <ListIcon as={FiClock} color="orange.500" />
                                  σ (uncertainty) increases gradually (0.0833 per day)
                                </ListItem>
                                <ListItem>
                                  <ListIcon as={FiClock} color="orange.500" />
                                  μ (skill) stays the same
                                </ListItem>
                                <ListItem>
                                  <ListIcon as={FiClock} color="orange.500" />
                                  This results in slightly lower displayed MMR
                                </ListItem>
                                <ListItem>
                                  <ListIcon as={FiClock} color="orange.500" />
                                  σ caps at 8.333 (starting uncertainty)
                                </ListItem>
                              </List>
                              <Text fontSize="sm" color="gray.600">
                                This models potential skill deterioration from not playing
                              </Text>
                            </VStack>
                          </AccordionPanel>
                        </AccordionItem>
                      </Accordion>
                    </VStack>
                  </CardBody>
                </Card>

                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">Match Impact Factors</Heading>
                  </CardHeader>
                  <CardBody>
                    <Table variant="simple">
                      <Thead>
                        <Tr>
                          <Th>Factor</Th>
                          <Th>Impact on Rating Change</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        <Tr>
                          <Td fontWeight="semibold">Opponent Strength</Td>
                          <Td>Win vs stronger team = bigger gain. Lose vs weaker team = bigger loss</Td>
                        </Tr>
                        <Tr>
                          <Td fontWeight="semibold">Your Uncertainty</Td>
                          <Td>Higher σ = larger MMR swings</Td>
                        </Tr>
                        <Tr>
                          <Td fontWeight="semibold">Game Mode</Td>
                          <Td>All modes (2v2-5v5) use same algorithm</Td>
                        </Tr>
                        <Tr>
                          <Td fontWeight="semibold">Team Performance</Td>
                          <Td>Individual skill extracted from team result</Td>
                        </Tr>
                      </Tbody>
                    </Table>
                  </CardBody>
                </Card>
              </VStack>
            </TabPanel>

            {/* Configuration Tab */}
            <TabPanel>
              <VStack spacing={6} align="stretch">
                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">TrueSkill Configuration</Heading>
                  </CardHeader>
                  <CardBody>
                    <Table variant="simple">
                      <Thead>
                        <Tr>
                          <Th>Parameter</Th>
                          <Th>Value</Th>
                          <Th>Description</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        <Tr>
                          <Td fontFamily="mono">mu (μ)</Td>
                          <Td><Code>25.0</Code></Td>
                          <Td>Initial skill estimate for new players</Td>
                        </Tr>
                        <Tr>
                          <Td fontFamily="mono">sigma (σ)</Td>
                          <Td><Code>8.333</Code></Td>
                          <Td>Initial uncertainty for new players</Td>
                        </Tr>
                        <Tr>
                          <Td fontFamily="mono">beta (β)</Td>
                          <Td><Code>4.166</Code></Td>
                          <Td>Skill class width (half of sigma)</Td>
                        </Tr>
                        <Tr>
                          <Td fontFamily="mono">tau (τ)</Td>
                          <Td><Code>0.0833</Code></Td>
                          <Td>Skill decay per day of inactivity</Td>
                        </Tr>
                        <Tr>
                          <Td fontFamily="mono">draw_probability</Td>
                          <Td><Code>0.0</Code></Td>
                          <Td>SC2 has no draws</Td>
                        </Tr>
                      </Tbody>
                    </Table>
                  </CardBody>
                </Card>

                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">Recency Weighting</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      <HStack justify="space-between">
                        <Stat>
                          <StatLabel>Enabled</StatLabel>
                          <StatNumber>
                            <Badge colorScheme="green" fontSize="lg">YES</Badge>
                          </StatNumber>
                          <StatHelpText>Recent matches weighted more</StatHelpText>
                        </Stat>

                        <Stat>
                          <StatLabel>Half-Life</StatLabel>
                          <StatNumber>60 days</StatNumber>
                          <StatHelpText>Match from 60 days ago = 50% weight</StatHelpText>
                        </Stat>
                      </HStack>

                      <Divider />

                      <Box>
                        <Heading size="sm" mb={2}>How It Works</Heading>
                        <Text fontSize="sm" color="gray.600">
                          Your "recency-weighted MMR" gives more importance to recent matches.
                          A match from today has 100% weight, a match from 60 days ago has 50% weight,
                          and a match from 120 days ago has 25% weight. This better reflects current skill.
                        </Text>
                      </Box>
                    </VStack>
                  </CardBody>
                </Card>

                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">MMR Display Settings</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      <HStack justify="space-between">
                        <Stat>
                          <StatLabel>Rounding</StatLabel>
                          <StatNumber>1 decimal</StatNumber>
                          <StatHelpText>MMR shown as 1234.5</StatHelpText>
                        </Stat>

                        <Stat>
                          <StatLabel>Win Rate Format</StatLabel>
                          <StatNumber>Percentage</StatNumber>
                          <StatHelpText>Shown as 62.5%</StatHelpText>
                        </Stat>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>

                <Alert status="warning" borderRadius="md">
                  <AlertIcon />
                  <Box>
                    <AlertTitle>Configuration is Fixed</AlertTitle>
                    <AlertDescription>
                      These parameters are currently fixed to ensure fair and consistent ratings across all players.
                      Changing them would require recalculating all historical ratings.
                    </AlertDescription>
                  </Box>
                </Alert>
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>

        {/* Footer Note */}
        <Card bg={cardBg} borderColor="brand.500" borderWidth={2}>
          <CardBody>
            <VStack spacing={3} align="start">
              <HStack>
                <FiInfo />
                <Heading size="sm">Learn More</Heading>
              </HStack>
              <Text fontSize="sm">
                TrueSkill was developed by Microsoft Research for ranking and matchmaking in multiplayer games.
                It's used in Xbox Live and is particularly well-suited for team-based games like StarCraft 2.
              </Text>
              <Text fontSize="sm" color="gray.600">
                For technical details, see:{' '}
                <Text
                  as="a"
                  href="https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/"
                  target="_blank"
                  color="brand.500"
                  textDecoration="underline"
                >
                  Microsoft Research - TrueSkill
                </Text>
              </Text>
            </VStack>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};

export default RatingSystem;
