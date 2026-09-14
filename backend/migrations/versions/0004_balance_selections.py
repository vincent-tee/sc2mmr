"""Persist final, pre-game selections without modifying historical ratings."""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    op.create_table(
        "balance_selections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("balance_prediction_id", sa.Integer,
                  sa.ForeignKey("balance_predictions.id"), nullable=False, unique=True),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("team1_ids_key", sa.String, nullable=False),
        sa.Column("team2_ids_key", sa.String, nullable=False),
        sa.Column("map_name", sa.String, nullable=True),
        sa.Column("predicted_team1_win_prob", sa.Float, nullable=False),
        sa.Column("match_id", sa.Integer, sa.ForeignKey("matches.id", ondelete="SET NULL"), unique=True),
        sa.Column("team1_won", sa.Integer, nullable=True),
    )
    # SQLite supports ADD COLUMN REFERENCES; avoid table recreation of history.
    if op.get_bind().dialect.name == "sqlite":
        op.execute("ALTER TABLE pregame_judgments ADD COLUMN selection_id INTEGER REFERENCES balance_selections(id)")
    else:
        op.add_column("pregame_judgments", sa.Column("selection_id", sa.Integer,
                      sa.ForeignKey("balance_selections.id"), nullable=True))
    op.create_index("uq_judgment_selection", "pregame_judgments", ["selection_id"], unique=True)


def downgrade():
    op.drop_index("uq_judgment_selection", "pregame_judgments")
    op.drop_column("pregame_judgments", "selection_id")
    op.drop_table("balance_selections")
