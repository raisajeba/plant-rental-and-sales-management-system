
"""Pydantic schemas: request validation and safe (no password) responses."""
import re
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.constants import UserStatus


class RoleOut(BaseModel):
    id: int
    role_name: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class PageOut(BaseModel):
    id: int
    page_name: str
    page_url: str
    description: str | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Registration payload. Admin accounts can NOT be self-registered."""

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Literal["User", "Nursery"] = "User"

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        return v


class UserUpdate(BaseModel):
    """Profile update. Only fields that are sent get changed."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        return v.strip() if v else v

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str | None) -> str | None:
        return v.lower() if v else v

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.name is None and self.email is None:
            raise ValueError("Provide at least one field to update")
        return self


class AdminUserUpdate(BaseModel):
    role_id: int | None = None
    status: UserStatus | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.role_id is None and self.status is None:
            raise ValueError("Provide role_id and/or status")
        return self


class UserOut(BaseModel):
    """Safe user representation: never includes password or hash."""

    id: int
    name: str
    email: EmailStr
    status: str
    role: RoleOut

    # Profile picture URL/path
    profile_image: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

