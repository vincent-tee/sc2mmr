/**
 * BalanceResults Component - the suggested splits, one editable at a time
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, ButtonGroup, Flex, Heading, HStack, Text } from '@chakra-ui/react';
import { FiChevronUp, FiCopy, FiUpload } from 'react-icons/fi';
import type { TeamSuggestionWithImpact } from '@/types/api';
import TeamEditor from './TeamEditor';

interface BalanceResultsProps {
  suggestions: TeamSuggestionWithImpact[];
  title: string;
  onExport: (suggestion: TeamSuggestionWithImpact, format: 'text' | 'download') => Promise<void>;
  onExportAll: () => Promise<void>;
  onClear: () => void;
}

const optionLabel = (index: number) => (index === 0 ? 'Fairest' : `Option ${index + 1}`);

const BalanceResults: React.FC<BalanceResultsProps> = ({ suggestions, title, onExport, onExportAll, onClear }) => {
  const navigate = useNavigate();
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => setSelectedIndex(0), [suggestions]);

  if (suggestions.length === 0) return null;
  const selected = suggestions[selectedIndex];

  return (
    <Box id="balance-results">
      <Flex justify="space-between" align="end" gap={3} flexWrap="wrap" mb={4}>
        <Box>
          <Heading size="lg" fontFamily="heading" color="gray.50">{title}</Heading>
          <Text fontSize="sm" color="gray.400">
            {suggestions.length > 1
              ? 'Ranked fairest first. Adjust any of them before you play.'
              : 'Adjust them before you play if you like.'}
          </Text>
        </Box>
        <HStack spacing={2} flexWrap="wrap">
          <Button size="sm" variant="ghost" leftIcon={<FiChevronUp />} onClick={onClear}>Change players</Button>
          {suggestions.length >= 2 && (
            <Button size="sm" variant="outline" leftIcon={<FiCopy />} onClick={onExportAll}>Copy top two</Button>
          )}
          <Button size="sm" colorScheme="brand" leftIcon={<FiUpload />} onClick={() => navigate('/upload')}>
            Played it? Upload
          </Button>
        </HStack>
      </Flex>

      {suggestions.length > 1 && (
        <ButtonGroup size="sm" variant="outline" mb={4} spacing={0} gap={2} flexWrap="wrap">
          {suggestions.map((suggestion, index) => (
            <Button
              key={index}
              onClick={() => setSelectedIndex(index)}
              variant={index === selectedIndex ? 'solid' : 'outline'}
              colorScheme={index === selectedIndex ? 'brand' : 'gray'}
              aria-pressed={index === selectedIndex}
            >
              {optionLabel(index)}
              <Text as="span" ml={2} fontFamily="mono" fontSize="xs" opacity={0.8}>
                {Math.round(suggestion.match_quality)}%
              </Text>
            </Button>
          ))}
        </ButtonGroup>
      )}

      <TeamEditor key={`${selectedIndex}-${selected.balance_prediction_id ?? 'draft'}`} suggestion={selected} onExport={onExport} />
    </Box>
  );
};

export default BalanceResults;
