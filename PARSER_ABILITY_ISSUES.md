# SC2 Parser: Ability Tracking Analysis

## Problem Identified: Hardcoded Ability List is Fundamentally Flawed

### Current Approach (Option A - Partial Fix)
- Hardcoded `TRACKED_ABILITIES` with ~38 ability names
- Assumes abilities are named like: "PsionicStorm", "Blink", "Stimpack"

### Actual Replay Reality
Replays use ability names with these patterns:
- `Train[Name]` - TrainMarine, TrainZealot, TrainSCV (200+ uses/replay)
- `Build[Name]` - BuildBarracks, BuildNexus, BuildGateway (100+ uses/replay)
- `Research[Name]` - ResearchWarpGate, ResearchCombatShield
- `WarpIn[Name]` - WarpInZealot (6+ uses/replay)
- `NexusMassRecall` - Not "EnergyRecharge"
- `Attack` - 153 uses (ALL units have basic attack command)

### Critical Issues

1. **Name Mismatch**: "PsionicStorm" in TRACKED_ABILITIES ≠ actual replay format
2. **False Positives**: 38 abilities "tracked" but 0 actual matches
3. **Coverage Gap**: 77 actual abilities in replay, only ~38 "tracked" (~50% loss)
4. **Noise**: "Attack" counted 153 times (not meaningful for skill assessment)
5. **Not Future-Proof**: Next patch breaks ability naming again

### Evidence from Test Replay
```
Player 1: 0 tracked abilities / 77 actual abilities (0% coverage)
Player 2: 0 tracked abilities / 77 actual abilities (0% coverage)
Player 3: 0 tracked abilities / 77 actual abilities (0% coverage)
...
```

All 6 new 5.0.14/5.0.15 abilities show "0 uses" because:
- "EnergyRecharge" ≠ "NexusMassRecall" (actual ability)
- "GuardianShield" ≠ "ResearchCombatShield" (actual ability)
- "TimeWarp" ≠ "ResearchWarpGate" (actual ability)
- "MicrobialShroud" not found in this replay
- "CentrifugalHooks" not found in this replay
