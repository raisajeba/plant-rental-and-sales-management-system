"""Admin-only management endpoints (RBAC example)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import (
    ApprovalStatus,
    AvailabilityStatus,
    ListingApprovalStatus,
    RoleName,
    UserStatus,
)
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import Nursery, Page, Plant, Role, RolePage, User
from app.schemas.auth import MessageResponse
from app.schemas.nursery import AdminNurseryOut, AdminNurseryUpdate
from app.schemas.plant import AdminPlantOut, AdminPlantUpdate, PlantCreate, PlantOut
from app.schemas.user import AdminUserUpdate, PageOut, RoleOut, UserOut

# The dependency on the router protects EVERY endpoint below.
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_roles(RoleName.ADMIN))],
)


def _admin_plant_data(plant: Plant) -> dict:
    return {
        **PlantOut.model_validate(plant).model_dump(),
        "nursery_name": plant.nursery.name,
        "nursery_owner_id": plant.nursery.owner.id,
        "nursery_owner_name": plant.nursery.owner.name,
        "nursery_owner_email": plant.nursery.owner.email,
    }


def _admin_plant_query():
    return select(Plant).options(
        joinedload(Plant.nursery).joinedload(Nursery.owner)
    )


@router.get("/plants", response_model=list[AdminPlantOut])
def list_plants(
    approval_status: ListingApprovalStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    statement = _admin_plant_query()
    if approval_status is not None:
        statement = statement.where(Plant.approval_status == approval_status.value)
    plants = db.scalars(
        statement.order_by(Plant.id).offset(skip).limit(limit)
    ).all()
    return [_admin_plant_data(plant) for plant in plants]


@router.get("/plants/pending", response_model=list[AdminPlantOut])
def list_pending_plants(db: Session = Depends(get_db)):
    plants = db.scalars(
        _admin_plant_query()
        .where(Plant.approval_status == ListingApprovalStatus.PENDING.value)
        .order_by(Plant.created_at, Plant.id)
    ).all()
    return [_admin_plant_data(plant) for plant in plants]


@router.get("/plants/{plant_id}", response_model=AdminPlantOut)
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    plant = db.scalar(
        _admin_plant_query().where(Plant.id == plant_id)
    )
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant listing not found")
    return _admin_plant_data(plant)


def _set_listing_approval(
    plant_id: int,
    approval_status: ListingApprovalStatus,
    db: Session,
) -> dict:
    plant = db.scalar(
        _admin_plant_query()
        .where(Plant.id == plant_id)
        .with_for_update()
    )
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant listing not found")
    if plant.approval_status != ListingApprovalStatus.PENDING.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only pending plant listings can be approved or rejected",
        )

    if approval_status == ListingApprovalStatus.APPROVED:
        try:
            PlantCreate.model_validate(
                {
                    "name": plant.name,
                    "category": plant.category,
                    "size": plant.size,
                    "description": plant.description,
                    "buy_price": plant.buy_price,
                    "rent_price": plant.rent_price,
                    "available_quantity": plant.available_quantity,
                    "availability_status": plant.availability_status,
                    "care_instructions": plant.care_instructions,
                }
            )
        except ValidationError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=exc.errors(include_input=False, include_context=False),
            )

    plant.approval_status = approval_status.value
    if approval_status == ListingApprovalStatus.REJECTED:
        plant.availability_status = AvailabilityStatus.UNAVAILABLE.value
    db.commit()
    db.refresh(plant)
    return _admin_plant_data(plant)


@router.post("/plants/{plant_id}/approve", response_model=AdminPlantOut)
def approve_plant(plant_id: int, db: Session = Depends(get_db)):
    return _set_listing_approval(
        plant_id, ListingApprovalStatus.APPROVED, db
    )


@router.post("/plants/{plant_id}/reject", response_model=AdminPlantOut)
def reject_plant(plant_id: int, db: Session = Depends(get_db)):
    return _set_listing_approval(
        plant_id, ListingApprovalStatus.REJECTED, db
    )


@router.patch("/plants/{plant_id}", response_model=AdminPlantOut)
def update_plant_listing(
    plant_id: int,
    payload: AdminPlantUpdate,
    db: Session = Depends(get_db),
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant listing not found")
    if (
        payload.availability_status != AvailabilityStatus.UNAVAILABLE
        and plant.approval_status != ListingApprovalStatus.APPROVED.value
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only approved plant listings can be made available",
        )

    data = {
        "name": plant.name,
        "category": plant.category,
        "size": plant.size,
        "description": plant.description,
        "buy_price": plant.buy_price,
        "rent_price": plant.rent_price,
        "available_quantity": (
            payload.available_quantity
            if payload.available_quantity is not None
            else plant.available_quantity
        ),
        "availability_status": payload.availability_status.value,
        "care_instructions": plant.care_instructions,
    }
    if data["available_quantity"] == 0:
        data["availability_status"] = AvailabilityStatus.UNAVAILABLE.value
    try:
        PlantCreate.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(include_input=False, include_context=False),
        )

    plant.available_quantity = data["available_quantity"]
    plant.availability_status = data["availability_status"]
    db.commit()
    db.refresh(plant)
    result = db.scalar(_admin_plant_query().where(Plant.id == plant.id))
    return _admin_plant_data(result)


@router.get("/nurseries", response_model=list[AdminNurseryOut])
def list_nurseries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Nursery)
        .options(joinedload(Nursery.owner))
        .order_by(Nursery.id)
        .offset(skip)
        .limit(limit)
    ).all()


@router.get("/nurseries/{nursery_id}", response_model=AdminNurseryOut)
def get_nursery(nursery_id: int, db: Session = Depends(get_db)):
    nursery = db.scalar(
        select(Nursery)
        .options(joinedload(Nursery.owner))
        .where(Nursery.id == nursery_id)
    )
    if nursery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    return nursery


@router.patch("/nurseries/{nursery_id}", response_model=AdminNurseryOut)
def update_nursery(
    nursery_id: int,
    payload: AdminNurseryUpdate,
    db: Session = Depends(get_db),
):
    nursery = db.get(Nursery, nursery_id)
    if nursery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")

    nursery.status = payload.status.value
    db.commit()
    db.refresh(nursery)
    return nursery


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