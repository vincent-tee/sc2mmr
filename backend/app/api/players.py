"""
API endpoints for player statistics and management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from ..auth import require_admin
from ..database import get_db
from ..models import Player, MatchPlayer, Match
from ..rating_system import RatingSystem
from ..impact_service import ImpactService
from ..replay_parser import ReplayData, PlayerData
from ..services.rating_recalculation import recalculate_ratings_in_place
from pydantic import BaseModel


router = APIRouter(prefix="/players", tags=["players"])

# "New player" is about game count (provisional rating, not yet earned a
# stable rank); "active" is about recency (real last match date). Kept as
# two independent signals so a brand-new but currently-playing member isn't
# lumped in with a veteran who stopped playing years ago.
#
# New players get a *shorter* inactivity window than established players:
# someone who played a handful of games once, years ago, and never came
# back shouldn't linger in "new player" views indefinitely.
NEW_PLAYER_GAME_THRESHOLD = 15
NEW_PLAYER_INACTIVE_DAYS = 180  # ~6 months
INACTIVE_DAYS_THRESHOLD = 730  # ~2 years, for established (>=15 games) players


def compute_activity_flags(
    total_games: int, last_played: Optional[datetime], now: Optional[datetime] = None
) -> Tuple[bool, bool, Optional[int]]:
    """Returns (is_new, is_active, days_since_played)."""
    now = now or datetime.utcnow()
    is_new = total_games < NEW_PLAYER_GAME_THRESHOLD
    days_since_played = (now - last_played).days if last_played else None
    if days_since_played is None:
        is_active = True
    elif is_new:
        is_active = days_since_played <= NEW_PLAYER_INACTIVE_DAYS
    else:
        is_active = days_since_played <= INACTIVE_DAYS_THRESHOLD
    return is_new, is_active, days_since_played


def active_only_clause(now: Optional[datetime] = None):
    """SQLAlchemy filter: last_played within the games-count-appropriate window."""
    now = now or datetime.utcnow()
    new_cutoff = now - timedelta(days=NEW_PLAYER_INACTIVE_DAYS)
    established_cutoff = now - timedelta(days=INACTIVE_DAYS_THRESHOLD)
    return or_(
        and_(Player.total_games < NEW_PLAYER_GAME_THRESHOLD, Player.last_played >= new_cutoff),
        and_(Player.total_games >= NEW_PLAYER_GAME_THRESHOLD, Player.last_played >= established_cutoff),
    )


def _calculate_recent_form(db: Session, player_id: int, num_games: int = 5) -> Optional[float]:
    """Calculate recent form (win rate) from last N games for a single player."""
    matches = (
        db.query(MatchPlayer)
        .join(Match)
        .filter(MatchPlayer.player_id == player_id)
        .order_by(desc(Match.played_at))
        .limit(num_games)
        .all()
    )
    if not matches:
        return None
    wins = sum(1 for mp in matches if mp.won)
    return wins / len(matches)


def _batch_recent_form(db: Session, player_ids: List[int], num_games: int = 5) -> dict:
    """Batch-calculate recent form for multiple players — 2 queries total instead of N+1."""
    if not player_ids:
        return {}
    from sqlalchemy import func, case
    # For each player grab the last `num_games` MatchPlayer rows ordered by match date.
    # We use a subquery with ROW_NUMBER to rank each player's matches by recency.
    inner = (
        db.query(
            MatchPlayer.player_id,
            MatchPlayer.won,
            func.row_number()
            .over(
                partition_by=MatchPlayer.player_id,
                order_by=desc(Match.played_at),
            )
            .label("rn"),
        )
        .join(Match, MatchPlayer.match_id == Match.id)
        .filter(MatchPlayer.player_id.in_(player_ids))
        .subquery()
    )
    rows = (
        db.query(
            inner.c.player_id,
            func.count().label("total"),
            func.sum(case((inner.c.won == True, 1), else_=0)).label("wins"),
        )
        .filter(inner.c.rn <= num_games)
        .group_by(inner.c.player_id)
        .all()
    )
    return {
        row.player_id: row.wins / row.total if row.total else None
        for row in rows
    }


def _player_to_response(p: "Player", recent_form: Optional[float] = None) -> "PlayerResponse":
    is_new, is_active, days_since_played = compute_activity_flags(p.total_games, p.last_played)
    return PlayerResponse(
        id=p.id,
        name=p.name,
        mu=p.mu,
        sigma=p.sigma,
        mmr=p.mmr,
        unified_mmr=p.unified_mmr,
        recency_weighted_mmr=p.recency_weighted_mmr,
        hybrid_mmr=p.hybrid_mmr,
        avg_pim=p.avg_pim,
        total_games=p.total_games,
        wins=p.wins,
        losses=p.losses,
        win_rate=p.win_rate,
        favorite_race=p.favorite_race,
        is_core_player=bool(p.is_core_player),
        is_ai=bool(p.is_ai),
        last_played=p.last_played,
        recent_form=recent_form,
        terran_games=p.terran_games,
        protoss_games=p.protoss_games,
        zerg_games=p.zerg_games,
        random_games=p.random_games,
        is_new=is_new,
        is_active=is_active,
        days_since_played=days_since_played,
    )


# Request/Response models
class PlayerResponse(BaseModel):
    """Response model for player data."""

    id: int
    name: str
    mu: float
    sigma: float
    mmr: float
    unified_mmr: Optional[float] = None
    recency_weighted_mmr: Optional[float] = None
    hybrid_mmr: Optional[float] = None
    avg_pim: Optional[float] = None
    total_games: int
    wins: int
    losses: int
    win_rate: float
    favorite_race: str
    is_core_player: bool
    is_ai: bool = False
    last_played: Optional[datetime]
    recent_form: Optional[float] = None  # Win rate from last 5 games (0.0-1.0)
    terran_games: int = 0
    protoss_games: int = 0
    zerg_games: int = 0
    random_games: int = 0
    is_new: bool = False  # fewer than NEW_PLAYER_GAME_THRESHOLD games — provisional rating
    is_active: bool = True  # played within INACTIVE_DAYS_THRESHOLD days
    days_since_played: Optional[int] = None

    class Config:
        from_attributes = True


class PlayerDetailResponse(BaseModel):
    """Detailed player response with race statistics."""

    id: int
    name: str
    mu: float
    sigma: float
    mmr: float
    unified_mmr: Optional[float] = None
    recency_weighted_mmr: Optional[float]
    # Hybrid MMR System (SPEC-ML-001)
    hybrid_mmr: Optional[float] = None
    avg_pim: Optional[float] = None
    total_games: int
    wins: int
    losses: int
    win_rate: float
    is_core_player: bool
    is_ai: bool = False
    last_played: Optional[datetime]
    race_stats: dict
    recent_matches: List[dict]

    class Config:
        from_attributes = True


class PlayerRankingResponse(BaseModel):
    """Player ranking response."""

    rank: int
    player: PlayerResponse

    class Config:
        from_attributes = True


class MMRHistoryEntry(BaseModel):
    """Entry for MMR history chart."""

    match_id: int
    played_at: datetime
    mmr: float
    mmr_change: float
    won: bool
    map_name: str


class PlayerHistoryResponse(BaseModel):
    """Response model for player MMR history."""

    player_id: int
    player_name: str
    history: List[MMRHistoryEntry]


class CreatePlayerRequest(BaseModel):
    """Request to create a new player."""

    name: str
    is_core_player: bool = True


class CalibratePlayerRequest(BaseModel):
    """Request to calibrate a new outsider player."""

    name: str
    similar_to_player_id: int


@router.get("/", response_model=List[PlayerResponse])
def get_all_players(
    core_only: bool = False,
    min_games: int = 0,
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Player).filter(Player.is_ai == 0)
    if core_only:
        query = query.filter(Player.is_core_player == 1)
    if min_games > 0:
        query = query.filter(Player.total_games >= min_games)
    if active_only:
        # Recency-based, independent of min_games — a brand-new player who
        # just played is "active" even though they'd fail a games threshold.
        # New (<15-game) players use a tighter 6-month window than the
        # 2-year window for established players, so a one-off dabbler from
        # years ago doesn't linger in "new player" views indefinitely.
        query = query.filter(active_only_clause())

    players = query.all()

    # Batch recent_form: single SQL query for all players instead of N+1
    player_ids = [p.id for p in players]
    recent_form_map = _batch_recent_form(db, player_ids)

    return [_player_to_response(p, recent_form=recent_form_map.get(p.id)) for p in players]


@router.get("/rankings", response_model=List[PlayerRankingResponse])
def get_player_rankings(
    min_games: int = 5, core_only: bool = False, db: Session = Depends(get_db)
):
    query = db.query(Player).filter(Player.total_games >= min_games, Player.is_ai == 0)

    if core_only:
        query = query.filter(Player.is_core_player == 1)

    # Rating of record = display MMR (owner decision 2026-07-02, rating
    # consolidation campaign Phase 5); unified_mmr is a display-only stat.
    players = query.order_by(desc(Player.mmr)).all()

    return [
        PlayerRankingResponse(rank=i + 1, player=_player_to_response(p))
        for i, p in enumerate(players)
    ]


@router.get("/{player_id}", response_model=PlayerDetailResponse)
def get_player_details(
    player_id: int,
    recent_matches_limit: int = 10,
    recent_matches_offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific player.

    Args:
        player_id: Player ID
        recent_matches_limit: Number of recent matches to include
        recent_matches_offset: Offset for recent matches pagination
        db: Database session

    Returns:
        PlayerDetailResponse with full player details

    Raises:
        HTTPException: If player not found
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Race statistics
    race_stats = {
        "Terran": player.terran_games,
        "Protoss": player.protoss_games,
        "Zerg": player.zerg_games,
        "Random": player.random_games,
    }

    # Recent matches with optimized join to avoid N+1 queries
    from sqlalchemy.orm import joinedload

    match_players = (
        db.query(MatchPlayer)
        .options(joinedload(MatchPlayer.match))
        .filter(MatchPlayer.player_id == player_id)
        .join(Match)
        .order_by(Match.played_at.desc())
        .offset(recent_matches_offset)
        .limit(recent_matches_limit)
        .all()
    )

    recent_matches = []
    for mp in match_players:
        if mp.match:
            recent_matches.append(
                {
                    "match_id": mp.match.id,
                    "played_at": mp.match.played_at.isoformat(),
                    "game_mode": mp.match.game_mode.value,
                    "map_name": mp.match.map_name,
                    "race": mp.race.value,
                    "won": bool(mp.won),
                    "team_number": mp.team_number,
                    "mmr_before": round(mp.mmr_before or 0, 1),
                    "mmr_after": round(mp.mmr_after or 0, 1),
                    "mmr_change": round((mp.mmr_after or 0) - (mp.mmr_before or 0), 1),
                }
            )

    return PlayerDetailResponse(
        id=player.id,
        name=player.name,
        mu=player.mu,
        sigma=player.sigma,
        mmr=player.mmr,
        unified_mmr=player.unified_mmr,
        recency_weighted_mmr=player.recency_weighted_mmr,
        hybrid_mmr=player.hybrid_mmr,
        avg_pim=player.avg_pim,
        total_games=player.total_games,
        wins=player.wins,
        losses=player.losses,
        win_rate=player.win_rate,
        is_core_player=bool(player.is_core_player),
        last_played=player.last_played,
        race_stats=race_stats,
        recent_matches=recent_matches,
    )


@router.get("/{player_id}/history", response_model=PlayerHistoryResponse)
def get_player_mmr_history(
    player_id: int, limit: int = 50, db: Session = Depends(get_db)
):
    """
    Get historical MMR data for a player to display on a chart.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    from sqlalchemy.orm import joinedload

    match_players = (
        db.query(MatchPlayer)
        .options(joinedload(MatchPlayer.match))
        .filter(MatchPlayer.player_id == player_id)
        .join(Match)
        .order_by(Match.played_at.desc())
        .limit(limit)
        .all()
    )

    # Reverse so the chart plots left-to-right chronologically
    match_players.reverse()

    history = []
    for mp in match_players:
        if mp.match:
            history.append(
                MMRHistoryEntry(
                    match_id=mp.match.id,
                    played_at=mp.match.played_at,
                    mmr=round(mp.mmr_after or 0, 1),
                    mmr_change=round((mp.mmr_after or 0) - (mp.mmr_before or 0), 1),
                    won=bool(mp.won),
                    map_name=mp.match.map_name,
                )
            )

    return PlayerHistoryResponse(
        player_id=player.id, player_name=player.name, history=history
    )


@router.post("/", response_model=PlayerResponse)
def create_player(request: CreatePlayerRequest, db: Session = Depends(get_db)):
    """
    Create a new player.

    Args:
        request: CreatePlayerRequest
        db: Database session

    Returns:
        PlayerResponse for created player

    Raises:
        HTTPException: If player name already exists
    """
    # Check if player already exists
    existing_player = db.query(Player).filter(Player.name == request.name).first()
    if existing_player:
        raise HTTPException(
            status_code=409, detail=f"Player with name '{request.name}' already exists"
        )

    # Create new player
    player = Player(
        name=request.name, is_core_player=1 if request.is_core_player else 0
    )

    db.add(player)
    db.commit()
    db.refresh(player)

    return _player_to_response(player)


@router.post("/calibrate", response_model=PlayerResponse)
def calibrate_player(request: CalibratePlayerRequest, db: Session = Depends(get_db)):
    """
    Create a new outsider player calibrated to a similar core player.

    Args:
        request: CalibratePlayerRequest
        db: Database session

    Returns:
        PlayerResponse for calibrated player

    Raises:
        HTTPException: If player name exists or similar player not found
    """
    # Check if player already exists
    existing_player = db.query(Player).filter(Player.name == request.name).first()
    if existing_player:
        raise HTTPException(
            status_code=409, detail=f"Player with name '{request.name}' already exists"
        )

    try:
        # Calibrate new player
        player = RatingSystem.calibrate_new_player(
            db, request.name, request.similar_to_player_id
        )

        return _player_to_response(player)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class RecalculationStats(BaseModel):
    players_updated: int
    matches_processed: int
    matches_skipped: int


@router.post(
    "/recalculate-ratings",
    response_model=RecalculationStats,
    dependencies=[Depends(require_admin)],
)
def recalculate_all_ratings(db: Session = Depends(get_db)):
    """Recalculate every player's TrueSkill mu/sigma/display-MMR from scratch,
    in chronological order, using the same policy as live ingestion.

    Updates existing match_players rows by primary key -- never deletes or
    recreates them, so child tables (metrics, performance features) can
    never be orphaned by this running. See app/services/rating_recalculation.py.
    """
    stats = recalculate_ratings_in_place(db)
    return RecalculationStats(**stats)


class MergePlayersRequest(BaseModel):
    """Request to merge two players."""

    source_player_name: str  # Player to merge from (will be deleted)
    target_player_name: str  # Player to merge into (will be kept)


class AddPlayerAliasRequest(BaseModel):
    """Request to map an alternate name to a canonical player."""

    source_name: str  # Name as it appears in replays (e.g. an old handle)
    target_player_name: str  # Canonical player this name should resolve to
    exclude_1v1: bool = True
    min_players: int = 4


class AddPlayerAliasResponse(BaseModel):
    """Response from creating/updating a player alias."""

    source_name: str
    target_player_name: str
    exclude_1v1: bool
    min_players: int


class MergePlayersResponse(BaseModel):
    """Response from merging players."""

    success: bool
    message: str
    kept_player: PlayerResponse
    matches_transferred: int
    synergies_updated: int


@router.post(
    "/merge",
    response_model=MergePlayersResponse,
    dependencies=[Depends(require_admin)],
)
def merge_players(request: MergePlayersRequest, db: Session = Depends(get_db)):
    """
    Merge two players into one.

    This combines all match history, statistics, and ratings from the source player
    into the target player, then deletes the source player.

    Use case: When the same person has been added under two different names.

    Args:
        request: MergePlayersRequest with source and target player names
        db: Database session

    Returns:
        MergePlayersResponse with merge results

    Raises:
        HTTPException: If either player not found or if trying to merge player with itself
    """
    # Find both players
    source_player = (
        db.query(Player).filter(Player.name == request.source_player_name).first()
    )
    target_player = (
        db.query(Player).filter(Player.name == request.target_player_name).first()
    )

    if not source_player:
        raise HTTPException(
            status_code=404,
            detail=f"Source player '{request.source_player_name}' not found",
        )

    if not target_player:
        raise HTTPException(
            status_code=404,
            detail=f"Target player '{request.target_player_name}' not found",
        )

    if source_player.id == target_player.id:
        raise HTTPException(status_code=400, detail="Cannot merge a player with itself")

    # Save original stats before merging
    source_total_games = source_player.total_games
    source_wins = source_player.wins
    source_losses = source_player.losses
    source_economic = source_player.avg_economic_score
    source_combat = source_player.avg_combat_score
    source_efficiency = source_player.avg_efficiency_score
    source_overall = source_player.avg_overall_impact

    target_total_games = target_player.total_games
    target_wins = target_player.wins
    target_losses = target_player.losses
    target_economic = target_player.avg_economic_score
    target_combat = target_player.avg_combat_score
    target_efficiency = target_player.avg_efficiency_score
    target_overall = target_player.avg_overall_impact

    # Transfer all match participations from source to target
    # Use bulk update to avoid ORM tracking issues
    from sqlalchemy import update

    # Count matches first
    matches_transferred = (
        db.query(MatchPlayer).filter(MatchPlayer.player_id == source_player.id).count()
    )

    # Bulk update match_players
    db.execute(
        update(MatchPlayer)
        .where(MatchPlayer.player_id == source_player.id)
        .values(player_id=target_player.id)
    )

    from ..models import PlayerSynergy, PlayerAchievement, PlayerRivalry, PlayerAlias

    db.execute(
        update(PlayerAchievement)
        .where(PlayerAchievement.player_id == source_player.id)
        .values(player_id=target_player.id)
    )

    db.execute(
        update(PlayerRivalry)
        .where(PlayerRivalry.player1_id == source_player.id)
        .values(player1_id=target_player.id)
    )

    db.execute(
        update(PlayerRivalry)
        .where(PlayerRivalry.player2_id == source_player.id)
        .values(player2_id=target_player.id)
    )

    synergies_p1_count = (
        db.query(PlayerSynergy)
        .filter(PlayerSynergy.player1_id == source_player.id)
        .count()
    )

    db.execute(
        update(PlayerSynergy)
        .where(PlayerSynergy.player1_id == source_player.id)
        .values(player1_id=target_player.id)
    )

    # Count and update synergies as player2
    synergies_p2_count = (
        db.query(PlayerSynergy)
        .filter(PlayerSynergy.player2_id == source_player.id)
        .count()
    )

    db.execute(
        update(PlayerSynergy)
        .where(PlayerSynergy.player2_id == source_player.id)
        .values(player2_id=target_player.id)
    )

    synergies_updated = synergies_p1_count + synergies_p2_count

    db.execute(
        update(PlayerAlias)
        .where(PlayerAlias.target_player_id == source_player.id)
        .values(target_player_id=target_player.id)
    )

    # Flush to ensure updates are committed before we delete
    db.flush()

    # Merge statistics by adding source to target
    target_player.total_games = target_total_games + source_total_games
    target_player.wins = target_wins + source_wins
    target_player.losses = target_losses + source_losses

    # For race statistics, we need to query and recalculate since we don't store them
    # Query ALL match_players for target (which now includes source's matches)
    all_matches = (
        db.query(MatchPlayer).filter(MatchPlayer.player_id == target_player.id).all()
    )

    # Reset and recalculate race statistics from ALL matches
    target_player.terran_games = 0
    target_player.protoss_games = 0
    target_player.zerg_games = 0
    target_player.random_games = 0

    for mp in all_matches:
        if mp.race.value == "Terran":
            target_player.terran_games += 1
        elif mp.race.value == "Protoss":
            target_player.protoss_games += 1
        elif mp.race.value == "Zerg":
            target_player.zerg_games += 1
        elif mp.race.value == "Random":
            target_player.random_games += 1

    # Update last_played to most recent of the two
    if source_player.last_played:
        if (
            not target_player.last_played
            or source_player.last_played > target_player.last_played
        ):
            target_player.last_played = source_player.last_played

    # Merge impact scores (weighted average based on game counts)
    if target_total_games > 0 and source_total_games > 0:
        total_combined_games = target_total_games + source_total_games
        target_weight = target_total_games / total_combined_games
        source_weight = source_total_games / total_combined_games

        target_player.avg_economic_score = (
            target_economic * target_weight + source_economic * source_weight
        )
        target_player.avg_combat_score = (
            target_combat * target_weight + source_combat * source_weight
        )
        target_player.avg_efficiency_score = (
            target_efficiency * target_weight + source_efficiency * source_weight
        )
        target_player.avg_overall_impact = (
            target_overall * target_weight + source_overall * source_weight
        )
    elif source_total_games > 0:
        # Target had no games, just use source's scores
        target_player.avg_economic_score = source_economic
        target_player.avg_combat_score = source_combat
        target_player.avg_efficiency_score = source_efficiency
        target_player.avg_overall_impact = source_overall

    # Note: TrueSkill ratings (mu, sigma) are NOT merged
    # The target player keeps their existing rating
    # This is intentional - merging would require recalculating all matches chronologically

    # Delete the source player
    db.delete(source_player)

    # Commit all changes
    db.commit()
    db.refresh(target_player)

    return MergePlayersResponse(
        success=True,
        message=f"Successfully merged '{request.source_player_name}' into '{request.target_player_name}'. {matches_transferred} matches transferred.",
        kept_player=_player_to_response(target_player),
        matches_transferred=matches_transferred,
        synergies_updated=synergies_updated,
    )


@router.post(
    "/aliases",
    response_model=AddPlayerAliasResponse,
    dependencies=[Depends(require_admin)],
)
def add_player_alias(request: AddPlayerAliasRequest, db: Session = Depends(get_db)):
    """
    Map an alternate name to a canonical player so future replay uploads
    under that name are attributed to the canonical player instead of
    creating a new duplicate.
    """
    from ..services.player_service import PlayerService

    try:
        alias = PlayerService.add_alias(
            db,
            request.source_name,
            request.target_player_name,
            exclude_1v1=request.exclude_1v1,
            min_players=request.min_players,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return AddPlayerAliasResponse(
        source_name=alias.source_name,
        target_player_name=request.target_player_name,
        exclude_1v1=bool(alias.exclude_1v1),
        min_players=alias.min_players,
    )


class CoachingResponse(BaseModel):
    player_id: int
    player_name: str
    tips: List[str]


@router.get("/{player_id}/coaching", response_model=CoachingResponse)
def get_player_coaching(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    from ..services.coaching_service import CoachingService

    tips = CoachingService.get_tips(player_id, db)

    return CoachingResponse(player_id=player.id, player_name=player.name, tips=tips)
