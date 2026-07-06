/**
 * Failed Uploads Page
 * Review replay files that failed to process
 */
import { useState, type ChangeEvent, type ReactNode } from 'react';
import {
  Box,
  Container,
  Text,
  VStack,
  HStack,
  Badge,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Select,
  Icon,
  Tooltip,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Textarea,
  useDisclosure,
  useToast,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  FiAlertCircle,
  FiXCircle,
  FiAlertTriangle,
  FiFileText,
  FiCheck,
  FiFilter,
  FiEye,
  FiChevronDown,
  FiChevronRight,
} from 'react-icons/fi';
import { replaysApi, type FailedUpload } from '../api/endpoints';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import { formatDateOnly, formatTimeOnly } from '../utils/formatting';
import type { IconType } from 'react-icons/lib';

// API response for set winner mutation
interface SetWinnerResponse {
  match_id: number;
  message?: string;
}

const FailedUploads: React.FC = () => {
  const [errorTypeFilter, setErrorTypeFilter] = useState<string>('');
  // Default to actionable rows (not yet reviewed); switch to "All Statuses" to see everything.
  const [reviewedFilter, setReviewedFilter] = useState<string>('false');
  const [selectedUpload, setSelectedUpload] = useState<FailedUpload | null>(null);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isDetailsOpen, onOpen: onDetailsOpen, onClose: onDetailsClose } = useDisclosure();
  const [reviewNotes, setReviewNotes] = useState<string>('');

  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  // Design tokens
  const cardBg = 'space.800';
  const borderColor = 'space.900';
  const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';
  const errorBoxBg = 'space.900';
  const hoverBg = 'space.700';
  const expandedRowBg = 'space.900';

  // Fetch failed uploads
  const { data: failedUploads, isLoading } = useQuery<FailedUpload[]>({
    queryKey: ['failed-uploads', errorTypeFilter, reviewedFilter],
    queryFn: async () => {
      const reviewedParam = reviewedFilter === '' ? null : reviewedFilter === 'true';
      const response = await replaysApi.getFailedUploads(
        50,
        0,
        errorTypeFilter || null,
        reviewedParam
      );
      return response.data;
    },
  });

  // Mark as reviewed mutation
  const markReviewedMutation = useMutation({
    mutationFn: ({ uploadId, notes }: { uploadId: number; notes: string | null }) =>
      replaysApi.markUploadReviewed(uploadId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['failed-uploads'] });
      toast({
        title: 'Marked as reviewed',
        description: 'Failed upload has been marked as reviewed',
        status: 'success',
        duration: 3000,
      });
      onClose();
      setReviewNotes('');
      setSelectedUpload(null);
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast({
        title: 'Error',
        description: axiosError.response?.data?.detail || 'Failed to mark as reviewed',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Manual winner determination mutation
  const setWinnerMutation = useMutation({
    mutationFn: ({ uploadId, winnerTeam }: { uploadId: number; winnerTeam: number }) =>
      replaysApi.setManualWinner(uploadId, winnerTeam),
    onSuccess: (response: { data: SetWinnerResponse }) => {
      const matchId = response.data.match_id;
      queryClient.invalidateQueries({ queryKey: ['failed-uploads'] });
      queryClient.invalidateQueries({ queryKey: ['matches'] });
      // Also invalidate players since ratings are updated when a match is processed
      queryClient.invalidateQueries({ queryKey: ['players'] });

      // Show success toast with "View Match" button
      toast({
        title: 'Replay processed successfully',
        description: (
          <VStack align="start" spacing={2}>
            <Text>{response.data.message || `Match #${matchId} created with manual winner determination`}</Text>
            <Button
              size="sm"
              colorScheme="blue"
              onClick={() => navigate(`/history/${matchId}`)}
            >
              View Match Details
            </Button>
          </VStack>
        ) as unknown as string,
        status: 'success',
        duration: 8000,
        isClosable: true,
      });
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast({
        title: 'Error processing replay',
        description: axiosError.response?.data?.detail || 'Failed to process replay with manual winner',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleSetWinner = (upload: FailedUpload, winnerTeam: number): void => {
    if (window.confirm(`Set Team ${winnerTeam} as the winner for this match?`)) {
      setWinnerMutation.mutate({
        uploadId: upload.id,
        winnerTeam
      });
    }
  };

  const handleMarkReviewed = (): void => {
    if (selectedUpload) {
      markReviewedMutation.mutate({
        uploadId: selectedUpload.id,
        notes: reviewNotes || null,
      });
    }
  };

  const openReviewModal = (upload: FailedUpload): void => {
    setSelectedUpload(upload);
    setReviewNotes('');
    onOpen();
  };

  const openDetailsModal = (upload: FailedUpload): void => {
    setSelectedUpload(upload);
    onDetailsOpen();
  };

  const formatErrorMessage = (message: string): ReactNode => {
    // Split by newlines and preserve formatting
    return message.split('\n').map((line, i) => (
      <Text key={i} fontFamily="mono" fontSize="sm" whiteSpace="pre">
        {line}
      </Text>
    ));
  };

  const getErrorIcon = (errorType: string): IconType => {
    switch (errorType) {
      case 'parse_error':
      case 'corrupt_file':
        return FiXCircle;
      case 'winner_determination':
        return FiAlertCircle;
      case 'validation_error':
      case 'unsupported_mode':
        return FiAlertTriangle;
      default:
        return FiFileText;
    }
  };

  const getErrorColor = (errorType: string): string => {
    switch (errorType) {
      case 'parse_error':
      case 'corrupt_file':
        return 'red';
      case 'winner_determination':
        return 'orange';
      case 'validation_error':
        return 'yellow';
      case 'unsupported_mode':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const formatErrorType = (errorType: string): string => {
    return errorType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const handleErrorTypeChange = (e: ChangeEvent<HTMLSelectElement>): void => {
    setErrorTypeFilter(e.target.value);
  };

  const handleReviewedFilterChange = (e: ChangeEvent<HTMLSelectElement>): void => {
    setReviewedFilter(e.target.value);
  };

  const handleReviewNotesChange = (e: ChangeEvent<HTMLTextAreaElement>): void => {
    setReviewNotes(e.target.value);
  };

  const handleRowClick = (uploadId: number): void => {
    setExpandedRow(expandedRow === uploadId ? null : uploadId);
  };

  if (isLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading failed uploads..." />
      </Container>
    );
  }

  return (
    <Box minH="100vh" pb={16}>
      <PageHeader
        kicker="Needs Attention"
        title="Failed [Uploads]"
        description="Replay files that failed to process — review, retry, or dismiss them."
      />
      <Container maxW="container.xl" pt={8}>
      <VStack spacing={8} align="stretch">
        {/* Info Alert */}
        <Alert
          status="info"
          variant="left-accent"
          borderRadius="xl"
          bg="space.800"
          border="3px solid"
          borderColor={borderColor}
          boxShadow={brandShadow}
        >
          <AlertIcon />
          <Box>
            <AlertTitle fontFamily="heading" letterSpacing="wide">Manual Review Required</AlertTitle>
            <AlertDescription color="gray.300">
              These replays failed to process automatically. Review them to identify patterns or
              edge cases that may need algorithm improvements.
            </AlertDescription>
          </Box>
        </Alert>

        {/* Filters */}
        <Box
          bg={cardBg}
          borderRadius="xl"
          border="3px solid"
          borderColor={borderColor}
          boxShadow={brandShadow}
          p={4}
        >
          <HStack spacing={4} justify="space-between">
            <HStack spacing={4}>
              <Icon as={FiFilter} color="gray.400" />
              <Select
                placeholder="All Error Types"
                value={errorTypeFilter}
                onChange={handleErrorTypeChange}
                maxW="300px"
                bg="space.900"
                borderColor="space.700"
              >
                <option value="parse_error">Parse Error</option>
                <option value="validation_error">Validation Error</option>
                <option value="winner_determination">Winner Determination</option>
                <option value="unsupported_mode">Unsupported Mode</option>
                <option value="corrupt_file">Corrupt File</option>
                <option value="other">Other</option>
              </Select>

              <Select
                placeholder="All Statuses"
                value={reviewedFilter}
                onChange={handleReviewedFilterChange}
                maxW="200px"
                bg="space.900"
                borderColor="space.700"
              >
                <option value="false">Not Reviewed</option>
                <option value="true">Reviewed</option>
              </Select>
            </HStack>

            {(errorTypeFilter || reviewedFilter) && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setErrorTypeFilter('');
                  setReviewedFilter('');
                }}
              >
                Clear Filters
              </Button>
            )}
          </HStack>
        </Box>

        {/* Failed Uploads List */}
        {!failedUploads || failedUploads.length === 0 ? (
          <EmptyState
            variant="stats"
            title="No Failed Uploads"
            description={
              errorTypeFilter || reviewedFilter
                ? 'No failed uploads match your filters'
                : 'All replays processed successfully'
            }
          />
        ) : (
          <Box
            bg={cardBg}
            borderRadius="xl"
            border="3px solid"
            borderColor={borderColor}
            boxShadow={brandShadow}
            overflow="hidden"
          >
            <Box overflowX="auto" maxW="100%">
              <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th w="40px"></Th>
                      <Th minW="180px">Filename</Th>
                      <Th minW="140px">Error Type</Th>
                      <Th minW="100px">Date</Th>
                      <Th minW="80px">Status</Th>
                      <Th minW="120px">Actions</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {failedUploads.map((upload) => (
                      <>
                        <Tr
                          key={upload.id}
                          opacity={upload.reviewed ? 0.6 : 1}
                          borderLeft="4px solid"
                          borderLeftColor={
                            upload.reviewed ? 'green.500' : `${getErrorColor(upload.error_type)}.500`
                          }
                          _hover={{ bg: hoverBg }}
                          cursor="pointer"
                          onClick={() => handleRowClick(upload.id)}
                        >
                          <Td p={2}>
                            <Icon
                              as={expandedRow === upload.id ? FiChevronDown : FiChevronRight}
                              color="gray.500"
                              boxSize={4}
                            />
                          </Td>
                          <Td>
                            <Tooltip label={upload.filename}>
                              <VStack align="start" spacing={0}>
                                <Text fontSize="sm" isTruncated maxW="180px" fontWeight="medium">
                                  {upload.filename}
                                </Text>
                                {upload.file_size_bytes && (
                                  <Text fontSize="xs" color="gray.500">
                                    {(upload.file_size_bytes / 1024).toFixed(1)} KB
                                  </Text>
                                )}
                              </VStack>
                            </Tooltip>
                          </Td>
                          <Td>
                            <Badge
                              colorScheme={getErrorColor(upload.error_type)}
                              display="flex"
                              alignItems="center"
                              gap={1}
                              w="fit-content"
                              fontSize="xs"
                            >
                              <Icon as={getErrorIcon(upload.error_type)} boxSize={3} />
                              {formatErrorType(upload.error_type)}
                            </Badge>
                          </Td>
                          <Td>
                            <Text fontSize="xs">
                              {formatDateOnly(upload.uploaded_at)}
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                              {formatTimeOnly(upload.uploaded_at)}
                            </Text>
                          </Td>
                          <Td>
                            {upload.reviewed ? (
                              <Badge colorScheme="green" display="flex" alignItems="center" gap={1} fontSize="xs">
                                <Icon as={FiCheck} boxSize={3} />
                                Reviewed
                              </Badge>
                            ) : (
                              <Badge colorScheme="gray" fontSize="xs">Pending</Badge>
                            )}
                          </Td>
                          <Td onClick={(e) => e.stopPropagation()}>
                            <HStack spacing={1}>
                              <Tooltip label="View Details">
                                <Button
                                  size="xs"
                                  variant="ghost"
                                  colorScheme="blue"
                                  aria-label="View details"
                                  onClick={() => openDetailsModal(upload)}
                                >
                                  <Icon as={FiEye} />
                                </Button>
                              </Tooltip>
                              {!upload.reviewed && (
                                <Tooltip label="Mark Reviewed">
                                  <Button
                                    size="xs"
                                    variant="ghost"
                                    colorScheme="green"
                                    aria-label="Mark reviewed"
                                    onClick={() => openReviewModal(upload)}
                                  >
                                    <Icon as={FiCheck} />
                                  </Button>
                                </Tooltip>
                              )}
                            </HStack>
                          </Td>
                        </Tr>
                        {expandedRow === upload.id && (
                          <Tr key={`${upload.id}-expanded`}>
                            <Td colSpan={6} bg={expandedRowBg} p={4}>
                              <VStack align="stretch" spacing={4}>
                                {/* Error Message Section */}
                                <Box>
                                  <Text fontSize="sm" fontWeight="bold" mb={2}>
                                    Error Message:
                                  </Text>
                                  <Box
                                    bg={cardBg}
                                    p={3}
                                    borderRadius="md"
                                    border="1px solid"
                                    borderColor={borderColor}
                                    maxH="200px"
                                    overflowY="auto"
                                  >
                                    <Text fontSize="sm" fontFamily="mono" whiteSpace="pre-wrap">
                                      {upload.error_message}
                                    </Text>
                                  </Box>
                                </Box>

                                {/* Match Info Section */}
                                {(upload.map_name || upload.game_mode) && (
                                  <HStack spacing={4}>
                                    <Text fontSize="sm" fontWeight="bold">
                                      Match Info:
                                    </Text>
                                    {upload.map_name && (
                                      <Badge variant="outline">{upload.map_name}</Badge>
                                    )}
                                    {upload.game_mode && (
                                      <Badge variant="outline">{upload.game_mode}</Badge>
                                    )}
                                  </HStack>
                                )}

                                {/* Winner Determination Actions */}
                                {upload.error_type === 'winner_determination' && !upload.reviewed && (
                                  <Box>
                                    <Text fontSize="sm" fontWeight="bold" mb={2}>
                                      Manual Winner Selection:
                                    </Text>
                                    <HStack spacing={3}>
                                      <Button
                                        size="sm"
                                        colorScheme="blue"
                                        onClick={() => handleSetWinner(upload, 1)}
                                        isLoading={setWinnerMutation.isPending}
                                      >
                                        Team 1 Won
                                      </Button>
                                      <Button
                                        size="sm"
                                        colorScheme="orange"
                                        onClick={() => handleSetWinner(upload, 2)}
                                        isLoading={setWinnerMutation.isPending}
                                      >
                                        Team 2 Won
                                      </Button>
                                    </HStack>
                                  </Box>
                                )}
                              </VStack>
                            </Td>
                          </Tr>
                        )}
                      </>
                    ))}
                  </Tbody>
              </Table>
            </Box>
          </Box>
        )}
      </VStack>

      {/* Review Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Mark as Reviewed</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedUpload && (
              <VStack align="stretch" spacing={4}>
                <Box>
                  <Text fontWeight="bold" mb={2}>
                    {selectedUpload.filename}
                  </Text>
                  <Text fontSize="sm" color="gray.500">
                    {selectedUpload.error_message}
                  </Text>
                </Box>

                <Box>
                  <Text mb={2} fontWeight="semibold">
                    Review Notes (Optional)
                  </Text>
                  <Textarea
                    value={reviewNotes}
                    onChange={handleReviewNotesChange}
                    placeholder="Add any notes about this failed upload..."
                    rows={4}
                  />
                </Box>
              </VStack>
            )}
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="green"
              onClick={handleMarkReviewed}
              isLoading={markReviewedMutation.isPending}
            >
              Mark as Reviewed
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Error Details Modal */}
      <Modal isOpen={isDetailsOpen} onClose={onDetailsClose} size="4xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Error Details</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedUpload && (
              <VStack align="stretch" spacing={4}>
                <Box>
                  <Text fontWeight="bold" fontSize="lg" mb={2}>
                    {selectedUpload.filename}
                  </Text>
                  <HStack spacing={3} mb={4}>
                    <Badge
                      colorScheme={getErrorColor(selectedUpload.error_type)}
                      display="flex"
                      alignItems="center"
                      gap={1}
                    >
                      <Icon as={getErrorIcon(selectedUpload.error_type)} />
                      {formatErrorType(selectedUpload.error_type)}
                    </Badge>
                    {selectedUpload.map_name && (
                      <Badge variant="outline">{selectedUpload.map_name}</Badge>
                    )}
                    {selectedUpload.game_mode && (
                      <Badge variant="outline">{selectedUpload.game_mode}</Badge>
                    )}
                  </HStack>
                </Box>

                <Box
                  bg={errorBoxBg}
                  p={4}
                  borderRadius="md"
                  border="1px solid"
                  borderColor={borderColor}
                  maxH="500px"
                  overflowY="auto"
                >
                  <VStack align="stretch" spacing={1}>
                    {formatErrorMessage(selectedUpload.error_message)}
                  </VStack>
                </Box>

                {selectedUpload.error_type === 'winner_determination' && (
                  <Alert status="info" borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <AlertTitle>Manual Review Suggested</AlertTitle>
                      <AlertDescription fontSize="sm">
                        Use the team stats above to manually verify which team won.
                        A future update will allow you to manually specify the winner.
                      </AlertDescription>
                    </Box>
                  </Alert>
                )}
              </VStack>
            )}
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" onClick={onDetailsClose}>
              Close
            </Button>
            {selectedUpload && !selectedUpload.reviewed && (
              <Button
                colorScheme="green"
                ml={3}
                onClick={() => {
                  onDetailsClose();
                  openReviewModal(selectedUpload);
                }}
              >
                Mark as Reviewed
              </Button>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>
      </Container>
    </Box>
  );
};

export default FailedUploads;
