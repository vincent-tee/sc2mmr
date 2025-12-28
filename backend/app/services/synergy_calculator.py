"""
Synergy Calculator

Calculates synergy bonuses for duo + trio combinations.
- Checks all pairs (2-player combos)
- Checks all trios (3-player combos)
- Max bonus: +15 rating
- Requires minimum matches to trust synergy (5 for pairs, 3 for trios)
- Uses existing PlayerSynergy model for pair caching
- Trio synergies calculated on-the-fly (no persistent cache)
"""

from datetime import datetime
from itertools import combinations
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from ..models import Match, MatchPlayer, PlayerSynergy

logger = logging.getLogger(__name__)


class SynergyCalculator:
    """Calculate synergy bonuses for duo + trio combinations."""

    MIN_MATCHES_PAIR = 5  # Minimum matches to trust duo synergy
    MIN_MATCHES_TRIO = 3  # Minimum matches to trust trio synergy
    WIN_RATE_THRESHOLD = 0.60  # 60% win rate = good synergy
    MAX_BONUS = 15.0  # Cap total synergy bonus

    # In-memory cache for trio synergies (cleared after each match)
    _trio_cache: Dict[str, float] = {}

    @staticmethod
    def get_synergy_score(player_ids: List[int], db: Session) -> float:
        """
        Calculate synergy bonus for a team composition.
        Checks all pairs AND trios.
        Returns: Rating boost (0 to +15)
        """
        if not player_ids or len(player_ids) < 2:
            return 0.0

        total_boost = 0.0

        try:
            # Check all pairs (2-player combos)
            for p1, p2 in combinations(player_ids, 2):
                pair_boost = SynergyCalculator._get_pair_synergy(p1, p2, db)
                total_boost += pair_boost

            # Check all trios (3-player combos)
            if len(player_ids) >= 3:
                for p1, p2, p3 in combinations(player_ids, 3):
                    trio_boost = SynergyCalculator._get_trio_synergy(p1, p2, p3, db)
                    total_boost += trio_boost

            # Cap at max bonus
            return min(total_boost, SynergyCalculator.MAX_BONUS)

        except Exception as e:
            logger.error(f"Error calculating synergy score: {e}")
            return 0.0

    @staticmethod
    def _normalize_pair_ids(p1_id: int, p2_id: int) -> Tuple[int, int]:
        """Ensure consistent ordering for pair lookups (lower ID first)."""
        return (min(p1_id, p2_id), max(p1_id, p2_id))

    @staticmethod
    def _get_pair_synergy(p1_id: int, p2_id: int, db: Session) -> float:
        """Calculate synergy boost for a player pair using existing PlayerSynergy model."""
        try:
            # Normalize IDs for consistent lookup
            player1_id, player2_id = SynergyCalculator._normalize_pair_ids(p1_id, p2_id)

            # Check existing PlayerSynergy cache
            cached = (
                db.query(PlayerSynergy)
                .filter(
                    and_(
                        PlayerSynergy.player1_id == player1_id,
                        PlayerSynergy.player2_id == player2_id,
                    )
                )
                .first()
            )

            if cached and cached.games_together >= SynergyCalculator.MIN_MATCHES_PAIR:
                # Use cached synergy if we have enough games
                win_rate = (
                    cached.wins_together / cached.games_together
                    if cached.games_together > 0
                    else 0.0
                )

                if win_rate <= SynergyCalculator.WIN_RATE_THRESHOLD:
                    return 0.0

                # Scale: 10% above 50% = +1.5 rating
                excess_win_rate = win_rate - 0.5
                return max(0.0, excess_win_rate * 15)

            # Calculate from match history if not cached or insufficient games
            pair_matches = SynergyCalculator._get_matches_together([p1_id, p2_id], db)

            if len(pair_matches) < SynergyCalculator.MIN_MATCHES_PAIR:
                return 0.0

            wins = sum(1 for m in pair_matches if m["won_together"])
            win_rate = wins / len(pair_matches)

            # Calculate boost: scale by how much they exceed expected (50%)
            if win_rate <= SynergyCalculator.WIN_RATE_THRESHOLD:
                boost = 0.0
            else:
                excess_win_rate = win_rate - 0.5
                boost = excess_win_rate * 15  # Scale: 10% above = +1.5 rating

            # Update cache
            SynergyCalculator._update_pair_cache(
                player1_id, player2_id, len(pair_matches), wins, win_rate, boost, db
            )

            return boost

        except Exception as e:
            logger.error(f"Error calculating pair synergy for {p1_id}, {p2_id}: {e}")
            return 0.0

    @staticmethod
    def _get_trio_synergy(p1_id: int, p2_id: int, p3_id: int, db: Session) -> float:
        """Calculate synergy boost for a player trio (calculated on-the-fly)."""
        try:
            # Create sorted key for in-memory cache
            ids_key = str(tuple(sorted([p1_id, p2_id, p3_id])))

            # Check in-memory cache first
            if ids_key in SynergyCalculator._trio_cache:
                return SynergyCalculator._trio_cache[ids_key]

            trio_matches = SynergyCalculator._get_matches_together(
                [p1_id, p2_id, p3_id], db
            )

            if len(trio_matches) < SynergyCalculator.MIN_MATCHES_TRIO:
                SynergyCalculator._trio_cache[ids_key] = 0.0
                return 0.0

            wins = sum(1 for m in trio_matches if m["won_together"])
            win_rate = wins / len(trio_matches)

            if win_rate <= SynergyCalculator.WIN_RATE_THRESHOLD:
                boost = 0.0
            else:
                excess_win_rate = win_rate - 0.5
                boost = excess_win_rate * 10  # Trios weighted slightly lower

            # Cache in memory
            SynergyCalculator._trio_cache[ids_key] = boost

            return boost

        except Exception as e:
            logger.error(
                f"Error calculating trio synergy for {p1_id}, {p2_id}, {p3_id}: {e}"
            )
            return 0.0

    @staticmethod
    def _get_matches_together(player_ids: List[int], db: Session) -> List[Dict]:
        """Get all matches where specified players played together on same team."""
        result = []

        try:
            # Get match IDs where any of the players participated
            match_id_rows = (
                db.query(MatchPlayer.match_id)
                .filter(MatchPlayer.player_id.in_(player_ids))
                .distinct()
                .all()
            )

            match_id_list = [row[0] for row in match_id_rows]

            if not match_id_list:
                return result

            all_matches = (
                db.query(Match)
                .filter(Match.id.in_(match_id_list), Match.played_at.isnot(None))
                .all()
            )

            for match in all_matches:
                match_players = (
                    db.query(MatchPlayer)
                    .filter(
                        MatchPlayer.match_id == match.id,
                        MatchPlayer.player_id.in_(player_ids),
                    )
                    .all()
                )

                # Check if all players in this match
                if len(match_players) != len(player_ids):
                    continue

                # Check if all on same team
                teams = set(mp.team_number for mp in match_players)
                if len(teams) != 1:
                    continue

                # Check if they won
                won = all(mp.won == 1 for mp in match_players)

                result.append({"match_id": match.id, "won_together": won})

        except Exception as e:
            logger.error(
                f"Error getting matches together for players {player_ids}: {e}"
            )

        return result

    @staticmethod
    def _update_pair_cache(
        player1_id: int,
        player2_id: int,
        matches_played: int,
        matches_won: int,
        win_rate: float,
        synergy_score: float,
        db: Session,
    ):
        """Update or create synergy cache entry for a pair."""
        try:
            existing = (
                db.query(PlayerSynergy)
                .filter(
                    and_(
                        PlayerSynergy.player1_id == player1_id,
                        PlayerSynergy.player2_id == player2_id,
                    )
                )
                .first()
            )

            if existing:
                existing.games_together = matches_played
                existing.wins_together = matches_won
                existing.losses_together = matches_played - matches_won
                existing.avg_win_rate = win_rate
                existing.synergy_score = synergy_score
                existing.updated_at = datetime.utcnow()
            else:
                cache = PlayerSynergy(
                    player1_id=player1_id,
                    player2_id=player2_id,
                    games_together=matches_played,
                    wins_together=matches_won,
                    losses_together=matches_played - matches_won,
                    synergy_score=synergy_score,
                    avg_win_rate=win_rate,
                    updated_at=datetime.utcnow(),
                )
                db.add(cache)

            db.commit()

        except Exception as e:
            logger.error(
                f"Error updating pair cache for {player1_id}, {player2_id}: {e}"
            )
            db.rollback()

    @staticmethod
    def invalidate_cache_for_players(player_ids: List[int], db: Session):
        """Invalidate synergy cache entries that include any of these players."""
        if not player_ids:
            return

        try:
            # Delete pair cache entries containing any of these players
            db.query(PlayerSynergy).filter(
                (PlayerSynergy.player1_id.in_(player_ids))
                | (PlayerSynergy.player2_id.in_(player_ids))
            ).delete(synchronize_session="fetch")

            db.commit()

            # Clear trio in-memory cache for entries containing these players
            keys_to_remove = []
            for key in SynergyCalculator._trio_cache:
                try:
                    cached_ids = eval(key)
                    if any(pid in cached_ids for pid in player_ids):
                        keys_to_remove.append(key)
                except (ValueError, SyntaxError):
                    pass

            for key in keys_to_remove:
                del SynergyCalculator._trio_cache[key]

            logger.info(f"Invalidated synergy cache for players: {player_ids}")

        except Exception as e:
            logger.error(f"Error invalidating cache for players {player_ids}: {e}")
            db.rollback()

    @staticmethod
    def update_synergy_after_match(match_id: int, db: Session):
        """Update synergy cache after a match is played."""
        try:
            match_players = (
                db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
            )

            if not match_players:
                logger.warning(f"No players found for match {match_id}")
                return

            player_ids = [mp.player_id for mp in match_players]

            # Invalidate cache for all players in this match
            SynergyCalculator.invalidate_cache_for_players(player_ids, db)

            logger.info(f"Updated synergy cache after match {match_id}")

        except Exception as e:
            logger.error(f"Error updating synergy after match {match_id}: {e}")

    @staticmethod
    def clear_trio_cache():
        """Clear the in-memory trio synergy cache."""
        SynergyCalculator._trio_cache.clear()
        logger.debug("Cleared trio synergy cache")

    @staticmethod
    def get_pair_stats(player1_id: int, player2_id: int, db: Session) -> Optional[Dict]:
        """Get detailed synergy stats for a player pair."""
        try:
            p1_id, p2_id = SynergyCalculator._normalize_pair_ids(player1_id, player2_id)

            synergy = (
                db.query(PlayerSynergy)
                .filter(
                    and_(
                        PlayerSynergy.player1_id == p1_id,
                        PlayerSynergy.player2_id == p2_id,
                    )
                )
                .first()
            )

            if not synergy:
                # Calculate on the fly
                matches = SynergyCalculator._get_matches_together(
                    [player1_id, player2_id], db
                )
                if not matches:
                    return None

                wins = sum(1 for m in matches if m["won_together"])
                return {
                    "player1_id": p1_id,
                    "player2_id": p2_id,
                    "games_together": len(matches),
                    "wins_together": wins,
                    "losses_together": len(matches) - wins,
                    "win_rate": wins / len(matches) if matches else 0.0,
                    "synergy_score": SynergyCalculator._get_pair_synergy(
                        player1_id, player2_id, db
                    ),
                    "meets_threshold": len(matches)
                    >= SynergyCalculator.MIN_MATCHES_PAIR,
                }

            return {
                "player1_id": synergy.player1_id,
                "player2_id": synergy.player2_id,
                "games_together": synergy.games_together,
                "wins_together": synergy.wins_together,
                "losses_together": synergy.losses_together,
                "win_rate": synergy.avg_win_rate,
                "synergy_score": synergy.synergy_score,
                "meets_threshold": synergy.games_together
                >= SynergyCalculator.MIN_MATCHES_PAIR,
            }

        except Exception as e:
            logger.error(
                f"Error getting pair stats for {player1_id}, {player2_id}: {e}"
            )
            return None

    @staticmethod
    def get_team_synergy_breakdown(player_ids: List[int], db: Session) -> Dict:
        """Get detailed breakdown of synergy bonuses for a team."""
        breakdown = {
            "total_bonus": 0.0,
            "pair_bonuses": [],
            "trio_bonuses": [],
            "capped": False,
        }

        if not player_ids or len(player_ids) < 2:
            return breakdown

        try:
            raw_total = 0.0

            # Calculate all pair bonuses
            for p1, p2 in combinations(player_ids, 2):
                pair_boost = SynergyCalculator._get_pair_synergy(p1, p2, db)
                breakdown["pair_bonuses"].append(
                    {"players": [p1, p2], "bonus": pair_boost}
                )
                raw_total += pair_boost

            # Calculate all trio bonuses
            if len(player_ids) >= 3:
                for p1, p2, p3 in combinations(player_ids, 3):
                    trio_boost = SynergyCalculator._get_trio_synergy(p1, p2, p3, db)
                    breakdown["trio_bonuses"].append(
                        {"players": [p1, p2, p3], "bonus": trio_boost}
                    )
                    raw_total += trio_boost

            # Apply cap
            if raw_total > SynergyCalculator.MAX_BONUS:
                breakdown["capped"] = True
                breakdown["total_bonus"] = SynergyCalculator.MAX_BONUS
            else:
                breakdown["total_bonus"] = raw_total

        except Exception as e:
            logger.error(f"Error getting team synergy breakdown: {e}")

        return breakdown
