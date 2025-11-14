/**
 * Failed Uploads Page
 * Review replay files that failed to process
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
  CardBody,
  Badge,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Select,
  useColorModeValue,
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
} from 'react-icons/fi';
import { replaysApi } from '../api/endpoints';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';

const FailedUploads = () => {
  const [errorTypeFilter, setErrorTypeFilter] = useState('');
  const [reviewedFilter, setReviewedFilter] = useState('');
  const [selectedUpload, setSelectedUpload] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isDetailsOpen, onOpen: onDetailsOpen, onClose: onDetailsClose } = useDisclosure();
  const [reviewNotes, setReviewNotes] = useState('');

  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Fetch failed uploads
  const { data: failedUploads, isLoading } = useQuery({
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
    mutationFn: ({ uploadId, notes }) => replaysApi.markUploadReviewed(uploadId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries(['failed-uploads']);
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
    onError: (error) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to mark as reviewed',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Manual winner determination mutation
  const setWinnerMutation = useMutation({
    mutationFn: ({ uploadId, winnerTeam }) => replaysApi.setManualWinner(uploadId, winnerTeam),
    onSuccess: (response) => {
      const matchId = response.data.match_id;
      queryClient.invalidateQueries(['failed-uploads']);
      queryClient.invalidateQueries(['matches']);

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
        ),
        status: 'success',
        duration: 8000,
        isClosable: true,
      });
    },
    onError: (error) => {
      toast({
        title: 'Error processing replay',
        description: error.response?.data?.detail || 'Failed to process replay with manual winner',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleSetWinner = (upload, winnerTeam) => {
    if (window.confirm(`Set Team ${winnerTeam} as the winner for this match?`)) {
      setWinnerMutation.mutate({
        uploadId: upload.id,
        winnerTeam
      });
    }
  };

  const handleMarkReviewed = () => {
    if (selectedUpload) {
      markReviewedMutation.mutate({
        uploadId: selectedUpload.id,
        notes: reviewNotes || null,
      });
    }
  };

  const openReviewModal = (upload) => {
    setSelectedUpload(upload);
    setReviewNotes('');
    onOpen();
  };

  const openDetailsModal = (upload) => {
    setSelectedUpload(upload);
    onDetailsOpen();
  };

  const formatErrorMessage = (message) => {
    // Split by newlines and preserve formatting
    return message.split('\n').map((line, i) => (
      <Text key={i} fontFamily="mono" fontSize="sm" whiteSpace="pre">
        {line}
      </Text>
    ));
  };

  const getErrorIcon = (errorType) => {
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

  const getErrorColor = (errorType) => {
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

  const formatErrorType = (errorType) => {
    return errorType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  if (isLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <LoadingState message="Loading failed uploads..." />
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="xl" mb={2}>
            Failed Uploads
          </Heading>
          <Text color="gray.500" fontSize="lg">
            Review replay files that failed to process
          </Text>
        </Box>

        {/* Info Alert */}
        <Alert status="info" variant="left-accent" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Manual Review Required</AlertTitle>
            <AlertDescription>
              These replays failed to process automatically. Review them to identify patterns or
              edge cases that may need algorithm improvements.
            </AlertDescription>
          </Box>
        </Alert>

        {/* Filters */}
        <Card bg={cardBg}>
          <CardBody>
            <HStack spacing={4}>
              <Icon as={FiFilter} color="gray.500" />
              <Select
                placeholder="All Error Types"
                value={errorTypeFilter}
                onChange={(e) => setErrorTypeFilter(e.target.value)}
                maxW="300px"
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
                onChange={(e) => setReviewedFilter(e.target.value)}
                maxW="200px"
              >
                <option value="false">Not Reviewed</option>
                <option value="true">Reviewed</option>
              </Select>
            </HStack>
          </CardBody>
        </Card>

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
          <Card bg={cardBg}>
            <CardBody>
              <TableContainer>
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Filename</Th>
                      <Th>Error Type</Th>
                      <Th>Error Message</Th>
                      <Th>Match Info</Th>
                      <Th>Uploaded</Th>
                      <Th>Status</Th>
                      <Th>Actions</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {failedUploads.map((upload) => (
                      <Tr
                        key={upload.id}
                        opacity={upload.reviewed ? 0.6 : 1}
                        borderLeft="4px solid"
                        borderLeftColor={
                          upload.reviewed ? 'green.500' : `${getErrorColor(upload.error_type)}.500`
                        }
                      >
                        <Td>
                          <Tooltip label={upload.filename}>
                            <Text fontSize="sm" isTruncated maxW="200px">
                              {upload.filename}
                            </Text>
                          </Tooltip>
                          {upload.file_size_bytes && (
                            <Text fontSize="xs" color="gray.500">
                              {(upload.file_size_bytes / 1024).toFixed(1)} KB
                            </Text>
                          )}
                        </Td>
                        <Td>
                          <Badge
                            colorScheme={getErrorColor(upload.error_type)}
                            display="flex"
                            alignItems="center"
                            gap={1}
                            w="fit-content"
                          >
                            <Icon as={getErrorIcon(upload.error_type)} />
                            {formatErrorType(upload.error_type)}
                          </Badge>
                        </Td>
                        <Td>
                          <VStack align="start" spacing={1}>
                            <Text fontSize="sm" color="gray.600" noOfLines={3} maxW="400px">
                              {upload.error_message}
                            </Text>
                            <Button
                              size="xs"
                              leftIcon={<FiEye />}
                              variant="ghost"
                              colorScheme="blue"
                              onClick={() => openDetailsModal(upload)}
                            >
                              View Full Error
                            </Button>
                          </VStack>
                        </Td>
                        <Td>
                          {upload.map_name || upload.game_mode ? (
                            <VStack align="start" spacing={0}>
                              {upload.map_name && (
                                <Text fontSize="xs">{upload.map_name}</Text>
                              )}
                              {upload.game_mode && (
                                <Badge size="sm" fontSize="xx-small">
                                  {upload.game_mode}
                                </Badge>
                              )}
                            </VStack>
                          ) : (
                            <Text fontSize="xs" color="gray.500">
                              N/A
                            </Text>
                          )}
                        </Td>
                        <Td>
                          <Text fontSize="xs">
                            {new Date(upload.uploaded_at).toLocaleDateString()}
                          </Text>
                          <Text fontSize="xs" color="gray.500">
                            {new Date(upload.uploaded_at).toLocaleTimeString()}
                          </Text>
                        </Td>
                        <Td>
                          {upload.reviewed ? (
                            <Badge colorScheme="green" display="flex" alignItems="center" gap={1}>
                              <Icon as={FiCheck} />
                              Reviewed
                            </Badge>
                          ) : (
                            <Badge colorScheme="gray">Pending</Badge>
                          )}
                        </Td>
                        <Td>
                          <VStack spacing={2} align="stretch">
                            {upload.error_type === 'winner_determination' && !upload.reviewed && (
                              <HStack spacing={2}>
                                <Button
                                  size="sm"
                                  colorScheme="blue"
                                  onClick={() => handleSetWinner(upload, 1)}
                                  isLoading={setWinnerMutation.isLoading}
                                >
                                  Team 1 Won
                                </Button>
                                <Button
                                  size="sm"
                                  colorScheme="orange"
                                  onClick={() => handleSetWinner(upload, 2)}
                                  isLoading={setWinnerMutation.isLoading}
                                >
                                  Team 2 Won
                                </Button>
                              </HStack>
                            )}
                            {!upload.reviewed && (
                              <Button
                                size="sm"
                                colorScheme="green"
                                variant="ghost"
                                onClick={() => openReviewModal(upload)}
                              >
                                Mark Reviewed
                              </Button>
                            )}
                          </VStack>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </TableContainer>
            </CardBody>
          </Card>
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
                    onChange={(e) => setReviewNotes(e.target.value)}
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
                  bg={useColorModeValue('gray.50', 'gray.900')}
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
  );
};

export default FailedUploads;
