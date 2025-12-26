# Phase 4.3: MCP Integration Guide

## SC2 MMR Tracker - UI Review Workflow

**Review Date:** December 26, 2025  
**Reviewer:** Mr.Alfred (MoAI-ADK)  
**Status:** Complete

---

## Executive Summary

This guide details how to leverage MCP (Model Context Protocol) servers for UI review and validation during the Cozy LAN Party transformation. The setup enables AI-assisted visual review, automated screenshot capture, and design validation.

---

## Current MCP Configuration

**Location:** `/home/vtee/projects/sc2mmr/.mcp.json`

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "figma-dev-mode-mcp-server": {
      "type": "sse",
      "url": "http://127.0.0.1:3845/sse"
    }
  }
}
```

### Existing Servers

| Server | Purpose | Status |
|--------|---------|--------|
| **context7** | Documentation/context retrieval | ✅ Active |
| **playwright** | Browser automation & screenshots | ✅ Active |
| **figma-dev-mode** | Figma design sync | ⚠️ Requires local server |

---

## Recommended Additional MCP Servers

### 1. Frontend Review MCP

**Purpose:** Compare before/after screenshots, validate UI changes

```json
{
  "mcpServers": {
    "frontend-review": {
      "command": "npx",
      "args": ["-y", "@anthropic/frontend-review-mcp@latest"]
    }
  }
}
```

**Capabilities:**
- Screenshot comparison
- Visual diff generation
- Accessibility checks
- Color contrast validation

### 2. Desktop Screenshot Server

**Purpose:** Capture desktop/browser screenshots on demand

```json
{
  "mcpServers": {
    "screenshot": {
      "command": "npx",
      "args": ["-y", "@anthropic/screenshot-mcp@latest"]
    }
  }
}
```

**Capabilities:**
- Full screen capture
- Window-specific capture
- Region selection
- Multi-monitor support

### 3. Design Token Validator

**Purpose:** Validate design token usage across codebase

```json
{
  "mcpServers": {
    "design-tokens": {
      "command": "npx", 
      "args": ["-y", "@anthropic/design-tokens-mcp@latest"]
    }
  }
}
```

**Capabilities:**
- Token usage audit
- Hardcoded value detection
- Token coverage report

---

## Updated MCP Configuration

**Recommended `.mcp.json`:**

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "figma-dev-mode-mcp-server": {
      "type": "sse",
      "url": "http://127.0.0.1:3845/sse"
    }
  }
}
```

---

## UI Review Workflow

### Workflow 1: Before/After Comparison

**Use Case:** Validate Cozy UI changes against tactical baseline

```
┌─────────────────────────────────────────────────────────────┐
│                   BEFORE/AFTER WORKFLOW                      │
└─────────────────────────────────────────────────────────────┘

1. CAPTURE BASELINE (Before changes)
   │
   ├── Start dev server: npm run dev
   │
   ├── Use Playwright MCP to screenshot key pages:
   │   • Home page
   │   • Team Generator
   │   • Player Detail
   │   • Match History
   │
   └── Save to: .moai/reviews/screenshots/baseline/

2. MAKE CHANGES
   │
   ├── Update theme tokens
   ├── Transform components
   └── Update pages

3. CAPTURE UPDATED (After changes)
   │
   ├── Use Playwright MCP to screenshot same pages
   │
   └── Save to: .moai/reviews/screenshots/updated/

4. COMPARE & VALIDATE
   │
   ├── Request AI comparison of screenshots
   │
   └── Validate against Cozy UI criteria:
       • No neon glows
       • Rounded corners
       • Warm color palette
       • Friendly typography
```

### Workflow 2: Component Review

**Use Case:** Validate individual component transformations

```
┌─────────────────────────────────────────────────────────────┐
│                   COMPONENT REVIEW WORKFLOW                  │
└─────────────────────────────────────────────────────────────┘

1. ISOLATE COMPONENT
   │
   └── Create Storybook story or isolated test page

2. CAPTURE STATES
   │
   ├── Default state
   ├── Hover state
   ├── Selected state
   ├── Disabled state
   └── Loading state

3. VALIDATE EACH STATE
   │
   ├── Check border radius
   ├── Check color palette
   ├── Check typography
   ├── Check shadows
   └── Check animations

4. DOCUMENT FINDINGS
   │
   └── Add to component migration checklist
```

### Workflow 3: Accessibility Validation

**Use Case:** Ensure accessibility during transformation

```
┌─────────────────────────────────────────────────────────────┐
│                   ACCESSIBILITY WORKFLOW                     │
└─────────────────────────────────────────────────────────────┘

1. AUTOMATED CHECKS
   │
   ├── Run axe-core via Playwright
   │
   └── Capture accessibility report

2. MANUAL CHECKS
   │
   ├── Keyboard navigation test
   ├── Screen reader test
   └── Color contrast verification

3. FIX & VERIFY
   │
   ├── Address findings
   │
   └── Re-run checks to confirm fixes
```

---

## Playwright MCP Usage

### Available Commands

The Playwright MCP server provides these capabilities:

#### 1. Navigate to Page
```
Navigate to: http://localhost:5173/
```

#### 2. Take Screenshot
```
Take a screenshot of the current page
```

#### 3. Click Element
```
Click on the element with selector: [data-testid="generate-teams"]
```

#### 4. Fill Input
```
Fill the input [name="search"] with "Player1"
```

#### 5. Wait for Element
```
Wait for element [data-testid="team-results"] to be visible
```

### Screenshot Workflow Example

**Step 1: Start the development server**
```bash
cd frontend && npm run dev
```

**Step 2: Request screenshots via Claude**
```
Please use Playwright to:
1. Navigate to http://localhost:5173
2. Take a screenshot of the home page
3. Navigate to http://localhost:5173/balance
4. Take a screenshot of the team generator page
```

**Step 3: Review and provide feedback**
```
Looking at these screenshots, I notice:
- The cards still have angular corners (should be rounded)
- The font appears to be Rajdhani (should be Poppins)
- There are cyan glow effects (should be soft shadows)

Please update the theme to address these issues.
```

---

## Figma Integration

### Setup Requirements

1. **Install Figma Desktop App**
2. **Install Figma Dev Mode Plugin**
3. **Start local server** (port 3845)

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                   FIGMA DESIGN SYNC WORKFLOW                 │
└─────────────────────────────────────────────────────────────┘

1. DESIGN IN FIGMA
   │
   ├── Create Cozy UI component designs
   ├── Define color tokens
   └── Export design specs

2. SYNC VIA MCP
   │
   ├── Connect to Figma file
   ├── Extract design tokens
   └── Generate CSS variables

3. IMPLEMENT
   │
   ├── Apply extracted tokens
   └── Match Figma designs

4. VALIDATE
   │
   ├── Compare implementation to Figma
   └── Iterate until matched
```

### Design Token Export

If using Figma for the Cozy UI design system:

```typescript
// Generated from Figma via MCP
export const figmaTokens = {
  colors: {
    primary: {
      50: '#FFF8F0',
      500: '#F97316',
      900: '#7C2D12',
    },
    surface: {
      50: '#FEFDFB',
      100: '#FDF8F3',
      // ...
    },
  },
  radii: {
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
  },
  shadows: {
    card: '0 4px 12px rgba(0, 0, 0, 0.08)',
    cardHover: '0 8px 24px rgba(0, 0, 0, 0.12)',
  },
};
```

---

## Review Checklist Templates

### Pre-Transformation Checklist

Before starting Cozy UI changes:

- [ ] Baseline screenshots captured for all pages
- [ ] Current theme tokens documented
- [ ] Component inventory complete
- [ ] Test coverage adequate for refactoring

### Component Transformation Checklist

For each component being transformed:

- [ ] Remove clip-path/polygon shapes
- [ ] Replace angular corners with borderRadius
- [ ] Remove neon glow shadows
- [ ] Add soft depth shadows
- [ ] Update color references to cozy palette
- [ ] Remove uppercase text transforms
- [ ] Update font family references
- [ ] Verify hover/active states
- [ ] Check keyboard accessibility
- [ ] Screenshot comparison approved

### Page Transformation Checklist

For each page being updated:

- [ ] Update page title/heading
- [ ] Replace military terminology
- [ ] Update component usage
- [ ] Verify layout consistency
- [ ] Check responsive behavior
- [ ] Screenshot comparison approved
- [ ] User flow tested

### Final Validation Checklist

Before completing transformation:

- [ ] All pages screenshot compared
- [ ] No cyan/neon colors visible
- [ ] All corners rounded
- [ ] Poppins/Inter fonts in use
- [ ] Soft shadows throughout
- [ ] Friendly terminology used
- [ ] Accessibility audit passed
- [ ] Performance benchmarks met
- [ ] User feedback positive

---

## Troubleshooting

### Playwright MCP Issues

**Problem:** Browser doesn't launch
```
Solution: Ensure Playwright browsers are installed
npx playwright install chromium
```

**Problem:** Screenshots are blank
```
Solution: Wait for page to fully load
Add: await page.waitForLoadState('networkidle')
```

**Problem:** Element not found
```
Solution: Use more specific selectors or wait for element
Add: await page.waitForSelector('[data-testid="..."]')
```

### Figma MCP Issues

**Problem:** Connection refused on port 3845
```
Solution: Start Figma Dev Mode server
1. Open Figma Desktop
2. Enable Dev Mode
3. Start the local server from plugin
```

**Problem:** Design tokens not syncing
```
Solution: Ensure Figma file has proper token naming
Use format: colors/primary/500, spacing/md, etc.
```

---

## Best Practices

### 1. Iterative Review

Don't wait until the end to review. Capture screenshots after each significant change:

```
Change → Screenshot → Review → Iterate
```

### 2. Consistent Viewport

Always use the same viewport size for comparisons:

```typescript
// Recommended viewport for screenshots
const viewport = {
  width: 1440,
  height: 900,
};
```

### 3. State Documentation

Capture all interactive states:

- Default
- Hover
- Focus
- Active
- Disabled
- Loading
- Error
- Empty

### 4. Naming Convention

Use consistent naming for screenshots:

```
.moai/reviews/screenshots/
├── baseline/
│   ├── home-default.png
│   ├── home-loading.png
│   ├── teamgen-default.png
│   └── teamgen-with-players.png
├── updated/
│   ├── home-default.png
│   └── ...
└── diffs/
    ├── home-default-diff.png
    └── ...
```

### 5. Review Sessions

Schedule dedicated review sessions:

- **Daily:** Quick visual check of changes
- **Weekly:** Full page comparison
- **Per-milestone:** Comprehensive accessibility audit

---

## Integration with CI/CD

### Visual Regression Testing

Add Playwright visual tests to CI:

```yaml
# .github/workflows/visual-tests.yml
name: Visual Regression Tests

on:
  pull_request:
    paths:
      - 'frontend/src/**'

jobs:
  visual-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: cd frontend && npm ci
      
      - name: Install Playwright
        run: npx playwright install chromium
      
      - name: Start dev server
        run: cd frontend && npm run dev &
      
      - name: Run visual tests
        run: npx playwright test --project=visual
      
      - name: Upload screenshots
        uses: actions/upload-artifact@v4
        with:
          name: screenshots
          path: frontend/test-results/
```

### Screenshot Artifacts

Store screenshots as PR artifacts for review:

```yaml
- name: Comment PR with screenshots
  uses: actions/github-script@v7
  with:
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: '## Visual Changes\n\nScreenshots attached as artifacts.'
      })
```

---

## Summary

The MCP integration enables:

1. **Playwright MCP** - Automated browser screenshots and interactions
2. **Figma MCP** - Design token sync and specification extraction
3. **Context7 MCP** - Documentation and context retrieval

**Workflow:**
1. Capture baseline screenshots before changes
2. Make incremental Cozy UI changes
3. Capture updated screenshots
4. Request AI comparison and feedback
5. Iterate until validation passes

**Key Benefits:**
- Visual validation at each step
- Consistent review process
- Documentation of changes
- Automated regression detection

---

**Document Version:** 1.0  
**Status:** Complete  
**Related:** `04-cozy-ui-roadmap.md`, `05-priority-matrix.md`
