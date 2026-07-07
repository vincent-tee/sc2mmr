"""
Achievement API endpoints for SC2 MMR Tracking.

Provides endpoints for:
- Viewing player achievements
- Achievement leaderboard
- Recent achievements feed
- Achievement initialization
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..auth import require_admin
from ..database import get_db
from ..services import AchievementService

router = APIRouter(prefix="/achievements", tags=["achievements"])


# ============================================================================
# Response Models
# ============================================================================


class AchievementResponse(BaseModel):
    """Achievement details."""

    code: str
    name: str
    description: str
    flavor_text: Optional[str]
    category: str
    rarity: str
    icon: Optional[str]
    color: Optional[str]
    points: int
    is_hidden: bool = False
    earned_at: Optional[str] = None
    trigger_value: Optional[float] = None
    is_featured: bool = False


class PlayerAchievementsResponse(BaseModel):
    """Player's achievements summary."""

    player_id: int
    player_name: str
    total_achievements: int
    total_points: int
    awarded: List[AchievementResponse]
    available_achievements: Optional[List[dict]] = None


class AchievementLeaderboardEntry(BaseModel):
    """Leaderboard entry."""

    rank: int
    player_id: int
    name: str
    total_achievements: int
    total_points: int


class RecentAchievementEntry(BaseModel):
    """Recent achievement feed entry."""

    player_name: str
    player_id: int
    achievement_code: str
    achievement_name: str
    achievement_icon: Optional[str]
    rarity: str
    earned_at: str


class InitResponse(BaseModel):
    """Initialization response."""

    success: bool
    created: int
    message: str


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/player/{player_id}", response_model=PlayerAchievementsResponse)
async def get_player_achievements(
    player_id: int,
    include_available: bool = Query(
        False, description="Include achievements not yet earned"
    ),
    db: Session = Depends(get_db),
):
    """
    Get all achievements for a specific player.

    Returns:
    - Earned achievements with details
    - Total points
    - Optionally: available achievements to earn
    """
    from ..models import Player

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    achievements = AchievementService.get_player_achievements(db, player_id)
    total_points = sum(a.get("points", 0) for a in achievements)

    response = {
        "player_id": player_id,
        "player_name": player.name,
        "total_achievements": len(achievements),
        "total_points": total_points,
        "awarded": achievements,
    }

    if include_available:
        response["available_achievements"] = (
            AchievementService.get_available_achievements(db, player_id)
        )

    return response


@router.get("/leaderboard", response_model=List[AchievementLeaderboardEntry])
async def get_achievement_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get the achievement points leaderboard.

    Players ranked by total achievement points earned.
    """
    results = AchievementService.get_achievement_leaderboard(db, limit)

    return [
        {
            "rank": i + 1,
            "player_id": r["player_id"],
            "name": r["name"],
            "total_achievements": r["total_achievements"],
            "total_points": r["total_points"],
        }
        for i, r in enumerate(results)
    ]


@router.get("/recent", response_model=List[RecentAchievementEntry])
async def get_recent_achievements(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get the most recently earned achievements across all players.

    Perfect for a live feed on the homepage.
    """
    return AchievementService.get_recent_achievements(db, limit)


@router.get("/rarest")
async def get_rarest_achievements(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Get the rarest achievements (fewest players have earned them).

    Great for showing "Most Elite" achievements.
    """
    return AchievementService.get_rarest_achievements(db, limit)


@router.post("/check/{player_id}")
async def check_player_achievements(
    player_id: int,
    match_id: Optional[int] = Query(None, description="Specific match to check"),
    db: Session = Depends(get_db),
):
    """
    Check and award any newly earned achievements for a player.

    This is automatically called after each match, but can also be
    triggered manually to backfill achievements.
    """
    from ..models import Player

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    newly_awarded = AchievementService.check_and_award_all(db, player_id, match_id)

    return {
        "player_id": player_id,
        "player_name": player.name,
        "newly_awarded": newly_awarded,
        "count": len(newly_awarded),
    }


@router.post("/check-all", dependencies=[Depends(require_admin)])
async def check_all_player_achievements(
    db: Session = Depends(get_db),
):
    """
    Check and award achievements for ALL players.

    Use this to backfill achievements after adding new achievement types.
    May take a while for large player counts.
    """
    from ..models import Player

    players = db.query(Player).filter(Player.total_games > 0).all()
    results = []

    for player in players:
        newly_awarded = AchievementService.check_and_award_all(db, player.id)
        if newly_awarded:
            results.append(
                {
                    "player_id": player.id,
                    "player_name": player.name,
                    "newly_awarded": newly_awarded,
                    "count": len(newly_awarded),
                }
            )

    return {
        "players_checked": len(players),
        "players_with_new_achievements": len(results),
        "results": results,
    }


@router.post("/init", response_model=InitResponse)
async def initialize_achievements(db: Session = Depends(get_db)):
    """
    Initialize achievement definitions in the database.

    Should be called once during setup, or when new achievements are added.
    Safe to call multiple times (won't duplicate existing achievements).
    """
    created = AchievementService.init_achievements(db)

    return {
        "success": True,
        "created": created,
        "message": f"Created {created} new achievement definitions",
    }


@router.post("/player/{player_id}/feature/{achievement_code}")
async def feature_achievement(
    player_id: int,
    achievement_code: str,
    db: Session = Depends(get_db),
):
    """
    Set an achievement as the player's featured/showcase badge.

    Only one achievement can be featured at a time.
    """
    from ..models import PlayerAchievement, Achievement

    # Find the player's achievement
    player_achievement = (
        db.query(PlayerAchievement)
        .join(Achievement)
        .filter(
            PlayerAchievement.player_id == player_id,
            Achievement.code == achievement_code,
        )
        .first()
    )

    if not player_achievement:
        raise HTTPException(
            status_code=404,
            detail="Achievement not found or not earned by this player",
        )

    # Unfeature all other achievements
    db.query(PlayerAchievement).filter(
        PlayerAchievement.player_id == player_id,
        PlayerAchievement.is_featured == True,
    ).update({"is_featured": False})

    # Feature this one
    player_achievement.is_featured = True
    db.commit()

    return {
        "success": True,
        "featured_achievement": achievement_code,
    }


@router.get("/all")
async def get_all_achievements(
    include_hidden: bool = Query(False, description="Include hidden achievements"),
    db: Session = Depends(get_db),
):
    """
    Get all achievement definitions.

    Useful for displaying the achievement catalog/trophy case.
    """
    from ..models import Achievement

    query = db.query(Achievement).filter(Achievement.is_active == True)

    if not include_hidden:
        query = query.filter(Achievement.is_hidden == False)

    achievements = query.order_by(Achievement.category, Achievement.rarity).all()

    return [
        {
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
        }
        for a in achievements
    ]
