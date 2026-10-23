"""Add an optional nursery association to maintenance requests."""
from sqlalchemy import inspect, text

from app.database import engine


def migrate() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        required_tables = {"maintenance_requests", "nurseries"}
        missing_tables = required_tables - tables
        if missing_tables:
            raise RuntimeError(
                "Maintenance nursery migration requires existing tables: "
                + ", ".join(sorted(missing_tables))
            )

        columns = {
            column["name"]
            for column in inspector.get_columns("maintenance_requests")
        }
        if "nursery_id" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE maintenance_requests "
                    "ADD COLUMN nursery_id INTEGER "
                    "REFERENCES nurseries(id) ON DELETE SET NULL ON UPDATE CASCADE"
                )
            )

        indexes = {
            index["name"]
            for index in inspect(connection).get_indexes("maintenance_requests")
        }
        if "ix_maintenance_requests_nursery_id" not in indexes:
            connection.execute(
                text(
                    "CREATE INDEX ix_maintenance_requests_nursery_id "
                    "ON maintenance_requests (nursery_id)"
                )
            )


if __name__ == "__main__":
    migrate()
