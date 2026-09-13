from pathlib import Path
import logging

from alembic import command
from alembic.config import Config


def upgrade_schema(engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
    with engine.connect() as connection:
        if connection.dialect.name != "sqlite":
            raise RuntimeError("The application migrations currently support SQLite only")
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            existing_violations = set(connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall())
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            new_violations = set(connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()) - existing_violations
            if new_violations:
                raise RuntimeError(f"Migration introduced foreign key violations: {list(new_violations)[:10]}")
            connection.commit()
            if existing_violations:
                logging.getLogger(__name__).warning(
                    "Database has %s existing foreign key violations requiring review",
                    len(existing_violations),
                )
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


if __name__ == "__main__":
    from .database import engine

    upgrade_schema(engine)
