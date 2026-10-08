from datetime import date, datetime

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
    request_type: MaintenanceTask
    description: str = Field(min_length=10, max_length=1000)
    preferred_date: date | None = None

    @field_validator("plant_name")
    @classmethod
    def clean_plant_name(cls, v: str | None) -> str | None:
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
    plant_name: str | None = None
    request_type: str
    description: str
    preferred_date: date | None = None
    status: str
    response_note: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)