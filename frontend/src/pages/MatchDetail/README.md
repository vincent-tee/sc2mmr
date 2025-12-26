# MatchDetail Component Decomposition

This directory contains the decomposed MatchDetail page component, split into smaller, more maintainable sub-components.

## File Structure

```
src/pages/MatchDetail/
├── index.tsx                    # Main component (data fetching & routing)
├── MatchHeader.tsx              # Match metadata header
├── OperativesTab.tsx            # Player/operative stats table
├── CommentaryTab.tsx            # AI-generated match commentary
├── AnalyticsTab.tsx             # Player metrics & analytics charts
├── types.ts                     # Type definitions for all components
├── helpers.ts                   # Utility functions for data transformation
└── README.md                    # This file
```

## Component Responsibilities

### index.tsx
- Handles all data fetching via React Query
- Manages route parameters and navigation
- Composes the main page layout with tabs
- Coordinates data flow to child components

**Data Queries:**
- Match details (basic info, players, map, duration)
- Match commentary (AI-generated analysis)
- Player metrics (impact scores, damage stats)
- Damage timelines (game progression visualization)

### MatchHeader.tsx
- Displays match metadata (map name, game mode, date, duration)
- Shows win probability analysis with team predictions
- Displays upset indicators for unexpected results
- Visual probability comparison bars

**Props:** `matchData`, `team1Won`

### OperativesTab.tsx
- Renders two team tables with player information
- Shows player names, races, MMR before/after
- Displays MMR change with color coding (up/down indicators)
- Victory badges for winning team

**Props:** `matchData`, `team1Won`

### CommentaryTab.tsx
- Displays AI-generated match analysis
- Shows match overview, critical moments, MVP analysis
- Includes individual player performance breakdowns
- Team analysis and final match summary

**Props:** `commentary`, `isLoading`

### AnalyticsTab.tsx
- Renders player metrics comparison charts
- Individual player analytics per team:
  - Impact score radar charts
  - Damage distribution charts
  - Damage timeline graphs
- Handles loading and empty states

**Props:** `matchData`, `playerMetrics`, `damageTimelines`, `metricsLoading`, `timelinesLoading`

## Type Definitions (types.ts)

### Core Types
- `MvpAnalysis` - MVP selection with impact score
- `MatchCommentary` - Flexible commentary structure
- `PlayerMetricsResponse` - Detailed player performance metrics
- `DamageDistribution` - Early/mid/late game damage breakdown
- `TimelineData` - Damage progression over match duration
- `PlayerTimeline` - Per-player timeline data

## Utility Functions (helpers.ts)

### transformDamageDistribution()
Normalizes damage distribution data to consistent format:
- Handles both `early_game`/`mid_game`/`late_game` and `early`/`mid`/`late` naming

### transformTimelineData()
Prepares timeline data for visualization components

## Integration Notes

### With App.tsx
```typescript
import MatchDetail from './pages/MatchDetail';
// App.tsx automatically imports from index.tsx
```

### Component Hierarchy
```
MatchDetail (index.tsx)
├── MatchHeader
├── Tabs
│   ├── OperativesTab
│   ├── CommentaryTab
│   └── AnalyticsTab
```

### Data Flow
```
React Query (index.tsx)
├── matchData → MatchHeader, OperativesTab, AnalyticsTab
├── commentary → CommentaryTab
├── playerMetrics → AnalyticsTab
└── damageTimelines → AnalyticsTab
```

## Styling & Design

All components use:
- Chakra UI components (no custom styling needed)
- Shared color theme from `useColorModeValue()`
- Consistent typography (fontFamily="heading", textTransform="uppercase")
- Tactical styling with gradients and glow effects

## Performance Considerations

1. **Data Fetching**
   - Match data fetched first
   - Commentary only fetched after match data available
   - Metrics fetched in parallel for all players
   - Timelines fetched independently with error handling

2. **Rendering**
   - Tab panels only render visible content
   - Charts use lazy loading where applicable
   - No unnecessary re-renders (proper dependency arrays)

3. **Error Handling**
   - Graceful degradation for missing metrics/timelines
   - User-friendly error messages
   - Loading states for async operations

## Testing Strategy

- Unit tests for helper functions (transformations)
- Component tests for UI rendering and user interactions
- Integration tests for data flow between components
- E2E tests for full match detail page workflow
- Target: 85%+ coverage

## Future Enhancements

1. Extract color configurations to theme
2. Memoize components to prevent unnecessary re-renders
3. Add component stories for Storybook
4. Improve error handling with retry logic
5. Add time-based caching for stable data (match details)
