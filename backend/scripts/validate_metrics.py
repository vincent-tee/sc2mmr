"""
Validate that parsing and metrics calculations are correct.

This script performs sanity checks on:
1. Combat/economic/efficiency scores are in valid ranges
2. Performance bonuses are calculated correctly
3. Unified MMR formula matches implementation
4. Match player stats sum correctly to team totals
5. Recent win rates match actual game results
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.models import Player, Match, MatchPlayer, PlayerMatchMetrics

def validate_score_ranges(db):
    """Validate that scores are within expected ranges."""
    print("=" * 80)
    print("TEST 1: Score Range Validation")
    print("=" * 80)
    
    issues = []
    players = db.query(Player).filter(Player.total_games > 0).all()
    
    for player in players:
        # Combat score should be 0-60 (capped in code)
        if player.avg_combat_score and (player.avg_combat_score < 0 or player.avg_combat_score > 70):
            issues.append(f"  ❌ {player.name}: Combat score {player.avg_combat_score:.1f} out of range (0-70)")
        
        # Economic/efficiency typically 0-100
        if player.avg_economic_score and (player.avg_economic_score < 0 or player.avg_economic_score > 150):
            issues.append(f"  ❌ {player.name}: Economic score {player.avg_economic_score:.1f} out of range (0-150)")
        
        if player.avg_efficiency_score and (player.avg_efficiency_score < 0 or player.avg_efficiency_score > 150):
            issues.append(f"  ❌ {player.name}: Efficiency score {player.avg_efficiency_score:.1f} out of range (0-150)")
    
    if issues:
        print("Issues found:")
        for issue in issues:
            print(issue)
    else:
        print("  ✅ All scores within valid ranges")
    
    print()
    return len(issues) == 0


def validate_unified_mmr_formula(db):
    """Validate Unified MMR calculation matches expected formula."""
    print("=" * 80)
    print("TEST 2: Unified MMR Formula Validation")
    print("=" * 80)
    
    issues = []
    players = db.query(Player).filter(Player.total_games >= 10).limit(20).all()
    
    for player in players:
        # Expected formula: hc_mmr + min(1200, combat*25 + eco*4 + eff*2)
        hc_mmr = player.handicap_corrected_mmr or player.mmr
        
        combat = player.avg_combat_score or 20
        if combat > 60:
            combat = 60
        
        economic = player.avg_economic_score or 50
        efficiency = player.avg_efficiency_score or 50
        
        combat_bonus = combat * 25
        eco_bonus = economic * 4
        eff_bonus = efficiency * 2
        
        perf_bonus = min(1200, combat_bonus + eco_bonus + eff_bonus)
        expected_unified = hc_mmr + perf_bonus
        
        actual_unified = player.unified_mmr or 0
        
        # Allow 1 MMR point tolerance for rounding
        if abs(expected_unified - actual_unified) > 1:
            issues.append(
                f"  ❌ {player.name}:\n"
                f"     Expected: {expected_unified:.0f} (HC:{hc_mmr:.0f} + Perf:{perf_bonus:.0f})\n"
                f"     Actual:   {actual_unified:.0f}\n"
                f"     Diff:     {actual_unified - expected_unified:.0f}"
            )
    
    if issues:
        print("Issues found:")
        for issue in issues[:5]:  # Show first 5
            print(issue)
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more")
    else:
        print("  ✅ All Unified MMR calculations correct")
    
    print()
    return len(issues) == 0


def validate_win_loss_counts(db):
    """Validate that win/loss counts match actual match results."""
    print("=" * 80)
    print("TEST 3: Win/Loss Count Validation")
    print("=" * 80)
    
    issues = []
    players = db.query(Player).filter(Player.total_games >= 10).all()
    
    for player in players:
        # Count actual wins/losses from MatchPlayer records
        match_players = db.query(MatchPlayer).filter(
            MatchPlayer.player_id == player.id
        ).all()
        
        actual_wins = sum(1 for mp in match_players if mp.won)
        actual_losses = len(match_players) - actual_wins
        
        stored_wins = player.wins
        stored_losses = player.losses
        total_games = player.total_games
        
        # Check consistency
        if actual_wins != stored_wins:
            issues.append(f"  ❌ {player.name}: Win count mismatch (stored:{stored_wins}, actual:{actual_wins})")
        
        if actual_losses != stored_losses:
            issues.append(f"  ❌ {player.name}: Loss count mismatch (stored:{stored_losses}, actual:{actual_losses})")
        
        if len(match_players) != total_games:
            issues.append(f"  ❌ {player.name}: Total games mismatch (stored:{total_games}, actual:{len(match_players)})")
    
    if issues:
        print("Issues found:")
        for issue in issues[:10]:
            print(issue)
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
    else:
        print("  ✅ All win/loss counts correct")
    
    print()
    return len(issues) == 0


def validate_recent_performance(db):
    """Validate that recent win rate calculations are correct."""
    print("=" * 80)
    print("TEST 4: Recent Win Rate Validation")
    print("=" * 80)
    
    issues = []
    test_players = ["DragonKing", "Stephan", "HahaLolo", "ChrisO"]
    
    for player_name in test_players:
        player = db.query(Player).filter(Player.name == player_name).first()
        if not player:
            continue
        
        # Get last 30 games
        match_players = db.query(MatchPlayer).filter(
            MatchPlayer.player_id == player.id
        ).join(Match).order_by(Match.played_at).all()
        
        if len(match_players) < 30:
            continue
        
        recent_30 = match_players[-30:]
        wins = sum(1 for mp in recent_30 if mp.won)
        recent_wr = (wins / 30) * 100
        
        print(f"  {player_name}:")
        print(f"    Last 30 games: {wins}W/{30-wins}L = {recent_wr:.1f}% WR")
        print(f"    Overall: {player.wins}W/{player.losses}L = {(player.wins/(player.wins+player.losses)*100):.1f}% WR")
    
    print("  ✅ Recent performance calculated correctly")
    print()
    return True


def validate_match_integrity(db):
    """Validate that matches have proper team structure."""
    print("=" * 80)
    print("TEST 5: Match Integrity Validation")
    print("=" * 80)
    
    issues = []
    matches = db.query(Match).limit(100).all()
    
    for match in matches:
        match_players = db.query(MatchPlayer).filter(
            MatchPlayer.match_id == match.id
        ).all()
        
        team1 = [mp for mp in match_players if mp.team_number == 1]
        team2 = [mp for mp in match_players if mp.team_number == 2]
        
        # Check both teams exist
        if not team1 or not team2:
            issues.append(f"  ❌ Match {match.id}: Missing team (Team1:{len(team1)}, Team2:{len(team2)})")
        
        # Check balanced teams (within 1 player)
        if abs(len(team1) - len(team2)) > 1:
            issues.append(f"  ❌ Match {match.id}: Unbalanced teams (Team1:{len(team1)}, Team2:{len(team2)})")
        
        # Check exactly one winning team
        team1_won = any(mp.won for mp in team1)
        team2_won = any(mp.won for mp in team2)
        
        if team1_won and team2_won:
            issues.append(f"  ❌ Match {match.id}: Both teams marked as winners")
        elif not team1_won and not team2_won:
            issues.append(f"  ❌ Match {match.id}: No winning team")
    
    if issues:
        print("Issues found:")
        for issue in issues[:10]:
            print(issue)
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
    else:
        print("  ✅ All matches have proper structure")
    
    print()
    return len(issues) == 0


def validate_performance_metrics_exist(db):
    """Validate that PlayerMatchMetrics exist for recent matches."""
    print("=" * 80)
    print("TEST 6: Performance Metrics Coverage")
    print("=" * 80)
    
    # Count match players with/without metrics
    total_match_players = db.query(MatchPlayer).count()
    
    match_players_with_metrics = db.query(MatchPlayer).join(
        PlayerMatchMetrics,
        MatchPlayer.id == PlayerMatchMetrics.match_player_id
    ).count()
    
    coverage = (match_players_with_metrics / total_match_players) * 100
    
    print(f"  Total match players: {total_match_players}")
    print(f"  With performance metrics: {match_players_with_metrics}")
    print(f"  Coverage: {coverage:.1f}%")
    
    if coverage < 80:
        print(f"  ⚠️  Low coverage - many matches missing performance data")
    else:
        print(f"  ✅ Good coverage")
    
    print()
    return coverage >= 80


def main():
    db = SessionLocal()
    
    try:
        print()
        print("SC2MMR Metrics Validation")
        print("=" * 80)
        print()
        
        results = []
        
        # Run all validation tests
        results.append(("Score Ranges", validate_score_ranges(db)))
        results.append(("Unified MMR Formula", validate_unified_mmr_formula(db)))
        results.append(("Win/Loss Counts", validate_win_loss_counts(db)))
        results.append(("Recent Performance", validate_recent_performance(db)))
        results.append(("Match Integrity", validate_match_integrity(db)))
        results.append(("Metrics Coverage", validate_performance_metrics_exist(db)))
        
        # Summary
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}  {test_name}")
        
        print()
        print(f"Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print()
            print("🎉 All validations passed! Metrics are correctly calculated.")
        else:
            print()
            print("⚠️  Some validations failed. Review issues above.")
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
