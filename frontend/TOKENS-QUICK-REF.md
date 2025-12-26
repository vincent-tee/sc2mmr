# Design Tokens - Quick Reference Card

## Import Statement
```typescript
import {
  colors,
  shadows,
  spacing,
  radii,
  typography,
  transitions,
  layout,
  presets,
  keyframes
} from '../theme/tokens';
```

## Most Used Tokens

### Colors - Common Cases
```typescript
// Primary brand (cyan glow)
bg={colors.brand[500]}          // #00D4FF
color={colors.brand[400]}       // #1ADBFF

// Accent (gold)
bg={colors.accent[500]}         // #FFB300

// Success/shields (green)
bg={colors.shield[500]}         // #00FF88

// Backgrounds
bg={colors.background.card}     // rgba(26, 32, 44, 0.8)

// Race colors
bg={colors.race.terran[500]}    // #0080FF
bg={colors.race.protoss[500]}   // #FFD700
bg={colors.race.zerg[500]}      // #9C27B0
bg={colors.race.random[500]}    // #616161

// Status
bg={colors.status.win}          // #00FF88
bg={colors.status.loss}         // #FF4444
bg={colors.status.draw}         // #FFB300
```

### Shadows - Glow Effects
```typescript
// Brand cyan
boxShadow={shadows.brandGlow}           // 0 0 20px rgba(0, 212, 255, 0.4)
boxShadow={shadows.brandGlowLarge}      // 0 0 40px rgba(0, 212, 255, 0.8)
boxShadow={shadows.brandGlowSubtle}     // 0 0 10px rgba(0, 212, 255, 0.6)

// Accent gold
boxShadow={shadows.accentGlow}          // 0 0 20px rgba(255, 179, 0, 0.4)
boxShadow={shadows.accentGlowSubtle}    // 0 0 10px rgba(255, 179, 0, 0.6)

// Shield green
boxShadow={shadows.shieldGlow}          // 0 0 20px rgba(0, 255, 136, 0.4)

// Hover state
boxShadow={shadows.hoverElevation}      // Double glow
```

### Spacing - Padding/Margin
```typescript
// 8px (most common)
p={spacing.sm}
m={spacing.sm}

// 12px
p={spacing.md}

// 16px
p={spacing.lg}
mb={spacing.lg}

// 24px
p={spacing.xl}
mb={spacing.xl}
```

### Border Radius
```typescript
borderRadius={radii.md}   // 8px (cards, inputs)
borderRadius={radii.lg}   // 12px (larger cards)
borderRadius={radii.full} // 9999px (full circle)
```

### Typography
```typescript
// Headings
fontFamily={typography.fontFamily.heading}  // Rajdhani/Orbitron
fontWeight={typography.fontWeight.bold}     // 700
letterSpacing={typography.letterSpacing.wider} // 0.2em

// Body
fontFamily={typography.fontFamily.body}     // Inter
fontSize={typography.fontSize.md}           // 16px
fontWeight={typography.fontWeight.normal}   // 400
```

### Transitions
```typescript
transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
// = all 250ms cubic-bezier(0.4, 0, 0.2, 1)

transition={`all ${transitions.fast} ${transitions.easing.easeOut}`}
// = all 150ms cubic-bezier(0.0, 0, 0.2, 1)
```

## Component Patterns

### Tactical Card
```typescript
<Box
  bg={colors.background.card}
  borderRadius={radii.lg}
  border="2px solid"
  borderColor={colors.border.medium}
  boxShadow={shadows.elevation}
  p={spacing.lg}
  transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
  _hover={{
    borderColor: colors.border.brand,
    boxShadow: shadows.hoverElevation,
  }}
>
  {children}
</Box>
```

### Button - Brand Primary
```typescript
<Button
  {...presets.button.base}
  {...presets.button.primary}
/>
// Adds: bg, color, hover effects, transitions
```

### Badge - MMR High
```typescript
<Badge
  bg={colors.shield[500]}
  color="gray.900"
  fontWeight={typography.fontWeight.bold}
/>
```

### Badge - Race
```typescript
// Terran
<Badge bg={colors.race.terran[500]} color="white" />

// Protoss
<Badge bg={colors.race.protoss[500]} color="gray.900" />

// Zerg
<Badge bg={colors.race.zerg[500]} color="white" />
```

### Avatar with Race Color
```typescript
<Avatar
  bg={`${colors.race.terran[500]}`}
  border="3px solid"
  borderColor={colors.brand[400]}
  boxShadow={shadows.brandGlow}
/>
```

### Animated Stat (Pulse)
```typescript
<Box
  animation={`pulse 2s ease-in-out infinite`}
  sx={{
    '@keyframes pulse': keyframes.pulse,
  }}
>
  {value}
</Box>
```

## Color Scales Reference

### Brand (Cyan)
```
50  100  200  300  400  500  600  700  800  900
Light ⟹ | Primary | ⟹ Dark
```
- **500**: Primary interactive color
- **400**: Hover/bright state
- **600**: Active/pressed state
- **300**: Highlight/focus
- **700+**: Darker variants for depth

### How to Use Scales
```typescript
// Light bg with dark text
bg={colors.brand[100]}

// Primary action
bg={colors.brand[500]}
color="gray.900"

// Hover state
bg={colors.brand[400]}

// Active/pressed
bg={colors.brand[600]}

// Disabled
bg={colors.brand[800]}
color={colors.text.disabled}
```

## Race Color Quick Access

```typescript
const terranColor = colors.race.terran[500];     // #0080FF
const protossColor = colors.race.protoss[500];   // #FFD700
const zergColor = colors.race.zerg[500];         // #9C27B0
const randomColor = colors.race.random[500];     // #616161
```

## Layout Constants
```typescript
layout.navHeight              // "64px"
layout.containerMaxWidth      // "1280px"
layout.cardBorderRadius       // "12px"
layout.hexagonClipPath        // Polygon definition
```

## Common Values

| Property | Token | Value |
|----------|-------|-------|
| Primary Cyan | `colors.brand[500]` | #00D4FF |
| Gold Accent | `colors.accent[500]` | #FFB300 |
| Green Success | `colors.shield[500]` | #00FF88 |
| Dark Card | `colors.background.card` | rgba(26, 32, 44, 0.8) |
| Base Spacing | `spacing.md` | 12px |
| Base Radius | `radii.md` | 8px |
| Base Transition | `transitions.base` | 250ms |

## Most Common Patterns

### 1. Glow Effect (on hover)
```typescript
boxShadow={shadows.brandGlow}
_hover={{ boxShadow: shadows.brandGlowLarge }}
```

### 2. Color Text Highlight
```typescript
textShadow={presets.textShadow.glow}
// or construct it: `0 0 40px rgba(0, 212, 255, 0.6)`
```

### 3. Card with Hover
```typescript
{...presets.card.base}
_hover={presets.card.hover}
```

### 4. Button with Transition
```typescript
bg={colors.brand[500]}
transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
_hover={{ bg: colors.brand[400] }}
_active={{ bg: colors.brand[600] }}
```

### 5. Race-Based Background
```typescript
const raceColors = {
  terran: colors.race.terran[500],
  protoss: colors.race.protoss[500],
  zerg: colors.race.zerg[500],
  random: colors.race.random[500],
};

bg={raceColors[race]}
```

## Debug Tip: Find All Token Values

Open `src/theme/tokens.ts` and search for:
- `brand: {` - All cyan colors
- `accent: {` - All gold colors
- `race: {` - All SC2 race colors
- `shadows` - All glow effects
- `spacing` - All spacing values

## Common Fixes

### "Color not found" Error
Check if you're using the correct level (50-900):
```typescript
// Wrong
bg={colors.brand}  // ❌

// Right
bg={colors.brand[500]}  // ✅
```

### "Shadow too subtle"
Use larger glow:
```typescript
// Subtle (default)
boxShadow={shadows.brandGlowSubtle}

// Medium
boxShadow={shadows.brandGlow}

// Large
boxShadow={shadows.brandGlowLarge}
```

### "Transition too fast"
Adjust timing:
```typescript
// Fast (150ms)
transition={`all ${transitions.fast}...`}

// Normal (250ms) ⭐ Most common
transition={`all ${transitions.base}...`}

// Slow (350ms)
transition={`all ${transitions.slow}...`}
```

---
**Last Updated**: 2025-12-08
**File Location**: `src/theme/tokens.ts`
**Import Path**: `../theme/tokens`
