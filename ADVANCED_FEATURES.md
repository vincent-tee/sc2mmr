# SC2 MMR Tracker - Advanced Features

## Overview

Beyond basic win/loss tracking, the system extracts detailed SC2-specific metrics to provide deep insights into player performance, roles, and synergies.

## 📊 Advanced Metrics Tracked

### Economic Performance
- **Resources Collected**: Total minerals and vespene gas gathered
- **Workers Created**: Number of SCVs/Probes/Drones built
- **Spending Efficiency**: How effectively resources were spent (%)
- **Bases Created**: Number of expansions taken
- **First Expansion Timing**: When 2nd base was built (game seconds)

### Combat Performance
- **Damage Dealt**: Total damage to enemy units
- **Damage Taken**: Total damage received
- **Damage Ratio**: Dealt/Taken (higher is better)
- **Units Killed**: Count of enemy units destroyed
- **Units Lost**: Count of own units lost
- **Army Value Killed**: Resource value of enemy units destroyed
- **Army Value Lost**: Resource value of units lost

### Army Composition
- **Units Trained**: Total units built
- **Army Value Built**: Total resources spent on military
- **Unit Composition**: Top 5 units by count (e.g., Marine: 50, Marauder: 20)

### Mechanics
- **APM**: Actions per minute
- **Build Order Timings**: When key structures/units appear
- **Tech Progression**: Upgrade and building completion times

## 🎯 Impact Scoring System

Each player receives scores (0-100) across multiple dimensions:

### 1. Economic Score
Measures resource generation and management:
- Resources collected (normalized)
- Worker production
- Spending efficiency

**Formula**: `(resource_score + worker_score + spending_score) / 3`

### 2. Combat Score
Measures fighting effectiveness:
- Damage dealt (normalized)
- Army value killed
- Kill/death ratio

**Formula**: `(damage_score + kill_score + ratio_score) / 3`

### 3. Efficiency Score
Measures overall performance:
- Spending efficiency
- Damage ratio
- Unit trade efficiency

**Formula**: `(spending + damage_ratio + trade_ratio) / 3`

### 4. Overall Impact
Weighted average emphasizing combat:
```
Overall = Economic * 0.3 + Combat * 0.5 + Efficiency * 0.2
```

**Why this weighting?**
- Combat (50%): Team games are won through fights
- Economic (30%): Economy enables army
- Efficiency (20%): Doing more with less

## 🤝 Synergy Detection

The system automatically detects which players work well together by analyzing:

### 1. Win Rate Together
Most important factor (60% weight):
- How often they win when teamed up
- Sample size matters (min 3-5 games)

### 2. Role Complementarity (20% weight)
Players with different strengths synergize better:
- One player focuses on economy → other on combat
- Balanced teams: Economic + Combat players
- Measured by difference in Economic vs Combat scores

Example:
```
Player A: Economic 80, Combat 50 (Economy specialist)
Player B: Economic 50, Combat 85 (Fighter)
→ High complementarity = Good synergy!
```

### 3. Performance Consistency (20% weight)
Teams that perform consistently together:
- Lower variance in combined impact
- Stable coordination across games

### Synergy Score
Final score (0-100):
```
Synergy = WinRate * 0.6 + Complementarity * 0.2 + Consistency * 0.2
```

**Interpretation**:
- 80-100: Excellent synergy (keep together!)
- 65-80: Good synergy
- 50-65: Neutral
- 35-50: Poor synergy
- 0-35: Bad synergy (avoid pairing)

## 🎮 API Endpoints

### Impact Statistics

#### Get Players by Impact
```bash
GET /impact/players?sort_by=combat&min_games=5
```

Sort options:
- `economic` - Best economic players
- `combat` - Best fighters
- `efficiency` - Most efficient players
- `overall` - Overall impact

Response:
```json
[
  {
    "id": 1,
    "name": "Player1",
    "mmr": 18.45,
    "avg_impact": {
      "economic_score": 75.2,
      "combat_score": 82.5,
      "efficiency_score": 71.3,
      "overall_impact": 77.8
    },
    "total_games": 25,
    "win_rate": 68.0
  }
]
```

#### Get Player Match Details
```bash
GET /impact/players/{player_id}/matches?limit=20
```

Returns detailed metrics for recent matches:
```json
[
  {
    "match_id": 123,
    "player_name": "Player1",
    "race": "Terran",
    "won": true,
    "minerals_collected": 45000,
    "vespene_collected": 18000,
    "total_resources": 63000,
    "workers_created": 65,
    "units_killed": 42,
    "units_lost": 18,
    "damage_dealt": 28500,
    "damage_taken": 12000,
    "damage_ratio": 2.375,
    "economic_score": 78.5,
    "combat_score": 85.2,
    "efficiency_score": 80.1,
    "overall_impact": 82.3,
    "apm": 145.5,
    "first_expansion_timing": 185
  }
]
```

#### Get Player Synergies
```bash
GET /impact/players/{player_id}/synergies?min_games=3
```

Returns synergies with other players:
```json
{
  "player_id": 1,
  "player_name": "Player1",
  "synergies": [
    {
      "player1_id": 1,
      "player1_name": "Player1",
      "player2_id": 3,
      "player2_name": "Player3",
      "games_together": 15,
      "wins_together": 12,
      "win_rate": 80.0,
      "synergy_score": 78.5,
      "avg_combined_impact": 155.2
    }
  ]
}
```

#### Get Top Synergies
```bash
GET /impact/synergies/top?min_games=5&limit=10
```

Returns best synergies across all players.

#### Impact Leaderboards
```bash
GET /impact/leaderboard/{category}?min_games=5&limit=10
```

Categories:
- `economic` - Top resource collectors
- `combat` - Top damage dealers
- `efficiency` - Most efficient players
- `overall` - Overall impact leaders

### Upload with Advanced Metrics

```bash
POST /replays/upload-advanced
```

Upload replay files to extract advanced metrics automatically. This is the recommended endpoint for all new uploads.

## 📈 Use Cases

### 1. Find Your Fighters
```bash
GET /impact/leaderboard/combat?min_games=10
```

Identify who deals the most damage and gets the kills.

### 2. Find Your Economy Players
```bash
GET /impact/leaderboard/economic?min_games=10
```

Identify who best manages resources and expansions.

### 3. Discover Best Duos
```bash
GET /impact/synergies/top?min_games=10
```

Find player pairs with highest synergy for tournaments or important matches.

### 4. Analyze Your Own Performance
```bash
GET /impact/players/{your_id}/matches?limit=50
```

Track your economic vs combat tendencies, identify improvement areas.

### 5. Build Balanced Teams
When using team balancer, consider:
- Mix high economic + high combat players
- Pair players with proven synergy
- Balance roles across both teams

## 🔬 Analysis Examples

### Example: Fighter vs Economy Player

**Player A (Fighter)**:
```json
{
  "economic_score": 62.0,
  "combat_score": 88.5,
  "efficiency_score": 75.0,
  "overall_impact": 77.3
}
```

**Player B (Economy)**:
```json
{
  "economic_score": 85.0,
  "combat_score": 65.0,
  "efficiency_score": 72.0,
  "overall_impact": 74.1
}
```

These players have **complementary roles** and likely synergize well together!

### Example: Good vs Bad Synergy

**Good Synergy (Score: 82.5)**:
- Games together: 20
- Win rate: 75%
- Role complementarity: High
- Consistent performance: High

**Bad Synergy (Score: 38.2)**:
- Games together: 15
- Win rate: 40%
- Role complementarity: Low (both fight for same role)
- Inconsistent performance

## 🎯 Future Enhancements

Metrics that can be added (sc2reader supports):

1. **First Attack Timing** - When first enemy unit dies
2. **Peak Army Supply** - Maximum army size reached
3. **Upgrade Timings** - When specific upgrades complete (stim, +1 armor, etc.)
4. **Average Unspent Resources** - How much "bank" is kept
5. **Time Supply Blocked** - Time spent supply blocked
6. **Objective Damage** - Damage specifically to structures
7. **Control Group Usage** - Number of control groups actively used
8. **Camera Hotkeys** - Map awareness metric

Want any of these added? They're just an sc2reader event parser away!

## 💡 Tips for Using Advanced Metrics

### Team Balancing
1. **Don't just balance MMR** - Consider roles
2. **Leverage synergies** - Keep proven duos together when possible
3. **Mix styles** - One economy + one fighter per team works well

### Player Development
1. **Track your trends** - Are you improving economically or in combat?
2. **Identify weaknesses** - Low economic score? Expand more!
3. **Learn from top players** - Compare your metrics to highest impact players

### Competitive Play
1. **Scout roles** - Know who the enemy damage dealers are
2. **Target high impact** - Focus fire on their combat players
3. **Leverage matchups** - Use synergy data for roster decisions

## 🔐 Data Privacy

All metrics are calculated from replay files only. No screen recording, no external data. Just pure SC2 game data!

## 📊 Batch Processing with Advanced Metrics

Want to process your entire replay history with advanced metrics?

The batch processor has been updated to support advanced parsing:

```bash
cd backend
python batch_process_replays.py /path/to/replays --advanced --show-predictions
```

This will:
1. Extract all advanced metrics
2. Calculate impact scores
3. Update player averages
4. Build synergy database
5. Show predictions improving over time

## 🚀 Next Steps

1. Upload replays using `/replays/upload-advanced`
2. View impact leaderboards
3. Check player synergies
4. Use insights for better team balancing!

---

**Questions or want additional metrics? Let me know!**
