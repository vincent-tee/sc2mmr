#!/usr/bin/env python3
"""
Bulk upload all SC2 replays from a directory.
Usage: python upload_all_replays.py /path/to/replays/
"""

import os
import sys
import time
import requests
from pathlib import Path

API_URL = "http://localhost:8000/replays/upload-advanced"

def upload_replay(file_path: str) -> dict:
    """Upload a single replay file."""
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
        response = requests.post(API_URL, files=files)
        return {
            'status_code': response.status_code,
            'response': response.json() if response.status_code in [200, 400, 409] else response.text
        }

def main():
    replay_dir = sys.argv[1] if len(sys.argv) > 1 else "/mnt/c/Users/tru_n/Documents/StarCraft II/Accounts/396750040/1-S2-1-11883598/Replays/Multiplayer"

    # Find all replay files
    replay_path = Path(replay_dir)
    replays = list(replay_path.glob("*.SC2Replay"))

    print(f"Found {len(replays)} replay files in {replay_dir}")
    print("=" * 60)

    success = 0
    duplicates = 0
    failed = 0
    errors = []

    for i, replay in enumerate(replays, 1):
        print(f"[{i}/{len(replays)}] Uploading: {replay.name}...", end=" ", flush=True)

        try:
            result = upload_replay(str(replay))

            if result['status_code'] == 200:
                match_id = result['response'].get('match_id', '?')
                print(f"✅ Match #{match_id}")
                success += 1
            elif result['status_code'] == 409:
                print(f"⏭️  Duplicate (skipped)")
                duplicates += 1
            else:
                error_msg = result['response'].get('detail', str(result['response']))[:50]
                print(f"❌ {error_msg}")
                failed += 1
                errors.append({'file': replay.name, 'error': error_msg})

        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            failed += 1
            errors.append({'file': replay.name, 'error': str(e)})

        # Small delay to avoid overwhelming server
        time.sleep(0.1)

    print("\n" + "=" * 60)
    print(f"UPLOAD COMPLETE")
    print(f"  ✅ Success:    {success}")
    print(f"  ⏭️  Duplicates: {duplicates}")
    print(f"  ❌ Failed:     {failed}")
    print(f"  📊 Total:      {len(replays)}")

    if errors:
        print(f"\nFailed uploads:")
        for err in errors[:10]:
            print(f"  - {err['file']}: {err['error']}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

if __name__ == "__main__":
    main()
