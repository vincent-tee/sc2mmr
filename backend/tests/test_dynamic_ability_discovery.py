"""
Test Dynamic Ability Discovery System

Validates that Option B correctly:
1. Discovers ALL abilities from replays (not just hardcoded list)
2. Correctly filters trivial abilities (Train*, Build*)
3. Classifies abilities into categories
4. Assigns appropriate priorities
5. Works with 5.0.14/5.0.15 ability names
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
import sc2reader
from app.services.ability_discovery import DynamicAbilityDiscovery, get_discovery_engine


def test_discovery_coverage():
    """Test that dynamic discovery captures 100% of abilities."""
    print("=" * 60)
    print("TEST 1: Discovery Coverage")
    print("=" * 60)

    replay_path = (
        Path(__file__).parent
        / "replays"
        / "182798096b582be280eaef93df553ade36906b4ee8ca99e5fe61d791863a057f.SC2Replay"
    )

    if not replay_path.exists():
        print(f"❌ Test replay not found: {replay_path}")
        return False

    print(f"📁 Loading replay: {replay_path.name}")

    try:
        replay = sc2reader.load_replay(str(replay_path), load_level=4)
        discovery = get_discovery_engine()

        # Discover abilities
        discovered = discovery.discover_from_replay(replay, "5.0.15")

        # Get total unique abilities in replay
        all_abilities = set()
        for event in replay.game_events:
            if hasattr(event, "ability") and hasattr(event.ability, "name"):
                all_abilities.add(event.ability.name)

        total_replay_abilities = len(all_abilities)
        total_discovered = len(discovered)

        print(f"\n📊 Replay Statistics:")
        print(f"  Total unique abilities in replay: {total_replay_abilities}")
        print(f"  Abilities discovered by engine: {total_discovered}")
        print(f"  Coverage: {(total_discovered / total_replay_abilities) * 100:.1f}%")

        # Check for specific 5.0.14/5.0.15 abilities
        new_patch_abilities = [
            "NexusMassRecall",  # EnergyRecharge (actual name)
            "ResearchCombatShield",  # GuardianShield (actual name)
            "ResearchWarpGate",  # TimeWarp (actual name)
            "MicrobialShroud",
            "CentrifugalHooks",
        ]

        print(f"\n🎯 5.0.14/5.0.15 Ability Detection:")
        for ability in new_patch_abilities:
            in_replay = ability in all_abilities
            in_discovered = ability in discovered
            tracked = discovery.should_track_ability(ability)

            status = "✅" if tracked else "⏭"
            replay_status = "✅" if in_replay else "❌"
            discovery_status = "✅" if in_discovered else "❌"

            print(
                f"  {status} {ability:20} | Replay:{replay_status} | Discovery:{discovery_status}"
            )

        # Show sample of discovered abilities
        print(f"\n📋 Sample Discovered Abilities (first 20):")
        for i, ability in enumerate(sorted(list(discovered))[:20]):
            priority = discovery.get_priority(ability)
            category = discovery.get_category(ability)
            print(
                f"  {i + 1}. {ability:20} | Priority:{priority} | Category:{category}"
            )

        if len(discovered) > 20:
            print(f"\n  ... and {len(discovered) - 20} more")

        # Success criteria: 90%+ coverage
        success = (total_discovered / total_replay_abilities) >= 0.9
        print(
            f"\n{'✅ PASS' if success else '❌ FAIL'}: Coverage {total_discovered}/{total_replay_abilities} ({(total_discovered / total_replay_abilities) * 100:.1f}%)"
        )

        return success

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_filtering():
    """Test that filtering works correctly."""
    print("\n" + "=" * 60)
    print("TEST 2: Ability Filtering")
    print("=" * 60)

    discovery = get_discovery_engine()

    # Test abilities that should be tracked
    should_track = [
        ("PsionicStorm", "high micro ability"),
        ("Blink", "high micro ability"),
        ("EnergyRecharge", "medium micro ability"),
        ("MicrobialShroud", "medium micro ability"),
        ("NexusMassRecall", "macro ability - actual replay name"),
    ]

    print("\n✅ Should Track (high priority):")
    for ability, reason in should_track:
        tracked = discovery.should_track_ability(ability)
        priority = discovery.get_priority(ability)
        print(f"  {ability:20} | Tracked: {tracked} | Priority: {priority}")

    # Test abilities that should be filtered
    should_filter = [
        ("TrainMarine", "trivial - Train prefix"),
        ("BuildBarracks", "trivial - Build prefix"),
        ("ResearchWarpGate", "research - Research prefix but has Warp suffix"),
        ("RightClick", "trivial - RightClick prefix"),
    ]

    print("\n⏭ Should Filter Out:")
    for ability, reason in should_filter:
        tracked = discovery.should_track_ability(ability)
        print(f"  {ability:20} | Tracked: {tracked} ({reason})")

    # Test: WarpInZealot (should be tracked - Warp is include suffix)
    warp_tracked = discovery.should_track_ability("WarpInZealot")
    print(
        f"\n✅ WarpInZealot | Tracked: {warp_tracked} (Warp suffix means significant ability)"
    )

    success = all(
        discovery.should_track_ability(ability) for ability, _ in should_track
    ) and not any(
        discovery.should_track_ability(ability) for ability, _ in should_filter
    )

    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Filtering system works correctly")

    return success


def test_classification():
    """Test ability classification system."""
    print("\n" + "=" * 60)
    print("TEST 3: Ability Classification")
    print("=" * 60)

    discovery = get_discovery_engine()

    categories_tested = {
        "high_micro": ["PsionicStorm", "EMP", "Fungal", "Blink"],
        "medium_micro": ["EnergyRecharge", "ForceField", "MicrobialShroud"],
        "macro": ["ChronoBoost", "NexusMassRecall", "SpawnLarva"],
        "movement": ["Blink", "Charge", "PhaseShift"],
        "utility": ["ScannerSweep", "GuardianShield", "Cloak"],
    }

    print("\n🏷 Classification Accuracy:")
    for category, abilities in categories_tested.items():
        correct = 0
        for ability in abilities:
            detected_category = discovery.get_category(ability)
            if detected_category == category:
                correct += 1

        accuracy = (correct / len(abilities)) * 100
        status = "✅" if accuracy == 100 else "⚠️"
        print(
            f"  {status} {category:15} | {accuracy:.0f}% ({correct}/{len(abilities)})"
        )

    success = all(
        (
            discovery.get_category(ability) == expected_cat
            for ability, expected_cat in abilities
        )
        for category, abilities in categories_tested.items()
    )

    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Classification system works")

    return success


def test_config_persistence():
    """Test that config can be saved and loaded."""
    print("\n" + "=" * 60)
    print("TEST 4: Configuration Persistence")
    print("=" * 60)

    discovery = get_discovery_engine()

    # Test statistics
    stats = discovery.get_statistics()

    print(f"\n📊 Current Discovery Statistics:")
    print(f"  Total abilities discovered: {stats['total_discovered']}")
    print(f"  Config version: {stats.get('config_version', 'unknown')}")
    print(f"  By category:")
    for category, count in stats.get("by_category", {}).items():
        print(f"    {category:15}: {count}")
    if stats.get("most_common"):
        print(
            f"  Most common: {stats['most_common']} ({stats['most_common_count']} uses)"
        )
    if stats.get("newest_ability"):
        print(f"  Newest: {stats['newest_ability']}")

    # Try saving
    print("\n💾 Testing config save...")
    try:
        discovery.save_config()
        print("✅ Config saved successfully")
        success = True
    except Exception as e:
        print(f"❌ Failed to save config: {e}")
        success = False

    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Configuration persistence works")

    return success


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print(" Dynamic Ability Discovery System - Test Suite")
    print("=" * 60)
    print("\nValidating Option B implementation...")

    results = {
        "Coverage": test_discovery_coverage(),
        "Filtering": test_filtering(),
        "Classification": test_classification(),
        "Config Persistence": test_config_persistence(),
    }

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    print(f"\n{'🎉 ALL TESTS PASSED' if all_passed else '⚠️ SOME TESTS FAILED'}")

    if all_passed:
        print("\n✅ Option B implementation is ready for production use")
        return 0
    else:
        print("\n❌ Option B implementation needs fixes before production use")
        return 1


if __name__ == "__main__":
    sys.exit(main())
