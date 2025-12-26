"""
Achievement Service for SC2 MMR Tracking.

Handles achievement calculation, tracking, and awarding.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from ..models import (
    Player, Match, MatchPlayer, PlayerMatchMetrics, PlayerSynergy,
    Achievement, PlayerAchievement, AchievementCategory, AchievementRarity,
    ACHIEVEMENT_DEFINITIONS,
)


class AchievementService:
    """Service for calculating and awarding achievements."""

    @staticmethod
    def init_achievements(db: Session) -> int:
        """
        Initialize achievement definitions in the database.
        Returns the number of achievements created.
        """
        created = 0
        for achievement_def in ACHIEVEMENT_DEFINITIONS:
            existing = db.query(Achievement).filter(
                Achievement.code == achievement_def["code"]
            ).first()

            if not existing:
                achievement = Achievement(
                    code=achievement_def["code"],
                    name=achievement_def["name"],
                    description=achievement_def["description"],
                    flavor_text=achievement_def.get("flavor_text"),
                    category=achievement_def["category"],
                    rarity=achievement_def["rarity"],
                    icon=achievement_def.get("icon"),
                    color=achievement_def.get("color"),
                    requirement_type=achievement_def["requirement_type"],
                    requirement_threshold=achievement_def["requirement_threshold"],
                    requirement_extra=achievement_def.get("requirement_extra"),
                    points=achievement_def.get("points", 10),
                    is_hidden=achievement_def.get("is_hidden", False),
                    is_active=achievement_def.get("is_active", True),
                )
                db.add(achievement)
                created += 1

        db.commit()
        return created

    @staticmethod
    def get_player_achievements(db: Session, player_id: int) -> List[Dict[str, Any]]:
        """Get all achievements for a player with full details."""
        achievements = db.query(PlayerAchievement, Achievement).join(
            Achievement, PlayerAchievement.achievement_id == Achievement.id
        ).filter(
            PlayerAchievement.player_id == player_id
        ).order_by(desc(PlayerAchievement.earned_at)).all()

        return [
            {
                "id": pa.id,
                "code": a.code,
                "name": a.name,
                "description": a.description,
                "flavor_text": a.flavor_text,
                "category": a.category.value,
                "rarity": a.rarity.value,
                "icon": a.icon,
                "color": a.color,
                "points": a.points,
                "is_hidden": a.is_hidden,
                "earned_at": pa.earned_at.isoformat(),
                "trigger_value": pa.trigger_value,
                "is_featured": pa.is_featured,
            }
            for pa, a in achievements
        ]

    @staticmethod
    def get_available_achievements(db: Session, player_id: int) -> List[Dict[str, Any]]:
        """Get all achievements a player hasn't earned yet (excluding hidden ones)."""
        earned_ids = db.query(PlayerAchievement.achievement_id).filter(
            PlayerAchievement.player_id == player_id
        ).subquery()

        available = db.query(Achievement).filter(
            and_(
                Achievement.id.notin_(earned_ids),
                Achievement.is_active == True,
                Achievement.is_hidden == False,
            )
        ).order_by(Achievement.category, Achievement.rarity).all()

        return [
            {
                "code": a.code,
                "name": a.name,
                "description": a.description,
                "category": a.category.value,
                "rarity": a.rarity.value,
                "icon": a.icon,
                "points": a.points,
                "requirement_type": a.requirement_type,
                "requirement_threshold": a.requirement_threshold,
            }
            for a in available
        ]

    @staticmethod
    def award_achievement(
        db: Session,
        player_id: int,
        achievement_code: str,
        match_id: Optional[int] = None,
        trigger_value: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Award an achievement to a player.
        Returns the achievement details if newly awarded, None if already has it.
        """
        achievement = db.query(Achievement).filter(
            Achievement.code == achievement_code
        ).first()

        if not achievement:
            return None

        # Check if already earned
        existing = db.query(PlayerAchievement).filter(
            and_(
                PlayerAchievement.player_id == player_id,
                PlayerAchievement.achievement_id == achievement.id,
            )
        ).first()

        if existing:
            return None

        # Award it!
        player_achievement = PlayerAchievement(
            player_id=player_id,
            achievement_id=achievement.id,
            trigger_match_id=match_id,
            trigger_value=trigger_value,
        )
        db.add(player_achievement)
        db.commit()

        return {
            "code": achievement.code,
            "name": achievement.name,
            "description": achievement.description,
            "flavor_text": achievement.flavor_text,
            "category": achievement.category.value,
            "rarity": achievement.rarity.value,
            "icon": achievement.icon,
            "points": achievement.points,
            "earned_at": player_achievement.earned_at.isoformat(),
            "trigger_value": trigger_value,
        }

    @classmethod
    def check_and_award_all(
        cls,
        db: Session,
        player_id: int,
        match_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check all achievements for a player and award any newly earned ones.
        Should be called after each match.
        Returns list of newly awarded achievements.
        """
        newly_awarded = []
        player = db.query(Player).filter(Player.id == player_id).first()

        if not player:
            return newly_awarded

        # Get player's stats
        stats = cls._calculate_player_stats(db, player_id)

        # Get all active achievements the player doesn't have
        earned_codes = {
            pa.achievement.code for pa in db.query(PlayerAchievement).join(Achievement).filter(
                PlayerAchievement.player_id == player_id
            ).all()
        }

        all_achievements = db.query(Achievement).filter(Achievement.is_active == True).all()

        for achievement in all_achievements:
            if achievement.code in earned_codes:
                continue

            should_award, trigger_value = cls._check_achievement(
                db, player, achievement, stats, match_id
            )

            if should_award:
                result = cls.award_achievement(
                    db, player_id, achievement.code, match_id, trigger_value
                )
                if result:
                    newly_awarded.append(result)

        return newly_awarded

    @classmethod
    def _calculate_player_stats(cls, db: Session, player_id: int) -> Dict[str, Any]:
        """Calculate comprehensive stats for achievement checking."""
        player = db.query(Player).filter(Player.id == player_id).first()

        # Get match history for streak calculations
        match_history = db.query(MatchPlayer).filter(
            MatchPlayer.player_id == player_id
        ).join(Match).order_by(Match.played_at).all()

        # Calculate streaks
        win_streak, max_win_streak = 0, 0
        loss_streak, max_loss_streak = 0, 0

        for mp in match_history:
            if mp.won:
                win_streak += 1
                loss_streak = 0
                max_win_streak = max(max_win_streak, win_streak)
            else:
                loss_streak += 1
                win_streak = 0
                max_loss_streak = max(max_loss_streak, loss_streak)

        # Get max damage, kills from matches
        max_damage = db.query(func.max(PlayerMatchMetrics.damage_dealt)).join(
            MatchPlayer, PlayerMatchMetrics.match_player_id == MatchPlayer.id
        ).filter(MatchPlayer.player_id == player_id).scalar() or 0

        max_kills = db.query(func.max(PlayerMatchMetrics.units_killed)).join(
            MatchPlayer, PlayerMatchMetrics.match_player_id == MatchPlayer.id
        ).filter(MatchPlayer.player_id == player_id).scalar() or 0

        max_resources = db.query(func.max(PlayerMatchMetrics.total_resources_collected)).join(
            MatchPlayer, PlayerMatchMetrics.match_player_id == MatchPlayer.id
        ).filter(MatchPlayer.player_id == player_id).scalar() or 0

        # Get synergy stats
        synergies = db.query(PlayerSynergy).filter(
            or_(
                PlayerSynergy.player1_id == player_id,
                PlayerSynergy.player2_id == player_id,
            )
        ).all()

        best_duo_wins = max([s.wins_together for s in synergies], default=0)
        best_duo_winrate = 0
        for s in synergies:
            if s.games_together >= 10:
                wr = (s.wins_together / s.games_together) * 100
                best_duo_winrate = max(best_duo_winrate, wr)

        # Get unique play days
        unique_days = db.query(func.count(func.distinct(func.date(Match.played_at)))).join(
            MatchPlayer, MatchPlayer.match_id == Match.id
        ).filter(MatchPlayer.player_id == player_id).scalar() or 0

        return {
            "total_games": player.total_games,
            "wins": player.wins,
            "losses": player.losses,
            "mmr": player.hybrid_mmr or player.mmr,
            "terran_games": player.terran_games,
            "protoss_games": player.protoss_games,
            "zerg_games": player.zerg_games,
            "max_win_streak": max_win_streak,
            "current_win_streak": win_streak,
            "max_loss_streak": max_loss_streak,
            "current_loss_streak": loss_streak,
            "max_damage": max_damage,
            "max_kills": max_kills,
            "max_resources": max_resources,
            "best_duo_wins": best_duo_wins,
            "best_duo_winrate": best_duo_winrate,
            "unique_play_days": unique_days,
        }

    @classmethod
    def _check_achievement(
        cls,
        db: Session,
        player: Player,
        achievement: Achievement,
        stats: Dict[str, Any],
        match_id: Optional[int],
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if a player should receive an achievement.
        Returns (should_award, trigger_value).
        """
        req_type = achievement.requirement_type
        threshold = achievement.requirement_threshold

        # Milestone achievements
        if req_type == "games_played":
            return stats["total_games"] >= threshold, stats["total_games"]

        if req_type == "wins":
            return stats["wins"] >= threshold, stats["wins"]

        # Streak achievements
        if req_type == "win_streak":
            return stats["max_win_streak"] >= threshold, stats["max_win_streak"]

        if req_type == "loss_streak":
            return stats["max_loss_streak"] >= threshold, stats["max_loss_streak"]

        # Combat achievements
        if req_type == "match_damage":
            return stats["max_damage"] >= threshold, stats["max_damage"]

        if req_type == "match_kills":
            return stats["max_kills"] >= threshold, stats["max_kills"]

        if req_type == "match_resources":
            return stats["max_resources"] >= threshold, stats["max_resources"]

        # Race variety achievements
        if req_type == "race_games":
            import json
            extra = json.loads(achievement.requirement_extra or '{}')
            race = extra.get("race", "")
            race_games = {
                "Terran": stats["terran_games"],
                "Protoss": stats["protoss_games"],
                "Zerg": stats["zerg_games"],
            }.get(race, 0)
            return race_games >= threshold, race_games

        if req_type == "race_variety":
            # All 3 races with threshold games each
            min_games = min(stats["terran_games"], stats["protoss_games"], stats["zerg_games"])
            return min_games >= threshold, min_games

        if req_type == "single_race_games":
            max_race = max(stats["terran_games"], stats["protoss_games"], stats["zerg_games"])
            other_races = stats["total_games"] - max_race
            # 90%+ of games on one race
            if stats["total_games"] >= threshold and max_race >= stats["total_games"] * 0.9:
                return True, max_race
            return False, max_race

        # Teamwork achievements
        if req_type == "duo_wins":
            return stats["best_duo_wins"] >= threshold, stats["best_duo_wins"]

        if req_type == "duo_winrate":
            return stats["best_duo_winrate"] >= threshold, stats["best_duo_winrate"]

        # MMR achievements
        if req_type == "mmr_reached":
            return stats["mmr"] >= threshold, stats["mmr"]

        # Time-based achievements
        if req_type == "unique_days":
            return stats["unique_play_days"] >= threshold, stats["unique_play_days"]

        # Match-specific achievements (need current match data)
        if match_id and req_type in [
            "fast_win", "long_win", "upset_win", "first_damage",
            "glass_cannon", "tank_win", "low_spend_win", "combat_damage_ratio"
        ]:
            return cls._check_match_specific_achievement(
                db, player.id, match_id, req_type, threshold
            )

        return False, None

    @classmethod
    def _check_match_specific_achievement(
        cls,
        db: Session,
        player_id: int,
        match_id: int,
        req_type: str,
        threshold: float,
    ) -> Tuple[bool, Optional[float]]:
        """Check achievements that depend on specific match performance."""
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return False, None

        mp = db.query(MatchPlayer).filter(
            and_(MatchPlayer.match_id == match_id, MatchPlayer.player_id == player_id)
        ).first()

        if not mp or not mp.won:
            return False, None

        metrics = db.query(PlayerMatchMetrics).filter(
            PlayerMatchMetrics.match_player_id == mp.id
        ).first()

        # Fast win (under threshold seconds)
        if req_type == "fast_win":
            if match.duration_seconds <= threshold:
                return True, match.duration_seconds

        # Long win (over threshold seconds)
        if req_type == "long_win":
            if match.duration_seconds >= threshold:
                return True, match.duration_seconds

        # Upset win (won despite low predicted chance)
        if req_type == "upset_win":
            if mp.team_number == 1 and match.predicted_team1_win_prob:
                win_prob = match.predicted_team1_win_prob * 100
            elif mp.team_number == 2 and match.predicted_team2_win_prob:
                win_prob = match.predicted_team2_win_prob * 100
            else:
                return False, None

            if win_prob <= threshold:
                return True, win_prob

        if metrics:
            # Glass cannon: top damage AND top damage taken
            if req_type == "glass_cannon":
                team_metrics = cls._get_team_metrics(db, match_id, mp.team_number)
                if team_metrics:
                    max_damage = max(m.damage_dealt for m in team_metrics)
                    max_taken = max(m.damage_taken for m in team_metrics)
                    if (metrics.damage_dealt == max_damage and
                        metrics.damage_taken == max_taken):
                        return True, metrics.damage_dealt

        return False, None

    @staticmethod
    def _get_team_metrics(
        db: Session, match_id: int, team_number: int
    ) -> List[PlayerMatchMetrics]:
        """Get all metrics for a team in a match."""
        return db.query(PlayerMatchMetrics).join(
            MatchPlayer, PlayerMatchMetrics.match_player_id == MatchPlayer.id
        ).filter(
            and_(
                MatchPlayer.match_id == match_id,
                MatchPlayer.team_number == team_number,
            )
        ).all()

    @staticmethod
    def get_achievement_leaderboard(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
        """Get players ranked by achievement points."""
        results = db.query(
            Player.id,
            Player.name,
            func.count(PlayerAchievement.id).label("total_achievements"),
            func.sum(Achievement.points).label("total_points"),
        ).join(
            PlayerAchievement, Player.id == PlayerAchievement.player_id
        ).join(
            Achievement, PlayerAchievement.achievement_id == Achievement.id
        ).group_by(Player.id).order_by(desc("total_points")).limit(limit).all()

        return [
            {
                "player_id": r.id,
                "name": r.name,
                "total_achievements": r.total_achievements,
                "total_points": r.total_points or 0,
            }
            for r in results
        ]

    @staticmethod
    def get_rarest_achievements(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the rarest achievements (fewest players have them)."""
        results = db.query(
            Achievement,
            func.count(PlayerAchievement.id).label("earned_count"),
        ).outerjoin(
            PlayerAchievement, Achievement.id == PlayerAchievement.achievement_id
        ).filter(
            Achievement.is_active == True
        ).group_by(Achievement.id).order_by("earned_count").limit(limit).all()

        return [
            {
                "code": a.code,
                "name": a.name,
                "description": a.description,
                "rarity": a.rarity.value,
                "icon": a.icon,
                "earned_count": count,
            }
            for a, count in results
        ]

    @staticmethod
    def get_recent_achievements(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the most recently earned achievements across all players."""
        results = db.query(PlayerAchievement, Achievement, Player).join(
            Achievement, PlayerAchievement.achievement_id == Achievement.id
        ).join(
            Player, PlayerAchievement.player_id == Player.id
        ).order_by(desc(PlayerAchievement.earned_at)).limit(limit).all()

        return [
            {
                "player_name": p.name,
                "player_id": p.id,
                "achievement_code": a.code,
                "achievement_name": a.name,
                "achievement_icon": a.icon,
                "rarity": a.rarity.value,
                "earned_at": pa.earned_at.isoformat(),
            }
            for pa, a, p in results
        ]
