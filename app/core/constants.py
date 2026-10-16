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

# The customer and nursery menus, in display order.
# (page_name, page_url, description)
# The page_url values must match the role-specific routes in frontend/js/layout.js.
MENU_PAGES: list[tuple[str, str, str]] = [
    ("Dashboard", "/dashboard", "User dashboard"),
    ("Buy", "/buy", "Browse plants available to buy"),
    ("Rent", "/rent", "Browse plants available to rent"),
    ("Purchase History", "/customer-history", "View purchase and rental history"),
    ("Maintenance", "/maintenance", "Care schedule and maintenance requests"),
    ("Profile", "/profile", "Manage your account details"),
]

NURSERY_MENU_PAGES: list[tuple[str, str, str]] = [
    ("Nursery Dashboard", "/nursery-dashboard", "Nursery management overview"),
    ("My Plants", "/my-plants", "Manage your nursery plant listings"),
    ("Add Plant", "/add-plant", "Add a plant to your nursery"),
    ("Sell Orders", "/sell-orders", "Manage plant sales"),
    ("Rent Orders", "/rent-orders", "Manage plant rentals"),
    ("Nursery Maintenance", "/nursery-maintenance", "Manage maintenance requests"),
    ("Nursery Profile", "/nursery-profile", "Manage your nursery profile"),
]

ALL_MENU_PAGES = MENU_PAGES + NURSERY_MENU_PAGES