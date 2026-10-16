"""Admin-only management endpoints (RBAC example)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import ApprovalStatus, RoleName, UserStatus
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import Page, Role, RolePage, User
from app.schemas.auth import MessageResponse
from app.schemas.user import AdminUserUpdate, PageOut, RoleOut, UserOut

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


@router.get("/users/pending", response_model=list[UserOut])
def list_pending_users(db: Session = Depends(get_db)):
    return db.scalars(
        select(User)
        .where(User.approval_status == ApprovalStatus.PENDING.value)
        .order_by(User.created_at, User.id)
    ).all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def _set_account_approval(
    user_id: int,
    approval_status: ApprovalStatus,
    account_status: UserStatus,
    db: Session,
) -> User:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.approval_status != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only pending accounts can be approved or rejected",
        )

    user.approval_status = approval_status.value
    user.status = account_status.value
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/approve", response_model=UserOut)
def approve_user(user_id: int, db: Session = Depends(get_db)):
    return _set_account_approval(
        user_id,
        ApprovalStatus.APPROVED,
        UserStatus.ACTIVE,
        db,
    )


@router.post("/users/{user_id}/reject", response_model=UserOut)
def reject_user(user_id: int, db: Session = Depends(get_db)):
    return _set_account_approval(
        user_id,
        ApprovalStatus.REJECTED,
        UserStatus.INACTIVE,
        db,
    )


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
        if (
            payload.status == UserStatus.ACTIVE
            and user.approval_status != ApprovalStatus.APPROVED.value
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Account must be approved before it can be activated",
            )
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