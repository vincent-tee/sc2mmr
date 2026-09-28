import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..impact_service import ImpactService
from ..models import Match, MatchPlayer, PlayerMatchMetrics

BACKFILLED_FIELDS = (
    "army_value_built", "army_value_killed", "army_value_lost", "spending_efficiency",
    "peak_active_workers", "units_killed", "units_lost", "kill_death_ratio",
    "economic_score", "combat_score", "efficiency_score", "overall_impact",
)


@dataclass
class BackfillStats:
    updated: int = 0
    created: int = 0
    unmatched: int = 0
    players_reaveraged: int = 0


def apply_metrics_rows(db: Session, rows: list[dict]) -> BackfillStats:
    stats = BackfillStats()
    match_ids = dict(db.query(Match.replay_hash, Match.id)
                     .filter(Match.replay_hash.in_({r["replay_hash"] for r in rows})).all())
    touched_players = set()
    for row in rows:
        participant = db.query(MatchPlayer).filter(
            MatchPlayer.match_id == match_ids.get(row["replay_hash"]),
            MatchPlayer.player_id == row["player_id"],
        ).first()
        if participant is None:
            stats.unmatched += 1
            continue
        metrics = db.query(PlayerMatchMetrics).filter(
            PlayerMatchMetrics.match_player_id == participant.id).first()
        if metrics is None:
            metrics = PlayerMatchMetrics(match_player_id=participant.id)
            db.add(metrics)
            stats.created += 1
        else:
            stats.updated += 1
        for name in BACKFILLED_FIELDS:
            setattr(metrics, name, row[name])
        metrics.unit_composition = json.dumps(row["unit_composition"]) if row["unit_composition"] else None
        touched_players.add(participant.player_id)
    db.flush()
    for player_id in touched_players:
        ImpactService.update_player_averages(db, player_id)
    db.commit()
    stats.players_reaveraged = len(touched_players)
    return stats
