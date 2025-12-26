"""
Blended Rating Service - Provides Consensus MMR Change by weighting TrueSkill and XGBoost outputs.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .xgboost_predictor import get_xgboost_predictor
from ..rating_system import RatingSystem
from ..models import Player, Match, MatchPlayer

logger = logging.getLogger(__name__)


class BlendedRatingService:
    """
    Consensus MMR Change Calculator.

    Weights:
    - TrueSkill (Foundation): 70%
    - XGBoost (Performance/Context): 30%
    """

    @staticmethod
    def get_consensus_mmr_change(
        db: Session,
        player_id: int,
        match_id: int,
        trueskill_change: float,
        weight_trueskill: float = 0.7,
        weight_xgboost: float = 0.3,
    ) -> float:
        """
        Calculate a weighted consensus MMR change by blending TrueSkill and XGBoost.

        This provides a more comprehensive view of skill change by accounting for both
        the Bayesian outcome prediction (TrueSkill) and the performance-contextual
        prediction (XGBoost).

        Args:
            db: Database session
            player_id: ID of the player
            match_id: ID of the match
            trueskill_change: The MMR change calculated by TrueSkill
            weight_trueskill: Relative weight for TrueSkill contribution
            weight_xgboost: Relative weight for XGBoost contribution

        Returns:
            Blended MMR change
        """
        # 1. Get TrueSkill contribution
        ts_contribution = trueskill_change * weight_trueskill

        # 2. Get XGBoost contribution
        xgboost_contribution = 0.0

        try:
            predictor = get_xgboost_predictor()
            match = db.query(Match).filter(Match.id == match_id).first()
            if match:
                # Find the player in the match
                mp = (
                    db.query(MatchPlayer)
                    .filter(
                        MatchPlayer.match_id == match_id,
                        MatchPlayer.player_id == player_id,
                    )
                    .first()
                )

                if mp:
                    # Get win probability from XGBoost
                    team1_players = (
                        db.query(MatchPlayer)
                        .filter(
                            MatchPlayer.match_id == match_id,
                            MatchPlayer.team_number == 1,
                        )
                        .all()
                    )
                    team2_players = (
                        db.query(MatchPlayer)
                        .filter(
                            MatchPlayer.match_id == match_id,
                            MatchPlayer.team_number == 2,
                        )
                        .all()
                    )

                    team1_ids = [p.player_id for p in team1_players]
                    team2_ids = [p.player_id for p in team2_players]

                    # Ensure predictor is trained/loaded
                    prediction = predictor.predict(db, team1_ids, team2_ids)

                    if "error" not in prediction:
                        # Probability of THIS player's team winning
                        prob = (
                            prediction["team_1_win_probability"] / 100.0
                            if mp.team_number == 1
                            else prediction["team_2_win_probability"] / 100.0
                        )
                        actually_won = bool(mp.won)

                        # Calculate adjustment factor based on "surprise"
                        # If underdog wins, they get more. If favorite wins, they get less.
                        if actually_won:
                            if prob > 0.7:
                                # Heavy favorite won - reduce gain (expected)
                                adjustment = 1.0 - (prob - 0.5) * 0.5
                            elif prob < 0.3:
                                # Underdog won - increase gain (impressive)
                                adjustment = 1.0 + (0.5 - prob) * 0.6
                            else:
                                adjustment = 1.0
                        else:
                            if prob > 0.7:
                                # Heavy favorite lost - increase loss (bad performance)
                                adjustment = 1.0 + (prob - 0.5) * 0.6
                            elif prob < 0.3:
                                # Underdog lost - reduce loss (expected)
                                adjustment = 1.0 - (0.5 - prob) * 0.5
                            else:
                                adjustment = 1.0

                        # XGBoost contribution is the adjusted trueskill change weighted
                        xgboost_contribution = (
                            trueskill_change * adjustment
                        ) * weight_xgboost
                    else:
                        # Fallback if prediction fails
                        xgboost_contribution = trueskill_change * weight_xgboost
                else:
                    xgboost_contribution = trueskill_change * weight_xgboost
            else:
                xgboost_contribution = trueskill_change * weight_xgboost

        except Exception as e:
            logger.warning(
                f"Failed to calculate XGBoost contribution for player {player_id}: {e}"
            )
            xgboost_contribution = trueskill_change * weight_xgboost

        consensus_change = ts_contribution + xgboost_contribution

        logger.debug(
            f"Consensus MMR Change for player {player_id}: "
            f"TS({trueskill_change:.1f} * {weight_trueskill}) + "
            f"XG({xgboost_contribution / weight_xgboost:.1f} * {weight_xgboost}) = "
            f"{consensus_change:.1f}"
        )

        return consensus_change
