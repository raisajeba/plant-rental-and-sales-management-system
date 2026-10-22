from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import MaintenanceTask


class CareTipOut(BaseModel):
    task_type: str
    how_to: str


# ---------- Schedules ----------
class MaintenanceScheduleCreate(BaseModel):
    plant_name: str = Field(min_length=2, max_length=100)
    task_type: MaintenanceTask
    # Optional: if empty, the default care tip for the task type is used
    instructions: str | None = Field(default=None, max_length=1000)
    due_date: date
    frequency_days: int | None = Field(default=None, ge=1, le=365)

    @field_validator("plant_name")
    @classmethod
    def clean_plant_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("instructions")
    @classmethod
    def clean_instructions(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None

    @field_validator("due_date")
    @classmethod
    def not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("due_date cannot be in the past")
        return v

    @model_validator(mode="after")
    def other_needs_instructions(self):
        if self.task_type == MaintenanceTask.OTHER and not self.instructions:
            raise ValueError("instructions are required when task_type is 'other'")
        return self


class MaintenanceScheduleOut(BaseModel):
    id: int
    plant_name: str
    task_type: str
    instructions: str
    due_date: date
    frequency_days: int | None = None
    status: str
    completed_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Requests ----------
class MaintenanceRequestCreate(BaseModel):
    plant_name: str | None = Field(default=None, max_length=100)
    nursery_id: int | None = Field(default=None, gt=0)
    nursery_name: str | None = Field(default=None, min_length=2, max_length=150)
    request_type: MaintenanceTask
    description: str = Field(min_length=10, max_length=1000)
    preferred_date: date | None = None

    @field_validator("plant_name")
    @classmethod
    def clean_plant_name(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None

    @field_validator("nursery_name")
    @classmethod
    def clean_nursery_name(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None

    @field_validator("preferred_date")
    @classmethod
    def not_in_past(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("preferred_date cannot be in the past")
        return v


class MaintenanceRequestOut(BaseModel):
    id: int
    user_id: int
    nursery_id: int | None = None
    plant_name: str | None = None
    request_type: str
    description: str
    preferred_date: date | None = None
    status: str
    response_note: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MaintenancePlantCustomerOut(BaseModel):
    plant_id: int
    plant_name: str
    customer_id: int
    customer_name: str


class NurseryMaintenanceCreate(BaseModel):
    plant_id: int = Field(gt=0)
    customer_id: int = Field(gt=0)
    request_type: MaintenanceTask
    description: str = Field(min_length=10, max_length=1000)
    preferred_date: date | None = None

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("description must be at least 10 characters")
        return value

    @field_validator("preferred_date")
    @classmethod
    def not_in_past(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("preferred_date cannot be in the past")
        return value


class NurseryMaintenanceUpdate(BaseModel):
    status: Literal["pending", "scheduled", "in_progress", "completed"] | None = None
    preferred_date: date | None = None
    response_note: str | None = Field(default=None, max_length=500)

    @field_validator("preferred_date")
    @classmethod
    def not_in_past(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("preferred_date cannot be in the past")
        return value

    @field_validator("response_note")
    @classmethod
    def clean_response_note(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None

    @model_validator(mode="after")
    def require_a_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide a status, preferred_date, or response_note")
        return self


class NurseryMaintenanceOut(BaseModel):
    id: int
    plant_id: int | None = None
    plant_name: str | None = None
    customer_id: int
    customer_name: str
    request_type: str
    description: str
    preferred_date: date | None = None
    status: Literal["pending", "scheduled", "in_progress", "completed", "cancelled"]
    response_note: str | None = None
    created_at: datetime
    updated_at: datetime