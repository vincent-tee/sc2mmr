/**
 * Upload hub: drop replays, see what each one became, and what still needs a person.
 */
import { useState, useEffect, useLayoutEffect, useRef } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Flex,
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
  FiLock,
  FiArrowRight,
} from 'react-icons/fi';
import { useDropzone } from 'react-dropzone';
import { Link as RouterLink } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { replaysApi } from '../api/endpoints';
import PageHeader from '../components/PageHeader';
import type { ApiClientError } from '../api/client';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../components/AuthGate';
import { parseErrorMessage } from '../utils/formatting';
import type { ReplayUploadResponse } from '../types/api';
import type { IconType } from 'react-icons';
import NeedsAttention from './Upload/NeedsAttention';

const cardBg = 'space.800';
const BATCH_SIZE = 5;

const UPLOAD_STATUS = {
  QUEUED: 'queued',
  UPLOADING: 'uploading',
  COMPLETE: 'complete',
  DUPLICATE: 'duplicate',
  ERROR: 'error',
} as const;

type UploadStatusType = typeof UPLOAD_STATUS[keyof typeof UPLOAD_STATUS];

interface UploadFile {
  id: string;
  file: File;
  name: string;
  status: UploadStatusType;
  progress: number;
  message: string | null;
  data: ReplayUploadResponse | null;
}

interface FileItemProps {
  file: UploadFile;
  onRetry: (fileId: string) => void;
  onRemove: (fileId: string) => void;
}

const toUploadFile = (file: File): UploadFile => ({
  id: `${file.name}-${Date.now()}-${Math.random()}`,
  file,
  name: file.name,
  status: UPLOAD_STATUS.QUEUED,
  progress: 0,
  message: null,
  data: null,
});

const plural = (count: number, word: string): string => `${count} ${word}${count === 1 ? '' : 's'}`;

const UploadReplays: React.FC = () => {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [awaitingSignIn, setAwaitingSignIn] = useState<UploadFile[]>([]);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const toast = useToast();
  const queryClient = useQueryClient();
  const { authEnabled, authenticated, requireLogin } = useAuth();
  const mustSignIn = authEnabled && !authenticated;

  const hasUploadsInProgress = files.some(
    (file) => file.status === UPLOAD_STATUS.UPLOADING || file.status === UPLOAD_STATUS.QUEUED
  );

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent): string | void => {
      if (hasUploadsInProgress || awaitingSignIn.length > 0) {
        e.preventDefault();
        e.returnValue = 'Replays are still waiting to upload. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUploadsInProgress, awaitingSignIn.length]);

  const updateFile = (fileId: string, changes: Partial<UploadFile>): void => {
    setFiles((prevFiles) => prevFiles.map((f) => (f.id === fileId ? { ...f, ...changes } : f)));
  };

  const refreshDerivedQueries = (): void => {
    queryClient.invalidateQueries({ queryKey: ['matches'] });
    queryClient.invalidateQueries({ queryKey: ['players'] });
    queryClient.invalidateQueries({ queryKey: ['recent-matches-ticker'] });
    queryClient.invalidateQueries({ queryKey: ['failed-uploads'] });
    queryClient.invalidateQueries({ queryKey: ['result-review'] });
  };

  const processFile = async (file: UploadFile): Promise<UploadStatusType> => {
    updateFile(file.id, { status: UPLOAD_STATUS.UPLOADING, message: null, progress: 0, data: null });

    try {
      const response = await replaysApi.uploadAdvanced(file.file, (progressEvent) => {
        const total = progressEvent.total || 1;
        updateFile(file.id, { progress: Math.round((progressEvent.loaded * 100) / total) });
      });

      const responseData = response.data as ReplayUploadResponse & {
        processing_stats?: { total_time_ms: number };
      };
      const wasAlreadyRecorded = responseData.created === false;
      const status = wasAlreadyRecorded ? UPLOAD_STATUS.DUPLICATE : UPLOAD_STATUS.COMPLETE;
      const processedIn = responseData.processing_stats
        ? `Processed in ${responseData.processing_stats.total_time_ms}ms`
        : responseData.message;
      updateFile(file.id, {
        status,
        message: wasAlreadyRecorded ? 'Already recorded - existing match refreshed' : processedIn,
        progress: 100,
        data: responseData,
      });
      return status;
    } catch (error) {
      const uploadError = error as ApiClientError;
      if (uploadError.isDuplicate) {
        updateFile(file.id, {
          status: UPLOAD_STATUS.DUPLICATE,
          message: uploadError.userMessage || 'Replay already uploaded',
          progress: 100,
        });
        return UPLOAD_STATUS.DUPLICATE;
      }
      updateFile(file.id, {
        status: UPLOAD_STATUS.ERROR,
        message: parseErrorMessage(uploadError),
        progress: 0,
      });
      return UPLOAD_STATUS.ERROR;
    }
  };

  const startUploads = async (newFiles: UploadFile[]): Promise<void> => {
    setFiles((prev) => [...prev, ...newFiles]);
    setIsExpanded(true);

    const outcomes: UploadStatusType[] = [];
    for (let i = 0; i < newFiles.length; i += BATCH_SIZE) {
      outcomes.push(...(await Promise.all(newFiles.slice(i, i + BATCH_SIZE).map(processFile))));
    }
    refreshDerivedQueries();

    const count = (status: UploadStatusType) => outcomes.filter((o) => o === status).length;
    const summary = [
      `${count(UPLOAD_STATUS.COMPLETE)} new`,
      `${count(UPLOAD_STATUS.DUPLICATE)} already recorded`,
      plural(count(UPLOAD_STATUS.ERROR), 'error'),
    ].join(', ');
    if (count(UPLOAD_STATUS.ERROR) > 0) {
      toast.warning(summary, 'Upload finished');
    } else {
      toast.success(summary, 'Upload finished');
    }
  };

  const startUploadsRef = useRef(startUploads);
  useLayoutEffect(() => {
    startUploadsRef.current = startUploads;
  });

  useEffect(() => {
    if (mustSignIn || awaitingSignIn.length === 0) return;
    const signedInBatch = awaitingSignIn;
    setAwaitingSignIn([]);
    startUploadsRef.current(signedInBatch);
  }, [mustSignIn, awaitingSignIn]);

  const onDrop = (acceptedFiles: File[]): void => {
    const newFiles = acceptedFiles.filter((file) => file.name.endsWith('.SC2Replay')).map(toUploadFile);

    if (newFiles.length === 0) {
      toast.warning('Please upload .SC2Replay files only');
      return;
    }

    if (mustSignIn) {
      setAwaitingSignIn((prev) => [...prev, ...newFiles]);
      requireLogin();
      return;
    }

    startUploads(newFiles);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/octet-stream': ['.SC2Replay'],
    },
    multiple: true,
  });

  const retryFile = async (fileId: string): Promise<void> => {
    const file = files.find((f) => f.id === fileId);
    if (!file) return;
    if (mustSignIn) {
      requireLogin();
      return;
    }
    await processFile(file);
    refreshDerivedQueries();
  };

  const removeFile = (fileId: string): void => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const countOf = (status: UploadStatusType) => files.filter((f) => f.status === status).length;
  const stats = {
    total: files.length,
    remaining: countOf(UPLOAD_STATUS.QUEUED) + countOf(UPLOAD_STATUS.UPLOADING),
    complete: countOf(UPLOAD_STATUS.COMPLETE),
    duplicate: countOf(UPLOAD_STATUS.DUPLICATE),
    error: countOf(UPLOAD_STATUS.ERROR),
  };
  const finished = stats.complete + stats.duplicate + stats.error;
  const isUploading = stats.remaining > 0;
  const hasFiles = files.length > 0;

  return (
    <Box minH="100vh" pb={16}>
      <PageHeader
        kicker="Fresh Data"
        title="Upload [Replays]"
        description="Drop StarCraft II replay files or folders — ratings update automatically. Anything that needs a person is listed below."
      />
      <Container maxW="container.xl" pt={8}>
      <VStack spacing={8} align="stretch">
        {!isUploading && (
          <Box
            {...getRootProps()}
            bg={cardBg}
            borderWidth={2}
            borderStyle="dashed"
            borderColor={isDragActive ? 'brand.500' : 'space.600'}
            borderRadius="xl"
            px={{ base: 6, md: 16 }}
            py={hasFiles ? { base: 6, md: 8 } : { base: 10, md: 16 }}
            textAlign="center"
            cursor="pointer"
            transition="border-color 0.2s, transform 0.2s"
            _hover={{
              borderColor: 'brand.500',
              transform: 'translateY(-2px)',
            }}
          >
            <input {...getInputProps()} />
            <VStack spacing={hasFiles ? 2 : 4}>
              <Icon
                as={FiUploadCloud}
                boxSize={hasFiles ? 10 : 16}
                color={isDragActive ? 'brand.500' : 'gray.500'}
              />
              <Heading
                size={hasFiles ? 'md' : 'lg'}
                fontFamily="heading"
                letterSpacing="wide"
                color={isDragActive ? 'brand.400' : 'gray.300'}
              >
                {isDragActive
                  ? 'Drop your replays here'
                  : hasFiles
                    ? 'Drop more replays'
                    : 'Drag replay files or folders here'}
              </Heading>
              <Text color="gray.500" fontSize={hasFiles ? 'sm' : 'lg'}>
                or click to browse
              </Text>
              {mustSignIn ? (
                <HStack spacing={1.5} color="accent.400" fontSize="sm">
                  <Icon as={FiLock} boxSize={3.5} />
                  <Text>You&apos;ll be asked to sign in before anything is sent</Text>
                </HStack>
              ) : (
                <Text
                  fontFamily="mono"
                  fontSize="xs"
                  color="gray.600"
                  textTransform="uppercase"
                  letterSpacing="wider"
                >
                  .SC2Replay files only
                </Text>
              )}
            </VStack>
          </Box>
        )}

        {awaitingSignIn.length > 0 && (
          <Flex
            bg={cardBg}
            border="1px solid"
            borderColor="accent.600"
            borderRadius="xl"
            p={4}
            gap={3}
            align={{ base: 'stretch', sm: 'center' }}
            direction={{ base: 'column', sm: 'row' }}
          >
            <HStack spacing={3} flex={1} minW={0}>
              <Icon as={FiLock} color="accent.400" boxSize={5} flexShrink={0} />
              <Text fontSize="sm" color="gray.200">
                <Text as="span" fontFamily="mono" fontWeight="700">{awaitingSignIn.length}</Text>
                {' '}{awaitingSignIn.length === 1 ? 'replay is' : 'replays are'} waiting — sign in to upload{' '}
                {awaitingSignIn.length === 1 ? 'it' : 'them'}.
              </Text>
            </HStack>
            <HStack spacing={2}>
              <Button size="sm" colorScheme="brand" onClick={() => requireLogin()}>
                Sign in to upload
              </Button>
              <Button size="sm" variant="ghost" color="gray.400" onClick={() => setAwaitingSignIn([])}>
                Discard
              </Button>
            </HStack>
          </Flex>
        )}

        {hasFiles && (
          <Box
            bg={cardBg}
            borderRadius="xl"
            border="1px solid"
            borderColor="whiteAlpha.100"
            p={{ base: 4, md: 6 }}
          >
            <VStack spacing={4} align="stretch">
              <HStack justify="space-between">
                <Heading size="md" fontFamily="heading" letterSpacing="wide" color="gray.200">
                  {isUploading ? 'Uploading' : 'This session'}
                  <Text as="span" fontFamily="mono" fontSize="sm" color="gray.500" ml={2}>
                    {finished}/{stats.total}
                  </Text>
                </Heading>
                <IconButton
                  icon={isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                  variant="ghost"
                  onClick={() => setIsExpanded(!isExpanded)}
                  aria-label={isExpanded ? 'Hide replays' : 'Show replays'}
                  color="gray.400"
                  _hover={{ color: 'brand.400' }}
                />
              </HStack>

              <HStack spacing={2} wrap="wrap">
                {stats.complete > 0 && (
                  <Badge colorScheme="green" variant="subtle" fontSize="xs" px={2} py={0.5} borderRadius="full">
                    <Text as="span" fontFamily="mono">{stats.complete}</Text> new
                  </Badge>
                )}
                {stats.duplicate > 0 && (
                  <Badge colorScheme="gray" variant="subtle" fontSize="xs" px={2} py={0.5} borderRadius="full">
                    <Text as="span" fontFamily="mono">{stats.duplicate}</Text> already recorded
                  </Badge>
                )}
                {stats.error > 0 && (
                  <Badge colorScheme="red" variant="subtle" fontSize="xs" px={2} py={0.5} borderRadius="full">
                    <Text as="span" fontFamily="mono">{stats.error}</Text> failed
                  </Badge>
                )}
                {isUploading && (
                  <Badge colorScheme="blue" variant="subtle" fontSize="xs" px={2} py={0.5} borderRadius="full">
                    <Text as="span" fontFamily="mono">{stats.remaining}</Text> remaining
                  </Badge>
                )}
              </HStack>

              {isUploading && (
                <Progress
                  value={(finished / stats.total) * 100}
                  colorScheme="brand"
                  size="sm"
                  borderRadius="full"
                  bg="space.900"
                />
              )}

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
                    Clear list
                  </Button>
                  {stats.error > 0 && (
                    <Text fontSize="xs" color="gray.500">
                      Replays that fail to process also appear under failed uploads below.
                    </Text>
                  )}
                </HStack>
              )}
            </VStack>
          </Box>
        )}

        <NeedsAttention />
      </VStack>
      </Container>
    </Box>
  );
};

const STATUS_ICON: Partial<Record<UploadStatusType, { icon: IconType; color: string }>> = {
  [UPLOAD_STATUS.COMPLETE]: { icon: FiCheckCircle, color: 'green.400' },
  [UPLOAD_STATUS.DUPLICATE]: { icon: FiAlertCircle, color: 'gray.400' },
  [UPLOAD_STATUS.ERROR]: { icon: FiXCircle, color: 'red.400' },
};

const FileItem: React.FC<FileItemProps> = ({ file, onRetry, onRemove }) => {
  const statusIcon = STATUS_ICON[file.status];
  const isDone = file.status !== UPLOAD_STATUS.QUEUED && file.status !== UPLOAD_STATUS.UPLOADING;
  const match = file.data;

  return (
    <ListItem>
      <HStack
        spacing={3}
        p={3}
        bg="space.700"
        borderRadius="lg"
        border="1px solid"
        borderColor="whiteAlpha.100"
        align="start"
      >
        {statusIcon && <Icon as={statusIcon.icon} color={statusIcon.color} boxSize={5} mt={0.5} flexShrink={0} />}

        <VStack flex={1} minW={0} align="stretch" spacing={1}>
          {match ? (
            <HStack spacing={2} minW={0} flexWrap="wrap">
              <Text fontSize="sm" fontWeight="semibold" color="gray.100" noOfLines={1}>
                {match.map_name || 'Unknown map'}
              </Text>
              {match.game_mode && (
                <Badge bg="space.900" color="gray.400" fontSize="2xs" px={1.5}>
                  {match.game_mode}
                </Badge>
              )}
            </HStack>
          ) : null}

          <Text fontSize="xs" color={match ? 'gray.500' : 'gray.200'} noOfLines={1} wordBreak="break-all">
            {file.name}
          </Text>

          {file.status === UPLOAD_STATUS.UPLOADING && (
            <Progress
              value={file.progress}
              size="xs"
              colorScheme="brand"
              width="100%"
              borderRadius="full"
              bg="space.900"
            />
          )}

          {file.message && (
            <Text fontSize="xs" color={file.status === UPLOAD_STATUS.ERROR ? 'red.300' : 'gray.500'} noOfLines={2}>
              {file.message}
            </Text>
          )}

          {match && (
            <Link
              as={RouterLink}
              to={`/history/${match.match_id}`}
              fontSize="xs"
              color="brand.400"
              fontWeight="medium"
              display="inline-flex"
              alignItems="center"
              gap={1}
              alignSelf="start"
              _hover={{ color: 'brand.300', textDecoration: 'underline' }}
            >
              Open match <Text as="span" fontFamily="mono">#{match.match_id}</Text>
              <Icon as={FiArrowRight} boxSize={3} />
            </Link>
          )}
        </VStack>

        <HStack spacing={0} flexShrink={0}>
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
          {isDone && (
            <IconButton
              icon={<FiXCircle />}
              size="sm"
              variant="ghost"
              onClick={() => onRemove(file.id)}
              aria-label="Remove from list"
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
