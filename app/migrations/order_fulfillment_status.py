"""Normalize payment states and allow shipment statuses on purchase orders."""
from sqlalchemy import inspect, text

from app.database import engine


def migrate() -> None:
    if engine.dialect.name != "mysql":
        raise RuntimeError("This migration currently supports MySQL only")

    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        if not {"orders", "plant_rental_orders"}.issubset(tables):
            raise RuntimeError("Purchase and rental order tables must exist")

        constraints = inspector.get_check_constraints("orders")
        order_status_check = next(
            (
                constraint
                for constraint in constraints
                if constraint.get("name") == "ck_orders_status"
            ),
            None,
        )
        if order_status_check and not all(
            status in (order_status_check.get("sqltext") or "")
            for status in ("Shipped", "Delivered")
        ):
            connection.execute(text("ALTER TABLE orders DROP CHECK ck_orders_status"))
            connection.execute(
                text(
                    "ALTER TABLE orders ADD CONSTRAINT ck_orders_status "
                    "CHECK (status IN "
                    "('Pending', 'Confirmed', 'Processing', 'Shipped', "
                    "'Delivered', 'Completed', 'Cancelled'))"
                )
            )

        for table_name in ("orders", "plant_rental_orders"):
            columns = {
                column["name"]: column
                for column in inspect(connection).get_columns(table_name)
            }
            if "payment_status" not in columns:
                raise RuntimeError(
                    f"Run payment_tracking migration before updating {table_name}"
                )
            connection.execute(
                text(
                    f"UPDATE {table_name} "
                    "SET payment_status = UPPER(payment_status)"
                )
            )
            if columns["payment_status"].get("default") != "'PENDING'":
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ALTER COLUMN payment_status SET DEFAULT 'PENDING'"
                    )
                )


if __name__ == "__main__":
    migrate()
