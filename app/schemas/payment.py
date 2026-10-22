from typing import Literal

from pydantic import BaseModel, Field


class PaymentItem(BaseModel):
    plant_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class PaymentInitiateRequest(BaseModel):
    order_type: Literal["purchase", "rental"]
    order_id: int = Field(gt=0)
    cart_items: list[PaymentItem] | None = Field(default=None, min_length=1)
    phone: str = Field(min_length=5, max_length=20, pattern=r"^[0-9+() -]+$")
    address: str = Field(min_length=3, max_length=200)
    city: str = Field(min_length=2, max_length=50)
    postcode: str = Field(min_length=3, max_length=20)


class PaymentInitiateResponse(BaseModel):
    gateway_url: str = Field(serialization_alias="GatewayPageURL")
    transaction_id: str
