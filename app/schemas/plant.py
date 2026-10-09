from pydantic import BaseModel, Field
from enum import Enum

class AvailabilityStatus(str, Enum):
    AVAILABLE = "Available"
    OUT_OF_STOCK = "Out of Stock"

class PlantBase(BaseModel):
    name: str
    quantity: int = Field(..., ge=0, description="Quantity cannot be negative")

class PlantResponse(PlantBase):
    id: int
    availability_status: AvailabilityStatus

    class Config:
        orm_mode = True

class TransactionRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")