# Frontend Restructure - Living Model Dashboard

## Problem

With **10 games per 2 weeks**, model updates are infrequent. The frontend needs to:
1. Show model evolution very clearly (even with sparse updates)
2. Highlight what changed after each session
3. Make learning visible and exciting
4. Help user understand what the AI is learning

Current AI Model page is good for weight optimization, but doesn't show:
- Model version history and evolution
- Win probability blending stats
- Feature importance changes over time
- AI-suggested features waiting for implementation

---

## Proposed Structure

### **New Unified Page: "Living Model"**

Instead of separate pages, create one comprehensive dashboard that tells the story of model improvement:

```
/adaptive-model  →  Living Model Dashboard

┌─────────────────────────────────────────────────────────────┐
│  🧠 LIVING MODEL DASHBOARD                                  │
│  "Your AI is learning from your gameplay"                   │
└─────────────────────────────────────────────────────────────┘

├─ SECTION 1: Model Evolution Timeline (Top)
│  └─ Visual timeline showing model versions and improvements
│
├─ SECTION 2: Current Performance (Left Column)
│  ├─ Win prediction accuracy
│  ├─ Blending statistics
│  └─ Upset detection rate
│
├─ SECTION 3: What's Changing (Right Column)
│  ├─ Weight adjustments this version
│  ├─ Feature importance rankings
│  └─ Recent learning activity
│
├─ SECTION 4: AI Suggestions (Bottom - Highlighted)
│  ├─ Pending weight updates
│  ├─ Proposed new features
│  └─ Implementation status
│
└─ SECTION 5: Your Input (Interactive)
   ├─ Manual feature suggestion form
   ├─ Pattern annotation tool
   └─ "What did you notice?" feedback
```

---

## Section Breakdown

### **Section 1: Model Evolution Timeline**

```jsx
<Timeline>
  {/* Show model versions over time */}
  <TimelineNode version="v1.0" date="Jan 1" replays={162} active={false}>
    <Badge>Baseline</Badge>
    <Stats>
      - 65% accuracy
      - 4 features
      - Combat weight: 40%
    </Stats>
  </TimelineNode>

  <TimelineNode version="v1.1" date="Jan 15" replays={172} active={false}>
    <Badge colorScheme="green">+3% accuracy</Badge>
    <Changes>
      ✓ Combat weight: 40% → 45%
      ✓ Map synergy added
      ✓ Upset detection improved
    </Changes>
  </TimelineNode>

  <TimelineNode version="v1.2" date="Feb 1" replays={182} active={true}>
    <Badge colorScheme="purple">Current</Badge>
    <Stats>
      - 71% accuracy (+6% total)
      - 5 features
      - 23 upsets detected
    </Stats>
  </TimelineNode>

  <TimelineNode version="v1.3" date="Future" experimental={true}>
    <Badge colorScheme="cyan">Testing</Badge>
    <Text>Early aggression feature (20% traffic)</Text>
  </TimelineNode>
</Timeline>
```

**Why:** With 2-week gaps between updates, make each version change VERY visible.

---

### **Section 2: Current Performance (Left Column)**

```jsx
<VStack spacing={6}>
  {/* Overall Accuracy */}
  <StatCard>
    <StatLabel>Win Prediction Accuracy</StatLabel>
    <StatNumber fontSize="5xl">71.2%</StatNumber>
    <StatArrow type="increase" />
    <StatHelpText>+3.1% from v1.1 (10 games ago)</StatHelpText>

    <Progress value={71.2} colorScheme="green" />
    <Text fontSize="xs" color="gray.500">
      Target: 75% (4 more percentage points)
    </Text>
  </StatCard>

  {/* Blending Stats */}
  <StatCard bg="linear-gradient(135deg, rgba(0,212,255,0.1), rgba(255,179,0,0.1))">
    <Heading size="sm">Blending Impact</Heading>
    <HStack justify="space-between" mt={3}>
      <VStack align="start">
        <Text fontSize="xs">TrueSkill Only</Text>
        <Text fontSize="2xl">67.8%</Text>
      </VStack>
      <Icon as={FiArrowRight} />
      <VStack align="end">
        <Text fontSize="xs">Blended</Text>
        <Text fontSize="2xl" color="green.400">71.2%</Text>
      </VStack>
    </HStack>
    <Badge colorScheme="green">+3.4% improvement from blending</Badge>
  </StatCard>

  {/* Upset Detection */}
  <StatCard>
    <Heading size="sm">Upset Detection</Heading>
    <Text fontSize="3xl">23 upsets</Text>
    <Text fontSize="sm" color="gray.500">
      Out of 182 matches (12.6%)
    </Text>

    <Box mt={3}>
      <HStack justify="space-between" fontSize="sm">
        <Text>Avg MMR boost for upsets:</Text>
        <Badge colorScheme="green">+35 MMR</Badge>
      </HStack>
      <HStack justify="space-between" fontSize="sm">
        <Text>vs. expected wins:</Text>
        <Badge>+21 MMR</Badge>
      </HStack>
    </Box>
  </StatCard>
</VStack>
```

---

### **Section 3: What's Changing (Right Column)**

```jsx
<VStack spacing={6}>
  {/* Weight Changes This Version */}
  <Card>
    <Heading size="md">Weight Evolution</Heading>

    {/* Animated comparison */}
    <Table size="sm">
      <Tbody>
        <Tr>
          <Td>Combat</Td>
          <Td>
            <HStack>
              <Progress value={40} w="100px" colorScheme="gray" />
              <Icon as={FiArrowRight} />
              <Progress value={47} w="100px" colorScheme="blue" />
            </HStack>
          </Td>
          <Td>
            <Badge colorScheme="blue">40% → 47%</Badge>
          </Td>
        </Tr>
        <Tr>
          <Td>Economy</Td>
          <Td>
            <HStack>
              <Progress value={20} w="100px" colorScheme="gray" />
              <Icon as={FiArrowRight} />
              <Progress value={18} w="100px" colorScheme="orange" />
            </HStack>
          </Td>
          <Td>
            <Badge colorScheme="orange">20% → 18%</Badge>
          </Td>
        </Tr>
        {/* ... */}
      </Tbody>
    </Table>

    <Alert status="info" mt={3}>
      <AlertIcon />
      <Text fontSize="sm">
        Combat matters more! Model learned from recent aggressive plays.
      </Text>
    </Alert>
  </Card>

  {/* Feature Importance */}
  <Card>
    <Heading size="md">Feature Impact Ranking</Heading>

    <VStack spacing={2} align="stretch" mt={3}>
      {[
        { name: 'Combat Score', correlation: 0.45, trend: 'up' },
        { name: 'Map Synergy', correlation: 0.32, trend: 'up' },
        { name: 'Team Contribution', correlation: 0.28, trend: 'stable' },
        { name: 'Economy', correlation: 0.18, trend: 'down' },
        { name: 'Efficiency', correlation: 0.09, trend: 'stable' }
      ].map(feature => (
        <HStack justify="space-between" key={feature.name}>
          <Text fontSize="sm">{feature.name}</Text>
          <HStack>
            <Progress
              value={feature.correlation * 100}
              w="100px"
              colorScheme={
                feature.correlation > 0.4 ? 'green' :
                feature.correlation > 0.25 ? 'blue' : 'gray'
              }
            />
            <Icon
              as={
                feature.trend === 'up' ? FiTrendingUp :
                feature.trend === 'down' ? FiTrendingDown : FiMinus
              }
              color={
                feature.trend === 'up' ? 'green.400' :
                feature.trend === 'down' ? 'red.400' : 'gray.400'
              }
            />
          </HStack>
        </HStack>
      ))}
    </VStack>
  </Card>

  {/* Recent Activity */}
  <Card>
    <Heading size="sm">Recent Learning Activity</Heading>
    <VStack align="stretch" spacing={2} mt={3} fontSize="sm">
      <HStack>
        <Icon as={FiCheckCircle} color="green.400" />
        <Text>Retrained on 10 new matches (2 hours ago)</Text>
      </HStack>
      <HStack>
        <Icon as={FiTrendingUp} color="blue.400" />
        <Text>Accuracy improved from 68.1% to 71.2%</Text>
      </HStack>
      <HStack>
        <Icon as={FiZap} color="yellow.400" />
        <Text>Detected 2 upsets this session</Text>
      </HStack>
    </VStack>
  </Card>
</VStack>
```

---

### **Section 4: AI Suggestions (Bottom - Highlighted)**

```jsx
<Box
  border="3px solid"
  borderColor="accent.500"
  borderRadius="lg"
  p={6}
  bg="linear-gradient(135deg, rgba(255,179,0,0.05), rgba(0,212,255,0.05))"
  boxShadow="0 0 40px rgba(255,179,0,0.2)"
>
  <HStack mb={4}>
    <Icon as={FiCpu} boxSize={8} color="accent.500" />
    <Heading size="lg">AI Recommendations</Heading>
    <Badge colorScheme="yellow" fontSize="md">2 Pending</Badge>
  </HStack>

  <VStack spacing={6} align="stretch">
    {/* Weight Update Suggestion */}
    <Card bg="rgba(0,212,255,0.05)">
      <HStack justify="space-between">
        <VStack align="start">
          <HStack>
            <Icon as={FiCheckCircle} color="green.400" />
            <Heading size="sm">Weight Optimization</Heading>
          </HStack>
          <Text fontSize="sm" color="gray.500">
            Found adjustments that improve accuracy by 4.2%
          </Text>
        </VStack>
        <VStack>
          <Badge colorScheme="green">High Confidence (87%)</Badge>
          <Button size="sm" colorScheme="green">Review Changes</Button>
        </VStack>
      </HStack>
    </Card>

    {/* Feature Suggestion */}
    <Card bg="rgba(255,179,0,0.05)" borderColor="accent.500" borderWidth="2px">
      <VStack align="stretch" spacing={4}>
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <HStack>
              <Icon as={FiZap} color="accent.500" />
              <Heading size="sm">New Feature Suggested</Heading>
              <Badge colorScheme="yellow">AI Discovery</Badge>
            </HStack>
            <Text fontWeight="bold" color="accent.500">
              "early_game_aggression"
            </Text>
          </VStack>
          <Badge colorScheme="yellow">Medium Confidence (65%)</Badge>
        </HStack>

        <Box bg="gray.800" p={3} borderRadius="md">
          <Text fontSize="xs" fontFamily="mono" color="gray.300">
            <strong>Reasoning:</strong> High upset rate (40%) suggests early game
            dynamics not captured. Underdogs may win through early pressure.
          </Text>
        </Box>

        <Box>
          <Text fontSize="sm" fontWeight="bold" mb={2}>Suggested Extraction:</Text>
          <Code display="block" whiteSpace="pre" fontSize="xs" p={3} borderRadius="md">
{`early_units = count_units(replay, time=0-300s)
early_attacks = count_attacks(replay, time=0-300s)
score = (early_units * 0.3 + early_attacks * 0.7)`}
          </Code>
        </Box>

        <HStack>
          <Text fontSize="xs" color="gray.500">
            Expected impact: +0.25 correlation
          </Text>
          <Button size="sm" variant="outline">Implement Later</Button>
          <Button size="sm" colorScheme="yellow">Start Implementation</Button>
        </HStack>
      </VStack>
    </Card>
  </VStack>
</Box>
```

---

### **Section 5: Your Input (Interactive)**

```jsx
<Card>
  <Heading size="md" mb={4}>
    <Icon as={FiEdit} mr={2} />
    You Know Your Meta Best
  </Heading>

  <Tabs>
    <TabList>
      <Tab>Suggest Feature</Tab>
      <Tab>Annotate Pattern</Tab>
      <Tab>Session Feedback</Tab>
    </TabList>

    <TabPanels>
      {/* Manual Feature Suggestion */}
      <TabPanel>
        <VStack spacing={4} align="stretch">
          <FormControl>
            <FormLabel>Feature Name</FormLabel>
            <Input placeholder="e.g., player_map_preference" />
          </FormControl>

          <FormControl>
            <FormLabel>What Did You Notice?</FormLabel>
            <Textarea
              placeholder="e.g., Player X always wins on Lost Temple but struggles on other maps. This should affect predictions."
              rows={4}
            />
          </FormControl>

          <FormControl>
            <FormLabel>How to Extract This?</FormLabel>
            <Textarea
              placeholder="e.g., Track player win rate per map, boost/reduce prediction based on map familiarity"
              rows={3}
            />
          </FormControl>

          <Button colorScheme="blue" leftIcon={<FiZap />}>
            Submit for Validation
          </Button>
        </VStack>
      </TabPanel>

      {/* Pattern Annotation */}
      <TabPanel>
        <VStack spacing={4} align="stretch">
          <Text fontSize="sm" color="gray.500">
            Help the AI learn faster by annotating patterns you see:
          </Text>

          <CheckboxGroup>
            <VStack align="start">
              <Checkbox>
                Protoss+Terran combos seem to win more
              </Checkbox>
              <Checkbox>
                Late night games are sloppier (more upsets)
              </Checkbox>
              <Checkbox>
                Player X tilts after first loss
              </Checkbox>
              <Checkbox>
                Map "Daybreak" favors aggressive play
              </Checkbox>
            </VStack>
          </CheckboxGroup>

          <Button colorScheme="blue">
            Save Annotations (AI will test these)
          </Button>
        </VStack>
      </TabPanel>

      {/* Session Feedback */}
      <TabPanel>
        <VStack spacing={4} align="stretch">
          <Stat>
            <StatLabel>Last Session (10 games, 2 hours ago)</StatLabel>
            <StatNumber>7/10 predictions correct</StatNumber>
          </Stat>

          <FormControl>
            <FormLabel>Which predictions felt wrong?</FormLabel>
            <CheckboxGroup>
              <VStack align="start">
                <Checkbox>Match #1 - Model favored wrong team</Checkbox>
                <Checkbox>Match #4 - Didn't account for player fatigue</Checkbox>
                <Checkbox>Match #7 - Map advantage missed</Checkbox>
              </VStack>
            </CheckboxGroup>
          </FormControl>

          <FormControl>
            <FormLabel>Additional Notes</FormLabel>
            <Textarea placeholder="Any other observations..." />
          </FormControl>

          <Button colorScheme="blue">Submit Feedback</Button>
        </VStack>
      </TabPanel>
    </TabPanels>
  </Tabs>
</Card>
```

---

## After-Session Notification

When user uploads 10 new matches, show prominent notification:

```jsx
<Alert
  status="success"
  variant="left-accent"
  p={6}
  borderWidth="3px"
  borderColor="green.400"
  boxShadow="0 0 40px rgba(0,255,136,0.3)"
>
  <AlertIcon boxSize={8} />
  <Box flex="1">
    <AlertTitle fontSize="xl">
      🎉 Model Retrained on Your Latest Session!
    </AlertTitle>
    <AlertDescription>
      <VStack align="start" spacing={2} mt={3}>
        <Text>
          <strong>10 new matches processed</strong> (182 total replays)
        </Text>
        <Text>
          Accuracy: 68.1% → <strong style={{ color: 'green' }}>71.2% (+3.1%)</strong>
        </Text>
        <Text>
          Combat weight increased: 45% → 47% (aggressive play rewarded)
        </Text>
        <Text>
          Detected 2 upsets this session (model learning!)
        </Text>
      </VStack>
    </AlertDescription>
  </Box>
  <Button colorScheme="green" onClick={() => navigate('/adaptive-model')}>
    See What Changed →
  </Button>
</Alert>
```

---

## Summary

### Key Changes:

1. **Unified Dashboard** - One page tells the whole story
2. **Timeline Visualization** - See model evolution clearly
3. **Session-Based Updates** - Highlight what changed after each 10-game session
4. **Human Input** - Let user suggest features based on their knowledge
5. **Clear AI Suggestions** - Make recommendations very visible
6. **Celebration of Progress** - Show improvements prominently

### Why This Works for Low Frequency:

- ✅ Each update is **dramatic and visible**
- ✅ User sees **exactly what the AI learned**
- ✅ **Human insights** accelerate learning
- ✅ Progress feels **meaningful** even with 5 games/week
- ✅ **Encourages engagement** with the learning system

---

**Next:** Implement this new dashboard structure?
