import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE matches SET game_fingerprint = NULL WHERE game_fingerprint = ''"))
    duplicates = connection.execute(sa.text(
        "SELECT game_fingerprint, GROUP_CONCAT(id) AS ids FROM matches "
        "WHERE game_fingerprint IS NOT NULL GROUP BY game_fingerprint HAVING COUNT(*) > 1"
    )).all()
    if duplicates:
        ids = "; ".join(row.ids for row in duplicates)
        raise RuntimeError(f"Duplicate games require review before migration; match IDs: {ids}")
    op.create_index("uq_matches_game_fingerprint", "matches", ["game_fingerprint"], unique=True)


def downgrade():
    op.drop_index("uq_matches_game_fingerprint", table_name="matches")
