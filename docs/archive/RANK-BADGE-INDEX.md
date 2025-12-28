# Rank Badge System - Documentation Index

Complete reference for the SC2MMR rank badge utility and component system.

---

## Quick Navigation

### I need to...

**Use the component in my code**
→ Start with [RANK-BADGE-QUICK-START.md](./RANK-BADGE-QUICK-START.md)

**Understand the full API**
→ Read [RANK-BADGE-GUIDE.md](./RANK-BADGE-GUIDE.md)

**See working examples**
→ Check [src/components/examples/RankBadgeExamples.tsx](./src/components/examples/RankBadgeExamples.tsx)

**Integrate into a component**
→ Follow [RANK-BADGE-GUIDE.md - Integration Examples](./RANK-BADGE-GUIDE.md#integration-examples)

**Customize colors/thresholds**
→ See [RANK-BADGE-GUIDE.md - Styling and Theming](./RANK-BADGE-GUIDE.md#styling-and-theming)

**Debug an issue**
→ Check [RANK-BADGE-QUICK-START.md - Common Issues](./RANK-BADGE-QUICK-START.md#common-issues)

---

## Documentation Files

### Production Files

| File | Purpose | Audience |
|------|---------|----------|
| **src/utils/ranks.ts** | Rank utility functions | Developers |
| **src/components/RankBadge.tsx** | React component | Developers |

### Documentation

| File | Purpose | Length | Best For |
|------|---------|--------|----------|
| **RANK-BADGE-QUICK-START.md** | Quick reference & copy-paste examples | 150+ lines | Getting started fast |
| **RANK-BADGE-GUIDE.md** | Complete API documentation | 400+ lines | Deep understanding |
| **RANK-BADGE-IMPLEMENTATION-SUMMARY.md** | Technical details & integration | 380+ lines | Implementation planning |
| **RANK-BADGE-DELIVERY-SUMMARY.md** | Project delivery overview | 500+ lines | Project overview |
| **RANK-BADGE-INDEX.md** | This file - navigation guide | Navigation | Finding what you need |

### Examples

| File | Purpose | Content |
|------|---------|---------|
| **src/components/examples/RankBadgeExamples.tsx** | Working examples | 8 example components |

---

## File Locations

```
/home/vtee/projects/sc2mmr/
├── frontend/
│   ├── src/
│   │   ├── utils/
│   │   │   └── ranks.ts
│   │   └── components/
│   │       ├── RankBadge.tsx
│   │       └── examples/
│   │           └── RankBadgeExamples.tsx
│   ├── RANK-BADGE-QUICK-START.md
│   ├── RANK-BADGE-GUIDE.md
│   ├── RANK-BADGE-IMPLEMENTATION-SUMMARY.md
│   └── RANK-BADGE-INDEX.md (this file)
└── RANK-BADGE-DELIVERY-SUMMARY.md
```

---

## Quick API Reference

### Component Usage

```typescript
import RankBadge from '@/components/RankBadge';

<RankBadge
  mmr={2850}                    // Required: Player MMR
  size="md"                     // Optional: 'xs'|'sm'|'md'|'lg'
  showMMR={false}               // Optional: Show MMR value
  showIcon={true}               // Optional: Show rank icon
  className="custom-class"      // Optional: CSS class
/>
```

### Utility Functions

```typescript
import {
  getRankFromMMR,
  getRankBadgeProps,
  getRankTierDescription,
  RANK_THRESHOLDS,
  RANK_COLORS
} from '@/utils/ranks';

// Get rank information
const rank = getRankFromMMR(2850);
// Returns: { name: 'Diamond', bg: 'blue.400', color: 'white', icon: '⚔⚔⚔⚔⚔' }

// Get badge styling props
const props = getRankBadgeProps(2850);
// Returns: { bg: 'blue.400', color: 'white', textTransform: 'uppercase', ... }

// Get rank description
const desc = getRankTierDescription(2850);
// Returns: 'Diamond - 50% progress (50 MMR to next rank)'
```

---

## Rank System

### Thresholds

| Rank | MMR | Icon |
|------|-----|------|
| Bronze | 0-1500 | ⚔ |
| Silver | 1500-2000 | ⚔⚔ |
| Gold | 2000-2300 | ⚔⚔⚔ |
| Platinum | 2300-2600 | ⚔⚔⚔⚔ |
| Diamond | 2600-2900 | ⚔⚔⚔⚔⚔ |
| Master | 2900-3200 | 👑 |
| Grandmaster | 3200+ | 👑⭐ |

---

## Integration Checklist

- [ ] Read RANK-BADGE-QUICK-START.md (5 min)
- [ ] Review RankBadgeExamples.tsx (5 min)
- [ ] Copy component import into target file
- [ ] Replace existing MMR display with RankBadge
- [ ] Test with sample MMR values (1000, 2000, 3000, 3500)
- [ ] Verify tooltip appears on hover
- [ ] Check colors match design

---

## Common Tasks

### Use in PlayerCard

```typescript
import RankBadge from '@/components/RankBadge';

export const PlayerCard = ({ player }) => (
  <VStack>
    <Text>{player.name}</Text>
    <RankBadge mmr={player.mmr} showMMR={true} />
  </VStack>
);
```

**Reference:** [RANK-BADGE-GUIDE.md#in-playercard](./RANK-BADGE-GUIDE.md#in-playercard)

### Use in MatchHistory

```typescript
<HStack>
  <Text>{player1.name}</Text>
  <RankBadge mmr={player1.mmr} size="sm" />
  <Text>vs</Text>
  <Text>{player2.name}</Text>
  <RankBadge mmr={player2.mmr} size="sm" />
</HStack>
```

**Reference:** [RANK-BADGE-GUIDE.md#in-matchhistory](./RANK-BADGE-GUIDE.md#in-matchhistory)

### Change Rank Colors

Edit `/frontend/src/utils/ranks.ts`:

```typescript
export const RANK_COLORS = {
  Bronze: {
    bg: 'orange.700',  // Changed color
    color: 'white',
    icon: '⚔',
  },
  // ... rest
};
```

**Reference:** [RANK-BADGE-GUIDE.md#customizing-colors](./RANK-BADGE-GUIDE.md#customizing-colors)

---

## Documentation by Topic

### Component API

- Props: [RANK-BADGE-GUIDE.md#component-api](./RANK-BADGE-GUIDE.md#component-api)
- Features: [RANK-BADGE-GUIDE.md#component-api](./RANK-BADGE-GUIDE.md#component-api)
- Examples: [RANK-BADGE-GUIDE.md#examples](./RANK-BADGE-GUIDE.md#examples)

### Utility Functions

- `getRankFromMMR()`: [RANK-BADGE-GUIDE.md#getrank-frommm](./RANK-BADGE-GUIDE.md#getrank-frommm)
- `getRankBadgeProps()`: [RANK-BADGE-GUIDE.md#getrank-badgeprops](./RANK-BADGE-GUIDE.md#getrank-badgeprops)
- `getRankTierDescription()`: [RANK-BADGE-GUIDE.md#getrank-tierdes](./RANK-BADGE-GUIDE.md#getrank-tierdes)

### Styling

- Colors: [RANK-BADGE-GUIDE.md#color-palette](./RANK-BADGE-GUIDE.md#color-palette)
- Theme integration: [RANK-BADGE-GUIDE.md#styling-and-theming](./RANK-BADGE-GUIDE.md#styling-and-theming)
- Customization: [RANK-BADGE-GUIDE.md#customizing-colors](./RANK-BADGE-GUIDE.md#customizing-colors)

### Integration

- PlayerCard: [RANK-BADGE-GUIDE.md#in-playercard](./RANK-BADGE-GUIDE.md#in-playercard)
- MatchHistory: [RANK-BADGE-GUIDE.md#in-matchhistory](./RANK-BADGE-GUIDE.md#in-matchhistory)
- Leaderboard: [RANK-BADGE-GUIDE.md#in-leaderboard](./RANK-BADGE-GUIDE.md#in-leaderboard)
- Custom styling: [RANK-BADGE-GUIDE.md#with-custom-styling](./RANK-BADGE-GUIDE.md#with-custom-styling)

### Testing

- Unit tests: [RANK-BADGE-GUIDE.md#testing](./RANK-BADGE-GUIDE.md#testing)
- E2E tests: [RANK-BADGE-IMPLEMENTATION-SUMMARY.md#e2e-tests-with-playwright](./RANK-BADGE-IMPLEMENTATION-SUMMARY.md#e2e-tests-with-playwright)

### Troubleshooting

- Common issues: [RANK-BADGE-QUICK-START.md#common-issues](./RANK-BADGE-QUICK-START.md#common-issues)
- Debugging: [RANK-BADGE-IMPLEMENTATION-SUMMARY.md#support--troubleshooting](./RANK-BADGE-IMPLEMENTATION-SUMMARY.md#support--troubleshooting)

---

## Examples by Use Case

### Simple rank display
```typescript
<RankBadge mmr={2850} />
```
→ [src/components/examples/RankBadgeExamples.tsx#AllRankTiers](./src/components/examples/RankBadgeExamples.tsx)

### With MMR value
```typescript
<RankBadge mmr={2850} showMMR={true} />
```
→ [src/components/examples/RankBadgeExamples.tsx#WithMMRDisplay](./src/components/examples/RankBadgeExamples.tsx)

### In player card
```typescript
<RankBadge mmr={player.mmr} showMMR={true} />
```
→ [src/components/examples/RankBadgeExamples.tsx#PlayerCardLayout](./src/components/examples/RankBadgeExamples.tsx)

### In match comparison
```typescript
<RankBadge mmr={team1Player.mmr} />
vs
<RankBadge mmr={team2Player.mmr} />
```
→ [src/components/examples/RankBadgeExamples.tsx#PlayerComparison](./src/components/examples/RankBadgeExamples.tsx)

### In leaderboard
```typescript
<HStack><Text>#{rank}</Text><RankBadge mmr={mmr} /></HStack>
```
→ [src/components/examples/RankBadgeExamples.tsx#LeaderboardRow](./src/components/examples/RankBadgeExamples.tsx)

---

## File Statistics

| Type | Count | Lines |
|------|-------|-------|
| Source files | 2 | 244 |
| Documentation | 5 | 1,800+ |
| Examples | 1 | 340 |
| **Total** | **8** | **2,400+** |

---

## Version Information

- **Created:** 2025-12-09
- **Status:** Production Ready
- **React Version:** 19+
- **TypeScript:** 5.0+
- **Chakra UI:** 2.0+

---

## Next Steps

1. **Quick Start:** Read [RANK-BADGE-QUICK-START.md](./RANK-BADGE-QUICK-START.md) (5 min)
2. **Review Examples:** Check [RankBadgeExamples.tsx](./src/components/examples/RankBadgeExamples.tsx) (5 min)
3. **Integrate:** Add to 1-2 components (15 min)
4. **Test:** Verify with various MMR values (5 min)
5. **Customize:** Adjust colors/thresholds if needed (Optional)

---

## Getting Help

### For...

**Quick answers** → Check [RANK-BADGE-QUICK-START.md](./RANK-BADGE-QUICK-START.md)

**API details** → See [RANK-BADGE-GUIDE.md](./RANK-BADGE-GUIDE.md)

**Working code** → Review [RankBadgeExamples.tsx](./src/components/examples/RankBadgeExamples.tsx)

**Integration tips** → Read [RANK-BADGE-GUIDE.md#integration-examples](./RANK-BADGE-GUIDE.md#integration-examples)

**Troubleshooting** → Check [RANK-BADGE-QUICK-START.md#common-issues](./RANK-BADGE-QUICK-START.md#common-issues)

**Technical details** → See [RANK-BADGE-IMPLEMENTATION-SUMMARY.md](./RANK-BADGE-IMPLEMENTATION-SUMMARY.md)

---

## Related Files in Project

- Existing theme: `/frontend/src/theme/index.ts`
- Color tokens: `/frontend/src/theme/tokens.ts`
- Formatting utilities: `/frontend/src/utils/formatting.ts`
- Example components: `/frontend/src/components/PlayerCard.tsx`

---

**Last Updated:** 2025-12-09
**Documentation Complete:** Yes
**Ready for Use:** Yes
