/**
 * Match History Page - TACTICAL BATTLE ARCHIVE
 * Browse past games with win probability analysis
 */
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  Badge,
  Button,
  useColorModeValue,
  Flex,
  Icon,
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Grid,
  IconButton,
  ButtonGroup,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiTarget, FiTrendingUp, FiZap, FiActivity, FiAlertTriangle, FiChevronLeft, FiChevronRight, FiChevronsLeft, FiChevronsRight } from 'react-icons/fi';
import { replaysApi } from '../api/endpoints';
import EmptyState from '../components/EmptyState';
import LoadingState, { MatchCardSkeleton } from '../components/LoadingState';
import { formatDuration, formatDateTime, formatWinProbability, getUpsetIndicator } from '../utils/formatting';

const MatchHistory = () => {
  const navigate = useNavigate();
  const cardBg = useColorModeValue('white', 'rgba(17, 25, 40, 0.7)');
  const borderColor = useColorModeValue('gray.200', 'rgba(0, 212, 255, 0.2)');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const matchesPerPage = 20;

  // Fetch matches with pagination
  const { data: matchesData, isLoading } = useQuery({
    queryKey: ['matches', currentPage],
    queryFn: async () => {
      const offset = (currentPage - 1) * matchesPerPage;
      const response = await replaysApi.getMatches(matchesPerPage, offset);
      return response.data;
    },
  });

  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_count || 0;
  const totalPages = Math.ceil(totalMatches / matchesPerPage);

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (isLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading>Match History</Heading>
          <VStack spacing={4}>
            {Array.from({ length: 10 }).map((_, idx) => (
              <MatchCardSkeleton key={idx} />
            ))}
          </VStack>
        </VStack>
      </Container>
    );
  }

  if (matches.length === 0) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading>Match History</Heading>
          <EmptyState
            variant="stats"
            title="No Matches Yet"
            description="Upload some replay files to start tracking your game history."
            onAction={() => navigate('/upload')}
          />
        </VStack>
      </Container>
    );
  }

  return (
    <Box position="relative">
      {/* Animated tactical grid background */}
      <Box
        position="fixed"
        top={0}
        left={0}
        right={0}
        bottom={0}
        opacity={0.02}
        pointerEvents="none"
        backgroundImage="linear-gradient(rgba(0, 212, 255, 0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.8) 1px, transparent 1px)"
        backgroundSize="60px 60px"
        zIndex={0}
      />

      <Container maxW="container.xl" py={8} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Bold Header Section */}
          <Box position="relative">
            <HStack justify="space-between" align="start" mb={2}>
              <VStack align="start" spacing={1}>
                <HStack spacing={3}>
                  <Icon as={FiActivity} boxSize={8} color="brand.400" />
                  <Heading
                    size="2xl"
                    fontFamily="heading"
                    textTransform="uppercase"
                    letterSpacing="wider"
                    color="brand.400"
                    textShadow="0 0 30px rgba(0, 212, 255, 0.5)"
                  >
                    BATTLE ARCHIVE
                  </Heading>
                </HStack>
                <Text
                  color="gray.500"
                  fontFamily="heading"
                  letterSpacing="wide"
                  fontSize="sm"
                  textTransform="uppercase"
                >
                  [ {totalMatches} OPERATIONS RECORDED{totalPages > 1 ? ` • PAGE ${currentPage}/${totalPages}` : ''} ]
                </Text>
              </VStack>

              {/* Stats badges */}
              <HStack spacing={3}>
                <Badge
                  bg="brand.500"
                  color="gray.900"
                  px={4}
                  py={2}
                  borderRadius="md"
                  fontSize="lg"
                  fontFamily="heading"
                  boxShadow="0 0 20px rgba(0, 212, 255, 0.4)"
                >
                  <Icon as={FiTrendingUp} mr={2} />
                  ACTIVE
                </Badge>
              </HStack>
            </HStack>

            {/* Decorative line */}
            <Box
              h="2px"
              bg="linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.6), transparent)"
              mt={4}
              mb={6}
            />
          </Box>

          {/* Match List with dramatic styling */}
          <VStack spacing={4} align="stretch">
            {matches.map((match) => {
              // Determine which team won by fetching players (we'll need to handle this properly)
              // For now, we'll show the probabilities if they exist
              const hasWinProb = match.predicted_team1_win_prob && match.predicted_team2_win_prob;
              const team1Prob = match.predicted_team1_win_prob || 0.5;
              const team2Prob = match.predicted_team2_win_prob || 0.5;

              // We can't determine winner from match data alone - need players
              // So we'll show upset indicator in detail page instead

              return (
                <Card
                  key={match.id}
                  bg={cardBg}
                  cursor="pointer"
                  onClick={() => navigate(`/history/${match.id}`)}
                  transition="all 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
                  border="2px solid"
                  borderColor={borderColor}
                  position="relative"
                  overflow="hidden"
                  _hover={{
                    transform: 'translateY(-4px) scale(1.01)',
                    boxShadow: '0 12px 40px rgba(0, 212, 255, 0.3), 0 0 80px rgba(255, 179, 0, 0.1)',
                    borderColor: 'brand.500',
                  }}
                  _before={{
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: '-100%',
                    width: '100%',
                    height: '100%',
                    background: 'linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.1), transparent)',
                    transition: 'left 0.5s',
                  }}
                  sx={{
                    '&:hover::before': {
                      left: '100%',
                    },
                  }}
                >
                  <CardBody>
                    <Grid
                      templateColumns={{ base: '1fr', md: 'auto 1fr auto' }}
                      gap={6}
                      alignItems="center"
                    >
                      {/* Left: Match icon */}
                      <Box
                        bg="linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(255, 179, 0, 0.2))"
                        p={4}
                        borderRadius="lg"
                        border="2px solid"
                        borderColor="brand.500"
                        boxShadow="0 0 20px rgba(0, 212, 255, 0.3)"
                      >
                        <Icon as={FiTarget} boxSize={8} color="brand.400" />
                      </Box>

                      {/* Middle: Match details */}
                      <VStack align="start" spacing={3} flex={1}>
                        <HStack spacing={3} flexWrap="wrap">
                          <Heading
                            size="lg"
                            fontFamily="heading"
                            textTransform="uppercase"
                            letterSpacing="wide"
                          >
                            {match.map_name}
                          </Heading>
                          <Badge
                            colorScheme="blue"
                            fontSize="md"
                            px={3}
                            py={1}
                            borderRadius="md"
                            fontFamily="heading"
                          >
                            {match.game_mode}
                          </Badge>
                        </HStack>

                        <HStack spacing={4} fontSize="sm" color="gray.400" fontFamily="heading">
                          <Text>{formatDateTime(match.played_at)}</Text>
                          <Text>•</Text>
                          <HStack>
                            <Icon as={FiZap} />
                            <Text>Duration: {formatDuration(match.duration_seconds)}</Text>
                          </HStack>
                        </HStack>

                        {/* Win Probability Display - BOLD & DRAMATIC */}
                        {hasWinProb && (
                          <Box w="full">
                            <HStack justify="space-between" mb={2} fontSize="sm" fontFamily="heading">
                              <HStack>
                                <Icon as={FiTrendingUp} color="brand.400" />
                                <Text color="brand.400" fontWeight="bold">TEAM 1</Text>
                                <Badge
                                  bg={team1Prob > 0.5 ? 'shield.500' : 'gray.600'}
                                  color="gray.900"
                                  fontSize="xs"
                                  px={2}
                                >
                                  {formatWinProbability(team1Prob)}
                                </Badge>
                              </HStack>
                              <HStack>
                                <Badge
                                  bg={team2Prob > 0.5 ? 'shield.500' : 'gray.600'}
                                  color="gray.900"
                                  fontSize="xs"
                                  px={2}
                                >
                                  {formatWinProbability(team2Prob)}
                                </Badge>
                                <Text color="accent.400" fontWeight="bold">TEAM 2</Text>
                                <Icon as={FiTrendingUp} color="accent.400" />
                              </HStack>
                            </HStack>

                            {/* Dual progress bars - dramatic visualization */}
                            <Box position="relative">
                              <HStack spacing={1}>
                                <Box flex={team1Prob} position="relative">
                                  <Progress
                                    value={100}
                                    size="lg"
                                    colorScheme="cyan"
                                    borderRadius="md"
                                    bg="gray.700"
                                    sx={{
                                      '& > div': {
                                        background: 'linear-gradient(90deg, rgba(0, 212, 255, 0.6), rgba(0, 212, 255, 1))',
                                        boxShadow: '0 0 10px rgba(0, 212, 255, 0.5)',
                                      },
                                    }}
                                  />
                                </Box>
                                <Box flex={team2Prob}>
                                  <Progress
                                    value={100}
                                    size="lg"
                                    colorScheme="orange"
                                    borderRadius="md"
                                    bg="gray.700"
                                    sx={{
                                      '& > div': {
                                        background: 'linear-gradient(90deg, rgba(255, 179, 0, 1), rgba(255, 179, 0, 0.6))',
                                        boxShadow: '0 0 10px rgba(255, 179, 0, 0.5)',
                                      },
                                    }}
                                  />
                                </Box>
                              </HStack>
                            </Box>
                          </Box>
                        )}
                      </VStack>

                      {/* Right: Action button */}
                      <Button
                        size="lg"
                        variant="primary"
                        rightIcon={<Icon as={FiTarget} />}
                        fontFamily="heading"
                        px={6}
                      >
                        ANALYZE
                      </Button>
                    </Grid>
                  </CardBody>
                </Card>
              );
            })}
          </VStack>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <Box mt={8}>
              <VStack spacing={4}>
                {/* Page info */}
                <Text
                  color="gray.500"
                  fontFamily="heading"
                  fontSize="sm"
                  textTransform="uppercase"
                  letterSpacing="wide"
                >
                  Page {currentPage} of {totalPages} • Showing {matches.length} of {totalMatches} matches
                </Text>

                {/* Pagination buttons */}
                <HStack spacing={2}>
                  <IconButton
                    icon={<FiChevronsLeft />}
                    onClick={() => handlePageChange(1)}
                    isDisabled={currentPage === 1}
                    aria-label="First page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />
                  <IconButton
                    icon={<FiChevronLeft />}
                    onClick={() => handlePageChange(currentPage - 1)}
                    isDisabled={currentPage === 1}
                    aria-label="Previous page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />

                  {/* Page number buttons */}
                  <ButtonGroup spacing={2}>
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      // Show pages around current page
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }

                      return (
                        <Button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          variant={currentPage === pageNum ? 'solid' : 'ghost'}
                          colorScheme="cyan"
                          size="lg"
                          fontFamily="heading"
                          minW="50px"
                          bg={currentPage === pageNum ? 'brand.500' : undefined}
                          color={currentPage === pageNum ? 'gray.900' : undefined}
                          _hover={{
                            bg: currentPage === pageNum ? 'brand.400' : 'whiteAlpha.200',
                          }}
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                  </ButtonGroup>

                  <IconButton
                    icon={<FiChevronRight />}
                    onClick={() => handlePageChange(currentPage + 1)}
                    isDisabled={currentPage === totalPages}
                    aria-label="Next page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />
                  <IconButton
                    icon={<FiChevronsRight />}
                    onClick={() => handlePageChange(totalPages)}
                    isDisabled={currentPage === totalPages}
                    aria-label="Last page"
                    variant="ghost"
                    colorScheme="cyan"
                    size="lg"
                  />
                </HStack>
              </VStack>
            </Box>
          )}
        </VStack>
      </Container>
    </Box>
  );
};

export default MatchHistory;
