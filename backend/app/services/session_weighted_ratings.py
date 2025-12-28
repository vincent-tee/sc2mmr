"""
Session-Weighted Rating System

Calculates player ratings with aggressive volatility:
- Current session matches: 3x weight
- Recent week matches: 2x weight
- Older matches: 1x weight

Max volatility: ±50 MMR per session update
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import logging

from ..models import Player, Match, MatchPlayer

logger = logging.getLogger(__name__)


class SessionWeightedRatings:
    """Calculate session-weighted ratings with aggressive volatility."""

    SESSION_GAP_HOURS = 4.0  # 4 hours gap = new session
    AGGRESSIVE_ALPHA = 0.6  # 60% new, 40% old (aggressive)
    MAX_VOLATILITY = 50.0  # Max change per update

    # Recency multipliers
    RECENCY_WEIGHTS = {"current_session": 3.0, "recent_week": 2.0, "older": 1.0}

    @staticmethod
    def get_player_matches_with_recency(player_id: int, db: Session) -> List[Dict]:
        """Get all matches with recency classification."""
        matches = (
            db.query(Match)
            .join(MatchPlayer)
            .filter(MatchPlayer.player_id == player_id, Match.played_at.isnot(None))
            .order_by(Match.played_at.desc())
            .all()
        )

        result = []
        now = datetime.utcnow()
        session_cutoff = now - timedelta(hours=SessionWeightedRatings.SESSION_GAP_HOURS)
        week_cutoff = now - timedelta(days=7)

        for match in matches:
            mp = (
                db.query(MatchPlayer)
                .filter(
                    MatchPlayer.match_id == match.id, MatchPlayer.player_id == player_id
                )
                .first()
            )

            if not mp:
                continue

            match_mmr = (
                mp.mmr_after
                if hasattr(mp, "mmr_after") and mp.mmr_after
                else (
                    mp.mmr_before
                    if hasattr(mp, "mmr_before") and mp.mmr_before
                    else None
                )
            )

            if match_mmr is None:
                # Fallback to player's current MMR
                player = db.query(Player).filter(Player.id == player_id).first()
                match_mmr = player.mmr if player else 1000

            # Determine recency
            if match.played_at >= session_cutoff:
                recency = "current_session"
            elif match.played_at >= week_cutoff:
                recency = "recent_week"
            else:
                recency = "older"

            result.append(
                {
                    "match_id": match.id,
                    "mmr_at_match": match_mmr,
                    "recency_weight": SessionWeightedRatings.RECENCY_WEIGHTS[recency],
                    "played_at": match.played_at,
                }
            )

        return result

    @staticmethod
    def calculate_session_weighted_mmr(player_id: int, db: Session) -> float:
        """Calculate session-weighted MMR with ±50 volatility cap."""
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return 1000.0

        base_mmr = player.mmr or 1000.0

        matches = SessionWeightedRatings.get_player_matches_with_recency(player_id, db)

        if not matches:
            return base_mmr

        total_weight = sum(m["recency_weight"] for m in matches)
        weighted_sum = sum(m["mmr_at_match"] * m["recency_weight"] for m in matches)

        weighted_mmr = weighted_sum / total_weight if total_weight > 0 else base_mmr

        # Aggressive update: 60% new weighted, 40% old base
        session_mmr = (
            SessionWeightedRatings.AGGRESSIVE_ALPHA * weighted_mmr
            + (1 - SessionWeightedRatings.AGGRESSIVE_ALPHA) * base_mmr
        )

        # Enforce ±50 volatility cap
        max_change = SessionWeightedRatings.MAX_VOLATILITY
        change = session_mmr - base_mmr

        if abs(change) > max_change:
            session_mmr = base_mmr + (max_change if change > 0 else -max_change)

        return round(session_mmr, 1)

    @staticmethod
    def update_player_session_rating(player_id: int, db: Session) -> float:
        """Update session-weighted MMR for a player."""
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return 0.0

        session_mmr = SessionWeightedRatings.calculate_session_weighted_mmr(
            player_id, db
        )
        player.session_weighted_mmr = session_mmr
        player.last_session_weight_update = datetime.utcnow()

        db.commit()

        logger.info(f"Updated session MMR for player {player_id}: {session_mmr}")
        return session_mmr

    @staticmethod
    def update_all_players_session_ratings(db: Session) -> int:
        """Update session ratings for all players. Returns count updated."""
        players = db.query(Player).all()
        count = 0

        for player in players:
            SessionWeightedRatings.update_player_session_rating(player.id, db)
            count += 1

        logger.info(f"Updated session MMR for {count} players")
        return count
