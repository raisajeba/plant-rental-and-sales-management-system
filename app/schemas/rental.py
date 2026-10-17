from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import date, datetime
from typing import Optional
from enum import Enum

class RentalStatusEnum(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class PlantRentalOrderCreate(BaseModel):
    plant_id: int = Field(..., gt=0, description="Valid Plant ID required")
    quantity: int = Field(..., gt=0, description="Quantity must be positive")
    rental_start_date: date
    rental_end_date: date
    rental_price_per_day: float = Field(..., gt=0, description="Price must be positive")

    @model_validator(mode="after")
    def validate_rental_dates(self):
        if self.rental_start_date and self.rental_end_date:
            if self.rental_end_date < self.rental_start_date:
                raise ValueError("rental_end_date cannot be earlier than rental_start_date")
        return self

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
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)