"""Allow owner approval and rejection states for plant rental requests."""
from sqlalchemy import inspect, text

from app.database import engine

_RENTAL_STATUSES = (
    "Pending",
    "Approved",
    "Confirmed",
    "Active",
    "Completed",
    "Rejected",
    "Cancelled",
)


def migrate() -> None:
    if engine.dialect.name != "mysql":
        raise RuntimeError("This migration currently supports MySQL only")

    with engine.begin() as connection:
        inspector = inspect(connection)
        if "plant_rental_orders" not in inspector.get_table_names():
            raise RuntimeError("The plant_rental_orders table must exist")

        status_check = next(
            (
                constraint
                for constraint in inspector.get_check_constraints(
                    "plant_rental_orders"
                )
                if constraint.get("name") == "check_rental_status"
            ),
            None,
        )
        check_sql = "status IN (" + ", ".join(
            f"'{rental_status}'" for rental_status in _RENTAL_STATUSES
        ) + ")"

        if status_check and all(
            f"'{rental_status}'" in (status_check.get("sqltext") or "")
            for rental_status in _RENTAL_STATUSES
        ):
            return

        if status_check:
            connection.execute(
                text(
                    "ALTER TABLE plant_rental_orders "
                    "DROP CHECK check_rental_status, "
                    f"ADD CONSTRAINT check_rental_status CHECK ({check_sql})"
                )
            )
        else:
            connection.execute(
                text(
                    "ALTER TABLE plant_rental_orders "
                    f"ADD CONSTRAINT check_rental_status CHECK ({check_sql})"
                )
            )


if __name__ == "__main__":
    migrate()
