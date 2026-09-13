"""Shared, atomic persistence for HTTP uploads and batch replay ingestion."""

from contextlib import contextmanager
from typing import Callable, Optional
import logging

from sqlalchemy.orm import Session

from ..exceptions import ValidationError
from ..models import FailedUpload, Match, MatchPlayer, Player, Race
from ..replay_parser import ReplayData
from ..rating_system import RatingSystem
from .player_service import PlayerService


@contextmanager
def ingestion_transaction(db: Session):
    connection = db.connection()
    if connection.dialect.name == "sqlite":
        driver = connection.connection.driver_connection
        if not driver.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
    try:
        with Session(bind=connection, join_transaction_mode="rollback_only") as work:
            yield work
            work.flush()
            if not connection.in_transaction():
                raise RuntimeError("An ingestion helper rolled back the transaction")
            work.commit()
        db.commit()
        db.expire_all()
    except BaseException:
        db.rollback()
        raise


def find_existing_match(db: Session, replay_data: ReplayData) -> Optional[Match]:
    existing = db.query(Match).filter(Match.replay_hash == replay_data.replay_hash).first()
    fingerprint = getattr(replay_data, "game_fingerprint", None)
    if existing is None and fingerprint:
        existing = db.query(Match).filter(Match.game_fingerprint == fingerprint).first()
    return existing


def upsert_match(db: Session, replay_data: ReplayData, replay_file_path=None) -> tuple[Match, bool]:
    match = find_existing_match(db, replay_data)
    if match is not None:
        return match, False
    match = Match(
        played_at=replay_data.played_at,
        game_mode=replay_data.game_mode,
        map_name=replay_data.map_name,
        duration_seconds=replay_data.duration_seconds,
        replay_file_path=replay_file_path,
        replay_hash=replay_data.replay_hash,
        game_fingerprint=getattr(replay_data, "game_fingerprint", None) or None,
        predicted_team1_win_prob=getattr(replay_data, "predicted_team1_win_prob", None),
        predicted_team2_win_prob=getattr(replay_data, "predicted_team2_win_prob", None),
    )
    db.add(match)
    db.flush()
    return match, True


def validate_result(replay_data: ReplayData) -> None:
    teams = {p.team for p in replay_data.players}
    winning_teams = {p.team for p in replay_data.players if p.won}
    if teams != {1, 2} or len(winning_teams) != 1:
        raise ValidationError("Replay must have two teams and one winning team")
    winner = next(iter(winning_teams))
    if any(bool(p.won) != (p.team == winner) for p in replay_data.players):
        raise ValidationError("Replay contains conflicting results within a team")


def resolve_player_names(db: Session, replay_data: ReplayData) -> list[str]:
    names = [PlayerService.resolve_canonical_name(
        db, p.name, replay_data.game_mode, len(replay_data.players)
    ) for p in replay_data.players]
    if len(set(names)) != len(names):
        raise ValidationError("Multiple replay players resolve to the same player")
    return names


def validate_team_experience(db: Session, replay_data: ReplayData, names: list[str]) -> None:
    experienced_teams = set()
    for participant, name in zip(replay_data.players, names):
        player = db.query(Player).filter(Player.name == name).first()
        if player is not None and player.total_games > 10:
            experienced_teams.add(participant.team)
    if experienced_teams != {1, 2}:
        raise ValidationError(
            "Team experience requirement not met: Each team must have "
            "at least one player with more than 10 games played"
        )


def create_participants(db: Session, match: Match, replay_data: ReplayData, names: list[str]) -> None:
    for participant, name in zip(replay_data.players, names):
        player = db.query(Player).filter(Player.name == name).first()
        if player is None:
            player = Player(name=name, is_ai=int(participant.is_ai))
            db.add(player)
            db.flush()
        db.add(MatchPlayer(
            match_id=match.id, player_id=player.id, team_number=participant.team,
            race=Race(participant.race), won=int(participant.won),
            mu_before=player.mu, sigma_before=player.sigma,
            mu_after=player.mu, sigma_after=player.sigma,
        ))
    db.flush()


def validate_existing_result(match: Match, replay_data: ReplayData, names: list[str]) -> None:
    existing = {mp.player.name: bool(mp.won) for mp in match.participants}
    incoming = {name: bool(p.won) for name, p in zip(names, replay_data.players)}
    if existing != incoming:
        raise ValidationError("Replay conflicts with the recorded participants or winner")


def ingest_match(
    db: Session,
    replay_data: ReplayData,
    replay_file_path: Optional[str] = None,
    *,
    save_metrics: Optional[Callable[[Session, Match], None]] = None,
    require_experience: bool = True,
    failed_upload_id: Optional[int] = None,
) -> tuple[Match, bool]:
    from ..impact_service import ImpactService
    from ..performance_rating import PerformanceRatingAdjuster

    validate_result(replay_data)
    with ingestion_transaction(db) as work:
        match, created = upsert_match(work, replay_data, replay_file_path)
        names = resolve_player_names(work, replay_data)
        if created:
            if require_experience:
                validate_team_experience(work, replay_data, names)
            create_participants(work, match, replay_data, names)
        else:
            validate_existing_result(match, replay_data, names)

        refresh = created or match.replay_hash == replay_data.replay_hash or (
            replay_data.duration_seconds > match.duration_seconds
        )
        if refresh:
            if replay_file_path:
                match.replay_file_path = replay_file_path
                match.replay_hash = replay_data.replay_hash
            match.duration_seconds = max(match.duration_seconds, replay_data.duration_seconds)
            if save_metrics:
                save_metrics(work, match)
            work.flush()
        if created:
            RatingSystem.update_ratings_from_match(work, replay_data, match)
            if save_metrics:
                PerformanceRatingAdjuster.adjust_ratings_for_match(work, int(match.id))
            ImpactService.update_synergies(work, int(match.id))
        if failed_upload_id is not None:
            failed = work.get(FailedUpload, failed_upload_id)
            if failed is not None:
                work.delete(failed)
        match_id = match.id
    return db.query(Match).filter(Match.id == match_id).one(), created


def save_advanced_metrics(db: Session, match: Match, advanced_data) -> None:
    from ..impact_service import ImpactService

    for metrics in advanced_data.player_metrics:
        name = PlayerService.resolve_canonical_name(
            db, metrics.player_name, match.game_mode, len(advanced_data.basic_data.players)
        )
        mp = (db.query(MatchPlayer).join(Player)
              .filter(MatchPlayer.match_id == match.id, Player.name == name).first())
        if mp is not None:
            ImpactService.save_match_metrics(db, mp.id, metrics)
            ImpactService.update_player_averages(db, mp.player_id)


def run_optional_processing(db: Session, name: str, action: Callable) -> None:
    try:
        with ingestion_transaction(db) as work:
            action(work)
    except Exception:
        logging.getLogger(__name__).exception("%s failed", name)


def post_process_match(db: Session, match_id: int, created: bool, replay_path=None,
                       optimize: bool = False) -> None:
    from .achievement_service import AchievementService
    from .balance_capture import BalancePredictionService
    from .ml_features_service import MLFeaturesService
    from .rivalry_service import RivalryService
    from ..online_learning import OnlineLearningEngine
    from ..auto_adaptive import trigger_auto_optimization

    def award_achievements(work):
        for mp in work.query(MatchPlayer).filter(MatchPlayer.match_id == match_id):
            AchievementService.check_and_award_all(work, mp.player_id, match_id)

    def record_outcome(work):
        team1_won = work.query(MatchPlayer).filter(
            MatchPlayer.match_id == match_id, MatchPlayer.team_number == 1,
            MatchPlayer.won == 1,
        ).first() is not None
        OnlineLearningEngine(work).record_outcome(match_id, team1_won)

    if replay_path:
        run_optional_processing(db, "ML feature extraction", lambda work:
                                MLFeaturesService.extract_and_save_ml_features(work, replay_path, match_id))
    run_optional_processing(db, "Balance prediction resolution", lambda work:
                            BalancePredictionService.resolve_for_match(work, work.get(Match, match_id)))
    if created:
        run_optional_processing(db, "Achievements", award_achievements)
        run_optional_processing(db, "Online learning", record_outcome)
        run_optional_processing(db, "Rivalry calculation", RivalryService.calculate_all_rivalries)
        if optimize:
            run_optional_processing(db, "Optimization", trigger_auto_optimization)
