"""Idempotent startup seed: roles, pages, role-page mapping, optional first admin."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import RoleName
from app.core.security import hash_password
from app.models import Page, Role, RolePage, User

logger = logging.getLogger(__name__)

PAGES = [
    # (page_name, page_url, description)
    ("Dashboard", "/dashboard", "Main dashboard"),
    ("Buy Plants", "/buy-plants", "Browse and buy plants"),
    ("Rent Plants", "/rent-plants", "Browse and rent plants"),
    ("My Orders", "/my-orders", "Purchase order history"),
    ("My Rentals", "/my-rentals", "Rental history"),
    ("Maintenance", "/maintenance", "Plant maintenance records"),
    ("My Profile", "/profile", "View and edit profile"),
    ("Nursery Management", "/nursery/manage", "Manage nursery plants and stock"),
    ("User Management", "/admin/users", "Manage users and roles"),
]

_COMMON = ["/dashboard", "/buy-plants", "/rent-plants", "/my-orders",
           "/my-rentals", "/maintenance", "/profile"]

ROLE_PAGES = {
    RoleName.USER.value: _COMMON,
    RoleName.NURSERY.value: _COMMON + ["/nursery/manage"],
    RoleName.ADMIN.value: [p[1] for p in PAGES],  # everything
}


def seed_initial_data(db: Session) -> None:
    # Roles
    roles: dict[str, Role] = {}
    for rn in RoleName:
        role = db.scalar(select(Role).where(Role.role_name == rn.value))
        if role is None:
            role = Role(role_name=rn.value)
            db.add(role)
        roles[rn.value] = role

    # Pages
    pages: dict[str, Page] = {}
    for name, url, desc in PAGES:
        page = db.scalar(select(Page).where(Page.page_url == url))
        if page is None:
            page = Page(page_name=name, page_url=url, description=desc)
            db.add(page)
        pages[url] = page
    db.flush()  # assign ids

    # Role <-> Page mapping
    for role_name, urls in ROLE_PAGES.items():
        for url in urls:
            if db.get(RolePage, (roles[role_name].id, pages[url].id)) is None:
                db.add(RolePage(role_id=roles[role_name].id, page_id=pages[url].id))

    # Optional first admin
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        email = settings.ADMIN_EMAIL.lower()
        if db.scalar(select(User.id).where(User.email == email)) is None:
            db.add(User(
                name=settings.ADMIN_NAME or "Administrator",
                email=email,
                password=hash_password(settings.ADMIN_PASSWORD),
                role_id=roles[RoleName.ADMIN.value].id,
            ))
            logger.info("Default admin account created")

    db.commit()