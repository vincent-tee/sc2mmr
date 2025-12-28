# SC2 Rank Badge Utility and Component Guide

## Overview

The rank badge system provides a unified way to display StarCraft 2 player ranks based on MMR (Matchmaking Rating) values. It includes both a utility library for rank calculations and a reusable React component for visual display.

## Files Created

1. **`/frontend/src/utils/ranks.ts`** - Rank utility functions and constants
2. **`/frontend/src/components/RankBadge.tsx`** - React component for displaying rank badges

## Rank System

### Rank Thresholds

The StarCraft 2 ranking system follows these MMR ranges:

| Rank | MMR Range | Icon |
|------|-----------|------|
| Bronze | 0-1500 | ⚔ |
| Silver | 1500-2000 | ⚔⚔ |
| Gold | 2000-2300 | ⚔⚔⚔ |
| Platinum | 2300-2600 | ⚔⚔⚔⚔ |
| Diamond | 2600-2900 | ⚔⚔⚔⚔⚔ |
| Master | 2900-3200 | 👑 |
| Grandmaster | 3200+ | 👑⭐ |

### Color Palette

Each rank has a distinct color using the warm theme palette:

| Rank | Background | Text Color |
|------|-----------|-----------|
| Bronze | orange.600 | white |
| Silver | gray.400 | gray.900 |
| Gold | yellow.500 | gray.900 |
| Platinum | cyan.400 | gray.900 |
| Diamond | blue.400 | white |
| Master | purple.500 | white |
| Grandmaster | red.500 | white (gold border) |

## Utility API

### `getRankFromMMR(mmr: number)`

Determines the rank name and colors for a given MMR value.

**Returns:**
```typescript
{
  name: RankName;
  bg: string;          // Chakra UI background color name
  color: string;       // Chakra UI text color name
  icon: string;        // Rank icon/symbol
  border?: string;     // Optional border color (Grandmaster only)
}
```

**Example:**
```typescript
import { getRankFromMMR } from '@/utils/ranks';

const rankInfo = getRankFromMMR(2850);
console.log(rankInfo.name);  // "Diamond"
console.log(rankInfo.icon);  // "⚔⚔⚔⚔⚔"
```

### `getRankBadgeProps(mmr: number)`

Returns Chakra UI Badge component props with appropriate styling.

**Returns:**
```typescript
{
  bg: string;
  color: string;
  textTransform: string;
  fontWeight: string;
  letterSpacing: string;
  borderWidth?: string;      // Grandmaster only
  borderColor?: string;      // Grandmaster only
  boxShadow?: string;        // Grandmaster only
}
```

**Example:**
```typescript
import { getRankBadgeProps } from '@/utils/ranks';
import { Badge } from '@chakra-ui/react';

const props = getRankBadgeProps(3250);
<Badge {...props}>Grandmaster</Badge>
```

### `getRankTierDescription(mmr: number)`

Generates a human-readable rank tier description with progress information.

**Returns:** A string describing the rank and progress

**Example:**
```typescript
import { getRankTierDescription } from '@/utils/ranks';

const description = getRankTierDescription(2550);
console.log(description);  // "Platinum - 33% progress (50 MMR to next rank)"
```

### Constants

#### `RANK_THRESHOLDS`

Object defining MMR ranges for each rank:

```typescript
export const RANK_THRESHOLDS = {
  Bronze: { min: 0, max: 1500 },
  Silver: { min: 1500, max: 2000 },
  Gold: { min: 2000, max: 2300 },
  Platinum: { min: 2300, max: 2600 },
  Diamond: { min: 2600, max: 2900 },
  Master: { min: 2900, max: 3200 },
  Grandmaster: { min: 3200, max: Infinity },
};
```

#### `RANK_COLORS`

Mapping of ranks to their color and icon properties:

```typescript
export const RANK_COLORS: Record<RankName, { bg: string; color: string; icon: string }>;
```

#### Type: `RankName`

Union type of all valid rank names:

```typescript
type RankName = 'Bronze' | 'Silver' | 'Gold' | 'Platinum' | 'Diamond' | 'Master' | 'Grandmaster';
```

## Component API

### `RankBadge`

A React component that displays a rank badge with tooltip and progress information.

**Props:**

```typescript
interface RankBadgeProps {
  /** Player's MMR value (required) */
  mmr: number;

  /** Badge size variant ('xs' | 'sm' | 'md' | 'lg') - default: 'md' */
  size?: 'xs' | 'sm' | 'md' | 'lg';

  /** Show MMR value next to rank - default: false */
  showMMR?: boolean;

  /** Show rank icon - default: true */
  showIcon?: boolean;

  /** Custom className */
  className?: string;
}
```

**Features:**
- Automatic rank detection based on MMR
- Hover effect with smooth transitions
- Tooltip showing rank tier description and MMR (if enabled)
- Four size variants for different use cases
- Optional rank icon and MMR display

**Examples:**

```typescript
import RankBadge from '@/components/RankBadge';

// Basic usage - Shows rank icon and name
<RankBadge mmr={2850} />

// With MMR displayed
<RankBadge mmr={2850} showMMR={true} />

// Small size for compact layouts
<RankBadge mmr={2850} size="sm" />

// Large size with full details
<RankBadge mmr={3250} size="lg" showMMR={true} showIcon={true} />

// Without icon (just rank name)
<RankBadge mmr={1750} showIcon={false} />

// Custom styling
<RankBadge mmr={2000} className="my-custom-class" />
```

## Integration Examples

### In PlayerCard

```typescript
import RankBadge from '@/components/RankBadge';

export const PlayerCardWithRank = ({ player }) => (
  <VStack>
    <Text>{player.name}</Text>
    <RankBadge mmr={player.mmr} showMMR={true} />
  </VStack>
);
```

### In MatchHistory

```typescript
<HStack justify="space-between">
  <VStack>
    <Text>{team1Players[0].name}</Text>
    <RankBadge mmr={team1Players[0].mmr} size="sm" />
  </VStack>
  <Text fontWeight="bold">vs</Text>
  <VStack>
    <Text>{team2Players[0].name}</Text>
    <RankBadge mmr={team2Players[0].mmr} size="sm" />
  </VStack>
</HStack>
```

### In Leaderboard

```typescript
const LeaderboardRow = ({ player, rank }) => (
  <HStack>
    <Text fontWeight="bold">{rank}</Text>
    <Text flex={1}>{player.name}</Text>
    <RankBadge mmr={player.mmr} size="md" showMMR={true} />
  </HStack>
);
```

### With Custom Styling

```typescript
<Box _hover={{ transform: 'scale(1.05)' }}>
  <RankBadge
    mmr={2550}
    size="lg"
    showMMR={true}
    className="rank-badge-highlight"
  />
</Box>
```

## Styling and Theming

The RankBadge component uses Chakra UI colors defined in the theme configuration. To modify rank colors, edit the `RANK_COLORS` object in `/frontend/src/utils/ranks.ts`.

### Customizing Colors

```typescript
// In /frontend/src/utils/ranks.ts
export const RANK_COLORS: Record<RankName, { bg: string; color: string; icon: string }> = {
  Bronze: {
    bg: 'orange.700',  // Changed from orange.600
    color: 'white',
    icon: '⚔',
  },
  // ... rest of ranks
};
```

### Customizing Thresholds

```typescript
// In /frontend/src/utils/ranks.ts
export const RANK_THRESHOLDS = {
  Bronze: { min: 0, max: 1600 },    // Adjusted upper bound
  Silver: { min: 1600, max: 2100 }, // Adjusted range
  // ... rest of thresholds
};
```

## Testing

```typescript
import { getRankFromMMR, getRankBadgeProps, getRankTierDescription, RANK_THRESHOLDS } from '@/utils/ranks';

// Test rank detection
expect(getRankFromMMR(1000).name).toBe('Bronze');
expect(getRankFromMMR(1750).name).toBe('Silver');
expect(getRankFromMMR(2150).name).toBe('Gold');
expect(getRankFromMMR(2450).name).toBe('Platinum');
expect(getRankFromMMR(2750).name).toBe('Diamond');
expect(getRankFromMMR(3050).name).toBe('Master');
expect(getRankFromMMR(3500).name).toBe('Grandmaster');

// Test badge props
const props = getRankBadgeProps(3250);
expect(props.bg).toBe('red.500');
expect(props.borderWidth).toBe('2px');

// Test tier description
const desc = getRankTierDescription(2000);
expect(desc).toContain('Gold');
```

## Migration Guide

If you have existing rank-related code, here's how to migrate:

**Before:**
```typescript
const getRankColor = (mmr: number): string => {
  if (mmr >= 2900) return 'purple';
  if (mmr >= 2600) return 'blue';
  // ... etc
};
```

**After:**
```typescript
import { getRankFromMMR } from '@/utils/ranks';

const rankInfo = getRankFromMMR(mmr);
const color = rankInfo.bg; // e.g., 'purple.500'
```

## Performance Notes

- All rank utility functions are pure and have O(1) complexity
- The RankBadge component uses memoization internally for optimal re-rendering
- Consider wrapping in `React.memo()` if used in large lists

## Accessibility

- Badge includes `cursor: help` to indicate interactivity
- Tooltip provides additional rank information for screen readers
- High contrast colors ensure WCAG AA compliance

## Future Enhancements

Potential improvements for future versions:

1. Animated rank progression on MMR changes
2. Rank history visualization
3. Comparison tooltips for head-to-head matchups
4. Custom rank tier names (e.g., "Bronze 1", "Bronze 2", etc.)
5. Integration with competitive season data
