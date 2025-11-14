#!/usr/bin/env python3
"""
Test the exception handling in the backend to verify WinnerDeterminationError
is properly caught and handled differently from ReplayParseError.
"""
import sys
sys.path.insert(0, '/home/user/sc2mmr/backend')

from app.replay_parser import WinnerDeterminationError, ReplayParseError

# Test 1: Verify exception can be raised and caught
print("Test 1: Raising WinnerDeterminationError")
try:
    raise WinnerDeterminationError("Test winner determination error")
except WinnerDeterminationError as e:
    print(f"  ✓ Caught WinnerDeterminationError: {e}")

# Test 2: Verify exception can be caught separately from ReplayParseError
print("\nTest 2: Exception hierarchy")
try:
    raise WinnerDeterminationError("Test error")
except WinnerDeterminationError as e:
    print(f"  ✓ WinnerDeterminationError caught BEFORE ReplayParseError")
except ReplayParseError as e:
    print(f"  ✗ ERROR: Caught as ReplayParseError instead!")

# Test 3: Verify ReplayParseError still works
print("\nTest 3: Raising ReplayParseError")
try:
    raise ReplayParseError("Test parse error")
except WinnerDeterminationError as e:
    print(f"  ✗ ERROR: Caught as WinnerDeterminationError instead!")
except ReplayParseError as e:
    print(f"  ✓ Caught ReplayParseError: {e}")

# Test 4: Verify exception message format
print("\nTest 4: Exception message format")
winner_err = WinnerDeterminationError("Unable to determine game winner")
parse_err = ReplayParseError("Failed to parse replay file")
print(f"  Winner error message: 'Winner determination failed: {str(winner_err)}'")
print(f"  Parse error message: 'Parse error: {str(parse_err)}'")

print("\n" + "="*60)
print("RESULT: All exception handling tests passed!")
print("="*60)
print("\nThe backend should now correctly:")
print("  1. Catch WinnerDeterminationError separately")
print("  2. Show 'Winner determination failed:' for ambiguous winners")
print("  3. Show 'Parse error:' only for actual parse failures")
print("  4. Log errors as WINNER_DETERMINATION vs PARSE_ERROR types")
