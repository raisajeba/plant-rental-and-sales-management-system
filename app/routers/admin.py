"""Admin authentication and admin-only management endpoints."""
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import RoleName, UserStatus
from app.core.security import DUMMY_HASH, create_access_token, verify_password
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import Nursery, Page, Plant, Role, RolePage, User
from app.schemas.auth import LoginRequest, MessageResponse, TokenResponse
from app.schemas.nursery import NurseryOut
from app.schemas.plant import PlantOut
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
    status: UserStatus | None = None,
    db: Session = Depends(get_db),
):
    query = select(User).order_by(User.id)
    if status is not None:
        query = query.where(User.status == status.value)
    query = query.offset(skip).limit(limit)
    return db.scalars(query).all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


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


@router.post("/users/{user_id}/approve", response_model=UserOut)
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleName.ADMIN)),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own account state")

    user.status = UserStatus.ACTIVE.value
    db.commit()
    db.refresh(user)
    return user


@router.get("/nurseries", response_model=list[NurseryOut])
def list_nurseries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, description="active or inactive"),
    db: Session = Depends(get_db),
):
    query = select(Nursery).order_by(Nursery.id)
    if status is not None:
        query = query.where(Nursery.status == status)
    query = query.offset(skip).limit(limit)
    return db.scalars(query).all()


@router.get("/nurseries/{nursery_id}", response_model=NurseryOut)
def get_nursery(nursery_id: int, db: Session = Depends(get_db)):
    nursery = db.get(Nursery, nursery_id)
    if nursery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    return nursery


@router.patch("/nurseries/{nursery_id}", response_model=NurseryOut)
def update_nursery(
    nursery_id: int,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    nursery = db.get(Nursery, nursery_id)
    if nursery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")

    allowed_fields = {"name", "description", "address", "city", "phone", "email", "image_url", "status"}
    invalid_fields = sorted(set(payload) - allowed_fields)
    if invalid_fields:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported fields for nursery update: {', '.join(invalid_fields)}",
        )

    if "status" in payload and payload["status"] not in {"active", "inactive"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nursery status must be active or inactive")

    for field, value in payload.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(nursery, field, value)

    db.commit()
    db.refresh(nursery)
    return nursery


@router.post("/nurseries/{nursery_id}/approve", response_model=NurseryOut)
def approve_nursery(
    nursery_id: int,
    db: Session = Depends(get_db),
):
    nursery = db.get(Nursery, nursery_id)
    if nursery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    nursery.status = "active"
    db.commit()
    db.refresh(nursery)
    return nursery


@router.get("/plants", response_model=list[PlantOut])
def list_plants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, description="Plant availability status"),
    nursery_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    query = select(Plant).order_by(Plant.id)
    if status is not None:
        query = query.where(Plant.availability_status == status)
    if nursery_id is not None:
        query = query.where(Plant.nursery_id == nursery_id)
    query = query.offset(skip).limit(limit)
    return db.scalars(query).all()


@router.get("/plants/{plant_id}", response_model=PlantOut)
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    return plant


@router.patch("/plants/{plant_id}", response_model=PlantOut)
def update_plant(
    plant_id: int,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")

    allowed_fields = {
        "name",
        "category",
        "size",
        "description",
        "buy_price",
        "rent_price",
        "available_quantity",
        "availability_status",
        "care_instructions",
        "image_url",
    }
    invalid_fields = sorted(set(payload) - allowed_fields)
    if invalid_fields:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported fields for plant update: {', '.join(invalid_fields)}",
        )

    if "availability_status" in payload and payload["availability_status"] not in {
        "unavailable",
        "available_for_sale",
        "available_for_rent",
        "available_for_both",
    }:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Plant availability_status must be unavailable, available_for_sale, available_for_rent, or available_for_both",
        )

    for field, value in payload.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(plant, field, value)

    db.commit()
    db.refresh(plant)
    return plant


@router.post("/plants/{plant_id}/approve", response_model=PlantOut)
def approve_plant(
    plant_id: int,
    db: Session = Depends(get_db),
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")

    if plant.buy_price is not None and plant.rent_price is not None:
        plant.availability_status = "available_for_both"
    elif plant.buy_price is not None:
        plant.availability_status = "available_for_sale"
    elif plant.rent_price is not None:
        plant.availability_status = "available_for_rent"
    else:
        plant.availability_status = "unavailable"

    db.commit()
    db.refresh(plant)
    return plant


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