"""Tests for the 2026-09-15 replay metrics review fixes made to
UnifiedParser._process_tracker_events / _calculate_damage_metrics:

1. army_value_killed/lost must use only the *_army split of PlayerStatsEvent,
   not the army+economy+technology aggregate (`resources_killed`/`resources_lost`).
2. spending_efficiency must measure this player's own spend, not the sum of
   army value killed (opponent's loss) and lost (this player's own loss).
3. Unknown unit costs in UNIT_COSTS must be skipped from army_value_built,
   not silently guessed at 100.
4. total_resources_collected is documented as an estimate (four-bucket sum);
   this test locks in its current formula so a silent regression is caught.

Fake PlayerStatsEvent-like objects are built with SimpleNamespace, matching
the pattern used elsewhere in this test suite (see test_replay_clock.py).
"""
from types import SimpleNamespace

from app.services.unified_parser import UnifiedParser
from app.types.results import PlayerMatchResult
from app.models import Race


def _stats_event(pid=1, **overrides):
    """A PlayerStatsEvent-like object with every field the parser reads,
    defaulted to 0 so tests only need to set the fields they care about."""
    fields = dict(
        pid=pid,
        minerals_current=0,
        vespene_current=0,
        minerals_used_current=0,
        vespene_used_current=0,
        minerals_used_in_progress=0,
        vespene_used_in_progress=0,
        minerals_lost=0,
        vespene_lost=0,
        minerals_lost_army=0,
        vespene_lost_army=0,
        minerals_killed_army=0,
        vespene_killed_army=0,
        resources_lost=0,
        resources_killed=0,
        food_used=0,
        food_made=200,
    )
    fields.update(overrides)
    return SimpleNamespace(name="PlayerStatsEvent", **fields)


def _result(pid=1):
    return pid, PlayerMatchResult(name=f"P{pid}", race=Race.TERRAN, team=1, won=True)


def test_army_value_killed_and_lost_exclude_economy_and_technology():
    """resources_killed/resources_lost aggregate army+economy+technology.
    A player who lost an expansion (economy) and a tech building
    (technology) but no army should show that loss as 0, not as the
    inflated aggregate."""
    parser = UnifiedParser()
    pid, result = _result()
    player_results = {pid: result}

    event = _stats_event(
        pid=pid,
        # Aggregate fields deliberately include non-army value, to prove the
        # fix doesn't fall back to reading them.
        resources_lost=900,       # economy (expansion) + technology (tech building)
        resources_killed=700,     # opponent's economy/technology losses
        minerals_lost_army=150,   # this player's actual army loss
        vespene_lost_army=50,
        minerals_killed_army=300,  # this player's actual army kills
        vespene_killed_army=100,
    )

    parser._process_tracker_events([event], player_results)

    assert result.army_value_lost == 200  # 150 + 50, NOT the 900 aggregate
    assert result.army_value_killed == 400  # 300 + 100, NOT the 700 aggregate


def test_unknown_unit_cost_is_skipped_not_guessed_at_100():
    """A unit type absent from UNIT_COSTS must not silently contribute 100
    to army_value_built, and must not be silently dropped as 0 either --
    it's tracked in the unknown-cost counter instead."""
    parser = UnifiedParser()
    pid, result = _result()
    player_results = {pid: result}

    known_event = SimpleNamespace(
        name="UnitBornEvent", control_pid=pid, unit_type_name="Marine"  # cost 50
    )
    unknown_event = SimpleNamespace(
        name="UnitBornEvent", control_pid=pid, unit_type_name="TotallyMadeUpUnit"
    )

    parser._process_tracker_events([known_event, unknown_event], player_results)

    # Only the known unit's cost is counted -- not 100 for the unknown one,
    # and the unknown one isn't silently treated as free (0) either: it's
    # excluded from the sum and tracked separately.
    assert result.army_value_built == 50
    assert parser._unknown_unit_cost_counts == {"TotallyMadeUpUnit": 1}


def test_spending_efficiency_reflects_own_spend_not_kills_plus_losses():
    """The old formula was (army_value_killed + army_value_lost) /
    total_resources_collected -- destroying an opponent's army isn't
    spending your own resources. A player who kills a lot but banks
    (doesn't spend) most of their own resources should show LOW spending
    efficiency, not a high one inflated by their kills."""
    parser = UnifiedParser()
    pid, result = _result()
    player_results = {pid: result}

    event = _stats_event(
        pid=pid,
        minerals_current=1000,       # sitting in the bank, unspent
        vespene_current=0,
        minerals_used_current=100,   # actually invested
        vespene_used_current=0,
        minerals_used_in_progress=0,
        vespene_used_in_progress=0,
        minerals_lost=0,
        vespene_lost=0,
        minerals_killed_army=5000,   # huge kills -- must NOT inflate spending_efficiency
        vespene_killed_army=0,
    )
    parser._process_tracker_events([event], player_results)
    parser._calculate_damage_metrics([result])

    # total_resources_collected = 1000 (bank) + 100 (used_current) = 1100
    # resources_spent = 100 (used_current only, nothing lost/in-progress)
    assert result.total_resources_collected == 1100
    assert result.resources_spent == 100
    assert result.spending_efficiency == 100 / 1100
    # Confirm it's nowhere near 1.0, which the old (killed+lost)/collected
    # formula would have produced given army_value_killed=5000.
    assert result.spending_efficiency < 0.2


def test_spending_efficiency_numerator_and_denominator_both_include_lost():
    """A player who spent everything and then lost it all in a fight should
    show HIGH spending efficiency (nothing idle in the bank), not 0. This
    requires `lost` to appear in both total_resources_collected (denominator)
    and resources_spent (numerator) -- omitting it from just the numerator
    would make spending-then-losing look like never spending at all."""
    parser = UnifiedParser()
    pid, result = _result()
    player_results = {pid: result}

    event = _stats_event(
        pid=pid,
        minerals_current=0,     # nothing left in the bank
        vespene_current=0,
        minerals_used_current=0,   # nothing currently alive either...
        vespene_used_current=0,
        minerals_used_in_progress=0,
        vespene_used_in_progress=0,
        minerals_lost=5000,     # ...because it was all built and lost
        vespene_lost=0,
    )
    parser._process_tracker_events([event], player_results)
    parser._calculate_damage_metrics([result])

    assert result.total_resources_collected == 5000
    assert result.resources_spent == 5000
    assert result.spending_efficiency == 1.0
