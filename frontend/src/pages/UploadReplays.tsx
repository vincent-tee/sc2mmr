/**
 * Upload Replays Page - Friend Squad Edition
 * Drag-and-drop bulk upload interface with comic-book styling
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
  Collapse,
  IconButton,
  Link,
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
import { useDropzone, type FileRejection } from 'react-dropzone';
import { Link as RouterLink } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { replaysApi } from '../api/endpoints';
import PageHeader from '../components/PageHeader';
import type { ApiClientError } from '../api/client';
import { useToast } from '../hooks/useToast';
import { parseErrorMessage } from '../utils/formatting';
import type { ReplayUploadResponse } from '../types/api';
import type { IconType } from 'react-icons';

// Design tokens
const cardBg = 'space.800';
const borderColor = 'space.900';
const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';

// Upload status enum
const UPLOAD_STATUS = {
  QUEUED: 'queued',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  COMPLETE: 'complete',
  DUPLICATE: 'duplicate',
  ERROR: 'error',
} as const;

type UploadStatusType = typeof UPLOAD_STATUS[keyof typeof UPLOAD_STATUS];

// File upload state interface
interface UploadFile {
  id: string;
  file: File;
  name: string;
  status: UploadStatusType;
  progress: number;
  message: string | null;
  data: ReplayUploadResponse | null;
}

// Error with custom properties
interface UploadError extends Error {
  isDuplicate?: boolean;
  userMessage?: string;
}

// Props for FileItem component
interface FileItemProps {
  file: UploadFile;
  onRetry: (fileId: string) => void;
  onRemove: (fileId: string) => void;
}

const UploadReplays: React.FC = () => {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const toast = useToast();
  const queryClient = useQueryClient();

  // Check if any files are currently uploading
  const hasUploadsInProgress = files.some(
    (file) => file.status === UPLOAD_STATUS.UPLOADING || file.status === UPLOAD_STATUS.PROCESSING
  );

  // Warn user before leaving page if uploads are in progress
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent): string | void => {
      if (hasUploadsInProgress) {
        e.preventDefault();
        e.returnValue = 'Uploads are still in progress. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUploadsInProgress]);

  // Update file status
  const updateFileStatus = (
    fileId: string,
    status: UploadStatusType,
    message: string | null,
    progress: number,
    data: ReplayUploadResponse | null = null
  ): void => {
    setFiles((prevFiles) =>
      prevFiles.map((f) =>
        f.id === fileId
          ? { ...f, status, message, progress, data }
          : f
      )
    );
  };

  // Process a single file
  const processFile = async (file: UploadFile): Promise<void> => {
    updateFileStatus(file.id, UPLOAD_STATUS.UPLOADING, null, 0);

    try {
      const response = await replaysApi.uploadAdvanced(file.file, (progressEvent) => {
        const total = progressEvent.total || 1;
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / total
        );
        updateFileStatus(file.id, UPLOAD_STATUS.UPLOADING, null, percentCompleted);
      });

      const responseData = response.data as ReplayUploadResponse & {
        processing_stats?: { total_time_ms: number; parse_time_ms: number; rating_update_time_ms: number }
      };
      const stats = responseData.processing_stats;
      const processingMessage = stats
        ? `Processed in ${stats.total_time_ms}ms`
        : response.data.message;

      updateFileStatus(
        file.id,
        UPLOAD_STATUS.COMPLETE,
        processingMessage,
        100,
        response.data
      );

      queryClient.invalidateQueries({ queryKey: ['matches'] });
      queryClient.invalidateQueries({ queryKey: ['players'] });
      queryClient.invalidateQueries({ queryKey: ['recent-matches-ticker'] });
    } catch (error) {
      const uploadError = error as UploadError;
      if (uploadError.isDuplicate) {
        updateFileStatus(
          file.id,
          UPLOAD_STATUS.DUPLICATE,
          uploadError.userMessage || 'Replay already uploaded',
          100
        );
      } else {
        updateFileStatus(
          file.id,
          UPLOAD_STATUS.ERROR,
          parseErrorMessage(error as ApiClientError),
          0
        );
      }
    }
  };

  // Process files in batches
  const processFiles = async (filesToProcess: UploadFile[]): Promise<void> => {
    const batchSize = 5;
    const batches: UploadFile[][] = [];

    for (let i = 0; i < filesToProcess.length; i += batchSize) {
      batches.push(filesToProcess.slice(i, i + batchSize));
    }

    for (const batch of batches) {
      await Promise.all(batch.map((file) => processFile(file)));
    }
  };

  // Handle file drop
  const onDrop = useCallback(
    async (acceptedFiles: File[], _fileRejections: FileRejection[]) => {
      const newFiles: UploadFile[] = acceptedFiles
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

      await processFiles(newFiles);

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
  const retryFile = (fileId: string): void => {
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
  const removeFile = (fileId: string): void => {
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
    <Box minH="100vh" pb={16}>
      <PageHeader
        kicker="Fresh Data"
        title="Upload [Replays]"
        description="Drag and drop your StarCraft II replay files or folders — ratings update automatically."
      />
      <Container maxW="container.xl" pt={8}>
      <VStack spacing={8} align="stretch">
        {/* Main Upload Area */}
        {(!hasFiles || !isUploading) && (
          <Box
            {...getRootProps()}
            bg={cardBg}
            borderWidth={3}
            borderStyle="dashed"
            borderColor={isDragActive ? 'brand.500' : 'space.600'}
            borderRadius="xl"
            p={16}
            textAlign="center"
            cursor="pointer"
            transition="all 0.2s cubic-bezier(0.68, -0.35, 0.265, 1.35)"
            _hover={{
              borderColor: 'brand.500',
              transform: 'translateY(-2px)',
              boxShadow: brandShadow,
            }}
          >
            <input {...getInputProps()} />
            <VStack spacing={4}>
              <Icon
                as={FiUploadCloud}
                boxSize={20}
                color={isDragActive ? 'brand.500' : 'gray.500'}
              />
              <Heading
                size="lg"
                fontFamily="heading"
                letterSpacing="wide"
                color={isDragActive ? 'brand.400' : 'gray.300'}
              >
                {isDragActive
                  ? 'Drop your replays here!'
                  : 'Drag replay files or folders here'}
              </Heading>
              <Text color="gray.500" fontSize="lg">
                or click to browse
              </Text>
              <Text
                fontFamily="mono"
                fontSize="xs"
                color="gray.600"
                textTransform="uppercase"
                letterSpacing="wider"
              >
                .SC2Replay files only
              </Text>
            </VStack>
          </Box>
        )}

        {/* Upload Summary */}
        {hasFiles && (
          <Box
            bg={cardBg}
            borderRadius="xl"
            border="3px solid"
            borderColor={borderColor}
            boxShadow={brandShadow}
            p={6}
          >
            <VStack spacing={4} align="stretch">
              <HStack justify="space-between">
                <Heading size="md" fontFamily="heading" letterSpacing="wide" color="gray.200">
                  {isUploading
                    ? `Uploading ${stats.total} replays...`
                    : 'Upload Complete'}
                </Heading>
                <IconButton
                  icon={isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                  variant="ghost"
                  onClick={() => setIsExpanded(!isExpanded)}
                  aria-label="Toggle details"
                  color="gray.400"
                  _hover={{ color: 'brand.400' }}
                />
              </HStack>

              <HStack spacing={3} wrap="wrap">
                <Badge bg="green.500" color="white" fontSize="sm" px={3} py={1} borderRadius="full">
                  {stats.complete} complete
                </Badge>
                {stats.duplicate > 0 && (
                  <Badge bg="yellow.500" color="white" fontSize="sm" px={3} py={1} borderRadius="full">
                    {stats.duplicate} duplicates
                  </Badge>
                )}
                {stats.error > 0 && (
                  <Badge bg="red.500" color="white" fontSize="sm" px={3} py={1} borderRadius="full">
                    {stats.error} errors
                  </Badge>
                )}
                {(stats.uploading > 0 || stats.processing > 0 || stats.queued > 0) && (
                  <Badge bg="blue.500" color="white" fontSize="sm" px={3} py={1} borderRadius="full">
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
                  bg="space.900"
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
                <HStack spacing={3}>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setFiles([])}
                    borderColor="space.600"
                    color="gray.400"
                    _hover={{ bg: 'space.700' }}
                  >
                    Clear All
                  </Button>
                  <Box
                    flex={1}
                    {...getRootProps()}
                    display="inline-block"
                  >
                    <input {...getInputProps()} />
                    <Button
                      size="sm"
                      bg="brand.500"
                      color="white"
                      _hover={{ bg: 'brand.600' }}
                    >
                      Upload More Files
                    </Button>
                  </Box>
                </HStack>
              )}
            </VStack>
          </Box>
        )}

        {/* Companion link to failed uploads */}
        <HStack justify="center" spacing={2} color="gray.500" fontSize="sm">
          <Icon as={FiAlertCircle} boxSize={4} />
          <Text>A replay didn't go through?</Text>
          <Link
            as={RouterLink}
            to="/failed-uploads"
            color="brand.400"
            fontWeight="medium"
            _hover={{ color: 'brand.300', textDecoration: 'underline' }}
          >
            Review failed uploads
          </Link>
        </HStack>
      </VStack>
      </Container>
    </Box>
  );
};

// File Item Component
const FileItem: React.FC<FileItemProps> = ({ file, onRetry, onRemove }) => {
  const getStatusIcon = (status: UploadStatusType): { icon: IconType; color: string } | null => {
    switch (status) {
      case UPLOAD_STATUS.COMPLETE:
        return { icon: FiCheckCircle, color: 'green.400' };
      case UPLOAD_STATUS.DUPLICATE:
        return { icon: FiAlertCircle, color: 'yellow.400' };
      case UPLOAD_STATUS.ERROR:
        return { icon: FiXCircle, color: 'red.400' };
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
        bg="space.700"
        borderRadius="lg"
        border="2px solid"
        borderColor="space.600"
      >
        {/* Status Icon */}
        {statusIcon && <Icon as={statusIcon.icon} color={statusIcon.color} boxSize={5} />}

        {/* File Info */}
        <VStack flex={1} align="start" spacing={1}>
          <Text fontSize="sm" fontWeight="medium" color="gray.200" noOfLines={1}>
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
              bg="space.900"
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
            <Text fontSize="xs" color="yellow.400">
              Already uploaded
            </Text>
          )}

          {/* Match Result (for completed uploads) */}
          {file.status === UPLOAD_STATUS.COMPLETE && file.data && (
            <HStack spacing={2} fontSize="xs" color="gray.500" flexWrap="wrap">
              {file.data.map_name && <Text noOfLines={1}>{file.data.map_name}</Text>}
              {file.data.game_mode && (
                <Badge bg="space.900" color="gray.400" fontSize="2xs" px={1.5}>
                  {file.data.game_mode}
                </Badge>
              )}
              <Link
                as={RouterLink}
                to={`/history/${file.data.match_id}`}
                color="brand.400"
                fontWeight="medium"
                _hover={{ color: 'brand.300', textDecoration: 'underline' }}
              >
                View match
              </Link>
            </HStack>
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
              color="gray.400"
              _hover={{ color: 'brand.400' }}
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
              color="gray.400"
              _hover={{ color: 'red.400' }}
            />
          )}
        </HStack>
      </HStack>
    </ListItem>
  );
};

export default UploadReplays;
