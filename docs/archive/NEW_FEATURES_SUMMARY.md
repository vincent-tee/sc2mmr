# New Features Summary

This document summarizes all new features implemented for the SC2 MMR system.

---

## 1. Auto-Optimization System ✅ **COMPLETE**

### What It Does
Automatically optimizes Adaptive Model weights after every N matches without manual intervention.

### Configuration
- **Frequency**: Every 5 matches (configurable)
- **Triggers**: Automatically during replay uploads
- **Analysis**: Retroactive - analyzes all matches in database (up to 1,000)

### Why It Matters
- **Before**: Manual refresh required after uploads
- **After**: Continuous improvement - system learns automatically
- **Perfect for**: 200-300 matches/year datasets

### How to Use

**Backend (Automatic):**
```bash
# Auto-optimization runs during uploads
# No action needed!

# Check status via API:
curl http://localhost:8000/adaptive/auto-status

# Force optimization (testing):
curl -X POST http://localhost:8000/adaptive/force-optimize
```

**Frontend:**
- Visit **Adaptive Model** page
- See progress bar: "3 / 5 matches until next optimization"
- Updates automatically every 30 seconds
- Refreshes on manual "Refresh Analysis" click

### Configuration
```python
# In backend/app/auto_adaptive.py
AutoAdaptiveConfig.MATCHES_PER_OPTIMIZATION = 5  # Change frequency
AutoAdaptiveConfig.ENABLED = True  # Enable/disable
```

---

## 2. Predictive Win Probability ✅ **BACKEND COMPLETE** / ⏸️ **FRONTEND TODO**

### What It Does
Tracks predicted vs actual match outcomes to validate rating accuracy.

### How It Works

1. **Before Match**: Calculate win probability from TrueSkill ratings
   ```python
   # Team 1: Players with mu=27.5, 26.2, 28.1
   # Team 2: Players with mu=25.0, 24.3, 26.8
   # Predicted: Team 1 win probability = 0.68 (68%)
   ```

2. **Store Prediction**: Save with match record
   ```python
   match.predicted_team1_win_prob = 0.68
   match.predicted_team2_win_prob = 0.32
   ```

3. **After Match**: Compare prediction to actual outcome
   ```python
   # Actual: Team 1 wins
   # Prediction was correct! (68% prob, happened)

   # OR
   # Actual: Team 2 wins (upset!)
   # Prediction was wrong (68% said Team 1, but Team 2 won)
   ```

### Backend Implementation ✅

**Database:**
- Added `predicted_team1_win_prob` column to matches table
- Added `predicted_team2_win_prob` column to matches table
- Migration script: `backend/add_match_predictions.py`

**Calculation:**
- Uses Gaussian CDF with TrueSkill mu/sigma
- Accounts for team strength AND uncertainty
- Formula: P(team1 > team2) = CDF(delta_mu / total_sigma)

**API Response:**
- Match details now include predictions
- Available in `/replays/matches/{id}`
- Included in match history endpoints

### Frontend Implementation ⏸️ **TODO**

Need to add displays to these pages:

**1. Match Detail Page** (`frontend/src/pages/MatchDetail.jsx`):
```jsx
// Add prediction vs outcome card
<Card>
  <Heading size="sm">Pre-Match Prediction</Heading>
  <HStack>
    <VStack>
      <Text>Team 1 (Predicted)</Text>
      <Text fontSize="2xl" fontWeight="bold">68%</Text>
      <Badge colorScheme="green">Winner ✓</Badge>
    </VStack>
    <Icon as={FiTrendingUp} />
    <VStack>
      <Text>Team 2 (Predicted)</Text>
      <Text fontSize="2xl">32%</Text>
      <Badge>Loser</Badge>
    </VStack>
  </HStack>
  <Progress value={68} colorScheme="green" />
  <Text fontSize="sm" color="gray.500">
    Rating system predicted this outcome correctly
  </Text>
</Card>
```

**2. Match History Page** (`frontend/src/pages/MatchHistory.jsx`):
```jsx
// Add prediction indicator
<Badge colorScheme={isPredictionCorrect ? "green" : "orange"}>
  {isPredictionCorrect ? "Expected" : `Upset! (${predictedProb}%)`}
</Badge>
```

**3. New: Prediction Accuracy Page** (create new):
```jsx
// Show overall prediction stats
- Total matches with predictions: 150
- Correctly predicted: 118 (79%)
- Upsets (wrong predictions): 32 (21%)
- Average predicted probability: 64%
- Calibration chart (predicted vs actual win rate)
```

### Migration Steps

**For existing matches** (won't have predictions):
```bash
cd /home/user/sc2mmr/backend

# Add columns to database
python3 add_match_predictions.py

# Existing matches will have NULL predictions
# New uploads will calculate automatically
```

### Use Cases

1. **Validate Ratings**: Are predictions accurate?
2. **Track Upsets**: Low-probability wins = exciting matches
3. **Improve Balancing**: See if teams are truly balanced
4. **Player Analysis**: Who performs better/worse than predicted?

---

## 3. Timestamp on Adaptive Model ✅ **COMPLETE**

### What It Does
Shows when analysis was last refreshed.

### Display
```
Last updated: 2:30:45 PM
```

Updates every time "Refresh Analysis" is clicked, providing visual confirmation the system is working.

---

## 4. Database Reset Utilities ✅ **COMPLETE**

### Scripts Created

**`backend/reset_database.py`:**
- Clear matches only (keep players)
- Clear everything (full reset)
- Used for starting fresh or testing

**`backend/recalculate_ratings.py`:**
- Recalculates TrueSkill from scratch
- Processes matches chronologically
- Used after player merges

### Usage
```bash
cd /home/user/sc2mmr/backend

# Reset matches (keep players)
python3 reset_database.py matches

# Complete wipe
python3 reset_database.py everything

# Recalculate ratings
python3 recalculate_ratings.py
```

---

## Summary of What's Working

| Feature | Backend | Frontend | Status |
|---------|---------|----------|--------|
| Auto-Optimization | ✅ | ✅ | **Complete** |
| Optimization Progress Bar | ✅ | ✅ | **Complete** |
| Timestamp Display | ✅ | ✅ | **Complete** |
| Win Probability Calculation | ✅ | ⏸️ | **Backend Done** |
| Win Probability Display | ✅ | ⏸️ | **Frontend TODO** |
| Database Reset | ✅ | N/A | **Complete** |

---

## Next Steps

### Immediate (Recommended):

1. **Run Database Migration**:
   ```bash
   cd /home/user/sc2mmr/backend
   python3 add_match_predictions.py
   ```

2. **Restart Backend**:
   ```bash
   sudo systemctl restart sc2mmr-backend
   ```

3. **Rebuild Frontend**:
   ```bash
   cd /home/user/sc2mmr/frontend
   npm run build
   sudo cp -r build/* /var/www/html/sc2mmr/
   ```

### Optional (Frontend Enhancement):

Add prediction displays to:
- Match Detail page (predicted vs actual)
- Match History page (upset badges)
- New Prediction Accuracy page (stats & charts)

**Example implementation** in `MatchDetail.jsx`:
```jsx
{match.predicted_team1_win_prob && (
  <Card p={4} mb={4}>
    <Heading size="sm" mb={3}>Pre-Match Prediction</Heading>
    <HStack justify="space-around">
      <VStack>
        <Text fontSize="3xl" fontWeight="bold" color={team1Won ? "green.500" : "gray.400"}>
          {formatPercentage(match.predicted_team1_win_prob)}
        </Text>
        <Text fontSize="sm">Team 1</Text>
        {team1Won && <Badge colorScheme="green">Winner ✓</Badge>}
      </VStack>

      <Icon as={FiVersus} boxSize={6} color="gray.400" />

      <VStack>
        <Text fontSize="3xl" fontWeight="bold" color={!team1Won ? "green.500" : "gray.400"}>
          {formatPercentage(match.predicted_team2_win_prob)}
        </Text>
        <Text fontSize="sm">Team 2</Text>
        {!team1Won && <Badge colorScheme="green">Winner ✓</Badge>}
      </VStack>
    </HStack>

    {/* Upset indicator */}
    {((team1Won && match.predicted_team1_win_prob < 0.4) ||
      (!team1Won && match.predicted_team2_win_prob < 0.4)) && (
      <Alert status="warning" mt={3}>
        <AlertIcon />
        <Text>Upset! The underdog won this match.</Text>
      </Alert>
    )}
  </Card>
)}
```

---

## Testing Checklist

- [ ] Upload a replay - check auto-optimization triggers in logs
- [ ] Visit Adaptive Model page - see progress bar
- [ ] Wait for 5 matches - verify auto-optimization runs
- [ ] Check match details - predictions should be present (after migration)
- [ ] Verify timestamp updates on manual refresh
- [ ] Test database reset scripts

---

## Configuration Reference

### Auto-Optimization
**File**: `backend/app/auto_adaptive.py`
```python
MATCHES_PER_OPTIMIZATION = 5      # How often to optimize
MIN_MATCHES_FOR_FIRST_RUN = 50   # Minimum data needed
ENABLED = True                    # Master switch
```

### TrueSkill
**File**: `backend/app/rating_system.py`
```python
trueskill.setup(
    mu=25.0,              # Starting skill
    sigma=8.333,          # Starting uncertainty
    beta=4.166,           # Skill class width
    tau=0.0833,           # Dynamics factor
    draw_probability=0.0  # No draws
)
```

---

## Documentation Files

- `DEPLOYMENT_TESTING_GUIDE.md` - Complete deployment guide
- `RESET_AND_RECALCULATE_GUIDE.md` - Database reset procedures
- `PLAYER_MERGE_GUIDE.md` - Merging duplicate players
- `NEW_FEATURES_SUMMARY.md` - This file!

---

## Support

All features are committed and pushed to branch: `claude/code-review-logging-ui-01SG2RJtaJHMZ7KPyzzLJC16`

**Latest commits:**
- `384ac7e` - Predictive win probability (backend)
- `9987cd4` - Auto-optimization system
- `44dd068` - Timestamp display
- `c4c2fde` - AEST timezone
- Previous commits include UI fixes, pagination, etc.
