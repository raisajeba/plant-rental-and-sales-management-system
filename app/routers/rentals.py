from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.constants import RoleName
from app.crud.rental import (
    create_rental_request,
    get_available_rental_plants,
    get_rental_plant,
    list_owner_rental_requests,
    update_owner_rental_status,
)
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import RentalStatus, User
from app.schemas.plant import PlantOut
from app.schemas.rental import (
    PlantRentalOrderCreate,
    PlantRentalOrderResponse,
    RentalOwnerOrderOut,
    RentalStatusUpdate,
)

router = APIRouter(
    prefix="/rentals",
    tags=["Plant Rentals"]
)


@router.get("/plants", response_model=list[PlantOut], status_code=status.HTTP_200_OK)
def browse_available_plants(db: Session = Depends(get_db)):
    return get_available_rental_plants(db)


@router.get("/plants/{plant_id}", response_model=PlantOut)
def get_plant_details(plant_id: int, db: Session = Depends(get_db)):
    return get_rental_plant(db, plant_id)


@router.post(
    "/requests",
    response_model=PlantRentalOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rental_order(
    order: PlantRentalOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.USER)),
):
    return create_rental_request(db, user=current_user, request=order)


@router.get("/owner", response_model=list[RentalOwnerOrderOut])
def get_owner_rental_requests(
    current_user: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    return list_owner_rental_requests(db, owner_id=current_user.id)


@router.patch(
    "/owner/{rental_id}/status",
    response_model=RentalOwnerOrderOut,
)
def update_rental_request_status(
    rental_id: int,
    payload: RentalStatusUpdate,
    current_user: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    return update_owner_rental_status(
        db,
        rental_id=rental_id,
        owner_id=current_user.id,
        new_status=RentalStatus(payload.status.value),
    )