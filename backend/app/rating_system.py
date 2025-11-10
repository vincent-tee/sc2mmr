"""
TrueSkill rating system integration for player skill tracking.

TrueSkill is a Bayesian skill rating system that:
- Models player skill as a normal distribution (mu, sigma)
- mu: skill estimate (default 25.0)
- sigma: uncertainty (default 8.333, decreases with games played)
- Handles team-based games naturally
- Increases uncertainty over time without games (skill decay)
"""
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import trueskill
from sqlalchemy.orm import Session

from .models import Player, Match, MatchPlayer
from .replay_parser import ReplayData


# TrueSkill environment configuration
# These defaults work well for most games
trueskill.setup(
    mu=25.0,              # Initial skill estimate
    sigma=8.333,          # Initial uncertainty
    beta=4.166,           # Skill class width (half of sigma)
    tau=0.0833,           # Dynamics factor (skill change per day)
    draw_probability=0.0  # No draws in SC2
)


class RatingSystem:
    """
    Manages TrueSkill ratings for players.
    """

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
    def get_conservative_rating(mu: float, sigma: float) -> float:
        """
        Get conservative skill estimate (mu - 3*sigma).
        This is the MMR we display and use for balancing.

        Args:
            mu: Skill estimate
            sigma: Uncertainty

        Returns:
            Conservative MMR value
        """
        return mu - (3 * sigma)

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
