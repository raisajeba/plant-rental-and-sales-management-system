from pydantic import BaseModel, ConfigDict, Field
from typing import List
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
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
    payment_status: str = "PENDING"
    created_at: datetime
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True


class CustomerOrderHistoryItemOut(BaseModel):
    plant_id: int
    plant_name: str
    quantity: int
    unit_price: float
    total_price: float
    rental_months: int | None = None
    rental_duration_days: int | None = None


class CustomerOrderHistoryOut(BaseModel):
    id: int
    order_type: str
    total_amount: float
    created_at: datetime
    status: str
    payment_status: str
    items: list[CustomerOrderHistoryItemOut]


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
    payment_status: str = "PENDING"
    order_date: datetime
    items: List[OwnerOrderItemOut]

# --- Jira Feature: Order Status Update Request Schema ---
class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(
        ..., 
        description="Must be one of: Pending, Confirmed, Processing, Shipped, Delivered, Completed, Cancelled"
    )
