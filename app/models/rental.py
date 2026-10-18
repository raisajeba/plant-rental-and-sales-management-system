import enum
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from app.database import Base


class RentalStatus(str, enum.Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class PlantRentalOrder(Base):
    __tablename__ = "plant_rental_orders"

    rental_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plant_id = Column(
        Integer, ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    quantity = Column(Integer, nullable=False)
    rental_start_date = Column(Date, nullable=False)
    rental_end_date = Column(Date, nullable=False)
    rental_duration_days = Column(Integer, nullable=False)
    rental_price_per_day = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)

    status = Column(
        Enum(
            RentalStatus,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=RentalStatus.PENDING,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        onupdate=func.now(),
        server_default=func.now(),
    )

    user = relationship("User", back_populates="rental_orders")
    plant = relationship("Plant", back_populates="rental_orders")

    __table_args__ = (
        CheckConstraint(
            "quantity > 0", name="check_plant_rental_quantity_positive"
        ),
        CheckConstraint("rental_duration_days > 0", name="check_duration_positive"),
        CheckConstraint("rental_price_per_day > 0", name="check_price_positive"),
        CheckConstraint(
            "total_amount > 0", name="check_plant_rental_total_amount_positive"
        ),
        CheckConstraint(
            "status IN ('Pending', 'Confirmed', 'Active', 'Completed', 'Cancelled')",
            name="check_rental_status",
        ),
        CheckConstraint(
            "rental_end_date >= rental_start_date", name="check_rental_dates"
        ),
    )

    @validates("quantity", "rental_duration_days")
    def validate_quantity(self, key, value):
        if value <= 0:
            raise ValueError(f"{key} must be greater than 0.")
        return value