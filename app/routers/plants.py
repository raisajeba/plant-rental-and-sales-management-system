import logging
from pathlib import Path
from uuid import uuid4

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.core.constants import AvailabilityStatus, RoleName
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import Nursery, Plant, User
from app.schemas.plant import PlantOut, PlantSearchOut
from app.schemas.plant import PlantCreate, PlantUpdate

router = APIRouter(prefix="/plants", tags=["Plants"])
logger = logging.getLogger(__name__)
PLANT_IMAGE_DIR = Path("uploads/plants")
PLANT_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_PLANT_IMAGE_SIZE = 5 * 1024 * 1024


def _remove_managed_plant_image(image_url: str | None) -> None:
    if not image_url or not image_url.startswith("/uploads/plants/"):
        return

    image_path = Path(image_url.lstrip("/"))
    try:
        if image_path.parent.resolve() == PLANT_IMAGE_DIR.resolve():
            image_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove replaced plant image: %s", image_path)


def verify_plant_ownership(db: Session, user_id: int, plant: Plant) -> None:
    nursery = db.get(Nursery, plant.nursery_id)
    if nursery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    if nursery.owner_id != user_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can only perform actions on plants in your own nursery",
        )


@router.get("", response_model=list[PlantSearchOut])
def list_plants(
    plant_type: Literal["Indoor", "Outdoor"] | None = Query(None),
    size: str | None = Query(None, min_length=1, max_length=50),
    min_price: Decimal | None = Query(None, ge=0, max_digits=10, decimal_places=2),
    max_price: Decimal | None = Query(None, ge=0, max_digits=10, decimal_places=2),
    availability: AvailabilityStatus | None = Query(None),
    category: str | None = Query(None, min_length=1, max_length=50),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    """Filter active-nursery plants; Indoor/Outdoor uses the existing category field."""
    search_terms = {"size": size, "category": category}
    normalized_terms = {
        key: value.strip()
        for key, value in search_terms.items()
        if value is not None
    }
    if any(not value for value in normalized_terms.values()):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Search criteria cannot be blank",
        )
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "min_price must not be greater than max_price",
        )

    statement = (
        select(Plant, Nursery.name.label("nursery_name"))
        .join(Nursery, Plant.nursery_id == Nursery.id)
        .where(Nursery.status == "active")
    )
    if plant_type is not None:
        statement = statement.where(
            func.lower(Plant.category) == plant_type.lower()
        )
    if "size" in normalized_terms:
        statement = statement.where(
            func.lower(Plant.size) == normalized_terms["size"].lower()
        )
    if "category" in normalized_terms:
        statement = statement.where(
            func.lower(Plant.category) == normalized_terms["category"].lower()
        )
    if availability is not None:
        statement = statement.where(
            Plant.availability_status == availability.value
        )
    if min_price is not None or max_price is not None:
        price_conditions = []
        for price_column in (Plant.buy_price, Plant.rent_price):
            bounds = []
            if min_price is not None:
                bounds.append(price_column >= min_price)
            if max_price is not None:
                bounds.append(price_column <= max_price)
            price_conditions.append(and_(*bounds))
        statement = statement.where(or_(*price_conditions))

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


@router.get("/public", response_model=list[PlantSearchOut])
def list_public_plants(
    limit: int = Query(8, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return available listings for the public plant catalog."""
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
        .order_by(Plant.name, Plant.id)
        .limit(limit)
    )
    matches = db.execute(statement).all()
    return [
        {
            **PlantOut.model_validate(plant).model_dump(),
            "nursery_name": nursery_name,
        }
        for plant, nursery_name in matches
    ]


@router.get("/search", response_model=list[PlantSearchOut])
def search_plants(
    name: str | None = Query(None, min_length=1, max_length=150),
    category: str | None = Query(None, min_length=1, max_length=50),
    nursery: str | None = Query(None, min_length=1, max_length=150),
    nursery_id: int | None = Query(None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles(RoleName.USER)),
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
def get_plant(
    plant_id: int,
    _: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    return plant


# 4. Update Plant (Authenticated Nursery Owner Only)
@router.put("/{plant_id}", response_model=PlantOut)
async def update_plant(
    plant_id: int,
    request: Request,
    current_user: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")

    verify_plant_ownership(db, current_user.id, plant)

    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    image: UploadFile | None = None
    if content_type == "multipart/form-data":
        form = await request.form()
        fields = {}
        for key, value in form.multi_items():
            if key == "image":
                if not isinstance(value, UploadFile):
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid image upload")
                image = value
            else:
                fields[key] = None if value == "" and key in {"buy_price", "rent_price"} else value
    elif content_type == "application/json":
        fields = await request.json()
        if not isinstance(fields, dict):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Plant update must be a JSON object",
            )
    else:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Send plant updates as JSON or multipart/form-data",
        )

    try:
        plant_in = PlantUpdate.model_validate(fields)
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error.errors(include_context=False, include_url=False),
        )

    update_data = plant_in.model_dump(exclude_unset=True)

    if "name" in update_data:
        duplicate_id = db.scalar(
            select(Plant.id).where(
                Plant.nursery_id == plant.nursery_id,
                Plant.name == update_data["name"],
                Plant.id != plant.id,
            )
        )
        if duplicate_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This nursery already has a plant with this name",
            )

    candidate = {
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
    candidate.update(update_data)
    if candidate["available_quantity"] == 0:
        candidate["availability_status"] = AvailabilityStatus.UNAVAILABLE
        update_data["availability_status"] = AvailabilityStatus.UNAVAILABLE

    try:
        validated_candidate = PlantCreate.model_validate(candidate)
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error.errors(include_context=False, include_url=False),
        )

    candidate_data = validated_candidate.model_dump()
    old_image_url = plant.image_url
    image_path = None
    if image is not None:
        image_extension = PLANT_IMAGE_CONTENT_TYPES.get(image.content_type or "")
        if image_extension is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Only JPG, PNG, and WEBP plant images are allowed",
            )
        image_data = await image.read(MAX_PLANT_IMAGE_SIZE + 1)
        if not image_data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded image is empty")
        if len(image_data) > MAX_PLANT_IMAGE_SIZE:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Plant images must not exceed 5 MB")

        filename = f"plant_{uuid4().hex}{image_extension}"
        image_path = PLANT_IMAGE_DIR / filename
        try:
            PLANT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(image_data)
        except OSError as error:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "The plant image could not be saved",
            ) from error
        candidate_data["image_url"] = f"/uploads/plants/{filename}"

    for key, value in candidate_data.items():
        setattr(plant, key, value.value if key == "availability_status" else value)
    db.add(plant)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if image_path is not None:
            _remove_managed_plant_image(f"/{image_path.as_posix()}")
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The plant could not be updated because it conflicts with existing data",
        ) from error
    except SQLAlchemyError:
        db.rollback()
        if image_path is not None:
            _remove_managed_plant_image(f"/{image_path.as_posix()}")
        raise
    db.refresh(plant)
    if image_path is not None:
        _remove_managed_plant_image(old_image_url)
    return plant


# 5. Delete Plant (Authenticated Nursery Owner Only)
@router.delete("/{plant_id}", status_code=status.HTTP_200_OK)
def delete_plant(
    plant_id: int,
    current_user: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db)
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")

    verify_plant_ownership(db, current_user.id, plant)

    db.delete(plant)
    db.commit()
    return {"message": "Plant deleted successfully"}
    PlantUpdate.model_rebuild()