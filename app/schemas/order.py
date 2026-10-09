from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "Pending"
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