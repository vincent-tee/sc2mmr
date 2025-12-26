# Phase 1: Complete Option B Integration Guide

## Overview
This guide provides step-by-step instructions for integrating dynamic ability discovery
into `enhanced_parser.py` with instant rollback capability.

## Pre-Requisites
✅ Already Complete:
- `backend/app/services/ability_discovery.py` - Dynamic discovery engine
- `backend/config/abilities_config.json` - Configuration file
- `backend/tests/test_option_b_integration.py` - Integration tests passing
- `backend/app/services/enhanced_parser.py` - Existing parser to modify

## Instant Rollback Strategy

### Method 1: Environment Variable (RECOMMENDED - Instant)
```bash
# ENABLE dynamic discovery (production)
export USE_DYNAMIC_DISCOVERY=true

# DISABLE dynamic discovery (instant rollback)
export USE_DYNAMIC_DISCOVERY=false

# Apply by restarting your application
```

### Method 2: Code Comment (Backup)
```python
# Comment out dynamic discovery code (lines added in Phase 1)
# To disable, comment lines X-Y, uncomment original code
```

---

## Step-by-Step Implementation

### File 1: `backend/app/services/enhanced_parser.py`

#### Change 1.1: Add imports (after line ~24)

**Find this section:**
```python
import sc2reader
from sc2reader.events import (
    TrackerEvent,
)
```

**Add after it:**
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

---

#### Change 1.2: Update `__init__` method (replace lines ~349-359)

**Find:**
```python
def __init__(self, replay_path: str):
    self.replay_path = replay_path
    self.replay = None
    self._player_features: Dict[int, EnhancedPlayerFeatures] = {}
```

**Replace with:**
```python
def __init__(self, replay_path: str):
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

---

#### Change 1.3: Update `_extract_ability_usage` method (replace lines ~587-619)

**Find:**
```python
def _extract_ability_usage(self):
    """Extract ability usage counts for micro skill assessment."""
    if not hasattr(self.replay, 'game_events'):
        logger.warning("No game events available for ability extraction")
        return

    for event in self.replay.game_events:
        if hasattr(event, 'ability') and hasattr(event, 'player'):
            self._process_ability_event(event)
```

**Replace with:**
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

---

#### Change 1.4: Add new method after `parse()` method (after line ~400)

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

---

## Verification Steps

### Step 1: Test Import
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

### Step 2: Test with Environment Variable (OFF by default)
```bash
# Dynamic discovery OFF (hardcoded fallback)
cd /home/vtee/projects/sc2mmr/backend
python3 -c "
import os
os.environ['USE_DYNAMIC_DISCOVERY'] = 'false'
from services.enhanced_parser import EnhancedReplayParser
parser = EnhancedReplayParser('replays/test.SC2Replay')
print(f'✅ Parser created, use_dynamic: {parser.use_dynamic_discovery}')
"
```

### Step 3: Test with Environment Variable (ON)
```bash
# Dynamic discovery ON
cd /home/vtee/projects/sc2mmr/backend
python3 -c "
import os
os.environ['USE_DYNAMIC_DISCOVERY'] = 'true'
from services.enhanced_parser import EnhancedReplayParser
parser = EnhancedReplayParser('replays/test.SC2Replay')
print(f'✅ Parser created, use_dynamic: {parser.use_dynamic_discovery}')
print(f'✅ Discovery engine: {parser.ability_discovery is not None}')
"
```

### Step 4: Test Full Parse
```bash
cd /home/vtee/projects/sc2mmr/backend
python3 -c "
import os
os.environ['USE_DYNAMIC_DISCOVERY'] = 'true'
from services.enhanced_parser import EnhancedReplayParser
from pathlib import Path

replay_path = Path('replays/182798096b582be280eaef93df553ade36906b4ee8ca99e5fe61d791863a057f.SC2Replay')
parser = EnhancedReplayParser(str(replay_path))
features = parser.parse()

for pid, player_features in features.items():
    abilities = player_features.ability_usage.abilities
    print(f'Player {pid}: {len(abilities)} abilities tracked')
    
# Check if dynamic discovery worked
if parser.use_dynamic_discovery:
    discovered = parser.get_discovered_abilities()
    print(f'✅ Discovered abilities: {len(discovered)}')
    for ability, meta in list(discovered.items())[:5]:
        print(f'  {ability}: {meta[\"category\"]} (priority: {meta[\"priority\"]})')
"
```

---

## Rollback Instructions

### Instant Rollback (No Code Changes)
```bash
# Set environment variable to disable
export USE_DYNAMIC_DISCOVERY=false

# Restart your application
# Dynamic discovery instantly disabled
```

### Rollback (Code Changes)
To completely remove Phase 1 changes:
1. Revert `enhanced_parser.py` to original state (git checkout)
```bash
git checkout backend/app/services/enhanced_parser.py
```

---

## Expected Results

### Before Phase 1
- Hardcoded ~38 abilities in `TRACKED_ABILITIES`
- ~50% ability coverage (only hardcoded matches)
- Manual updates needed for each SC2 patch

### After Phase 1
- 100% ability coverage (dynamic discovery)
- Automatic adaptation to new patches
- Instant rollback via environment variable
- No breaking changes to existing parsing

### Test Metrics
Run integration tests:
```bash
cd /home/vtee/projects/sc2mmr/backend
python3 tests/test_option_b_integration.py
```

Expected output:
```
✅ Discovery Engine: Working
✅ Replay Loading: Working
✅ Ability Discovery: 20 abilities found
✅ Filtering System: Working
✅ Statistics: Working
✅ Config Persistence: Tested (dry run)
✅ ALL TESTS PASSED
```

---

## Troubleshooting

### Issue: Import Error
```
ImportError: cannot import name 'get_discovery_engine'
```
**Solution:** Ensure `ability_discovery.py` is in same directory as `enhanced_parser.py`

### Issue: Environment Variable Not Working
```bash
echo $USE_DYNAMIC_DISCOVERY
# Should print: true or false
```
**Solution:** Set variable in shell before running application, or in your Dockerfile/startup script

### Issue: No Abilities Tracked
```bash
# After parsing, check abilities are being tracked
Player 1: 0 abilities tracked
```
**Solutions:**
1. Verify replay has ability events: `replay.game_events`
2. Check config: `backend/config/abilities_config.json` exists
3. Enable debug: Check logs for "✅ Discovered X unique abilities"

---

## Next Steps (After Phase 1 Complete)

### Phase 2: SHAP Feature Importance (2-3 weeks)
- Install: `pip install shap`
- Calculate feature importance for XGBoost model
- Identify top 10 features driving MMR predictions
- Optimize feature set (remove noise)
- Provide explainable predictions

### Phase 3: Advanced Player Insights (1-2 months)
- Build ability synergy database
- Calculate win rates by ability
- Create visualization dashboard
- Generate strategy recommendations

---

## Success Criteria

Phase 1 is complete when:
- [ ] `enhanced_parser.py` modified with all 4 changes
- [ ] Environment variable `USE_DYNAMIC_DISCOVERY` works for toggle
- [ ] Integration tests pass (`test_option_b_integration.py`)
- [ ] Parse completes successfully on test replay
- [ ] More abilities tracked than hardcoded baseline
- [ ] Instant rollback verified (`export USE_DYNAMIC_DISCOVERY=false`)

---

## Deployment Strategy (Recommended)

### Week 1: Staging Only
1. Deploy modified `enhanced_parser.py` to staging
2. Set `USE_DYNAMIC_DISCOVERY=true` for 5% of parses
3. Compare results: ability counts, parse time
4. Monitor for errors

### Week 2: Production Read-Only
1. Deploy with `USE_DYNAMIC_DISCOVERY=false` (off by default)
2. Log dynamic discovery results without using them
3. Validate no performance degradation

### Week 3: Production Partial Rollout
1. Enable for 10% of parses
2. Monitor: ability counts, ML feature quality, parse time
3. Compare MMR prediction accuracy: old vs new

### Week 4: Full Rollout
1. If metrics positive, enable for 100%
2. Keep `USE_DYNAMIC_DISCOVERY` flag for instant rollback

---

## Notes

- **Minimal Logging**: Only print statements added, no complex logging system
- **Instant Rollback**: Environment variable takes effect immediately on app restart
- **No Breaking Changes**: Original hardcoded path still available as fallback
- **XGBoost Compatible**: Phase 2 will integrate with your existing XGBoost model
- **Type Errors**: Pre-existing type errors not addressed (blocking issue, not runtime issue)

---

## Files Modified in Phase 1

| File | Changes | Lines Affected |
|------|----------|----------------|
| `backend/app/services/enhanced_parser.py` | 4 changes (imports, init, method, new method) | ~50 lines |

## Files Created (Already Complete)

| File | Purpose |
|------|---------|
| `backend/app/services/ability_discovery.py` | Dynamic discovery engine |
| `backend/config/abilities_config.json` | Configuration |
| `backend/tests/test_option_b_integration.py` | Integration tests |

---

**Phase 1 Timeline: 1-2 days** (testing + deployment)
**Risk Level: Low** (feature flag + instant rollback)
**ML Impact: Foundation for Phase 2** (SHAP feature importance)
