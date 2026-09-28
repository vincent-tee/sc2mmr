from datetime import datetime, timedelta

from app.models import GameMode, Player, Race
from app.replay_parser import ReplayData, PlayerData
from app.services.achievement_service import AchievementService
from app.services.ingestion import ingest_match


def game(minutes_later, partner_of_alice, alice_team_won):
    teams = {"Alice": 1, partner_of_alice: 1, "Carol": 2, "Dave": 2}
    return ReplayData(
        played_at=datetime(2026, 8, 1) + timedelta(minutes=minutes_later),
        game_mode=GameMode.TWO_V_TWO, map_name="Test map", duration_seconds=600,
        replay_hash=f"game-{minutes_later}", game_fingerprint=f"game-{minutes_later}",
        players=[PlayerData(name=name, race=Race.TERRAN, team=team, won=(team == 1) == alice_team_won)
                 for name, team in teams.items()],
    )


def test_best_duo_counts_wins_with_the_same_teammate(db_session):
    results = [("Bob", True), ("Bob", True), ("Bob", False), ("Eve", True)]
    for i, (partner, won) in enumerate(results):
        ingest_match(db_session, game(i * 20, partner, won), require_experience=False)
    alice = db_session.query(Player).filter(Player.name == "Alice").one()

    stats = AchievementService._calculate_player_stats(db_session, alice.id)

    assert stats["best_duo_wins"] == 2
    assert stats["best_duo_winrate"] == 0
