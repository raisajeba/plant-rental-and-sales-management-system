"""Dashboard menu: the pages the logged-in user's role may access."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Page, RolePage, User
from app.schemas.user import PageOut

router = APIRouter(prefix="/pages", tags=["Pages"])


@router.get("/my-menu", response_model=list[PageOut])
def my_menu(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = (
        select(Page)
        .join(RolePage, RolePage.page_id == Page.id)
        .where(RolePage.role_id == current_user.role_id, Page.status == "active")
        .order_by(Page.id)
    )
    return db.scalars(stmt).all()