from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/api/rentals",
    tags=["Plant Rentals"]
)


# 1. Browse Available Plants
@router.get("/plants", status_code=status.HTTP_200_OK)
def browse_available_plants(db: Session = Depends(get_db)):
    plants = db.query(models.Plant).all()
    return plants if plants else []


# 2. View Plant Details
@router.get("/plants/{plant_id}", status_code=status.HTTP_200_OK)
def get_plant_details(plant_id: int, db: Session = Depends(get_db)):
    plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found."
        )
    return plant


# 3. Create Rental Request (Requires Authentication)
@router.post("/", response_model=schemas.PlantRentalOrderResponse, status_code=status.HTTP_201_CREATED)
def create_rental_order(
    order: schemas.PlantRentalOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Check if plant exists
    plant = db.query(models.Plant).filter(models.Plant.id == order.plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {order.plant_id} not found."
        )

    # Check plant availability
    if hasattr(plant, "is_available") and not plant.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected plant is currently unavailable for rent."
        )

    # Calculate rental duration
    duration_days = (order.rental_end_date - order.rental_start_date).days
    if duration_days <= 0:
        duration_days = 1

    # Calculate total price
    total_price = order.quantity * order.rental_price_per_day * duration_days

    # Save to Database using Logged-in User ID
    db_order = models.rental.PlantRentalOrder(
        user_id=current_user.id,
        plant_id=order.plant_id,
        quantity=order.quantity,
        rental_start_date=order.rental_start_date,
        rental_end_date=order.rental_end_date,
        rental_duration_days=duration_days,
        rental_price_per_day=order.rental_price_per_day,
        total_amount=total_price,
        status=models.rental.RentalStatus.PENDING
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order