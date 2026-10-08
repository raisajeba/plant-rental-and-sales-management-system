from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.constants import AvailabilityStatus, RoleName
from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models import Nursery, Plant, User
from app.schemas.nursery import NurseryCreate, NurseryOut
from app.schemas.plant import PlantCreate, PlantOut

router = APIRouter(prefix="/nurseries", tags=["Nurseries"])

def _get_owned_nursery(nursery_id: int, user: User, db: Session) -> Nursery:
    nursery = db.get(Nursery, nursery_id)
    if nursery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    if nursery.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only add plants to your own nursery")
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

@router.get("", response_model=list[NurseryOut])
def list_nurseries(
    city: str | None = Query(None, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Nursery).where(Nursery.status == "active")
    if city:
        stmt = stmt.where(Nursery.city.ilike(f"%{city}%"))
    return db.scalars(stmt.order_by(Nursery.id.desc()).offset(skip).limit(limit)).all()

@router.get("/{nursery_id}", response_model=NurseryOut)
def get_nursery(
    nursery_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    nursery = db.get(Nursery, nursery_id)
    if nursery is None or nursery.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    return nursery

@router.post("/{nursery_id}/plants", response_model=PlantOut, status_code=status.HTTP_201_CREATED)
def add_plant_to_nursery(
    nursery_id: int,
    payload: PlantCreate,
    owner: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    nursery = _get_owned_nursery(nursery_id, owner, db)
    duplicate = db.scalar(
        select(Plant.id).where(Plant.nursery_id == nursery.id, Plant.name == payload.name)
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "This nursery already has a plant with this name")
    
    data = payload.model_dump()
    data["availability_status"] = payload.availability_status.value
    plant = Plant(nursery_id=nursery.id, **data)
    db.add(plant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The plant could not be saved.")
    db.refresh(plant)
    return plant

@router.get("/{nursery_id}/plants", response_model=list[PlantOut])
def list_nursery_plants(
    nursery_id: int,
    category: str | None = Query(None, max_length=50),
    availability: AvailabilityStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nursery = db.get(Nursery, nursery_id)
    if nursery is None or nursery.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nursery not found")
    
    stmt = select(Plant).where(Plant.nursery_id == nursery_id)
    if category:
        stmt = stmt.where(Plant.category.ilike(category))
    if availability:
        stmt = stmt.where(Plant.availability_status == availability.value)
    return db.scalars(stmt.order_by(Plant.id.desc()).offset(skip).limit(limit)).all()