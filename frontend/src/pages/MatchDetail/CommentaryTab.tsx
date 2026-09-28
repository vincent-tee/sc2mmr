/**
 * CommentaryTab Component - short written recap: overview, key moments and MVP
 */
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Badge,
  Icon,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { FiAward } from 'react-icons/fi';
import LoadingState from '@/components/LoadingState';
import type { MatchCommentary } from './types';

interface CommentaryTabProps {
  commentary: MatchCommentary | undefined;
  isLoading: boolean;
}

const CommentaryTab: React.FC<CommentaryTabProps> = ({ commentary, isLoading }) => {
  if (isLoading) {
    return <LoadingState message="Writing the recap..." />;
  }

  if (!commentary || commentary.error) {
    return (
      <Alert status="info" borderRadius="lg">
        <AlertIcon />
        A recap isn't available for this match.
      </Alert>
    );
  }

  const mvp = commentary.mvp_analysis;

  return (
    <Box bg="space.800" border="1px solid" borderColor="whiteAlpha.100" borderRadius="xl" p={{ base: 4, md: 6 }}>
      <VStack align="stretch" spacing={5}>
        {commentary.overview && <Text color="gray.200" lineHeight="tall">{commentary.overview}</Text>}

        {mvp && (
          <HStack align="start" spacing={3} p={4} bg="whiteAlpha.50" borderRadius="lg" borderLeft="3px solid" borderLeftColor="shield.400">
            <Icon as={FiAward} color="shield.400" boxSize={5} mt={0.5} />
            <Box>
              <HStack spacing={2} mb={1} flexWrap="wrap">
                <Text fontWeight="bold" color="gray.50">MVP: {mvp.player_name}</Text>
                <Badge variant="subtle" colorScheme="yellow">Team {mvp.team}</Badge>
                {mvp.impact_score !== null && (
                  <Badge variant="subtle" colorScheme="green" fontFamily="mono">Impact {mvp.impact_score.toFixed(1)}</Badge>
                )}
              </HStack>
              <Text fontSize="sm" color="gray.400">{mvp.reasoning}</Text>
            </Box>
          </HStack>
        )}

        {commentary.key_moments && commentary.key_moments.length > 0 && (
          <Box>
            <Heading size="xs" color="gray.500" textTransform="uppercase" letterSpacing="widest" mb={2}>
              Key moments
            </Heading>
            <VStack align="stretch" spacing={2}>
              {commentary.key_moments.map((moment) => (
                <Text key={moment} fontSize="sm" color="gray.300" pl={3} borderLeft="2px solid" borderColor="brand.500">
                  {moment}
                </Text>
              ))}
            </VStack>
          </Box>
        )}

        {commentary.match_summary && <Text fontSize="sm" color="gray.400">{commentary.match_summary}</Text>}
      </VStack>
    </Box>
  );
};

export default CommentaryTab;
