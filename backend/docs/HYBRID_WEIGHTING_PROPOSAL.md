# Hybrid Weighting System Proposal

## Problem Statement

Current recency weighting (90-day half-life) doesn't adequately reward:
- Players on recent hot streaks (e.g., DragonKing: 66.7% WR in 30d vs 35.7% overall)
- High-volume players with consistent performance
- Strong in-game performance metrics (combat, economic impact)

## Proposed Solution: Multi-Factor Weighting

### 1. Time-Based Recency (Current System)
```python
time_weight = 0.5^(days_ago / half_life_days)
```
- Current: 90-day half-life
- Proposal: Make configurable per use case

### 2. Game-Volume Weighting (NEW)
```python
# Weight recent games more, but also consider game volume
game_position_weight = 1.0 - (game_index / total_games) * volume_factor

# Example: For 400 games, more recent games weighted higher
# Game 400 (latest): weight = 1.0
# Game 300: weight = 0.75
# Game 200: weight = 0.5
# Game 100: weight = 0.25
```

### 3. Performance-Adjusted Weighting (NEW)
```python
# Weight matches by in-game performance, not just win/loss
performance_weight = (
    0.4 * normalized_combat_score +
    0.3 * normalized_economic_score +
    0.2 * normalized_overall_impact +
    0.1 * (1 if won else 0.5)
)

# This rewards strong performances even in losses
```

### 4. Momentum Weighting (NEW)
```python
# Detect and reward positive trends
def calculate_momentum_factor(recent_wr, overall_wr):
    """
    Boost rating if recent performance exceeds historical average.
    """
    momentum = recent_wr - overall_wr

    if momentum > 0.15:  # Significant improvement
        return 1.3  # 30% boost
    elif momentum > 0.08:  # Moderate improvement
        return 1.15  # 15% boost
    elif momentum < -0.15:  # Significant decline
        return 0.85  # 15% penalty
    else:
        return 1.0  # Neutral
```

### 5. Sample Size Confidence (NEW)
```python
# Players with more games have more stable ratings
def calculate_confidence_weight(game_count, min_games=50, max_games=500):
    """
    Weight matches by player experience level.
    More games = more confidence in rating stability.
    """
    if game_count < min_games:
        return 0.5 + (game_count / min_games) * 0.5  # 0.5 to 1.0
    elif game_count > max_games:
        return 1.2  # Veteran bonus
    else:
        return 1.0 + (game_count - min_games) / (max_games - min_games) * 0.2
```

---

## Combined Weighting Formula

```python
def calculate_hybrid_weight(
    days_ago: float,
    game_index: int,
    total_games: int,
    performance_metrics: dict,
    recent_wr: float,
    overall_wr: float,
    config: dict
) -> float:
    """
    Calculate hybrid weight for a match.

    Combines:
    1. Time decay (exponential)
    2. Game position (linear)
    3. Performance quality
    4. Win rate momentum
    5. Sample size confidence
    """
    # 1. Time-based recency (40% weight)
    time_weight = 0.5 ** (days_ago / config['half_life_days'])

    # 2. Game volume position (20% weight)
    volume_weight = 1.0 - (game_index / max(total_games, 1)) * config['volume_factor']

    # 3. Performance quality (25% weight)
    perf_weight = (
        0.4 * performance_metrics.get('combat_score_norm', 0.5) +
        0.3 * performance_metrics.get('economic_score_norm', 0.5) +
        0.2 * performance_metrics.get('overall_impact_norm', 0.5) +
        0.1 * (1.0 if performance_metrics.get('won') else 0.5)
    )

    # 4. Momentum factor (10% weight)
    momentum = calculate_momentum_factor(recent_wr, overall_wr)

    # 5. Confidence factor (5% weight)
    confidence = calculate_confidence_weight(total_games)

    # Combine all factors
    hybrid_weight = (
        time_weight * 0.40 +
        volume_weight * 0.20 +
        perf_weight * 0.25 +
        momentum * 0.10 +
        confidence * 0.05
    )

    return hybrid_weight
```

---

## Impact on DragonKing

**Current System:**
- Recency MMR: 2817 (-38 from standard)
- Recent hot streak (66.7% WR) barely recognized

**Proposed Hybrid System (Estimated):**
```python
# DragonKing's metrics:
# - 406 games (high volume) → confidence_weight = 1.15
# - 66.7% recent WR vs 35.7% overall → momentum_factor = 1.3
# - Combat score 25.10 (excellent) → perf_weight boost
# - Last match: today → time_weight = 1.0

Estimated Hybrid MMR: 3050-3150 (+195-295 from standard)
```

This would place him closer to his true current skill level.

---

## Other Metrics to Consider

### A. Team Handicap Adjustment (Already Implemented)
```python
# Handicap-corrected MMR considers team strength imbalance
handicap_corrected_mmr = mmr + (outperformance * 3000)
```
- DragonKing: 2735 (-120) - He's often on stronger teams

### B. Combat Performance Multiplier (Already in Unified MMR)
```python
# Unified MMR formula
unified_mmr = handicap_corrected_mmr + (20 * avg_combat_score)
```
- DragonKing: 3712 (+857) - His combat shines here!

### C. Additional Metrics to Implement

#### 1. **Consistency Score**
```python
def calculate_consistency_score(match_results):
    """
    Reward consistent performance (low variance).
    """
    mmr_changes = [match.mmr_after - match.mmr_before for match in match_results]
    variance = np.var(mmr_changes)

    # Low variance = consistent = bonus
    if variance < 100:
        return 1.1
    elif variance > 300:
        return 0.95
    return 1.0
```

#### 2. **Clutch Performance**
```python
def calculate_clutch_factor(close_game_wr, overall_wr):
    """
    Reward winning close games (predicted < 55%).
    """
    if close_game_wr > overall_wr + 0.10:
        return 1.15  # Clutch player
    return 1.0
```

#### 3. **Role Versatility**
```python
def calculate_versatility_bonus(race_distribution):
    """
    Reward players who perform well across multiple roles/races.
    """
    entropy = -sum(p * log(p) for p in race_distribution if p > 0)
    max_entropy = log(3)  # 3 races

    versatility = entropy / max_entropy
    return 1.0 + (versatility * 0.1)  # Up to 10% bonus
```

#### 4. **MVP Rate**
```python
def calculate_mvp_factor(mvp_rate):
    """
    How often is player the top performer in their matches?
    """
    if mvp_rate > 0.5:  # MVP in >50% of games
        return 1.2
    elif mvp_rate > 0.3:
        return 1.1
    return 1.0
```

#### 5. **Comeback Factor**
```python
def calculate_comeback_bonus(comeback_wins, expected_losses):
    """
    Reward winning games where team was predicted to lose.
    """
    comeback_rate = comeback_wins / max(expected_losses, 1)

    if comeback_rate > 0.5:  # Win >50% of underdog matches
        return 1.25
    elif comeback_rate > 0.35:
        return 1.15
    return 1.0
```

---

## Recommended Configurations

### Profile 1: Momentum-Focused (Rewards Hot Streaks)
```python
config = {
    'half_life_days': 45,  # Shorter = more responsive
    'volume_factor': 0.3,
    'momentum_weight': 0.20,  # Higher momentum influence
    'performance_weight': 0.25,
    'time_weight': 0.35,
}
```
**Best for:** Active players like DragonKing

### Profile 2: Consistency-Focused (Rewards Stable Performance)
```python
config = {
    'half_life_days': 120,  # Longer = more stable
    'volume_factor': 0.5,
    'momentum_weight': 0.05,
    'performance_weight': 0.35,  # Higher performance weight
    'time_weight': 0.40,
}
```
**Best for:** Veterans like ChrisO, Stephan

### Profile 3: Balanced Hybrid
```python
config = {
    'half_life_days': 75,
    'volume_factor': 0.4,
    'momentum_weight': 0.15,
    'performance_weight': 0.25,
    'time_weight': 0.35,
    'confidence_weight': 0.10,
}
```
**Best for:** General leaderboard

---

## Implementation Priority

### Phase 1: Quick Wins (High Impact, Low Effort)
1. ✅ **Momentum Factor** - Detect hot/cold streaks
2. ✅ **Performance Weighting** - Use existing combat/economic scores
3. ⚠️ **Adjustable Half-Life** - Make configurable (45-120 days)

### Phase 2: Advanced Metrics (Medium Effort)
4. **Game-Volume Weighting** - Position in match history
5. **Consistency Score** - Variance analysis
6. **Clutch Performance** - Close game analysis

### Phase 3: Deep Analysis (High Effort)
7. **MVP Rate** - Track top performer frequency
8. **Comeback Factor** - Underdog win analysis
9. **Role Versatility** - Cross-race performance

---

## Testing Strategy

1. **Backtest** on historical data:
   - Compare Standard vs Recency vs Hybrid rankings
   - Measure prediction accuracy for each system

2. **Edge Case Analysis:**
   - New players (< 50 games)
   - Inactive players returning
   - Players on extreme streaks

3. **Validation Metrics:**
   - Prediction accuracy (actual vs predicted match outcomes)
   - Rank stability (day-to-day variance)
   - Player satisfaction (survey)

---

## Conclusion

**For DragonKing specifically:**
- Enable **Momentum Factor** (+30% boost for 66.7% recent WR)
- Reduce **Half-Life to 45-60 days** (more responsive to recent play)
- Keep **Combat Performance Bonus** (already giving +857 in Unified MMR)
- Add **Clutch Performance** tracking (likely wins close games)

This would move his rating from **2817 → ~3000-3100**, better reflecting his current hot streak while still accounting for historical performance.
