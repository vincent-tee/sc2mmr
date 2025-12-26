import pytest
from app.services.rivalry_service import RivalryService
from app.models import Match, MatchPlayer, Player, Race, GameMode
from datetime import datetime, timedelta

def test_rivalry_service(db_session):
    # Setup players
    p1 = Player(name="P1", mu=25.0, sigma=8.333)
    p2 = Player(name="P2", mu=25.0, sigma=8.333)
    p3 = Player(name="P3", mu=25.0, sigma=8.333)
    db_session.add_all([p1, p2, p3])
    db_session.flush()

    # Create 3 matches between P1 and P2
    # Match 1: P1 wins
    m1 = Match(
        played_at=datetime.utcnow() - timedelta(days=2),
        game_mode=GameMode.TWO_V_TWO, # Irrelevant
        map_name="Map 1",
        duration_seconds=600
    )
    db_session.add(m1)
    db_session.flush()

    db_session.add_all([
        MatchPlayer(match_id=m1.id, player_id=p1.id, team_number=1, race=Race.TERRAN, won=1,
                    mu_before=25.0, mu_after=26.0, sigma_before=8.0, sigma_after=7.9),
        MatchPlayer(match_id=m1.id, player_id=p3.id, team_number=1, race=Race.TERRAN, won=1,
                    mu_before=25.0, mu_after=26.0, sigma_before=8.0, sigma_after=7.9),
        MatchPlayer(match_id=m1.id, player_id=p2.id, team_number=2, race=Race.ZERG, won=0,
                    mu_before=25.0, mu_after=24.0, sigma_before=8.0, sigma_after=7.9),
    ])

    # Match 2: P2 wins
    m2 = Match(
        played_at=datetime.utcnow() - timedelta(days=1),
        game_mode=GameMode.TWO_V_TWO, # Irrelevant
        map_name="Map 1",
        duration_seconds=600
    )
    db_session.add(m2)
    db_session.flush()
    
    db_session.add_all([
        MatchPlayer(match_id=m2.id, player_id=p1.id, team_number=1, race=Race.TERRAN, won=0,
                    mu_before=26.0, mu_after=25.0, sigma_before=7.9, sigma_after=7.8),
        MatchPlayer(match_id=m2.id, player_id=p2.id, team_number=2, race=Race.ZERG, won=1,
                    mu_before=24.0, mu_after=25.0, sigma_before=7.9, sigma_after=7.8),
    ])

    # Match 3: P1 wins
    m3 = Match(
        played_at=datetime.utcnow(),
        game_mode=GameMode.TWO_V_TWO, # Type check might fail if enum strict? Service assumes enum.
        map_name="Map 1",
        duration_seconds=600
    )
    # Using 1v1 enum usually logic wise, but DB validation might require valid ENUM value if strict.
    # Service doesn't check mode.
    m3.game_mode = GameMode.TWO_V_TWO # Safe
    db_session.add(m3)
    db_session.flush()
    
    db_session.add_all([
        MatchPlayer(match_id=m3.id, player_id=p1.id, team_number=1, race=Race.TERRAN, won=1,
                    mu_before=25.0, mu_after=26.0, sigma_before=7.8, sigma_after=7.7),
        MatchPlayer(match_id=m3.id, player_id=p2.id, team_number=2, race=Race.ZERG, won=0,
                    mu_before=25.0, mu_after=24.0, sigma_before=7.8, sigma_after=7.7),
    ])
    
    db_session.commit()

    # Calculate
    count = RivalryService.calculate_all_rivalries(db_session)
    assert count >= 1 # Should create at least P1-P2 rivalry
    
    # Check results
    # Use ordered IDs
    pid1, pid2 = min(p1.id, p2.id), max(p1.id, p2.id)
    
    from app.models import PlayerRivalry
    rivalry = db_session.query(PlayerRivalry).filter_by(player1_id=pid1, player2_id=pid2).first()
    
    assert rivalry is not None
    assert rivalry.games_against == 3
    
    # Check wins
    # P1 won match 1, match 3. P2 won match 2.
    # If p1.id == pid1: p1_wins=2, p2_wins=1
    # If p1.id == pid2: p1_wins=1, p2_wins=2
    if p1.id == pid1:
        assert rivalry.player1_wins == 2
        assert rivalry.player2_wins == 1
    else:
        assert rivalry.player1_wins == 1
        assert rivalry.player2_wins == 2

    # Check Score
    # 3 games => Volume = 6
    # Closeness => 1/2 = 0.5 * 40 = 20
    # Recency => 0 days = 20
    # Total = 6 + 20 + 20 = 46
    assert rivalry.rivalry_score == 46.0

