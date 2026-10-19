from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.core.constants import AvailabilityStatus, ListingApprovalStatus, RoleName
from app.crud import nursery as crud_nursery
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import Nursery, Plant, User
from app.schemas.nursery import NurseryCreate, NurseryOut, NurseryUpdate
from app.schemas.plant import PlantCreate, PlantOut

router = APIRouter(prefix="/nurseries", tags=["Nurseries"])

PLANT_IMAGE_DIR = Path("uploads/plants")
PLANT_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_PLANT_IMAGE_SIZE = 5 * 1024 * 1024


def _get_owned_nursery(nursery_id: int, user: User, db: Session) -> Nursery:
    nursery = db.get(Nursery, nursery_id)
    if nursery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    if nursery.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You can only perform actions on your own nursery"
        )
    if nursery.status != "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This nursery is not active")
    return nursery


@router.post("", response_model=NurseryOut, status_code=status.HTTP_201_CREATED)
def create_nursery(
    payload: NurseryCreate,
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    duplicate = db.scalar(
        select(Nursery.id).where(Nursery.owner_id == owner.id, Nursery.name == payload.name)
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a nursery with this name")

    nursery = Nursery(owner_id=owner.id, **payload.model_dump())
    db.add(nursery)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a nursery with this name")
    db.refresh(nursery)
    return nursery


@router.get("/mine", response_model=list[NurseryOut])
def list_my_nurseries(
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    stmt = select(Nursery).where(Nursery.owner_id == owner.id).order_by(Nursery.id.desc())
    return db.scalars(stmt).all()


@router.get("/me", response_model=NurseryOut, summary="View Current Nursery Profile")
def view_my_nursery_profile(
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    """View logged-in user's nursery profile."""
    nursery = crud_nursery.get_nursery_by_owner_id(db, owner_id=owner.id)
    if not nursery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nursery profile not found for current user",
        )
    return nursery


@router.get("/mine/plants", response_model=list[PlantOut])
def list_my_nursery_plants(
    category: str | None = Query(None, max_length=50),
    availability: AvailabilityStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Plant)
        .join(Nursery, Plant.nursery_id == Nursery.id)
        .where(Nursery.owner_id == owner.id)
    )
    if category:
        stmt = stmt.where(Plant.category.ilike(category))
    if availability:
        stmt = stmt.where(Plant.availability_status == availability.value)
    return db.scalars(stmt.order_by(Plant.id.desc()).offset(skip).limit(limit)).all()


@router.put("/{nursery_id}", response_model=NurseryOut, summary="Update Nursery Profile")
def update_nursery_profile(
    nursery_id: int,
    payload: NurseryUpdate,
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    """Update nursery details with authorization and ownership checks."""
    nursery = _get_owned_nursery(nursery_id, owner, db)
    updated_nursery = crud_nursery.update_nursery(db, db_nursery=nursery, nursery_in=payload)
    return updated_nursery


@router.get("", response_model=list[NurseryOut])
def list_nurseries(
    city: str | None = Query(None, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    stmt = select(Nursery).where(Nursery.status == "active")
    if city:
        stmt = stmt.where(Nursery.city.ilike(f"%{city}%"))
    return db.scalars(stmt.order_by(Nursery.id.desc()).offset(skip).limit(limit)).all()


@router.get("/{nursery_id}", response_model=NurseryOut)
def get_nursery(
    nursery_id: int,
    _: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    nursery = db.get(Nursery, nursery_id)
    if nursery is None or nursery.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    return nursery


@router.post("/{nursery_id}/plants", response_model=PlantOut, status_code=status.HTTP_201_CREATED)
async def add_plant_to_nursery(
    nursery_id: int,
    request: Request,
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
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
                fields[key] = value
    elif content_type == "application/json":
        fields = await request.json()
    else:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Send plant data as JSON or multipart/form-data",
        )

    try:
        payload = PlantCreate.model_validate(fields)
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error.errors(include_context=False, include_url=False),
        )

    image_data = None
    image_extension = None
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

    nursery = _get_owned_nursery(nursery_id, owner, db)
    duplicate = db.scalar(
        select(Plant.id).where(Plant.nursery_id == nursery.id, Plant.name == payload.name)
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "This nursery already has a plant with this name")

    data = payload.model_dump()
    data["availability_status"] = payload.availability_status.value
    plant = Plant(
        nursery_id=nursery.id,
        approval_status=ListingApprovalStatus.PENDING.value,
        **data,
    )
    db.add(plant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if image_path is not None:
            image_path.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The plant could not be saved.")
    except SQLAlchemyError:
        db.rollback()
        if image_path is not None:
            image_path.unlink(missing_ok=True)
        raise
    db.refresh(plant)
    return plant


@router.get("/{nursery_id}/plants", response_model=list[PlantOut])
def list_nursery_plants(
    nursery_id: int,
    category: str | None = Query(None, max_length=50),
    availability: AvailabilityStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    nursery = db.get(Nursery, nursery_id)
    if nursery is None or nursery.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")

    stmt = select(Plant).where(
        Plant.nursery_id == nursery_id,
        Plant.approval_status == ListingApprovalStatus.APPROVED.value,
    )
    if category:
        stmt = stmt.where(Plant.category.ilike(category))
    if availability:
        stmt = stmt.where(Plant.availability_status == availability.value)
    return db.scalars(stmt.order_by(Plant.id.desc()).offset(skip).limit(limit)).all()