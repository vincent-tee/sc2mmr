"""
API endpoints for team balancing.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..balancer import TeamBalancer, BalancerStats
from ..models import Player
from ..services.ai_mmr_service import get_all_ai_difficulties
from ..services.balance_capture import BalancePredictionService


router = APIRouter(prefix="/teams", tags=["teams"])


# Request/Response models
class BalanceTeamsRequest(BaseModel):
    """Request to balance teams."""

    player_ids: List[int]
    top_n: int = 10
    map_name: Optional[str] = None
    ai_difficulty: Optional[str] = (
        None  # "easy", "medium", "hard", "very_hard", "elite"
    )


class PlayerInfo(BaseModel):
    """Player information in team suggestion."""

    id: int
    name: str
    mmr: float
    mu: float
    sigma: float


class TeamInfo(BaseModel):
    """Team information."""

    players: List[PlayerInfo]
    total_mmr: float
    avg_mmr: float
    has_ai: bool = False
    ai_mmr: Optional[float] = None


class TeamSuggestionResponse(BaseModel):
    balance_prediction_id: Optional[int] = None
    map_name: Optional[str] = None
    """Team suggestion response."""

    team_1: TeamInfo
    team_2: TeamInfo
    mmr_difference: float
    match_quality: float
    win_probability_team_1: float
    win_probability_team_2: float
    fairness_rating: str
    team_1_avg_impact: float = 0.0
    team_2_avg_impact: float = 0.0
    impact_balance_score: float = 1.0
    impact_difference: float = 0.0


def _suggestion_response(suggestion, map_name: Optional[str] = None) -> TeamSuggestionResponse:
    """Turn a balancer suggestion into the API response."""
    analysis = BalancerStats.analyze_suggestion(suggestion)
    balance = analysis["balance"]

    def team_info(players, team_key: str) -> TeamInfo:
        return TeamInfo(
            players=[
                PlayerInfo(id=p.id, name=p.name, mmr=p.mmr, mu=p.mu, sigma=p.sigma)
                for p in players
            ],
            total_mmr=analysis[team_key]["total_mmr"],
            avg_mmr=analysis[team_key]["avg_mmr"],
        )

    return TeamSuggestionResponse(
        balance_prediction_id=suggestion.balance_prediction_id,
        map_name=map_name,
        team_1=team_info(suggestion.team_1, "team_1"),
        team_2=team_info(suggestion.team_2, "team_2"),
        mmr_difference=balance["mmr_difference"],
        match_quality=balance["match_quality"],
        win_probability_team_1=balance["win_probability_team_1"],
        win_probability_team_2=balance["win_probability_team_2"],
        fairness_rating=balance["fairness_rating"],
        team_1_avg_impact=balance["team_1_avg_impact"],
        team_2_avg_impact=balance["team_2_avg_impact"],
        impact_balance_score=balance["impact_balance_score"],
        impact_difference=balance["impact_difference"],
    )


class CustomPlayerInfo(BaseModel):
    """Information for a custom (non-DB) player."""

    name: str
    mmr: float = 1000.0
    mu: float = 25.0
    sigma: float = 8.333
    overall_impact: float = 50.0
    total_games: int = 0


class BalanceWithCustomPlayersRequest(BaseModel):
    """Request to balance teams with both DB and custom players."""

    player_ids: List[int]
    custom_players: List[CustomPlayerInfo]
    top_n: int = 3


@router.post(
    "/balance-with-custom-players", response_model=List[TeamSuggestionResponse]
)
def balance_with_custom_players(
    request: BalanceWithCustomPlayersRequest, db: Session = Depends(get_db)
):
    """
    Balance teams using a mix of database players and custom (guest) players.
    """
    from ..balancer import PlayerInfo as BalancerPlayerInfo

    # Get DB players
    db_players = db.query(Player).filter(Player.id.in_(request.player_ids)).all()
    player_infos = [BalancerPlayerInfo.from_player(p) for p in db_players]

    # Add custom players
    for idx, cp in enumerate(request.custom_players):
        player_infos.append(
            BalancerPlayerInfo(
                id=-(idx + 1),  # Negative IDs for custom players
                name=cp.name,
                mu=cp.mu,
                sigma=cp.sigma,
                mmr=cp.mmr,
                overall_impact=cp.overall_impact,
                total_games=cp.total_games,
            )
        )

    if len(player_infos) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players total")

    suggestions = TeamBalancer.generate_team_suggestions(player_infos, top_n=request.top_n)

    return [_suggestion_response(suggestion) for suggestion in suggestions]


class DraftPickResponse(BaseModel):
    """A single pick in a captain's draft."""

    pick_number: int
    team_index: int
    role: str  # "captain" | "pick"
    player: PlayerInfo


class DraftTeamResponse(BaseModel):
    """A team's roster from a captain's draft."""

    players: List[PlayerInfo]
    total_mmr: float
    avg_mmr: float


class DraftResponse(BaseModel):
    """Response for a captain's-draft team construction."""

    teams: List[DraftTeamResponse]
    draft_log: List[DraftPickResponse]


class DraftRequest(BaseModel):
    """Request for captain's-draft team construction."""

    player_ids: List[int]
    custom_players: List[CustomPlayerInfo] = []
    num_teams: int = 2


@router.post("/draft", response_model=DraftResponse)
def draft_teams(request: DraftRequest, db: Session = Depends(get_db)):
    """
    POC: captain's-draft team construction (snake draft) - a transparent,
    explainable alternative to /balance's exhaustive-search optimal split.
    Not validated as producing better-balanced teams; see
    TeamBalancer.snake_draft's docstring.
    """
    from ..balancer import PlayerInfo as BalancerPlayerInfo, TeamBalancer

    db_players = db.query(Player).filter(Player.id.in_(request.player_ids)).all()
    player_infos = [BalancerPlayerInfo.from_player(p) for p in db_players]

    for idx, cp in enumerate(request.custom_players):
        player_infos.append(
            BalancerPlayerInfo(
                id=-(idx + 1),
                name=cp.name,
                mu=cp.mu,
                sigma=cp.sigma,
                mmr=cp.mmr,
                overall_impact=cp.overall_impact,
                total_games=cp.total_games,
            )
        )

    if len(player_infos) < max(2, request.num_teams):
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {max(2, request.num_teams)} players total",
        )

    try:
        result = TeamBalancer.snake_draft(player_infos, num_teams=request.num_teams)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    def to_player_info(p: "BalancerPlayerInfo") -> PlayerInfo:
        return PlayerInfo(
            id=p.id, name=p.name, mmr=p.mmr,
            mu=p.mu, sigma=p.sigma,
        )

    teams_response = [
        DraftTeamResponse(
            players=[to_player_info(p) for p in team],
            total_mmr=sum(p.mmr for p in team),
            avg_mmr=sum(p.mmr for p in team) / len(team) if team else 0.0,
        )
        for team in result["teams"]
    ]
    draft_log_response = [
        DraftPickResponse(
            pick_number=entry["pick_number"],
            team_index=entry["team_index"],
            role=entry["role"],
            player=to_player_info(entry["player"]),
        )
        for entry in result["draft_log"]
    ]

    return DraftResponse(teams=teams_response, draft_log=draft_log_response)


class SwapSuggestionResponse(BaseModel):
    """A single suggested player swap between two fixed teams."""

    player_out_of_team_1: PlayerInfo
    player_out_of_team_2: PlayerInfo
    new_match_quality: float
    new_win_probability: float
    quality_delta: float


class SuggestSwapsResponse(BaseModel):
    """Response for swap-suggestion analysis of a fixed split."""

    current_match_quality: float
    current_win_probability: float
    suggestions: List[SwapSuggestionResponse]


class SuggestSwapsRequest(BaseModel):
    """Request to analyze a fixed team split for improving swaps."""

    team_1_ids: List[int]
    team_2_ids: List[int]
    custom_players: List[CustomPlayerInfo] = []
    top_n: int = 3


@router.post("/suggest-swaps", response_model=SuggestSwapsResponse)
def suggest_swaps(request: SuggestSwapsRequest, db: Session = Depends(get_db)):
    """
    Given a fixed 2-team split (e.g. from a manual draft or hand-adjusted
    teams), suggest single-player swaps that would improve balance. See
    TeamBalancer.suggest_swaps' docstring - this is a local search around
    the given split using the proven TrueSkill scoring, not a claim of
    global optimality.
    """
    from ..balancer import PlayerInfo as BalancerPlayerInfo, TeamBalancer

    def resolve_players(ids: List[int]) -> List["BalancerPlayerInfo"]:
        db_players = db.query(Player).filter(Player.id.in_(ids)).all()
        by_id = {p.id: BalancerPlayerInfo.from_player(p) for p in db_players}
        for idx, cp in enumerate(request.custom_players):
            by_id[-(idx + 1)] = BalancerPlayerInfo(
                id=-(idx + 1), name=cp.name, mu=cp.mu, sigma=cp.sigma,
                mmr=cp.mmr, overall_impact=cp.overall_impact, total_games=cp.total_games,
            )
        return [by_id[i] for i in ids if i in by_id]

    team_1 = resolve_players(request.team_1_ids)
    team_2 = resolve_players(request.team_2_ids)

    if not team_1 or not team_2:
        raise HTTPException(status_code=400, detail="Both teams need at least one player")

    result = TeamBalancer.suggest_swaps(team_1, team_2, top_n=request.top_n)

    def to_player_info(p: "BalancerPlayerInfo") -> PlayerInfo:
        return PlayerInfo(
            id=p.id, name=p.name, mmr=p.mmr,
            mu=p.mu, sigma=p.sigma,
        )

    return SuggestSwapsResponse(
        current_match_quality=result["current_match_quality"],
        current_win_probability=result["current_win_probability"],
        suggestions=[
            SwapSuggestionResponse(
                player_out_of_team_1=to_player_info(c["player_out_of_team_1"]),
                player_out_of_team_2=to_player_info(c["player_out_of_team_2"]),
                new_match_quality=c["new_match_quality"],
                new_win_probability=c["new_win_probability"],
                quality_delta=c["quality_delta"],
            )
            for c in result["suggestions"]
        ],
    )


@router.post("/balance", response_model=List[TeamSuggestionResponse])
def balance_teams(request: BalanceTeamsRequest, db: Session = Depends(get_db)):
    """
    Generate balanced team suggestions for given players.

    This is the PRIMARY FEATURE of the application.

    Args:
        request: BalanceTeamsRequest with player IDs
        db: Database session

    Returns:
        List of TeamSuggestionResponse objects, sorted by balance quality

    Raises:
        HTTPException: If invalid number of players or players not found
    """
    # Validate minimum players
    num_players = len(request.player_ids)
    if num_players < 2:
        raise HTTPException(
            status_code=400, detail=f"Need at least 2 players, got {num_players}"
        )

    # Maximum reasonable limit
    if num_players > 20:
        raise HTTPException(
            status_code=400,
            detail=f"Too many players: {num_players}. Maximum is 20 players (10v10)",
        )

    try:
        # Generate team suggestions
        suggestions = TeamBalancer.balance_teams(
            db, request.player_ids, top_n=request.top_n
        )

        # Capture predictions for calibration tracking (resolved on upload)
        BalancePredictionService.record_suggestions(
            db, "mmr_v2", suggestions, max_rank=len(suggestions), map_name=request.map_name
        )

        return [_suggestion_response(suggestion, request.map_name) for suggestion in suggestions]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/balance-calibration")
def get_balance_calibration(
    method: Optional[str] = None,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Calibration metrics for balancer predictions vs actual outcomes.

    Returns Brier score, log loss, directional accuracy, and reliability
    bins per balancing method (from captured balance-time predictions),
    plus the upload-time TrueSkill baseline stored on matches.
    Lower Brier/log-loss = better-calibrated balancing.
    """
    try:
        methods = BalancePredictionService.get_calibration(db, method=method, days=days)
        baseline = BalancePredictionService.get_upload_baseline_calibration(
            db, days=days
        )
        return {
            "methods": methods,
            "upload_trueskill_baseline": baseline,
            "notes": (
                "methods = captured balance-time predictions (rank-1 picks only), "
                "resolved against uploaded replays. Brier: 0.25 = coin flip, "
                "lower is better."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# AI-Aware Balancing Endpoint
# =============================================================================


@router.get("/ai-difficulties")
def list_ai_difficulties():
    """List available AI difficulty levels and their MMR values."""
    return {
        "difficulties": get_all_ai_difficulties(),
        "config_path": "backend/config/ai_mmr.json",
        "note": "Edit the config file to recalibrate AI MMR values",
    }


# =============================================================================
# Match Prediction Endpoint (Phase 1 Feature)
# =============================================================================


class PredictMatchRequest(BaseModel):
    """Request to predict match outcome."""

    team_1_ids: List[int]
    team_2_ids: List[int]


class TeamPredictionInfo(BaseModel):
    """Detailed team prediction info."""

    players: List[PlayerInfo]
    total_mmr: float
    avg_mmr: float
    win_probability: float


class MatchPredictionResponse(BaseModel):
    """Enhanced match prediction response."""

    team_1: TeamPredictionInfo
    team_2: TeamPredictionInfo
    predicted_winner: int  # 1 or 2
    confidence: str  # "High", "Medium", "Low"
    match_quality: float
    factors: List[str]  # Explanation of prediction factors


@router.post("/predict", response_model=MatchPredictionResponse)
def predict_match(request: PredictMatchRequest, db: Session = Depends(get_db)):
    """
    Predict match outcome with detailed analysis.

    Factors in:
    - Team MMR difference
    - Match quality (how competitive the match should be)

    Args:
        request: Teams to predict
        db: Database session

    Returns:
        Detailed match prediction with confidence and factors
    """
    from ..balancer import TeamBalancer
    from ..balancer import PlayerInfo as BalancerPlayerInfo

    # Get players
    team_1_players = db.query(Player).filter(Player.id.in_(request.team_1_ids)).all()
    team_2_players = db.query(Player).filter(Player.id.in_(request.team_2_ids)).all()

    if len(team_1_players) != len(request.team_1_ids):
        raise HTTPException(status_code=404, detail="Some team 1 players not found")
    if len(team_2_players) != len(request.team_2_ids):
        raise HTTPException(status_code=404, detail="Some team 2 players not found")

    # Convert to balancer format
    t1_info = [BalancerPlayerInfo.from_player(p) for p in team_1_players]
    t2_info = [BalancerPlayerInfo.from_player(p) for p in team_2_players]

    # Calculate base predictions
    win_prob_t1 = TeamBalancer.calculate_win_probability(t1_info, t2_info)
    match_quality = TeamBalancer.calculate_match_quality(t1_info, t2_info)

    # Calculate MMR totals
    t1_total_mmr = sum(p.mmr for p in team_1_players)
    t2_total_mmr = sum(p.mmr for p in team_2_players)
    t1_avg_mmr = t1_total_mmr / len(team_1_players)
    t2_avg_mmr = t2_total_mmr / len(team_2_players)

    # Determine prediction factors
    factors = []

    mmr_diff = abs(t1_total_mmr - t2_total_mmr)
    if mmr_diff > 800:
        factors.append(f"Large MMR gap ({mmr_diff:.0f} total difference)")
    elif mmr_diff < 200:
        factors.append("Very close MMR - could go either way")

    if match_quality > 0.4:
        factors.append("High match quality - competitive game expected")
    elif match_quality < 0.2:
        factors.append("Low match quality - one-sided match likely")

    # Determine confidence
    if abs(win_prob_t1 - 0.5) > 0.25:
        confidence = "High"
    elif abs(win_prob_t1 - 0.5) > 0.1:
        confidence = "Medium"
    else:
        confidence = "Low"

    predicted_winner = 1 if win_prob_t1 >= 0.5 else 2

    # Build response
    return MatchPredictionResponse(
        team_1=TeamPredictionInfo(
            players=[
                PlayerInfo(id=p.id, name=p.name, mmr=p.mmr, mu=p.mu, sigma=p.sigma)
                for p in team_1_players
            ],
            total_mmr=round(t1_total_mmr, 1),
            avg_mmr=round(t1_avg_mmr, 1),
            win_probability=round(win_prob_t1 * 100, 1),
        ),
        team_2=TeamPredictionInfo(
            players=[
                PlayerInfo(id=p.id, name=p.name, mmr=p.mmr, mu=p.mu, sigma=p.sigma)
                for p in team_2_players
            ],
            total_mmr=round(t2_total_mmr, 1),
            avg_mmr=round(t2_avg_mmr, 1),
            win_probability=round((1 - win_prob_t1) * 100, 1),
        ),
        predicted_winner=predicted_winner,
        confidence=confidence,
        match_quality=round(match_quality, 3),
        factors=factors if factors else ["Evenly matched teams"],
    )
