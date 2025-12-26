/**
 * EmptyState Component
 * Friendly messages for empty data scenarios
 */
import React from 'react';
import {
  Box,
  VStack,
  Heading,
  Text,
  Button,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiUploadCloud, FiUsers, FiBarChart } from 'react-icons/fi';
import type { IconType } from 'react-icons';

type EmptyStateVariant = 'upload' | 'players' | 'stats';

interface EmptyStateContent {
  title: string;
  description: string;
  actionLabel: string;
}

interface EmptyStateProps {
  variant?: EmptyStateVariant;
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: IconType;
}

const iconMap: Record<EmptyStateVariant, IconType> = {
  upload: FiUploadCloud,
  players: FiUsers,
  stats: FiBarChart,
};

const EmptyState: React.FC<EmptyStateProps> = ({
  variant = 'upload',
  title,
  description,
  actionLabel,
  onAction,
  icon: customIcon,
}) => {
  const bgColor = useColorModeValue('gray.50', 'gray.800');
  const IconComponent = customIcon || iconMap[variant] || FiUploadCloud;

  const defaultContent: Record<EmptyStateVariant, EmptyStateContent> = {
    upload: {
      title: 'Ready to Get Started?',
      description: 'Upload your StarCraft 2 replay files to start tracking your games, player stats, and team balancing.',
      actionLabel: 'Upload Replays',
    },
    players: {
      title: 'No Players Yet',
      description: 'Once you upload some replays, your players will appear here with their stats and ratings.',
      actionLabel: 'Upload Replays',
    },
    stats: {
      title: 'Need More Games',
      description: 'A few more matches will help us generate accurate statistics and predictions for you.',
      actionLabel: 'Upload More Replays',
    },
  };

  const content = defaultContent[variant] || defaultContent.upload;

  return (
    <Box
      bg={bgColor}
      borderRadius="xl"
      p={12}
      textAlign="center"
      borderWidth={2}
      borderStyle="dashed"
      borderColor="gray.600"
    >
      <VStack spacing={4}>
        <Icon
          as={IconComponent}
          boxSize={16}
          color="gray.500"
        />

        <Heading size="lg" color="gray.300">
          {title || content.title}
        </Heading>

        <Text color="gray.500" maxW="md">
          {description || content.description}
        </Text>

        {onAction && (
          <Button
            variant="primary"
            size="lg"
            mt={4}
            onClick={onAction}
          >
            {actionLabel || content.actionLabel}
          </Button>
        )}
      </VStack>
    </Box>
  );
};

export default EmptyState;
