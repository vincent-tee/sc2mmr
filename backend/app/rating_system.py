"""
TrueSkill rating system integration for player skill tracking.

TrueSkill is a Bayesian skill rating system that:
- Models player skill as a normal distribution (mu, sigma)
- mu: skill estimate (default 25.0)
- sigma: uncertainty (default 8.333, decreases with games played)
- Handles team-based games naturally
- Increases uncertainty over time without games (skill decay)
- Recency weighting: Recent matches count more than older matches
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import trueskill
import math
from sqlalchemy.orm import Session

from .models import Player, Match, MatchPlayer
from .replay_parser import ReplayData
from .config import settings
import logging

logger = logging.getLogger(__name__)


# TrueSkill environment configuration using centralized settings
trueskill.setup(
    mu=settings.trueskill_mu,
    sigma=settings.trueskill_sigma,
    beta=settings.trueskill_beta,
    tau=settings.trueskill_tau,
    draw_probability=settings.trueskill_draw_probability,
)

# Recency weighting configuration from settings
RECENCY_HALF_LIFE_DAYS = settings.recency_half_life_days
RECENCY_ENABLED = settings.recency_enabled


class RatingSystem:
    """Manage rating persistence using the shared rating policy.

    Official display MMR is base + mu_multiplier * mu - 200 * sigma.
    The separate legacy conservative helper uses the configured sigma multiplier.
    """

    # MMR Calculation Constants - from centralized settings
    MMR_BASE = settings.mmr_base
    MMR_MU_MULTIPLIER = settings.mmr_mu_multiplier
    MMR_SIGMA_MULTIPLIER = settings.mmr_sigma_multiplier

    @staticmethod
    def create_rating(mu: float = 25.0, sigma: float = 8.333) -> trueskill.Rating:
        """
        Create a TrueSkill Rating object.

        Args:
            mu: Skill estimate
            sigma: Uncertainty

        Returns:
            TrueSkill Rating object
        """
        return trueskill.Rating(mu=mu, sigma=sigma)

    @staticmethod
    def calculate_display_mmr(mu: float, sigma: float) -> float:
        """
        Calculate the official display MMR used everywhere in the system.

        Formula: 1000 + (100 * mu) - (200 * sigma)

        The sigma penalty is settled doctrine (owner decision 2026-07-02):
        it measured +2.3pp match-prediction accuracy over the no-sigma
        formula (McNemar p=0.031, n=860; see
        docs/superpowers/campaign/rating-consolidation-log.md Session 2),
        besides ensuring ranks are 'earned' through games.
        """
        return (
            RatingSystem.MMR_BASE
            + (RatingSystem.MMR_MU_MULTIPLIER * mu)
            - (200.0 * sigma)
        )

    @staticmethod
    def get_conservative_rating(mu: float, sigma: float) -> float:
        """
        Get conservative MMR rating for matchmaking and team balancing.

        Formula: MMR = 1000 + 100*mu - 300*sigma

        This formula INCLUDES sigma (uncertainty) because:
        - Provides a "worst case" estimate for fair matchmaking
        - New/uncertain players are rated more conservatively
        - Helps create balanced teams by accounting for uncertainty

        Args:
            mu: Skill estimate
            sigma: Uncertainty (higher = less certain about skill)

        Returns:
            Conservative MMR value
        """
        return (
            RatingSystem.MMR_BASE
            + (RatingSystem.MMR_MU_MULTIPLIER * mu)
            - (RatingSystem.MMR_SIGMA_MULTIPLIER * sigma)
        )

    @staticmethod
    def calculate_win_probability(
        team1_ratings: List[trueskill.Rating], team2_ratings: List[trueskill.Rating]
    ) -> Tuple[float, float]:
        """
        Calculate win probability for each team using TrueSkill.

        This uses the Gaussian CDF to calculate the probability that
        team 1's skill is greater than team 2's skill.

        Args:
            team1_ratings: List of TrueSkill Rating objects for team 1
            team2_ratings: List of TrueSkill Rating objects for team 2

        Returns:
            Tuple of (team1_win_prob, team2_win_prob)
            Both values are between 0.0 and 1.0 and sum to 1.0
        """
        from .rating_policy import win_probability

        probability = win_probability(team1_ratings, team2_ratings)
        return probability, 1.0 - probability

    @staticmethod
    def apply_skill_decay(
        player: Player, days_since_last_game: int, db: Optional[Session] = None,
        reference_date: Optional[datetime] = None,
    ) -> None:
        from .rating_policy import decayed_sigma

        gap = RatingSystem.calculate_typical_session_gap(db, player, reference_date) if db else 0.0
        player.sigma = decayed_sigma(player.sigma, days_since_last_game, player.total_games, gap)

    @staticmethod
    def calculate_typical_session_gap(
        db: Session, player: Player, reference_date: Optional[datetime] = None,
    ) -> float:
        from .rating_policy import typical_session_gap

        query = db.query(Match.played_at).join(MatchPlayer).filter(
            MatchPlayer.player_id == player.id, Match.played_at.isnot(None)
        )
        # The current game's timestamp is available, but future backfilled
        # history must never influence an earlier game's inactivity policy.
        if reference_date is not None:
            query = query.filter(Match.played_at <= reference_date)
        return typical_session_gap([row[0] for row in query.all()])

    @staticmethod
    def calculate_recency_weight(
        days_ago: float, reference_date: Optional[datetime] = None
    ) -> float:
        """
        Calculate exponential recency weight for a match.

        Weight decays exponentially with half-life of RECENCY_HALF_LIFE_DAYS.
        - Match today: weight = 1.0
        - Match RECENCY_HALF_LIFE_DAYS ago: weight = 0.5
        - Match 2*RECENCY_HALF_LIFE_DAYS ago: weight = 0.25

        Args:
            days_ago: Number of days since the match
            reference_date: Reference date for calculating days_ago (defaults to now)

        Returns:
            Weight multiplier (0.0 to 1.0)
        """
        if not RECENCY_ENABLED:
            return 1.0

        if days_ago < 0:
            days_ago = 0

        # Exponential decay: weight = 0.5^(days_ago / half_life)
        decay_factor = math.log(0.5) / RECENCY_HALF_LIFE_DAYS
        weight = math.exp(decay_factor * days_ago)

        return weight

    @staticmethod
    def update_recency_weighted_rating(
        db: Session, player: Player, reference_date: Optional[datetime] = None
    ) -> None:
        """
        Calculate and update a player's recency-weighted MMR.

        This rating weighs recent matches more heavily than older matches,
        providing a better estimate of current skill level.

        Args:
            db: Database session
            player: Player to update
            reference_date: Date to calculate recency from (defaults to now)
        """
        if reference_date is None:
            reference_date = datetime.utcnow()

        # Get all matches for this player, ordered by date
        match_players = (
            db.query(MatchPlayer)
            .filter(MatchPlayer.player_id == player.id)
            .join(Match)
            .order_by(Match.played_at)
            .all()
        )

        if not match_players:
            # No matches, use standard MMR
            player.recency_weighted_mmr = player.mmr
            return

        # Calculate weighted performance
        total_weight = 0.0
        weighted_mmr_sum = 0.0

        for mp in match_players:
            match = db.query(Match).filter(Match.id == mp.match_id).first()
            if not match:
                continue

            # Calculate days ago
            days_ago = (reference_date - match.played_at).total_seconds() / 86400

            # Calculate weight
            weight = RatingSystem.calculate_recency_weight(days_ago)

            # Use post-match display MMR for this calculation
            # Using display MMR (not conservative) for consistency with Player.mmr
            match_mmr = RatingSystem.calculate_display_mmr(mp.mu_after, mp.sigma_after)

            weighted_mmr_sum += match_mmr * weight
            total_weight += weight

        if total_weight > 0:
            player.recency_weighted_mmr = weighted_mmr_sum / total_weight
        else:
            player.recency_weighted_mmr = player.mmr

        db.commit()

    @staticmethod
    def update_ratings_from_match(
        db: Session, replay_data: ReplayData, match: Match
    ) -> None:
        """
        Update player ratings based on match results.

        Args:
            db: Database session
            replay_data: Parsed replay data
            match: Match database object

        This function:
        1. Gets or creates players
        2. Applies skill decay if needed
        3. Calculates new ratings using TrueSkill
        4. Updates player statistics
        5. Creates MatchPlayer records
        """
        from .services.player_service import PlayerService

        # Organize players by team
        team_1_players = [p for p in replay_data.players if p.team == 1]
        team_2_players = [p for p in replay_data.players if p.team == 2]

        # Get or create Player objects
        team_1_db = []
        team_2_db = []

        # Get game mode and player count for alias resolution
        game_mode = match.game_mode
        num_players = len(replay_data.players)

        for player_data in team_1_players:
            # Resolve canonical name (handle aliases like barcodes)
            resolved_name = PlayerService.resolve_canonical_name(
                db, player_data.name, game_mode, num_players
            )
            player = db.query(Player).filter(Player.name == resolved_name).first()
            if not player:
                player = Player(name=resolved_name, is_ai=1 if player_data.is_ai else 0)
                db.add(player)
                db.flush()
            team_1_db.append((player, player_data))

        for player_data in team_2_players:
            # Resolve canonical name (handle aliases like barcodes)
            resolved_name = PlayerService.resolve_canonical_name(
                db, player_data.name, game_mode, num_players
            )
            player = db.query(Player).filter(Player.name == resolved_name).first()
            if not player:
                player = Player(name=resolved_name, is_ai=1 if player_data.is_ai else 0)
                db.add(player)
                db.flush()
            team_2_db.append((player, player_data))

        # Apply adaptive skill decay for inactive players
        # Uses per-player typical session gaps to avoid penalizing infrequent players
        current_date = replay_data.played_at
        for player, _ in team_1_db + team_2_db:
            if player.last_played:
                days_since = (current_date - player.last_played).days
                if days_since > 0:
                    RatingSystem.apply_skill_decay(player, days_since, db, current_date)

        # Create TrueSkill Rating objects for each team
        team_1_ratings = [
            trueskill.Rating(mu=player.mu, sigma=player.sigma)
            for player, _ in team_1_db
        ]
        team_2_ratings = [
            trueskill.Rating(mu=player.mu, sigma=player.sigma)
            for player, _ in team_2_db
        ]

        # Calculate and store win probabilities BEFORE the match
        team1_win_prob, team2_win_prob = RatingSystem.calculate_win_probability(
            team_1_ratings, team_2_ratings
        )
        match.predicted_team1_win_prob = team1_win_prob
        match.predicted_team2_win_prob = team2_win_prob

        # Determine winner (ranks: 0 for winner, 1 for loser)
        team_1_won = team_1_players[0].won
        # Calculate new ratings
        from .rating_policy import rate_teams

        new_ratings = rate_teams(team_1_ratings, team_2_ratings, team_1_won)

        new_team_1_ratings = new_ratings[0]
        new_team_2_ratings = new_ratings[1]

        # Update player ratings and statistics
        for i, (player, player_data) in enumerate(team_1_db):
            old_rating = team_1_ratings[i]
            new_rating = new_team_1_ratings[i]

            # Upsert MatchPlayer record
            match_player = (
                db.query(MatchPlayer)
                .filter(
                    MatchPlayer.match_id == match.id, MatchPlayer.player_id == player.id
                )
                .first()
            )
            if not match_player:
                match_player = MatchPlayer(
                    match_id=match.id,
                    player_id=player.id,
                    team_number=1,
                    race=player_data.race,
                    won=1 if player_data.won else 0,
                    mu_before=old_rating.mu,
                    sigma_before=old_rating.sigma,
                    mu_after=new_rating.mu,
                    sigma_after=new_rating.sigma,
                    mmr_before=RatingSystem.calculate_display_mmr(
                        old_rating.mu, old_rating.sigma
                    ),
                    mmr_after=RatingSystem.calculate_display_mmr(
                        new_rating.mu, new_rating.sigma
                    ),
                )
                db.add(match_player)
            else:
                match_player.mu_before = old_rating.mu
                match_player.sigma_before = old_rating.sigma
                match_player.mu_after = new_rating.mu
                match_player.sigma_after = new_rating.sigma
                match_player.mmr_before = RatingSystem.calculate_display_mmr(
                    old_rating.mu, old_rating.sigma
                )
                match_player.mmr_after = RatingSystem.calculate_display_mmr(
                    new_rating.mu, new_rating.sigma
                )

            # Update player
            player.mu = new_rating.mu
            player.sigma = new_rating.sigma
            player.mmr = RatingSystem.calculate_display_mmr(
                new_rating.mu, new_rating.sigma
            )
            player.total_games += 1
            if player_data.won:
                player.wins += 1
            else:
                player.losses += 1

            # Update race statistics
            race_attr = f"{player_data.race.value.lower()}_games"
            setattr(player, race_attr, getattr(player, race_attr) + 1)

            # Advance-only: replays can be ingested out of chronological
            # order (backfills, reprocessed failed uploads), so never let
            # an older match's date push last_played backwards.
            if not player.last_played or replay_data.played_at > player.last_played:
                player.last_played = replay_data.played_at

        for i, (player, player_data) in enumerate(team_2_db):
            old_rating = team_2_ratings[i]
            new_rating = new_team_2_ratings[i]

            # Upsert MatchPlayer record
            match_player = (
                db.query(MatchPlayer)
                .filter(
                    MatchPlayer.match_id == match.id, MatchPlayer.player_id == player.id
                )
                .first()
            )
            if not match_player:
                match_player = MatchPlayer(
                    match_id=match.id,
                    player_id=player.id,
                    team_number=2,
                    race=player_data.race,
                    won=1 if player_data.won else 0,
                    mu_before=old_rating.mu,
                    sigma_before=old_rating.sigma,
                    mu_after=new_rating.mu,
                    sigma_after=new_rating.sigma,
                    mmr_before=RatingSystem.calculate_display_mmr(
                        old_rating.mu, old_rating.sigma
                    ),
                    mmr_after=RatingSystem.calculate_display_mmr(
                        new_rating.mu, new_rating.sigma
                    ),
                )
                db.add(match_player)
            else:
                match_player.mu_before = old_rating.mu
                match_player.sigma_before = old_rating.sigma
                match_player.mu_after = new_rating.mu
                match_player.sigma_after = new_rating.sigma
                match_player.mmr_before = RatingSystem.calculate_display_mmr(
                    old_rating.mu, old_rating.sigma
                )
                match_player.mmr_after = RatingSystem.calculate_display_mmr(
                    new_rating.mu, new_rating.sigma
                )

            # Update player
            player.mu = new_rating.mu
            player.sigma = new_rating.sigma
            player.mmr = RatingSystem.calculate_display_mmr(
                new_rating.mu, new_rating.sigma
            )
            player.total_games += 1
            if player_data.won:
                player.wins += 1
            else:
                player.losses += 1

            # Update race statistics
            race_attr = f"{player_data.race.value.lower()}_games"
            setattr(player, race_attr, getattr(player, race_attr) + 1)

            # Advance-only: see team_1 loop above for rationale.
            if not player.last_played or replay_data.played_at > player.last_played:
                player.last_played = replay_data.played_at

        db.commit()

    @staticmethod
    def calibrate_new_player(
        db: Session, new_player_name: str, similar_to_player_id: int
    ) -> Player:
        """
        Calibrate a new outsider player based on a similar core player.

        Args:
            db: Database session
            new_player_name: Name of the new player
            similar_to_player_id: ID of similar core player

        Returns:
            New Player object with calibrated rating
        """
        # Get the similar player
        similar_player = (
            db.query(Player).filter(Player.id == similar_to_player_id).first()
        )
        if not similar_player:
            raise ValueError(f"Player with ID {similar_to_player_id} not found")

        # Create new player with similar rating but higher uncertainty
        new_player = Player(
            name=new_player_name,
            mu=similar_player.mu,
            sigma=min(similar_player.sigma + 2.0, 8.333),  # Add uncertainty
            is_core_player=0,  # Mark as outsider
        )

        db.add(new_player)
        db.commit()
        db.refresh(new_player)

        return new_player

    @staticmethod
    def get_player_ratings_dict(db: Session) -> Dict[int, Tuple[float, float]]:
        """
        Get all player ratings as a dictionary.

        Args:
            db: Database session

        Returns:
            Dict mapping player_id to (mu, sigma) tuple
        """
        players = db.query(Player).all()
        return {player.id: (player.mu, player.sigma) for player in players}
