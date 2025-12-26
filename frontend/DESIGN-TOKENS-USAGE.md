# Design Tokens Usage Guide

## Overview

The design tokens file (`src/theme/tokens.ts`) provides a centralized, semantic approach to styling the SC2 MMR Tracker. This replaces hardcoded colors and values throughout the codebase.

## File Location

```
frontend/src/theme/tokens.ts
```

## Token Categories

### 1. Colors

#### Brand Colors (Primary - Tactical Cyan)
```typescript
import { colors } from '../theme/tokens';

// Usage
<Box bg={colors.brand[500]} /> // #00D4FF
<Box color={colors.brand[400]} /> // #1ADBFF
```

#### Accent Colors (Vespene Gold)
```typescript
<Box bg={colors.accent[500]} /> // #FFB300
```

#### Shield Colors (Success - Protoss Green)
```typescript
<Box bg={colors.shield[500]} /> // #00FF88
```

#### Race-Specific Colors
```typescript
// Terran
<Box bg={colors.race.terran[500]} /> // #0080FF

// Protoss
<Box bg={colors.race.protoss[500]} /> // #FFD700

// Zerg
<Box bg={colors.race.zerg[500]} /> // #9C27B0

// Random
<Box bg={colors.race.random[500]} /> // #616161
```

#### Status Colors
```typescript
<Badge bg={colors.status.win} />      // Victory
<Badge bg={colors.status.loss} />     // Defeat
<Badge bg={colors.status.draw} />     // Draw
```

#### Background Colors
```typescript
<Box bg={colors.background.card} />
<Box bg={colors.background.overlay} />
<Box bg={colors.background.selected} />
```

### 2. Shadows (Glows)

#### Tactical Glow Effects
```typescript
import { shadows } from '../theme/tokens';

// Brand cyan glow
<Box boxShadow={shadows.brandGlow} />           // 0 0 20px rgba(0, 212, 255, 0.4)
<Box boxShadow={shadows.brandGlowLarge} />      // 0 0 40px rgba(0, 212, 255, 0.8)
<Box boxShadow={shadows.brandGlowSubtle} />     // 0 0 10px rgba(0, 212, 255, 0.6)

// Accent gold glow
<Box boxShadow={shadows.accentGlow} />          // 0 0 20px rgba(255, 179, 0, 0.4)
<Box boxShadow={shadows.accentGlowSubtle} />    // 0 0 10px rgba(255, 179, 0, 0.6)

// Shield green glow
<Box boxShadow={shadows.shieldGlow} />          // 0 0 20px rgba(0, 255, 136, 0.4)

// Zerg purple glow
<Box boxShadow={shadows.zergGlow} />            // 0 0 20px rgba(156, 39, 176, 0.4)

// Hover elevation
<Box _hover={{ boxShadow: shadows.hoverElevation }} />
```

### 3. Typography

#### Font Families
```typescript
import { typography } from '../theme/tokens';

// Headings - Rajdhani/Orbitron
<Heading fontFamily={typography.fontFamily.heading} />

// Body text - Inter
<Text fontFamily={typography.fontFamily.body} />
```

#### Font Sizes
```typescript
<Text fontSize={typography.fontSize.sm} />     // 12px
<Text fontSize={typography.fontSize.md} />     // 16px
<Heading fontSize={typography.fontSize['4xl']} /> // 36px
```

#### Font Weights
```typescript
<Text fontWeight={typography.fontWeight.bold} />      // 700
<Heading fontWeight={typography.fontWeight.black} />  // 900
```

#### Letter Spacing
```typescript
<Text letterSpacing={typography.letterSpacing.sm} />  // 0.05em (wider)
<Heading letterSpacing={typography.letterSpacing.wider} /> // 0.2em
```

### 4. Spacing

```typescript
import { spacing } from '../theme/tokens';

<Box p={spacing.md} />      // 12px
<Box m={spacing.lg} />      // 16px
<Box mb={spacing.xl} />     // 24px
```

### 5. Border Radius

```typescript
import { radii } from '../theme/tokens';

<Box borderRadius={radii.md} />  // 8px
<Box borderRadius={radii.lg} />  // 12px
<Box borderRadius={radii.full} /> // 9999px (full circle)
```

### 6. Transitions

```typescript
import { transitions } from '../theme/tokens';

<Box
  transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
/>
```

### 7. Presets

#### Card Preset
```typescript
import { presets } from '../theme/tokens';

<Box {...presets.card.base} _hover={presets.card.hover} />
```

#### Button Preset
```typescript
<Button {...presets.button.base} {...presets.button.primary} />
<Button {...presets.button.base} {...presets.button.accent} />
```

## Common Refactoring Examples

### Before (Hardcoded)
```typescript
<Box
  bg="rgba(26, 32, 44, 0.8)"
  borderRadius="12px"
  border="2px solid"
  borderColor="rgba(0, 212, 255, 0.3)"
  boxShadow="0 0 20px rgba(0, 212, 255, 0.4)"
  p={6}
  transition="all 250ms cubic-bezier(0.4, 0, 0.2, 1)"
>
  {children}
</Box>
```

### After (Using Tokens)
```typescript
import { colors, shadows, radii, spacing, transitions } from '../theme/tokens';

<Box
  bg={colors.background.card}
  borderRadius={radii.lg}
  border="2px solid"
  borderColor={colors.border.medium}
  boxShadow={shadows.brandGlow}
  p={spacing['3xl']} // or p={6}
  transition={`all ${transitions.base} ${transitions.easing.easeInOut}`}
>
  {children}
</Box>
```

## Component-Specific Guidelines

### Navigation Component
```typescript
// Background
bg={colors.background.overlay}

// Border glow
boxShadow="0 2px 10px rgba(0, 212, 255, 0.1)"

// Logo styling
bg={colors.brand[500]}
boxShadow={shadows.brandGlow}
```

### Tactical Card Component
```typescript
// Card background
bg={colors.background.card}

// Border
borderColor={colors.border.medium}

// Hover effects
boxShadow={shadows.hoverElevation}
```

### Status/MMR Badges
```typescript
// High MMR (Shield green)
bg={colors.shield[500]}

// Medium MMR (Accent gold)
bg={colors.accent[500]}

// Low MMR (Accent orange)
bg="orange.500"

// Race badges
bg={colors.race.terran[500]}
bg={colors.race.protoss[500]}
bg={colors.race.zerg[500]}
bg={colors.race.random[500]}
```

### HexagonalStat Component
```typescript
// Hexagon border
borderColor={color}
boxShadow={`0 0 30px ${color}40`}

// Use color parameter with token colors
<HexagonalStat color={colors.brand[500]} />
<HexagonalStat color={colors.accent[500]} />
<HexagonalStat color={colors.shield[500]} />
```

## StarCraft 2 Race Colors

| Race | Color | Token |
|------|-------|-------|
| Terran | Blue (#0080FF) | `colors.race.terran[500]` |
| Protoss | Gold (#FFD700) | `colors.race.protoss[500]` |
| Zerg | Purple (#9C27B0) | `colors.race.zerg[500]` |
| Random | Gray (#616161) | `colors.race.random[500]` |

## Theming Best Practices

### 1. Use Semantic Color Names
```typescript
// Good - semantic meaning
bg={colors.status.win}
bg={colors.background.card}

// Avoid - non-semantic
bg={colors.brand[300]}
```

### 2. Consistent Glow Effects
```typescript
// For brand elements
boxShadow={shadows.brandGlow}

// For accent elements
boxShadow={shadows.accentGlow}

// For success/shield elements
boxShadow={shadows.shieldGlow}
```

### 3. Color Variants
All color groups have numbered scales (50-900):
- **50-100**: Light backgrounds
- **400-500**: Primary interactive colors
- **600-700**: Hover/active states
- **800-900**: Dark/disabled states

Example progression:
```typescript
brand[50]  → brand[100] → brand[200] → brand[300] → brand[400] → brand[500]
# light ═════════════════════════════════════════════════════════ primary
brand[600] → brand[700] → brand[800] → brand[900]
primary ═════════════════════════════════════════════════════════ dark
```

## Layout Constants

```typescript
import { layout } from '../theme/tokens';

// Navigation height
height={layout.navHeight}

// Container max width
maxW={layout.containerMaxWidth}

// Hexagon clipping
clipPath={layout.hexagonClipPath}
```

## Responsive Design

Use Chakra UI's responsive syntax with pixel values from breakpoints:

```typescript
<Box
  fontSize={{ base: '12px', md: '16px', lg: '18px' }}
  p={{ base: spacing.sm, md: spacing.md, lg: spacing.lg }}
/>
```

## Animation Keyframes

```typescript
import { keyframes } from '../theme/tokens';

<Box
  animation={`pulse 2s ease-in-out infinite`}
  sx={{
    '@keyframes pulse': keyframes.pulse,
  }}
/>
```

## Testing Token Values

All tokens are exported as `const` types, enabling TypeScript autocomplete:

```typescript
import { colors, shadows } from '../theme/tokens';

// TypeScript will autocomplete available colors
const cardBg = colors.background.card
const glowEffect = shadows.brandGlow
```

## Maintenance

When updating design tokens:

1. Edit values in `src/theme/tokens.ts`
2. All components using these tokens automatically reflect the change
3. No need to update individual component files
4. TypeScript ensures type safety across the application

## Future Enhancements

- Implement dark/light mode variants
- Add animation presets
- Create component-specific token groups
- Add accessibility contrast checking
