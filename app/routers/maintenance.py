"""Maintenance: a user's care schedule (when / how) and maintenance requests."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select, union
from sqlalchemy.orm import Session

from app.core.care_guide import CARE_GUIDE
from app.core.constants import MaintenanceStatus, RequestStatus, RoleName
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import (
    MaintenanceRequest,
    MaintenanceSchedule,
    Nursery,
    Order,
    OrderItem,
    Plant,
    PlantRentalOrder,
    PurchaseOrder,
    RentalOrder,
    User,
)
from app.schemas.auth import MessageResponse
from app.schemas.maintenance import (
    CareTipOut,
    MaintenanceRequestCreate,
    MaintenanceRequestOut,
    MaintenanceScheduleCreate,
    MaintenanceScheduleOut,
    MaintenancePlantCustomerOut,
    NurseryMaintenanceCreate,
    NurseryMaintenanceOut,
    NurseryMaintenanceUpdate,
)

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


def _customer_plant_pairs():
    """Existing non-cancelled orders are the plant association source."""
    return union(
        select(Order.user_id.label("user_id"), OrderItem.plant_id.label("plant_id"))
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.status != "Cancelled"),
        select(PurchaseOrder.user_id.label("user_id"), PurchaseOrder.plant_id.label("plant_id"))
        .where(PurchaseOrder.order_status != "CANCELLED"),
        select(RentalOrder.user_id.label("user_id"), RentalOrder.plant_id.label("plant_id"))
        .where(RentalOrder.status.notin_(("Cancelled", "Rejected"))),
        select(PlantRentalOrder.user_id.label("user_id"), PlantRentalOrder.plant_id.label("plant_id"))
        .where(PlantRentalOrder.status.notin_(("Cancelled", "Rejected"))),
    ).subquery()


def _owner_records_query(owner: User):
    return (
        select(MaintenanceRequest, Plant, User)
        .outerjoin(
            Plant,
            and_(
                Plant.name == MaintenanceRequest.plant_name,
                Plant.nursery_id == MaintenanceRequest.nursery_id,
            ),
        )
        .join(Nursery, Nursery.id == MaintenanceRequest.nursery_id)
        .join(User, User.id == MaintenanceRequest.user_id)
        .where(
            Nursery.owner_id == owner.id,
            MaintenanceRequest.status != "cancelled"  # Cancelled request-gulo filter out korbe
        )
    )


def _owner_record_out(
    request: MaintenanceRequest, plant: Plant | None, customer: User
) -> NurseryMaintenanceOut:
    if request.status == RequestStatus.IN_PROGRESS.value:
        view_status = "in_progress"
    elif request.status == RequestStatus.RESOLVED.value:
        view_status = "completed"
    elif request.status == RequestStatus.CANCELLED.value:
        view_status = "cancelled"
    else:
        view_status = "scheduled" if request.preferred_date else "pending"

    return NurseryMaintenanceOut(
        id=request.id,
        plant_id=plant.id if plant else None,
        plant_name=plant.name if plant else request.plant_name,
        customer_id=customer.id,
        customer_name=customer.name,
        request_type=request.request_type,
        description=request.description,
        preferred_date=request.preferred_date,
        status=view_status,
        response_note=request.response_note,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


# =====================  CARE GUIDE  =====================
@router.get("/care-guide", response_model=list[CareTipOut])
def care_guide(_: User = Depends(require_roles(RoleName.USER))):
    """Default 'how to' tips. The frontend can show these or prefill the form."""
    return [CareTipOut(task_type=k, how_to=v) for k, v in CARE_GUIDE.items() if v]


# =====================  SCHEDULES  =====================
@router.get("/schedules/my", response_model=list[MaintenanceScheduleOut])
def my_schedules(
    status_filter: MaintenanceStatus | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    """The table on the Maintenance page: soonest task first."""
    stmt = select(MaintenanceSchedule).where(MaintenanceSchedule.user_id == user.id)
    if status_filter:
        stmt = stmt.where(MaintenanceSchedule.status == status_filter.value)
    stmt = stmt.order_by(MaintenanceSchedule.due_date).offset(skip).limit(limit)
    return db.scalars(stmt).all()


@router.post(
    "/schedules", response_model=MaintenanceScheduleOut, status_code=status.HTTP_201_CREATED
)
def create_schedule(
    payload: MaintenanceScheduleCreate,
    user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    """The user adds a care task for one of their plants."""
    schedule = MaintenanceSchedule(
        user_id=user.id,
        plant_name=payload.plant_name,
        task_type=payload.task_type.value,
        instructions=payload.instructions or CARE_GUIDE[payload.task_type.value],
        due_date=payload.due_date,
        frequency_days=payload.frequency_days,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def _get_my_schedule(schedule_id: int, user: User, db: Session) -> MaintenanceSchedule:
    schedule = db.scalar(
        select(MaintenanceSchedule).where(
            MaintenanceSchedule.id == schedule_id, MaintenanceSchedule.user_id == user.id
        )
    )
    if schedule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
    return schedule


@router.patch("/schedules/{schedule_id}/complete", response_model=MaintenanceScheduleOut)
def complete_schedule(
    schedule_id: int,
    user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    """Mark a task done. Recurring tasks automatically create the next one."""
    schedule = _get_my_schedule(schedule_id, user, db)
    if schedule.status != MaintenanceStatus.PENDING.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only pending tasks can be completed")

    schedule.status = MaintenanceStatus.COMPLETED.value
    schedule.completed_at = func.now()

    if schedule.frequency_days:
        next_due = max(schedule.due_date, date.today()) + timedelta(days=schedule.frequency_days)
        db.add(MaintenanceSchedule(
            user_id=schedule.user_id,
            plant_name=schedule.plant_name,
            task_type=schedule.task_type,
            instructions=schedule.instructions,
            due_date=next_due,
            frequency_days=schedule.frequency_days,
        ))

    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/schedules/{schedule_id}", response_model=MessageResponse)
def delete_schedule(
    schedule_id: int,
    user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    schedule = _get_my_schedule(schedule_id, user, db)
    db.delete(schedule)
    db.commit()
    return MessageResponse(message="Task deleted")


# =====================  REQUESTS  =====================
@router.post(
    "/requests", response_model=MaintenanceRequestOut, status_code=status.HTTP_201_CREATED
)
def create_request(
    payload: MaintenanceRequestCreate,
    user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    nursery_id = payload.nursery_id
    if payload.nursery_name:
        if nursery_id is not None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Provide nursery_id or nursery_name, not both",
            )
        matching_nurseries = db.scalars(
            select(Nursery).where(
                Nursery.name == payload.nursery_name,
                Nursery.status == "active",
            )
        ).all()
        if not matching_nurseries:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
        if len(matching_nurseries) > 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Multiple nurseries have this name; provide nursery_id",
            )
        nursery_id = matching_nurseries[0].id
    if nursery_id is not None:
        nursery = db.get(Nursery, nursery_id)
        if nursery is None or nursery.status != "active":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")

    try:
        request = MaintenanceRequest(
            user_id=user.id,
            nursery_id=nursery_id,
            plant_name=payload.plant_name,
            request_type=payload.request_type.value,
            description=payload.description,
            preferred_date=payload.preferred_date,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
    except Exception as e:
        db.rollback()
        # Fallback to prevent 503 OperationalError in MySQL/Database
        request = MaintenanceRequest(
            user_id=user.id,
            nursery_id=nursery_id,
            plant_name=payload.plant_name if payload.plant_name else "General Plant",
            request_type=payload.request_type.value,
            description=payload.description,
            preferred_date=payload.preferred_date,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request


@router.get("/requests/my", response_model=list[MaintenanceRequestOut])
def my_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    # Customer-এর নিজের তৈরি করা Requests (যেখানে nursery_id আছে অথবা user নিজে submit করেছে)
    stmt = (
        select(MaintenanceRequest)
        .where(MaintenanceRequest.user_id == user.id)
        .order_by(MaintenanceRequest.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.patch("/requests/{request_id}/cancel", response_model=MaintenanceRequestOut)
def cancel_request(
    request_id: int,
    user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    request = db.scalar(
        select(MaintenanceRequest).where(
            MaintenanceRequest.id == request_id, MaintenanceRequest.user_id == user.id
        )
    )
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if request.status != RequestStatus.OPEN.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only open requests can be cancelled")

    request.status = RequestStatus.CANCELLED.value
    db.commit()
    db.refresh(request)
    return request


# =====================  NURSERY RECORDS  =====================
@router.get("/owner/plant-customers", response_model=list[MaintenancePlantCustomerOut])
def owner_plant_customers(
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    """Only show customers with an order for a plant owned by this nursery."""
    pairs = _customer_plant_pairs()
    stmt = (
        select(
            Plant.id.label("plant_id"),
            Plant.name.label("plant_name"),
            User.id.label("customer_id"),
            User.name.label("customer_name"),
        )
        .join(Nursery, Nursery.id == Plant.nursery_id)
        .join(pairs, pairs.c.plant_id == Plant.id)
        .join(User, User.id == pairs.c.user_id)
        .where(Nursery.owner_id == owner.id)
        .distinct()
        .order_by(Plant.name, User.name)
    )
    return db.execute(stmt).mappings().all()


@router.get("/owner/records", response_model=list[NurseryMaintenanceOut])
def owner_maintenance_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        _owner_records_query(owner)
        .order_by(MaintenanceRequest.updated_at.desc(), MaintenanceRequest.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return [_owner_record_out(*row) for row in rows]


@router.post(
    "/owner/records",
    response_model=NurseryMaintenanceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_owner_maintenance_record(
    payload: NurseryMaintenanceCreate,
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    plant = db.scalar(
        select(Plant)
        .join(Nursery, Nursery.id == Plant.nursery_id)
        .where(Plant.id == payload.plant_id, Nursery.owner_id == owner.id)
    )
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")

    pairs = _customer_plant_pairs()
    customer = db.scalar(
        select(User)
        .join(pairs, pairs.c.user_id == User.id)
        .where(pairs.c.plant_id == plant.id, User.id == payload.customer_id)
    )
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant/customer association not found")

    # 1. MaintenanceRequest (Owner History-র জন্য):
    request = MaintenanceRequest(
        user_id=customer.id,
        nursery_id=plant.nursery_id,
        plant_name=plant.name,
        request_type=payload.request_type.value,
        description=payload.description,
        preferred_date=payload.preferred_date,
    )
    db.add(request)

    # 2. ALSO Add to MaintenanceSchedule (Customer-এর 'My Care Schedule'-এর জন্য):
    instructions_text = f"[Nursery Task] {payload.description}"
    schedule = MaintenanceSchedule(
        user_id=customer.id,
        plant_name=plant.name,
        task_type=payload.request_type.value,
        instructions=instructions_text,
        due_date=payload.preferred_date or date.today(),
        status="pending"
    )
    db.add(schedule)

    db.commit()
    db.refresh(request)
    return _owner_record_out(request, plant, customer)

@router.patch("/owner/records/{request_id}", response_model=NurseryMaintenanceOut)
def update_owner_maintenance_record(
    request_id: int,
    payload: NurseryMaintenanceUpdate,
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    row = db.execute(
        _owner_records_query(owner).where(MaintenanceRequest.id == request_id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maintenance record not found")
    request, plant, customer = row
    if request.status == RequestStatus.CANCELLED.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cancelled records cannot be updated")

    changes = payload.model_fields_set
    if "preferred_date" in changes:
        request.preferred_date = payload.preferred_date
    if "response_note" in changes:
        request.response_note = payload.response_note
    if payload.status == "pending":
        request.status = RequestStatus.OPEN.value
        if "preferred_date" not in changes:
            request.preferred_date = None
    elif payload.status == "scheduled":
        if request.preferred_date is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "A preferred date is required for a scheduled record",
            )
        request.status = RequestStatus.OPEN.value
    elif payload.status == "in_progress":
        request.status = RequestStatus.IN_PROGRESS.value
    elif payload.status == "completed":
        request.status = RequestStatus.RESOLVED.value
   
    db.commit()
    db.refresh(request)
    
    # Ekhane return statement-ti add kore dite hobe:
    return _owner_record_out(request, plant, customer)