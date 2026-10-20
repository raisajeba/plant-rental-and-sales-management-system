"""Admin authentication and admin-only management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import RoleName
from app.core.security import DUMMY_HASH, create_access_token, verify_password
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import Page, Role, RolePage, User
from app.schemas.auth import LoginRequest, MessageResponse, TokenResponse
from app.schemas.user import AdminUserUpdate, PageOut, RoleOut, UserOut

auth_router = APIRouter(prefix="/admin", tags=["Admin Authentication"])


@auth_router.post("/login", response_model=TokenResponse)
def admin_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate an active admin account using its existing user and role rows."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        verify_password(payload.password, DUMMY_HASH)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, user.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin_role_id = db.scalar(
        select(Role.id).where(Role.role_name == RoleName.ADMIN.value)
    )
    if admin_role_id is None or user.role_id != admin_role_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Administrator access is required",
        )
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")
    if user.role.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role is disabled")

    token, _ = create_access_token(user.id, user.role.role_name)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


# The dependency on the router protects EVERY endpoint below.
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_roles(RoleName.ADMIN))],
)


@router.get("/users", response_model=list[UserOut])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return db.scalars(select(User).order_by(User.id).offset(skip).limit(limit)).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleName.ADMIN)),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot modify your own role or status")

    if payload.role_id is not None:
        if db.get(Role, payload.role_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
        user.role_id = payload.role_id
    if payload.status is not None:
        user.status = payload.status.value

    db.commit()
    db.refresh(user)
    return user


@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db)):
    return db.scalars(select(Role).order_by(Role.id)).all()


@router.get("/pages", response_model=list[PageOut])
def list_pages(db: Session = Depends(get_db)):
    return db.scalars(select(Page).order_by(Page.id)).all()


@router.post("/roles/{role_id}/pages/{page_id}", response_model=MessageResponse)
def grant_page_to_role(role_id: int, page_id: int, db: Session = Depends(get_db)):
    if db.get(Role, role_id) is None or db.get(Page, page_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role or page not found")
    if db.get(RolePage, (role_id, page_id)) is None:  # idempotent
        db.add(RolePage(role_id=role_id, page_id=page_id))
        db.commit()
    return MessageResponse(message="Page access granted")


@router.delete("/roles/{role_id}/pages/{page_id}", response_model=MessageResponse)
def revoke_page_from_role(role_id: int, page_id: int, db: Session = Depends(get_db)):
    link = db.get(RolePage, (role_id, page_id))
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mapping not found")
    db.delete(link)
    db.commit()
    return MessageResponse(message="Page access revoked")