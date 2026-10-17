from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.constants import AvailabilityStatus
from app.models import Nursery, Plant, PlantRentalOrder, RentalStatus, User
from app.schemas.rental import PlantRentalOrderCreate

_RENTAL_STATUSES_RESERVING_STOCK = (
    RentalStatus.PENDING,
    RentalStatus.CONFIRMED,
    RentalStatus.ACTIVE,
)


def _plant_is_available_for_rent(plant: Plant) -> bool:
    return (
        plant.nursery.status == "active"
        and plant.availability_status
        in (
            AvailabilityStatus.FOR_RENT.value,
            AvailabilityStatus.FOR_BOTH.value,
        )
        and plant.available_quantity > 0
        and plant.rent_price is not None
        and plant.rent_price > 0
    )


def get_available_rental_plants(db: Session) -> list[Plant]:
    statement = (
        select(Plant)
        .join(Nursery, Nursery.id == Plant.nursery_id)
        .where(
            Nursery.status == "active",
            Plant.availability_status.in_(
                (
                    AvailabilityStatus.FOR_RENT.value,
                    AvailabilityStatus.FOR_BOTH.value,
                )
            ),
            Plant.available_quantity > 0,
            Plant.rent_price.is_not(None),
            Plant.rent_price > 0,
        )
        .order_by(Plant.name, Plant.id)
    )
    return list(db.scalars(statement).all())


def get_rental_plant(db: Session, plant_id: int) -> Plant:
    plant = db.scalar(
        select(Plant)
        .options(joinedload(Plant.nursery))
        .where(Plant.id == plant_id)
    )
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found",
        )
    if not _plant_is_available_for_rent(plant):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant is not currently available for rent",
        )
    return plant


def create_rental_request(
    db: Session,
    *,
    user: User,
    request: PlantRentalOrderCreate,
) -> PlantRentalOrder:
    plant = db.scalar(
        select(Plant)
        .options(joinedload(Plant.nursery))
        .where(Plant.id == request.plant_id)
        .with_for_update()
    )
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found",
        )
    if not _plant_is_available_for_rent(plant):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Plant is not currently available for rent",
        )

    overlapping_orders = db.scalars(
        select(PlantRentalOrder)
        .where(
            PlantRentalOrder.plant_id == plant.id,
            PlantRentalOrder.status.in_(_RENTAL_STATUSES_RESERVING_STOCK),
            PlantRentalOrder.rental_start_date <= request.rental_end_date,
            PlantRentalOrder.rental_end_date >= request.rental_start_date,
        )
        .with_for_update()
    ).all()
    candidate_days = {
        request.rental_start_date,
        *(
            order.rental_start_date
            for order in overlapping_orders
            if request.rental_start_date
            <= order.rental_start_date
            <= request.rental_end_date
        ),
    }
    maximum_reserved_quantity = max(
        (
            sum(
                order.quantity
                for order in overlapping_orders
                if order.rental_start_date <= rental_day <= order.rental_end_date
            )
            for rental_day in candidate_days
        ),
        default=0,
    )
    if maximum_reserved_quantity + request.quantity > plant.available_quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Requested quantity exceeds the plant's available quantity "
                "for the selected dates."
            ),
        )

    rental_duration_days = max(
        (request.rental_end_date - request.rental_start_date).days,
        1,
    )
    rental_price_per_day = Decimal(str(plant.rent_price)).quantize(
        Decimal("0.01")
    )
    total_amount = (
        rental_price_per_day * request.quantity * rental_duration_days
    ).quantize(Decimal("0.01"))
    if total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The calculated rental amount must be greater than zero",
        )

    rental_order = PlantRentalOrder(
        user_id=user.id,
        plant_id=plant.id,
        quantity=request.quantity,
        rental_start_date=request.rental_start_date,
        rental_end_date=request.rental_end_date,
        rental_duration_days=rental_duration_days,
        rental_price_per_day=rental_price_per_day,
        total_amount=total_amount,
        status=RentalStatus.PENDING,
    )
    db.add(rental_order)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The rental request could not be saved. Please try again.",
        ) from exc
    db.refresh(rental_order)
    return rental_order


def list_owner_rental_requests(db: Session, *, owner_id: int) -> list[dict]:
    rows = db.execute(
        select(PlantRentalOrder, User.name, Plant.name)
        .join(User, User.id == PlantRentalOrder.user_id)
        .join(Plant, Plant.id == PlantRentalOrder.plant_id)
        .join(Nursery, Nursery.id == Plant.nursery_id)
        .where(Nursery.owner_id == owner_id)
        .order_by(PlantRentalOrder.created_at.desc(), PlantRentalOrder.rental_id.desc())
    ).all()
    return [
        {
            "id": rental.rental_id,
            "customer_name": customer_name,
            "plant_name": plant_name,
            "quantity": rental.quantity,
            "rental_start_date": rental.rental_start_date,
            "rental_end_date": rental.rental_end_date,
            "rental_duration_days": rental.rental_duration_days,
            "rental_price_per_day": rental.rental_price_per_day,
            "total_amount": rental.total_amount,
            "status": rental.status,
            "created_at": rental.created_at,
        }
        for rental, customer_name, plant_name in rows
    ]


def update_owner_rental_status(
    db: Session,
    *,
    rental_id: int,
    owner_id: int,
    new_status: RentalStatus,
) -> dict:
    rental = db.scalar(
        select(PlantRentalOrder)
        .join(Plant, Plant.id == PlantRentalOrder.plant_id)
        .join(Nursery, Nursery.id == Plant.nursery_id)
        .where(
            PlantRentalOrder.rental_id == rental_id,
            Nursery.owner_id == owner_id,
        )
        .with_for_update()
    )
    if rental is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rental request not found",
        )

    allowed_transitions = {
        RentalStatus.PENDING: {
            RentalStatus.CONFIRMED,
            RentalStatus.CANCELLED,
        },
        RentalStatus.CONFIRMED: {
            RentalStatus.ACTIVE,
            RentalStatus.CANCELLED,
        },
        RentalStatus.ACTIVE: {RentalStatus.COMPLETED},
        RentalStatus.COMPLETED: set(),
        RentalStatus.CANCELLED: set(),
    }
    if new_status not in allowed_transitions[rental.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot change rental status from {rental.status.value} to {new_status.value}",
        )

    rental.status = new_status
    db.commit()
    db.refresh(rental)
    return {
        "id": rental.rental_id,
        "customer_name": rental.user.name,
        "plant_name": rental.plant.name,
        "quantity": rental.quantity,
        "rental_start_date": rental.rental_start_date,
        "rental_end_date": rental.rental_end_date,
        "rental_duration_days": rental.rental_duration_days,
        "rental_price_per_day": rental.rental_price_per_day,
        "total_amount": rental.total_amount,
        "status": rental.status,
        "created_at": rental.created_at,
    }
