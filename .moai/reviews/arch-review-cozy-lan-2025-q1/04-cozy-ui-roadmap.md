# Phase 4.1: Cozy LAN Party UI Roadmap

## SC2 MMR Tracker - Aesthetic Transformation Guide

**Review Date:** December 26, 2025  
**Reviewer:** Mr.Alfred (MoAI-ADK)  
**Status:** Complete  
**Token Usage:** ~30K tokens

---

## Executive Summary

This roadmap defines the systematic transformation from **"Military Tactical"** aesthetic to **"Cozy LAN Party"** visual language. The transformation touches 20+ files across theme, components, and pages, with an estimated effort of **20-25 hours**.

### Transformation Philosophy

| Dimension | Tactical (Current) | Cozy LAN Party (Target) |
|-----------|-------------------|------------------------|
| **Mood** | Intense, serious | Warm, friendly, relaxed |
| **Typography** | Sci-fi, uppercase | Friendly, mixed case |
| **Colors** | Neon glows, dark | Warm pastels, cream backgrounds |
| **Shapes** | Angular, clipped | Rounded, soft curves |
| **Language** | Military jargon | Casual gaming terms |
| **Animations** | Scanlines, pulses | Gentle fades, bounces |

---

## Phase 1: Theme Foundation (3-4 hours)

### 1.1 Font Stack Update

**Current** (`theme/tokens.ts:214-217`):
```typescript
fontFamily: {
  heading: "'Rajdhani', 'Orbitron', 'Inter', ...",
  body: "'Inter', -apple-system, ...",
}
```

**Target**:
```typescript
fontFamily: {
  heading: "'Poppins', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  body: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  // Keep monospace for stats/numbers
  mono: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
}
```

**Google Fonts Import** (`index.html`):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

### 1.2 Color Palette Softening

**Current Palette** → **Cozy Palette**:

```typescript
// theme/tokens.ts - Updated colors

export const cozyColors = {
  // Primary: Pastel Orange (warmer, less intense)
  primary: {
    50: '#FFF8F0',
    100: '#FFEDD5',
    200: '#FED7AA',
    300: '#FDBA74',
    400: '#FB923C',
    500: '#F97316',  // Main primary - softer orange
    600: '#EA580C',
    700: '#C2410C',
    800: '#9A3412',
    900: '#7C2D12',
  },

  // Accent: Coral/Salmon (warm, friendly)
  accent: {
    50: '#FFF5F5',
    100: '#FFE4E6',
    200: '#FECDD3',
    300: '#FDA4AF',
    400: '#FB7185',
    500: '#F43F5E',  // Soft coral
    600: '#E11D48',
    700: '#BE123C',
    800: '#9F1239',
    900: '#881337',
  },

  // Success: Soft Teal (calming success)
  success: {
    50: '#F0FDFA',
    100: '#CCFBF1',
    200: '#99F6E4',
    300: '#5EEAD4',
    400: '#2DD4BF',
    500: '#14B8A6',  // Teal success
    600: '#0D9488',
    700: '#0F766E',
    800: '#115E59',
    900: '#134E4A',
  },

  // Background: Warm Cream/Beige
  surface: {
    50: '#FEFDFB',   // Lightest cream
    100: '#FDF8F3',  // Card background
    200: '#FAF3EB',  // Hover state
    300: '#F5EAD8',  // Borders
    400: '#E8D5B9',  // Muted elements
    500: '#D4B896',  // Secondary text
    600: '#B89B74',
    700: '#957852',
    800: '#725838',
    900: '#4A3823',  // Dark text (softer than black)
  },

  // Race colors (softened versions)
  race: {
    terran: {
      light: '#BFDBFE',  // Soft blue
      main: '#60A5FA',   // Medium blue
      dark: '#2563EB',
    },
    protoss: {
      light: '#FEF3C7',  // Soft gold
      main: '#FBBF24',   // Amber
      dark: '#D97706',
    },
    zerg: {
      light: '#E9D5FF',  // Soft purple
      main: '#A855F7',   // Purple
      dark: '#7C3AED',
    },
    random: {
      light: '#E5E7EB',  // Light gray
      main: '#9CA3AF',   // Medium gray
      dark: '#6B7280',
    },
  },
};
```

### 1.3 Shadow System Update

**Remove neon glows, add soft depth shadows**:

```typescript
// theme/tokens.ts - Updated shadows

export const cozyShadows = {
  none: 'none',
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  base: '0 2px 4px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
  md: '0 4px 8px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
  lg: '0 8px 16px rgba(0, 0, 0, 0.1), 0 4px 8px rgba(0, 0, 0, 0.05)',
  xl: '0 16px 32px rgba(0, 0, 0, 0.12), 0 8px 16px rgba(0, 0, 0, 0.06)',
  
  // Card-specific shadows
  card: '0 4px 12px rgba(0, 0, 0, 0.08)',
  cardHover: '0 8px 24px rgba(0, 0, 0, 0.12)',
  
  // Colored subtle glows (for race colors)
  primaryGlow: '0 4px 16px rgba(249, 115, 22, 0.2)',
  successGlow: '0 4px 16px rgba(20, 184, 166, 0.2)',
  
  // Inner shadows for depth
  inset: 'inset 0 2px 4px rgba(0, 0, 0, 0.05)',
};
```

### 1.4 Animation Presets

**Remove scanlines, add gentle transitions**:

```typescript
// theme/animations.ts - Cozy animations

export const cozyAnimations = {
  // Gentle hover bounce
  bounce: {
    '0%, 100%': { transform: 'translateY(0)' },
    '50%': { transform: 'translateY(-4px)' },
  },
  
  // Soft pulse for attention
  softPulse: {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.7 },
  },
  
  // Smooth fade in
  fadeIn: {
    from: { opacity: 0, transform: 'translateY(8px)' },
    to: { opacity: 1, transform: 'translateY(0)' },
  },
  
  // Card hover lift
  lift: {
    from: { transform: 'translateY(0)', boxShadow: 'var(--shadow-card)' },
    to: { transform: 'translateY(-4px)', boxShadow: 'var(--shadow-cardHover)' },
  },
  
  // Celebration confetti (optional)
  confettiDrop: {
    '0%': { transform: 'translateY(-100vh) rotate(0deg)', opacity: 1 },
    '100%': { transform: 'translateY(100vh) rotate(720deg)', opacity: 0 },
  },
};

// Remove these tactical animations:
// - scanline
// - shimmer (aggressive)
// - pulse (aggressive)
// - twinkle (starfield)
```

### 1.5 Global Styles Update

**Remove background effects** (`theme/index.ts:88-127`):

```typescript
// BEFORE (tactical):
body: {
  '&::before': {
    // starfield effect - REMOVE
  },
  '&::after': {
    // scanline effect - REMOVE
  },
}

// AFTER (cozy):
styles: {
  global: {
    body: {
      bg: 'surface.100',
      color: 'surface.900',
      fontFamily: 'body',
      lineHeight: 'relaxed',
    },
    // Simple, clean global styles
    '*': {
      borderColor: 'surface.300',
    },
    'h1, h2, h3, h4, h5, h6': {
      fontFamily: 'heading',
      fontWeight: '600',
    },
  },
}
```

---

## Phase 2: Component Library (8-10 hours)

### 2.1 TacticalCard → CozyCard

**Current** (`components/TacticalCard.tsx`):
- Clip-path polygon corners
- Neon glow borders
- Scanline overlay
- Corner brackets

**Target** (`components/Card.tsx`):
```tsx
interface CardProps extends BoxProps {
  variant?: 'default' | 'elevated' | 'outlined';
  hoverEffect?: boolean;
  children: ReactNode;
}

const Card: FC<CardProps> = ({ 
  variant = 'default', 
  hoverEffect = true,
  children, 
  ...props 
}) => {
  const variants = {
    default: {
      bg: 'surface.100',
      border: '1px solid',
      borderColor: 'surface.300',
    },
    elevated: {
      bg: 'white',
      boxShadow: 'card',
    },
    outlined: {
      bg: 'transparent',
      border: '2px solid',
      borderColor: 'primary.300',
    },
  };

  return (
    <Box
      borderRadius="xl"          // Rounded corners
      p={4}
      transition="all 0.2s ease"
      {...variants[variant]}
      {...(hoverEffect && {
        _hover: {
          transform: 'translateY(-2px)',
          boxShadow: 'cardHover',
        },
      })}
      {...props}
    >
      {children}
    </Box>
  );
};
```

### 2.2 TacticalBackground → Remove or Simplify

**Current**: Grid pattern with cyan glow

**Target**: Remove entirely or use subtle dot pattern:
```tsx
// Optional: Subtle dot pattern background
const DotBackground: FC = () => (
  <Box
    position="fixed"
    inset={0}
    zIndex={-1}
    bg="surface.50"
    backgroundImage="radial-gradient(surface.300 1px, transparent 1px)"
    backgroundSize="24px 24px"
    opacity={0.5}
  />
);
```

### 2.3 HexagonalStat → RoundedStat

**Current**: Hexagonal clip-path, neon borders

**Target**:
```tsx
interface StatCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
}

const StatCard: FC<StatCardProps> = ({ label, value, icon, trend }) => (
  <VStack
    bg="surface.100"
    borderRadius="2xl"
    p={4}
    spacing={1}
    minW="120px"
    boxShadow="sm"
    border="1px solid"
    borderColor="surface.200"
  >
    {icon && <Box color="primary.500" fontSize="xl">{icon}</Box>}
    <Text 
      fontSize="2xl" 
      fontWeight="bold" 
      color="surface.800"
      fontFamily="mono"
    >
      {value}
    </Text>
    <Text fontSize="sm" color="surface.600" textTransform="capitalize">
      {label}
    </Text>
    {trend && (
      <Badge 
        colorScheme={trend === 'up' ? 'green' : trend === 'down' ? 'red' : 'gray'}
        variant="subtle"
        borderRadius="full"
      >
        {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '–'}
      </Badge>
    )}
  </VStack>
);
```

### 2.4 Navigation Softening

**Changes**:
1. Remove corner brackets pseudo-elements
2. Remove glow effects
3. Add rounded pill-style nav links
4. Soften logo treatment

```tsx
// Navigation link style update
const navLinkStyle = {
  px: 4,
  py: 2,
  borderRadius: 'full',
  fontWeight: 'medium',
  color: 'surface.700',
  transition: 'all 0.2s',
  _hover: {
    bg: 'primary.50',
    color: 'primary.600',
  },
  _activeLink: {
    bg: 'primary.100',
    color: 'primary.700',
  },
};
```

### 2.5 PlayerCard Transformation

**Current Features to Remove**:
- Glow on hover
- Clip-path corners
- Uppercase text
- Military styling

**Target Features**:
- Rounded avatar with soft shadow
- Warm color badges
- Friendly stat display
- Subtle hover elevation

```tsx
const PlayerCard: FC<PlayerCardProps> = ({ player, size = 'md', onClick }) => {
  return (
    <VStack
      bg="white"
      borderRadius="2xl"
      boxShadow="card"
      p={4}
      spacing={3}
      cursor={onClick ? 'pointer' : 'default'}
      transition="all 0.2s ease"
      _hover={onClick ? {
        transform: 'translateY(-4px)',
        boxShadow: 'cardHover',
      } : undefined}
      onClick={onClick}
    >
      {/* Rounded avatar with race color ring */}
      <Avatar
        size={size === 'lg' ? 'xl' : 'lg'}
        name={player.name}
        bg={`race.${player.favorite_race.toLowerCase()}.light`}
        color={`race.${player.favorite_race.toLowerCase()}.dark`}
        borderWidth={3}
        borderColor={`race.${player.favorite_race.toLowerCase()}.main`}
      />
      
      {/* Player name - Title case, friendly font */}
      <Text 
        fontWeight="semibold" 
        fontSize={size === 'lg' ? 'xl' : 'md'}
        color="surface.800"
      >
        {player.name}
      </Text>
      
      {/* MMR with skill badge */}
      <HStack>
        <SkillBadge mmr={player.mmr} size="sm" />
        <Text color="surface.600" fontSize="sm">
          {Math.round(player.mmr)} MMR
        </Text>
      </HStack>
      
      {/* Win rate pill */}
      <Badge 
        colorScheme={player.win_rate >= 0.5 ? 'green' : 'orange'}
        borderRadius="full"
        px={3}
      >
        {(player.win_rate * 100).toFixed(0)}% wins
      </Badge>
    </VStack>
  );
};
```

### 2.6 RankBadge → SkillBadge

**Rename and soften**:
- Remove angular shapes
- Use rounded badges with gradient fills
- Friendly tier names (optional)

```tsx
const skillTiers = [
  { min: 0, max: 1500, name: 'Bronze', color: '#CD7F32' },
  { min: 1500, max: 2000, name: 'Silver', color: '#C0C0C0' },
  { min: 2000, max: 2500, name: 'Gold', color: '#FFD700' },
  { min: 2500, max: 3000, name: 'Platinum', color: '#E5E4E2' },
  { min: 3000, max: 3500, name: 'Diamond', color: '#B9F2FF' },
  { min: 3500, max: Infinity, name: 'Master', color: '#9B30FF' },
];

const SkillBadge: FC<{ mmr: number; size?: 'sm' | 'md' | 'lg' }> = ({ mmr, size = 'md' }) => {
  const tier = skillTiers.find(t => mmr >= t.min && mmr < t.max);
  
  return (
    <Badge
      bg={tier?.color}
      color="white"
      px={size === 'sm' ? 2 : 3}
      py={size === 'sm' ? 0.5 : 1}
      borderRadius="full"
      fontWeight="semibold"
      fontSize={size === 'sm' ? 'xs' : 'sm'}
      textShadow="0 1px 2px rgba(0,0,0,0.2)"
    >
      {tier?.name}
    </Badge>
  );
};
```

### 2.7 LoadingState & EmptyState

**LoadingState**: Replace skeleton glow with subtle shimmer
```tsx
const LoadingState: FC<{ variant: string }> = ({ variant }) => (
  <VStack spacing={4} p={8} align="center">
    <Spinner 
      size="xl" 
      color="primary.400" 
      thickness="4px"
      speed="0.8s"
    />
    <Text color="surface.600">Loading {variant}...</Text>
  </VStack>
);
```

**EmptyState**: Friendly illustrations and messaging
```tsx
const EmptyState: FC<{ variant: string }> = ({ variant }) => (
  <VStack spacing={6} p={12} textAlign="center">
    {/* Use friendly emoji or illustration */}
    <Text fontSize="6xl">
      {variant === 'players' ? '👥' : variant === 'matches' ? '🎮' : '📭'}
    </Text>
    <VStack spacing={2}>
      <Text fontSize="xl" fontWeight="semibold" color="surface.800">
        {variant === 'players' ? 'No Players Yet' : 'No Matches Found'}
      </Text>
      <Text color="surface.600">
        {variant === 'players' 
          ? 'Upload some replays to get started!' 
          : 'Play some games and upload the replays.'}
      </Text>
    </VStack>
    <Button colorScheme="primary" borderRadius="full">
      Upload Replay
    </Button>
  </VStack>
);
```

---

## Phase 3: Page-Level Changes (6-8 hours)

### 3.1 Terminology Replacement

| File | Current | Cozy Alternative |
|------|---------|------------------|
| `Home.tsx` | "TACTICAL COMMAND" | "MMR Tracker" |
| `Home.tsx` | "COMMAND CENTER" | "Home" |
| `Home.tsx` | "COMMAND MODULES" | "Quick Actions" |
| `TeamGenerator/index.tsx` | "TACTICAL DEPLOYMENT" | "Team Builder" |
| `TeamGenerator/index.tsx` | "OPERATIVES" | "Players" |
| `TeamGenerator/BalanceResults.tsx` | "DEPLOYMENT CONFIGURATIONS" | "Team Options" |
| `MatchHistory.tsx` | "BATTLE ARCHIVE" | "Match History" |
| `MatchHistory.tsx` | "OPERATIONS LOG" | "Recent Games" |
| `MatchDetail/index.tsx` | "OPERATIVES" | "Players" |
| `MatchDetail/index.tsx` | "MISSION SUMMARY" | "Match Summary" |
| `Players.tsx` | "OPERATIVE ROSTER" | "Player Directory" |
| `Navigation.tsx` | "COMMAND PANEL" | "Menu" |

### 3.2 Text Transform Removal

**Global search/replace**:
```typescript
// Remove all instances of:
textTransform: 'uppercase'  // 100+ occurrences

// Replace with:
textTransform: 'capitalize'  // For headings only

// Or remove entirely for body text
```

### 3.3 Letter Spacing Reduction

**Current**: `letterSpacing: 'wider'` (~0.15em)  
**Target**: `letterSpacing: 'normal'` or remove

### 3.4 Page Header Updates

**Current Pattern**:
```tsx
<Text 
  fontSize="4xl" 
  fontWeight="black" 
  textTransform="uppercase"
  letterSpacing="wider"
  textShadow="0 0 40px rgba(0, 212, 255, 0.6)"
>
  TACTICAL COMMAND
</Text>
```

**Cozy Pattern**:
```tsx
<Heading 
  as="h1"
  size="2xl" 
  color="surface.800"
  fontWeight="semibold"
>
  Team Builder
</Heading>
<Text color="surface.600" fontSize="lg">
  Balance your teams for the best matches
</Text>
```

---

## Phase 4: Micro-Interactions (2-3 hours)

### 4.1 Button Interactions

**Current**: Glow on hover, harsh transitions  
**Target**: Subtle lift, soft shadow expansion

```tsx
const Button = {
  baseStyle: {
    borderRadius: 'full',  // Pill buttons
    fontWeight: '600',
    transition: 'all 0.2s ease',
  },
  variants: {
    primary: {
      bg: 'primary.500',
      color: 'white',
      _hover: {
        bg: 'primary.600',
        transform: 'translateY(-1px)',
        boxShadow: 'primaryGlow',
      },
      _active: {
        transform: 'translateY(0)',
        bg: 'primary.700',
      },
    },
    secondary: {
      bg: 'surface.100',
      color: 'surface.800',
      border: '1px solid',
      borderColor: 'surface.300',
      _hover: {
        bg: 'surface.200',
        borderColor: 'surface.400',
      },
    },
  },
};
```

### 4.2 Card Selection

**Current**: Pulsing glow animation  
**Target**: Soft check indicator, subtle border color

```tsx
// Selected state
const selectedCardStyle = {
  borderColor: 'primary.400',
  borderWidth: '2px',
  bg: 'primary.50',
  position: 'relative',
  '&::after': {
    content: '"✓"',
    position: 'absolute',
    top: 2,
    right: 2,
    bg: 'primary.500',
    color: 'white',
    borderRadius: 'full',
    w: 6,
    h: 6,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 'xs',
    fontWeight: 'bold',
  },
};
```

### 4.3 Success Celebrations

**Add optional confetti for team generation**:
```tsx
import { useCallback } from 'react';
import confetti from 'canvas-confetti';

const celebrateSuccess = useCallback(() => {
  confetti({
    particleCount: 100,
    spread: 70,
    origin: { y: 0.6 },
    colors: ['#F97316', '#FBBF24', '#14B8A6'],
  });
}, []);
```

### 4.4 Toast Styling

```tsx
const cozyToast = {
  success: {
    bg: 'success.50',
    color: 'success.800',
    borderLeft: '4px solid',
    borderColor: 'success.500',
  },
  error: {
    bg: 'accent.50',
    color: 'accent.800',
    borderLeft: '4px solid',
    borderColor: 'accent.500',
  },
  info: {
    bg: 'primary.50',
    color: 'primary.800',
    borderLeft: '4px solid',
    borderColor: 'primary.500',
  },
};
```

---

## Implementation Checklist

### Week 1: Theme Foundation
- [ ] Update `theme/tokens.ts` with cozy color palette
- [ ] Replace fonts in `theme/index.ts`
- [ ] Update `theme/animations.ts` with gentle animations
- [ ] Remove global background effects
- [ ] Update shadow definitions
- [ ] Add Google Fonts import to `index.html`

### Week 2: Core Components
- [ ] Transform `TacticalCard` → `Card`
- [ ] Remove or simplify `TacticalBackground`
- [ ] Transform `HexagonalStat` → `StatCard`
- [ ] Update `Navigation` styling
- [ ] Update `PlayerCard` design
- [ ] Transform `RankBadge` → `SkillBadge`

### Week 3: Pages
- [ ] Update `Home.tsx` terminology and styling
- [ ] Update `TeamGenerator/*` components
- [ ] Update `MatchHistory.tsx`
- [ ] Update `MatchDetail/*` components
- [ ] Update `Players.tsx`
- [ ] Global text-transform cleanup

### Week 4: Polish
- [ ] Update `LoadingState` and `EmptyState`
- [ ] Add micro-interactions
- [ ] Toast styling
- [ ] Optional: Add celebration animations
- [ ] Final review and accessibility check

---

## Validation Criteria

### Visual Validation
- [ ] No neon/cyan glows visible
- [ ] All corners rounded (no clip-path)
- [ ] Typography uses Poppins/Inter
- [ ] No UPPERCASE text blocks
- [ ] Warm cream/beige backgrounds
- [ ] Soft shadows instead of glows

### Functional Validation
- [ ] All interactive elements work
- [ ] Hover states are subtle but visible
- [ ] Loading states are clear
- [ ] Error states are friendly
- [ ] Mobile responsiveness preserved

### User Feedback
- [ ] "Cozy" or "friendly" descriptor used
- [ ] No "intense" or "aggressive" feedback
- [ ] Readable text at all sizes
- [ ] Comfortable for extended use

---

**Document Version:** 1.0  
**Status:** Complete  
**Related:** `05-priority-matrix.md`, `06-mcp-integration-guide.md`
