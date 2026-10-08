import enum
from sqlalchemy import Column, Integer, String, Enum, CheckConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "Available"
    OUT_OF_STOCK = "Out of Stock"

class Plant(Base):
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    availability_status = Column(Enum(AvailabilityStatus), nullable=False, default=AvailabilityStatus.OUT_OF_STOCK)

    __table_args__ = (
        CheckConstraint('quantity >= 0', name='check_quantity_non_negative'),
    )

    def update_availability_status(self):
        """Automatically sync availability status based on stock quantity."""
        if self.quantity > 0:
            self.availability_status = AvailabilityStatus.AVAILABLE
        else:
            self.availability_status = AvailabilityStatus.OUT_OF_STOCK