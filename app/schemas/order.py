from pydantic import BaseModel, ConfigDict, Field
from typing import List
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class OrderItemOut(BaseModel):
    id: int
    plant_id: int
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: OrderStatus
    created_at: datetime
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True


class RentalOrderCreate(BaseModel):
    plant_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=1_000_000)
    rental_months: int = Field(ge=1, le=120)


class OrderHistoryItemOut(BaseModel):
    id: int
    plant_id: int
    plant_name: str
    quantity: int
    unit_price: float
    total_price: float
    rental_months: int | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderHistoryOut(BaseModel):
    id: int
    order_type: str
    total_amount: float
    status: str
    created_at: datetime
    items: List[OrderHistoryItemOut]

class OwnerOrderItemOut(BaseModel):
    plant_id: int
    plant_name: str
    quantity: int
    unit_price: float
    total_price: float


class OwnerOrderOut(BaseModel):
    id: int
    customer_name: str
    total_price: float
    status: OrderStatus
    order_date: datetime
    items: List[OwnerOrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class RentalOrderOut(BaseModel):
    id: int
    user_id: int
    plant_id: int
    quantity: int
    rental_months: int
    total_amount: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)