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


# TrueSkill environment configuration using centralized settings
trueskill.setup(
    mu=settings.trueskill_mu,
    sigma=settings.trueskill_sigma,
    beta=settings.trueskill_beta,
    tau=settings.trueskill_tau,
    draw_probability=settings.trueskill_draw_probability
)

# Recency weighting configuration from settings
RECENCY_HALF_LIFE_DAYS = settings.recency_half_life_days
RECENCY_ENABLED = settings.recency_enabled


class RatingSystem:
    """
    Manages TrueSkill ratings for players.

    MMR Calculation Constants (Single Source of Truth from config):
    - MMR_BASE: Base MMR value for all players (default 1000)
    - MMR_MU_MULTIPLIER: How much each mu point affects MMR (default 40)
    - MMR_SIGMA_MULTIPLIER: How much sigma affects conservative MMR (default 120)

    Two MMR formulas exist for different purposes:
    1. Display MMR: MMR_BASE + MMR_MU_MULTIPLIER*mu (used for player cards, leaderboards)
       - Does NOT include sigma to avoid penalizing inactive players
    2. Conservative MMR: MMR_BASE + MMR_MU_MULTIPLIER*mu - MMR_SIGMA_MULTIPLIER*sigma
       - Includes sigma to give conservative estimate for balanced matches
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
    def calculate_display_mmr(mu: float) -> float:
        """
        Calculate MMR for display purposes (player cards, leaderboards).

        Formula: MMR = 1000 + 40*mu

        This formula does NOT include sigma (uncertainty) because:
        - Inactive players shouldn't have their displayed rating penalized
        - Provides a stable, intuitive rating that only changes with match results
        - New players start at ~2000 MMR (mu=25)

        Args:
            mu: Skill estimate from TrueSkill

        Returns:
            Display MMR value (typically 800-2400 range)
        """
        return RatingSystem.MMR_BASE + (RatingSystem.MMR_MU_MULTIPLIER * mu)

    @staticmethod
    def get_conservative_rating(mu: float, sigma: float) -> float:
        """
        Get conservative MMR rating for matchmaking and team balancing.

        Formula: MMR = 1000 + 40*mu - 120*sigma

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
        return (RatingSystem.MMR_BASE +
                (RatingSystem.MMR_MU_MULTIPLIER * mu) -
                (RatingSystem.MMR_SIGMA_MULTIPLIER * sigma))

    @staticmethod
    def calculate_win_probability(
        team1_ratings: List[trueskill.Rating],
        team2_ratings: List[trueskill.Rating]
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
        import math
        from scipy.stats import norm

        # Calculate team strengths (sum of mu values)
        team1_mu = sum(r.mu for r in team1_ratings)
        team2_mu = sum(r.mu for r in team2_ratings)

        # Calculate team uncertainties (sum of sigma squared, then sqrt)
        team1_sigma_sq = sum(r.sigma ** 2 for r in team1_ratings)
        team2_sigma_sq = sum(r.sigma ** 2 for r in team2_ratings)

        # Total variance
        total_sigma = math.sqrt(team1_sigma_sq + team2_sigma_sq)

        # Difference in team strengths
        delta_mu = team1_mu - team2_mu

        # Calculate win probability using cumulative distribution function
        # P(team1 wins) = P(team1_strength > team2_strength)
        team1_win_prob = norm.cdf(delta_mu / total_sigma)
        team2_win_prob = 1.0 - team1_win_prob

        return (team1_win_prob, team2_win_prob)

    @staticmethod
    def apply_skill_decay(player: Player, days_since_last_game: int) -> None:
        """
        Increase uncertainty (sigma) for players who haven't played recently.
        This models skill deterioration from inactivity.

        Args:
            player: Player to apply decay to
            days_since_last_game: Number of days since last game
        """
        # Increase sigma based on days inactive
        # tau (0.0833) per day is the default dynamics factor
        decay_per_day = 0.0833
        sigma_increase = decay_per_day * days_since_last_game

        # Cap sigma at initial value (8.333)
        player.sigma = min(player.sigma + sigma_increase, 8.333)

    @staticmethod
    def calculate_recency_weight(days_ago: float, reference_date: Optional[datetime] = None) -> float:
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
        db: Session,
        player: Player,
        reference_date: Optional[datetime] = None
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
        match_players = db.query(MatchPlayer).filter(
            MatchPlayer.player_id == player.id
        ).join(Match).order_by(Match.played_at).all()

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
            match_mmr = RatingSystem.calculate_display_mmr(mp.mu_after)

            weighted_mmr_sum += match_mmr * weight
            total_weight += weight

        if total_weight > 0:
            player.recency_weighted_mmr = weighted_mmr_sum / total_weight
        else:
            player.recency_weighted_mmr = player.mmr

        db.commit()

    @staticmethod
    def update_ratings_from_match(
        db: Session,
        replay_data: ReplayData,
        match: Match
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
        # Organize players by team
        team_1_players = [p for p in replay_data.players if p.team == 1]
        team_2_players = [p for p in replay_data.players if p.team == 2]

        # Get or create Player objects
        team_1_db = []
        team_2_db = []

        for player_data in team_1_players:
            player = db.query(Player).filter(Player.name == player_data.name).first()
            if not player:
                player = Player(name=player_data.name)
                db.add(player)
                db.flush()
            team_1_db.append((player, player_data))

        for player_data in team_2_players:
            player = db.query(Player).filter(Player.name == player_data.name).first()
            if not player:
                player = Player(name=player_data.name)
                db.add(player)
                db.flush()
            team_2_db.append((player, player_data))

        # Apply skill decay for inactive players
        current_date = replay_data.played_at
        for player, _ in team_1_db + team_2_db:
            if player.last_played:
                days_since = (current_date - player.last_played).days
                if days_since > 0:
                    RatingSystem.apply_skill_decay(player, days_since)

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
        if team_1_won:
            ranks = [0, 1]  # Team 1 wins
        else:
            ranks = [1, 0]  # Team 2 wins

        # Calculate new ratings
        new_ratings = trueskill.rate(
            [team_1_ratings, team_2_ratings],
            ranks=ranks
        )

        new_team_1_ratings = new_ratings[0]
        new_team_2_ratings = new_ratings[1]

        # Update player ratings and statistics
        for i, (player, player_data) in enumerate(team_1_db):
            old_rating = team_1_ratings[i]
            new_rating = new_team_1_ratings[i]

            # Create MatchPlayer record
            match_player = MatchPlayer(
                match_id=match.id,
                player_id=player.id,
                team_number=1,
                race=player_data.race,
                won=1 if player_data.won else 0,
                mu_before=old_rating.mu,
                sigma_before=old_rating.sigma,
                mu_after=new_rating.mu,
                sigma_after=new_rating.sigma
            )
            db.add(match_player)

            # Update player
            player.mu = new_rating.mu
            player.sigma = new_rating.sigma
            player.total_games += 1
            if player_data.won:
                player.wins += 1
            else:
                player.losses += 1

            # Update race statistics
            race_attr = f"{player_data.race.value.lower()}_games"
            setattr(player, race_attr, getattr(player, race_attr) + 1)

            player.last_played = replay_data.played_at

        for i, (player, player_data) in enumerate(team_2_db):
            old_rating = team_2_ratings[i]
            new_rating = new_team_2_ratings[i]

            # Create MatchPlayer record
            match_player = MatchPlayer(
                match_id=match.id,
                player_id=player.id,
                team_number=2,
                race=player_data.race,
                won=1 if player_data.won else 0,
                mu_before=old_rating.mu,
                sigma_before=old_rating.sigma,
                mu_after=new_rating.mu,
                sigma_after=new_rating.sigma
            )
            db.add(match_player)

            # Update player
            player.mu = new_rating.mu
            player.sigma = new_rating.sigma
            player.total_games += 1
            if player_data.won:
                player.wins += 1
            else:
                player.losses += 1

            # Update race statistics
            race_attr = f"{player_data.race.value.lower()}_games"
            setattr(player, race_attr, getattr(player, race_attr) + 1)

            player.last_played = replay_data.played_at

        db.commit()

        # Update recency-weighted ratings for all players in this match
        if RECENCY_ENABLED:
            for player, _ in team_1_db + team_2_db:
                RatingSystem.update_recency_weighted_rating(db, player, replay_data.played_at)

    @staticmethod
    def calibrate_new_player(
        db: Session,
        new_player_name: str,
        similar_to_player_id: int
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
        similar_player = db.query(Player).filter(Player.id == similar_to_player_id).first()
        if not similar_player:
            raise ValueError(f"Player with ID {similar_to_player_id} not found")

        # Create new player with similar rating but higher uncertainty
        new_player = Player(
            name=new_player_name,
            mu=similar_player.mu,
            sigma=min(similar_player.sigma + 2.0, 8.333),  # Add uncertainty
            is_core_player=0  # Mark as outsider
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
