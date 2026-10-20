from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import MaintenanceStatus, RequestStatus
from app.models.order import OrderStatus as CheckoutOrderStatus
from app.models.purchase_order import OrderStatus as PurchaseOrderStatus
from app.models.rental import RentalStatus


class PurchaseOrderAdminOut(BaseModel):
    order_id: int
    user_id: int
    plant_id: int
    quantity: int
    total_amount: float
    order_status: PurchaseOrderStatus
    order_date: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderStatusUpdate(BaseModel):
    status: PurchaseOrderStatus


class CheckoutOrderStatusUpdate(BaseModel):
    status: CheckoutOrderStatus


class RentalOrderStatusUpdate(BaseModel):
    status: RentalStatus


class LegacyRentalOrderAdminOut(BaseModel):
    id: int
    user_id: int
    plant_id: int
    quantity: int
    rental_months: int
    total_amount: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaintenanceScheduleAdminUpdate(BaseModel):
    status: MaintenanceStatus


class MaintenanceRequestAdminUpdate(BaseModel):
    status: RequestStatus | None = None
    response_note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_a_change(self):
        if self.status is None and "response_note" not in self.model_fields_set:
            raise ValueError("Provide a status or response_note")
        return self