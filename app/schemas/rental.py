from pydantic import BaseModel, Field, root_validator
from datetime import date
from enum import Enum

class RentalStatusEnum(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

# Data Input Schema
class PlantRentalOrderCreate(BaseModel):
    user_id: int
    plant_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be positive")
    rental_start_date: date
    rental_end_date: date
    rental_price_per_day: float = Field(..., gt=0, description="Price must be positive")

    @root_validator(pre=False)
    def validate_dates(cls, values):
        start = values.get("rental_start_date")
        end = values.get("rental_end_date")
        if start and end and end < start:
            raise ValueError("rental_end_date cannot be earlier than rental_start_date")
        return values

# API Response Schema
class PlantRentalOrderResponse(BaseModel):
    rental_id: int
    user_id: int
    plant_id: int
    quantity: int
    rental_start_date: date
    rental_end_date: date
    rental_duration_days: int
    rental_price_per_day: float
    total_amount: float
    status: RentalStatusEnum

    class Config:
        from_attributes = True  # Pydantic v2-এর জন্য (Pydantic v1 হলে orm_mode = True লিখবেন)