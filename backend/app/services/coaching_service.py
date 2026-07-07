import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models import Player, MatchPlayer, PerformanceFeatures, PlayerMatchMetrics

logger = logging.getLogger(__name__)


class CoachingService:
    FEATURE_MAPPING = {
        "supply_block_diff": "Macro: You were supply blocked for significantly longer than your opponents.",
        "minerals_diff": "Economy: Your mineral collection rate was lower than the match average.",
        "combat_diff": "Combat: You dealt less effective damage or lost more army value than expected.",
        "teamfight_diff": "Teamwork: You were missing from key team engagements on the map.",
        "aggression_diff": "Playstyle: You were either too passive or over-extended compared to your opponents.",
        "form_trend_diff": "Momentum: You are currently on a downward performance trend.",
        "spending_diff": "Efficiency: Your Spending Quotient (SQ) indicates unspent resources during critical phases.",
    }

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

        negative_impacts: Dict[str, float] = {}

        for mp in recent_losses:
            perf = (
                db.query(PerformanceFeatures)
                .filter(PerformanceFeatures.match_player_id == mp.id)
                .first()
            )

            if perf and perf.ml_shap_values:
                for entry in perf.ml_shap_values:
                    feature = entry.get("feature")
                    impact = entry.get("impact")
                    if feature in CoachingService.FEATURE_MAPPING and impact < 0:
                        negative_impacts[feature] = negative_impacts.get(
                            feature, 0
                        ) + abs(impact)

        if not negative_impacts:
            return CoachingService._generate_fallback_tips(player_id, db)

        sorted_features = sorted(
            negative_impacts.items(), key=lambda x: x[1], reverse=True
        )

        tips = []
        for feature, _ in sorted_features[:limit]:
            tips.append(CoachingService.FEATURE_MAPPING[feature])

        return tips

    @staticmethod
    def _generate_fallback_tips(player_id: int, db: Session) -> List[str]:
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
        if player.avg_combat_score < (avg_stats.combat or 25) * 0.8:
            tips.append(
                "Focus on lethality: Your damage output is significantly below the squad average."
            )
        if player.avg_economic_score < (avg_stats.eco or 50) * 0.8:
            tips.append(
                "Macro stability: Work on your worker production and resource collection."
            )

        if not tips:
            tips.append(
                "Your fundamentals are solid. Focus on map-specific strategies."
            )

        return tips[:2]
