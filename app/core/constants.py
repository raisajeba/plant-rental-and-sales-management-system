"""Shared constants so role / status / menu strings are never typed by hand."""
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


class MaintenanceTask(str, Enum):
    WATERING = "watering"
    FERTILIZING = "fertilizing"
    PRUNING = "pruning"
    REPOTTING = "repotting"
    PEST_CONTROL = "pest_control"
    OTHER = "other"


class MaintenanceStatus(str, Enum):  # a scheduled care task
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class RequestStatus(str, Enum):  # a user's maintenance request
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class AvailabilityStatus(str, Enum):
    FOR_SALE = "available_for_sale"
    FOR_RENT = "available_for_rent"
    FOR_BOTH = "available_for_both"
    UNAVAILABLE = "unavailable"

# The user dashboard menu: the ONLY pages in the system, in display order.
# (page_name, page_url, description)
# The page_url values must match MENU_ROUTES in the frontend js/layout.js.
MENU_PAGES: list[tuple[str, str, str]] = [
    ("Plants", "/plants", "Plant list (coming soon)"),
    ("Rent", "/rent-plants", "Rent plants (coming soon)"),
    ("Buy", "/buy-plants", "Buy plants (coming soon)"),
    ("Maintenance", "/maintenance", "Care schedule and maintenance requests"),
    ("Contact Us", "/contact", "Send us a message"),
    ("About Us", "/about", "About Green Forest"),
]