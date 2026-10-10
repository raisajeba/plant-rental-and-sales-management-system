from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.core.constants import AvailabilityStatus

_SALE_STATUSES = {AvailabilityStatus.FOR_SALE, AvailabilityStatus.FOR_BOTH}
_RENT_STATUSES = {AvailabilityStatus.FOR_RENT, AvailabilityStatus.FOR_BOTH}


class PlantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    category: str = Field(min_length=2, max_length=50)
    size: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=1000)
    buy_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    rent_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    available_quantity: int = Field(default=0, ge=0, le=1_000_000)
    availability_status: AvailabilityStatus = AvailabilityStatus.UNAVAILABLE
    care_instructions: str | None = Field(default=None, max_length=1000)

    @field_validator("name", "category")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()

    @field_validator("size", "description", "care_instructions")
    @classmethod
    def blank_to_none(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None

    @model_validator(mode="after")
    def check_status_rules(self):
        status = self.availability_status
        if status in _SALE_STATUSES and self.buy_price is None:
            raise ValueError("buy_price is required when the plant is available for sale")
        if status in _RENT_STATUSES and self.rent_price is None:
            raise ValueError("rent_price is required when the plant is available for rent")
        if status != AvailabilityStatus.UNAVAILABLE and self.available_quantity < 1:
            raise ValueError("available_quantity must be at least 1 for an available plant")
        return self


class PlantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    category: str | None = Field(default=None, min_length=2, max_length=50)
    size: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=1000)
    buy_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    rent_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    available_quantity: int | None = Field(default=None, ge=0, le=1_000_000)
    availability_status: AvailabilityStatus | None = None
    care_instructions: str | None = Field(default=None, max_length=1000)

    @field_validator("name", "category")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return v.strip() if v else None

    @field_validator("size", "description", "care_instructions")
    @classmethod
    def blank_to_none(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None


class PlantOut(BaseModel):
    id: int
    nursery_id: int
    name: str
    image_url: str | None = None
    category: str
    size: str | None = None
    description: str | None = None
    buy_price: float | None = None
    rent_price: float | None = None
    available_quantity: int
    availability_status: str
    care_instructions: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlantSearchOut(PlantOut):
    nursery_name: str
