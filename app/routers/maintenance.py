"""Maintenance: a user's care schedule (when / how) and maintenance requests."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.care_guide import CARE_GUIDE
from app.core.constants import MaintenanceStatus, RequestStatus
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import MaintenanceRequest, MaintenanceSchedule, User
from app.schemas.auth import MessageResponse
from app.schemas.maintenance import (
    CareTipOut,
    MaintenanceRequestCreate,
    MaintenanceRequestOut,
    MaintenanceScheduleCreate,
    MaintenanceScheduleOut,
)

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


# =====================  CARE GUIDE  =====================
@router.get("/care-guide", response_model=list[CareTipOut])
def care_guide(_: User = Depends(get_current_user)):
    """Default 'how to' tips. The frontend can show these or prefill the form."""
    return [CareTipOut(task_type=k, how_to=v) for k, v in CARE_GUIDE.items() if v]


# =====================  SCHEDULES  =====================
@router.get("/schedules/my", response_model=list[MaintenanceScheduleOut])
def my_schedules(
    status_filter: MaintenanceStatus | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The user adds a care task for one of their plants."""
    schedule = MaintenanceSchedule(
        user_id=user.id,
        plant_name=payload.plant_name,
        task_type=payload.task_type.value,
        # No instructions typed? Fall back to the default tip for this task type
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = MaintenanceRequest(
        user_id=user.id,
        plant_name=payload.plant_name,
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    user: User = Depends(get_current_user),
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