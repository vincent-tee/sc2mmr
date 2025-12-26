# SC2 MMR Tracker - Design Concept V2
## "Friend Squad" Edition - Warm, Personable, Comic-Book Inspired

**Created**: 2025-12-09
**Philosophy**: This isn't an esports tool - it's a celebration of friends playing together.

---

## 1. Design Pillars

### 1.1 Warm Over Cold
- **OUT**: Neon cyan, tactical military, cold space black
- **IN**: Sunset oranges, warm blues, cozy dark backgrounds
- **Feel**: Like a favorite gaming cafe, not a sterile command center

### 1.2 Comic-Book Personality
- **OUT**: Flat minimalism, corporate smoothness
- **IN**: Bold outlines, halftone textures, dynamic panels
- **Feel**: Like a graphic novel about your friend group's gaming adventures

### 1.3 Friend-Group First
- **OUT**: Anonymous player IDs, generic stats
- **IN**: Nicknames, avatars, rivalries, inside jokes
- **Feel**: Like your group's private clubhouse

### 1.4 Playful SC2 Integration
- **OUT**: Serious military aesthetic
- **IN**: Fun race mascots, playful unit references
- **Feel**: SC2 fan art, not SC2 HUD clone

---

## 2. Color Palette

### 2.1 Primary Colors

```
┌─────────────────────────────────────────────────────────┐
│  WARM SUNSET PRIMARY                                     │
├─────────────────────────────────────────────────────────┤
│  primary.500    #FF6B35   Sunset Orange (Main CTA)      │
│  primary.400    #FF8C5A   Light Orange (Hover)          │
│  primary.600    #E85A2A   Deep Orange (Active)          │
│  primary.100    #FFE4D6   Cream (Subtle backgrounds)    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  FRIENDLY BLUE SECONDARY                                 │
├─────────────────────────────────────────────────────────┤
│  secondary.500  #4ECDC4   Teal (Accents)                │
│  secondary.400  #7EDCD6   Light Teal (Hover)            │
│  secondary.600  #3DBDB4   Deep Teal (Active)            │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Race Colors (Warmer Versions)

```
┌─────────────────────────────────────────────────────────┐
│  SC2 RACE PALETTE (COMIC-BOOK WARM)                     │
├─────────────────────────────────────────────────────────┤
│  Terran         #5B9BD5   Friendly Blue (not harsh)     │
│  Terran.light   #89B8E5   Highlight                     │
│  Terran.dark    #3A7BBD   Shadow                        │
│                                                          │
│  Protoss        #FFD93D   Warm Gold (not cold yellow)   │
│  Protoss.light  #FFE566   Highlight                     │
│  Protoss.dark   #E5C235   Shadow                        │
│                                                          │
│  Zerg           #C77DFF   Soft Purple (not harsh)       │
│  Zerg.light     #D9A3FF   Highlight                     │
│  Zerg.dark      #A855F7   Shadow                        │
│                                                          │
│  Random         #94A3B8   Warm Gray                     │
└─────────────────────────────────────────────────────────┘
```

### 2.3 Background Colors

```
┌─────────────────────────────────────────────────────────┐
│  COZY DARK BACKGROUNDS                                   │
├─────────────────────────────────────────────────────────┤
│  bg.deep        #1A1625   Warm Dark (not cold black)    │
│  bg.card        #252136   Card Background               │
│  bg.elevated    #2F2A40   Elevated Surface              │
│  bg.overlay     #1A1625E6 Modal Overlay (90%)           │
└─────────────────────────────────────────────────────────┘
```

### 2.4 Status Colors

```
┌─────────────────────────────────────────────────────────┐
│  FUN STATUS COLORS                                       │
├─────────────────────────────────────────────────────────┤
│  win            #4ADE80   Victory Green                 │
│  loss           #F87171   Defeat Red (not harsh)        │
│  streak.hot     #FF6B35   On Fire!                      │
│  streak.cold    #60A5FA   Ice Cold                      │
│  rivalry        #F472B6   Rivalry Pink                  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Typography

### 3.1 Font Stack

```css
/* Comic-Book Headings - Bold, Fun, Chunky */
--font-heading: 'Bangers', 'Comic Neue', cursive;

/* Alternative: More readable but still fun */
--font-heading-alt: 'Fredoka One', 'Nunito', sans-serif;

/* Body Text - Friendly, Readable */
--font-body: 'Nunito', 'Quicksand', sans-serif;

/* Accent Text - For "POW!" effects */
--font-accent: 'Bangers', 'Impact', sans-serif;

/* Monospace - Stats and numbers */
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

### 3.2 Type Scale

```
Hero Title:     4rem / 64px   (Player names on detail page)
Page Title:     2.5rem / 40px (Page headings)
Section Title:  1.75rem / 28px (Card headers)
Card Title:     1.25rem / 20px (Player names in cards)
Body Large:     1.125rem / 18px (Important text)
Body:           1rem / 16px (Default)
Caption:        0.875rem / 14px (Secondary info)
Micro:          0.75rem / 12px (Timestamps, labels)
```

### 3.3 Comic Effects Text

```css
/* "POW!" style text for achievements/kills */
.comic-effect {
  font-family: var(--font-accent);
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow:
    3px 3px 0 #000,
    -1px -1px 0 #000,
    1px -1px 0 #000,
    -1px 1px 0 #000;
  transform: rotate(-5deg);
}
```

---

## 4. Component Concepts

### 4.1 PlayerCard - "Hero Card" Style

```
┌──────────────────────────────────────┐
│ ╔══════════════════════════════════╗ │  <- Bold black border (3px)
│ ║  ┌────────┐                      ║ │
│ ║  │ AVATAR │  "DESTROYER_9000"    ║ │  <- Fun nickname, big
│ ║  │  😎    │   aka "Dave"         ║ │  <- Real name small
│ ║  └────────┘                      ║ │
│ ║                                  ║ │
│ ║  ⚔️ MMR: 2,150                   ║ │  <- Chunky numbers
│ ║  🏆 Win Streak: 5 🔥             ║ │  <- Emoji indicators
│ ║  👑 "Zerg Crusher"               ║ │  <- Fun title
│ ║                                  ║ │
│ ║  [Terran Icon]  65% WR          ║ │  <- Race shown playfully
│ ╚══════════════════════════════════╝ │
│    ░░░ Halftone shadow effect ░░░    │  <- Comic-book shadow
└──────────────────────────────────────┘
```

**Key Elements**:
- Bold black border (not glowing)
- Halftone dot pattern for shadows
- Avatar with fun expressions
- Emoji use encouraged
- "Fun titles" based on achievements

### 4.2 MatchCard - "Comic Panel" Style

```
┌─────────────────────────────────────────────────────────┐
│ ┌─────────────────┐  VS  ┌─────────────────┐            │
│ │   TEAM ALPHA    │ ⚡️  │   TEAM OMEGA    │            │
│ │  Dave, Sarah    │      │  Mike, Lisa     │            │
│ │   [Avatars]     │      │   [Avatars]     │            │
│ └─────────────────┘      └─────────────────┘            │
│                                                          │
│  ╔═══════════════════════════════════════════════════╗  │
│  ║                  "BOOM!"                          ║  │
│  ║        Team Alpha WINS in 18:32                   ║  │
│  ╚═══════════════════════════════════════════════════╝  │
│                                                          │
│  🌟 HERO MOMENT: Dave's Battlecruiser Rush!             │
│  📊 Map: Romanticide  |  Mode: 2v2                       │
└─────────────────────────────────────────────────────────┘
```

**Key Elements**:
- Panel layout like comic strip
- "BOOM!", "POW!", "CLUTCH!" callouts
- Hero moment highlights
- Team avatars grouped together

### 4.3 Rivalry Banner

```
┌─────────────────────────────────────────────────────────┐
│  🔥 RIVALRY ALERT! 🔥                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│    [Dave Avatar]  ⚔️ vs ⚔️  [Sarah Avatar]              │
│                                                          │
│    Dave: 7 wins    ◄━━━━━━━━━►    Sarah: 5 wins         │
│                                                          │
│    "Dave is ON FIRE against Sarah this month!"          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 4.4 Team Generator - "Assemble Your Squad!"

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│    ★ ═══ ASSEMBLE YOUR SQUAD! ═══ ★                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  WHO'S PLAYING TODAY?                              │ │
│  │                                                    │ │
│  │  [✓] Dave 😎   [✓] Sarah 🎮   [ ] Mike 🎯        │ │
│  │  [✓] Lisa 🏆   [ ] Tom 🎪    [✓] Alex ⚡️         │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│         ╔═══════════════════════════════╗               │
│         ║   🎲 GENERATE TEAMS! 🎲      ║               │
│         ╚═══════════════════════════════╝               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 4.5 Leaderboard - "Hall of Fame" Style

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│    ═══════ 🏆 HALL OF FAME 🏆 ═══════                   │
│                                                          │
│    #1  👑 Dave "The Destroyer"     2,350 MMR           │
│        └─ 🔥 5 game streak! "Unstoppable!"             │
│                                                          │
│    #2  ⚔️ Sarah "Zerg Queen"       2,280 MMR           │
│        └─ 📈 Most improved this month                   │
│                                                          │
│    #3  🎯 Mike "Sniper"            2,150 MMR           │
│        └─ 🎪 Best late-game player                      │
│                                                          │
│    #4  🌟 Lisa "Rookie Star"       1,980 MMR           │
│        └─ 🆕 Newcomer of the month                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Animation Guidelines

### 5.1 Principles

- **Bouncy over smooth**: Use spring/elastic easing
- **Playful over corporate**: Overshoot, squash & stretch
- **Celebratory**: Confetti, explosions for wins
- **Quick**: Nothing should feel slow or laggy

### 5.2 Key Animations

```css
/* Bouncy entrance */
@keyframes bounceIn {
  0% { transform: scale(0); }
  50% { transform: scale(1.1); }
  70% { transform: scale(0.95); }
  100% { transform: scale(1); }
}

/* Win celebration */
@keyframes celebrate {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-5deg) scale(1.1); }
  75% { transform: rotate(5deg) scale(1.1); }
}

/* Comic "POW!" appearance */
@keyframes comicPop {
  0% { transform: scale(0) rotate(-20deg); opacity: 0; }
  60% { transform: scale(1.3) rotate(5deg); opacity: 1; }
  100% { transform: scale(1) rotate(-3deg); opacity: 1; }
}

/* Hot streak fire effect */
@keyframes fireGlow {
  0%, 100% {
    box-shadow: 0 0 5px #FF6B35, 0 0 10px #FF8C5A;
  }
  50% {
    box-shadow: 0 0 15px #FF6B35, 0 0 25px #FF8C5A;
  }
}
```

### 5.3 Transitions

```css
/* Standard transition - bouncy */
transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);

/* Hover lift */
&:hover {
  transform: translateY(-4px) rotate(1deg);
  box-shadow: 6px 6px 0 rgba(0,0,0,0.3);
}
```

---

## 6. Friend-Group Features

### 6.1 Player Profiles

**Avatar System**:
- Upload custom photo
- OR choose from fun preset avatars
- Animated reactions (win face, loss face, thinking)

**Nickname System**:
- Display name (fun/silly)
- Real name (optional)
- Current title (earned through play)

**Titles** (Auto-assigned):
- "The Destroyer" - Most kills
- "Comeback King" - Most comeback wins
- "Zerg Crusher" - Best vs Zerg
- "Early Bird" - Best early game
- "Macro Master" - Best economy
- "Pizza Break Champion" - Longest AFK time 😄

### 6.2 Rivalry System

- Auto-detect most frequent matchups
- Track head-to-head records
- "Rivalry of the Week" highlight
- Trash talk prompts (optional, fun)

### 6.3 Achievement Badges

```
🏆 First Blood      - First kill in a match
🔥 On Fire          - 5+ game win streak
❄️ Ice Cold         - 5+ game loss streak (friendly roast)
👑 Weekly Champion  - Highest MMR gain in week
🎯 Sniper           - Best damage efficiency
🏗️ Macro God        - Best economy score
⚔️ Micro Legend     - Best combat score
🤝 Team Player      - Best team fight participation
🆕 Rising Star      - New player doing well
🎪 Clutch Master    - Most comeback wins
```

### 6.4 Group Stats Page

- "Our Group" summary
- Total games played together
- Most epic matches
- Funniest moments (manual highlights?)
- Group photo / banner upload
- Discord/social integration

---

## 7. SC2 Integration (Fun, Not Serious)

### 7.1 Race Mascots

Instead of serious race icons, use playful versions:
- **Terran**: Chunky Marine with oversized helmet
- **Protoss**: Smug Zealot with sparkles
- **Zerg**: Derpy Zergling with big eyes
- **Random**: Dice with question mark

### 7.2 Unit References

Fun callouts based on play style:
- "Battlecruiser Operational!" - When someone turtles
- "We require more minerals!" - Economy player
- "NUCLEAR LAUNCH DETECTED" - Cheese player

### 7.3 Map Illustrations

- Stylized, colorful map thumbnails
- Cartoon style, not realistic
- Highlight key areas humorously

---

## 8. Visual Effects

### 8.1 Comic-Book Borders

```css
.comic-border {
  border: 3px solid #1A1625;
  border-radius: 8px;
  box-shadow:
    4px 4px 0 #1A1625,        /* Hard shadow */
    6px 6px 0 rgba(0,0,0,0.1); /* Soft shadow */
}
```

### 8.2 Halftone Pattern

```css
.halftone-bg {
  background-image: radial-gradient(#1A1625 1px, transparent 1px);
  background-size: 4px 4px;
  opacity: 0.1;
}
```

### 8.3 Action Lines

```css
.action-lines {
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 10px,
    rgba(255,107,53,0.1) 10px,
    rgba(255,107,53,0.1) 20px
  );
}
```

---

## 9. Implementation Priority

### Phase 1: Core Warmth
1. Replace color palette (tokens.ts)
2. Update typography (add Nunito, Bangers)
3. Update card borders to comic style
4. Remove all neon glows

### Phase 2: Personality
1. Avatar system
2. Nickname display
3. Fun titles
4. Rivalry detection

### Phase 3: Polish
1. Animations (bouncy transitions)
2. Comic effects ("POW!" callouts)
3. Achievement badges
4. Group features

---

## 10. Before/After Vision

### BEFORE (Current):
- Cold tactical cyan everywhere
- Generic "military command center"
- Anonymous player stats
- Serious esports aesthetic
- Could be any space game

### AFTER (V2):
- Warm sunset oranges and friendly teals
- Comic-book panels and bold borders
- Dave, Sarah, Mike with avatars and nicknames
- Fun rivalries and achievements
- Unmistakably YOUR friend group's app

---

**This design celebrates friendship through gaming, not just tracks stats.**
