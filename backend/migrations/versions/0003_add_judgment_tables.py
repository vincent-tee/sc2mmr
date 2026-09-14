import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    op.create_table(
        "pregame_judgments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column(
            "balance_prediction_id",
            sa.Integer,
            sa.ForeignKey("balance_predictions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "match_id",
            sa.Integer,
            sa.ForeignKey("matches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("team1_player_ids_key", sa.String, nullable=False),
        sa.Column("team2_player_ids_key", sa.String, nullable=False),
        sa.Column("map_name", sa.String, nullable=True),
        sa.Column("team1_context_json", sa.JSON, nullable=True),
        sa.Column("team2_context_json", sa.JSON, nullable=True),
        sa.Column("model_version", sa.String, nullable=True),
        sa.Column("model_predicted_team1_win_prob", sa.Float, nullable=True),
        sa.Column("human_estimate", sa.String(13), nullable=False),
        sa.Column("human_win_prob", sa.Float, nullable=True),
        sa.Column("confidence", sa.String(6), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.Column("reason_note", sa.String, nullable=True),
        sa.Column("author", sa.String, nullable=False),
        sa.Column("is_locked", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_pregame_judgments_id", "pregame_judgments", ["id"])
    op.create_index("ix_pregame_judgments_match_id", "pregame_judgments", ["match_id"])

    op.create_table(
        "postgame_feedback",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column(
            "judgment_id",
            sa.Integer,
            sa.ForeignKey("pregame_judgments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "match_id",
            sa.Integer,
            sa.ForeignKey("matches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("feedback", sa.String(16), nullable=False),
        sa.Column("note", sa.String, nullable=True),
        sa.Column("author", sa.String, nullable=False),
    )
    op.create_index("ix_postgame_feedback_id", "postgame_feedback", ["id"])
    op.create_index("ix_postgame_feedback_match_id", "postgame_feedback", ["match_id"])


def downgrade():
    op.drop_table("postgame_feedback")
    op.drop_table("pregame_judgments")
