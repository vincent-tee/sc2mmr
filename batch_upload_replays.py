#!/usr/bin/env python3
"""
Batch upload SC2 replay files to the MMR tracker.
Usage: python batch_upload_replays.py <directory>
"""
import sys
import os
import requests
from pathlib import Path
import time


def upload_replay(file_path: str, api_url: str = "http://localhost:8000/replays/upload") -> dict:
    """Upload a single replay file."""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
            response = requests.post(api_url, files=files, timeout=30)

        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        elif response.status_code == 409:
            return {'success': False, 'error': 'duplicate', 'message': 'Duplicate replay'}
        else:
            return {'success': False, 'error': 'failed', 'message': response.json().get('detail', 'Unknown error')}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'connection', 'message': 'Cannot connect to backend. Is it running?'}
    except Exception as e:
        return {'success': False, 'error': 'exception', 'message': str(e)}


def batch_upload(directory: str, delay_seconds: float = 0.5):
    """Upload all replay files in a directory."""
    replay_dir = Path(directory)

    if not replay_dir.exists():
        print(f"✗ Directory not found: {directory}")
        return

    # Find all .SC2Replay files
    replay_files = list(replay_dir.glob("*.SC2Replay"))

    if not replay_files:
        print(f"✗ No .SC2Replay files found in {directory}")
        return

    print(f"Found {len(replay_files)} replay file(s)")
    print("=" * 60)

    # Check if backend is running
    try:
        requests.get("http://localhost:8000", timeout=2)
    except:
        print("⚠️  WARNING: Cannot connect to backend at http://localhost:8000")
        print("   Make sure the backend is running:")
        print("   cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            return

    # Upload each replay
    results = {
        'success': 0,
        'duplicate': 0,
        'failed': 0,
        'errors': []
    }

    for i, replay_file in enumerate(replay_files, 1):
        filename = replay_file.name
        print(f"[{i}/{len(replay_files)}] Uploading {filename[:50]}...", end=' ')

        result = upload_replay(str(replay_file))

        if result['success']:
            print("✓ Success")
            results['success'] += 1
        elif result.get('error') == 'duplicate':
            print("⊘ Duplicate")
            results['duplicate'] += 1
        elif result.get('error') == 'connection':
            print(f"✗ Connection Error")
            print(f"   {result['message']}")
            break
        else:
            print(f"✗ Failed")
            error_msg = result.get('message', 'Unknown error')
            # Truncate long error messages
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            print(f"   {error_msg}")
            results['failed'] += 1
            results['errors'].append({'file': filename, 'error': error_msg})

        # Small delay to avoid overwhelming the server
        if i < len(replay_files):
            time.sleep(delay_seconds)

    # Print summary
    print("")
    print("=" * 60)
    print("Upload Summary:")
    print(f"  ✓ Successful: {results['success']}")
    print(f"  ⊘ Duplicates: {results['duplicate']}")
    print(f"  ✗ Failed: {results['failed']}")
    print("")

    if results['errors']:
        print("Failed uploads (check Failed Uploads page for details):")
        for error in results['errors'][:5]:
            print(f"  - {error['file']}")
            print(f"    {error['error']}")
        if len(results['errors']) > 5:
            print(f"  ... and {len(results['errors']) - 5} more")


def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_upload_replays.py <directory>")
        print("")
        print("Examples:")
        print("  python batch_upload_replays.py ~/sc2_replays")
        print("  python batch_upload_replays.py /mnt/c/Users/YourName/Documents/StarCraft\\ II/Accounts/.../Replays/Multiplayer")
        sys.exit(1)

    directory = sys.argv[1]
    batch_upload(directory)


if __name__ == "__main__":
    main()
