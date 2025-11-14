/**
 * Upload Replays Page
 * Drag-and-drop bulk upload interface for SC2 replay files
 */
import { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Progress,
  Badge,
  Icon,
  Button,
  Card,
  CardBody,
  Collapse,
  IconButton,
  useColorModeValue,
  List,
  ListItem,
} from '@chakra-ui/react';
import {
  FiUploadCloud,
  FiCheckCircle,
  FiXCircle,
  FiAlertCircle,
  FiChevronDown,
  FiChevronUp,
  FiRefreshCw,
} from 'react-icons/fi';
import { useDropzone } from 'react-dropzone';
import { replaysApi } from '../api/endpoints';
import { useToast } from '../hooks/useToast';
import { parseErrorMessage, formatDate } from '../utils/formatting';

const UPLOAD_STATUS = {
  QUEUED: 'queued',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  COMPLETE: 'complete',
  DUPLICATE: 'duplicate',
  ERROR: 'error',
};

const UploadReplays = () => {
  const [files, setFiles] = useState([]);
  const [isExpanded, setIsExpanded] = useState(true);
  const toast = useToast();

  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const dropzoneBg = useColorModeValue('white', 'gray.800');
  const dropzoneBorder = useColorModeValue('gray.300', 'gray.600');

  // Check if any files are currently uploading
  const hasUploadsInProgress = files.some(
    (file) => file.status === UPLOAD_STATUS.UPLOADING || file.status === UPLOAD_STATUS.PROCESSING
  );

  // Warn user before leaving page if uploads are in progress
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasUploadsInProgress) {
        e.preventDefault();
        e.returnValue = 'Uploads are still in progress. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUploadsInProgress]);

  // Process a single file
  const processFile = async (file) => {
    // Update status to uploading
    updateFileStatus(file.id, UPLOAD_STATUS.UPLOADING, null, 0);

    try {
      // Upload the file with advanced metrics (required for match commentary)
      const response = await replaysApi.uploadAdvanced(file.file, (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        updateFileStatus(file.id, UPLOAD_STATUS.UPLOADING, null, percentCompleted);
      });

      // Mark as complete with processing stats
      const stats = response.data.processing_stats;
      const processingMessage = stats
        ? `Processed in ${stats.total_time_ms}ms (parse: ${stats.parse_time_ms}ms, ratings: ${stats.rating_update_time_ms}ms)`
        : response.data.message;

      updateFileStatus(
        file.id,
        UPLOAD_STATUS.COMPLETE,
        processingMessage,
        100,
        response.data
      );
    } catch (error) {
      if (error.isDuplicate) {
        updateFileStatus(
          file.id,
          UPLOAD_STATUS.DUPLICATE,
          error.userMessage || 'Replay already uploaded',
          100
        );
      } else {
        updateFileStatus(
          file.id,
          UPLOAD_STATUS.ERROR,
          parseErrorMessage(error),
          0
        );
      }
    }
  };

  // Update file status
  const updateFileStatus = (fileId, status, message, progress, data = null) => {
    setFiles((prevFiles) =>
      prevFiles.map((f) =>
        f.id === fileId
          ? { ...f, status, message, progress, data }
          : f
      )
    );
  };

  // Process files in batches
  const processFiles = async (filesToProcess) => {
    const batchSize = 5;
    const batches = [];

    // Create batches
    for (let i = 0; i < filesToProcess.length; i += batchSize) {
      batches.push(filesToProcess.slice(i, i + batchSize));
    }

    // Process batches sequentially, files within batch in parallel
    for (const batch of batches) {
      await Promise.all(batch.map((file) => processFile(file)));
    }
  };

  // Handle file drop
  const onDrop = useCallback(
    async (acceptedFiles) => {
      const newFiles = acceptedFiles
        .filter((file) => file.name.endsWith('.SC2Replay'))
        .map((file) => ({
          id: `${file.name}-${Date.now()}-${Math.random()}`,
          file,
          name: file.name,
          status: UPLOAD_STATUS.QUEUED,
          progress: 0,
          message: null,
          data: null,
        }));

      if (newFiles.length === 0) {
        toast.warning('Please upload .SC2Replay files only');
        return;
      }

      setFiles((prev) => [...prev, ...newFiles]);
      setIsExpanded(true);

      // Start processing
      await processFiles(newFiles);

      // Show summary toast - query current state to get accurate counts
      setFiles((currentFiles) => {
        const newFileIds = new Set(newFiles.map(f => f.id));
        const processedFiles = currentFiles.filter(f => newFileIds.has(f.id));

        const completed = processedFiles.filter((f) => f.status === UPLOAD_STATUS.COMPLETE).length;
        const duplicates = processedFiles.filter((f) => f.status === UPLOAD_STATUS.DUPLICATE).length;
        const errors = processedFiles.filter((f) => f.status === UPLOAD_STATUS.ERROR).length;

        toast.success(
          `Upload complete! ${completed} processed, ${duplicates} duplicates, ${errors} errors`
        );

        return currentFiles;
      });
    },
    [toast]
  );

  // Dropzone configuration
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/octet-stream': ['.SC2Replay'],
    },
    multiple: true,
  });

  // Retry failed file
  const retryFile = (fileId) => {
    updateFileStatus(fileId, UPLOAD_STATUS.QUEUED, null, 0);
    setFiles((currentFiles) => {
      const file = currentFiles.find((f) => f.id === fileId);
      if (file) {
        processFile(file);
      }
      return currentFiles;
    });
  };

  // Remove file from list
  const removeFile = (fileId) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  // Statistics
  const stats = {
    total: files.length,
    queued: files.filter((f) => f.status === UPLOAD_STATUS.QUEUED).length,
    uploading: files.filter((f) => f.status === UPLOAD_STATUS.UPLOADING).length,
    processing: files.filter((f) => f.status === UPLOAD_STATUS.PROCESSING).length,
    complete: files.filter((f) => f.status === UPLOAD_STATUS.COMPLETE).length,
    duplicate: files.filter((f) => f.status === UPLOAD_STATUS.DUPLICATE).length,
    error: files.filter((f) => f.status === UPLOAD_STATUS.ERROR).length,
  };

  const isUploading = stats.uploading > 0 || stats.processing > 0 || stats.queued > 0;
  const hasFiles = files.length > 0;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="xl" mb={2}>
            Upload Replays
          </Heading>
          <Text color="gray.500">
            Drag and drop your StarCraft 2 replay files or folders
          </Text>
        </Box>

        {/* Main Upload Area */}
        {(!hasFiles || !isUploading) && (
          <Box
            {...getRootProps()}
            bg={dropzoneBg}
            borderWidth={3}
            borderStyle="dashed"
            borderColor={isDragActive ? 'brand.500' : dropzoneBorder}
            borderRadius="xl"
            p={16}
            textAlign="center"
            cursor="pointer"
            transition="all 0.2s"
            _hover={{
              borderColor: 'brand.500',
              bg: useColorModeValue('brand.50', 'gray.700'),
            }}
          >
            <input {...getInputProps()} />
            <VStack spacing={4}>
              <Icon
                as={FiUploadCloud}
                boxSize={20}
                color={isDragActive ? 'brand.500' : 'gray.400'}
              />
              <Heading size="lg" color={isDragActive ? 'brand.500' : undefined}>
                {isDragActive
                  ? 'Drop your replays here!'
                  : 'Drag replay files or folders here'}
              </Heading>
              <Text color="gray.500" fontSize="lg">
                or click to browse
              </Text>
              <Badge colorScheme="blue" fontSize="md" px={3} py={1}>
                .SC2Replay files only
              </Badge>
            </VStack>
          </Box>
        )}

        {/* Upload Summary (when uploading) */}
        {hasFiles && (
          <Card>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <HStack justify="space-between">
                  <Heading size="md">
                    {isUploading
                      ? `Uploading ${stats.total} replays...`
                      : `Upload Complete`}
                  </Heading>
                  <IconButton
                    icon={isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                    variant="ghost"
                    onClick={() => setIsExpanded(!isExpanded)}
                    aria-label="Toggle details"
                  />
                </HStack>

                <HStack spacing={4} wrap="wrap">
                  <Badge colorScheme="green" fontSize="md">
                    {stats.complete} complete
                  </Badge>
                  {stats.duplicate > 0 && (
                    <Badge colorScheme="yellow" fontSize="md">
                      {stats.duplicate} duplicates
                    </Badge>
                  )}
                  {stats.error > 0 && (
                    <Badge colorScheme="red" fontSize="md">
                      {stats.error} errors
                    </Badge>
                  )}
                  {(stats.uploading > 0 || stats.processing > 0 || stats.queued > 0) && (
                    <Badge colorScheme="blue" fontSize="md">
                      {stats.uploading + stats.processing + stats.queued} remaining
                    </Badge>
                  )}
                </HStack>

                {isUploading && (
                  <Progress
                    value={(stats.complete / stats.total) * 100}
                    colorScheme="brand"
                    size="sm"
                    borderRadius="full"
                  />
                )}

                {/* File List */}
                <Collapse in={isExpanded}>
                  <List spacing={2} maxH="400px" overflowY="auto">
                    {files.map((file) => (
                      <FileItem
                        key={file.id}
                        file={file}
                        onRetry={retryFile}
                        onRemove={removeFile}
                      />
                    ))}
                  </List>
                </Collapse>

                {/* Actions */}
                {!isUploading && (
                  <HStack>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setFiles([])}
                    >
                      Clear All
                    </Button>
                    <Box
                      flex={1}
                      {...getRootProps()}
                      display="inline-block"
                    >
                      <input {...getInputProps()} />
                      <Button size="sm" variant="primary" width="auto">
                        Upload More Files
                      </Button>
                    </Box>
                  </HStack>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}
      </VStack>
    </Container>
  );
};

// File Item Component
const FileItem = ({ file, onRetry, onRemove }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case UPLOAD_STATUS.COMPLETE:
        return { icon: FiCheckCircle, color: 'green.500' };
      case UPLOAD_STATUS.DUPLICATE:
        return { icon: FiAlertCircle, color: 'yellow.500' };
      case UPLOAD_STATUS.ERROR:
        return { icon: FiXCircle, color: 'red.500' };
      default:
        return null;
    }
  };

  const statusIcon = getStatusIcon(file.status);

  return (
    <ListItem>
      <HStack
        spacing={3}
        p={3}
        bg={useColorModeValue('gray.50', 'gray.700')}
        borderRadius="md"
      >
        {/* Status Icon */}
        {statusIcon && <Icon as={statusIcon.icon} color={statusIcon.color} boxSize={5} />}

        {/* File Info */}
        <VStack flex={1} align="start" spacing={1}>
          <Text fontSize="sm" fontWeight="medium" noOfLines={1}>
            {file.name}
          </Text>

          {/* Progress Bar */}
          {(file.status === UPLOAD_STATUS.UPLOADING ||
            file.status === UPLOAD_STATUS.PROCESSING) && (
            <Progress
              value={file.progress}
              size="xs"
              colorScheme="brand"
              width="100%"
              borderRadius="full"
            />
          )}

          {/* Status Message */}
          {file.message && (
            <Text fontSize="xs" color="gray.500" noOfLines={2}>
              {file.message}
            </Text>
          )}

          {/* Match Details (for duplicates) */}
          {file.status === UPLOAD_STATUS.DUPLICATE && file.data && (
            <Text fontSize="xs" color="yellow.600">
              Already uploaded
            </Text>
          )}
        </VStack>

        {/* Actions */}
        <HStack>
          {file.status === UPLOAD_STATUS.ERROR && (
            <IconButton
              icon={<FiRefreshCw />}
              size="sm"
              variant="ghost"
              onClick={() => onRetry(file.id)}
              aria-label="Retry"
            />
          )}
          {(file.status === UPLOAD_STATUS.COMPLETE ||
            file.status === UPLOAD_STATUS.DUPLICATE ||
            file.status === UPLOAD_STATUS.ERROR) && (
            <IconButton
              icon={<FiXCircle />}
              size="sm"
              variant="ghost"
              onClick={() => onRemove(file.id)}
              aria-label="Remove"
            />
          )}
        </HStack>
      </HStack>
    </ListItem>
  );
};

export default UploadReplays;
