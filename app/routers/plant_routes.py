from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas.plant import PlantResponse, TransactionRequest
from services.plant_service import PlantStockService
from models.plant import Plant

router = APIRouter(prefix="/api/plants", tags=["Plants"])

@router.get("/", response_model=List[PlantResponse])
def get_all_plants(db: Session = Depends(get_db)):
    """Fetch all plant listings with latest status and quantity."""
    return db.query(Plant).all()

@router.post("/{plant_id}/purchase", response_model=PlantResponse)
def purchase_plant(plant_id: int, req: TransactionRequest, db: Session = Depends(get_db)):
    """Purchase plant and update stock."""
    return PlantStockService.process_transaction(db, plant_id, req.quantity)

@router.post("/{plant_id}/rent", response_model=PlantResponse)
def rent_plant(plant_id: int, req: TransactionRequest, db: Session = Depends(get_db)):
    """Rent plant and update stock."""
    return PlantStockService.process_transaction(db, plant_id, req.quantity)

@router.patch("/{plant_id}/update-stock", response_model=PlantResponse)
def update_plant_stock(plant_id: int, new_quantity: int, db: Session = Depends(get_db)):
    """Manual stock update by Nursery owner."""
    return PlantStockService.update_stock_manually(db, plant_id, new_quantity)