#!/usr/bin/env python3
"""
Simple CLI for parsing SC2 replays using PyCommandCenter.

Usage:
    python parse_replay.py /path/to/replay.SC2Replay [num_players]

Outputs JSON with player metrics to stdout.
"""

import json
import sys
import os

# Add lib to path
sys.path.insert(0, "/app/lib")
sys.path.insert(0, "/app")

from app.services.commandcenter_parser import CommandCenterParser


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_replay.py <replay_path> [num_players]", file=sys.stderr)
        sys.exit(1)

    replay_path = sys.argv[1]
    num_players = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    if not os.path.exists(replay_path):
        print(f"Error: Replay not found: {replay_path}", file=sys.stderr)
        sys.exit(1)

    try:
        parser = CommandCenterParser()
        metrics = parser.parse_replay(replay_path, num_players=num_players)

        # Output JSON
        print(json.dumps(metrics, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
