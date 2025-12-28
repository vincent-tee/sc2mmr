# Rank Badge - Quick Start Guide

## Files Created

```
frontend/src/
├── utils/
│   └── ranks.ts          # Rank utility functions
└── components/
    └── RankBadge.tsx     # React component
```

## Installation & Setup

No additional installation needed - both files use existing dependencies (React, Chakra UI).

## Quick Examples

### 1. Basic Usage

```tsx
import RankBadge from '@/components/RankBadge';

// Display rank badge for a player with 2850 MMR
<RankBadge mmr={2850} />
// Output: Diamond badge with icon
```

### 2. Show MMR Value

```tsx
<RankBadge mmr={2850} showMMR={true} />
// Output: Diamond ⚔⚔⚔⚔⚔ 2850
```

### 3. Different Sizes

```tsx
<RankBadge mmr={2850} size="xs" />   {/* Small */}
<RankBadge mmr={2850} size="sm" />   {/* Small-Medium */}
<RankBadge mmr={2850} size="md" />   {/* Medium (default) */}
<RankBadge mmr={2850} size="lg" />   {/* Large */}
```

### 4. In a List

```tsx
{players.map(player => (
  <HStack key={player.id}>
    <Text>{player.name}</Text>
    <RankBadge mmr={player.mmr} size="sm" />
  </HStack>
))}
```

## Utility Functions

### Get rank info

```tsx
import { getRankFromMMR } from '@/utils/ranks';

const rank = getRankFromMMR(2850);
console.log(rank.name);   // "Diamond"
console.log(rank.icon);   // "⚔⚔⚔⚔⚔"
console.log(rank.bg);     // "blue.400"
```

### Get badge styling

```tsx
import { getRankBadgeProps } from '@/utils/ranks';
import { Badge } from '@chakra-ui/react';

const props = getRankBadgeProps(3250);
<Badge {...props}>Custom Badge</Badge>
```

### Get rank description

```tsx
import { getRankTierDescription } from '@/utils/ranks';

const desc = getRankTierDescription(2550);
// "Platinum - 33% progress (50 MMR to next rank)"
```

## Rank Thresholds

| Rank | MMR Range |
|------|-----------|
| Bronze | 0 - 1,500 |
| Silver | 1,500 - 2,000 |
| Gold | 2,000 - 2,300 |
| Platinum | 2,300 - 2,600 |
| Diamond | 2,600 - 2,900 |
| Master | 2,900 - 3,200 |
| Grandmaster | 3,200+ |

## Customize Colors

Edit `/frontend/src/utils/ranks.ts`:

```typescript
export const RANK_COLORS: Record<RankName, { bg: string; color: string; icon: string }> = {
  Bronze: {
    bg: 'orange.600',      // Change this
    color: 'white',
    icon: '⚔',
  },
  // ... rest
};
```

## Common Issues

**Issue:** Component not found
```
Cannot find module '@/components/RankBadge'
```
**Solution:** Verify the file exists at `/frontend/src/components/RankBadge.tsx`

**Issue:** Colors not applying
```
Badge appears with wrong colors
```
**Solution:** Ensure Chakra UI theme is initialized with `extendTheme()` in your theme config

**Issue:** TypeScript errors
```
'mmr' property is missing
```
**Solution:** Add required `mmr` prop: `<RankBadge mmr={2850} />`

## Next Steps

1. Import in your components
2. Pass MMR values from your data
3. Customize sizes and options as needed
4. See `RANK-BADGE-GUIDE.md` for detailed documentation

## Example Integration

```tsx
// In PlayerCard.tsx
import RankBadge from '@/components/RankBadge';

const PlayerCard = ({ player }) => (
  <VStack spacing={2}>
    <Avatar name={player.name} />
    <Text fontWeight="bold">{player.name}</Text>
    <RankBadge mmr={player.mmr} showMMR={true} />
    <Text fontSize="sm" color="gray.500">
      {formatMMR(player.mmr)} MMR
    </Text>
  </VStack>
);
```

## Support & Documentation

- Full API documentation: `RANK-BADGE-GUIDE.md`
- Source code: `/frontend/src/utils/ranks.ts` and `/frontend/src/components/RankBadge.tsx`
- Tests: Add tests to verify rank calculations
