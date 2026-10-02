"""Idempotent startup seed: roles, the six menu pages, and which roles can see them."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.constants import MENU_PAGES, RoleName
from app.models import Page, Role, RolePage


def seed_initial_data(db: Session) -> None:
    menu_urls = [url for _, url, _ in MENU_PAGES]

    # 1. The pages table contains ONLY the menu pages. Remove leftovers from earlier
    #    versions (/dashboard, /my-orders, /profile, /admin/users ...).
    stale_page_ids = select(Page.id).where(Page.page_url.not_in(menu_urls))
    db.execute(delete(RolePage).where(RolePage.page_id.in_(stale_page_ids)))
    db.execute(delete(Page).where(Page.page_url.not_in(menu_urls)))

    # 2. Roles
    roles: list[Role] = []
    for role_name in RoleName:
        role = db.scalar(select(Role).where(Role.role_name == role_name.value))
        if role is None:
            role = Role(role_name=role_name.value)
            db.add(role)
        roles.append(role)

    # 3. Menu pages (existing ones get their name / description refreshed)
    pages: list[Page] = []
    for name, url, description in MENU_PAGES:
        page = db.scalar(select(Page).where(Page.page_url == url))
        if page is None:
            page = Page(page_name=name, page_url=url, description=description)
            db.add(page)
        else:
            page.page_name = name
            page.description = description
        pages.append(page)
    db.flush()  # assign ids

    # 4. Every role sees the same six pages for now
    for role in roles:
        for page in pages:
            if db.get(RolePage, (role.id, page.id)) is None:
                db.add(RolePage(role_id=role.id, page_id=page.id))

    db.commit()