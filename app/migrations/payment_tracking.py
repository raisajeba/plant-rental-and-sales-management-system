"""Add payment state and transaction storage without replacing existing tables."""
from sqlalchemy import inspect, text

import app.models  # noqa: F401
from app.database import engine
from app.models import PaymentTransaction


def migrate() -> None:
    with engine.begin() as connection:
        existing_tables = set(inspect(connection).get_table_names())
        required_tables = {"orders", "plant_rental_orders", "users"}
        missing_tables = required_tables - existing_tables
        if missing_tables:
            raise RuntimeError(
                "Payment migration requires existing tables: "
                + ", ".join(sorted(missing_tables))
            )

        for table_name in ("orders", "plant_rental_orders"):
            existing_columns = {
                column["name"] for column in inspect(connection).get_columns(table_name)
            }
            if "payment_status" not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN payment_status VARCHAR(20) "
                        "NOT NULL DEFAULT 'PENDING'"
                    )
                )
            if "payment_transaction_id" not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN payment_transaction_id VARCHAR(64)"
                    )
                )

        PaymentTransaction.__table__.create(bind=connection, checkfirst=True)


if __name__ == "__main__":
    migrate()
