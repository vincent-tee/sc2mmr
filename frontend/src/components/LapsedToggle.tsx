import { FormControl, FormLabel, Switch, Tooltip } from '@chakra-ui/react';

export const LAPSED_EXPLANATION =
  "Lapsed players haven't played in 2 years (6 months if they played fewer than 15 games).";

interface LapsedToggleProps {
  id: string;
  isChecked: boolean;
  onChange: (checked: boolean) => void;
}

const LapsedToggle: React.FC<LapsedToggleProps> = ({ id, isChecked, onChange }) => (
  <Tooltip label={LAPSED_EXPLANATION} hasArrow placement="top" openDelay={300}>
    <FormControl w="auto" display="flex" alignItems="center" gap={2}>
      <FormLabel htmlFor={id} mb={0} fontSize="sm" color="gray.400" whiteSpace="nowrap" cursor="pointer">
        Include lapsed players
      </FormLabel>
      <Switch id={id} size="sm" colorScheme="orange" isChecked={isChecked} onChange={(e) => onChange(e.target.checked)} />
    </FormControl>
  </Tooltip>
);

export default LapsedToggle;
