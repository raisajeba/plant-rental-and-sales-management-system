from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models.plant import Plant, AvailabilityStatus

class PlantStockService:

    @staticmethod
    def get_plant_with_lock(db: Session, plant_id: int) -> Plant:
        """Fetch plant row with database locking to prevent concurrent issues."""
        plant = db.query(Plant).filter(Plant.id == plant_id).with_for_update().first()
        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plant with ID {plant_id} not found."
            )
        return plant

    @staticmethod
    def process_transaction(db: Session, plant_id: int, requested_qty: int) -> Plant:
        """Deducts quantity and auto-updates availability for Purchases and Rentals."""
        try:
            plant = PlantStockService.get_plant_with_lock(db, plant_id)

            if plant.quantity == 0 or plant.availability_status == AvailabilityStatus.OUT_OF_STOCK:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This plant is currently Out of Stock."
                )

            if plant.quantity < requested_qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Requested quantity ({requested_qty}) exceeds available stock ({plant.quantity})."
                )

            plant.quantity -= requested_qty
            plant.update_availability_status()

            db.commit()
            db.refresh(plant)
            return plant

        except Exception as e:
            db.rollback()
            raise e

    @staticmethod
    def update_stock_manually(db: Session, plant_id: int, new_quantity: int) -> Plant:
        """Nursery Owner manually updates plant quantity."""
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity cannot be negative."
            )
        try:
            plant = PlantStockService.get_plant_with_lock(db, plant_id)
            plant.quantity = new_quantity
            plant.update_availability_status()

            db.commit()
            db.refresh(plant)
            return plant
        except Exception as e:
            db.rollback()
            raise e