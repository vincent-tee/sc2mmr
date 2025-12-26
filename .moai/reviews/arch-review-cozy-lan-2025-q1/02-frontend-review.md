# SC2 MMR Tracker - Frontend Architecture Review (Phase 2)

**Review Date:** December 26, 2025
**Reviewer:** Mr.Alfred (MoAI-ADK)
**Status:** Complete
**Token Usage:** ~60K tokens

---

## Executive Summary

The frontend codebase demonstrates **solid TypeScript practices** with a well-structured React + Chakra UI architecture. However, it is deeply infused with **"Military Tactical" aesthetic** that permeates 30+ files across components, theme tokens, and pages. The transition to "Cozy LAN Party" will require coordinated changes across the theme system, component library, and page-level styling.

### Key Metrics

| Category | Status | Details |
|----------|--------|---------|
| Type Safety | ✅ Excellent | Only 4 `any` usages, 2 `as any` casts |
| Component Architecture | ✅ Good | Well-decomposed TeamGenerator, proper separation |
| State Management | ✅ Good | React Query used consistently |
| Performance | ⚠️ Partial | Limited memoization, no code splitting |
| Tactical Styling | 🔴 Heavy | 385+ tactical text instances, 111+ visual effects |

### Estimated Cozy Transformation Effort

| Scope | Files | Lines |
|-------|-------|-------|
| Theme Foundation | 3 | ~1,100 |
| Core Components | 6 | ~1,500 |
| Pages | 8 | ~2,500 |
| Utilities | 3 | ~200 |
| **Total** | **20** | **~5,300** |

---

## 2.1 Component Architecture

### 2.1.1 TypeScript Type Safety

**Status: EXCELLENT**

| Issue Type | Count | Files |
|------------|-------|-------|
| `: any` usage | 2 | `FailedUploads.tsx:116, 155` |
| `as any` casts | 2 | `WinProbabilityDisplay.tsx:140, 177` |
| Missing types | 0 | - |

**Specific Issues:**

```typescript
// FailedUploads.tsx:116 - Should use proper error type
onError: (error: any) => {  // Should be: ApiClientError | Error

// WinProbabilityDisplay.tsx:140 - Chakra prop type mismatch
textTransform={config.labelTextTransform as any}
```

**Recommendation:** Define proper error types and fix Chakra prop typing.

### 2.1.2 Component Reusability Patterns

**Status: GOOD**

| Component | Purpose | Reusability |
|-----------|---------|-------------|
| `TacticalCard` | Styled card wrapper | High (4 variants) |
| `TacticalBackground` | Grid background | High (3 color variants) |
| `PlayerCard` | Player display | High (3 sizes) |
| `RankBadge` | MMR rank display | High (4 sizes) |
| `EmptyState` | Empty data display | High (3 variants) |
| `LoadingState` | Skeleton loaders | High (3 variants) |
| `ErrorBoundary` | Error catching | High (per-route) |
| `HexagonalStat` | Stat display | Medium (single style) |

**Issues:**
- `HexagonalStat` is tightly coupled to tactical aesthetic
- `VSScreen` has hardcoded animation keyframes (should use theme)

### 2.1.3 Props Interface Design

**Status: EXCELLENT**

All components have properly typed interfaces:

```typescript
// Example: TacticalCard
interface TacticalCardProps extends Omit<BoxProps, 'onClick'> {
  children: ReactNode;
  glowColor?: string;
  onClick?: () => void;
  variant?: TacticalCardVariant;
}
```

### 2.1.4 Error Boundary Strategy

**Status: GOOD**

**Location:** `frontend/src/App.tsx:36-124`

- Per-route error boundaries wrapping each page
- Class component with `getDerivedStateFromError` and `componentDidCatch`
- Development mode shows stack trace
- Provides "Try Again" and "Go Home" recovery actions

**Recommendation:** Consider adding error reporting service integration.

### 2.1.5 Co-location Effectiveness

**Status: GOOD**

```
src/
├── pages/
│   ├── TeamGenerator/          # Decomposed with sub-components
│   │   ├── index.tsx
│   │   ├── TeamSelector.tsx
│   │   ├── BalanceControls.tsx
│   │   ├── GenerateButton.tsx
│   │   └── BalanceResults.tsx
│   └── MatchDetail/            # Decomposed with tabs
│       ├── index.tsx
│       ├── types.ts
│       ├── helpers.ts
│       └── [Tab components]
├── components/
│   ├── common/                 # Shared utilities
│   ├── charts/                 # Chart components
│   └── [feature components]
├── hooks/                      # Custom hooks
├── api/                        # API layer
└── theme/                      # Theme configuration
```

---

## 2.2 State Management

### 2.2.1 State Management Patterns

**Status: GOOD**

| Pattern | Usage | Files |
|---------|-------|-------|
| React Query | Server state | All data-fetching pages |
| useState | Local UI state | All interactive components |
| useDisclosure | Modal/drawer state | `FailedUploads.tsx`, `Navigation.tsx` |

**No global state management** (Redux/Zustand) - appropriate for 1-10 concurrent users.

### 2.2.2 Data Synchronization

**Status: GOOD**

React Query configuration (`main.tsx:15-22`):
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
});
```

Cache invalidation properly used:
- `queryClient.invalidateQueries({ queryKey: ['failed-uploads'] })` after mutations
- `keepPreviousData` for pagination

### 2.2.3 Loading State Handling

**Status: GOOD**

Consistent patterns across pages:
```typescript
if (isLoadingPlayers) {
  return <LoadingState variant="players" count={8} />;
}

if (!players || players.length === 0) {
  return <EmptyState variant="players" ... />;
}
```

### 2.2.4 Error Recovery Flows

**Status: GOOD**

1. **API errors:** Handled via Axios interceptor with user-friendly messages
2. **Upload errors:** Retry mechanism in `UploadReplays.tsx`
3. **Failed uploads:** Manual winner selection recovery flow
4. **React errors:** Per-route error boundaries with retry

### 2.2.5 Optimistic Update Opportunities

**Status: NOT IMPLEMENTED**

**Opportunities:**
1. Mark upload as reviewed (immediate UI feedback)
2. Clear/Remove file from list
3. Player toggle selection (already instant - good)

---

## 2.3 Performance

### 2.3.1 Bundle Size Analysis

**Status: ACCEPTABLE**

| Package | Purpose | Size Impact |
|---------|---------|-------------|
| `@chakra-ui/react` | UI framework | ~150KB gzipped |
| `framer-motion` | Animations | ~50KB gzipped |
| `recharts` | Charts | ~100KB gzipped |
| `react-dropzone` | File upload | ~10KB gzipped |
| `html2canvas` | Screenshots | ~40KB gzipped |
| `axios` | HTTP client | ~15KB gzipped |
| `react-icons` | Icons | Tree-shakeable |

**Total estimated:** ~400KB gzipped (acceptable for personal project)

**Recommendation:** Lazy load `recharts` and `html2canvas` (only used on specific pages).

### 2.3.2 Memoization Usage

**Status: PARTIAL**

**Files with memoization:**
| File | Techniques |
|------|------------|
| `HeadToHead.tsx` | `memo` (3), `useMemo` (3), `useCallback` (2) |
| `Leaderboard.tsx` | `memo` (5), `useMemo` (1), `useCallback` (1) |
| `Achievements.tsx` | `memo` (2), `useMemo` (2) |
| `AchievementGrid.tsx` | `memo` (2), `useMemo` (3), `useCallback` (2) |
| `LeaderboardTable.tsx` | `memo` (5), `useCallback` (1) |

**Missing memoization:**
1. `PlayerCard.tsx` - No memo despite list usage
2. `TacticalCard.tsx` - No memo
3. `MatchCard` in MatchHistory - No memo
4. `PlayerHighlightCard` in MatchHistory - No memo

### 2.3.3 Code Splitting

**Status: NOT IMPLEMENTED**

All routes eagerly loaded:
```typescript
import Home from './pages/Home';
import TeamGenerator from './pages/TeamGenerator';
```

**Recommendation:** Implement route-based code splitting:
```typescript
const Home = lazy(() => import('./pages/Home'));
const TeamGenerator = lazy(() => import('./pages/TeamGenerator'));
```

**Priority candidates:**
1. `AdaptiveModel.tsx` (AI documentation page)
2. `RatingSystem.tsx` (rating info page)
3. `HeadToHead.tsx` (secondary feature)
4. `Achievements.tsx` (secondary feature)

---

## 2.4 Styling & Theme System

### 2.4.1 Current Theme Structure

**Location:** `frontend/src/theme/`

| File | Purpose |
|------|---------|
| `index.ts` | Main Chakra theme extension |
| `tokens.ts` | Design token definitions |
| `animations.ts` | Keyframe animations |

### 2.4.2 Tactical Elements Inventory

#### Fonts (To Replace)

**Current** (`theme/index.ts:85-86`):
```typescript
fonts: {
  heading: `'Rajdhani', 'Orbitron', 'Inter', ...`,  // Sci-fi fonts
  body: `'Inter', -apple-system, ...`,
}
```

**Cozy Alternative:**
```typescript
fonts: {
  heading: `'Poppins', 'Inter', -apple-system, ...`,
  body: `'Inter', -apple-system, ...`,
}
```

#### Colors (Partial Update Needed)

| Current | Action | Cozy Rename |
|---------|--------|-------------|
| `brand` (orange) | Keep colors | `warm` |
| `accent` (red) | Soften to coral | `coral` |
| `shield` (gold) | Keep | `gold` |
| `space` (warm grays) | Keep | `cream` / `neutral` |

**Cyan/neon to remove:** 111 occurrences of `rgba(0, 212, 255, ...)`

#### Text Styling Patterns

| Pattern | Count | Action |
|---------|-------|--------|
| `textTransform: 'uppercase'` | ~100 | Remove or limit |
| `letterSpacing: 'wider'/'wide'` | ~80 | Reduce to 'normal' |
| `fontFamily: 'heading'` | ~120 | Update font stack |
| `textShadow: '0 0 ...'` (glows) | ~85 | Remove |

#### Visual Effects to Transform

| Current | Count | Cozy Alternative |
|---------|-------|------------------|
| `clipPath: 'polygon(...)'` | 15 | `borderRadius: 'xl'` |
| `boxShadow: '0 0 ... glow'` | 96 | `boxShadow: 'lg'` |
| Scanline animation | 3 | Remove or subtle fade |
| Corner brackets | 8 | Remove |
| Grid background | 4 | Dot pattern or remove |

### 2.4.3 Files Requiring Cozy Transformation

#### Priority 1: Core Theme (3 files)

| File | Lines | Key Changes |
|------|-------|-------------|
| `theme/index.ts` | 262 | Fonts, button styles, global styles |
| `theme/tokens.ts` | 455 | Color names, shadow definitions |
| `theme/animations.ts` | 418 | Remove/replace tactical animations |

#### Priority 2: Tactical Components (6 files)

| File | Lines | Key Changes |
|------|-------|-------------|
| `TacticalCard.tsx` | 128 | Rename to `Card`, remove clips |
| `TacticalBackground.tsx` | 97 | Remove or soften grid |
| `HexagonalStat.tsx` | 148 | Replace with rounded card stat |
| `Navigation.tsx` | 285 | Remove corner brackets, soften |
| `PlayerCard.tsx` | 304 | Remove glow effects, soften |
| `VSScreen.tsx` | 545 | Soften animations, colors |

#### Priority 3: Pages with Heavy Tactical Styling (8 files)

| File | Lines | Key Changes |
|------|-------|-------------|
| `Home.tsx` | 445 | Replace tactical headings, terms |
| `TeamGenerator/index.tsx` | 291 | "TACTICAL DEPLOYMENT" → "Team Builder" |
| `TeamGenerator/TeamSelector.tsx` | 151 | "OPERATIVE" → "Player" |
| `TeamGenerator/BalanceResults.tsx` | ~200 | "DEPLOYMENT" → "Configuration" |
| `MatchHistory.tsx` | 690 | "BATTLE ARCHIVE" → "Match History" |
| `MatchDetail/index.tsx` | ~300 | "OPERATIVES" → "Players" |
| `Players.tsx` | ~250 | "OPERATIVES" → "Players" |
| `MatchDetail/OperativesTab.tsx` | ~100 | Rename to PlayersTab.tsx |

### 2.4.4 Military Terminology to Replace

| Current | Cozy Alternative | Count |
|---------|------------------|-------|
| "TACTICAL COMMAND" | "MMR Tracker" | 2 |
| "TACTICAL DEPLOYMENT" | "Team Builder" | 4 |
| "COMMAND CENTER" | "Home" | 2 |
| "COMMAND MODULES" | "Quick Actions" | 1 |
| "COMMAND PANEL" | "Menu" | 1 |
| "OPERATIVES" | "Players" | 6 |
| "MISSIONS" | "Games" | 2 |
| "OPERATIONS" | "Matches" | 2 |
| "BATTLE ARCHIVE" | "Match History" | 2 |
| "DEPLOYMENT CONFIGURATIONS" | "Team Options" | 1 |

---

## 2.5 UX & User Journey

### 2.5.1 Team Balance Flow

**Current Flow:**
1. Page loads → Shows all players
2. Click players to select → Visual selection with glows
3. Click "Generate Teams" → Loading skeleton
4. Results display with export options

**Observations:**
- ✅ Clear selection state with visual feedback
- ✅ Validation messages (min 2 players, odd player warning)
- ⚠️ No drag-and-drop player selection
- ⚠️ No "undo" for accidental deselection

**Cozy Improvements:**
- Add player search/filter
- Consider drag-and-drop team assignment
- Add "last used" player preset

### 2.5.2 Replay Upload Feedback

**Status: EXCELLENT**

- Drag-drop zone with clear affordance
- Per-file status badges and progress bars
- Summary toast with success/duplicate/error counts
- BeforeUnload warning prevents accidental navigation
- Retry mechanism for failed files

### 2.5.3 Error Messaging Clarity

**Status: GOOD**

API error handling (`api/client.ts:43-76`) provides user-friendly messages:
```typescript
switch (status) {
  case 400: error.userMessage = data.detail || 'Invalid request';
  case 404: error.userMessage = data.detail || 'Resource not found';
  case 409: error.userMessage = data.detail || 'Duplicate entry';
  case 500: error.userMessage = 'Server error. Please try again later.';
}
```

### 2.5.4 Empty States and Loading States

**Status: EXCELLENT**

- `EmptyState.tsx`: 3 variants with action buttons
- `LoadingState.tsx`: Skeleton screens, 3 variants, custom message support

### 2.5.5 Micro-interaction Opportunities

**Currently Implemented:**
- Hover transforms (`translateY(-4px)`)
- Pulse animations on selected states
- Shimmer on primary CTA button
- Scanline effect on tactical cards

**Cozy Micro-interactions to Add:**
1. Subtle bounce on button click (instead of glow)
2. Confetti on team generation success
3. Gentle fade transitions between pages
4. Tooltip with delay for first-time hints
5. Progress celebration when milestones reached

---

## Priority Recommendations

### Immediate (Before Cozy Redesign)

| Priority | Task | Effort |
|----------|------|--------|
| P0 | Fix 4 `any` type usages | 30 min |
| P0 | Add `React.memo` to list components | 1 hour |
| P1 | Implement route-based code splitting | 2 hours |

### Cozy Redesign - Phase 1 (Theme Foundation)

| Priority | Task | Effort |
|----------|------|--------|
| P0 | Update fonts in `theme/index.ts` | 1 hour |
| P0 | Redefine tokens in `theme/tokens.ts` | 2 hours |
| P1 | Create new animation presets | 2 hours |

### Cozy Redesign - Phase 2 (Component Library)

| Priority | Task | Effort |
|----------|------|--------|
| P0 | Transform `TacticalCard` → `CozyCard` | 2 hours |
| P1 | Remove/redesign `TacticalBackground` | 1 hour |
| P1 | Simplify `HexagonalStat` to rounded stats | 2 hours |
| P1 | Update `Navigation` with friendly styling | 2 hours |

### Cozy Redesign - Phase 3 (Pages)

| Priority | Task | Effort |
|----------|------|--------|
| P1 | Update all page headings and terminology | 2 hours |
| P1 | Remove uppercase text transforms | 1 hour |
| P2 | Replace glows with subtle shadows | 2 hours |
| P2 | Add warm, friendly empty states | 1 hour |

---

## Summary

The SC2 MMR Tracker frontend has a solid technical foundation with excellent TypeScript practices and well-structured components. The main transformation required is aesthetic - shifting from the current "Military Tactical" visual language to a "Cozy LAN Party" feel.

**Key Findings:**
1. **Type Safety:** Excellent (only 4 minor issues to fix)
2. **Component Architecture:** Good (some memoization opportunities)
3. **State Management:** Good (React Query used effectively)
4. **Performance:** Acceptable (code splitting recommended)
5. **Styling:** Heavy tactical styling requiring systematic transformation

**Estimated Total Effort for Cozy Transformation:** 20-25 hours across 20 files

---

## 2.6 Responsive Design Review

> **Note:** This is primarily a **desktop application**. Mobile/tablet concerns are low priority.

### 2.6.1 Breakpoint Configuration

**Status: GOOD (but unused)**

Custom breakpoints defined in `theme/tokens.ts:289-296`:
```typescript
export const breakpoints = {
  xs: '320px',
  sm: '480px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;
```

**Note:** These are defined but NOT integrated into Chakra theme config - uses Chakra defaults.

### 2.6.2 Current Responsive Patterns

**54 instances** of Chakra responsive syntax found (good coverage for future mobile support):

| Component | Responsive Usage |
|-----------|------------------|
| `TeamSelector.tsx:133` | `columns={{ base: 2, md: 3, lg: 4, xl: 5 }}` |
| `Leaderboard.tsx` | Columns hidden on mobile via `display={{ base: 'none', md: 'table-cell' }}` |
| `Navigation.tsx:129,151,204` | Desktop/mobile nav switching with hamburger menu |
| `HeadToHead.tsx:386,457` | Grid adapts 1→3→4 columns |
| `Players.tsx:248` | Player cards grid responsive |

### 2.6.3 Desktop-Specific Considerations

| Concern | Status | Notes |
|---------|--------|-------|
| Wide screen layouts | ✅ Good | `container.xl` max-width prevents over-stretching |
| Mouse hover states | ✅ Good | All interactive elements have hover feedback |
| Keyboard shortcuts | ⚠️ Missing | No keyboard shortcuts for power users |
| Multi-monitor support | ✅ N/A | Standard web behavior |

### 2.6.4 Low Priority Mobile Issues

*These can be addressed if mobile support is needed later:*

| Issue | Location | Effort |
|-------|----------|--------|
| Touch targets < 44px | `Navigation.tsx:162`, `TeamSelector.tsx:111,120` | Low |
| Table horizontal scroll | `PlayerDetail.tsx:313-375` | Low |
| Fixed 80px column widths | `Leaderboard.tsx:147,209` | Low |

---

## 2.7 Accessibility Audit

> **Note:** Keyboard navigation and screen reader support remain important for desktop power users.

### 2.7.1 Overall Accessibility Score

| Category | Score | Notes |
|----------|-------|-------|
| WCAG Level A | **4/10** | Missing landmarks, keyboard support |
| WCAG Level AA | **5/10** | Decent color contrast, missing announcements |
| Keyboard Navigation | **3/10** | Critical gaps in interactive elements |

### 2.7.2 ARIA Attributes

**Status: PARTIAL**

| Attribute | Count | Assessment |
|-----------|-------|------------|
| `aria-label` | 14 | Present on key elements |
| `aria-labelledby` | 0 | Not used |
| `role` | 2 | Minimal usage |

### 2.7.3 Critical Keyboard Issues

These affect desktop power users who prefer keyboard navigation:

| Severity | Issue | Location | Fix |
|----------|-------|----------|-----|
| **Critical** | Logo clickable without keyboard | `Navigation.tsx:89` | Add `tabIndex`, `onKeyDown` |
| **Critical** | PlayerCard no keyboard support | `PlayerCard.tsx:108` | Add keyboard handlers |
| **Critical** | TacticalCard no keyboard support | `TacticalCard.tsx:49` | Add keyboard handlers |
| **Critical** | MatchCard no keyboard support | `MatchHistory.tsx:214-216` | Add keyboard handlers |
| **Critical** | RivalryCard no keyboard access | `HeadToHead.tsx:218-225` | Add keyboard handlers |
| **Major** | Clickable table rows no keyboard | `PlayerDetail.tsx:333` | Add keyboard handlers |
| **Major** | Leaderboard player links no keyboard | `Leaderboard.tsx:234-247` | Convert to Link or add handlers |

### 2.7.4 Semantic HTML Issues

| Issue | Location | Fix |
|-------|----------|-----|
| No `<main>` landmark | `App.tsx:34` | Wrap Routes in `<main>` |
| No `<nav>` element | `Navigation.tsx:76` | Add `as="nav"` to Box |
| No skip-to-content link | `App.tsx` | Add skip link |

### 2.7.5 Screen Reader Support

| Issue | Location | Impact |
|-------|----------|--------|
| No loading announcements | `LoadingState.tsx` | Users unaware of loading state |
| No live regions for updates | Team generation, pagination | Dynamic content not announced |
| Search inputs lack labels | `Players.tsx:190-204` | Screen readers can't identify purpose |

### 2.7.6 Quick Wins (High Impact, Low Effort)

| Fix | File | Effort | Impact |
|-----|------|--------|--------|
| Add `<main>` landmark | `App.tsx:34` | 5 min | High |
| Add `as="nav"` to navigation | `Navigation.tsx:76` | 2 min | High |
| Add skip-to-content link | `App.tsx` | 10 min | High |
| Add `aria-live="polite"` to LoadingState | `LoadingState.tsx` | 5 min | Medium |
| Add form labels (visually hidden) | `Players.tsx:186` | 5 min | Medium |

### 2.7.7 Reusable Keyboard Handler Pattern

Create a utility for consistent keyboard support across clickable elements:

```typescript
// utils/keyboard.ts
export const handleKeyboardClick = (
  onClick?: () => void
) => (e: React.KeyboardEvent) => {
  if (onClick && (e.key === 'Enter' || e.key === ' ')) {
    e.preventDefault();
    onClick();
  }
};

// Usage in components:
<Box
  onClick={onClick}
  tabIndex={onClick ? 0 : undefined}
  role={onClick ? "button" : undefined}
  onKeyDown={handleKeyboardClick(onClick)}
  cursor={onClick ? "pointer" : undefined}
>
```

Apply to: `PlayerCard`, `TacticalCard`, `MatchCard`, `RivalryCard`, clickable table rows.

---

## Updated Priority Recommendations

### Immediate Fixes (Desktop UX)

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| P0 | Fix 4 `any` type usages | 30 min | Code quality |
| P0 | Add keyboard support to interactive cards | 2 hours | Accessibility |
| P0 | Add semantic landmarks (`<main>`, `<nav>`) | 15 min | Accessibility |
| P1 | Add `React.memo` to list components | 1 hour | Performance |
| P1 | Implement route-based code splitting | 2 hours | Performance |

### Cozy Redesign Phases (unchanged)

*See sections above*

---

## Summary

The SC2 MMR Tracker frontend has a solid technical foundation with excellent TypeScript practices and well-structured components. The main transformation required is aesthetic - shifting from the current "Military Tactical" visual language to a "Cozy LAN Party" feel.

**Key Findings:**
1. **Type Safety:** Excellent (only 4 minor issues to fix)
2. **Component Architecture:** Good (some memoization opportunities)
3. **State Management:** Good (React Query used effectively)
4. **Performance:** Acceptable (code splitting recommended)
5. **Styling:** Heavy tactical styling requiring systematic transformation
6. **Responsive Design:** Good foundation (low priority for desktop-first app)
7. **Accessibility:** Needs work on keyboard navigation and landmarks

**Estimated Total Effort for Cozy Transformation:** 20-25 hours across 20 files
**Accessibility Quick Wins:** 2-3 hours for critical keyboard/landmark fixes

---

**Document Version:** 1.1
**Status:** Complete
**Next Phase:** Phase 3 (Integration & Data Flow Review)
