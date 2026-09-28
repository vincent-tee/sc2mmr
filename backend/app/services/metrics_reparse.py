"""Re-parse stored replays with the upload parser and save their metrics the way an upload would.

Rows are produced away from any database (one per replay file) and keyed by
replay hash and each player's in-replay name, so the same rows can be diffed
and applied against the local database or production.
"""

from dataclasses import asdict, dataclass, field, fields
from statistics import mean, median
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..advanced_parser import PlayerMetrics, parse_replay_advanced
from ..impact_service import ImpactService
from ..models import KillEvent, Match, MatchPlayer, Player, PlayerMatchMetrics
from .derived_data import mark_stale
from .player_service import PlayerService

# Only the winner-independent parts of a parse are used, so any team will do;
# naming one stops replays without a recorded result from needing the stats heuristic.
PLACEHOLDER_WINNER_TEAM = 1

DIFFED_FIELDS = (
    "supply_block_seconds", "units_killed", "units_lost", "workers_killed", "workers_lost",
    "army_value_killed", "army_value_lost", "total_resources_collected", "resources_spent",
    "economic_score", "combat_score", "efficiency_score", "overall_impact", "kill_death_ratio",
)


def serializable(metrics: PlayerMetrics) -> dict:
    row = asdict(metrics)
    if metrics.damage_timeline is not None:
        row["damage_timeline"] = metrics.damage_timeline.damage_events
    return row


def reparse_row(replay_path: str, replay_hash: str) -> dict:
    parsed = parse_replay_advanced(replay_path, manual_winner_team=PLACEHOLDER_WINNER_TEAM)
    return {
        "replay_hash": replay_hash,
        "num_players": len(parsed.basic_data.players),
        "players": [serializable(m) for m in parsed.player_metrics],
        "kill_events": parsed.kill_events,
    }


def player_metrics_from(row_player: dict) -> PlayerMetrics:
    known = {f.name for f in fields(PlayerMetrics)}
    return PlayerMetrics(**{k: v for k, v in row_player.items() if k in known})


def participants_by_replay_name(db: Session, match: Match, row: dict) -> dict:
    """Map each replay player name to the stored participant it belongs to."""
    found = {}
    for player in row["players"]:
        canonical = PlayerService.resolve_canonical_name(
            db, player["player_name"], match.game_mode, row["num_players"])
        mp = (db.query(MatchPlayer).join(Player)
              .filter(MatchPlayer.match_id == match.id, Player.name == canonical).first())
        if mp is not None:
            found[player["player_name"]] = mp
    return found


@dataclass
class FieldChange:
    changed: int = 0
    deltas: list = field(default_factory=list)


@dataclass
class ReparseReport:
    matches: int = 0
    unmatched_replays: int = 0
    players_updated: int = 0
    players_unmatched: int = 0
    fields: dict = field(default_factory=dict)

    def summary(self) -> dict:
        def describe(change: FieldChange) -> dict:
            if not change.deltas:
                return {"changed": 0}
            return {"changed": change.changed, "median_change": round(median(change.deltas), 2),
                    "mean_change": round(mean(change.deltas), 2),
                    "largest_drop": round(min(change.deltas), 2), "largest_rise": round(max(change.deltas), 2)}
        return {"matches": self.matches, "unmatched_replays": self.unmatched_replays,
                "players_updated": self.players_updated, "players_unmatched": self.players_unmatched,
                "fields": {name: describe(change) for name, change in self.fields.items()}}


def record_differences(report: ReparseReport, current: Optional[PlayerMatchMetrics], new: PlayerMetrics) -> None:
    for name in DIFFED_FIELDS:
        change = report.fields.setdefault(name, FieldChange())
        before = getattr(current, name, None) if current is not None else None
        after = getattr(new, name, None)
        if before is None or after is None:
            continue
        if abs(float(after) - float(before)) > 1e-6:
            change.changed += 1
            change.deltas.append(float(after) - float(before))


def apply_reparsed_rows(db: Session, rows: Iterable[dict], dry_run: bool) -> ReparseReport:
    """Diff (dry run) or save re-parsed metrics exactly as an upload saves them."""
    report = ReparseReport()
    touched_players = set()
    for row in rows:
        match = db.query(Match).filter(Match.replay_hash == row["replay_hash"]).first()
        if match is None:
            report.unmatched_replays += 1
            continue
        report.matches += 1
        participants = participants_by_replay_name(db, match, row)
        for player in row["players"]:
            mp = participants.get(player["player_name"])
            if mp is None:
                report.players_unmatched += 1
                continue
            new = player_metrics_from(player)
            current = db.query(PlayerMatchMetrics).filter(PlayerMatchMetrics.match_player_id == mp.id).first()
            record_differences(report, current, new)
            report.players_updated += 1
            if not dry_run:
                ImpactService.save_match_metrics(db, mp.id, new)
                touched_players.add(mp.player_id)
        if not dry_run:
            db.query(KillEvent).filter(KillEvent.match_id == match.id).delete()
            ImpactService.save_kill_events(db, int(match.id), row.get("kill_events", []))
    if dry_run:
        db.rollback()
        return report
    for player_id in touched_players:
        ImpactService.update_player_averages(db, player_id)
    mark_stale(db, "Per-match stats were re-parsed with the updated parser")
    db.commit()
    return report
