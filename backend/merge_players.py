#!/usr/bin/env python3
"""
Script to merge two players.

Usage: python merge_players.py <source_player> <target_player>

Example: python merge_players.py DemonSlayer DragonKing
"""
import sys
from app.database import SessionLocal
from app.models import Player, MatchPlayer, PlayerSynergy

def merge_players(source_name: str, target_name: str):
    """Merge source player into target player."""
    db = SessionLocal()

    try:
        # Find both players
        source_player = db.query(Player).filter(Player.name == source_name).first()
        target_player = db.query(Player).filter(Player.name == target_name).first()

        if not source_player:
            print(f"❌ Error: Source player '{source_name}' not found")
            return False

        if not target_player:
            print(f"❌ Error: Target player '{target_name}' not found")
            return False

        if source_player.id == target_player.id:
            print(f"❌ Error: Cannot merge a player with itself")
            return False

        print(f"\n🔄 Merging '{source_name}' into '{target_name}'...")
        print(f"   Source: {source_player.total_games} games, {source_player.wins}W-{source_player.losses}L, {source_player.mmr:.1f} MMR")
        print(f"   Target: {target_player.total_games} games, {target_player.wins}W-{target_player.losses}L, {target_player.mmr:.1f} MMR")

        # Transfer all match participations from source to target
        match_players = db.query(MatchPlayer).filter(
            MatchPlayer.player_id == source_player.id
        ).all()

        matches_transferred = len(match_players)
        print(f"\n📋 Transferring {matches_transferred} match participations...")

        for mp in match_players:
            mp.player_id = target_player.id

        # Update synergies
        synergies_as_p1 = db.query(PlayerSynergy).filter(
            PlayerSynergy.player1_id == source_player.id
        ).all()

        synergies_as_p2 = db.query(PlayerSynergy).filter(
            PlayerSynergy.player2_id == source_player.id
        ).all()

        synergies_updated = len(synergies_as_p1) + len(synergies_as_p2)

        if synergies_updated > 0:
            print(f"🤝 Updating {synergies_updated} synergy records...")

        for synergy in synergies_as_p1:
            synergy.player1_id = target_player.id

        for synergy in synergies_as_p2:
            synergy.player2_id = target_player.id

        # Recalculate target player's statistics
        total_transferred_wins = sum(1 for mp in match_players if mp.won)
        total_transferred_losses = sum(1 for mp in match_players if not mp.won)

        print(f"\n📊 Updating statistics...")
        print(f"   Adding {total_transferred_wins} wins and {total_transferred_losses} losses")

        target_player.total_games += len(match_players)
        target_player.wins += total_transferred_wins
        target_player.losses += total_transferred_losses

        # Transfer race statistics
        for mp in match_players:
            race = mp.race.value if hasattr(mp.race, 'value') else mp.race
            if race == 'Terran':
                target_player.terran_games += 1
            elif race == 'Protoss':
                target_player.protoss_games += 1
            elif race == 'Zerg':
                target_player.zerg_games += 1
            elif race == 'Random':
                target_player.random_games += 1

        # Update last_played to most recent
        if source_player.last_played:
            if not target_player.last_played or source_player.last_played > target_player.last_played:
                target_player.last_played = source_player.last_played

        # Merge impact scores (weighted average)
        if source_player.total_games > 0 and target_player.total_games > 0:
            total_combined_games = target_player.total_games
            source_weight = matches_transferred / total_combined_games
            target_weight = (total_combined_games - matches_transferred) / total_combined_games

            target_player.avg_economic_score = (
                target_player.avg_economic_score * target_weight +
                source_player.avg_economic_score * source_weight
            )
            target_player.avg_combat_score = (
                target_player.avg_combat_score * target_weight +
                source_player.avg_combat_score * source_weight
            )
            target_player.avg_efficiency_score = (
                target_player.avg_efficiency_score * target_weight +
                source_player.avg_efficiency_score * source_weight
            )
            target_player.avg_overall_impact = (
                target_player.avg_overall_impact * target_weight +
                source_player.avg_overall_impact * source_weight
            )

        # Delete the source player
        print(f"\n🗑️  Deleting source player '{source_name}'...")
        db.delete(source_player)

        # Commit all changes
        db.commit()
        db.refresh(target_player)

        print(f"\n✅ Merge complete!")
        print(f"   '{target_name}' now has:")
        print(f"   - {target_player.total_games} total games ({target_player.wins}W-{target_player.losses}L)")
        print(f"   - {target_player.win_rate*100:.1f}% win rate")
        print(f"   - {target_player.mmr:.1f} MMR")
        print(f"   - Favorite race: {target_player.favorite_race}")

        return True

    except Exception as e:
        print(f"\n❌ Error during merge: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python merge_players.py <source_player> <target_player>")
        print("\nExample: python merge_players.py DemonSlayer DragonKing")
        print("\nThis will merge all data from source_player into target_player,")
        print("then delete the source_player.")
        sys.exit(1)

    source = sys.argv[1]
    target = sys.argv[2]

    success = merge_players(source, target)
    sys.exit(0 if success else 1)
