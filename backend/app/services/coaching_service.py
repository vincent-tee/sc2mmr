import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models import Player, MatchPlayer, PlayerMatchMetrics

logger = logging.getLogger(__name__)


class CoachingService:
    @staticmethod
    def get_tips(player_id: int, db: Session, limit: int = 2) -> List[str]:
        recent_losses = (
            db.query(MatchPlayer)
            .filter(MatchPlayer.player_id == player_id, MatchPlayer.won == 0)
            .order_by(MatchPlayer.id.desc())
            .limit(10)
            .all()
        )

        if not recent_losses:
            return ["No recent losses found. Keep up the good work!"]

        return CoachingService._stat_based_tips(player_id, db)[:limit]

    @staticmethod
    def _stat_based_tips(player_id: int, db: Session) -> List[str]:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return []

        from sqlalchemy import func

        avg_stats = (
            db.query(
                func.avg(Player.avg_combat_score).label("combat"),
                func.avg(Player.avg_economic_score).label("eco"),
                func.avg(Player.avg_aggression_score).label("apm"),
            )
            .filter(Player.total_games >= 15, Player.is_ai == 0)
            .first()
        )

        if not avg_stats:
            return ["Play more games to unlock personalized coaching."]

        tips = []
        if player.avg_combat_score is not None and player.avg_combat_score < (avg_stats.combat or 25) * 0.8:
            tips.append(
                "Focus on lethality: Your damage output is significantly below the squad average."
            )
        if player.avg_economic_score is not None and player.avg_economic_score < (avg_stats.eco or 50) * 0.8:
            tips.append(
                "Macro stability: Work on your worker production and resource collection."
            )

        if not tips:
            tips.append(
                "Your fundamentals are solid. Focus on map-specific strategies."
            )

        return tips[:2]
