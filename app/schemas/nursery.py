import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s\-]{6,19}$")

class NurseryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    address: str = Field(min_length=5, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=30)
    email: EmailStr | None = None

    @field_validator("name", "address", "city", "phone")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()

    @field_validator("description")
    @classmethod
    def blank_to_none(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        if not PHONE_PATTERN.match(v):
            raise ValueError("Enter a valid phone number, e.g. +8801712345678")
        return v

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str | None) -> str | None:
        return v.lower() if v else v

class NurseryOut(BaseModel):
    id: int
    owner_id: int
    name: str
    image_url: str | None = None
    description: str | None = None
    address: str
    city: str
    phone: str
    email: EmailStr | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)