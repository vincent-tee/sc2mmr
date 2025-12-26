/**
 * GenerateButton Component - Team Generation Action Button
 * Displays button to generate teams and validation messages
 */
import { Box, Button, Text, VStack } from '@chakra-ui/react';
import { FiZap } from 'react-icons/fi';

interface GenerateButtonProps {
  canGenerate: boolean;
  isLoading: boolean;
  selectedPlayersCount: number;
  hasOddPlayers: boolean;
  minPlayers: number;
  onGenerate: () => void;
}

const GenerateButton: React.FC<GenerateButtonProps> = ({
  canGenerate,
  isLoading,
  selectedPlayersCount,
  hasOddPlayers,
  minPlayers,
  onGenerate,
}) => {
  return (
    <Box textAlign="center" py={6}>
      <Button
        size="lg"
        variant="accent"
        isDisabled={!canGenerate}
        isLoading={isLoading}
        loadingText="Analyzing combinations..."
        onClick={onGenerate}
        leftIcon={<FiZap />}
        px={16}
        py={8}
        fontSize="2xl"
        fontFamily="heading"
        letterSpacing="wider"
        position="relative"
        overflow="visible"
        _before={{
          content: '""',
          position: 'absolute',
          top: -2,
          left: -2,
          right: -2,
          bottom: -2,
          background:
            'linear-gradient(45deg, transparent, rgba(255, 179, 0, 0.3), transparent)',
          animation: canGenerate ? 'shimmer 2s ease-in-out infinite' : 'none',
          borderRadius: 'md',
          zIndex: -1,
        }}
        sx={{
          '@keyframes shimmer': {
            '0%, 100%': { opacity: 0.5 },
            '50%': { opacity: 1 },
          },
        }}
      >
        Generate Teams
      </Button>

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
