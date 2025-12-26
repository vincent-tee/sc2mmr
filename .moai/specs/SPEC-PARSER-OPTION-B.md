# SPEC: SC2 Replay Parser - Dynamic Ability Discovery (Option B)

## Status
**Type**: Implementation Plan  
**Created**: 2025-01-XX  
**Priority**: HIGH (parser fix needed)  
**Related**: Issues with missing abilities in patches 5.0.14/5.0.15

---

## Problem Statement

### Current Situation
- Parser uses hardcoded `TRACKED_ABILITIES` dictionary (~38 abilities)
- Cannot track abilities introduced in new SC2 patches
- Hardcoded names don't match actual ability format in replays
- **Coverage**: ~0-38 tracked abilities out of 77 actual (~50% loss)
- **Future-proof**: NO - requires manual updates for each patch

### Root Cause
1. **Ability Name Mismatch**: 
   - Expected: `"PsionicStorm"`, `"EnergyRecharge"`
   - Actual: `"NexusMassRecall"`, `"ResearchCombatShield"`, `"ResearchWarpGate"`
   
2. **Pattern Ignorance**:
   - Abilities follow patterns: `Train*`, `Build*`, `Research*`, `WarpIn*`, `Upgrade*`
   - Current hardcoded list cannot anticipate new patterns

3. **False Coverage Illusion**:
   - Parser reports "38 abilities tracked" but 0 actual matches
   - Gives false sense of ability tracking working

---

## Solution: Dynamic Ability Discovery

### Architecture

```
Enhanced Parser
├── Auto-Discovery Engine
│   ├── Discover ALL abilities from replays (no hardcoded list)
│   ├── Build ability database over time (learn from parsed games)
│   └── Generate ability config file
├── Priority System
│   ├── Load from external config (abilities_config.json)
│   ├── Auto-infer priority for unknown abilities
│   └── Support ability category classification
└── Fallback to sc2reader
    ├── Keep current parser for basic replay info
    └── Use dynamic discovery for ability-specific features
```

### Data Flow

```
1. Parse Replay
   ↓
2. Discover ALL abilities (game_events loop)
   ↓
3. Check each ability:
   ├─ In config.json? → Use configured priority
   ├─ New ability? → Infer priority from patterns
   └─ Trivial ability? (Train*, Build*) → Filter/skip
   ↓
4. Build ability usage metrics:
   ├─ Total abilities per player
   ├─ Abilities per minute
   ├─ Priority-weighted score
   └─ Category breakdown (micro, macro, utility)
   ↓
5. Save to database + update learned_abilities.json
```

---

## Implementation Plan

### Phase 1: Discovery Engine (Day 1-2)

**File**: `backend/app/services/enhanced_parser_v2.py` (new file)

```python
class DynamicAbilityDiscovery:
    """Auto-discover and classify abilities from replays."""
    
    def __init__(self):
        self.discovered_abilities = set()
        self.ability_patterns = self._load_patterns()
        
    def discover_from_replay(self, replay):
        """Extract ALL unique abilities from replay."""
        for event in replay.game_events:
            if hasattr(event, 'ability'):
                self.discovered_abilities.add(event.ability.name)
        return self.discovered_abilities
    
    def _load_patterns(self):
        """Load ability classification patterns."""
        return {
            'high_micro': ['Storm', 'EMP', 'Fungal', 'Blink', 'Stim', 'Feedback'],
            'medium_micro': ['Recharge', 'ForceField', 'Transfusion', 'Abduct'],
            'macro': ['Chrono', 'SpawnLarva', 'MULE', 'Warp'],
            'movement': ['Blink', 'Charge', 'Speed', 'Jump', 'Recall'],
            'utility': ['Scan', 'Shield', 'Cloak', 'Decloak'],
        }
    
    def classify_ability(self, ability_name):
        """Auto-classify ability based on name patterns."""
        for category, keywords in self.ability_patterns.items():
            if any(kw in ability_name for kw in keywords):
                return category
        return 'unknown'
    
    def infer_priority(self, ability_name):
        """Assign priority score (1-10) for ML feature weighting."""
        category = self.classify_ability(ability_name)
        
        if category == 'high_micro':
            return 10
        elif category == 'medium_micro':
            return 7
        elif category == 'macro':
            return 5
        elif category == 'movement':
            return 6
        elif category == 'utility':
            return 4
        else:
            return 2  # Low priority
```

### Phase 2: Configuration System (Day 2)

**File**: `backend/config/abilities_config.json`

```json
{
  "version": "5.0.15",
  "last_updated": "2025-01-XX",
  "manual_overrides": {
    "PsionicStorm": 10,
    "Blink": 10,
    "Stimpack": 10
  },
  "filter_patterns": {
    "exclude_prefixes": ["Train", "Build", "Research", "Upgrade", "RightClick"],
    "include_suffixes": ["Execute", "Mode", "Boost", "Warp"]
  },
  "learned_abilities": {
    "NexusMassRecall": 8,
    "ResearchCombatShield": 6,
    "WarpInZealot": 7
  }
}
```

### Phase 3: Integration (Day 3-4)

**Modified Files**:
1. `backend/app/services/enhanced_parser.py`
   - Replace hardcoded `TRACKED_ABILITIES` with `DynamicAbilityDiscovery`
   - Update `_extract_ability_usage()` to use discovery engine
   - Add config file loading
   
2. `backend/app/database.py`
   - Add table: `learned_abilities` (ability_name, priority, category, usage_count)
   
3. `backend/app/api/replays.py`
   - Update response to include discovered abilities count
   - Add endpoint: `GET /api/abilities/discovered` (for monitoring)

### Phase 4: ML Feature Updates (Day 5)

**File**: `backend/app/services/enhanced_parser_v2.py`

```python
def calculate_micro_skill_score(self, player_features):
    """Calculate micro skill from ability usage patterns."""
    
    # Priority-weighted ability count
    weighted_sum = sum(
        count * priority 
        for ability, (count, priority) in player_features.ability_priorities.items()
    )
    
    # Normalized by game length
    minutes = player_features.game_length_seconds / 60.0
    micro_score = weighted_sum / max(minutes, 1)
    
    return micro_score

def extract_ability_categories(self, player_features):
    """Categorize abilities for ML model inputs."""
    
    categories = {
        'offensive_micro': 0,
        'defensive_micro': 0,
        'macro_abilities': 0,
        'movement': 0,
        'utility': 0,
    }
    
    for ability, category in player_features.ability_categories.items():
        categories[category] += 1
    
    return categories
```

---

## Migration Strategy

### Backward Compatibility
```python
# Keep old enhanced_parser for existing features
# Add enhanced_parser_v2.py for dynamic discovery
# Gradual migration:
# Week 1: Run both in parallel, compare outputs
# Week 2: Use v2 for new replays, keep v1 for historical
# Week 3: Full switch to v2
# Week 4: Deprecate v1
```

### Testing Plan

```bash
# Unit tests
pytest tests/test_dynamic_ability_discovery.py

# Integration test - parse 100 recent replays
python3 scripts/test_discovery_coverage.py \
  --replay-dir ./test_replays/5_0_15/ \
  --expected-coverage 0.95 \
  --output ./coverage_report.json

# Compare against baseline
python3 scripts/compare_parser_versions.py \
  --old backend/app/services/enhanced_parser.py \
  --new backend/app/services/enhanced_parser_v2.py \
  --replay ./test_replay.SC2Replay
```

---

## Expected Outcomes

### Quantitative Metrics
- **Ability Coverage**: 77/77 → 100% (up from 0%)
- **False Positive Rate**: 0% (no more "38 tracked" illusion)
- **Patch Adaptation Time**: 0 days (auto-discovery) vs 1-2 weeks (manual updates)

### Qualitative Benefits
- ✅ **Future-proof**: Automatically learns new abilities from each replay
- ✅ **Patch-ready**: No manual updates needed for 5.0.16, 6.0.0, etc.
- ✅ **Better ML features**: True ability diversity metrics
- ✅ **Maintainable**: External config, no code changes for updates
- ✅ **Debuggable**: Can see discovered abilities via API endpoint

---

## Risks & Mitigations

### Risk 1: Performance Impact
**Concern**: Scanning ALL abilities may slow parsing  
**Mitigation**: 
- Use set() for O(1) lookups
- Cache discovered abilities in memory
- Only scan game_events once per replay

### Risk 2: Noise in Data
**Concern**: Including "Train*", "Build*" abilities reduces signal  
**Mitigation**:
- Configurable filters in abilities_config.json
- ML model can learn to ignore low-signal features
- Separate "micro" vs "macro" categories

### Risk 3: Ability Name Changes
**Concern**: Blizzard may rename abilities in future patches  
**Mitigation**:
- Fuzzy matching on ability name
- Pattern-based classification (not exact match)
- Manual override in config.json when needed

---

## Dependencies

### Python Libraries (No new dependencies)
- `json` (built-in)
- `dataclasses` (built-in)
- `typing` (built-in)

### External Tools
- None (pure Python implementation)

---

## Success Criteria

- [ ] Phase 1: Discovery engine extracts 77+ abilities from test replay
- [ ] Phase 2: Config system loads and saves ability metadata
- [ ] Phase 3: Integration passes existing test suite
- [ ] Phase 4: ML features improve (lower validation error vs. baseline)
- [ ] Performance: Parse time increase < 10% vs. v1
- [ ] Coverage: 95%+ abilities tracked across patch versions
- [ ] Documentation: Update README with new approach

---

## Notes

**Why Not Just Fix Hardcoded List?**
- Root cause is hardcoded approach itself, not just missing 5.0.14 abilities
- Adding 5-6 new abilities today → same problem in 3-6 months
- Option B invests in solution that prevents recurring issue

**Why Not Switch Parser (s2protocol-rs)?**
- Correctly addresses ability tracking via dynamic discovery
- Lower migration cost vs. learning Rust
- Can implement Option B → later consider parser upgrade if needed
- Timeframe: 5-7 days (B) vs 2-3 weeks (parser switch)
