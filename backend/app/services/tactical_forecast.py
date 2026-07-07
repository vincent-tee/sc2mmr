import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Player, Match, MatchPlayer, PerformanceFeatures, PlayerMatchMetrics

logger = logging.getLogger(__name__)


class TacticalForecastService:
    """
    Service to provide strategic insights for upcoming matches.
    Identifies playstyles, map specialties, and tactical risks.
    """

    @staticmethod
    def get_forecast(
        player_ids: List[int], map_name: Optional[str], db: Session
    ) -> Dict[str, Any]:
        """
        Generate tactical insights for a group of players on a specific map.
        """
        forecast = {
            "map_specialists": [],
            "playstyle_alerts": [],
            "synergy_warnings": [],
            "key_matchups": [],
        }

        for pid in player_ids:
            player = db.query(Player).filter(Player.id == pid).first()
            if not player:
                continue

            # 1. Map Specialization
            if map_name:
                map_stats = (
                    db.query(
                        func.count(Match.id).label("total"),
                        func.sum(MatchPlayer.won).label("wins"),
                    )
                    .join(MatchPlayer)
                    .filter(MatchPlayer.player_id == pid, Match.map_name == map_name)
                    .first()
                )

                if map_stats and map_stats.total >= 5:
                    win_rate = map_stats.wins / map_stats.total
                    if win_rate >= 0.7:
                        forecast["map_specialists"].append(
                            {
                                "player_name": player.name,
                                "type": "Expert",
                                "win_rate": round(win_rate * 100, 1),
                                "games": map_stats.total,
                            }
                        )
                    elif win_rate <= 0.3:
                        forecast["map_specialists"].append(
                            {
                                "player_name": player.name,
                                "type": "Struggler",
                                "win_rate": round(win_rate * 100, 1),
                                "games": map_stats.total,
                            }
                        )

            # 2. Playstyle / Archetype (from recent games)
            recent_archetype = (
                db.query(PerformanceFeatures.detected_build_type)
                .join(MatchPlayer)
                .filter(MatchPlayer.player_id == pid)
                .order_by(MatchPlayer.id.desc())
                .limit(10)
                .all()
            )

            if recent_archetype:
                types = [t[0] for t in recent_archetype if t[0]]
                if types:
                    most_common = max(set(types), key=types.count)
                    occurrence = types.count(most_common) / len(types)

                    if most_common in ["rush", "cheese"] and occurrence >= 0.4:
                        forecast["playstyle_alerts"].append(
                            {
                                "player_name": player.name,
                                "alert": f"Aggression Risk ({most_common.capitalize()})",
                                "confidence": round(occurrence * 100, 1),
                            }
                        )
                    elif most_common == "macro" and occurrence >= 0.7:
                        forecast["playstyle_alerts"].append(
                            {
                                "player_name": player.name,
                                "alert": "Greedy Macro Player",
                                "confidence": round(occurrence * 100, 1),
                            }
                        )

        return forecast
