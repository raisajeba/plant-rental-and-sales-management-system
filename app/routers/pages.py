"""Sidebar navigation: the menu pages the logged-in user's role may access."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import MENU_PAGES
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Page, RolePage, User
from app.schemas.user import PageOut

router = APIRouter(prefix="/pages", tags=["Pages"])

# page_url -> position, so the menu always comes back in the same order
MENU_ORDER = {url: index for index, (_, url, _) in enumerate(MENU_PAGES)}


@router.get("/my-menu", response_model=list[PageOut])
def my_menu(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns: Plants, Rent, Buy, Maintenance, Contact Us, About Us (in that order)."""
    stmt = (
        select(Page)
        .join(RolePage, RolePage.page_id == Page.id)
        .where(RolePage.role_id == current_user.role_id, Page.status == "active")
    )
    pages = db.scalars(stmt).all()
    return sorted(pages, key=lambda p: MENU_ORDER.get(p.page_url, len(MENU_ORDER)))