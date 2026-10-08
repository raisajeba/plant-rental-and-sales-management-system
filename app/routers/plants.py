from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Plant, User
from app.schemas.plant import PlantOut

router = APIRouter(prefix="/plants", tags=["Plants"])

@router.get("/{plant_id}", response_model=PlantOut)
def get_plant(plant_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    return plant