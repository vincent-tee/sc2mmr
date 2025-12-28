"""
API endpoints for player statistics and management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import Player, MatchPlayer, Match, PlayerMatchMetrics
from ..rating_system import RatingSystem
from ..performance_rating import PerformanceRatingAdjuster
from ..impact_service import ImpactService
from ..replay_parser import ReplayData, PlayerData
from pydantic import BaseModel
import time


router = APIRouter(prefix="/players", tags=["players"])


def _player_to_response(p: "Player") -> "PlayerResponse":
    """Convert a Player model to PlayerResponse."""
    return PlayerResponse(
        id=p.id,
        name=p.name,
        mu=p.mu,
        sigma=p.sigma,
        mmr=p.mmr,
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
    )


# Request/Response models
class PlayerResponse(BaseModel):
    """Response model for player data."""

    id: int
    name: str
    mu: float
    sigma: float
    mmr: float
    recency_weighted_mmr: Optional[float]
    # Hybrid MMR System (SPEC-ML-001)
    hybrid_mmr: Optional[float] = None  # Performance-adjusted MMR
    avg_pim: Optional[float] = None  # Average Performance Impact Modifier
    total_games: int
    wins: int
    losses: int
    win_rate: float
    favorite_race: str
    is_core_player: bool
    is_ai: bool = False
    last_played: Optional[datetime]

    class Config:
        from_attributes = True


class PlayerDetailResponse(BaseModel):
    """Detailed player response with race statistics."""

    id: int
    name: str
    mu: float
    sigma: float
    mmr: float
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


class CreatePlayerRequest(BaseModel):
    """Request to create a new player."""

    name: str
    is_core_player: bool = True


class CalibratePlayerRequest(BaseModel):
    """Request to calibrate a new outsider player."""

    name: str
    similar_to_player_id: int


@router.get("/", response_model=List[PlayerResponse])
def get_players(core_only: bool = False, db: Session = Depends(get_db)):
    """
    Get all players.

    Args:
        core_only: If True, only return core players
        db: Database session

    Returns:
        List of PlayerResponse objects
    """
    query = db.query(Player)

    if core_only:
        query = query.filter(Player.is_core_player == 1)

    players = query.order_by(Player.name).all()

    return [_player_to_response(p) for p in players]


@router.get("/rankings", response_model=List[PlayerRankingResponse])
def get_player_rankings(
    min_games: int = 5, core_only: bool = False, db: Session = Depends(get_db)
):
    """
    Get player rankings by MMR.

    Args:
        min_games: Minimum games played to be ranked
        core_only: If True, only rank core players
        db: Database session

    Returns:
        List of PlayerRankingResponse objects sorted by MMR
    """
    query = db.query(Player).filter(Player.total_games >= min_games)

    if core_only:
        query = query.filter(Player.is_core_player == 1)

    # Sort by MMR (mu - 3*sigma)
    players = query.all()
    players_sorted = sorted(players, key=lambda p: p.mmr, reverse=True)

    return [
        PlayerRankingResponse(
            rank=idx + 1,
            player=_player_to_response(p),
        )
        for idx, p in enumerate(players_sorted)
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

    # Recent matches
    match_players = (
        db.query(MatchPlayer)
        .filter(MatchPlayer.player_id == player_id)
        .order_by(MatchPlayer.id.desc())
        .offset(recent_matches_offset)
        .limit(recent_matches_limit)
        .all()
    )

    recent_matches = []
    for mp in match_players:
        match = db.query(Match).filter(Match.id == mp.match_id).first()
        if match:
            # Use centralized display MMR formula for consistency with Player.mmr
            from ..rating_system import RatingSystem

            mmr_before = RatingSystem.calculate_display_mmr(mp.mu_before)
            mmr_after = RatingSystem.calculate_display_mmr(mp.mu_after)

            recent_matches.append(
                {
                    "match_id": match.id,
                    "played_at": match.played_at.isoformat(),
                    "game_mode": match.game_mode.value,
                    "map_name": match.map_name,
                    "race": mp.race.value,
                    "won": bool(mp.won),
                    "team_number": mp.team_number,
                    "mmr_before": round(mmr_before, 1),
                    "mmr_after": round(mmr_after, 1),
                    "mmr_change": round(mmr_after - mmr_before, 1),
                }
            )

    return PlayerDetailResponse(
        id=player.id,
        name=player.name,
        mu=player.mu,
        sigma=player.sigma,
        mmr=player.mmr,
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
    """Statistics from rating recalculation."""

    total_players: int
    total_matches: int
    processing_time_ms: float
    players_updated: int
    matches_processed: int
    matches_with_performance_adjustments: int
    matches_without_metrics: int
    avg_performance_multiplier: float
    min_performance_multiplier: float
    max_performance_multiplier: float
    total_adjustments_applied: int


@router.post("/recalculate-ratings", response_model=RecalculationStats)
def recalculate_all_ratings(db: Session = Depends(get_db)):
    """
    Recalculate all player ratings from scratch using TrueSkill + Performance Adjustments.

    This endpoint:
    1. Resets all player ratings to default values (mu=25, sigma=8.333)
    2. Resets all player statistics (wins, losses, games)
    3. Gets all matches ordered chronologically
    4. Re-processes each match with TrueSkill algorithm
    5. Applies performance-based rating adjustments (living model)
    6. Applies recency bias - recent matches have stronger performance impact
    7. Updates MatchPlayer records with new ratings

    Recency Bias:
    - Oldest matches: 30% of performance adjustment strength
    - Newest matches: 100% of performance adjustment strength
    - This ensures recent performance has more impact on final ratings

    This is useful for:
    - After merging players
    - Testing algorithm changes
    - Fixing rating inconsistencies

    Args:
        db: Database session

    Returns:
        RecalculationStats with processing information and validation metrics
    """
    import trueskill
    from ..performance_rating import PerformanceRatingAdjuster

    start_time = time.time()

    # Get all players and matches
    all_players = db.query(Player).all()
    all_matches = db.query(Match).order_by(Match.played_at.asc()).all()

    # Reset all players to default ratings
    player_ratings = {}  # player_id -> trueskill.Rating
    for player in all_players:
        player.mu = 25.0
        player.sigma = 8.333
        player.wins = 0
        player.losses = 0
        player.total_games = 0
        player.last_played = None
        player.terran_games = 0
        player.protoss_games = 0
        player.zerg_games = 0
        player.random_games = 0
        player_ratings[player.id] = trueskill.Rating(mu=25.0, sigma=8.333)

    db.commit()

    matches_processed = 0
    players_updated = set()

    # Track performance adjustment statistics
    matches_with_performance_adjustments = 0
    matches_without_metrics = 0
    all_multipliers = []
    total_adjustments_applied = 0

    # Calculate recency weights (recent matches have more impact)
    total_matches_count = len(all_matches)

    # Re-process each match chronologically
    for match_index, match in enumerate(all_matches):
        # Get all match_players for this match
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )

        if not match_players:
            continue

        # Group by team
        team_1_mps = [mp for mp in match_players if mp.team_number == 1]
        team_2_mps = [mp for mp in match_players if mp.team_number == 2]

        if not team_1_mps or not team_2_mps:
            continue

        # Get current ratings for each team
        team_1_ratings = [player_ratings[mp.player_id] for mp in team_1_mps]
        team_2_ratings = [player_ratings[mp.player_id] for mp in team_2_mps]

        # Determine winner (check team 1's first player)
        team_1_won = team_1_mps[0].won == 1

        # Calculate new TrueSkill ratings
        if team_1_won:
            new_team_1_ratings, new_team_2_ratings = trueskill.rate(
                [team_1_ratings, team_2_ratings],
                ranks=[0, 1],  # Team 1 won (rank 0 beats rank 1)
            )
        else:
            new_team_1_ratings, new_team_2_ratings = trueskill.rate(
                [team_1_ratings, team_2_ratings],
                ranks=[1, 0],  # Team 2 won
            )

        # Update match_player records with TrueSkill ratings
        for i, mp in enumerate(team_1_mps):
            old_rating = player_ratings[mp.player_id]
            new_rating = new_team_1_ratings[i]

            # Update MatchPlayer with before/after ratings
            mp.mu_before = old_rating.mu
            mp.sigma_before = old_rating.sigma
            mp.mu_after = new_rating.mu
            mp.sigma_after = new_rating.sigma

            players_updated.add(mp.player_id)

        for i, mp in enumerate(team_2_mps):
            old_rating = player_ratings[mp.player_id]
            new_rating = new_team_2_ratings[i]

            mp.mu_before = old_rating.mu
            mp.sigma_before = old_rating.sigma
            mp.mu_after = new_rating.mu
            mp.sigma_after = new_rating.sigma

            players_updated.add(mp.player_id)

        # Apply performance-based adjustments (living model)
        # Fetch all metrics for this match in one query
        match_player_ids = [mp.id for mp in match_players]
        metrics_list = (
            db.query(PlayerMatchMetrics)
            .filter(PlayerMatchMetrics.match_player_id.in_(match_player_ids))
            .all()
        )

        # Create mapping: match_player_id -> metrics
        player_metrics_map = {m.match_player_id: m for m in metrics_list}

        # Get metrics for each team
        team_1_metrics = [
            player_metrics_map[mp.id]
            for mp in team_1_mps
            if mp.id in player_metrics_map
        ]
        team_2_metrics = [
            player_metrics_map[mp.id]
            for mp in team_2_mps
            if mp.id in player_metrics_map
        ]

        # Track if this match has metrics
        match_has_metrics = len(player_metrics_map) > 0
        if match_has_metrics:
            matches_with_performance_adjustments += 1
        else:
            matches_without_metrics += 1

        # Apply performance adjustments to each player
        for mp in match_players:
            if mp.id not in player_metrics_map:
                # No metrics for this player, use TrueSkill rating as-is
                player_ratings[mp.player_id] = trueskill.Rating(
                    mu=mp.mu_after, sigma=mp.sigma_after
                )
                continue

            metrics = player_metrics_map[mp.id]

            # Determine team and opponent metrics
            if mp.team_number == 1:
                team_metrics = team_1_metrics
                opponent_metrics = team_2_metrics
            else:
                team_metrics = team_2_metrics
                opponent_metrics = team_1_metrics

            # Calculate performance multiplier
            base_multiplier = (
                PerformanceRatingAdjuster.calculate_performance_multiplier(
                    metrics, team_metrics, opponent_metrics, bool(mp.won)
                )
            )

            # Apply recency bias: recent matches have stronger performance adjustments
            # Recency weight ranges from 0.3 (oldest match) to 1.0 (newest match)
            recency_weight = 0.3 + 0.7 * (match_index / max(1, total_matches_count - 1))

            # Blend multiplier toward 1.0 based on recency weight
            # Old matches: multiplier closer to 1.0 (less performance impact)
            # Recent matches: full multiplier effect
            multiplier = 1.0 + (base_multiplier - 1.0) * recency_weight

            # Track multiplier statistics (using final multiplier after recency)
            all_multipliers.append(multiplier)
            total_adjustments_applied += 1

            # Apply multiplier to the rating change (not the final value)
            base_mu_change = mp.mu_after - mp.mu_before
            adjusted_mu_change = base_mu_change * multiplier
            adjusted_mu_after = mp.mu_before + adjusted_mu_change

            # Validation: Ensure multiplier is within expected bounds
            if multiplier < 0.5 or multiplier > 1.5:
                print(
                    f"WARNING: Multiplier {multiplier} outside expected bounds for player {mp.player_id} in match {match.id}"
                )

            # Validation: Ensure rating change is reasonable
            if abs(base_mu_change) > 10:  # TrueSkill changes should rarely exceed 10
                print(
                    f"INFO: Large TrueSkill change {base_mu_change:.2f} for player {mp.player_id} in match {match.id}"
                )

            # Update the match_player record with adjusted rating
            mp.mu_after = adjusted_mu_after

            # Update in-memory rating with adjusted value
            player_ratings[mp.player_id] = trueskill.Rating(
                mu=adjusted_mu_after, sigma=mp.sigma_after
            )

        # Update player statistics
        for mp in match_players:
            player = db.query(Player).filter(Player.id == mp.player_id).first()
            if player:
                player.total_games += 1
                if mp.won:
                    player.wins += 1
                else:
                    player.losses += 1
                player.last_played = match.played_at

                # Update race stats
                if mp.race.value == "Terran":
                    player.terran_games += 1
                elif mp.race.value == "Protoss":
                    player.protoss_games += 1
                elif mp.race.value == "Zerg":
                    player.zerg_games += 1
                elif mp.race.value == "Random":
                    player.random_games += 1

        matches_processed += 1

        # Commit every 50 matches to avoid huge transactions
        if matches_processed % 50 == 0:
            db.commit()

    # Final commit
    db.commit()

    # Update all player ratings to their final values
    for player in all_players:
        if player.id in player_ratings:
            final_rating = player_ratings[player.id]
            player.mu = final_rating.mu
            player.sigma = final_rating.sigma

    db.commit()

    processing_time_ms = (time.time() - start_time) * 1000

    # Calculate statistics about performance adjustments
    avg_multiplier = (
        sum(all_multipliers) / len(all_multipliers) if all_multipliers else 1.0
    )
    min_multiplier = min(all_multipliers) if all_multipliers else 1.0
    max_multiplier = max(all_multipliers) if all_multipliers else 1.0

    return RecalculationStats(
        total_players=len(all_players),
        total_matches=len(all_matches),
        processing_time_ms=round(processing_time_ms, 2),
        players_updated=len(players_updated),
        matches_processed=matches_processed,
        matches_with_performance_adjustments=matches_with_performance_adjustments,
        matches_without_metrics=matches_without_metrics,
        avg_performance_multiplier=round(avg_multiplier, 3),
        min_performance_multiplier=round(min_multiplier, 3),
        max_performance_multiplier=round(max_multiplier, 3),
        total_adjustments_applied=total_adjustments_applied,
    )


class MergePlayersRequest(BaseModel):
    """Request to merge two players."""

    source_player_name: str  # Player to merge from (will be deleted)
    target_player_name: str  # Player to merge into (will be kept)


class MergePlayersResponse(BaseModel):
    """Response from merging players."""

    success: bool
    message: str
    kept_player: PlayerResponse
    matches_transferred: int
    synergies_updated: int


@router.post("/merge", response_model=MergePlayersResponse)
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

    # Update synergies - need to handle both player1 and player2
    from ..models import PlayerSynergy

    # Count and update synergies as player1
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
