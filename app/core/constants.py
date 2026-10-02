"""Shared constants so role/status strings are never typed by hand."""
from enum import Enum


class RoleName(str, Enum):
    USER = "User"
    NURSERY = "Nursery"
    ADMIN = "Admin"


class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"