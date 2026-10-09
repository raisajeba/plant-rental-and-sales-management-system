from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import AvailabilityStatus
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Nursery, Plant, User
from app.schemas.plant import PlantOut, PlantSearchOut

router = APIRouter(prefix="/plants", tags=["Plants"])


@router.get("/search", response_model=list[PlantSearchOut])
def search_plants(
    name: str | None = Query(None, min_length=1, max_length=150),
    category: str | None = Query(None, min_length=1, max_length=50),
    nursery: str | None = Query(None, min_length=1, max_length=150),
    nursery_id: int | None = Query(None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search available plants by name, category, nursery name, or nursery ID."""
    search_terms = {
        "name": name,
        "category": category,
        "nursery": nursery,
    }
    normalized_terms = {
        key: value.strip()
        for key, value in search_terms.items()
        if value is not None
    }
    if not normalized_terms and nursery_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "At least one search criterion is required",
        )
    if any(not value for value in normalized_terms.values()):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Search criteria cannot be blank",
        )

    statement = (
        select(Plant, Nursery.name.label("nursery_name"))
        .join(Nursery, Plant.nursery_id == Nursery.id)
        .where(
            Nursery.status == "active",
            Plant.available_quantity > 0,
            Plant.availability_status.in_(
                [
                    AvailabilityStatus.FOR_SALE.value,
                    AvailabilityStatus.FOR_RENT.value,
                    AvailabilityStatus.FOR_BOTH.value,
                ]
            ),
        )
    )
    if "name" in normalized_terms:
        statement = statement.where(
            Plant.name.ilike(f"%{normalized_terms['name']}%")
        )
    if "category" in normalized_terms:
        statement = statement.where(
            Plant.category.ilike(normalized_terms["category"])
        )
    if "nursery" in normalized_terms:
        statement = statement.where(
            Nursery.name.ilike(f"%{normalized_terms['nursery']}%")
        )
    if nursery_id is not None:
        statement = statement.where(Nursery.id == nursery_id)

    matches = db.execute(
        statement.order_by(Plant.name, Plant.id).offset(skip).limit(limit)
    ).all()
    return [
        {
            **PlantOut.model_validate(plant).model_dump(),
            "nursery_name": nursery_name,
        }
        for plant, nursery_name in matches
    ]


@router.get("/{plant_id}", response_model=PlantOut)
def get_plant(plant_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    return plant