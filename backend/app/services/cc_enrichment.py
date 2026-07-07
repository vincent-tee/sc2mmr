"""
CommandCenter Enrichment - best-effort background upgrade of a match's
PlayerMatchMetrics with true engine-derived damage/economy stats.

Runs after the /upload response is already sent (via FastAPI BackgroundTasks)
so a slow or hung SC2 engine never adds latency to an interactive upload.
Gated by settings.upload_cc_enrichment_enabled (default off) — see that
setting's docstring for why this stays opt-in.
"""

import logging
from typing import Dict, Optional

import sc2reader
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Match, MatchPlayer, Player, PlayerMatchMetrics
from .commandcenter_parser import is_commandcenter_available, parse_replay_isolated

logger = logging.getLogger(__name__)


def _sc2_pid_to_name(replay_file_path: str) -> Dict[int, str]:
    """
    Authoritative pid -> player name mapping for this exact replay file.

    CommandCenter's replay-observer pid and sc2reader's Player.pid are both
    derived from the same protocol-level player list in the same file, so
    re-parsing with sc2reader (cheap, no engine) gives a reliable mapping —
    safer than assuming MatchPlayer DB row order matches engine pid order.
    """
    replay = sc2reader.load_replay(replay_file_path, load_level=2)
    return {
        int(getattr(p, "pid", 0)): str(getattr(p, "name", None) or "")
        for p in getattr(replay, "players", [])
        if getattr(p, "is_human", False)
    }


def enrich_match_with_cc_metrics(db: Session, match_id: int) -> int:
    """
    Best-effort: overwrite a match's PlayerMatchMetrics with CommandCenter's
    true damage/economy numbers where the engine succeeds. Never raises.

    Returns the number of players updated (0 if disabled/unavailable/failed).
    """
    if not settings.upload_cc_enrichment_enabled:
        return 0

    if not is_commandcenter_available():
        logger.debug("CC enrichment skipped: CommandCenter not available")
        return 0

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or not match.replay_file_path:
        return 0

    match_players = db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
    if not match_players:
        return 0

    try:
        pid_to_name = _sc2_pid_to_name(match.replay_file_path)
    except Exception as e:
        logger.warning(f"CC enrichment: could not re-load replay {match_id}: {e}")
        return 0

    num_players = len(pid_to_name)
    if num_players < 2:
        return 0

    cc_results = parse_replay_isolated(match.replay_file_path, num_players=num_players)
    if not cc_results:
        logger.info(f"CC enrichment: no metrics returned for match {match_id}")
        return 0

    player_ids = [mp.player_id for mp in match_players]
    players_by_id = {
        p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }
    name_to_match_player = {
        players_by_id[mp.player_id].name: mp
        for mp in match_players
        if mp.player_id in players_by_id
    }

    updated = 0
    for cc_pid, stats in cc_results.items():
        name = pid_to_name.get(cc_pid)
        mp = name_to_match_player.get(name) if name else None
        if not mp:
            continue

        metrics = (
            db.query(PlayerMatchMetrics)
            .filter(PlayerMatchMetrics.match_player_id == mp.id)
            .first()
        )
        if not metrics:
            metrics = PlayerMatchMetrics(match_player_id=mp.id)
            db.add(metrics)

        metrics.minerals_collected = int(stats.get("collected_minerals", 0))
        metrics.vespene_collected = int(stats.get("collected_vespene", 0))
        metrics.total_resources_collected = (
            metrics.minerals_collected + metrics.vespene_collected
        )
        metrics.resources_spent = int(
            stats.get("spent_minerals", 0) + stats.get("spent_vespene", 0)
        )
        metrics.damage_dealt = int(stats.get("total_damage_dealt", 0))
        metrics.damage_taken = int(stats.get("total_damage_taken", 0))
        if metrics.damage_taken > 0:
            metrics.damage_ratio = metrics.damage_dealt / metrics.damage_taken
        metrics.army_value_killed = int(stats.get("total_killed_value", 0))
        metrics.army_value_built = int(
            stats.get("total_value_units", 0) + stats.get("total_value_structures", 0)
        )
        updated += 1

    if updated:
        db.commit()
        logger.info(
            f"CC enrichment: updated {updated}/{num_players} players for match {match_id}"
        )
    return updated


def enrich_match_with_cc_metrics_background(match_id: int) -> None:
    """
    Entry point for FastAPI BackgroundTasks — opens its own DB session since
    the request-scoped session may already be closing by the time this runs.
    """
    from ..database import get_db_context

    try:
        with get_db_context() as db:
            enrich_match_with_cc_metrics(db, match_id)
    except Exception as e:
        logger.warning(f"CC enrichment background task failed for match {match_id}: {e}")
