/**
 * GenerateButton Component - Team Generation Action Button
 * Displays button to generate teams and validation messages
 */
import { Box, Button, Text, VStack, HStack, Badge, Icon } from '@chakra-ui/react';
import { FiZap, FiCpu, FiPlus } from 'react-icons/fi';

interface GenerateButtonProps {
  canGenerate: boolean;
  isLoading: boolean;
  selectedPlayersCount: number;
  hasOddPlayers: boolean;
  minPlayers: number;
  onGenerate: () => void;
  aiSuggestion?: { difficulty: string; mmr: number } | null;
  onAddAI?: (difficulty: string, mmr: number) => void;
}

const GenerateButton: React.FC<GenerateButtonProps> = ({
  canGenerate,
  isLoading,
  selectedPlayersCount,
  hasOddPlayers,
  minPlayers,
  onGenerate,
  aiSuggestion,
  onAddAI,
}) => {
  return (
    <Box textAlign="center" py={8}>
      <VStack spacing={6}>
        {hasOddPlayers && aiSuggestion && (
          <Box
            bg="space.800"
            p={4}
            borderRadius="xl"
            border="2px dashed"
            borderColor="purple.500"
            maxW="lg"
            animation="fadeIn 0.5s ease-out"
          >
            <VStack spacing={3}>
              <HStack>
                <Icon as={FiCpu} color="purple.400" />
                <Text fontWeight="bold" color="purple.300" fontSize="sm" fontFamily="heading">
                  SMART AI SUGGESTION
                </Text>
              </HStack>
              <Text color="gray.400" fontSize="xs" textAlign="center">
                We detected uneven teams. Adding a <Text as="span" fontWeight="bold" color="white" textTransform="capitalize">
                {aiSuggestion.difficulty.replace('_', ' ')} AI</Text> would create the most balanced match based on current player MMRs.
              </Text>
              <Button
                size="sm"
                colorScheme="purple"
                variant="solid"
                leftIcon={<FiPlus />}
                onClick={() => onAddAI && onAddAI(aiSuggestion.difficulty, aiSuggestion.mmr)}
              >
                Add {aiSuggestion.difficulty.replace('_', ' ')} AI
              </Button>
            </VStack>
          </Box>
        )}

        <Button
          size="lg"
          variant="accent"
          isDisabled={!canGenerate}
          isLoading={isLoading}
          loadingText="Analyzing..."
          onClick={onGenerate}
          leftIcon={<FiZap />}
          px={16}
          py={8}
          fontSize="2xl"
          fontFamily="heading"
          fontWeight="black"
          letterSpacing="wider"
          position="relative"
          overflow="visible"
        >
          Generate Teams
        </Button>
      </VStack>

      {!canGenerate && selectedPlayersCount > 0 && (
        <Text
          color="gray.500"
          mt={4}
          fontSize="sm"
          fontFamily="heading"
        >
          Select {minPlayers - selectedPlayersCount} more player
          {minPlayers - selectedPlayersCount !== 1 ? 's' : ''}
        </Text>
      )}

      {canGenerate && hasOddPlayers && (
        <VStack spacing={2} mt={4}>
          <Text
            color="purple.400"
            fontSize="sm"
            fontFamily="heading"
          >
            Uneven Teams Detected
          </Text>
          <Text
            color="gray.500"
            fontSize="xs"
            fontFamily="heading"
            textAlign="center"
            maxW="md"
          >
            Teams will be unbalanced ({Math.ceil(selectedPlayersCount / 2)}v
            {Math.floor(selectedPlayersCount / 2)}). Consider adding 1 more
            player or adding an AI to balance.
          </Text>
        </VStack>
      )}
    </Box>
  );
};

export default GenerateButton;
