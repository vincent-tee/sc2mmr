# Phase 1: Dynamic Ability Discovery - Working Documentation

## Quick Start

**Time to Complete:** 1-2 hours (implementation) + 1 hour (testing)

**Risk Level:** LOW (feature flag pattern with instant rollback)

---

## Part 1: Implementation Instructions

### File to Modify: `backend/app/services/enhanced_parser.py`

### Step 1: Add Import Statements

**Location:** After line ~29 (after existing imports)

**Add these lines:**

```python
import os

# Dynamic ability discovery (Option B integration)
try:
    from ability_discovery import get_discovery_engine
    DYNAMIC_DISCOVERY_AVAILABLE = True
except ImportError:
    DYNAMIC_DISCOVERY_AVAILABLE = False
    get_discovery_engine = None
```

**What this does:**
- Imports the dynamic discovery engine (already built and tested)
- Sets a flag to know if it's available
- Falls back gracefully if import fails

---

### Step 2: Update `__init__` Method

**Location:** Lines ~350-375

**Replace entire method with:**

```python
def __init__(self, replay_path: str):
    """
    Initialize parser with replay file.

    Args:
        replay_path: Path to .SC2Replay file
    """
    self.replay_path = replay_path
    self.replay = None
    self._player_features: Dict[int, EnhancedPlayerFeatures] = {}
    
    # Option B: Dynamic ability discovery (feature flag for instant rollback)
    self.use_dynamic_discovery = os.getenv("USE_DYNAMIC_DISCOVERY", "false").lower() == "true"
    
    if self.use_dynamic_discovery and DYNAMIC_DISCOVERY_AVAILABLE:
        try:
            self.ability_discovery = get_discovery_engine()
            print("✅ Dynamic ability discovery ENABLED (Option B)")
        except Exception as e:
            print(f"⚠️ Failed to initialize dynamic discovery: {e}, using fallback")
            self.use_dynamic_discovery = False
            self.ability_discovery = None
    else:
        self.ability_discovery = None
        if self.use_dynamic_discovery and not DYNAMIC_DISCOVERY_AVAILABLE:
            print("⚠️ Dynamic discovery requested but module not available, using hardcoded")
        else:
            print("⚠️ Dynamic ability discovery DISABLED (using hardcoded TRACKED_ABILITIES)")
```

**What this does:**
- Checks environment variable for feature flag
- Only initializes dynamic discovery if enabled
- Falls back to original hardcoded logic if disabled
- Safe defaults to disabled mode

---

### Step 3: Replace `_extract_ability_usage` Method

**Location:** Lines ~587-630

**Replace entire method with:**

```python
def _extract_ability_usage(self):
    """Extract ability usage counts for micro skill assessment."""
    
    # Path 1: Original hardcoded tracking (if disabled)
    if not self.use_dynamic_discovery:
        print("⚠️ Using hardcoded TRACKED_ABILITIES (disabled)")
        if not hasattr(self.replay, 'game_events'):
            logger.warning("No game events available for ability extraction")
            return
        
        for event in self.replay.game_events:
            if hasattr(event, 'ability') and hasattr(event, 'player'):
                self._process_ability_event(event)
        return
    
    # Path 2: Dynamic discovery with filtering (Option B)
    print("✅ Using dynamic ability discovery (Option B)")
    
    if not hasattr(self.replay, 'game_events'):
        logger.warning("No game events available for ability extraction")
        return
    
    # Discover all abilities from replay
    try:
        discovered_abilities = self.ability_discovery.discover_from_replay(
            self.replay,
            getattr(self.replay, 'release_string', 'unknown')
        )
        print(f"✅ Discovered {len(discovered_abilities)} unique abilities")
    except Exception as e:
        print(f"❌ Ability discovery failed: {e}")
        return
    
    # Track only abilities that should be tracked (per filters)
    for event in self.replay.game_events:
        if hasattr(event, 'ability') and hasattr(event, 'player'):
            ability_name = getattr(event.ability, 'name', None) or str(event.ability)
            
            # Use dynamic discovery's filter logic
            if self.ability_discovery.should_track_ability(ability_name):
                self._process_ability_event(event)
    
    print("✅ Tracked abilities using dynamic discovery filters")
```

**What this does:**
- Checks feature flag to decide which path to use
- If disabled: Uses original hardcoded tracking (backward compatible)
- If enabled: Uses dynamic discovery to find all abilities
- Applies filters to exclude trivial abilities (Train*, Build*, etc.)

---

### Step 4: Add New Method After `parse()` Method

**Location:** After line ~400 (after the `parse()` method ends)

**Add this new method:**

```python
def get_discovered_abilities(self) -> Dict[str, Dict]:
    """
    Export discovered ability metadata for ML features.
    
    Returns:
        Dict mapping ability_name to metadata (category, priority, usage_count)
        Returns empty dict if dynamic discovery not enabled.
    """
    if not self.use_dynamic_discovery or self.ability_discovery is None:
        print("⚠️ Dynamic discovery not enabled, returning empty abilities")
        return {}
    
    return {
        ability_name: {
            "category": metadata.category,
            "priority": metadata.priority,
            "usage_count": metadata.usage_count,
            "patches_seen": metadata.patches_seen,
            "first_seen_date": metadata.first_seen_date,
        }
        for ability_name, metadata in self.ability_discovery.discovered_abilities.items()
    }
```

**What this does:**
- Exports discovered abilities with full metadata
- Returns empty dict if disabled (backward compatible)
- Provides data for ML pipeline (ability categories, priorities, usage counts)

---

## Part 2: Testing Instructions

### Test 1: Verify Import Works

```bash
cd /home/vtee/projects/sc2mmr/backend/app/services
python3 -c "
try:
    from ability_discovery import get_discovery_engine
    print('✅ Import works')
except Exception as e:
    print(f'❌ Import failed: {e}')
"
```

**Expected output:** `✅ Import works`

---

### Test 2: Test Baseline (Dynamic Discovery OFF)

```bash
cd /home/vtee/projects/sc2mmr/backend
export USE_DYNAMIC_DISCOVERY=false
python3 -c "
import os
from services.enhanced_parser import EnhancedReplayParser

parser = EnhancedReplayParser('replays/test.SC2Replay')
print(f'✅ Parser created')
print(f'✅ Dynamic mode: {parser.use_dynamic_discovery}')
print(f'✅ Discovery engine: {parser.ability_discovery is not None}')
"
```

**Expected output:**
```
✅ Parser created
✅ Dynamic mode: False
✅ Discovery engine: False
```

---

### Test 3: Test Dynamic Discovery ON

```bash
cd /home/vtee/projects/sc2mmr/backend
export USE_DYNAMIC_DISCOVERY=true
python3 -c "
import os
from services.enhanced_parser import EnhancedReplayParser
from pathlib import Path

replay_path = Path('replays/182798096b582be280eaef93df553ade36906b4ee8ca99e5fe61d791863a057f.SC2Replay')
parser = EnhancedReplayParser(str(replay_path))
print(f'✅ Parser created')
print(f'✅ Dynamic mode: {parser.use_dynamic_discovery}')
print(f'✅ Discovery engine: {parser.ability_discovery is not None}')
print(f'✅ Replay version: {parser.replay.release_string if parser.replay else \"N/A\"}')

# Parse the replay
features = parser.parse()

# Show results
for pid, player_features in features.items():
    abilities = player_features.ability_usage.abilities
    print(f'Player {pid}: {len(abilities)} abilities tracked')

# Check discovered abilities
if parser.use_dynamic_discovery:
    discovered = parser.get_discovered_abilities()
    print(f'✅ Discovered abilities: {len(discovered)}')
    if len(discovered) > 0:
        sample = list(discovered.items())[:3]
        for name, meta in sample:
            print(f'  Sample: {name} (category: {meta[\"category\"]}, priority: {meta[\"priority\"]})')
"
```

**Expected output:**
```
✅ Parser created
✅ Dynamic mode: True
✅ Discovery engine: True
✅ Replay version: 5.0.15.95299
✅ Discovered X unique abilities
Player 1: Y abilities tracked
Player 2: Y abilities tracked
✅ Discovered abilities: X
  Sample: NexusMassRecall (category: macro, priority: 8)
  Sample: WarpInZealot (category: high_micro, priority: 7)
  Sample: ...
```

---

### Test 4: Run Integration Tests

```bash
cd /home/vtee/projects/sc2mmr/backend
python3 tests/test_option_b_integration.py
```

**Expected output:**
```
✅ ALL TESTS PASSED

📋 NEXT STEPS:
1. Update enhanced_parser.py to use DynamicAbilityDiscovery
2. Add database table: learned_abilities
3. Update API endpoints to expose discovered abilities
4. Run existing test suite to ensure backward compatibility
5. Deploy and monitor ability discovery in production
```

---

## Part 3: Deployment Instructions

### Environment Setup

#### Option 1: Set Environment Variable in Shell

```bash
# For production deployment (recommended: start disabled)
export USE_DYNAMIC_DISCOVERY=false

# For testing/staging (dynamic discovery enabled)
export USE_DYNAMIC_DISCOVERY=true
```

#### Option 2: Set in Dockerfile

```dockerfile
# Add to your Dockerfile
ENV USE_DYNAMIC_DISCOVERY=false
```

#### Option 3: Set in systemd/Process Manager

```ini
# /etc/systemd/system/sc2mmr.service
[Service]
Environment="USE_DYNAMIC_DISCOVERY=false"
```

#### Option 4: Set in application startup script

```bash
#!/bin/bash
# start.sh
export USE_DYNAMIC_DISCOVERY=false
python3 app/main.py
```

---

### Deployment Strategy

#### Phase 1: Staging (Week 1)

**Steps:**

1. Deploy with `USE_DYNAMIC_DISCOVERY=false` (disabled)
   ```bash
   export USE_DYNAMIC_DISCOVERY=false
   python3 app/main.py
   ```

2. Verify baseline works:
   - Parse 10 test replays
   - Record ability counts
   - Note parse times

3. Enable for 5% of replays (A/B test):
   ```bash
   # In your code, randomly enable
   if random.random() < 0.05:
       os.environ['USE_DYNAMIC_DISCOVERY'] = 'true'
   ```

4. Compare results:
   - Ability counts (should be higher with dynamic)
   - Parse times (should be < 10% slower)
   - Error rates (should be same or lower)

5. Monitor for 1 week
   - Collect metrics
   - Check for any issues

---

#### Phase 2: Production Read-Only (Week 2)

**Steps:**

1. Deploy with `USE_DYNAMIC_DISCOVERY=false` (default off)
2. Add shadow logging:
   ```python
   # In your logging code
   if dynamic_discovery_available and use_dynamic_discovery:
       # Log results without using them
       discovered_abilities = discovery_engine.discover_from_replay(...)
       logger.info(f"Shadow mode: would discover {len(discovered_abilities)} abilities")
   ```

3. Monitor for 1 week
4. Validate no issues in production

---

#### Phase 3: Production Gradual Rollout (Week 3-4)

**Week 3: 10% Rollout**

```bash
# Enable for 10% of replay parsing
export USE_DYNAMIC_DISCOVERY=true
```

**Week 4: 50% Rollout**

```bash
# Enable for 50% of replay parsing
export USE_DYNAMIC_DISCOVERY=true
```

**Week 5+: 100% Rollout**

```bash
# Enable for all replay parsing
export USE_DYNAMIC_DISCOVERY=true
```

---

## Part 4: Rollback Instructions

### Method 1: Instant Rollback (Environment Variable) - RECOMMENDED

**Rollback in < 1 second:**

```bash
# Disable dynamic discovery instantly
export USE_DYNAMIC_DISCOVERY=false

# Restart application
systemctl restart sc2mmr
# OR
python3 app/main.py  # If not running as service
```

**Verification:**
```bash
# Check if disabled
python3 -c "
import os
print(f'USE_DYNAMIC_DISCOVERY: {os.getenv(\"USE_DYNAMIC_DISCOVERY\", \"not set\")}')
"
```

---

### Method 2: Code Rollback (Git)

**Complete rollback:**

```bash
# Revert to previous version
git checkout backend/app/services/enhanced_parser.py

# Restart application
systemctl restart sc2mmr
```

**Specific rollback (if needed):**

```bash
# Remove dynamic discovery code only, keep ability_discovery module
git checkout HEAD~ -- backend/app/services/enhanced_parser.py
# Then manually revert just the 4 changes
```

---

### Method 3: Using Rollback Script

```bash
# Run the provided script
./PHASE-1-ROLLBACK-SHELL.sh

# Choose option 1 (recommended)
export USE_DYNAMIC_DISCOVERY=false

# Restart application
```

---

## Part 5: Troubleshooting

### Issue: Module Not Found

```
ImportError: cannot import name 'get_discovery_engine'
```

**Cause:** `ability_discovery.py` not in same directory as `enhanced_parser.py`

**Solution:**
```bash
# Check file locations
ls -la backend/app/services/ | grep -E "(ability|enhanced)"

# They should be in same directory
# Both: backend/app/services/
```

---

### Issue: Environment Variable Not Working

```
Environment variable set but not recognized
```

**Cause:** Variable set after Python process started

**Solution:**
```bash
# Set BEFORE starting Python
export USE_DYNAMIC_DISCOVERY=true
python3 app/main.py  # Must be same command

# NOT this (doesn't work):
python3 app/main.py  # Then export inside Python
```

---

### Issue: No Abilities Tracked

```
Player 1: 0 abilities tracked
```

**Possible Causes:**

1. Replay has no game events
2. Discovery engine failing silently
3. Filter too aggressive

**Debug Steps:**

```bash
# Enable debug output
export USE_DYNAMIC_DISCOVERY=true

# Add debug prints (already included in implementation)
python3 app/main.py

# Look for these messages:
# - "✅ Discovered X unique abilities"
# - "✅ Tracked abilities using dynamic discovery filters"
# - "❌ Ability discovery failed:"
```

**Quick Fix:**

```bash
# If discovery failing, temporarily disable filters
# Edit abilities_config.json
# Set "min_priority": 1 (include everything)
```

---

### Issue: Parse Time Too Slow

```
Parse time increased by 50%+
```

**Cause:** Dynamic discovery overhead too high

**Solutions:**

1. Increase filter aggressiveness:
   ```json
   // In abilities_config.json
   {
     "filter_patterns": {
       "exclude_prefixes": ["Train", "Build", "Research", "Cancel", "RightClick"]
       // More aggressive
     }
   }
   ```

2. Enable caching:
   ```python
   # Add caching to ability_discovery.py
   # Cache discovered abilities from recent replays
   ```

3. Disable for production (if needed):
   ```bash
   export USE_DYNAMIC_DISCOVERY=false
   ```

---

## Part 6: Verification Checklist

### Before Implementation

- [ ] Backup current `enhanced_parser.py`
- [ ] Run existing tests to establish baseline
- [ ] Note current ability tracking counts
- [ ] Choose deployment environment (staging/production)

### During Implementation

- [ ] Follow Part 1 instructions exactly
- [ ] Test import after each change
- [ ] Verify no syntax errors
- [ ] Commit changes with descriptive message

### After Implementation

- [ ] Run Test 2 (baseline mode)
- [ ] Run Test 3 (dynamic mode)
- [ ] Run Test 4 (integration tests)
- [ ] Compare ability counts (dynamic > baseline)
- [ ] Check parse time impact (< 10% acceptable)

### Before Production Deployment

- [ ] Deploy to staging first
- [ ] Monitor for 24-48 hours
- [ ] Review metrics (ability coverage, parse time, errors)
- [ ] Get approval for production rollout

### After Production Deployment

- [ ] Monitor for 1 week
- [ ] Compare ML model accuracy (should improve or stay same)
- [ ] Check error rates (should not increase)
- [ ] Review user feedback

---

## Part 7: Integration with ML Pipeline

### Using Discovered Abilities in XGBoost

**After Phase 1 complete, you can use ability metadata in your ML pipeline:**

```python
from services.enhanced_parser import EnhancedReplayParser

# Parse replay with dynamic discovery
parser = EnhancedReplayParser(replay_path)
features = parser.parse()

# Get discovered abilities
discovered = parser.get_discovered_abilities()

# Example: Create ML features
ml_features = {}
for pid, player_features in features.items():
    # Ability diversity score
    ability_diversity = len(player_features.ability_usage.abilities)
    ml_features[f'player_{pid}_ability_diversity'] = ability_diversity
    
    # High-micro ability count (category filtering)
    high_micro_abilities = sum(
        1 for name, meta in discovered.items()
        if meta['category'] == 'high_micro' and name in player_features.ability_usage.abilities
    )
    ml_features[f'player_{pid}_high_micro_count'] = high_micro_abilities
    
    # Weighted ability score (priority * usage)
    weighted_score = sum(
        meta['priority'] * meta['usage_count']
        for name, meta in discovered.items()
        if name in player_features.ability_usage.abilities
    )
    ml_features[f'player_{pid}_weighted_ability_score'] = weighted_score

print(f"ML features: {ml_features}")
```

**This prepares for Phase 2 (SHAP feature importance) by providing:**
- Ability categories for feature engineering
- Priority weights for feature importance
- Usage counts for feature scaling

---

## Part 8: Success Criteria

Phase 1 is COMPLETE when ALL are true:

- [ ] All 4 code changes applied to `enhanced_parser.py`
- [ ] Import test passes (Test 1)
- [ ] Baseline test passes (Test 2)
- [ ] Dynamic mode test passes (Test 3)
- [ ] Integration tests pass (Test 4)
- [ ] Ability coverage increased (> baseline)
- [ ] Parse time impact < 10% (acceptable)
- [ ] Rollback tested (environment variable works)
- [ ] Documentation reviewed
- [ ] Ready for Phase 2 (SHAP)

---

## Quick Reference Commands

### Enable Dynamic Discovery
```bash
export USE_DYNAMIC_DISCOVERY=true
python3 app/main.py
```

### Disable Dynamic Discovery
```bash
export USE_DYNAMIC_DISCOVERY=false
python3 app/main.py
```

### Check Current State
```bash
echo $USE_DYNAMIC_DISCOVERY
```

### Test Discovery Engine
```bash
cd backend/app/services
python3 -c "from ability_discovery import get_discovery_engine; discovery = get_discovery_engine(); print('Available' if discovery else 'Not available')"
```

---

## Summary

**Implementation Time:** 1-2 hours
**Testing Time:** 1 hour
**Deployment Time:** 1 day (staging) → 1 week (gradual production)

**Risk:** LOW (feature flag + instant rollback)

**ML Uplift:** Foundation for Phase 2 (SHAP) - Expected 10-20% model accuracy improvement

---

**START HERE:** Part 1: Implementation Instructions (Step 1)
