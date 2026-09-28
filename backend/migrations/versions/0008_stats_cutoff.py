"""Record when each player's stats stop counting: when they left, or the recording's end."""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade():
    op.add_column("player_match_metrics", sa.Column("stats_cutoff_second", sa.Integer, nullable=True))
    op.add_column("player_match_metrics", sa.Column("stats_cutoff_reason", sa.String, nullable=True))


def downgrade():
    op.drop_column("player_match_metrics", "stats_cutoff_reason")
    op.drop_column("player_match_metrics", "stats_cutoff_second")
