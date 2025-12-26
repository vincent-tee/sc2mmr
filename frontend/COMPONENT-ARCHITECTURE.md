# TeamGenerator Component Architecture

## Component Hierarchy

```
TeamGenerator (index.tsx)
├── Header Section
│   └── Tactical Title & Description (static)
│
├── TeamSelector
│   ├── Selection Badge (shows count)
│   ├── Game Mode Display (1v1, 2v2, etc.)
│   ├── Validation Badges
│   └── Grid of PlayerCard Components
│       └── PlayerCard (multiple instances)
│
├── BalanceControls
│   ├── Enable/Disable Switch
│   ├── Collapsible Settings (when enabled)
│   │   ├── Impact Weight Slider
│   │   ├── Weight Percentage Display
│   │   └── Balance Indicators (MMR ↔ Impact)
│   └── Description Text
│
├── GenerateButton
│   ├── Primary CTA Button
│   ├── Loading State Message
│   └── Validation Messages
│       ├── "SELECT N MORE" (insufficient players)
│       └── "UNEVEN TEAMS DETECTED" (odd count)
│
├── Loading State (when generating)
│   └── Team Result Skeletons (3x)
│
└── BalanceResults (when results available)
    └── Multiple TeamSuggestionCard Components
        ├── Recommended Badge (first suggestion)
        ├── Header
        │   ├── Configuration Name
        │   ├── Win Probability Display (Team 1 vs Team 2)
        │   ├── Balance Progress Bar
        │   ├── Fairness Rating Badge
        │   └── MMR Difference
        │
        ├── Team Display Section
        │   ├── Team 1
        │   │   ├── Team Header
        │   │   ├── Player List (PlayerCard components)
        │   │   └── Stats Box
        │   │       ├── Average MMR
        │   │       └── Average Impact (if available)
        │   │
        │   └── Team 2
        │       ├── Team Header
        │       ├── Player List (PlayerCard components)
        │       └── Stats Box
        │           ├── Average MMR
        │           └── Average Impact (if available)
        │
        ├── Impact Distribution Metrics (when available)
        │   ├── Impact Balance Score
        │   ├── Distribution Progress Bar
        │   └── Impact Difference Display
        │
        └── Export Menu
            ├── Copy as Text
            └── Download File
```

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│  TeamGenerator (State Management)                       │
│  • selectedPlayers[]                                    │
│  • teamSuggestions[]                                    │
│  • useImpactBalance (boolean)                           │
│  • impactWeight (number 0-1)                            │
└─────────────────────────────────────────────────────────┘
           │          │          │           │
           ↓          ↓          ↓           ↓
      ┌────────┐┌──────────┐┌──────────┐┌────────────┐
      │Team    ││Balance   ││Generate  ││Balance     │
      │Selector││Controls  ││Button    ││Results     │
      │        ││          ││          ││            │
      │Input:  ││Input:    ││Input:    ││Input:      │
      │players ││toggle    ││state     ││suggestions│
      │selected││weight    ││canGen    ││           │
      │        ││          ││isLoading ││           │
      │Output: ││Output:   ││Output:   ││Output:    │
      │toggle  ││setToggle ││generate  ││export()   │
      │select  ││setWeight ││click     ││           │
      │all     ││          ││          ││           │
      │clear   ││          ││          ││           │
      └────────┘└──────────┘└──────────┘└────────────┘
           │          │          │           │
           └──────────┴──────────┴───────────┘
                      │
                      ↓
      ┌─────────────────────────────────────┐
      │  React Query Mutations               │
      │  • balanceTeamsMutation              │
      │    - Calls teamsApi.balance()        │
      │    - Calls teamsApi.balanceWithImpact│
      │    - Sets suggestions on success     │
      └─────────────────────────────────────┘
```

## Props Flow

### From Parent to Child

```
TeamGenerator
│
├─→ TeamSelector
│   ├─ players: Player[]
│   ├─ selectedPlayers: Player[]
│   ├─ onTogglePlayer: (player) => void
│   ├─ onSelectAll: () => void
│   └─ onClearSelection: () => void
│
├─→ BalanceControls
│   ├─ useImpactBalance: boolean
│   ├─ impactWeight: number
│   ├─ onUseImpactBalanceChange: (checked) => void
│   └─ onImpactWeightChange: (value) => void
│
├─→ GenerateButton
│   ├─ canGenerate: boolean
│   ├─ isLoading: boolean
│   ├─ selectedPlayersCount: number
│   ├─ hasOddPlayers: boolean
│   ├─ minPlayers: number
│   └─ onGenerate: () => void
│
└─→ BalanceResults
    ├─ suggestions: TeamSuggestionWithImpact[]
    └─ onExport: (suggestion, format) => Promise<void>
        │
        └─→ TeamSuggestionCard (child)
            ├─ suggestion: TeamSuggestionWithImpact
            ├─ index: number
            ├─ isRecommended: boolean
            └─ onExport: (suggestion, format) => Promise<void>
```

## State Locations

```
Component State Tree:
═══════════════════════════════════════════════════════════

Root (TeamGenerator)
├─ selectedPlayers: Player[]
│  ├─ Used by: TeamSelector (display), GenerateButton (count)
│  ├─ Modified by: togglePlayer, selectAll, clearSelection
│  └─ Purpose: Track which players are selected
│
├─ teamSuggestions: TeamSuggestionWithImpact[]
│  ├─ Used by: BalanceResults
│  ├─ Modified by: balanceTeamsMutation.onSuccess
│  └─ Purpose: Store team suggestions from API
│
├─ useImpactBalance: boolean
│  ├─ Used by: BalanceControls (display), generateTeams (logic)
│  ├─ Modified by: setUseImpactBalance
│  └─ Purpose: Toggle impact-aware balancing algorithm
│
└─ impactWeight: number (0-1)
   ├─ Used by: BalanceControls (display), generateTeams (logic)
   ├─ Modified by: setImpactWeight
   └─ Purpose: Control impact vs MMR balance weight

Child Components (Stateless/Pure)
├─ TeamSelector: Props-only, no internal state
├─ BalanceControls: Props-only, no internal state
├─ GenerateButton: Props-only, no internal state
└─ BalanceResults: Props-only, no internal state
```

## Event Flow

```
User Interaction → Handler → State Update → Re-render

1. Player Selection Flow:
   User clicks PlayerCard
   → togglePlayer(player)
   → setSelectedPlayers(updated array)
   → Re-render TeamSelector with new selection
   → GenerateButton updates canGenerate flag

2. Impact Balancing Flow:
   User toggles Switch
   → setUseImpactBalance(boolean)
   → Re-render BalanceControls (collapse/expand)

3. Weight Adjustment Flow:
   User moves Slider
   → setImpactWeight(value)
   → Re-render BalanceControls with new percentage

4. Team Generation Flow:
   User clicks "GENERATE TEAMS"
   → generateTeams()
   → balanceTeamsMutation.mutate(playerIds)
   → API call to backend
   → balanceTeamsMutation.onSuccess()
   → setTeamSuggestions(data)
   → Re-render BalanceResults with suggestions

5. Export Flow:
   User clicks Export menu
   → handleExport(suggestion, format)
   → If 'text': copyToClipboard() or download
   → Show toast notification
```

## Dependency Graph

```
External Dependencies:
├─ React (hooks)
│  ├─ useState
│  └─ Used in: TeamGenerator
│
├─ Chakra UI (components)
│  ├─ Layout: Box, Container, VStack, HStack
│  ├─ Typography: Heading, Text, Badge
│  ├─ Input: Switch, Slider, Button
│  ├─ Display: Progress, Icon, Collapse, Menu
│  └─ Used in: All components
│
├─ React Icons (icons)
│  ├─ Various Fi* icons
│  └─ Used in: All components
│
├─ TanStack React Query (data fetching)
│  ├─ useQuery, useMutation
│  └─ Used in: TeamGenerator
│
└─ Internal Dependencies:
   ├─ @/api/endpoints (API calls)
   │  ├─ playersApi.getAll()
   │  ├─ teamsApi.balance()
   │  └─ teamsApi.balanceWithImpact()
   │
   ├─ @/hooks/useToast (notifications)
   │  └─ Used in: TeamGenerator
   │
   ├─ @/utils/formatting (utilities)
   │  ├─ generateTeamText()
   │  ├─ copyToClipboard()
   │  ├─ formatMMR()
   │  └─ getFairnessColor()
   │
   ├─ @/components/* (shared components)
   │  ├─ PlayerCard
   │  ├─ TacticalCard
   │  ├─ TacticalBackground
   │  ├─ EmptyState
   │  └─ LoadingState
   │
   └─ @/types/api (TypeScript types)
      ├─ Player
      ├─ TeamSuggestion
      └─ Custom: TeamSuggestionWithImpact
```

## Component Complexity Analysis

```
Component          | Lines | Complexity | Responsibility
─────────────────────────────────────────────────────────
TeamGenerator      | 190   | Medium     | Orchestration
TeamSelector       | 108   | Low        | Display only
BalanceControls    | 138   | Low        | Display + toggle
GenerateButton     | 106   | Low        | Display + state
BalanceResults     | 548   | High       | Display + export
─────────────────────────────────────────────────────────
Total              | 1090  |            | Decomposed

Complexity Metrics:
• Low = Pure presentation, few props, no side effects
• Medium = State management, event handlers
• High = Complex UI, multiple sub-components, conditional rendering
```

## Render Path

```
Initial Render:
TeamGenerator
├─ useQuery (fetch players)
├─ Render loading state
└─ Once data loads:
   └─ Render full UI
      ├─ TeamSelector (with player list)
      ├─ BalanceControls (collapsed by default)
      ├─ GenerateButton (disabled if no players)
      └─ BalanceResults (empty, shown when suggestions exist)

After Team Generation:
TeamGenerator
├─ Render loading skeletons (while mutation pending)
│  └─ 3x TeamResultSkeleton
├─ After success:
│  └─ BalanceResults
│     └─ 3x TeamSuggestionCard
│        ├─ First marked as RECOMMENDED
│        └─ Rest as alternatives
└─ Cached data allows instant re-generation
```

## Performance Optimization Opportunities

```
✓ Current Optimizations:
├─ Component separation allows selective rendering
├─ Stateless child components prevent unnecessary re-renders
├─ Mutation loading state prevents double-submission
└─ Query caching prevents repeated API calls

Potential Future Optimizations:
├─ React.memo() for pure components
├─ useMemo() for expensive calculations
├─ useCallback() for stable function references
├─ Code splitting: lazy load BalanceResults
└─ Virtual scrolling for large player lists
```

---

**Last Updated**: December 8, 2025
**Status**: Production Ready
**Architecture Pattern**: Atomic Component Design with Separation of Concerns
