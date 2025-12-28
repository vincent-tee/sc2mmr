# Phase 1 Checklist

Copy this checklist and mark items as you complete them.

## Implementation

- [ ] **Step 1:** Add import statements to `enhanced_parser.py`
  - [ ] Add `import os`
  - [ ] Add dynamic discovery import with try/except
  - [ ] Test import works

- [ ] **Step 2:** Update `__init__` method
  - [ ] Add feature flag check (`USE_DYNAMIC_DISCOVERY`)
  - [ ] Initialize discovery engine if enabled
  - [ ] Add logging for enable/disable state
  - [ ] Test both modes (enabled/disabled)

- [ ] **Step 3:** Replace `_extract_ability_usage` method
  - [ ] Add fallback path (original code)
  - [ ] Add dynamic discovery path
  - [ ] Apply discovery filters
  - [ ] Test ability tracking increases

- [ ] **Step 4:** Add `get_discovered_abilities` method
  - [ ] Export metadata (category, priority, usage)
  - [ ] Return empty dict if disabled
  - [ ] Test metadata export

## Testing

- [ ] **Test 1:** Verify import works
  - [ ] Run: `python3 -c "from ability_discovery import get_discovery_engine; print('OK')"`
  - [ ] Result: ✅ OK

- [ ] **Test 2:** Baseline mode (disabled)
  - [ ] Set: `export USE_DYNAMIC_DISCOVERY=false`
  - [ ] Run: `python3 app/main.py`
  - [ ] Verify: Uses hardcoded tracking
  - [ ] Result: ✅ Works

- [ ] **Test 3:** Dynamic mode (enabled)
  - [ ] Set: `export USE_DYNAMIC_DISCOVERY=true`
  - [ ] Run: `python3 app/main.py`
  - [ ] Verify: Uses dynamic discovery
  - [ ] Verify: More abilities tracked than baseline
  - [ ] Result: ✅ Works

- [ ] **Test 4:** Integration tests
  - [ ] Run: `python3 tests/test_option_b_integration.py`
  - [ ] Verify: All tests pass
  - [ ] Result: ✅ All pass

## Deployment

- [ ] Deploy to staging environment
- [ ] Monitor for 24-48 hours
- [ ] Check metrics (ability coverage, parse time, errors)
- [ ] No issues found in monitoring

- [ ] Get approval for production
- [ ] Deploy to production (read-only mode first)

## Rollback Verification

- [ ] Test rollback: `export USE_DYNAMIC_DISCOVERY=false`
- [ ] Verify instant effect (no restart needed)
- [ ] Test rollback: `git checkout backend/app/services/enhanced_parser.py`
- [ ] Both rollback methods work

## Success Criteria

- [ ] All 4 code changes complete
- [ ] All 4 tests pass
- [ ] Ability coverage > baseline
- [ ] Parse time increase < 10%
- [ ] Instant rollback verified
- [ ] Ready for Phase 2 (SHAP)

## Notes

**Baseline Ability Count:** ___ abilities (hardcoded)
**Dynamic Ability Count:** ___ abilities (discovered)
**Coverage Improvement:** ___%

**Baseline Parse Time:** ___ seconds
**Dynamic Parse Time:** ___ seconds
**Parse Time Impact:** ___%

---

**Phase 1 Complete:** [ ] YES / [ ] NO

**Issues Encountered:**
1.
2.
3.

**Solutions Applied:**
1.
2.
3.

---

**Ready for Phase 2?** [ ] YES / [ ] NO
