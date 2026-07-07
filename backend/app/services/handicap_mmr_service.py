import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models import Player, Match, MatchPlayer
from ..rating_system import RatingSystem

logger = logging.getLogger(__name__)


class HandicapCorrectedMMRService:
    MIN_GAMES = 15
    OUTPERFORMANCE_MULTIPLIER = 3000

    @staticmethod
    def _parse_dt(dt_val: Any) -> datetime:
        if not dt_val:
            return datetime.utcnow()
        if isinstance(dt_val, str):
            clean_str = dt_val.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_str).replace(tzinfo=None)
        if hasattr(dt_val, "replace"):
            return dt_val.replace(tzinfo=None)
        return datetime.utcnow()

    @staticmethod
    def calculate_expected_win_rate(
        handicap_per_player: float, team_size: int = 1
    ) -> float:
        dampening = 1.0 / (1.0 + (team_size - 1) * 0.15)
        return 1 / (1 + 10 ** (-(handicap_per_player * dampening) / 400))

    @staticmethod
    def get_player_handicap_stats(player_id: int, db: Session) -> Optional[Dict]:
        query = text("""
            SELECT
                mp.won,
                (SELECT SUM(mp2.mmr_before)
                 FROM match_players mp2
                 WHERE mp2.match_id = m.id AND mp2.team_number = mp.team_number) as my_team_mmr,
                (SELECT SUM(mp2.mmr_before)
                 FROM match_players mp2
                 WHERE mp2.match_id = m.id AND mp2.team_number != mp.team_number) as opp_team_mmr,
                (SELECT COUNT(*)
                 FROM match_players mp2
                 WHERE mp2.match_id = m.id AND mp2.team_number = mp.team_number) as my_team_size,
                m.played_at,
                m.map_name
            FROM matches m
            JOIN match_players mp ON mp.match_id = m.id
            WHERE mp.player_id = :player_id
        """)

        try:
            result = db.execute(query, {"player_id": player_id})
            matches = result.fetchall()
        except Exception as e:
            logger.error(f"SQL failure for player {player_id}: {e}")
            return None

        if len(matches) < HandicapCorrectedMMRService.MIN_GAMES:
            return None

        map_stats = {}
        for row in matches:
            m_name = row[5]
            is_win = row[0]
            if m_name not in map_stats:
                map_stats[m_name] = {"w": 0, "t": 0}
            map_stats[m_name]["t"] += 1
            if is_win:
                map_stats[m_name]["w"] += 1

        total_valid = 0
        weighted_outperf_sum = 0.0
        weighted_handicap_sum = 0.0
        weighted_total = 0.0
        now = datetime.utcnow()

        for won, my_team_mmr, opp_team_mmr, my_size, played_at, map_name in matches:
            if my_team_mmr is None or opp_team_mmr is None or not my_size:
                continue

            total_valid += 1

            dt = HandicapCorrectedMMRService._parse_dt(played_at)
            days_ago = (now - dt).total_seconds() / 86400
            weight = RatingSystem.calculate_recency_weight(days_ago)

            handicap_per_player = (my_team_mmr - opp_team_mmr) / my_size
            expected_wr = HandicapCorrectedMMRService.calculate_expected_win_rate(
                handicap_per_player, my_size
            )

            match_outperf = (1.0 if won else 0.0) - expected_wr

            weighted_outperf_sum += match_outperf * weight
            weighted_handicap_sum += handicap_per_player * weight
            weighted_total += weight

        if total_valid < HandicapCorrectedMMRService.MIN_GAMES or weighted_total < 0.1:
            return None

        return {
            "total_games": total_valid,
            "avg_handicap": weighted_handicap_sum / weighted_total,
            "outperformance": weighted_outperf_sum / weighted_total,
        }

    @staticmethod
    def calculate_corrected_mmr(
        player: Player, db: Session
    ) -> Optional[Tuple[float, float, float, float]]:
        stats = HandicapCorrectedMMRService.get_player_handicap_stats(player.id, db)
        if not stats:
            return None

        confidence = min(1.0, player.total_games / 40.0)

        lp_dt = HandicapCorrectedMMRService._parse_dt(player.last_played)
        now = datetime.utcnow()
        days_ago = (now - lp_dt).total_seconds() / 86400

        if days_ago <= 14:
            inactivity_weight = 1.0
        else:
            inactivity_weight = math.pow(0.5, (days_ago - 14) / 45.0)

        op_val = stats["outperformance"]
        if op_val < 0:
            op_val *= 0.75

        bonus = (
            op_val
            * HandicapCorrectedMMRService.OUTPERFORMANCE_MULTIPLIER
            * confidence
            * inactivity_weight
        )
        hc_mmr = (player.mmr or 2000) + bonus

        combat_score = player.avg_combat_score or 20
        if combat_score > 60:
            combat_score = 60

        combat_bonus = combat_score * 25
        eco_bonus = (player.avg_economic_score or 50) * 4
        eff_bonus = (player.avg_efficiency_score or 50) * 2

        perf_bonus = min(1200, combat_bonus + eco_bonus + eff_bonus)

        return (
            hc_mmr,
            stats["avg_handicap"],
            stats["outperformance"] * 100 * confidence * inactivity_weight,
            perf_bonus,
        )

    @staticmethod
    def update_player_corrected_mmr(player: Player, db: Session) -> bool:
        result = HandicapCorrectedMMRService.calculate_corrected_mmr(player, db)
        if not result:
            return False

        hc_mmr, avg_handicap, outperf_pct, perf_bonus = result
        player.handicap_corrected_mmr = hc_mmr
        player.avg_team_handicap = avg_handicap
        player.outperformance_pct = outperf_pct
        player.unified_mmr = hc_mmr + perf_bonus
        return True

    @staticmethod
    def update_all_players(db: Session) -> int:
        db.execute(
            text(
                "UPDATE players SET avg_combat_score = (SELECT AVG(pmm.combat_score) FROM player_match_metrics pmm JOIN match_players mp ON pmm.match_player_id = mp.id WHERE mp.player_id = players.id) WHERE total_games > 0"
            )
        )

        db.execute(
            text(
                f"UPDATE players SET handicap_corrected_mmr = NULL, unified_mmr = NULL, outperformance_pct = NULL WHERE total_games < {HandicapCorrectedMMRService.MIN_GAMES} OR is_core_player = 0 OR is_ai = 1"
            )
        )

        players = (
            db.query(Player)
            .filter(
                Player.total_games >= HandicapCorrectedMMRService.MIN_GAMES,
                Player.is_core_player == 1,
                Player.is_ai == 0,
            )
            .all()
        )

        updated = 0
        for p in players:
            if HandicapCorrectedMMRService.update_player_corrected_mmr(p, db):
                updated += 1

        db.commit()
        return updated
