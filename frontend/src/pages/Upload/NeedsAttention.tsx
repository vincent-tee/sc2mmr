import { Badge, Box, Button, Grid, HStack, Heading, Icon, Text, VStack } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink } from 'react-router-dom';
import { FiAlertCircle, FiArrowRight, FiCheckCircle, FiHelpCircle } from 'react-icons/fi';
import type { IconType } from 'react-icons';
import { replaysApi, type FailedUpload } from '../../api/endpoints';
import { matchResultsApi } from '../../api/matchResults';
import { formatDateOnly } from '../../utils/formatting';

const PENDING_FAILURES_LIMIT = 500;
const FAILURES_PREVIEWED = 3;

const readableErrorType = (errorType: string): string =>
  errorType.split('_').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

const Count: React.FC<{ value: number | undefined; label: string; tone?: string }> = ({ value, label, tone = 'gray.50' }) => (
  <HStack spacing={2} align="baseline">
    <Text fontFamily="mono" fontWeight="700" fontSize="2xl" color={value ? tone : 'gray.500'}>
      {value ?? '–'}
    </Text>
    <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="0.08em">
      {label}
    </Text>
  </HStack>
);

const AttentionCard: React.FC<{
  icon: IconType;
  title: string;
  isClear: boolean;
  clearText: string;
  to: string;
  linkLabel: string;
  children: React.ReactNode;
}> = ({ icon, title, isClear, clearText, to, linkLabel, children }) => (
  <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" p={{ base: 4, md: 5 }} minW={0}>
    <HStack spacing={2} mb={3}>
      <Icon as={isClear ? FiCheckCircle : icon} color={isClear ? 'green.400' : 'accent.400'} boxSize={4} />
      <Heading as="h3" size="sm" color="gray.100">{title}</Heading>
    </HStack>
    {isClear ? <Text fontSize="sm" color="gray.500">{clearText}</Text> : children}
    <Button
      as={RouterLink}
      to={to}
      size="sm"
      variant={isClear ? 'ghost' : 'outline'}
      colorScheme={isClear ? 'gray' : 'brand'}
      rightIcon={<FiArrowRight />}
      mt={4}
    >
      {linkLabel}
    </Button>
  </Box>
);

const FailedPreview: React.FC<{ uploads: FailedUpload[] }> = ({ uploads }) => (
  <VStack align="stretch" spacing={1} mt={3}>
    {uploads.slice(0, FAILURES_PREVIEWED).map((upload) => (
      <HStack key={upload.id} spacing={3} fontSize="xs" minW={0}>
        <Text flex={1} minW={0} color="gray.300" noOfLines={1} wordBreak="break-all">{upload.filename}</Text>
        <Badge variant="subtle" colorScheme={upload.error_type === 'winner_determination' ? 'orange' : 'red'} fontSize="2xs" flexShrink={0}>
          {readableErrorType(upload.error_type)}
        </Badge>
        <Text fontFamily="mono" color="gray.500" flexShrink={0} display={{ base: 'none', sm: 'block' }}>
          {formatDateOnly(upload.uploaded_at)}
        </Text>
      </HStack>
    ))}
  </VStack>
);

const NeedsAttention: React.FC = () => {
  const failed = useQuery({
    queryKey: ['failed-uploads', 'pending-summary'],
    queryFn: async () => (await replaysApi.getFailedUploads(PENDING_FAILURES_LIMIT, 0, null, false)).data,
  });
  const review = useQuery({
    queryKey: ['result-review'],
    queryFn: async () => (await matchResultsApi.reviewQueue()).data,
  });

  const pendingFailures = failed.data ?? [];
  const needsWinner = pendingFailures.filter((u) => u.error_type === 'winner_determination').length;

  return (
    <Box as="section" aria-labelledby="needs-attention-heading">
      <Heading id="needs-attention-heading" as="h2" size="md" color="gray.100" mb={3}>
        Needs attention
      </Heading>
      <Grid templateColumns={{ base: '1fr', md: '1fr 1fr' }} gap={4}>
        <AttentionCard
          icon={FiHelpCircle}
          title="Results to review"
          isClear={review.isSuccess && review.data.total === 0}
          clearText="Every rated game has a recorded or confirmed result."
          to="/results-review"
          linkLabel="Review results"
        >
          <HStack spacing={5} flexWrap="wrap">
            <Count value={review.data?.total} label="Suggested" />
            <Count value={review.data?.conflicts} label="Doubtful" tone="yellow.300" />
          </HStack>
          <Text fontSize="sm" color="gray.500" mt={2}>
            These replays didn&apos;t record a winner, so one was suggested from team stats.
            Confirming needs the admin token.
          </Text>
          {review.data && review.data.unchecked > 0 && (
            <Text fontSize="sm" color="gray.500" mt={1}>
              <Text as="span" fontFamily="mono">{review.data.unchecked}</Text> older games not checked yet.
            </Text>
          )}
          {review.isError && <Text fontSize="sm" color="red.300" mt={2}>Couldn&apos;t load the review queue.</Text>}
        </AttentionCard>

        <AttentionCard
          icon={FiAlertCircle}
          title="Failed uploads"
          isClear={failed.isSuccess && pendingFailures.length === 0}
          clearText="No failed uploads waiting for review."
          to="/failed-uploads"
          linkLabel="Open failed uploads"
        >
          <HStack spacing={5} flexWrap="wrap">
            <Count value={failed.data?.length} label="Not reviewed" tone="red.300" />
            {needsWinner > 0 && <Count value={needsWinner} label="Need a winner" tone="orange.300" />}
          </HStack>
          <FailedPreview uploads={pendingFailures} />
          {failed.isError && <Text fontSize="sm" color="red.300" mt={2}>Couldn&apos;t load failed uploads.</Text>}
        </AttentionCard>
      </Grid>
    </Box>
  );
};

export default NeedsAttention;
