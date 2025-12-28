# TeamGenerator Quick Reference Guide

## File Locations

```
src/pages/TeamGenerator/
├── index.tsx              Main orchestration component
├── TeamSelector.tsx       Player selection UI
├── BalanceControls.tsx    Impact weight configuration
├── GenerateButton.tsx     Generation CTA button
└── BalanceResults.tsx     Results display with export
```

## Component Quick Start

### Using TeamGenerator in Your App

```tsx
// App.tsx (already configured)
import TeamGenerator from './pages/TeamGenerator';

<Route path="/balance" element={<ErrorBoundary><TeamGenerator /></ErrorBoundary>} />
```

### Component Props Reference

#### TeamSelector
```tsx
<TeamSelector
  players={players}                    // Player[] from API
  selectedPlayers={selectedPlayers}   // Player[] state
  onTogglePlayer={togglePlayer}       // (player: Player) => void
  onSelectAll={selectAll}             // () => void
  onClearSelection={clearSelection}   // () => void
/>
```

#### BalanceControls
```tsx
<BalanceControls
  useImpactBalance={useImpactBalance}
  impactWeight={impactWeight}
  onUseImpactBalanceChange={setUseImpactBalance}
  onImpactWeightChange={setImpactWeight}
/>
```

#### GenerateButton
```tsx
<GenerateButton
  canGenerate={selectedPlayers.length >= 2}
  isLoading={balanceTeamsMutation.isPending}
  selectedPlayersCount={selectedPlayers.length}
  hasOddPlayers={selectedPlayers.length % 2 !== 0}
  minPlayers={2}
  onGenerate={generateTeams}
/>
```

#### BalanceResults
```tsx
<BalanceResults
  suggestions={teamSuggestions}
  onExport={handleExport}
/>
```

## Adding New Features

### Add a New State Variable
```tsx
// In index.tsx
const [newState, setNewState] = useState<Type>(initialValue);

// Pass to child component
<ComponentName newState={newState} onNewStateChange={setNewState} />
```

### Add a New Calculation
```tsx
// In index.tsx (above JSX)
const calculatedValue = selectedPlayers.reduce((acc, p) => acc + p.mmr, 0) / selectedPlayers.length;

// Use in JSX or pass to child
<GenerateButton {...props} calculatedValue={calculatedValue} />
```

### Add a New Event Handler
```tsx
// In index.tsx
const handleNewAction = async (): Promise<void> => {
  try {
    // Action logic
    toast.success('Success message');
  } catch (error) {
    toast.error('Error message');
  }
};

// Pass to child component
<ComponentName onNewAction={handleNewAction} />
```

## Common Modifications

### Change Validation Rules
```tsx
// In index.tsx, update validation flags
const minPlayers = 2;        // Modify minimum players
const maxPlayers = 10;       // Add maximum if needed
const canGenerate = selectedPlayers.length >= minPlayers && selectedPlayers.length <= maxPlayers;
```

### Add New Export Format
```tsx
// In index.tsx, handleExport function
const handleExport = async (suggestion, format) => {
  if (format === 'csv') {
    // Add CSV export logic
    const csv = convertToCSV(suggestion);
    // Save file...
  }
};

// Update BalanceResults component to add MenuItem
<MenuItem icon={<FiDownload />} onClick={() => onExport(suggestion, 'csv')}>
  Download as CSV
</MenuItem>
```

### Customize Team Suggestions Count
```tsx
// In index.tsx, balance teams mutation
const response = await teamsApi.balance(playerIds, 5); // Change from 3 to 5 suggestions
```

### Add Loading Skeleton Count
```tsx
// In index.tsx, render section
{balanceTeamsMutation.isPending && (
  <VStack spacing={4}>
    <TeamResultSkeleton />
    <TeamResultSkeleton />
    <TeamResultSkeleton />
    <TeamResultSkeleton />  // Add more as needed
  </VStack>
)}
```

## Type Safety Checklist

Before committing changes:

- [ ] All new props have TypeScript interfaces defined
- [ ] All function parameters have type annotations
- [ ] All event handlers have proper typing
- [ ] Import statements use `type { ... }` for types
- [ ] No `any` types used (use `unknown` if necessary)
- [ ] Return types specified on functions
- [ ] Components use `React.FC<Props>` pattern

Run type check:
```bash
npx tsc --noEmit
```

## Testing Patterns

### Unit Test Template
```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TeamSelector from './TeamSelector';

describe('TeamSelector', () => {
  it('should toggle player selection', async () => {
    const mockToggle = jest.fn();
    render(
      <TeamSelector
        players={mockPlayers}
        selectedPlayers={[]}
        onTogglePlayer={mockToggle}
        onSelectAll={jest.fn()}
        onClearSelection={jest.fn()}
      />
    );

    const playerCard = screen.getByText('Player Name');
    await userEvent.click(playerCard);

    expect(mockToggle).toHaveBeenCalledWith(expect.any(Object));
  });
});
```

### Integration Test Template
```tsx
describe('TeamGenerator Integration', () => {
  it('should complete full workflow', async () => {
    // 1. Render component with React Query provider
    // 2. Wait for players to load
    // 3. Select players
    // 4. Enable impact balancing
    // 5. Generate teams
    // 6. Verify results displayed
    // 7. Test export functionality
  });
});
```

## Common Issues & Solutions

### Issue: "Cannot find module './TeamSelector'"
**Solution**: Verify file exists in correct location: `src/pages/TeamGenerator/TeamSelector.tsx`

### Issue: Props not updating child component
**Solution**: Check that prop is being passed correctly from parent state
```tsx
// ✓ Correct
<TeamSelector selectedPlayers={selectedPlayers} ... />

// ✗ Incorrect
<TeamSelector selectedPlayers={someOtherValue} ... />
```

### Issue: TypeScript error on component prop
**Solution**: Ensure interface is exported and imported correctly
```tsx
// ✓ Correct
interface TeamSelectorProps { ... }
const TeamSelector: React.FC<TeamSelectorProps> = ({ ... }) => { ... }

// ✗ Incorrect
const TeamSelector = ({ players }: any) => { ... }
```

### Issue: Event handler not firing
**Solution**: Verify onClick/onChange is connected to correct element
```tsx
// ✓ Correct - button has click handler
<Button onClick={onGenerate}>GENERATE</Button>

// ✗ Incorrect - handler not connected
<Button>GENERATE</Button>
```

## Performance Tips

### Optimize Re-renders
```tsx
// ✓ Memoize pure components
const BalanceResults = React.memo(BalanceResultsComponent);

// ✓ Use useCallback for stable references
const togglePlayer = useCallback((player: Player) => {
  setSelectedPlayers(prev => {
    const isSelected = prev.some(p => p.id === player.id);
    return isSelected ? prev.filter(p => p.id !== player.id) : [...prev, player];
  });
}, []);
```

### Avoid Expensive Operations
```tsx
// ✓ Memoize calculated values
const avgMMR = useMemo(
  () => selectedPlayers.reduce((sum, p) => sum + p.mmr, 0) / selectedPlayers.length,
  [selectedPlayers]
);

// ✗ Avoid recalculating on every render
const avgMMR = selectedPlayers.reduce((sum, p) => sum + p.mmr, 0) / selectedPlayers.length;
```

## API Integration

### Add New API Call
```tsx
// In teamsApi (endpoints.ts)
balanceWithRaceRestriction: (playerIds: number[], raceRestriction: string) =>
  Promise<AxiosResponse<TeamSuggestion[]>>

// In TeamGenerator index.tsx
if (useRaceRestriction) {
  const response = await teamsApi.balanceWithRaceRestriction(playerIds, selectedRace);
}
```

### Handle New API Response Fields
```tsx
// Extend the type
interface TeamSuggestionWithImpact extends TeamSuggestion {
  team_1_avg_impact?: number;
  team_2_avg_impact?: number;
  new_field?: string;  // Add new field
}

// Use in component
{suggestion.new_field && <Box>{suggestion.new_field}</Box>}
```

## Styling & Theming

### Add New Color Scheme
All colors are in Chakra theme. Components use:
- `brand.400` / `brand.500` - Cyan blue
- `accent.400` / `accent.500` - Gold/amber
- `purple.400` / `purple.500` - Purple (impact)
- `shield.500` - Green (recommended)

### Modify Card Styling
```tsx
<TacticalCard
  variant="command"  // 'command' | 'angled' | 'default'
  glowColor="rgba(0, 212, 255, 0.5)"  // Glow effect color
>
  {/* content */}
</TacticalCard>
```

## Debugging Tips

### Enable React DevTools
```tsx
// Open browser DevTools > React tab
// Inspect component tree
// Monitor state changes in real-time
```

### Log State Changes
```tsx
// In index.tsx
useEffect(() => {
  console.log('Selected players:', selectedPlayers);
  console.log('Can generate:', canGenerate);
}, [selectedPlayers, canGenerate]);
```

### Check Network Requests
```tsx
// DevTools > Network tab
// Check requests to:
// - /api/players (player list)
// - /api/teams/balance (team generation)
// - /api/teams/balance-impact (impact-aware generation)
```

### Verify TypeScript
```bash
# Check for any type errors
npx tsc --noEmit

# Generate type definitions
npx tsc --declaration
```

## Deployment Checklist

- [ ] All components render without errors
- [ ] TypeScript compiles cleanly
- [ ] All unit/integration tests pass
- [ ] No console warnings or errors
- [ ] No unused imports or variables
- [ ] API endpoints configured for production
- [ ] Environment variables set correctly
- [ ] Performance optimizations applied
- [ ] Accessibility requirements met (WCAG 2.1 AA)
- [ ] Responsive design tested on mobile/tablet

---

**Last Updated**: December 8, 2025
**Status**: Production Ready
**Contact**: Review refactoring documentation for detailed architecture
