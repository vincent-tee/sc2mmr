import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import Match, MatchPlayer, Player
from app.services.metrics_backfill import BACKFILLED_FIELDS
from app.services.player_service import PlayerService
from app.services.unified_parser import UnifiedParser


def participant_ids_by_canonical_name(db, match_id):
    return dict(db.query(Player.name, Player.id)
                .join(MatchPlayer, MatchPlayer.player_id == Player.id)
                .filter(MatchPlayer.match_id == match_id).all())


def metrics_row(match, player_id, parsed_player):
    row = {"replay_hash": match.replay_hash, "player_id": player_id,
           "unit_composition": parsed_player.unit_composition}
    row.update({name: getattr(parsed_player, name) for name in BACKFILLED_FIELDS})
    return row


def main(shard_idx, num_shards, replay_dir, out_dir):
    logging.getLogger("app.services.unified_parser").setLevel(logging.ERROR)
    out_dir.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    matches = db.query(Match).filter(Match.replay_hash.isnot(None)).order_by(Match.id).all()
    shard = [m for i, m in enumerate(matches) if i % num_shards == shard_idx]
    parser = UnifiedParser()
    parsed = missing_file = failed = rows = unresolved = 0
    with open(out_dir / f"shard_{shard_idx}.jsonl", "w") as out:
        for match in shard:
            replay_path = replay_dir / f"{match.replay_hash}.SC2Replay"
            if not replay_path.exists():
                missing_file += 1
                continue
            try:
                result = parser.parse(str(replay_path))
            except Exception:
                failed += 1
                continue
            parsed += 1
            participants = participant_ids_by_canonical_name(db, match.id)
            for parsed_player in result.players:
                canonical = PlayerService.resolve_canonical_name(
                    db, parsed_player.name, match.game_mode, len(result.players))
                player_id = participants.get(canonical)
                if player_id is None:
                    unresolved += 1
                    continue
                out.write(json.dumps(metrics_row(match, player_id, parsed_player)) + "\n")
                rows += 1
    db.close()
    print(f"shard {shard_idx}/{num_shards}: parsed={parsed} missing_file={missing_file} "
          f"failed={failed} rows={rows} unresolved_players={unresolved}")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
