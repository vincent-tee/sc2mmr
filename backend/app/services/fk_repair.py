"""Safe repair for the one known, investigated foreign-key violation category.

Every violation found in this project (local dev, 375 rows; production, 287
rows -- see backend/scripts/fk_violation_report.py and the campaign log) is
the same shape: player_match_metrics.match_player_id pointing at a deleted
match_players.id, left behind by historical bulk deletes (winner-fix
reprocessing, game-fingerprint dedup) that didn't cascade. player_match_metrics
is a leaf table -- nothing else references it -- so these rows are dead,
unrecoverable, and safe to delete.

This is intentionally narrow, not a generic "fix any FK violation" tool: it
only touches this one investigated category, and refuses (reports, does not
delete) if it finds a violation shape that hasn't been characterized, so a
future, different problem can't be silently swept up by this same endpoint.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import PlayerMatchMetrics

KNOWN_SAFE_CATEGORY = ("player_match_metrics", "match_players")


def repair_orphaned_metrics(db: Session) -> dict:
    violations = db.execute(text("PRAGMA foreign_key_check")).fetchall()
    categories = {(v[0], v[2]) for v in violations}
    unknown = categories - {KNOWN_SAFE_CATEGORY}
    if unknown:
        return dict(
            repaired=0,
            skipped_unknown_categories=sorted(str(c) for c in unknown),
            note="Refused to delete: found violation shape(s) not covered by this repair. No rows touched.",
        )

    orphaned = (
        db.query(PlayerMatchMetrics)
        .filter(~PlayerMatchMetrics.match_player_id.in_(text("SELECT id FROM match_players")))
        .all()
    )
    count = len(orphaned)
    for row in orphaned:
        db.delete(row)
    db.commit()

    remaining = db.execute(text("PRAGMA foreign_key_check")).fetchall()
    return dict(repaired=count, remaining_violations=len(remaining))
