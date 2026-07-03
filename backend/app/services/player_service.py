from sqlalchemy.orm import Session
from ..models import Player, PlayerAlias, GameMode
from typing import Optional


class PlayerService:
    @staticmethod
    def resolve_canonical_name(
        db: Session, name: str, game_mode: GameMode, num_players: int
    ) -> str:
        """
        Resolves a player name to its canonical version based on alias mappings.

        Supports conditional mapping, such as excluding 1v1 games for barcodes.
        """
        alias = db.query(PlayerAlias).filter(PlayerAlias.source_name == name).first()

        if not alias:
            return name

        is_1v1 = game_mode == GameMode.ONE_V_ONE or num_players < 2

        if alias.exclude_1v1 and is_1v1:
            return name

        if num_players < alias.min_players:
            return name

        return alias.target_player.name

    @staticmethod
    def add_alias(
        db: Session,
        source_name: str,
        target_player_name: str,
        exclude_1v1: bool = True,
        min_players: int = 4,
    ) -> PlayerAlias:
        target_player = (
            db.query(Player).filter(Player.name == target_player_name).first()
        )
        if not target_player:
            raise ValueError(f"Target player '{target_player_name}' not found")

        existing = (
            db.query(PlayerAlias).filter(PlayerAlias.source_name == source_name).first()
        )
        if existing:
            existing.target_player_id = target_player.id
            existing.exclude_1v1 = 1 if exclude_1v1 else 0
            existing.min_players = min_players
            db.commit()
            return existing

        alias = PlayerAlias(
            source_name=source_name,
            target_player_id=target_player.id,
            exclude_1v1=1 if exclude_1v1 else 0,
            min_players=min_players,
        )
        db.add(alias)
        db.commit()
        db.refresh(alias)
        return alias
