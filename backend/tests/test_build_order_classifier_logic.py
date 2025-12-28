import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import (
    Base,
    Match,
    MatchPlayer,
    Player,
    PerformanceFeatures,
    Race,
    GameMode,
)
from app.services.build_order_classifier import (
    train_classifier,
    classify_build,
    get_classifier,
)
from datetime import datetime


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_classifier_basic(db_session):
    # Setup some test data
    p = Player(name="TestPlayer")
    db_session.add(p)
    db_session.commit()

    m = Match(
        played_at=datetime.utcnow(),
        game_mode=GameMode.TWO_V_TWO,
        map_name="TestMap",
        duration_seconds=1200,
    )
    db_session.add(m)
    db_session.commit()

    mp = MatchPlayer(
        match_id=m.id,
        player_id=p.id,
        team_number=1,
        race=Race.TERRAN,
        won=1,
        mu_before=25.0,
        sigma_before=8.333,
        mu_after=26.0,
        sigma_after=8.0,
    )
    db_session.add(mp)
    db_session.commit()

    # Add performance features with build order
    # Example build order: 12 Rax, 16 Expand
    build_order = [
        {"second": 10, "unit_type": "SCV", "is_worker": True, "is_building": False},
        {
            "second": 45,
            "unit_type": "SupplyDepot",
            "is_worker": False,
            "is_building": True,
        },
        {
            "second": 100,
            "unit_type": "Barracks",
            "is_worker": False,
            "is_building": True,
        },
        {
            "second": 150,
            "unit_type": "Marine",
            "is_worker": False,
            "is_building": False,
        },
        {
            "second": 200,
            "unit_type": "CommandCenter",
            "is_worker": False,
            "is_building": True,
        },
    ]

    pf = PerformanceFeatures(
        match_player_id=mp.id, build_order_json=build_order, build_order_hash="abc"
    )
    db_session.add(pf)
    db_session.commit()

    # Train (even with 1 sample it should fall back to rules or work)
    res = train_classifier(db_session)
    assert res["samples"] == 1

    # Classify
    archetype, confidence = classify_build(db_session, mp.id)
    assert archetype in ["cheese", "rush", "macro", "timing_attack", "standard"]
    assert confidence > 0
