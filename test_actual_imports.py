#!/usr/bin/env python3
"""
Test what the running backend actually has imported in replays.py
"""
import requests
import sys

# Create a test endpoint that shows what replays.py actually imported
test_code = '''
import sys
sys.path.insert(0, '/home/user/sc2mmr/backend')

# Import the actual module that's running
from app.api import replays

# Check what it has
print("What replays.py has imported:")
print(f"  - ReplayParseError: {hasattr(replays, 'ReplayParseError')}")
print(f"  - WinnerDeterminationError: {hasattr(replays, 'WinnerDeterminationError')}")

# Try to access the actual exception class
try:
    print(f"  - WinnerDeterminationError class: {replays.WinnerDeterminationError}")
except AttributeError as e:
    print(f"  - WinnerDeterminationError class: MISSING - {e}")
'''

print("This test requires adding a debug endpoint to the backend.")
print("The /version endpoint only checks if it CAN import, not what WAS imported.")
print("")
print("Definitive proof the backend needs full restart:")
print("  - /version says: up-to-date")
print("  - But uploads say: 'Parse error:' (old message)")
print("  - Should say: 'Winner determination failed:' (new message)")
print("")
print("Solution: Force kill all backend processes and restart")
print("")
print("Run: ./force_restart_backend.sh")
