from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Plant, User, Nursery
from app.schemas.plant import PlantCreate, PlantUpdate, PlantOut

router = APIRouter(prefix="/plants", tags=["Plants"])


# Helper function: Check if current user owns the nursery that owns the plant
def verify_plant_ownership(db: Session, user_id: int, plant: Plant):
    nursery = db.query(Nursery).filter(Nursery.user_id == user_id).first()
    if not nursery or plant.nursery_id != nursery.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage plants for this nursery."
        )
    return nursery


# 1. Create Plant (Authenticated Nursery Owner Only)
@router.post("/", response_model=PlantOut, status_code=status.HTTP_201_CREATED)
def create_plant(
    plant_in: PlantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    nursery = db.query(Nursery).filter(Nursery.user_id == current_user.id).first()
    if not nursery:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must create a nursery profile first before adding plants."
        )

    db_plant = Plant(**plant_in.model_dump(), nursery_id=nursery.id)
    db.add(db_plant)
    db.commit()
    db.refresh(db_plant)
    return db_plant


# 2. Get Plant List (Filtering & Pagination)
@router.get("/", response_model=List[PlantOut])
def get_plants(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    only_available: bool = Query(True),
    db: Session = Depends(get_db)
):
    query = db.query(Plant)
    if only_available:
        query = query.filter(Plant.availability_status != "UNAVAILABLE", Plant.available_quantity > 0)
    if category:
        query = query.filter(Plant.category == category)
    
    return query.offset(skip).limit(limit).all()


# 3. Get Plant Details by ID
@router.get("/{plant_id}", response_model=PlantOut)
def get_plant(plant_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    return plant


# 4. Update Plant (Authenticated Nursery Owner Only)
@router.put("/{plant_id}", response_model=PlantOut)
def update_plant(
    plant_id: int,
    plant_in: PlantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")

    verify_plant_ownership(db, current_user.id, plant)

    update_data = plant_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plant, key, value)

    if plant.available_quantity == 0:
        plant.availability_status = "UNAVAILABLE"

    db.add(plant)
    db.commit()
    db.refresh(plant)
    return plant


# 5. Delete Plant (Authenticated Nursery Owner Only)
@router.delete("/{plant_id}", status_code=status.HTTP_200_OK)
def delete_plant(
    plant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")

    verify_plant_ownership(db, current_user.id, plant)

    db.delete(plant)
    db.commit()
    return {"message": "Plant deleted successfully"}