"""Record where each match's winner came from, and the evidence behind suggested winners."""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade():
    op.add_column("matches", sa.Column("result_source", sa.String, nullable=True))
    op.add_column("matches", sa.Column("result_evidence", sa.JSON, nullable=True))
    op.add_column("matches", sa.Column("result_confirmed_by", sa.String, nullable=True))
    op.add_column("matches", sa.Column("result_confirmed_at", sa.DateTime, nullable=True))
    op.create_index("ix_matches_result_source", "matches", ["result_source"])


def downgrade():
    op.drop_index("ix_matches_result_source", "matches")
    op.drop_column("matches", "result_confirmed_at")
    op.drop_column("matches", "result_confirmed_by")
    op.drop_column("matches", "result_evidence")
    op.drop_column("matches", "result_source")
