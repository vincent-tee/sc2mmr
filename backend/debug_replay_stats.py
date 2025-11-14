#!/usr/bin/env python3
"""
Debug script to test stats extraction from a single replay file.
Usage: python3 debug_replay_stats.py /path/to/replay.SC2Replay
"""
import sys
import sc2reader

if len(sys.argv) < 2:
    print("Usage: python3 debug_replay_stats.py /path/to/replay.SC2Replay")
    sys.exit(1)

replay_path = sys.argv[1]

print(f"Loading replay: {replay_path}")
print(f"SC2Reader version: {sc2reader.__version__ if hasattr(sc2reader, '__version__') else 'unknown'}")
print()

# Load replay with full stats (level 4)
replay = sc2reader.load_replay(replay_path, load_level=4)

print(f"Game length: {replay.game_length}")
print(f"Map: {replay.map_name}")
print(f"Players: {len(replay.players)}")
print()

# Check each human player
for p in replay.players:
    if not p.is_human:
        continue

    print(f"\n{'='*60}")
    print(f"Player: {p.name} (Team {p.team_id})")
    print(f"Result: {p.result}")
    print(f"Has stats: {hasattr(p, 'stats') and p.stats is not None}")

    if hasattr(p, 'stats') and p.stats:
        print(f"\nAvailable stat attributes:")
        stats_attrs = [attr for attr in dir(p.stats) if not attr.startswith('_')]
        for attr in sorted(stats_attrs):
            val = getattr(p.stats, attr, None)
            if isinstance(val, list):
                print(f"  {attr}: list with {len(val)} entries")
                if len(val) > 0:
                    print(f"    First: {val[0]}, Last: {val[-1]}")
            else:
                print(f"  {attr}: {val}")

        # Try to extract stats
        print(f"\nExtracted stats:")

        # Supply
        supply = 0
        if hasattr(p.stats, 'food_used') and p.stats.food_used:
            if isinstance(p.stats.food_used, list) and len(p.stats.food_used) > 0:
                supply = p.stats.food_used[-1]
        print(f"  Supply (food_used): {supply}")

        # Resources
        minerals = 0
        vespene = 0
        if hasattr(p.stats, 'minerals_collection_rate') and p.stats.minerals_collection_rate:
            if isinstance(p.stats.minerals_collection_rate, list) and len(p.stats.minerals_collection_rate) > 0:
                minerals = int(p.stats.minerals_collection_rate[-1])
        if hasattr(p.stats, 'vespene_collection_rate') and p.stats.vespene_collection_rate:
            if isinstance(p.stats.vespene_collection_rate, list) and len(p.stats.vespene_collection_rate) > 0:
                vespene = int(p.stats.vespene_collection_rate[-1])

        print(f"  Minerals: {minerals:,}")
        print(f"  Vespene: {vespene:,}")
        print(f"  Total Resources: {minerals + vespene:,}")
    else:
        print(f"  WARNING: No stats available for this player!")

print(f"\n{'='*60}")
print("If all stats are 0, the replay file may:")
print("1. Be corrupted or incomplete")
print("2. Be from a very old SC2 version")
print("3. Not have stats data for some other reason")
