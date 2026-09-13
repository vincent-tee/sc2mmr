from types import SimpleNamespace

import pytest

from app.services.ability_discovery import get_discovery_engine


@pytest.mark.parametrize("ability", ["TrainMarine", "BuildBarracks", "ResearchWarpGate", "RightClick"])
def test_trivial_commands_are_filtered(ability):
    assert not get_discovery_engine().should_track_ability(ability)


@pytest.mark.parametrize("ability", ["PsionicStorm", "Blink", "EnergyRecharge", "MicrobialShroud", "NexusMassRecall"])
def test_significant_abilities_are_tracked(ability):
    assert get_discovery_engine().should_track_ability(ability)


@pytest.mark.parametrize("ability", ["PsionicStorm", "EMP", "Fungal"])
def test_high_micro_classification(ability):
    assert get_discovery_engine().get_category(ability) == "high_micro"


def test_discovery_and_persistence(tmp_path):
    config_path = str(tmp_path / "abilities.json")
    discovery = get_discovery_engine(config_path)
    replay = SimpleNamespace(game_events=[
        SimpleNamespace(ability=SimpleNamespace(name=name))
        for name in ["PsionicStorm", "PsionicStorm", "TrainMarine"]
    ])
    assert discovery.discover_from_replay(replay, "test-patch") == {"PsionicStorm"}
    discovery.save_config()
    restored = get_discovery_engine(config_path)
    assert restored.discovered_abilities["PsionicStorm"].usage_count == 2
    assert restored.discovered_abilities["PsionicStorm"].patches_seen == ["test-patch"]
