"""Admin authentication and admin-only management endpoints."""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import MaintenanceStatus, RequestStatus, RoleName, UserStatus
from app.core.security import DUMMY_HASH, create_access_token, verify_password
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import (
    MaintenanceRequest,
    MaintenanceSchedule,
    Nursery,
    Order,
    Page,
    Plant,
    PlantRentalOrder,
    PurchaseOrder,
    RentalOrder,
    RentalStatus,
    Role,
    RolePage,
    User,
)
from app.models.order import OrderStatus as CheckoutOrderStatus
from app.models.purchase_order import OrderStatus as PurchaseOrderStatus
from app.schemas.auth import LoginRequest, MessageResponse, TokenResponse
from app.schemas.admin import (
    CheckoutOrderStatusUpdate,
    LegacyRentalOrderAdminOut,
    MaintenanceRequestAdminUpdate,
    MaintenanceScheduleAdminUpdate,
    PurchaseOrderAdminOut,
    PurchaseOrderStatusUpdate,
    RentalOrderStatusUpdate,
)
from app.schemas.nursery import NurseryOut
from app.schemas.maintenance import MaintenanceRequestOut, MaintenanceScheduleOut
from app.schemas.order import OrderOut
from app.schemas.plant import PlantOut
from app.schemas.rental import PlantRentalOrderResponse
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


def _count_rows(db: Session, model, *criteria) -> int:
    query = select(func.count()).select_from(model)
    if criteria:
        query = query.where(*criteria)
    return db.scalar(query) or 0


@router.get("/dashboard/summary")
def admin_dashboard_summary(db: Session = Depends(get_db)):
    available_plant_statuses = (
        "available_for_sale",
        "available_for_rent",
        "available_for_both",
    )
    purchase_pending = (
        _count_rows(db, PurchaseOrder, PurchaseOrder.order_status == PurchaseOrderStatus.PENDING)
        + _count_rows(db, Order, Order.status == "Pending")
    )
    rental_pending = (
        _count_rows(db, PlantRentalOrder, PlantRentalOrder.status == RentalStatus.PENDING)
        + _count_rows(db, RentalOrder, RentalOrder.status == RentalStatus.PENDING.value)
    )
    schedule_count = _count_rows(db, MaintenanceSchedule)
    request_count = _count_rows(db, MaintenanceRequest)

    return {
        "users": {
            "total": _count_rows(db, User),
            "active": _count_rows(db, User, User.status == UserStatus.ACTIVE.value),
            "inactive": _count_rows(db, User, User.status == UserStatus.INACTIVE.value),
            "blocked": _count_rows(db, User, User.status == UserStatus.BLOCKED.value),
        },
        "nurseries": {
            "total": _count_rows(db, Nursery),
            "active": _count_rows(db, Nursery, Nursery.status == "active"),
        },
        "plant_listings": {
            "total": _count_rows(db, Plant),
            "available": _count_rows(
                db, Plant, Plant.availability_status.in_(available_plant_statuses)
            ),
            "pending_review": _count_rows(
                db, Plant, Plant.availability_status.in_(("unavailable", "pending_review"))
            ),
        },
        "purchase_orders": {
            "total": _count_rows(db, PurchaseOrder) + _count_rows(db, Order),
            "pending": purchase_pending,
        },
        "rental_orders": {
            "total": _count_rows(db, PlantRentalOrder) + _count_rows(db, RentalOrder),
            "pending": rental_pending,
        },
        "maintenance_records": {
            "total": schedule_count + request_count,
            "schedules": schedule_count,
            "pending_schedules": _count_rows(
                db, MaintenanceSchedule, MaintenanceSchedule.status == MaintenanceStatus.PENDING.value
            ),
            "requests": request_count,
            "open_requests": _count_rows(
                db, MaintenanceRequest, MaintenanceRequest.status == RequestStatus.OPEN.value
            ),
        },
    }


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
        normalized = status.strip().lower()
        if normalized in {"pending", "pending_review", "pending-review"}:
            query = query.where(Plant.availability_status.in_(["unavailable", "pending_review"]))
        else:
            query = query.where(Plant.availability_status == normalized)
    if nursery_id is not None:
        query = query.where(Plant.nursery_id == nursery_id)
    query = query.offset(skip).limit(limit)
    return db.scalars(query).all()


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: CheckoutOrderStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(Order).order_by(Order.created_at.desc(), Order.id.desc())
    if status_filter is not None:
        query = query.where(Order.status == status_filter.value)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: CheckoutOrderStatusUpdate,
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    order.status = payload.status.value
    db.commit()
    db.refresh(order)
    return order


@router.get("/purchase-orders", response_model=list[PurchaseOrderAdminOut])
def list_purchase_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: PurchaseOrderStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(PurchaseOrder).order_by(
        PurchaseOrder.order_date.desc(), PurchaseOrder.order_id.desc()
    )
    if status_filter is not None:
        query = query.where(PurchaseOrder.order_status == status_filter)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.get("/purchase-orders/{order_id}", response_model=PurchaseOrderAdminOut)
def get_purchase_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(PurchaseOrder, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return order


@router.patch(
    "/purchase-orders/{order_id}/status", response_model=PurchaseOrderAdminOut
)
def update_purchase_order_status(
    order_id: int,
    payload: PurchaseOrderStatusUpdate,
    db: Session = Depends(get_db),
):
    order = db.get(PurchaseOrder, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    order.order_status = payload.status
    db.commit()
    db.refresh(order)
    return order


@router.get("/rentals", response_model=list[PlantRentalOrderResponse])
@router.get("/rental-orders", response_model=list[PlantRentalOrderResponse])
def list_rental_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: RentalStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(PlantRentalOrder).order_by(
        PlantRentalOrder.created_at.desc(), PlantRentalOrder.rental_id.desc()
    )
    if status_filter is not None:
        query = query.where(PlantRentalOrder.status == status_filter)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.get("/rentals/{rental_id}", response_model=PlantRentalOrderResponse)
@router.get("/rental-orders/{rental_id}", response_model=PlantRentalOrderResponse)
def get_rental_order(rental_id: int, db: Session = Depends(get_db)):
    rental = db.get(PlantRentalOrder, rental_id)
    if rental is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rental order not found")
    return rental


@router.patch("/rentals/{rental_id}/status", response_model=PlantRentalOrderResponse)
@router.patch("/rental-orders/{rental_id}/status", response_model=PlantRentalOrderResponse)
def update_rental_order_status(
    rental_id: int,
    payload: RentalOrderStatusUpdate,
    db: Session = Depends(get_db),
):
    rental = db.get(PlantRentalOrder, rental_id)
    if rental is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rental order not found")
    rental.status = payload.status
    if payload.status.value == "Rejected":
        rental.rejection_reason = "Rejected by administrator"
    else:
        rental.rejection_reason = None
    db.commit()
    db.refresh(rental)
    return rental


@router.get("/legacy-rental-orders", response_model=list[LegacyRentalOrderAdminOut])
def list_legacy_rental_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: RentalStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(RentalOrder).order_by(RentalOrder.created_at.desc(), RentalOrder.id.desc())
    if status_filter is not None:
        query = query.where(RentalOrder.status == status_filter.value)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.get("/legacy-rental-orders/{rental_id}", response_model=LegacyRentalOrderAdminOut)
def get_legacy_rental_order(rental_id: int, db: Session = Depends(get_db)):
    rental = db.get(RentalOrder, rental_id)
    if rental is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rental order not found")
    return rental


@router.patch(
    "/legacy-rental-orders/{rental_id}/status",
    response_model=LegacyRentalOrderAdminOut,
)
def update_legacy_rental_order_status(
    rental_id: int,
    payload: RentalOrderStatusUpdate,
    db: Session = Depends(get_db),
):
    rental = db.get(RentalOrder, rental_id)
    if rental is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rental order not found")
    rental.status = payload.status.value
    db.commit()
    db.refresh(rental)
    return rental


@router.get("/maintenance/schedules", response_model=list[MaintenanceScheduleOut])
def list_maintenance_schedules(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: MaintenanceStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(MaintenanceSchedule).order_by(
        MaintenanceSchedule.due_date, MaintenanceSchedule.id
    )
    if status_filter is not None:
        query = query.where(MaintenanceSchedule.status == status_filter.value)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.get(
    "/maintenance/schedules/{schedule_id}", response_model=MaintenanceScheduleOut
)
def get_maintenance_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.get(MaintenanceSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maintenance schedule not found")
    return schedule


@router.patch(
    "/maintenance/schedules/{schedule_id}", response_model=MaintenanceScheduleOut
)
def update_maintenance_schedule(
    schedule_id: int,
    payload: MaintenanceScheduleAdminUpdate,
    db: Session = Depends(get_db),
):
    schedule = db.get(MaintenanceSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maintenance schedule not found")
    schedule.status = payload.status.value
    schedule.completed_at = (
        datetime.utcnow() if payload.status == MaintenanceStatus.COMPLETED else None
    )
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/maintenance/requests", response_model=list[MaintenanceRequestOut])
def list_maintenance_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: RequestStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(MaintenanceRequest).order_by(
        MaintenanceRequest.updated_at.desc(), MaintenanceRequest.id.desc()
    )
    if status_filter is not None:
        query = query.where(MaintenanceRequest.status == status_filter.value)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.get(
    "/maintenance/requests/{request_id}", response_model=MaintenanceRequestOut
)
def get_maintenance_request(request_id: int, db: Session = Depends(get_db)):
    request = db.get(MaintenanceRequest, request_id)
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maintenance request not found")
    return request


@router.patch(
    "/maintenance/requests/{request_id}", response_model=MaintenanceRequestOut
)
def update_maintenance_request(
    request_id: int,
    payload: MaintenanceRequestAdminUpdate,
    db: Session = Depends(get_db),
):
    request = db.get(MaintenanceRequest, request_id)
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maintenance request not found")
    if payload.status is not None:
        request.status = payload.status.value
    if "response_note" in payload.model_fields_set:
        request.response_note = payload.response_note
    db.commit()
    db.refresh(request)
    return request


@router.get("/plants/pending", response_model=list[PlantOut])
def list_pending_plants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = select(Plant).where(Plant.availability_status.in_(["unavailable", "pending_review"])).order_by(Plant.id)
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

    if "status" in payload and "availability_status" not in payload:
        payload["availability_status"] = payload["status"]

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
        "status",
    }
    invalid_fields = sorted(set(payload) - allowed_fields)
    if invalid_fields:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported fields for plant update: {', '.join(invalid_fields)}",
        )

    status_value = payload.get("availability_status", payload.get("status"))
    if status_value is not None and status_value not in {
        "unavailable",
        "pending_review",
        "available_for_sale",
        "available_for_rent",
        "available_for_both",
    }:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Plant status must be unavailable, pending_review, available_for_sale, available_for_rent, or available_for_both",
        )

    for field, value in payload.items():
        if field == "status":
            continue
        if isinstance(value, str):
            value = value.strip()
        setattr(plant, field, value)

    if "availability_status" in payload:
        plant.availability_status = payload["availability_status"]

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
        plant.availability_status = "pending_review"

    db.commit()
    db.refresh(plant)
    return plant


@router.post("/plants/{plant_id}/reject", response_model=PlantOut)
def reject_plant(
    plant_id: int,
    db: Session = Depends(get_db),
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    plant.availability_status = "unavailable"
    if plant.available_quantity > 0:
        plant.available_quantity = 0
    db.commit()
    db.refresh(plant)
    return plant


@router.patch("/plants/{plant_id}/status", response_model=PlantOut)
def update_plant_status(
    plant_id: int,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    if "status" not in payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A status field is required")
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    plant.availability_status = payload["status"]
    if payload["status"] == "unavailable" and plant.available_quantity > 0:
        plant.available_quantity = 0
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