"""
Unit tests for app.advanced_parser -- covering the 2026-09-15 replay-metrics
review fixes (docs/reviews/2026-09-15-replay-metrics-review.md):

1. army_value_killed/lost must only sum the *_army mineral+vespene
   components of PlayerStatsEvent, not the full army+economy+technology
   aggregate.
2. spending_efficiency/resources_spent must be derived from actual
   invested-or-queued resources (minerals/vespene used_current +
   used_in_progress), never from combat outcomes (army_value_killed/lost).
3. get_unit_cost() must return None for unknown units instead of guessing
   100, and unknown units must be tracked separately rather than folded
   into the value sums as if their cost were known.
4. unit_composition must retain every observed unit type, not just the
   top 5.
5. workers_created (increment-only production count) and
   peak_active_workers (snapshot-based peak observation) must be tracked
   as two distinct fields, not conflated into one.

These tests exercise `_process_tracker_events` and `get_unit_cost`
directly with fake sc2reader-like events (SimpleNamespace), so they don't
require a real replay file.
"""

from types import SimpleNamespace

from app.advanced_parser import (
    PlayerMetrics,
    get_unit_cost,
    _process_tracker_events,
)


def make_player_metrics(pid_names):
    """Build a {pid: PlayerMetrics} dict for the given {pid: name} mapping;
    odd pids play on team 1 and even pids on team 2."""
    return {
        pid: PlayerMetrics(player_name=name, race="Terran", team=1 if pid % 2 else 2, won=True)
        for pid, name in pid_names.items()
    }


def player_stats_event(
    pid,
    *,
    minerals_lost_army=0,
    minerals_lost_economy=0,
    minerals_lost_technology=0,
    vespene_lost_army=0,
    vespene_lost_economy=0,
    vespene_lost_technology=0,
    minerals_killed_army=0,
    minerals_killed_economy=0,
    minerals_killed_technology=0,
    vespene_killed_army=0,
    vespene_killed_economy=0,
    vespene_killed_technology=0,
    minerals_used_current=0,
    minerals_used_in_progress=0,
    vespene_used_current=0,
    vespene_used_in_progress=0,
    minerals_current=0,
    vespene_current=0,
    workers_active_count=0,
    food_used=0,
    food_made=200,
):
    """Build a fake PlayerStatsEvent-like object with the real sc2reader
    field names (see sc2reader.events.tracker.PlayerStatsEvent)."""
    return SimpleNamespace(
        name="PlayerStatsEvent",
        pid=pid,
        minerals_lost_army=minerals_lost_army,
        minerals_lost_economy=minerals_lost_economy,
        minerals_lost_technology=minerals_lost_technology,
        vespene_lost_army=vespene_lost_army,
        vespene_lost_economy=vespene_lost_economy,
        vespene_lost_technology=vespene_lost_technology,
        minerals_killed_army=minerals_killed_army,
        minerals_killed_economy=minerals_killed_economy,
        minerals_killed_technology=minerals_killed_technology,
        vespene_killed_army=vespene_killed_army,
        vespene_killed_economy=vespene_killed_economy,
        vespene_killed_technology=vespene_killed_technology,
        minerals_used_current=minerals_used_current,
        minerals_used_in_progress=minerals_used_in_progress,
        vespene_used_current=vespene_used_current,
        vespene_used_in_progress=vespene_used_in_progress,
        minerals_current=minerals_current,
        vespene_current=vespene_current,
        workers_active_count=workers_active_count,
        food_used=food_used,
        food_made=food_made,
    )


def unit_born_event(pid, unit_type_name, frame=0):
    return SimpleNamespace(
        name="UnitBornEvent",
        control_pid=pid,
        unit_type_name=unit_type_name,
        frame=frame,
    )


def unit_died_event(unit_type_name, killer_pid=None, owner_pid=None, second=0, frame=None):
    owner = SimpleNamespace(pid=owner_pid) if owner_pid is not None else None
    unit = SimpleNamespace(name=unit_type_name, owner=owner) if owner is not None else None
    kwargs = dict(
        name="UnitDiedEvent",
        unit_type_name=unit_type_name,
        unit=unit,
        second=second,
        frame=frame if frame is not None else second * 16,  # 16 loops/sec fallback rate
    )
    if killer_pid is not None:
        kwargs["killer_pid"] = killer_pid
    return SimpleNamespace(**kwargs)


class TestArmyValueExcludesEconomyAndTechnology:
    """Issue 1: army_value_killed/lost must only sum the *_army fields."""

    def test_army_value_lost_excludes_economy_and_technology(self):
        metrics = make_player_metrics({1: "Alice"})
        event = player_stats_event(
            1,
            minerals_lost_army=100,
            minerals_lost_economy=500,
            minerals_lost_technology=200,
            vespene_lost_army=50,
            vespene_lost_economy=10,
            vespene_lost_technology=5,
        )
        _process_tracker_events([event], metrics, game_duration=600)

        # Only the army components (100 + 50 = 150), not the aggregate
        # (100+500+200 + 50+10+5 = 865).
        assert metrics[1].army_value_lost == 150

    def test_army_value_killed_excludes_economy_and_technology(self):
        metrics = make_player_metrics({1: "Alice"})
        event = player_stats_event(
            1,
            minerals_killed_army=80,
            minerals_killed_economy=300,
            minerals_killed_technology=40,
            vespene_killed_army=20,
            vespene_killed_economy=15,
            vespene_killed_technology=5,
        )
        _process_tracker_events([event], metrics, game_duration=600)

        # Only the army components (80 + 20 = 100), not the aggregate (460).
        assert metrics[1].army_value_killed == 100


class TestSpendingEfficiencyFromActualSpending:
    """Issue 2: spending_efficiency must reflect invested-or-queued
    resources at each snapshot, never combat outcomes."""

    def test_spending_efficiency_averages_per_snapshot_invested_ratio(self):
        metrics = make_player_metrics({1: "Alice"})
        events = [
            # Snapshot 1: invested 200 of 1000 collected -> ratio 0.2
            player_stats_event(
                1, minerals_used_current=200, minerals_current=800
            ),
            # Snapshot 2: invested 900 of 1000 collected -> ratio 0.9
            player_stats_event(
                1, minerals_used_current=900, minerals_current=100
            ),
        ]
        _process_tracker_events(events, metrics, game_duration=600)

        assert metrics[1].spending_efficiency == pytest_approx(0.55)
        # resources_spent is the final snapshot's invested amount, not a sum.
        assert metrics[1].resources_spent == 900

    def test_spending_efficiency_ignores_army_value_killed_and_lost(self):
        """Large kill/loss values must not leak into spending_efficiency --
        destroying enemy units or losing your own units is not spending
        your own resources."""
        metrics = make_player_metrics({1: "Alice"})
        event = player_stats_event(
            1,
            minerals_used_current=100,
            minerals_current=900,  # ratio 0.1
            minerals_killed_army=50000,
            minerals_lost_army=50000,
        )
        _process_tracker_events([event], metrics, game_duration=600)

        assert metrics[1].spending_efficiency == pytest_approx(0.1)


def pytest_approx(value, tol=1e-9):
    class _Approx:
        def __eq__(self, other):
            return abs(other - value) < tol

    return _Approx()


class TestUnknownUnitCostsNotDefaulted:
    """Issue 3: unknown units must not silently get cost 100."""

    def test_get_unit_cost_returns_none_for_unknown_unit(self):
        assert get_unit_cost("TotallyMadeUpUnit") is None

    def test_get_unit_cost_returns_known_cost(self):
        assert get_unit_cost("Marine") == 50

    def test_unit_died_event_with_unknown_cost_is_excluded_from_sums(self):
        metrics = make_player_metrics({1: "Killer", 2: "Victim"})
        event = unit_died_event(
            "SomeUnknownUnit", killer_pid=1, owner_pid=2, second=42
        )
        _process_tracker_events([event], metrics, game_duration=600)

        # Value sums must not silently absorb a guessed cost.
        assert metrics[1].army_value_killed == 0
        assert metrics[2].army_value_lost == 0

        # Unit *counts* are unaffected by unknown cost.
        assert metrics[1].units_killed == 1
        assert metrics[2].units_lost == 1

        # Coverage is tracked separately for both sides.
        assert metrics[1].unknown_unit_types == {"SomeUnknownUnit": 1}
        assert metrics[2].unknown_unit_types == {"SomeUnknownUnit": 1}

    def test_unit_died_event_with_known_cost_still_sums_correctly(self):
        metrics = make_player_metrics({1: "Killer", 2: "Victim"})
        event = unit_died_event("Marine", killer_pid=1, owner_pid=2, second=10)
        _process_tracker_events([event], metrics, game_duration=600)

        assert metrics[1].army_value_killed == 50
        assert metrics[2].army_value_lost == 50
        assert metrics[1].unknown_unit_types == {}
        assert metrics[2].unknown_unit_types == {}


class TestMineralPatchDepletionIsNotAKill:
    """See docs/reviews/2026-09-16-parser-field-audit.md section 4."""

    def test_mineral_field_depletion_excluded_from_units_killed(self):
        metrics = make_player_metrics({1: "Miner", 2: "Enemy"})
        events = [
            unit_died_event("MineralField750", killer_pid=1, second=100),
            unit_died_event("LabMineralField", killer_pid=1, second=200),
            unit_died_event("Zergling", killer_pid=1, owner_pid=2, second=300),
        ]
        _process_tracker_events(events, metrics, game_duration=600)
        assert metrics[1].units_killed == 1


class TestKillEventsRecordsKillerVictimAndLocation:
    """See docs/reviews/2026-09-16-parser-field-audit.md section 3."""

    def test_records_kill_with_killer_and_drops_killerless_deaths(self):
        metrics = make_player_metrics({1: "Killer", 2: "Victim"})
        events = [
            unit_died_event("Zergling", killer_pid=1, owner_pid=2, second=42),
            unit_died_event("Larva", killer_pid=None, second=99),  # morph, dropped
        ]
        kill_events = []
        _process_tracker_events(events, metrics, game_duration=600, kill_events=kill_events)
        assert len(kill_events) == 1
        assert kill_events[0]["killer_name"] == "Killer"
        assert kill_events[0]["victim_name"] == "Victim"
        assert kill_events[0]["unit_type"] == "Zergling"
        assert kill_events[0]["game_second"] == 42

    def test_kill_events_none_by_default_is_backward_compatible(self):
        metrics = make_player_metrics({1: "Killer", 2: "Victim"})
        event = unit_died_event("Zergling", killer_pid=1, owner_pid=2, second=10)
        _process_tracker_events([event], metrics, game_duration=600)
        assert metrics[1].units_killed == 1


class TestUnitCompositionKeepsAllUnits:
    """Issue 4: unit_composition must not be truncated to the top 5."""

    def test_all_observed_unit_types_are_retained(self):
        metrics = make_player_metrics({1: "Alice"})
        unit_types = [
            "Marine", "Marauder", "Reaper", "Ghost", "Hellion",
            "Hellbat", "WidowMine",  # 7 distinct types, more than 5
        ]
        events = [unit_born_event(1, name) for name in unit_types]
        _process_tracker_events(events, metrics, game_duration=600)

        assert set(metrics[1].unit_composition.keys()) == set(unit_types)
        assert len(metrics[1].unit_composition) == 7


class TestWorkersCreatedVsPeakActiveWorkers:
    """Issue 5: workers_created (increment-only production count) and
    peak_active_workers (snapshot peak) must be independent fields."""

    def test_fields_are_tracked_independently(self):
        metrics = make_player_metrics({1: "Alice"})
        events = [
            # A high peak-active snapshot should not affect the production
            # counter.
            player_stats_event(1, workers_active_count=15),
            unit_born_event(1, "SCV"),
            unit_born_event(1, "SCV"),
            unit_born_event(1, "SCV"),
            # A lower later snapshot must not decrease the recorded peak.
            player_stats_event(1, workers_active_count=10),
        ]
        _process_tracker_events(events, metrics, game_duration=600)

        assert metrics[1].workers_created == 3
        assert metrics[1].peak_active_workers == 15

    def test_workers_created_starts_at_zero_not_seeded_from_peak(self):
        """Regression for the historical conflation bug: workers_created
        used to be seeded from a peak-active observation and then have
        UnitBornEvents added on top, over-counting production."""
        metrics = make_player_metrics({1: "Alice"})
        events = [
            player_stats_event(1, workers_active_count=50),
        ]
        _process_tracker_events(events, metrics, game_duration=600)

        assert metrics[1].workers_created == 0
        assert metrics[1].peak_active_workers == 50


class TestFriendlyFireIsNotAKill:
    """See docs/reviews/2026-09-28-replay-cutoffs-and-score-semantics.md."""

    def test_killing_a_teammates_or_own_unit_counts_as_their_loss_not_a_kill(self):
        metrics = make_player_metrics({1: "Shooter", 3: "Teammate", 2: "Enemy"})
        events = [
            unit_died_event("Zergling", killer_pid=1, owner_pid=3, second=10),
            unit_died_event("Zergling", killer_pid=1, owner_pid=1, second=20),
            unit_died_event("Zergling", killer_pid=1, owner_pid=2, second=30),
        ]
        kills = []
        _process_tracker_events(events, metrics, game_duration=600, kill_events=kills)
        assert metrics[1].units_killed == 1
        assert (metrics[3].units_lost, metrics[1].units_lost) == (1, 1)
        assert [k["victim_name"] for k in kills] == ["Enemy"]


class TestSupplyBlockUsesRealIntervalsOnce:
    def test_each_blocked_snapshot_counts_until_the_next_one(self):
        from app.metric_accounting import supply_blocked_seconds
        assert supply_blocked_seconds([(0.0, False), (7.1, True), (14.2, True), (21.3, False)]) == 14
        assert supply_blocked_seconds([(0.0, True), (7.1, True), (8.0, False)]) == 8
        assert supply_blocked_seconds([(5.0, True)]) == 0

    def test_parser_counts_a_blocked_snapshot_once(self):
        metrics = make_player_metrics({1: "Blocked"})
        blocked, free = dict(food_used=20, food_made=20), dict(food_used=10, food_made=20)
        events = [
            SimpleNamespace(name="PlayerStatsEvent", pid=1, frame=0, **blocked),
            SimpleNamespace(name="PlayerStatsEvent", pid=1, frame=160, **free),
        ]
        _process_tracker_events(events, metrics, game_duration=600, total_frames=13440)
        assert metrics[1].supply_block_seconds == 7
