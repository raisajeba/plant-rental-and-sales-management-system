import enum
from sqlalchemy import Column, Integer, Numeric, Date, ForeignKey, Enum, DateTime, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from app.database import Base  # app.database থেকে Base ইম্পোর্ট করা হয়েছে

class RentalStatus(str, enum.Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class PlantRentalOrder(Base):
    __tablename__ = "plant_rental_orders"

    rental_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)

    quantity = Column(Integer, nullable=False)
    rental_start_date = Column(Date, nullable=False)
    rental_end_date = Column(Date, nullable=False)
    rental_duration_days = Column(Integer, nullable=False)
    rental_price_per_day = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)

    status = Column(Enum(RentalStatus), default=RentalStatus.PENDING, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Foreign Key Relationships
    user = relationship("User", back_populates="rental_orders")
    plant = relationship("Plant", back_populates="rental_orders")

    # DB Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('rental_price_per_day > 0', name='check_price_positive'),
        CheckConstraint('rental_end_date >= rental_start_date', name='check_rental_dates'),
    )

    @validates('quantity')
    def validate_quantity(self, key, value):
        if value <= 0:
            raise ValueError("Quantity must be greater than 0.")
        return value