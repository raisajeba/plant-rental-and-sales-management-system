from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RentalStatusEnum(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class PlantRentalOrderCreate(BaseModel):
    plant_id: int = Field(..., gt=0, description="Valid Plant ID required")
    quantity: int = Field(..., gt=0, le=1_000_000, description="Quantity must be positive")
    rental_start_date: date
    rental_end_date: date

    @model_validator(mode="after")
    def validate_rental_dates(self):
        if self.rental_start_date < datetime.now(timezone.utc).date():
            raise ValueError("rental_start_date cannot be earlier than today")
        if self.rental_end_date < self.rental_start_date:
            raise ValueError("rental_end_date cannot be earlier than rental_start_date")
        return self

    model_config = ConfigDict(extra="forbid")


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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RentalStatusUpdate(BaseModel):
    status: RentalStatusEnum


class RentalOwnerOrderOut(BaseModel):
    id: int
    customer_name: str
    plant_name: str
    quantity: int
    rental_start_date: date
    rental_end_date: date
    rental_duration_days: int
    rental_price_per_day: float
    total_amount: float
    status: RentalStatusEnum
    created_at: datetime