from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/rentals", tags=["Plant Rentals"])


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


# 3. Create Rental Request
@router.post("/", response_model=schemas.PlantRentalOrderResponse, status_code=status.HTTP_201_CREATED)
def create_rental_order(order: schemas.PlantRentalOrderCreate, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {order.user_id} not found."
        )

    # Check if plant exists
    plant = db.query(models.Plant).filter(models.Plant.id == order.plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {order.plant_id} not found."
        )

    # Calculate rental duration
    duration_days = (order.rental_end_date - order.rental_start_date).days
    if duration_days <= 0:
        duration_days = 1

    # Calculate total price
    total_price = order.quantity * order.rental_price_per_day * duration_days

    # Create rental order instance
    db_order = models.rental.PlantRentalOrder(
        user_id=order.user_id,
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