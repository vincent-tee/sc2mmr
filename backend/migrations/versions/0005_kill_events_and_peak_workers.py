"""Add player_match_metrics.peak_active_workers and a raw kill_events table."""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade():
    op.add_column(
        "player_match_metrics",
        sa.Column("peak_active_workers", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "kill_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("match_id", sa.Integer, sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("killer_player_id", sa.Integer, sa.ForeignKey("players.id"), nullable=True),
        sa.Column("victim_player_id", sa.Integer, sa.ForeignKey("players.id"), nullable=True),
        sa.Column("unit_type", sa.String, nullable=False),
        sa.Column("game_second", sa.Integer, nullable=False),
        sa.Column("x", sa.Integer, nullable=True),
        sa.Column("y", sa.Integer, nullable=True),
    )
    op.create_index("ix_kill_events_match_id", "kill_events", ["match_id"])


def downgrade():
    op.drop_index("ix_kill_events_match_id", "kill_events")
    op.drop_table("kill_events")
    op.drop_column("player_match_metrics", "peak_active_workers")
