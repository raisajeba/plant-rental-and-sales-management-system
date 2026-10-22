from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RentalStatusEnum(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    CONFIRMED = "Confirmed"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    REJECTED = "Rejected"
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
    order_identifier: str
    user_id: int
    plant_id: int
    quantity: int
    rental_start_date: date
    rental_end_date: date
    rental_duration_days: int
    rental_price_per_day: float
    total_amount: float
    status: RentalStatusEnum
    payment_status: str = "PENDING"
    created_at: datetime
    updated_at: datetime
    rejection_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RentalStatusUpdate(BaseModel):
    status: RentalStatusEnum
    rejection_reason: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_rejection_reason(self):
        if self.status == RentalStatusEnum.REJECTED:
            if self.rejection_reason is None or not self.rejection_reason.strip():
                raise ValueError("rejection_reason is required when rejecting a request")
            self.rejection_reason = self.rejection_reason.strip()
        elif self.rejection_reason is not None:
            raise ValueError("rejection_reason is only valid when rejecting a request")
        return self


class RentalOwnerOrderOut(BaseModel):
    id: int
    order_identifier: str
    customer_name: str
    plant_id: int
    plant_name: str
    quantity: int
    rental_start_date: date
    rental_end_date: date
    rental_duration_days: int
    rental_price_per_day: float
    total_amount: float
    status: RentalStatusEnum
    payment_status: str = "PENDING"
    created_at: datetime
    rejection_reason: str | None = None


class RentalHistoryItemOut(BaseModel):
    id: int
    order_identifier: str
    plant_id: int
    plant_name: str
    quantity: int
    rental_start_date: date
    rental_end_date: date
    rental_duration_days: int
    rental_price_per_day: float
    total_amount: float
    status: RentalStatusEnum
    payment_status: str = "PENDING"
    created_at: datetime
    rejection_reason: str | None = None


class RentalHistoryOut(BaseModel):
    current_orders: list[RentalHistoryItemOut]
    previous_orders: list[RentalHistoryItemOut]