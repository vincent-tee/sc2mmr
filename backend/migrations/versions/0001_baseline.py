from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    snapshot = sa.create_engine("sqlite://")
    try:
        with snapshot.begin() as connection:
            schema = Path(__file__).with_name("0001_schema.sql").read_text()
            for statement in schema.split(";"):
                if statement.strip():
                    connection.exec_driver_sql(statement)
        expected = sa.MetaData()
        expected.reflect(bind=snapshot)
        connection = op.get_bind()
        existing_tables = set(sa.inspect(connection).get_table_names())
        for table in expected.sorted_tables:
            if table.name not in existing_tables:
                table.create(connection)
                continue
            existing_columns = {c["name"] for c in sa.inspect(connection).get_columns(table.name)}
            missing = [c for c in table.columns if c.name not in existing_columns]
            if missing:
                with op.batch_alter_table(table.name, recreate="always") as batch:
                    for column in missing:
                        batch.add_column(sa.Column(
                            column.name, column.type, nullable=column.nullable,
                            server_default=column.server_default,
                        ))
            for index in table.indexes:
                index.create(connection, checkfirst=True)
    finally:
        snapshot.dispose()


def downgrade():
    raise RuntimeError("The baseline cannot be downgraded; restore a database backup")
