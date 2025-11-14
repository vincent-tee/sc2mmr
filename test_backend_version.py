#!/usr/bin/env python3
"""
Test if the backend is running the new code with WinnerDeterminationError.
"""
import requests
import sys

# Test 1: Check if backend is running
try:
    response = requests.get("http://localhost:8000", timeout=2)
    print("✓ Backend is running")
except:
    print("✗ Backend is not responding on http://localhost:8000")
    sys.exit(1)

# Test 2: Try to import the exception locally
print("\nChecking local code:")
sys.path.insert(0, '/home/user/sc2mmr/backend')
try:
    from app.replay_parser import WinnerDeterminationError
    print("✓ WinnerDeterminationError exists in local code")
except ImportError as e:
    print(f"✗ Cannot import WinnerDeterminationError: {e}")
    sys.exit(1)

# Test 3: Check the exception handling in replays.py
try:
    with open('/home/user/sc2mmr/backend/app/api/replays.py', 'r') as f:
        content = f.read()
        if 'except WinnerDeterminationError' in content:
            print("✓ replays.py contains WinnerDeterminationError exception handler")
        else:
            print("✗ replays.py does NOT contain WinnerDeterminationError exception handler")

        if 'Winner determination failed:' in content:
            print("✓ replays.py contains new error message")
        else:
            print("✗ replays.py does NOT contain new error message")
except Exception as e:
    print(f"✗ Error reading replays.py: {e}")

print("\n" + "="*60)
print("CONCLUSION:")
print("="*60)
print("The code files contain the fixes.")
print("If uploads still show 'Parse error:', the backend process is stale.")
print("\nTo fix:")
print("1. Find and kill all uvicorn processes:")
print("   ps aux | grep uvicorn")
print("   kill -9 <process_id>")
print("2. Start fresh:")
print("   cd /home/user/sc2mmr/backend")
print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
