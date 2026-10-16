"""Idempotent startup seed: roles, menu pages, and which roles can see them."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.constants import ALL_MENU_PAGES, MENU_PAGES, NURSERY_MENU_PAGES, RoleName
from app.models import Page, Role, RolePage


def seed_initial_data(db: Session) -> None:
    menu_urls = [url for _, url, _ in ALL_MENU_PAGES]

    # 1. Remove pages that are no longer part of the configured menu.
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
    pages: dict[str, Page] = {}
    for name, url, description in ALL_MENU_PAGES:
        page = db.scalar(select(Page).where(Page.page_url == url))
        if page is None:
            page = Page(page_name=name, page_url=url, description=description)
            db.add(page)
        else:
            page.page_name = name
            page.description = description
        pages[url] = page
    db.flush()  # assign ids

    # Rebuild assignments for managed menu pages so stale cross-role grants go away.
    menu_page_ids = [page.id for page in pages.values()]
    db.execute(delete(RolePage).where(RolePage.page_id.in_(menu_page_ids)))

    roles_by_name = {role.role_name: role for role in roles}
    role_menus = {
        RoleName.USER.value: MENU_PAGES,
        RoleName.NURSERY.value: NURSERY_MENU_PAGES,
    }
    for role_name, menu in role_menus.items():
        role = roles_by_name[role_name]
        for _, url, _ in menu:
            db.add(RolePage(role_id=role.id, page_id=pages[url].id))

    db.commit()