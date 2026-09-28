import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade():
    op.create_table(
        "derived_data_state",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("stale_since", sa.DateTime, nullable=True),
        sa.Column("stale_reason", sa.String, nullable=True),
        sa.Column("rebuild_due_at", sa.DateTime, nullable=True),
        sa.Column("rebuilding_started_at", sa.DateTime, nullable=True),
        sa.Column("last_rebuilt_at", sa.DateTime, nullable=True),
        sa.Column("last_rebuild_seconds", sa.Float, nullable=True),
        sa.Column("last_error", sa.String, nullable=True),
    )
    op.execute("INSERT INTO derived_data_state (id) VALUES (1)")


def downgrade():
    op.drop_table("derived_data_state")
